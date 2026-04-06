#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/mlx_vlm_runner.py"
PROFILES_DIR="$SCRIPT_DIR/profiles"

usage() {
  echo "Usage: ./chat.sh <profile-name> [options]"
  echo ""
  echo "  profile-name   Name of a profile in profiles/ (without .yml extension)"
  echo "                 e.g. ./chat.sh gemma-4-e4b-it-4bit"
  echo ""
  echo "Options:"
  echo "  --temp <float>       Override temperature"
  echo "  --max-tokens <int>   Override max tokens"
  echo "  (any extra flags are forwarded to mlx_vlm_runner.py chat)"
  echo ""
  echo "Available profiles:"
  if compgen -G "$PROFILES_DIR/*.yml" > /dev/null 2>&1; then
    ls "$PROFILES_DIR/"*.yml 2>/dev/null | sed 's|.*/||;s|\.yml$||' | sed 's/^/  /'
  else
    echo "  (none — create one from a .yml.example)"
  fi
}

if [[ $# -eq 0 ]]; then
  usage
  exit 1
fi

FIRST_ARG="${1:-}"

if [[ "$FIRST_ARG" == "-h" || "$FIRST_ARG" == "--help" ]]; then
  usage
  exit 0
fi

PROFILE_FILE=""
if [[ "$FIRST_ARG" == *.yml && -f "$FIRST_ARG" ]]; then
  PROFILE_FILE="$(realpath "$FIRST_ARG")"
elif [[ -f "$PROFILES_DIR/${FIRST_ARG}.yml" ]]; then
  PROFILE_FILE="$PROFILES_DIR/${FIRST_ARG}.yml"
elif [[ -f "$PROFILES_DIR/${FIRST_ARG}" ]]; then
  PROFILE_FILE="$PROFILES_DIR/${FIRST_ARG}"
else
  echo "❌ Profile not found: $FIRST_ARG" >&2
  echo "" >&2
  usage >&2
  exit 1
fi
shift

echo "🔄 Profile: $(basename "$PROFILE_FILE" .yml)"

GLOBAL_CONFIG="$SCRIPT_DIR/mlx_vlm_config.yml"
if [[ ! -f "$GLOBAL_CONFIG" ]]; then
  echo "❌ Missing mlx_vlm_config.yml. Copy mlx_vlm_config.yml.example → mlx_vlm_config.yml and edit it." >&2
  exit 1
fi

exec python3 "$RUNNER" \
  --config "$GLOBAL_CONFIG" \
  --profile "$PROFILE_FILE" \
  chat "$@"
