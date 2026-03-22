#!/usr/bin/env python3
"""Interactive chat client for a running SGLang server.

Usage:
    python3 sglang_chat.py [--profile longctx] [--mode thinking] [--no-think]
    ./chat.sh [--no-think] [--mode instruct]

Reads server config from sglang_configs/<profile>.yaml (host/port/model-path).
Sends requests to http://host:port/v1/chat/completions (OpenAI-compatible API).
Maintains conversation history for multi-turn chat.

Commands (type at the prompt):
    /clear     — clear conversation history (keep system prompt)
    /reset     — alias for /clear
    /history   — print current conversation turns
    /mode <m>  — switch mode (thinking/instruct/coding)
    /system <text> — set a new system prompt
    /quit, /exit, exit, quit — exit
    Ctrl-C / Ctrl-D — exit
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

# ── default generation params per mode ───────────────────────────────────────
MODE_DEFAULTS: dict[str, dict] = {
    "thinking": {
        "temperature": 1.0,
        "top_p": 0.95,
        "max_tokens": 8192,
        "system": "You are a helpful, thoughtful assistant. Think carefully before answering.",
    },
    "instruct": {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 4096,
        "system": "You are a helpful assistant.",
    },
    "coding": {
        "temperature": 0.6,
        "top_p": 0.95,
        "max_tokens": 8192,
        "system": "You are an expert programmer. Be precise and correct.",
    },
}

MODE_ALIASES = {
    "think": "thinking",
    "no-think": "instruct",
    "nothink": "instruct",
    "code": "coding",
}


def resolve_mode(mode: str) -> str:
    return MODE_ALIASES.get(mode.lower(), mode.lower())


def load_yaml_config(config_path: Path) -> dict:
    if yaml is None:
        print("Warning: PyYAML not installed, cannot read yaml config. Using defaults.")
        return {}
    if not config_path.exists():
        print(f"Warning: config not found: {config_path}. Using defaults.")
        return {}
    with config_path.open() as f:
        return yaml.safe_load(f) or {}


def get_server_url(cfg: dict) -> str:
    host = cfg.get("host", "localhost")
    port = cfg.get("port", 30000)
    # SGLang uses 0.0.0.0 as bind address — connect to localhost
    if host in ("0.0.0.0", ""):
        host = "localhost"
    return f"http://{host}:{port}"


def check_server(base_url: str) -> str | None:
    """Returns 'ready' if TCP port is open, None otherwise.
    Skips HTTP requests — those hang while Triton JIT compiles on startup.
    """
    import socket
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 30000
    try:
        with socket.create_connection((host, port), timeout=5):
            return "Qwen3.5-9B-AWQ"
    except Exception:
        return None


def chat_completion(
    base_url: str,
    messages: list[dict],
    mode_cfg: dict,
    stream: bool = True,
) -> str:
    payload = {
        "model": "default",
        "messages": messages,
        "temperature": mode_cfg.get("temperature", 0.7),
        "top_p": mode_cfg.get("top_p", 0.9),
        "max_tokens": mode_cfg.get("max_tokens", 4096),
        "stream": stream,
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    full_text = ""
    thinking_text = ""
    in_thinking = False

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            if stream:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        obj = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    delta = obj.get("choices", [{}])[0].get("delta", {})

                    # Handle reasoning_content (thinking) separately
                    thinking_delta = delta.get("reasoning_content") or ""
                    content_delta = delta.get("content") or ""

                    if thinking_delta:
                        if not in_thinking:
                            print("\033[2m<thinking>\033[0m", flush=True)
                            in_thinking = True
                        print(f"\033[2m{thinking_delta}\033[0m", end="", flush=True)
                        thinking_text += thinking_delta

                    if content_delta:
                        if in_thinking:
                            print("\n\033[2m</thinking>\033[0m\n", flush=True)
                            in_thinking = False
                        print(content_delta, end="", flush=True)
                        full_text += content_delta

                if in_thinking:
                    print("\n\033[2m</thinking>\033[0m", flush=True)
                print()  # newline after response
            else:
                obj = json.loads(resp.read())
                msg = obj["choices"][0]["message"]
                thinking_text = msg.get("reasoning_content") or ""
                full_text = msg.get("content") or ""
                if thinking_text:
                    print(f"\033[2m<thinking>\n{thinking_text}\n</thinking>\033[0m\n")
                print(full_text)

    except (urllib.error.URLError, ConnectionResetError, BrokenPipeError) as e:
        if full_text:
            # Partial response received before connection dropped — still usable
            print(f"\n\033[33m[connection dropped, partial response]\033[0m")
        else:
            print(f"\n\033[31mRequest failed: {e}\033[0m")
        return full_text

    return full_text


def print_help() -> None:
    print("""
Commands:
  /clear, /reset     — clear conversation history
  /history           — show current conversation
  /mode <name>       — switch mode (thinking / instruct / coding)
  /system <text>     — set system prompt
  /no-think          — switch to instruct (no thinking) mode
  /think             — switch to thinking mode
  /quit, /exit       — exit
""")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive SGLang chat client")
    parser.add_argument(
        "--profile", default="longctx",
        help="Config profile name (default: longctx). Reads sglang_configs/<profile>.yaml"
    )
    parser.add_argument(
        "--mode", default="thinking",
        help="Generation mode: thinking (default), instruct, coding"
    )
    parser.add_argument(
        "--no-think", dest="no_think", action="store_true",
        help="Shortcut for --mode instruct"
    )
    parser.add_argument(
        "--url", default=None,
        help="Override server URL (e.g. http://localhost:30000)"
    )
    parser.add_argument(
        "--config-dir", default=None,
        help="Directory containing sglang_configs/ (defaults to script dir)"
    )
    args = parser.parse_args()

    # Resolve config dir
    script_dir = Path(__file__).parent
    config_dir = Path(args.config_dir) if args.config_dir else script_dir
    config_path = config_dir / "sglang_configs" / f"qwen35_9b_awq_{args.profile}.yaml"

    # Load yaml config for host/port
    cfg = load_yaml_config(config_path)

    # Server URL
    base_url = args.url or get_server_url(cfg)

    # Check server
    print(f"\033[36mConnecting to SGLang server at {base_url} ...\033[0m")
    model_name = check_server(base_url)
    if model_name is None:
        print(f"\033[31mServer not reachable at {base_url}\033[0m")
        print("Is the server running? Start it with: ./launch.sh longctx")
        sys.exit(1)
    print(f"\033[32mConnected! Model: {model_name}\033[0m")

    # Resolve mode
    mode_name = resolve_mode("instruct" if args.no_think else args.mode)
    if mode_name not in MODE_DEFAULTS:
        print(f"Unknown mode '{mode_name}'. Using 'thinking'.")
        mode_name = "thinking"
    mode_cfg = dict(MODE_DEFAULTS[mode_name])

    # Conversation history
    messages: list[dict] = []
    system_prompt = mode_cfg.get("system", "")
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    print(f"\033[33mMode: {mode_name} | /help for commands | Ctrl-C to exit\033[0m\n")

    while True:
        try:
            user_input = input("\033[1mYou:\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue

        # Commands
        if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
            print("Bye.")
            break

        if user_input.lower() in ("/help", "/?"):
            print_help()
            continue

        if user_input.lower() in ("/clear", "/reset"):
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            print("\033[33m[History cleared]\033[0m")
            continue

        if user_input.lower() == "/history":
            for i, m in enumerate(messages):
                role = m["role"].upper()
                content = m["content"][:200] + ("…" if len(m["content"]) > 200 else "")
                print(f"  [{i}] {role}: {content}")
            continue

        if user_input.lower() in ("/no-think", "/nothink"):
            mode_name = "instruct"
            mode_cfg = dict(MODE_DEFAULTS["instruct"])
            print(f"\033[33m[Switched to instruct mode]\033[0m")
            continue

        if user_input.lower() in ("/think", "/thinking"):
            mode_name = "thinking"
            mode_cfg = dict(MODE_DEFAULTS["thinking"])
            print(f"\033[33m[Switched to thinking mode]\033[0m")
            continue

        if user_input.lower().startswith("/mode "):
            new_mode = resolve_mode(user_input[6:].strip())
            if new_mode in MODE_DEFAULTS:
                mode_name = new_mode
                mode_cfg = dict(MODE_DEFAULTS[mode_name])
                print(f"\033[33m[Switched to {mode_name} mode]\033[0m")
            else:
                print(f"Unknown mode. Available: {', '.join(MODE_DEFAULTS)}")
            continue

        if user_input.lower().startswith("/system "):
            system_prompt = user_input[8:].strip()
            # Update or insert system message
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] = system_prompt
            else:
                messages.insert(0, {"role": "system", "content": system_prompt})
            print(f"\033[33m[System prompt updated]\033[0m")
            continue

        # Regular message
        messages.append({"role": "user", "content": user_input})

        print("\033[1mAssistant:\033[0m ", end="", flush=True)
        response = chat_completion(base_url, messages, mode_cfg, stream=False)

        if response:
            messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
