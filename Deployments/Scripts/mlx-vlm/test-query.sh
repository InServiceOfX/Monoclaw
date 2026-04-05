#!/usr/bin/env bash
# =============================================================================
# test-query.sh — Smoke-test mlx_vlm.server using YAML-configured defaults
#
# Usage:
#   ./test-query.sh
#   ./test-query.sh "Describe this image request path"
#   ./test-query.sh --port 8091
#   ./test-query.sh --config /path/to/mlx_vlm_config.yml
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/mlx_vlm_config.yml"
EXAMPLE_CONFIG="$SCRIPT_DIR/mlx_vlm_config.example.yml"

if [[ ! -f "$CONFIG" ]]; then
  echo "ℹ️  No mlx_vlm_config.yml found. Copying from mlx_vlm_config.example.yml ..."
  cp "$EXAMPLE_CONFIG" "$CONFIG"
  echo "   Edit: $CONFIG"
fi

HOST_OVERRIDE=""
PORT_OVERRIDE=""
PROMPT="Describe your capabilities and expected multimodal request format."

show_help() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) show_help ;;
    --config) CONFIG="$2"; shift 2 ;;
    --host) HOST_OVERRIDE="$2"; shift 2 ;;
    --port) PORT_OVERRIDE="$2"; shift 2 ;;
    -*) echo "Unknown option: $1" >&2; show_help ;;
    *) PROMPT="$1"; shift ;;
  esac
done

readarray -t CFG_LINES < <(python3 - "$CONFIG" "$HOST_OVERRIDE" "$PORT_OVERRIDE" <<'PY'
import sys
from pathlib import Path

try:
    import yaml
except Exception:
    print("ERR:PyYAML is required. Install with: python3 -m pip install pyyaml")
    sys.exit(2)

config_path = Path(sys.argv[1]).expanduser()
host_override = sys.argv[2]
port_override = sys.argv[3]

if not config_path.exists():
    print(f"ERR:Config not found: {config_path}")
    sys.exit(2)

with config_path.open("r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}

serve = cfg.get("serve", {}) or {}
host = host_override or str(serve.get("host", "127.0.0.1"))
port = int(port_override or serve.get("port", 8081))
print(host)
print(port)
PY
)

if [[ "${CFG_LINES[0]:-}" == ERR:* ]]; then
  echo "❌ ${CFG_LINES[0]#ERR:}" >&2
  exit 1
fi

HOST="${CFG_LINES[0]}"
PORT="${CFG_LINES[1]}"
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
  "max_tokens": 512,
  "stream": false
}
EOF
)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  → $ENDPOINT"
echo "  Prompt: \"$PROMPT\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

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
    print(f"finish_reason: {finish}  |  prompt_tokens: {usage.get('prompt_tokens','?')}  |  completion_tokens: {usage.get('completion_tokens','?')}")
except json.JSONDecodeError:
    print("❌ Could not parse response:")
    print(sys.stdin.read())
'
