#!/usr/bin/env bash
# =============================================================================
# serve.sh — OpenAI-compatible HTTP server for Qwen3.5-27B local inference
#
# Starts mlx_lm.server on localhost:8080 (default).
# Exposes /v1/chat/completions, /v1/models — OpenAI API compatible.
#
# Usage:
#   ./serve.sh                    # thinking mode defaults (temp 1.0)
#   ./serve.sh --no-think         # instruct mode defaults (temp 0.7)
#   ./serve.sh --coding           # coding precision defaults (temp 0.6)
#   ./serve.sh --port 8090        # custom port
#   ./serve.sh --host 0.0.0.0     # expose on LAN (be careful!)
#   ./serve.sh --log-level DEBUG  # verbose logging
#   ./serve.sh -h                 # show help
#
# After starting, test with:
#   ./test-query.sh
#   curl localhost:8080/v1/models
#
# NOTE: mlx_lm.server sets DEFAULT sampling params that clients can override
# per-request. The values here are server-side defaults only.
# repetition_penalty is set per-request (not a server default flag) — see
# test-query.sh for the recommended per-request payload.
# =============================================================================

set -euo pipefail

# ── Paths ──────────────────────────────────────────────────────────────────
VENV_BIN="/Users/ernestyeung/Prop/openclaw/.venv/bin"
MLX_SERVER="$VENV_BIN/mlx_lm.server"
MODEL_PATH="/Users/ernestyeung/.cache/huggingface/hub/models--mlx-community--Qwen3.5-27B-Claude-4.6-Opus-Distilled-MLX-4bit/snapshots/5f690e9b35c3ebdb7563cdeef0485cefaa2dde62"

# ── Defaults ───────────────────────────────────────────────────────────────
HOST="127.0.0.1"
PORT="8080"
LOG_LEVEL="INFO"
MAX_TOKENS="8192"
MODE="thinking"

# Thinking mode defaults (Qwen3.5 official recommendation)
TEMP="1.0"
TOP_P="0.95"
TOP_K="20"
MIN_P="0.0"

# Concurrency (Apple Silicon — single process, tune as needed)
DECODE_CONCURRENCY="1"
PROMPT_CONCURRENCY="1"

# ── Arg parse ──────────────────────────────────────────────────────────────
show_help() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_help
      ;;
    --no-think|--instruct)
      MODE="instruct"
      TEMP="0.7"
      TOP_P="0.8"
      TOP_K="20"
      MIN_P="0.0"
      MAX_TOKENS="4096"
      shift
      ;;
    --coding)
      MODE="coding"
      TEMP="0.6"
      TOP_P="0.95"
      TOP_K="20"
      MIN_P="0.0"
      MAX_TOKENS="8192"
      shift
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --log-level)
      LOG_LEVEL="$2"
      shift 2
      ;;
    --max-tokens)
      MAX_TOKENS="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_help
      ;;
  esac
done

# ── Validate ──────────────────────────────────────────────────────────────
if [[ ! -x "$MLX_SERVER" ]]; then
  echo "❌  mlx_lm.server not found at: $MLX_SERVER" >&2
  echo "   Make sure the openclaw .venv is set up correctly." >&2
  exit 1
fi

if [[ ! -d "$MODEL_PATH" ]]; then
  echo "❌  Model not found at: $MODEL_PATH" >&2
  exit 1
fi

# Check if port is already in use
if lsof -iTCP:"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "⚠️   Port $PORT is already in use." >&2
  EXISTING_PID=$(lsof -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -1)
  echo "   Existing process PID: $EXISTING_PID" >&2
  echo "   Kill it with: kill $EXISTING_PID" >&2
  echo "   Or use: ./serve.sh --port 8090" >&2
  exit 1
fi

# ── Banner ─────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  MLX LM Server — Qwen3.5-27B-Claude-4.6-Opus-Distilled (4bit)  ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
printf "║  Mode:         %-50s ║\n" "$MODE"
printf "║  Endpoint:     http://%-45s ║\n" "$HOST:$PORT/v1"
printf "║  temp=%-5s  top_p=%-4s  top_k=%-4s  max_tokens=%-6s         ║\n" "$TEMP" "$TOP_P" "$TOP_K" "$MAX_TOKENS"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  ⚠️  repetition_penalty=1.15 must be set PER REQUEST            ║"
echo "║     (not a server-level flag). See test-query.sh for examples.  ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Test:  ./test-query.sh                                         ║"
echo "║  Kill:  Ctrl+C                                                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Starting server... (model load may take 30–60s on first inference)"
echo ""

# ── Launch ─────────────────────────────────────────────────────────────────
# Notes on flags:
# --temp / --top-p / --top-k / --min-p: server-side defaults (overridable per request)
# --max-tokens: default token budget; ALWAYS override to >=4096 per request for this model
# --chat-template-args: passes enable_thinking=true to the Qwen3.5 chat template
#   This is the proper way to activate thinking mode on Qwen3.5 with mlx-lm
# --decode-concurrency 1: safe default for single-user local use on Apple Silicon
# --allowed-origins '*': enables OpenClaw / local browser clients

exec "$MLX_SERVER" \
  --model "$MODEL_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  --temp "$TEMP" \
  --top-p "$TOP_P" \
  --top-k "$TOP_K" \
  --min-p "$MIN_P" \
  --max-tokens "$MAX_TOKENS" \
  --chat-template-args "{\"enable_thinking\":true}" \
  --allowed-origins '*' \
  --decode-concurrency "$DECODE_CONCURRENCY" \
  --prompt-concurrency "$PROMPT_CONCURRENCY" \
  --log-level "$LOG_LEVEL"
