#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/trtllm_runner.py"

if [[ ! -f "$SCRIPT_DIR/trtllm_config.yml" ]]; then
  echo "ℹ️  No trtllm_config.yml found. Copying from trtllm_config.example.yml ..."
  cp "$SCRIPT_DIR/trtllm_config.example.yml" "$SCRIPT_DIR/trtllm_config.yml"
  echo "   Edit: $SCRIPT_DIR/trtllm_config.yml"
fi

MODE="instruct"
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-think|--instruct) MODE="instruct"; shift ;;
    --coding) MODE="coding"; shift ;;
    --thinking) MODE="thinking"; shift ;;
    --reasoning) MODE="reasoning"; shift ;;
    --mode)
      if [[ $# -lt 2 || -z "${2:-}" || "${2:-}" == --* ]]; then
        echo "❌ --mode requires a value (example: --mode reasoning_qwen3)" >&2
        exit 2
      fi
      MODE="$2"; shift 2 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done

PROFILE_ARGS=()
if [[ -n "${TRTLLM_PROFILE:-}" ]]; then
  PROFILE_ARGS+=(--profile "$TRTLLM_PROFILE")
fi

exec python3 "$RUNNER" --config "$SCRIPT_DIR/trtllm_config.yml" "${PROFILE_ARGS[@]}" serve --mode "$MODE" ${ARGS[@]+"${ARGS[@]}"}
