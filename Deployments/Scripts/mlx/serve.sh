#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/mlx_runner.py"
PROFILES_DIR="$SCRIPT_DIR/profiles"

usage() {
  echo "Usage: ./serve.sh <profile-name> [options]"
  echo ""
  echo "  profile-name   Name of a profile in profiles/ (without .yml extension)"
  echo "                 e.g. ./serve.sh qwen35-9b-claude-opus-distilled-4bit"
  echo ""
  echo "Options:"
  echo "  --mode <mode>      Mode alias: thinking, coding, instruct, reasoning (default: thinking)"
  echo "  --no-think         Shortcut for --mode instruct"
  echo "  --coding           Shortcut for --mode coding"
  echo "  --reasoning        Shortcut for --mode reasoning"
  echo "  (any extra flags are forwarded to mlx_runner.py serve)"
  echo ""
  echo "Available profiles:"
  if compgen -G "$PROFILES_DIR/*.yml" > /dev/null 2>&1; then
    ls "$PROFILES_DIR/"*.yml 2>/dev/null | sed 's|.*/||;s|\.yml$||' | sed 's/^/  /'
  else
    echo "  (none — create one from a .yml.example)"
  fi
}

# ── Require a profile name as first argument ──
if [[ $# -eq 0 ]]; then
  usage
  exit 1
fi

FIRST_ARG="${1:-}"

# Handle help
if [[ "$FIRST_ARG" == "-h" || "$FIRST_ARG" == "--help" ]]; then
  usage
  exit 0
fi

# Resolve profile: accept bare name or name.yml, from profiles/ dir or as a path
PROFILE_FILE=""
if [[ "$FIRST_ARG" == *.yml && -f "$FIRST_ARG" ]]; then
  # Direct path to a .yml file
  PROFILE_FILE="$(realpath "$FIRST_ARG")"
elif [[ -f "$PROFILES_DIR/${FIRST_ARG}.yml" ]]; then
  # Bare profile name → look in profiles/
  PROFILE_FILE="$PROFILES_DIR/${FIRST_ARG}.yml"
elif [[ -f "$PROFILES_DIR/${FIRST_ARG}" ]]; then
  # Name with .yml already included
  PROFILE_FILE="$PROFILES_DIR/${FIRST_ARG}"
else
  echo "❌ Profile not found: $FIRST_ARG" >&2
  echo "" >&2
  usage >&2
  exit 1
fi
shift

echo "🔄 Profile: $(basename "$PROFILE_FILE" .yml)"

# ── Require global config ──
GLOBAL_CONFIG="$SCRIPT_DIR/mlx_config.yml"
if [[ ! -f "$GLOBAL_CONFIG" ]]; then
  echo "❌ Missing mlx_config.yml. Copy mlx_config.yml.example → mlx_config.yml and edit it." >&2
  exit 1
fi

# ── Parse remaining args for mode shortcuts ──
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

exec python3 "$RUNNER" \
  --config "$GLOBAL_CONFIG" \
  --profile "$PROFILE_FILE" \
  serve --mode "$MODE" ${ARGS[@]+"${ARGS[@]}"}
