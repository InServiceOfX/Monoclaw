#!/usr/bin/env python3
"""Unified launcher for mlx_vlm.chat and mlx_vlm.server using YAML config."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


DEFAULT_CONFIG = Path(__file__).with_name("mlx_vlm_config.yml")
EXAMPLE_CONFIG = Path(__file__).with_name("mlx_vlm_config.example.yml")

# NOTE: We no longer default to a single config file for every run.
# Instead, we encourage using --profile <name> which points to a specific
# profile YAML that contains model + sampling settings. The main config
# is used for common non-model-specific settings (host, port, log_level, etc).


class ConfigError(RuntimeError):
    pass


def load_config(config_path: Path) -> dict:
    if yaml is None:
        raise ConfigError("PyYAML is required. Install with: python3 -m pip install pyyaml")
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


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise ConfigError(f"{label} not found: {path}")


def resolve_model_dir(raw_path: Path) -> Path:
    if not raw_path.exists():
        raise ConfigError(f"model path not found: {raw_path}")
    if (raw_path / "config.json").exists():
        return raw_path
    snapshots = raw_path / "snapshots"
    if snapshots.is_dir():
        candidates = [p for p in snapshots.iterdir() if p.is_dir() and (p / "config.json").exists()]
        if not candidates:
            raise ConfigError(f"No valid snapshots with config.json under: {snapshots}")
        ref_main = raw_path / "refs" / "main"
        if ref_main.exists():
            try:
                target_hash = ref_main.read_text(encoding="utf-8").strip()
                preferred = snapshots / target_hash
                if (preferred / "config.json").exists():
                    return preferred
            except Exception:
                pass
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]
    raise ConfigError(
        "model_path must point to a directory containing config.json, or a HuggingFace cache repo root containing snapshots/."
    )


def base_paths(cfg: dict) -> tuple[Path, Path, Path, Path]:
    paths = cfg.get("paths", {}) or {}

    # mlx_vlm_bin_dir = directory containing mlx_vlm.chat, mlx_vlm.server, etc.
    # Usually: /Users/ernestyeung/Prop/openclaw/.venv/bin
    bin_dir = Path(paths.get("mlx_vlm_bin_dir", "")).expanduser()
    raw_model_path = Path(paths.get("model_path", "")).expanduser()

    if not raw_model_path:
        raise ConfigError("model_path is REQUIRED in config or profile")

    model_path = resolve_model_dir(raw_model_path)

    chat_bin = bin_dir / "mlx_vlm.chat"
    server_bin = bin_dir / "mlx_vlm.server"
    require_file(chat_bin, "mlx_vlm.chat")
    require_file(server_bin, "mlx_vlm.server")
    return bin_dir, model_path, chat_bin, server_bin


def run_chat(args: argparse.Namespace, cfg: dict) -> int:
    _, model_path, chat_bin, _ = base_paths(cfg)
    chat_cfg = cfg.get("chat", {}) or {}

    cmd = [str(chat_bin), "--model", str(model_path)]

    max_tokens = args.max_tokens if args.max_tokens is not None else chat_cfg.get("max_tokens")
    if max_tokens is not None:
        cmd.extend(["--max-tokens", str(int(max_tokens))])

    temperature = args.temp if args.temp is not None else chat_cfg.get("temperature")
    if temperature is not None:
        cmd.extend(["--temperature", str(float(temperature))])

    resize_shape = chat_cfg.get("resize_shape")
    if resize_shape:
        cmd.extend(["--resize-shape"] + [str(x) for x in resize_shape])

    kv_bits = chat_cfg.get("kv_bits")
    if kv_bits is not None:
        cmd.extend(["--kv-bits", str(float(kv_bits))])

    max_kv_size = chat_cfg.get("max_kv_size")
    if max_kv_size is not None:
        cmd.extend(["--max-kv-size", str(int(max_kv_size))])

    prefill_step_size = chat_cfg.get("prefill_step_size")
    if prefill_step_size is not None:
        cmd.extend(["--prefill-step-size", str(int(prefill_step_size))])

    enable_thinking = chat_cfg.get("enable_thinking", True)
    if enable_thinking:
        cmd.append("--enable-thinking")

    print(f"[mlx_vlm_runner] chat model={model_path}")
    print(f"[mlx_vlm_runner] exec: {shlex.join(cmd)}")
    os.execv(cmd[0], cmd)
    return 0


def run_serve(args: argparse.Namespace, cfg: dict) -> int:
    _, model_path, _, server_bin = base_paths(cfg)
    serve_cfg = cfg.get("serve", {}) or {}

    host = args.host if args.host is not None else serve_cfg.get("host", "0.0.0.0")
    port = args.port if args.port is not None else int(serve_cfg.get("port", 8081))

    if shutil.which("lsof"):
        check = subprocess.run(
            ["lsof", f"-iTCP:{int(port)}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
        )
        if check.returncode == 0 and check.stdout.strip():
            pid = check.stdout.strip().splitlines()[0]
            raise ConfigError(f"Port {port} is already in use by PID {pid}. Use --port to change.")

    cmd = [str(server_bin), "--model", str(model_path)]

    cmd.extend(["--host", str(host)])
    cmd.extend(["--port", str(int(port))])

    trust_remote_code = serve_cfg.get("trust_remote_code", True)
    if trust_remote_code:
        cmd.append("--trust-remote-code")

    prefill_step_size = serve_cfg.get("prefill_step_size")
    if prefill_step_size is not None:
        cmd.extend(["--prefill-step-size", str(int(prefill_step_size))])

    max_kv_size = serve_cfg.get("max_kv_size")
    if max_kv_size is not None:
        cmd.extend(["--max-kv-size", str(int(max_kv_size))])

    kv_bits = serve_cfg.get("kv_bits")
    if kv_bits is not None:
        cmd.extend(["--kv-bits", str(float(kv_bits))])

    kv_quant_scheme = serve_cfg.get("kv_quant_scheme")
    if kv_quant_scheme:
        cmd.extend(["--kv-quant-scheme", str(kv_quant_scheme)])

    kv_group_size = serve_cfg.get("kv_group_size")
    if kv_group_size is not None:
        cmd.extend(["--kv-group-size", str(int(kv_group_size))])

    quantized_kv_start = serve_cfg.get("quantized_kv_start")
    if quantized_kv_start is not None:
        cmd.extend(["--quantized-kv-start", str(int(quantized_kv_start))])

    reload_ = serve_cfg.get("reload", False)
    if reload_:
        cmd.append("--reload")

    extra_args = serve_cfg.get("extra_args", []) or []
    cmd.extend(extra_args)

    print(f"[mlx_vlm_runner] serve endpoint=http://{host}:{port}/v1")
    print(f"[mlx_vlm_runner] exec: {shlex.join(cmd)}")
    os.execv(cmd[0], cmd)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run mlx_vlm.chat or mlx_vlm.server from YAML config")
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to YAML config (default: mlx_vlm_config.yml)")

    sub = p.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="Run mlx_vlm.chat (interactive)")
    chat.add_argument("--temp", type=float)
    chat.add_argument("--max-tokens", type=int)

    serve = sub.add_parser("serve", help="Run mlx_vlm.server")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)

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
