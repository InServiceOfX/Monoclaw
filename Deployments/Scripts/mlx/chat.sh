#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/mlx_runner.py"

if [[ ! -f "$SCRIPT_DIR/mlx_config.yml" ]]; then
  echo "ℹ️  No mlx_config.yml found. Copying from mlx_config.example.yml ..."
  cp "$SCRIPT_DIR/mlx_config.example.yml" "$SCRIPT_DIR/mlx_config.yml"
  echo "   Edit: $SCRIPT_DIR/mlx_config.yml"
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

exec python3 "$RUNNER" --config "$SCRIPT_DIR/mlx_config.yml" chat --mode "$MODE" ${ARGS[@]+"${ARGS[@]}"}
