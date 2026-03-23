#!/usr/bin/env python3
"""
bench_api.py — Benchmark a running trtllm-serve endpoint.

Measures:
  - TTFT  (time to first token) — reflects prefill/input processing speed
  - Decode throughput (output tok/s) — reflects generation speed
  - Total latency

Usage:
  python3 bench_api.py [--url URL] [--model MODEL] [--max-tokens N] [--runs N]

Defaults connect to localhost:30000 with Qwen3-1.7B.
"""

import argparse
import json
import statistics
import time

import requests


def run_once(url: str, model: str, prompt: str, max_tokens: int) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "top_p": 0.8,
        "stream": True,
        # Disable thinking mode so all tokens go to content (not reasoning_content).
        # reasoning_parser: qwen3 splits <think> blocks into a separate field.
        "chat_template_kwargs": {"enable_thinking": False},
    }

    t0 = time.perf_counter()
    ttft = None
    tokens = 0
    full_text = ""

    with requests.post(url, json=payload, stream=True, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            if line == b"data: [DONE]":
                break
            raw = line
            if raw.startswith(b"data: "):
                raw = raw[6:]
            try:
                chunk = json.loads(raw)
            except json.JSONDecodeError:
                continue
            delta_obj = chunk["choices"][0]["delta"]
            # Count both content and reasoning_content (thinking mode splits them)
            delta = delta_obj.get("content") or delta_obj.get("reasoning_content") or ""
            if delta:
                if ttft is None:
                    ttft = time.perf_counter() - t0
                tokens += 1
                full_text += delta

    total = time.perf_counter() - t0
    decode_time = total - (ttft or 0)

    return {
        "ttft_ms": (ttft or 0) * 1000,
        "output_tokens": tokens,
        "decode_s": decode_time,
        "decode_tok_s": tokens / decode_time if decode_time > 0 else 0,
        "total_s": total,
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark trtllm-serve API")
    parser.add_argument("--url", default="http://localhost:30000/v1/chat/completions")
    parser.add_argument("--model", default="Qwen3-1.7B")
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--runs", type=int, default=3,
                        help="Number of runs to average (default: 3)")
    parser.add_argument("--prompt", default=(
        "Write a detailed explanation of quantum field theory in 600 words."
    ))
    args = parser.parse_args()

    print(f"Endpoint : {args.url}")
    print(f"Model    : {args.model}")
    print(f"Max tok  : {args.max_tokens}")
    print(f"Runs     : {args.runs}")
    print(f"Prompt   : {args.prompt[:80]}{'...' if len(args.prompt) > 80 else ''}")
    print()

    results = []
    for i in range(args.runs):
        print(f"Run {i+1}/{args.runs} ... ", end="", flush=True)
        r = run_once(args.url, args.model, args.prompt, args.max_tokens)
        results.append(r)
        print(f"TTFT={r['ttft_ms']:.0f}ms  "
              f"out={r['output_tokens']}tok  "
              f"decode={r['decode_tok_s']:.1f}tok/s  "
              f"total={r['total_s']:.2f}s")

    if args.runs > 1:
        print()
        print("── Summary ──────────────────────────────────")
        for key, label, fmt in [
            ("ttft_ms",      "TTFT (ms)",         ".0f"),
            ("output_tokens","Output tokens",      ".0f"),
            ("decode_tok_s", "Decode tok/s",       ".1f"),
            ("total_s",      "Total latency (s)",  ".2f"),
        ]:
            vals = [r[key] for r in results]
            print(f"  {label:<20} avg={statistics.mean(vals):{fmt}}  "
                  f"min={min(vals):{fmt}}  max={max(vals):{fmt}}")


if __name__ == "__main__":
    main()
