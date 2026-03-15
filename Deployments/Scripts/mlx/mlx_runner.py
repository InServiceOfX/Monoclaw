#!/usr/bin/env python3
"""Unified launcher for mlx_lm.chat and mlx_lm.server using YAML config."""

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
EXAMPLE_CONFIG = Path(__file__).with_name("mlx_config.example.yml")

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


def load_config(config_path: Path) -> dict:
    if yaml is None:
        raise ConfigError(
            "PyYAML is required. Install with: python3 -m pip install pyyaml"
        )

    if not config_path.exists():
        raise ConfigError(
            f"Config not found: {config_path}\n"
            f"Copy {EXAMPLE_CONFIG.name} -> {DEFAULT_CONFIG.name} and edit it."
        )

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ConfigError("Config root must be a YAML mapping/object")

    return data


def resolve_mode(mode: str) -> str:
    return MODE_ALIASES.get(mode, mode)


def get_mode_config(cfg: dict, mode: str) -> dict:
    mode_key = resolve_mode(mode)
    modes = cfg.get("modes", {})
    if mode_key not in modes:
        available = ", ".join(sorted(modes.keys()))
        raise ConfigError(f"Unknown mode '{mode_key}'. Available: {available}")
    return dict(modes[mode_key] or {})


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise ConfigError(f"{label} not found: {path}")


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
        candidates = [p for p in snapshots.iterdir() if p.is_dir() and (p / "config.json").exists()]
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


def base_paths(cfg: dict) -> tuple[Path, Path, Path, Path]:
    paths = cfg.get("paths", {})
    venv_bin = Path(paths.get("venv_bin", "")).expanduser()
    raw_model_path = Path(paths.get("model_path", "")).expanduser()
    model_path = resolve_model_dir(raw_model_path)
    chat_bin = venv_bin / "mlx_lm.chat"
    server_bin = venv_bin / "mlx_lm.server"

    require_file(chat_bin, "mlx_lm.chat")
    require_file(server_bin, "mlx_lm.server")

    return venv_bin, model_path, chat_bin, server_bin


def run_chat(args: argparse.Namespace, cfg: dict) -> int:
    _, model_path, chat_bin, _ = base_paths(cfg)
    mode_cfg = get_mode_config(cfg, args.mode)
    chat_cfg = cfg.get("chat", {}) or {}

    cmd = [
        str(chat_bin),
        "--model",
        str(model_path),
    ]

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

    # mlx_lm.chat currently only exposes --trust-remote-code for tokenizer config.
    # fix_mistral_regex is not exposed by the CLI (would require upstream mlx-lm change).
    trust_remote_code = chat_cfg.get("trust_remote_code")
    if trust_remote_code is True:
        cmd.append("--trust-remote-code")

    if chat_cfg.get("fix_mistral_regex") is True:
        print(
            "[mlx_runner] NOTE: fix_mistral_regex requested, but mlx_lm.chat CLI does not currently expose this tokenizer flag.",
            file=sys.stderr,
        )

    if args.seed is not None:
        cmd.extend(["--seed", str(args.seed)])

    print(f"[mlx_runner] chat mode={resolve_mode(args.mode)} model={model_path}")
    print(f"[mlx_runner] exec: {shlex.join(cmd)}")
    os.execv(cmd[0], cmd)
    return 0


def run_serve(args: argparse.Namespace, cfg: dict) -> int:
    _, model_path, _, server_bin = base_paths(cfg)
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

    decode_concurrency = serve_cfg.get("decode_concurrency")
    prompt_concurrency = serve_cfg.get("prompt_concurrency")
    allowed_origins = serve_cfg.get("allowed_origins")

    # Optional thinking toggle in server default template args.
    enable_thinking = mode_cfg.get("enable_thinking")

    # Only check port collision when we are explicitly setting a port.
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

    cmd = [
        str(server_bin),
        "--model",
        str(model_path),
    ]

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

    if allowed_origins is not None:
        if command_supports_flag(server_bin, "--allowed-origins"):
            cmd.extend(["--allowed-origins", str(allowed_origins)])
        else:
            print(
                "[mlx_runner] NOTE: serve.allowed_origins is set but this mlx_lm.server build does not support --allowed-origins; skipping.",
                file=sys.stderr,
            )
    if decode_concurrency is not None:
        cmd.extend(["--decode-concurrency", str(int(decode_concurrency))])
    if prompt_concurrency is not None:
        cmd.extend(["--prompt-concurrency", str(int(prompt_concurrency))])

    trust_remote_code = serve_cfg.get("trust_remote_code")
    if trust_remote_code is True:
        cmd.append("--trust-remote-code")

    if serve_cfg.get("fix_mistral_regex") is True:
        print(
            "[mlx_runner] NOTE: fix_mistral_regex requested, but mlx_lm.server CLI does not currently expose this tokenizer flag.",
            file=sys.stderr,
        )

    endpoint_host = host if host is not None else "127.0.0.1"
    endpoint_port = int(port) if port is not None else 8080
    print(f"[mlx_runner] serve mode={resolve_mode(args.mode)} endpoint=http://{endpoint_host}:{endpoint_port}/v1")
    print("[mlx_runner] NOTE: set repetition_penalty per request (recommend 1.15 for quantized reasoning).")
    print(f"[mlx_runner] exec: {shlex.join(cmd)}")
    os.execv(cmd[0], cmd)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run mlx_lm.chat or mlx_lm.server from YAML config")
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to YAML config (default: mlx_config.yml)")

    sub = p.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="Run mlx_lm.chat")
    chat.add_argument("--mode", default="thinking", help="Mode key or alias (thinking, coding, instruct, reasoning)")
    chat.add_argument("--system", help="Override system prompt")
    chat.add_argument("--temp", type=float)
    chat.add_argument("--top-p", type=float)
    chat.add_argument("--max-tokens", type=int)
    chat.add_argument("--max-kv-size", type=int)
    chat.add_argument("--seed", type=int)

    serve = sub.add_parser("serve", help="Run mlx_lm.server")
    serve.add_argument("--mode", default="thinking", help="Mode key or alias (thinking, coding, instruct, reasoning)")
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
        cfg = load_config(Path(args.config).expanduser())
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
