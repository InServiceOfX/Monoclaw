#!/usr/bin/env python3
"""Unified launcher for mlx_vlm.chat and mlx_vlm.server using YAML config.

Config is split into two layers:
  1. Global config (mlx_vlm_config.yml) — host, port, mlx_bin_dir, etc.
  2. Per-model profile (profiles/<name>.yml) — model_path, KV settings, etc.

Profile values override global values when both are present.
All fields are optional EXCEPT model_path (required in the profile).
"""

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


class ConfigError(RuntimeError):
    pass


def load_yaml(path: Path) -> dict:
    if yaml is None:
        raise ConfigError("PyYAML is required. Install with: python3 -m pip install pyyaml")
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


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise ConfigError(f"{label} not found: {path}")


def resolve_model_dir(raw_path: Path) -> Path:
    """Resolve a usable MLX model directory containing config.json."""
    if not raw_path.exists():
        raise ConfigError(f"model path not found: {raw_path}")

    if (raw_path / "config.json").exists():
        return raw_path

    snapshots = raw_path / "snapshots"
    if snapshots.is_dir():
        candidates = [
            p for p in snapshots.iterdir()
            if p.is_dir() and (p / "config.json").exists()
        ]
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
        "model_path must point to a directory containing config.json, "
        "or a HuggingFace cache repo root containing snapshots/."
    )


def resolve_bin_dir(cfg: dict) -> Path:
    """Get the directory containing mlx_vlm binaries.

    Looks for 'mlx_bin_dir' in paths. Falls back to legacy 'mlx_vlm_bin_dir' for
    backward compatibility.
    """
    paths = cfg.get("paths", {})
    raw = paths.get("mlx_bin_dir") or paths.get("mlx_vlm_bin_dir")
    if not raw:
        raise ConfigError(
            "Config must specify paths.mlx_bin_dir — the directory containing "
            "mlx_vlm.server, mlx_vlm.chat, etc."
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


def run_chat(args: argparse.Namespace, cfg: dict) -> int:
    model_path = resolve_model_path(cfg)
    bin_dir = resolve_bin_dir(cfg)
    chat_bin = bin_dir / "mlx_vlm.chat"
    require_file(chat_bin, "mlx_vlm.chat")

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

    enable_thinking = chat_cfg.get("enable_thinking")
    if enable_thinking is True:
        cmd.append("--enable-thinking")

    print(f"[mlx_vlm_runner] chat model={model_path}")
    print(f"[mlx_vlm_runner] exec: {shlex.join(cmd)}")
    os.execv(cmd[0], cmd)
    return 0


def run_serve(args: argparse.Namespace, cfg: dict) -> int:
    model_path = resolve_model_path(cfg)
    bin_dir = resolve_bin_dir(cfg)
    server_bin = bin_dir / "mlx_vlm.server"
    require_file(server_bin, "mlx_vlm.server")

    serve_cfg = cfg.get("serve", {}) or {}

    host = args.host if args.host is not None else serve_cfg.get("host", "127.0.0.1")
    port = args.port if args.port is not None else int(serve_cfg.get("port", 8081))

    # Port collision check
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

    # All optional flags from mlx_vlm.server --help
    trust_remote_code = serve_cfg.get("trust_remote_code")
    if trust_remote_code is True:
        cmd.append("--trust-remote-code")

    prefill_step_size = serve_cfg.get("prefill_step_size")
    if prefill_step_size is not None:
        cmd.extend(["--prefill-step-size", str(int(prefill_step_size))])

    kv_bits = serve_cfg.get("kv_bits")
    if kv_bits is not None:
        cmd.extend(["--kv-bits", str(float(kv_bits))])

    kv_quant_scheme = serve_cfg.get("kv_quant_scheme")
    if kv_quant_scheme is not None:
        cmd.extend(["--kv-quant-scheme", str(kv_quant_scheme)])

    kv_group_size = serve_cfg.get("kv_group_size")
    if kv_group_size is not None:
        cmd.extend(["--kv-group-size", str(int(kv_group_size))])

    max_kv_size = serve_cfg.get("max_kv_size")
    if max_kv_size is not None:
        cmd.extend(["--max-kv-size", str(int(max_kv_size))])

    quantized_kv_start = serve_cfg.get("quantized_kv_start")
    if quantized_kv_start is not None:
        cmd.extend(["--quantized-kv-start", str(int(quantized_kv_start))])

    adapter_path = serve_cfg.get("adapter_path")
    if adapter_path is not None:
        cmd.extend(["--adapter-path", str(adapter_path)])

    reload_ = serve_cfg.get("reload")
    if reload_ is True:
        cmd.append("--reload")

    print(f"[mlx_vlm_runner] serve endpoint=http://{host}:{port}/v1")
    print(f"[mlx_vlm_runner] model={model_path}")
    print(f"[mlx_vlm_runner] exec: {shlex.join(cmd)}")
    os.execv(cmd[0], cmd)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run mlx_vlm.chat or mlx_vlm.server from YAML config + profile"
    )
    p.add_argument(
        "--config", default=str(DEFAULT_CONFIG),
        help="Path to global YAML config (default: mlx_vlm_config.yml)"
    )
    p.add_argument(
        "--profile",
        help="Path to per-model profile YAML (merged on top of global config)"
    )

    sub = p.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="Run mlx_vlm.chat")
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
        cfg = load_yaml(Path(args.config).expanduser())

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
