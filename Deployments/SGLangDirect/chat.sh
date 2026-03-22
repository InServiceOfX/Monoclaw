#!/usr/bin/env bash
# SGLang interactive chat client
# Usage: ./chat.sh [--profile longctx] [--mode thinking] [--no-think]
#
# Assumes the server is already running via: ./launch.sh [profile]
# Connects to http://localhost:30000 by default (reads host/port from yaml config).
#
# Modes:
#   thinking (default) — extended thinking enabled, Qwen3.5 /think tokens
#   instruct / --no-think — thinking disabled, faster responses
#   coding   — thinking on, coding system prompt
#
# In-chat commands: /clear /mode <name> /no-think /think /history /quit

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROFILE="longctx"
ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            PROFILE="${2:?--profile requires a value}"
            shift 2 ;;
        --no-think|--instruct)
            ARGS+=(--no-think)
            shift ;;
        --mode)
            ARGS+=(--mode "${2:?--mode requires a value}")
            shift 2 ;;
        --url)
            ARGS+=(--url "${2:?--url requires a value}")
            shift 2 ;;
        *)
            ARGS+=("$1")
            shift ;;
    esac
done

exec python3 "$SCRIPT_DIR/sglang_chat.py" \
    --profile "$PROFILE" \
    --config-dir "$SCRIPT_DIR" \
    "${ARGS[@]+"${ARGS[@]}"}"
