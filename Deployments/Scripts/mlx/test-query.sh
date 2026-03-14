#!/usr/bin/env bash
# =============================================================================
# test-query.sh — Smoke-test the running mlx_lm.server
#
# Fires a single chat completion request with the recommended sampling params
# for Qwen3.5-27B reasoning/thinking mode.
#
# Usage:
#   ./test-query.sh                              # default test prompt
#   ./test-query.sh "Explain entropy"            # custom prompt
#   ./test-query.sh "Write a sort in Python" --coding   # coding mode params
#   ./test-query.sh "Hello" --stream             # streaming
#   ./test-query.sh "Hello" --no-think           # instruct mode params
#   ./test-query.sh "Hello" --port 8090          # custom port
#   ./test-query.sh -h                           # show help
# =============================================================================

set -euo pipefail

HOST="localhost"
PORT="8080"
STREAM="false"
MODE="thinking"

# ── Default sampling: thinking mode ───────────────────────────────────────
TEMP="1.0"
TOP_P="0.95"
TOP_K="20"
MIN_P="0.0"
PRESENCE_PENALTY="1.5"
REPETITION_PENALTY="1.15"
REPETITION_CONTEXT_SIZE="64"
MAX_TOKENS="8192"

PROMPT="Explain the difference between entropy in thermodynamics and information theory. Think carefully."

# ── Arg parse ──────────────────────────────────────────────────────────────
show_help() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) show_help ;;
    --stream) STREAM="true"; shift ;;
    --no-think|--instruct)
      MODE="instruct"
      TEMP="0.7"
      TOP_P="0.8"
      TOP_K="20"
      MIN_P="0.0"
      PRESENCE_PENALTY="1.5"
      REPETITION_PENALTY="1.15"
      MAX_TOKENS="4096"
      shift
      ;;
    --coding)
      MODE="coding"
      TEMP="0.6"
      TOP_P="0.95"
      TOP_K="20"
      MIN_P="0.0"
      PRESENCE_PENALTY="0.0"
      REPETITION_PENALTY="1.15"
      MAX_TOKENS="8192"
      shift
      ;;
    --port) PORT="$2"; shift 2 ;;
    --max-tokens) MAX_TOKENS="$2"; shift 2 ;;
    -*) echo "Unknown option: $1" >&2; show_help ;;
    *)  PROMPT="$1"; shift ;;
  esac
done

ENDPOINT="http://$HOST:$PORT/v1/chat/completions"

# ── Check server is up ─────────────────────────────────────────────────────
if ! curl -sf "http://$HOST:$PORT/v1/models" -o /dev/null 2>&1; then
  echo "❌  Server not responding at http://$HOST:$PORT" >&2
  echo "   Start it with: ./serve.sh" >&2
  exit 1
fi

# ── Build JSON payload ─────────────────────────────────────────────────────
# repetition_penalty and repetition_context_size are per-request params.
# CRITICAL for 4-bit quantized reasoning models: without repetition_penalty=1.15
# the model can loop indefinitely once it hits a local probability minimum.

PAYLOAD=$(cat <<EOF
{
  "messages": [
    {
      "role": "user",
      "content": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$PROMPT")
    }
  ],
  "temperature": $TEMP,
  "top_p": $TOP_P,
  "top_k": $TOP_K,
  "min_p": $MIN_P,
  "presence_penalty": $PRESENCE_PENALTY,
  "repetition_penalty": $REPETITION_PENALTY,
  "repetition_context_size": $REPETITION_CONTEXT_SIZE,
  "max_tokens": $MAX_TOKENS,
  "stream": $STREAM
}
EOF
)

# ── Banner ─────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  → $ENDPOINT"
echo "  Mode: $MODE | stream=$STREAM | temp=$TEMP | top_p=$TOP_P | top_k=$TOP_K"
echo "  rep_penalty=$REPETITION_PENALTY | presence=$PRESENCE_PENALTY | max_tokens=$MAX_TOKENS"
echo "  Prompt: \"$PROMPT\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Fire request ──────────────────────────────────────────────────────────
if [[ "$STREAM" == "true" ]]; then
  # Streaming: print chunks as they arrive
  curl -s -N "$ENDPOINT" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" | \
  while IFS= read -r line; do
    if [[ "$line" == data:* ]]; then
      data="${line#data: }"
      if [[ "$data" == "[DONE]" ]]; then
        echo ""
        echo ""
        echo "━━ [DONE] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        break
      fi
      # Extract content delta
      content=$(echo "$data" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    delta = d.get('choices', [{}])[0].get('delta', {})
    print(delta.get('content', ''), end='', flush=True)
except:
    pass
" 2>/dev/null || true)
      printf "%s" "$content"
    fi
  done
else
  # Non-streaming: pretty print
  RESPONSE=$(curl -s "$ENDPOINT" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

  echo "$RESPONSE" | python3 -c "
import sys, json

try:
    d = json.load(sys.stdin)

    # Check for error
    if 'error' in d:
        print('❌ Server error:', d['error'])
        sys.exit(1)

    choice = d.get('choices', [{}])[0]
    content = choice.get('message', {}).get('content', '(no content)')
    finish = choice.get('finish_reason', '?')
    usage = d.get('usage', {})

    print(content)
    print()
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    print(f'finish_reason: {finish}  |  prompt_tokens: {usage.get(\"prompt_tokens\",\"?\")}'
          f'  |  completion_tokens: {usage.get(\"completion_tokens\",\"?\")}')
except json.JSONDecodeError:
    print('❌ Could not parse response:')
    print(sys.stdin.read())
" <<< "$RESPONSE"
fi
