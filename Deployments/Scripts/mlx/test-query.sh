#!/usr/bin/env bash
# =============================================================================
# test-query.sh — Smoke-test mlx_lm.server using YAML-configured defaults
#
# Reads mode defaults + host/port from mlx_config.yml so sampling params are
# centralized in one place.
#
# Usage:
#   ./test-query.sh                              # thinking mode
#   ./test-query.sh "Explain entropy"            # custom prompt
#   ./test-query.sh --coding                     # thinking_coding mode
#   ./test-query.sh --instruct                   # instruct_general mode
#   ./test-query.sh --reasoning                  # instruct_reasoning mode
#   ./test-query.sh --mode custom_mode_key       # any modes.<key> from YAML
#   ./test-query.sh --stream                     # SSE streaming
#   ./test-query.sh --port 8090                  # override port
#   ./test-query.sh --config /path/to/mlx.yml    # custom config path
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/mlx_config.yml"
EXAMPLE_CONFIG="$SCRIPT_DIR/mlx_config.example.yml"

if [[ ! -f "$CONFIG" ]]; then
  echo "ℹ️  No mlx_config.yml found. Copying from mlx_config.example.yml ..."
  cp "$EXAMPLE_CONFIG" "$CONFIG"
  echo "   Edit: $CONFIG"
fi

MODE="thinking"
STREAM="false"
HOST_OVERRIDE=""
PORT_OVERRIDE=""
MAX_TOKENS_OVERRIDE=""
PROMPT="Explain the difference between entropy in thermodynamics and information theory. Think carefully."

show_help() {
  sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) show_help ;;
    --config) CONFIG="$2"; shift 2 ;;
    --stream) STREAM="true"; shift ;;
    --coding) MODE="coding"; shift ;;
    --instruct|--no-think) MODE="instruct"; shift ;;
    --reasoning) MODE="reasoning"; shift ;;
    --mode)
      if [[ $# -lt 2 || -z "${2:-}" || "${2:-}" == --* ]]; then
        echo "❌ --mode requires a value (example: --mode instruct_reasoning)" >&2
        exit 2
      fi
      MODE="$2"; shift 2 ;;

    --host) HOST_OVERRIDE="$2"; shift 2 ;;
    --port) PORT_OVERRIDE="$2"; shift 2 ;;
    --max-tokens) MAX_TOKENS_OVERRIDE="$2"; shift 2 ;;
    -*) echo "Unknown option: $1" >&2; show_help ;;
    *) PROMPT="$1"; shift ;;
  esac
done

# Read resolved config values from YAML via Python.
# Output format: HOST PORT TEMP TOP_P TOP_K MIN_P PRESENCE REPETITION MAX_TOKENS ENABLE_THINKING
readarray -t CFG_LINES < <(python3 - "$CONFIG" "$MODE" "$HOST_OVERRIDE" "$PORT_OVERRIDE" "$MAX_TOKENS_OVERRIDE" <<'PY'
import sys
from pathlib import Path

try:
    import yaml
except Exception:
    print("ERR:PyYAML is required. Install with: python3 -m pip install pyyaml")
    sys.exit(2)

config_path = Path(sys.argv[1]).expanduser()
mode_in = sys.argv[2]
host_override = sys.argv[3]
port_override = sys.argv[4]
max_tokens_override = sys.argv[5]

if not config_path.exists():
    print(f"ERR:Config not found: {config_path}")
    sys.exit(2)

with config_path.open("r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}

aliases = {
    "thinking": "thinking_general",
    "coding": "thinking_coding",
    "instruct": "instruct_general",
    "no-think": "instruct_general",
    "reasoning": "instruct_reasoning",
}

mode_key = aliases.get(mode_in, mode_in)
modes = cfg.get("modes", {})
if mode_key not in modes:
    print(f"ERR:Unknown mode '{mode_key}'. Available: {', '.join(sorted(modes.keys()))}")
    sys.exit(2)

mode = modes.get(mode_key, {}) or {}
serve = cfg.get("serve", {}) or {}

host = host_override or str(serve.get("host", "127.0.0.1"))
port = int(port_override or serve.get("port", 8080))

temp = float(mode.get("temperature", 1.0))
top_p = float(mode.get("top_p", 0.95))
top_k = int(mode.get("top_k", 20))
min_p = float(mode.get("min_p", 0.0))
presence_penalty = float(mode.get("presence_penalty", 0.0))
repetition_penalty = float(mode.get("repetition_penalty", 1.0))
max_tokens = int(max_tokens_override or mode.get("max_tokens", 8192))
if max_tokens < 4096:
    max_tokens = 4096

enable_thinking = bool(mode.get("enable_thinking", True))

print(host)
print(port)
print(temp)
print(top_p)
print(top_k)
print(min_p)
print(presence_penalty)
print(repetition_penalty)
print(max_tokens)
print("true" if enable_thinking else "false")
print(mode_key)
PY
)

if [[ "${CFG_LINES[0]:-}" == ERR:* ]]; then
  echo "❌ ${CFG_LINES[0]#ERR:}" >&2
  exit 1
fi

HOST="${CFG_LINES[0]}"
PORT="${CFG_LINES[1]}"
TEMP="${CFG_LINES[2]}"
TOP_P="${CFG_LINES[3]}"
TOP_K="${CFG_LINES[4]}"
MIN_P="${CFG_LINES[5]}"
PRESENCE_PENALTY="${CFG_LINES[6]}"
REPETITION_PENALTY="${CFG_LINES[7]}"
MAX_TOKENS="${CFG_LINES[8]}"
ENABLE_THINKING="${CFG_LINES[9]}"
RESOLVED_MODE="${CFG_LINES[10]}"

REPETITION_CONTEXT_SIZE="64"
ENDPOINT="http://$HOST:$PORT/v1/chat/completions"

if ! curl -sf "http://$HOST:$PORT/v1/models" -o /dev/null 2>&1; then
  echo "❌  Server not responding at http://$HOST:$PORT" >&2
  echo "   Start it with: ./serve.sh" >&2
  exit 1
fi

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

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  → $ENDPOINT"
echo "  Mode: $RESOLVED_MODE (enable_thinking=$ENABLE_THINKING) | stream=$STREAM"
echo "  temp=$TEMP | top_p=$TOP_P | top_k=$TOP_K | min_p=$MIN_P"
echo "  presence=$PRESENCE_PENALTY | rep_penalty=$REPETITION_PENALTY | max_tokens=$MAX_TOKENS"
echo "  Prompt: \"$PROMPT\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ "$STREAM" == "true" ]]; then
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
      content=$(echo "$data" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    delta = d.get("choices", [{}])[0].get("delta", {})
    print(delta.get("content", ""), end="", flush=True)
except:
    pass
' 2>/dev/null || true)
      printf "%s" "$content"
    fi
  done
else
  RESPONSE=$(curl -s "$ENDPOINT" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

  echo "$RESPONSE" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    if "error" in d:
        print("❌ Server error:", d["error"])
        sys.exit(1)
    choice = d.get("choices", [{}])[0]
    content = choice.get("message", {}).get("content", "(no content)")
    finish = choice.get("finish_reason", "?")
    usage = d.get("usage", {})
    print(content)
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"finish_reason: {finish}  |  prompt_tokens: {usage.get('"'"'prompt_tokens'"'"','"'"'?'"'"')}  |  completion_tokens: {usage.get('"'"'completion_tokens'"'"','"'"'?'"'"')}")
except json.JSONDecodeError:
    print("❌ Could not parse response:")
    print(sys.stdin.read())
'
fi
