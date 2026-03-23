#!/usr/bin/env python3
"""Config-driven wrapper for trtllm-serve."""

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


DEFAULT_CONFIG = Path(__file__).with_name("trtllm_config.yml")
EXAMPLE_CONFIG = Path(__file__).with_name("trtllm_config.example.yml")

MODE_ALIASES = {
    "thinking": "thinking_general",
    "coding": "thinking_coding",
    "instruct": "instruct_general",
    "no-think": "instruct_general",
    "reasoning": "reasoning_qwen3",
}


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


def resolve_mode(mode: str) -> str:
    return MODE_ALIASES.get(mode, mode)


def get_mode_config(cfg: dict, mode: str) -> dict:
    mode_key = resolve_mode(mode)
    modes = cfg.get("modes", {}) or {}
    if mode_key not in modes:
        available = ", ".join(sorted(modes.keys()))
        raise ConfigError(f"Unknown mode '{mode_key}'. Available: {available}")
    return dict(modes[mode_key] or {})


def ensure_path(path_str: str | None, label: str, *, must_exist: bool = True) -> Path | None:
    if not path_str:
        return None
    path = Path(path_str).expanduser()
    if must_exist and not path.exists():
        raise ConfigError(f"{label} not found: {path}")
    return path


def ensure_command(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise ConfigError(f"Required command not found in PATH: {name}")
    return resolved


def port_in_use(port: int) -> str | None:
    if not shutil.which("lsof"):
        return None
    check = subprocess.run(
        ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode == 0 and check.stdout.strip():
        return check.stdout.strip().splitlines()[0]
    return None


def add_flag(cmd: list[str], flag: str, value) -> None:
    if value is None:
        return
    cmd.extend([flag, str(value)])


def add_bool_flag(cmd: list[str], flag: str, enabled) -> None:
    if enabled is True:
        cmd.append(flag)


def maybe_add_mount_env(env_cfg: dict, model_path: Path) -> None:
    env_var = env_cfg.get("mount_hint_env_var")
    if not env_var:
        return
    os.environ.setdefault(str(env_var), str(model_path.parent))


def build_serve_command(args: argparse.Namespace, cfg: dict) -> tuple[list[str], str, int]:
    serve_bin = ensure_command(cfg.get("commands", {}).get("trtllm_serve", "trtllm-serve"))

    paths = cfg.get("paths", {}) or {}
    model_path = ensure_path(paths.get("model_path"), "model_path")
    if model_path is None:
        raise ConfigError("paths.model_path is required")

    config_path = ensure_path(paths.get("extra_llm_config"), "extra_llm_config")
    chat_template = ensure_path(paths.get("chat_template"), "chat_template")
    tokenizer = ensure_path(paths.get("tokenizer"), "tokenizer")

    serve_cfg = cfg.get("serve", {}) or {}
    mode_cfg = get_mode_config(cfg, args.mode)
    env_cfg = cfg.get("environment", {}) or {}

    host = args.host if args.host is not None else serve_cfg.get("host", "127.0.0.1")
    port = int(args.port if args.port is not None else serve_cfg.get("port", 8000))

    collision = port_in_use(port)
    if collision:
        raise ConfigError(f"Port {port} is already in use by PID {collision}. Use --port to change it.")

    maybe_add_mount_env(env_cfg, model_path)

    cmd = [serve_bin, "serve", str(model_path)]
    add_flag(cmd, "--host", host)
    add_flag(cmd, "--port", port)
    add_flag(cmd, "--backend", args.backend if args.backend is not None else serve_cfg.get("backend"))
    add_flag(cmd, "--log_level", args.log_level if args.log_level is not None else serve_cfg.get("log_level"))
    add_flag(cmd, "--served_model_name", serve_cfg.get("served_model_name"))
    add_flag(cmd, "--tokenizer", tokenizer)
    add_flag(cmd, "--max_batch_size", args.max_batch_size if args.max_batch_size is not None else serve_cfg.get("max_batch_size"))
    add_flag(cmd, "--max_num_tokens", args.max_num_tokens if args.max_num_tokens is not None else serve_cfg.get("max_num_tokens"))
    add_flag(cmd, "--max_seq_len", args.max_seq_len if args.max_seq_len is not None else serve_cfg.get("max_seq_len"))
    add_flag(cmd, "--max_beam_width", serve_cfg.get("max_beam_width"))
    add_flag(cmd, "--gpus_per_node", serve_cfg.get("gpus_per_node"))
    add_flag(cmd, "--free_gpu_memory_fraction", args.kv_cache_free_gpu_memory_fraction if args.kv_cache_free_gpu_memory_fraction is not None else serve_cfg.get("kv_cache_free_gpu_memory_fraction"))
    add_flag(cmd, "--kv_cache_dtype", serve_cfg.get("kv_cache_dtype"))
    add_flag(cmd, "--num_postprocess_workers", serve_cfg.get("num_postprocess_workers"))
    add_flag(cmd, "--reasoning_parser", args.reasoning_parser if args.reasoning_parser is not None else mode_cfg.get("reasoning_parser"))
    add_flag(cmd, "--tool_parser", args.tool_parser if args.tool_parser is not None else mode_cfg.get("tool_parser"))
    add_flag(cmd, "--chat_template", chat_template)
    add_flag(cmd, "--config", config_path)

    add_bool_flag(cmd, "--trust_remote_code", serve_cfg.get("trust_remote_code"))
    add_bool_flag(cmd, "--enable_chunked_prefill", serve_cfg.get("enable_chunked_prefill"))
    add_bool_flag(cmd, "--grpc", serve_cfg.get("grpc"))

    return cmd, host, port


def build_probe_command(args: argparse.Namespace, cfg: dict) -> tuple[list[str], str]:
    probe_cfg = cfg.get("probe", {}) or {}
    serve_cfg = cfg.get("serve", {}) or {}
    paths = cfg.get("paths", {}) or {}

    host = args.host if args.host is not None else serve_cfg.get("host", "127.0.0.1")
    port = int(args.port if args.port is not None else serve_cfg.get("port", 8000))
    model_name = probe_cfg.get("model_name") or serve_cfg.get("served_model_name") or Path(paths.get("model_path", "model")).name
    system_prompt = probe_cfg.get("system_prompt", "You are a helpful assistant.")
    user_prompt = args.prompt if args.prompt is not None else probe_cfg.get("prompt", "Where is New York?")
    max_tokens = int(args.max_tokens if args.max_tokens is not None else probe_cfg.get("max_tokens", 32))
    temperature = args.temperature if args.temperature is not None else probe_cfg.get("temperature", 0)

    json_payload = (
        '{'
        f'"model":"{model_name}",' 
        f'"messages":[{{"role":"system","content":{system_prompt!r}}},{{"role":"user","content":{user_prompt!r}}}],'
        f'"max_tokens":{max_tokens},'
        f'"temperature":{temperature}'
        '}'
    )
    json_payload = json_payload.replace("'", '"')

    cmd = [
        "curl",
        "-sS",
        "--fail-with-body",
        f"http://{host}:{port}/v1/chat/completions",
        "-H",
        "Content-Type: application/json",
        "-d",
        json_payload,
    ]
    return cmd, f"http://{host}:{port}/v1/chat/completions"


def run_serve(args: argparse.Namespace, cfg: dict) -> int:
    cmd, host, port = build_serve_command(args, cfg)
    print(f"[trtllm_runner] endpoint=http://{host}:{port}/v1")
    print(f"[trtllm_runner] exec: {shlex.join(cmd)}")
    os.execvp(cmd[0], cmd)
    return 0


def run_probe(args: argparse.Namespace, cfg: dict) -> int:
    cmd, endpoint = build_probe_command(args, cfg)
    print(f"[trtllm_runner] probe endpoint={endpoint}")
    print(f"[trtllm_runner] exec: {shlex.join(cmd)}")
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run trtllm-serve from YAML config")
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to YAML config (default: trtllm_config.yml)")

    sub = p.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run trtllm-serve serve")
    serve.add_argument("--mode", default="instruct", help="Mode key or alias (thinking, coding, instruct, reasoning)")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--backend")
    serve.add_argument("--log-level")
    serve.add_argument("--max-batch-size", type=int)
    serve.add_argument("--max-num-tokens", type=int)
    serve.add_argument("--max-seq-len", type=int)
    serve.add_argument("--kv-cache-free-gpu-memory-fraction", type=float)
    serve.add_argument("--reasoning-parser")
    serve.add_argument("--tool-parser")

    probe = sub.add_parser("probe", help="Send a chat/completions probe request")
    probe.add_argument("--host")
    probe.add_argument("--port", type=int)
    probe.add_argument("--prompt")
    probe.add_argument("--max-tokens", type=int)
    probe.add_argument("--temperature", type=float)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        cfg = load_config(Path(args.config).expanduser())
        if args.command == "serve":
            return run_serve(args, cfg)
        if args.command == "probe":
            return run_probe(args, cfg)
        parser.error(f"Unknown command: {args.command}")
        return 2
    except ConfigError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
