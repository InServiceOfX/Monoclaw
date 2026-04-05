#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/mlx_vlm_runner.py"

if [[ ! -f "$SCRIPT_DIR/mlx_vlm_config.yml" ]]; then
  echo "ℹ️  No mlx_vlm_config.yml found. Copying from mlx_vlm_config.example.yml ..."
  cp "$SCRIPT_DIR/mlx_vlm_config.example.yml" "$SCRIPT_DIR/mlx_vlm_config.yml"
  echo "   Edit: $SCRIPT_DIR/mlx_vlm_config.yml"
fi

CONFIG_OVERRIDE=""
if [[ ${1:-} == "--profile" || ${1:-} == "-p" ]]; then
  if [[ $# -lt 2 || -z "${2:-}" ]]; then
    echo "❌ --profile requires a value" >&2
    exit 2
  fi
  PROFILE_NAME="$2"
  shift 2
  PROFILE_FILE="$SCRIPT_DIR/profiles/${PROFILE_NAME}.yml"
  if [[ -f "$PROFILE_FILE" ]]; then
    echo "🔄 Loading profile: $PROFILE_NAME"
    export MLX_VLM_PROFILE="$PROFILE_NAME"
    CONFIG_OVERRIDE="$PROFILE_FILE"
  else
    echo "❌ Profile not found: $PROFILE_FILE" >&2
    echo "Available profiles:" >&2
    ls "$SCRIPT_DIR/profiles/"*.yml 2>/dev/null | sed 's|.*/||;s|\.yml$||' >&2 || true
    exit 1
  fi
fi

ARGS=()
while [[ $# -gt 0 ]]; do
  ARGS+=("$1")
  shift
done

if [[ -n "$CONFIG_OVERRIDE" ]]; then
  exec python3 "$RUNNER" --config "$CONFIG_OVERRIDE" chat ${ARGS[@]+"${ARGS[@]}"}
else
  exec python3 "$RUNNER" --config "$SCRIPT_DIR/mlx_vlm_config.yml" chat ${ARGS[@]+"${ARGS[@]}"}
fi
