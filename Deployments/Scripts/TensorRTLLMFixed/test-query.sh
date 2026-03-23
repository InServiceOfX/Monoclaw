#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/trtllm_runner.py"

if [[ ! -f "$SCRIPT_DIR/trtllm_config.yml" ]]; then
  echo "❌ Missing $SCRIPT_DIR/trtllm_config.yml" >&2
  echo "   Copy trtllm_config.example.yml to trtllm_config.yml and edit it first." >&2
  exit 1
fi

PROFILE_ARGS=()
if [[ -n "${TRTLLM_PROFILE:-}" ]]; then
  PROFILE_ARGS+=(--profile "$TRTLLM_PROFILE")
fi

exec python3 "$RUNNER" --config "$SCRIPT_DIR/trtllm_config.yml" "${PROFILE_ARGS[@]}" probe "$@"
