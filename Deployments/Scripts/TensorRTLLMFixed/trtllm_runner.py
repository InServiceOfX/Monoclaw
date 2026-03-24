#!/usr/bin/env python3
"""Config-driven wrapper for trtllm-serve."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from urllib import error, request

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


DEFAULT_CONFIG = Path(__file__).with_name("trtllm_config.yml")
EXAMPLE_CONFIG = Path(__file__).with_name("trtllm_config.example.yml")
PROFILES_DIR = Path(__file__).with_name("profiles")

MODE_ALIASES = {
    "thinking": "thinking_general",
    "coding": "thinking_coding",
    "instruct": "instruct_general",
    "no-think": "instruct_general",
    "reasoning": "reasoning_qwen3",
}


class ConfigError(RuntimeError):
    pass


def load_yaml_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a YAML mapping/object: {path}")
    return data


def deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def resolve_profile_path(profile: str) -> Path:
    raw = Path(profile).expanduser()
    candidates = []
    if raw.is_absolute() or raw.parent != Path("."):
        candidates.append(raw)
    else:
        candidates.extend([
            PROFILES_DIR / profile,
            PROFILES_DIR / f"{profile}.yml",
            PROFILES_DIR / f"{profile}.yaml",
        ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    tried = ", ".join(str(p) for p in candidates)
    raise ConfigError(f"Profile '{profile}' not found. Tried: {tried}")


def load_config(config_path: Path, profile: str | None = None) -> dict:
    if yaml is None:
        raise ConfigError("PyYAML is required. Install with: python3 -m pip install pyyaml")

    if not config_path.exists():
        raise ConfigError(
            f"Config not found: {config_path}\n"
            f"Copy {EXAMPLE_CONFIG.name} -> {DEFAULT_CONFIG.name} and edit it."
        )

    data = load_yaml_file(config_path)
    if profile:
        profile_path = resolve_profile_path(profile)
        profile_data = load_yaml_file(profile_path)
        data = deep_merge(data, profile_data)
        data.setdefault("_meta", {})["profile_path"] = str(profile_path)
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


def resolve_endpoint(args: argparse.Namespace, cfg: dict) -> tuple[str, int]:
    endpoint_cfg = cfg.get("endpoint", {}) or {}
    serve_cfg = cfg.get("serve", {}) or {}
    host = args.host if getattr(args, "host", None) is not None else endpoint_cfg.get("host") or serve_cfg.get("host", "127.0.0.1")
    port = int(args.port if getattr(args, "port", None) is not None else endpoint_cfg.get("port") or serve_cfg.get("port", 8000))
    return str(host), port


def resolve_model_name(cfg: dict) -> str:
    probe_cfg = cfg.get("probe", {}) or {}
    serve_cfg = cfg.get("serve", {}) or {}
    paths = cfg.get("paths", {}) or {}
    return str(probe_cfg.get("model_name") or serve_cfg.get("served_model_name") or Path(paths.get("model_path", "model")).name)


def build_chat_payload(cfg: dict, *, user_prompt: str, max_tokens: int | None = None, temperature: float | None = None, history: list[dict] | None = None, no_think: bool = False) -> dict:
    probe_cfg = cfg.get("probe", {}) or {}
    system_prompt = probe_cfg.get("system_prompt", "You are a helpful assistant.")
    payload = {
        "model": resolve_model_name(cfg),
        "messages": ([{"role": "system", "content": system_prompt}] + (history or []) + [{"role": "user", "content": user_prompt}]),
        "max_tokens": int(max_tokens if max_tokens is not None else probe_cfg.get("max_tokens", 32)),
        "temperature": temperature if temperature is not None else probe_cfg.get("temperature", 0),
    }
    if no_think:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    return payload


def http_json(method: str, url: str, payload: dict | None = None, timeout: float = 120.0) -> tuple[int, object]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else {"error": body}
        except Exception:
            parsed = {"error": body}
        return e.code, parsed


def build_probe_command(args: argparse.Namespace, cfg: dict) -> tuple[str, dict]:
    host, port = resolve_endpoint(args, cfg)
    user_prompt = args.prompt if args.prompt is not None else (cfg.get("probe", {}) or {}).get("prompt", "Where is New York?")
    payload = build_chat_payload(
        cfg,
        user_prompt=user_prompt,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    return f"http://{host}:{port}/v1/chat/completions", payload


def maybe_print_profile(cfg: dict) -> None:
    profile_path = ((cfg.get("_meta", {}) or {}).get("profile_path"))
    if profile_path:
        print(f"[trtllm_runner] profile={profile_path}")


def run_serve(args: argparse.Namespace, cfg: dict) -> int:
    cmd, host, port = build_serve_command(args, cfg)
    maybe_print_profile(cfg)
    print(f"[trtllm_runner] endpoint=http://{host}:{port}/v1")
    print(f"[trtllm_runner] exec: {shlex.join(cmd)}")
    os.execvp(cmd[0], cmd)
    return 0


def run_probe(args: argparse.Namespace, cfg: dict) -> int:
    endpoint, payload = build_probe_command(args, cfg)
    maybe_print_profile(cfg)
    print(f"[trtllm_runner] probe endpoint={endpoint}")
    print(f"[trtllm_runner] payload: {json.dumps(payload, ensure_ascii=False)}")
    status, body = http_json("POST", endpoint, payload)
    print(json.dumps(body, indent=2, ensure_ascii=False))
    return 0 if 200 <= status < 300 else 1


def run_health(args: argparse.Namespace, cfg: dict) -> int:
    host, port = resolve_endpoint(args, cfg)
    maybe_print_profile(cfg)
    url = f"http://{host}:{port}/health"
    status, body = http_json("GET", url, None, timeout=15.0)
    print(json.dumps(body, indent=2, ensure_ascii=False))
    return 0 if 200 <= status < 300 else 1


def run_models(args: argparse.Namespace, cfg: dict) -> int:
    host, port = resolve_endpoint(args, cfg)
    maybe_print_profile(cfg)
    url = f"http://{host}:{port}/v1/models"
    status, body = http_json("GET", url, None, timeout=15.0)
    print(json.dumps(body, indent=2, ensure_ascii=False))
    return 0 if 200 <= status < 300 else 1


def extract_assistant_text(body: object) -> str:
    if not isinstance(body, dict):
        return ""
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    text = first.get("text")
    if isinstance(text, str):
        return text
    return ""


def run_chat(args: argparse.Namespace, cfg: dict) -> int:
    host, port = resolve_endpoint(args, cfg)
    endpoint = f"http://{host}:{port}/v1/chat/completions"
    history_cfg = cfg.get("interactive", {}) or {}
    keep_history = bool(history_cfg.get("keep_history", True))
    default_max_tokens = int(history_cfg.get("max_tokens", (cfg.get("probe", {}) or {}).get("max_tokens", 128)))
    default_temperature = history_cfg.get("temperature", (cfg.get("probe", {}) or {}).get("temperature", 0.7))

    maybe_print_profile(cfg)
    print(f"[trtllm_runner] interactive chat -> {endpoint}")
    print("[trtllm_runner] Commands: /exit, /quit, /reset, /health, /models")

    history: list[dict] = []
    while True:
        try:
            prompt = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not prompt:
            continue
        if prompt in {"/exit", "/quit"}:
            return 0
        if prompt == "/reset":
            history = []
            print("[trtllm_runner] conversation reset")
            continue
        if prompt == "/health":
            status, body = http_json("GET", f"http://{host}:{port}/health", None, timeout=15.0)
            print(json.dumps(body, indent=2, ensure_ascii=False))
            if not (200 <= status < 300):
                print(f"[trtllm_runner] health check failed with status {status}", file=sys.stderr)
            continue
        if prompt == "/models":
            status, body = http_json("GET", f"http://{host}:{port}/v1/models", None, timeout=15.0)
            print(json.dumps(body, indent=2, ensure_ascii=False))
            if not (200 <= status < 300):
                print(f"[trtllm_runner] models query failed with status {status}", file=sys.stderr)
            continue

        payload = build_chat_payload(
            cfg,
            user_prompt=prompt,
            max_tokens=args.max_tokens if args.max_tokens is not None else default_max_tokens,
            temperature=args.temperature if args.temperature is not None else default_temperature,
            history=history if keep_history else [],
            no_think=getattr(args, "no_think", False),
        )
        try:
            status, body = http_json("POST", endpoint, payload)
        except Exception as exc:
            print(f"[trtllm_runner] request failed: {exc} — retry with /reset or retype your message", file=sys.stderr)
            continue
        if not (200 <= status < 300):
            print(json.dumps(body, indent=2, ensure_ascii=False), file=sys.stderr)
            continue

        reply = extract_assistant_text(body)
        print(f"model> {reply}")

        if keep_history:
            history.append({"role": "user", "content": prompt})
            history.append({"role": "assistant", "content": reply})



def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run trtllm-serve from YAML config")
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to YAML config (default: trtllm_config.yml)")
    p.add_argument("--profile", help="Named profile under profiles/ or explicit YAML path to merge over the base config")

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

    health = sub.add_parser("health", help="Check /health")
    health.add_argument("--host")
    health.add_argument("--port", type=int)

    models = sub.add_parser("models", help="Check /v1/models")
    models.add_argument("--host")
    models.add_argument("--port", type=int)

    chat = sub.add_parser("chat", help="Interactive terminal chat client against /v1/chat/completions")
    chat.add_argument("--host")
    chat.add_argument("--port", type=int)
    chat.add_argument("--max-tokens", type=int)
    chat.add_argument("--temperature", type=float)
    chat.add_argument("--no-think", action="store_true", default=False,
                      help="Disable thinking/reasoning mode (sets enable_thinking=false in chat_template_kwargs)")

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        cfg = load_config(Path(args.config).expanduser(), args.profile)
        if args.command == "serve":
            return run_serve(args, cfg)
        if args.command == "probe":
            return run_probe(args, cfg)
        if args.command == "health":
            return run_health(args, cfg)
        if args.command == "models":
            return run_models(args, cfg)
        if args.command == "chat":
            return run_chat(args, cfg)
        parser.error(f"Unknown command: {args.command}")
        return 2
    except ConfigError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
