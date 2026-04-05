#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/mlx_runner.py"

if [[ ! -f "$SCRIPT_DIR/mlx_config.yml" ]]; then
  echo "ℹ️  No mlx_config.yml found. Copying from mlx_config.example.yml ..."
  cp "$SCRIPT_DIR/mlx_config.example.yml" "$SCRIPT_DIR/mlx_config.yml"
  echo "   Edit: $SCRIPT_DIR/mlx_config.yml"
fi

# Support quick profile loading via --profile <name>
if [[ "$1" == "--profile" || "$1" == "-p" ]]; then
  PROFILE_NAME="$2"
  shift 2
  if [[ -n "$PROFILE_NAME" ]]; then
    PROFILE_FILE="$SCRIPT_DIR/profiles/${PROFILE_NAME}.yml"
    if [[ -f "$PROFILE_FILE" ]]; then
      echo "🔄 Loading profile: $PROFILE_NAME"
      export MLX_PROFILE="$PROFILE_NAME"
      CONFIG_OVERRIDE="$PROFILE_FILE"
    else
      echo "❌ Profile not found: $PROFILE_FILE" >&2
      echo "Available profiles:" >&2
      ls "$SCRIPT_DIR/profiles/"*.yml 2>/dev/null | sed 's|.*/||;s|\.yml$||' >&2
      exit 1
    fi
  fi
fi

MODE="thinking"
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-think|--instruct) MODE="instruct"; shift ;;
    --coding) MODE="coding"; shift ;;
    --reasoning) MODE="reasoning"; shift ;;
    --mode)
      if [[ $# -lt 2 || -z "${2:-}" || "${2:-}" == --* ]]; then
        echo "❌ --mode requires a value (example: --mode instruct_general)" >&2
        exit 2
      fi
      MODE="$2"; shift 2 ;;

    *) ARGS+=("$1"); shift ;;
  esac
done

if [[ -n "${CONFIG_OVERRIDE:-}" ]]; then
  exec python3 "$RUNNER" --config "$CONFIG_OVERRIDE" serve --mode "$MODE" ${ARGS[@]+"${ARGS[@]}"}
else
  exec python3 "$RUNNER" --config "$SCRIPT_DIR/mlx_config.yml" serve --mode "$MODE" ${ARGS[@]+"${ARGS[@]}"}
fi
