#!/usr/bin/env bash
# =============================================================================
# chat.sh — Interactive chat with Qwen3.5-27B-Claude-4.6-Opus-Distilled (4bit)
#
# Uses mlx_lm.chat from the openclaw .venv.
# Context is preserved for the lifetime of the REPL session.
#
# Usage:
#   ./chat.sh                  # thinking mode (default)
#   ./chat.sh --no-think       # instruct/non-thinking mode
#   ./chat.sh --coding         # coding precision mode (lower temp)
#   ./chat.sh --system "..."   # custom system prompt
#   ./chat.sh -h               # show this help
#
# mlx_lm.chat does not expose all sampler flags directly.
# Key flags available: --temp, --top-p, --max-tokens, --system-prompt,
#                      --max-kv-size, --seed
# repetition_penalty is only available in mlx_lm.generate / mlx_lm.server.
# For full sampler control (repetition_penalty etc.), use serve.sh + curl.
# =============================================================================

set -eo pipefail

# ── Paths ──────────────────────────────────────────────────────────────────
VENV_BIN="/Users/ernestyeung/Prop/openclaw/.venv/bin"
MLX_CHAT="$VENV_BIN/mlx_lm.chat"
MODEL_PATH="/Users/ernestyeung/.cache/huggingface/hub/models--mlx-community--Qwen3.5-27B-Claude-4.6-Opus-Distilled-MLX-4bit/snapshots/5f690e9b35c3ebdb7563cdeef0485cefaa2dde62"

# ── Defaults (thinking mode) ───────────────────────────────────────────────
TEMP="1.0"
TOP_P="0.95"
MAX_TOKENS="8192"
MAX_KV_SIZE="32768"  # full context window

# Default system prompt — encourages the model to think before answering
SYSTEM_PROMPT="You are a helpful, thoughtful assistant. Think step by step before answering."

MODE="thinking"

# ── Arg parse ──────────────────────────────────────────────────────────────
EXTRA_ARGS=()  # optional extra flags (e.g. --seed N)

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
      MAX_TOKENS="4096"
      SYSTEM_PROMPT="You are a helpful assistant."
      shift
      ;;
    --coding)
      MODE="coding"
      TEMP="0.6"
      TOP_P="0.95"
      MAX_TOKENS="8192"
      SYSTEM_PROMPT="You are an expert programmer. Be precise and correct."
      shift
      ;;
    --system)
      SYSTEM_PROMPT="$2"
      shift 2
      ;;
    --max-tokens)
      MAX_TOKENS="$2"
      shift 2
      ;;
    --seed)
      EXTRA_ARGS+=("--seed" "$2")
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_help
      ;;
  esac
done

# ── Validate ──────────────────────────────────────────────────────────────
if [[ ! -x "$MLX_CHAT" ]]; then
  echo "❌  mlx_lm.chat not found at: $MLX_CHAT" >&2
  echo "   Make sure the openclaw .venv is set up correctly." >&2
  exit 1
fi

if [[ ! -d "$MODEL_PATH" ]]; then
  echo "❌  Model not found at: $MODEL_PATH" >&2
  exit 1
fi

# ── Banner ─────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Qwen3.5-27B-Claude-4.6-Opus-Distilled (MLX 4bit)               ║"
echo "║  Mode: $MODE"
printf "║  temp=%-5s  top_p=%-4s  max_tokens=%-6s                       ║\n" "$TEMP" "$TOP_P" "$MAX_TOKENS"
echo "║  Type your message and press Enter. Ctrl+C or /quit to exit.     ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# ── Launch ─────────────────────────────────────────────────────────────────
# NOTE: mlx_lm.chat note on repetition_penalty:
# The chat CLI does not expose --repetition-penalty directly.
# The serve.sh + test-query.sh path supports it fully.
# For the REPL, we compensate with a higher min-p via top-p and seed stability.

exec "$MLX_CHAT" \
  --model "$MODEL_PATH" \
  --temp "$TEMP" \
  --top-p "$TOP_P" \
  --max-tokens "$MAX_TOKENS" \
  --max-kv-size "$MAX_KV_SIZE" \
  --system-prompt "$SYSTEM_PROMPT" \
  ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
