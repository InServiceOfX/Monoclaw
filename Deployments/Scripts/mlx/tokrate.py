#!/usr/bin/env python3
"""
tokrate.py — Live tokens/sec monitor for mlx_lm.server
Usage: python3 tokrate.py [prompt]
       python3 tokrate.py --host 127.0.0.1 --port 8080 "your prompt here"
"""

import argparse
import json
import sys
import time
import urllib.request

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_MODEL = "mlx-community/Qwen3.5-27B-Claude-4.6-Opus-Distilled-MLX-6bit"
DEFAULT_PROMPT = "Explain the theory of general relativity in a few sentences."
DEFAULT_MAX_TOKENS = 200


def stream_completion(host, port, model, prompt, max_tokens):
    url = f"http://{host}:{port}/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    token_count = 0
    char_buf = ""
    start_time = None
    ttft = None

    print(f"\n🤖 Model : {model}")
    print(f"💬 Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    print(f"{'─' * 60}")
    print("📝 Output:\n")

    with urllib.request.urlopen(req) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break

            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            delta = chunk.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content", "") or ""
            reasoning = delta.get("reasoning", "") or ""
            token_text = reasoning or content
            if not token_text:
                continue

            now = time.perf_counter()
            if start_time is None:
                start_time = now
                ttft = now  # will subtract request start below

            is_thinking = bool(reasoning and not content)
            token_count += 1
            char_buf += token_text
            prefix = "\033[2m[think] \033[0m" if is_thinking and token_count == 1 else ""
            sys.stdout.write(prefix + token_text)
            sys.stdout.flush()

            elapsed = now - start_time
            tok_per_sec = token_count / elapsed if elapsed > 0 else 0
            status = f"  [{token_count} tok | {tok_per_sec:.1f} tok/s]"
            # Overwrite status line in terminal
            sys.stdout.write(f"\r\033[K{status}")
            sys.stdout.write(f"\033[{len(status)}D")  # move cursor back
            sys.stdout.flush()

    end_time = time.perf_counter()
    total_elapsed = (end_time - start_time) if start_time else 0
    avg_tps = token_count / total_elapsed if total_elapsed > 0 else 0

    # Print final output cleanly
    print(f"\n\n{'─' * 60}")
    print(f"✅ Done!")
    print(f"   Tokens generated : {token_count}")
    print(f"   Total time        : {total_elapsed:.2f}s")
    print(f"   Avg tok/s         : {avg_tps:.1f}")
    if ttft and start_time:
        print(f"   Time to 1st token : ~real-time (streaming)")
    print(f"{'─' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="Live tok/s monitor for mlx_lm.server")
    parser.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT, help="Prompt to send")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    args = parser.parse_args()

    try:
        stream_completion(args.host, args.port, args.model, args.prompt, args.max_tokens)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted.")
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
