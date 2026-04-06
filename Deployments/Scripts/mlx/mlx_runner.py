#!/usr/bin/env python3
"""Unified launcher for mlx_lm.chat and mlx_lm.server using YAML config.

Config is split into two layers:
  1. Global config (mlx_config.yml) — host, port, log_level, mlx_bin_dir, etc.
  2. Per-model profile (profiles/<name>.yml) — model_path, sampling params, modes, etc.

Profile values override global values when both are present.
All fields are optional EXCEPT model_path (required in the profile).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import shlex
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


DEFAULT_CONFIG = Path(__file__).with_name("mlx_config.yml")
EXAMPLE_CONFIG = Path(__file__).with_name("mlx_config.yml.example")

MODE_ALIASES = {
    "thinking": "thinking_general",
    "coding": "thinking_coding",
    "instruct": "instruct_general",
    "no-think": "instruct_general",
    "reasoning": "instruct_reasoning",
}


class ConfigError(RuntimeError):
    pass


def command_supports_flag(executable: Path, flag: str) -> bool:
    try:
        out = subprocess.run(
            [str(executable), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        help_text = (out.stdout or "") + "\n" + (out.stderr or "")
        return flag in help_text
    except Exception:
        return False


def load_yaml(path: Path) -> dict:
    if yaml is None:
        raise ConfigError(
            "PyYAML is required. Install with: python3 -m pip install pyyaml"
        )
    if not path.exists():
        raise ConfigError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a YAML mapping/object: {path}")
    return data


def deep_merge(base: dict, overlay: dict) -> dict:
    """Merge overlay into base (overlay wins). Nested dicts are merged recursively."""
    merged = dict(base)
    for k, v in overlay.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def resolve_mode(mode: str) -> str:
    return MODE_ALIASES.get(mode, mode)


def get_mode_config(cfg: dict, mode: str) -> dict:
    mode_key = resolve_mode(mode)
    modes = cfg.get("modes", {})
    if not modes:
        # No modes defined — return empty (all defaults)
        return {}
    if mode_key not in modes:
        available = ", ".join(sorted(modes.keys()))
        raise ConfigError(f"Unknown mode '{mode_key}'. Available: {available}")
    return dict(modes[mode_key] or {})


def enforce_min_tokens(max_tokens: int) -> int:
    if max_tokens < 4096:
        print(
            "[mlx_runner] WARNING: max_tokens < 4096 is unsafe for this model; clamping to 4096.",
            file=sys.stderr,
        )
        return 4096
    return max_tokens


def resolve_model_dir(raw_path: Path) -> Path:
    """Resolve a usable MLX model directory containing config.json.

    Supports either:
    - direct snapshot/model directory (contains config.json), or
    - HF cache repo root (.../models--foo--bar) and auto-picks a snapshot.
    """
    if not raw_path.exists():
        raise ConfigError(f"model path not found: {raw_path}")

    # 1) Direct model directory
    if (raw_path / "config.json").exists():
        return raw_path

    # 2) HuggingFace cache layout: models--*/snapshots/<hash>/config.json
    snapshots = raw_path / "snapshots"
    if snapshots.is_dir():
        candidates = [
            p for p in snapshots.iterdir()
            if p.is_dir() and (p / "config.json").exists()
        ]
        if not candidates:
            raise ConfigError(
                f"No valid snapshots with config.json under: {snapshots}"
            )

        # Prefer refs/main target when available.
        ref_main = raw_path / "refs" / "main"
        if ref_main.exists():
            try:
                target_hash = ref_main.read_text(encoding="utf-8").strip()
                preferred = snapshots / target_hash
                if (preferred / "config.json").exists():
                    return preferred
            except Exception:
                pass

        # Fallback to newest mtime snapshot.
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    raise ConfigError(
        "model_path must point to a directory containing config.json, "
        "or a HuggingFace cache repo root containing snapshots/."
    )


def resolve_bin_dir(cfg: dict) -> Path:
    """Get the directory containing mlx_lm binaries (mlx_lm.server, mlx_lm.chat, etc.).

    Looks for 'mlx_bin_dir' in the config. Falls back to legacy 'venv_bin' for
    backward compatibility.
    """
    paths = cfg.get("paths", {})
    raw = paths.get("mlx_bin_dir") or paths.get("venv_bin")
    if not raw:
        raise ConfigError(
            "Config must specify paths.mlx_bin_dir — the directory containing "
            "mlx_lm.server, mlx_lm.chat, etc."
        )
    bin_dir = Path(raw).expanduser()
    if not bin_dir.is_dir():
        raise ConfigError(f"mlx_bin_dir not found: {bin_dir}")
    return bin_dir


def resolve_model_path(cfg: dict) -> Path:
    """Get the model_path from config (required)."""
    paths = cfg.get("paths", {})
    raw = paths.get("model_path")
    if not raw:
        raise ConfigError(
            "Profile must specify paths.model_path — the local path to MLX model weights."
        )
    return resolve_model_dir(Path(raw).expanduser())


def get_bins(cfg: dict) -> tuple[Path, Path, Path]:
    """Return (bin_dir, chat_bin, server_bin)."""
    bin_dir = resolve_bin_dir(cfg)
    chat_bin = bin_dir / "mlx_lm.chat"
    server_bin = bin_dir / "mlx_lm.server"
    # Only check existence of the one we'll actually use later,
    # but return both for the caller to pick.
    return bin_dir, chat_bin, server_bin


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise ConfigError(f"{label} not found: {path}")


def run_chat(args: argparse.Namespace, cfg: dict) -> int:
    model_path = resolve_model_path(cfg)
    _, chat_bin, _ = get_bins(cfg)
    require_file(chat_bin, "mlx_lm.chat")

    mode_cfg = get_mode_config(cfg, args.mode)
    chat_cfg = cfg.get("chat", {}) or {}

    cmd = [str(chat_bin), "--model", str(model_path)]

    temp = args.temp if args.temp is not None else mode_cfg.get("temperature")
    if temp is not None:
        cmd.extend(["--temp", str(temp)])

    top_p = args.top_p if args.top_p is not None else mode_cfg.get("top_p")
    if top_p is not None:
        cmd.extend(["--top-p", str(top_p)])

    max_tokens = args.max_tokens if args.max_tokens is not None else mode_cfg.get("max_tokens")
    if max_tokens is not None:
        cmd.extend(["--max-tokens", str(enforce_min_tokens(int(max_tokens)))])

    max_kv_size = args.max_kv_size if args.max_kv_size is not None else chat_cfg.get("max_kv_size")
    if max_kv_size is not None:
        cmd.extend(["--max-kv-size", str(max_kv_size)])

    system_prompt = args.system if args.system is not None else mode_cfg.get("system_prompt")
    if system_prompt is None:
        system_prompt = chat_cfg.get("default_system_prompt")
    if system_prompt is not None:
        cmd.extend(["--system-prompt", str(system_prompt)])

    trust_remote_code = chat_cfg.get("trust_remote_code")
    if trust_remote_code is True:
        cmd.append("--trust-remote-code")

    if args.seed is not None:
        cmd.extend(["--seed", str(args.seed)])

    print(f"[mlx_runner] chat mode={resolve_mode(args.mode)} model={model_path}")
    print(f"[mlx_runner] exec: {shlex.join(cmd)}")
    os.execv(cmd[0], cmd)
    return 0


def run_serve(args: argparse.Namespace, cfg: dict) -> int:
    model_path = resolve_model_path(cfg)
    _, _, server_bin = get_bins(cfg)
    require_file(server_bin, "mlx_lm.server")

    mode_cfg = get_mode_config(cfg, args.mode)
    serve_cfg = cfg.get("serve", {}) or {}

    host = args.host if args.host is not None else serve_cfg.get("host")
    port = args.port if args.port is not None else serve_cfg.get("port")
    log_level = args.log_level if args.log_level is not None else serve_cfg.get("log_level")

    temp = args.temp if args.temp is not None else mode_cfg.get("temperature")
    top_p = args.top_p if args.top_p is not None else mode_cfg.get("top_p")
    top_k = args.top_k if args.top_k is not None else mode_cfg.get("top_k")
    min_p = args.min_p if args.min_p is not None else mode_cfg.get("min_p")
    max_tokens = args.max_tokens if args.max_tokens is not None else mode_cfg.get("max_tokens")

    # Server-specific options from config (all optional)
    decode_concurrency = serve_cfg.get("decode_concurrency")
    prompt_concurrency = serve_cfg.get("prompt_concurrency")
    prefill_step_size = serve_cfg.get("prefill_step_size")
    prompt_cache_size = serve_cfg.get("prompt_cache_size")
    prompt_cache_bytes = serve_cfg.get("prompt_cache_bytes")
    pipeline = serve_cfg.get("pipeline")
    chat_template = serve_cfg.get("chat_template")
    use_default_chat_template = serve_cfg.get("use_default_chat_template")
    adapter_path = serve_cfg.get("adapter_path")
    draft_model = serve_cfg.get("draft_model")
    num_draft_tokens = serve_cfg.get("num_draft_tokens")

    # Optional thinking toggle in server default template args.
    enable_thinking = mode_cfg.get("enable_thinking")

    # Port collision check
    if port is not None and shutil.which("lsof"):
        port_num = int(port)
        check = subprocess.run(
            ["lsof", f"-iTCP:{port_num}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
        )
        if check.returncode == 0 and check.stdout.strip():
            pid = check.stdout.strip().splitlines()[0]
            raise ConfigError(
                f"Port {port_num} is already in use by PID {pid}. Use --port to change."
            )

    cmd = [str(server_bin), "--model", str(model_path)]

    if host is not None:
        cmd.extend(["--host", str(host)])
    if port is not None:
        cmd.extend(["--port", str(int(port))])
    if log_level is not None:
        cmd.extend(["--log-level", str(log_level)])

    if temp is not None:
        cmd.extend(["--temp", str(temp)])
    if top_p is not None:
        cmd.extend(["--top-p", str(top_p)])
    if top_k is not None:
        cmd.extend(["--top-k", str(top_k)])
    if min_p is not None:
        cmd.extend(["--min-p", str(min_p)])
    if max_tokens is not None:
        cmd.extend(["--max-tokens", str(enforce_min_tokens(int(max_tokens)))])

    if enable_thinking is not None:
        chat_template_args = json.dumps({"enable_thinking": bool(enable_thinking)})
        cmd.extend(["--chat-template-args", chat_template_args])

    if decode_concurrency is not None:
        cmd.extend(["--decode-concurrency", str(int(decode_concurrency))])
    if prompt_concurrency is not None:
        cmd.extend(["--prompt-concurrency", str(int(prompt_concurrency))])
    if prefill_step_size is not None:
        cmd.extend(["--prefill-step-size", str(int(prefill_step_size))])
    if prompt_cache_size is not None:
        cmd.extend(["--prompt-cache-size", str(int(prompt_cache_size))])
    if prompt_cache_bytes is not None:
        cmd.extend(["--prompt-cache-bytes", str(int(prompt_cache_bytes))])
    if pipeline is True:
        cmd.append("--pipeline")
    if chat_template is not None:
        cmd.extend(["--chat-template", str(chat_template)])
    if use_default_chat_template is True:
        cmd.append("--use-default-chat-template")
    if adapter_path is not None:
        cmd.extend(["--adapter-path", str(adapter_path)])
    if draft_model is not None:
        cmd.extend(["--draft-model", str(draft_model)])
    if num_draft_tokens is not None:
        cmd.extend(["--num-draft-tokens", str(int(num_draft_tokens))])

    trust_remote_code = serve_cfg.get("trust_remote_code")
    if trust_remote_code is True:
        cmd.append("--trust-remote-code")

    endpoint_host = host if host is not None else "127.0.0.1"
    endpoint_port = int(port) if port is not None else 8080
    print(f"[mlx_runner] serve mode={resolve_mode(args.mode)} endpoint=http://{endpoint_host}:{endpoint_port}/v1")
    print(f"[mlx_runner] model={model_path}")
    print(f"[mlx_runner] exec: {shlex.join(cmd)}")
    os.execv(cmd[0], cmd)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run mlx_lm.chat or mlx_lm.server from YAML config + profile"
    )
    p.add_argument(
        "--config", default=str(DEFAULT_CONFIG),
        help="Path to global YAML config (default: mlx_config.yml)"
    )
    p.add_argument(
        "--profile",
        help="Path to per-model profile YAML (merged on top of global config)"
    )

    sub = p.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="Run mlx_lm.chat")
    chat.add_argument("--mode", default="thinking")
    chat.add_argument("--system", help="Override system prompt")
    chat.add_argument("--temp", type=float)
    chat.add_argument("--top-p", type=float)
    chat.add_argument("--max-tokens", type=int)
    chat.add_argument("--max-kv-size", type=int)
    chat.add_argument("--seed", type=int)

    serve = sub.add_parser("serve", help="Run mlx_lm.server")
    serve.add_argument("--mode", default="thinking")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--log-level")
    serve.add_argument("--temp", type=float)
    serve.add_argument("--top-p", type=float)
    serve.add_argument("--top-k", type=int)
    serve.add_argument("--min-p", type=float)
    serve.add_argument("--max-tokens", type=int)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        # Load global config
        cfg = load_yaml(Path(args.config).expanduser())

        # Merge profile on top if provided
        if args.profile:
            profile = load_yaml(Path(args.profile).expanduser())
            cfg = deep_merge(cfg, profile)

        if args.command == "chat":
            return run_chat(args, cfg)
        if args.command == "serve":
            return run_serve(args, cfg)
        parser.error(f"Unknown command: {args.command}")
        return 2
    except ConfigError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
