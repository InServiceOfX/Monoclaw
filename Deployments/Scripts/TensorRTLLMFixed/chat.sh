#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/trtllm_runner.py"

if [[ ! -f "$SCRIPT_DIR/trtllm_config.yml" ]]; then
  echo "ℹ️  No trtllm_config.yml found. Copying from trtllm_config.example.yml ..."
  cp "$SCRIPT_DIR/trtllm_config.example.yml" "$SCRIPT_DIR/trtllm_config.yml"
  echo "   Edit: $SCRIPT_DIR/trtllm_config.yml"
fi

PROFILE_ARGS=()
if [[ -n "${TRTLLM_PROFILE:-}" ]]; then
  PROFILE_ARGS+=(--profile "$TRTLLM_PROFILE")
fi

exec python3 "$RUNNER" --config "$SCRIPT_DIR/trtllm_config.yml" "${PROFILE_ARGS[@]}" chat "$@"
