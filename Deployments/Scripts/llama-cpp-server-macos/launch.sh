#!/usr/bin/env bash
# launch.sh — Launch llama.cpp server natively on macOS (Metal).
#
# Usage:
#   ./launch.sh <profile>           # Start server with profile
#   ./launch.sh --stop              # Stop running server
#   ./launch.sh --status            # Show server status
#   ./launch.sh                     # List available profiles
#
# Global settings: config.yml (copy from config.yml.example)
# Model settings:  profiles/<profile>.yml
#
# Full server docs: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CONFIG_FILE="$SCRIPT_DIR/config.yml"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: config.yml not found. Run: cp config.yml.example config.yml"
    exit 1
fi

PID_FILE="$SCRIPT_DIR/.llama-server.pid"

# ── handle --stop / --status with no profile ──────────────────────────────────
case "${1:-}" in
    --stop|stop)
        if [[ -f "$PID_FILE" ]]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                echo "Stopped llama-server (PID $PID)"
            else
                echo "Process $PID not running (stale PID file)"
            fi
            rm -f "$PID_FILE"
        else
            echo "No PID file found. Checking for running llama-server..."
            pkill -f "llama-server.*--port" && echo "Killed" || echo "No llama-server found"
        fi
        exit 0
        ;;
    --status|status)
        if [[ -f "$PID_FILE" ]]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo "llama-server running (PID $PID)"
                ps -p "$PID" -o pid,comm,etime,rss | tail -1
            else
                echo "Not running (stale PID file)"
                rm -f "$PID_FILE"
            fi
        else
            pgrep -f "llama-server" >/dev/null 2>&1 \
                && echo "llama-server found (not managed by this script):" \
                && pgrep -af "llama-server" \
                || echo "No llama-server running"
        fi
        exit 0
        ;;
    "")
        echo "Usage: $0 <profile> [extra llama-server args...]"
        echo "       $0 --stop | stop"
        echo "       $0 --status | status"
        echo ""
        echo "Available profiles:"
        for f in "$SCRIPT_DIR/profiles/"*.yml; do
            [[ -f "$f" ]] && basename "$f" .yml | sed 's/^/  /'
        done
        exit 0
        ;;
esac

PROFILE="$1"; shift

PROFILE_FILE="$SCRIPT_DIR/profiles/${PROFILE}.yml"
if [[ ! -f "$PROFILE_FILE" ]]; then
    echo "Error: Profile not found: $PROFILE_FILE"
    echo "Available:"
    for f in "$SCRIPT_DIR/profiles/"*.yml; do
        [[ -f "$f" ]] && basename "$f" .yml | sed 's/^/  /'
    done
    exit 1
fi

# ── resolve Python from uv venv ──────────────────────────────────────────────
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python3"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Error: uv venv not found at $REPO_ROOT/.venv"
    echo "  Run: cd $REPO_ROOT && uv venv && uv pip install pyyaml"
    exit 1
fi

if ! "$VENV_PYTHON" -c "import yaml" 2>/dev/null; then
    echo "Error: pyyaml not installed in venv"
    echo "  Run: uv pip install pyyaml"
    exit 1
fi

# ── build server args via Python ─────────────────────────────────────────────
eval "$("$VENV_PYTHON" - "$CONFIG_FILE" "$PROFILE_FILE" <<'PYEOF'
import json
import os
from pathlib import Path
import sys
import yaml
import shlex

cfg = yaml.safe_load(open(sys.argv[1])) or {}
prof = yaml.safe_load(open(sys.argv[2])) or {}

srv_cfg = cfg.get("server", {})
binary = srv_cfg.get("binary", "llama-server")
models_dir = cfg.get("models_dir", "")

# Model path: profile takes precedence. Absolute paths are used as-is; relative
# paths are resolved against models_dir from config.yml.
model_path = prof.get("model_path", "")
if not model_path:
    print('echo "Error: No model_path in profile"; exit 1')
    sys.exit(0)
model_path = os.path.expandvars(os.path.expanduser(str(model_path)))
if not os.path.isabs(model_path):
    if not models_dir:
        print('echo "Error: Relative model_path requires models_dir in config.yml"; exit 1')
        sys.exit(0)
    base = Path(os.path.expandvars(os.path.expanduser(str(models_dir))))
    model_path = str(base / model_path)

# Server host/port: profile overrides config
srv_prof = prof.get("server", {})
host = srv_prof.get("host", srv_cfg.get("host", "127.0.0.1"))
port = str(srv_prof.get("port", srv_cfg.get("port", 8080)))

# Build llama-server args
server_args = ["-m", model_path, "--host", host, "--port", port]

def add(flag, key, src=prof):
    val = src.get(key)
    if val is not None and val != "":
        server_args.extend([flag, str(val)])

def add_bool(flag_on, flag_off, key):
    val = prof.get(key)
    if val is None:
        return
    server_args.append(flag_on if val else flag_off)

add("-ngl", "n_gpu_layers")
add("-c", "ctx_size")
add("-n", "n_predict")
add("-np", "parallel")
add("-b", "batch_size")
add("-ub", "ubatch_size")
add("-t", "threads")

# Flash attention
fa = prof.get("flash_attn")
if fa is not None:
    server_args.extend(["-fa", str(fa)])

# KV cache quantization
ctk = prof.get("cache_type_k")
if ctk:
    server_args.extend(["--cache-type-k", ctk])
ctv = prof.get("cache_type_v")
if ctv:
    server_args.extend(["--cache-type-v", ctv])

# Reasoning
reasoning = prof.get("reasoning")
if reasoning is not None:
    server_args.extend(["--reasoning", str(reasoning)])
rf = prof.get("reasoning_format")
if rf:
    server_args.extend(["--reasoning-format", rf])

# Boolean flags
if prof.get("metrics"):
    server_args.append("--metrics")
if prof.get("mlock"):
    server_args.append("--mlock")
add("--prio", "priority")
add("--poll", "poll")
add("--prio-batch", "priority_batch")
add("--poll-batch", "poll_batch")
if prof.get("no_mmap"):
    server_args.append("--no-mmap")
if prof.get("jinja") is not None:
    if prof["jinja"]:
        server_args.append("--jinja")
    else:
        server_args.append("--no-jinja")
add_bool("--cont-batching", "--no-cont-batching", "cont_batching")

# RoPE
add("--rope-scaling", "rope_scaling")
add("--rope-scale", "rope_scale")
add("--rope-freq-base", "rope_freq_base")
add("--rope-freq-scale", "rope_freq_scale")

# API key
api_key = prof.get("api_key")
if api_key:
    server_args.extend(["--api-key", api_key])

# Multimodal projector
mmproj = prof.get("mmproj_path")
if mmproj:
    server_args.extend(["--mmproj", mmproj])

# Chat template
ct = prof.get("chat_template")
if ct:
    server_args.extend(["--chat-template", ct])
ct_kwargs = prof.get("chat_template_kwargs")
if ct_kwargs:
    if isinstance(ct_kwargs, (dict, list)):
        ct_kwargs = json.dumps(ct_kwargs, separators=(",", ":"))
    server_args.extend(["--chat-template-kwargs", str(ct_kwargs)])

# Alias
alias = prof.get("alias")
if alias:
    server_args.extend(["-a", alias])

# Speculative decoding
if prof.get("spec_default"):
    server_args.append("--spec-default")

# Server tuning
add("--timeout", "timeout")
add("--threads-http", "threads_http")
add("--cache-ram", "cache_ram")
add("--ctx-checkpoints", "ctx_checkpoints")
add("--checkpoint-min-step", "checkpoint_min_step")
add_bool("--cache-prompt", "--no-cache-prompt", "cache_prompt")
add_bool("--cache-idle-slots", "--no-cache-idle-slots", "cache_idle_slots")
add_bool("--warmup", "--no-warmup", "warmup")

# Escape hatch for newly-added llama-server flags.
extra_args = prof.get("extra_args") or []
if isinstance(extra_args, str):
    extra_args = shlex.split(extra_args)
server_args.extend(str(arg) for arg in extra_args)

# Emit shell vars
print(f'LLAMA_BINARY={shlex.quote(binary)}')
print(f'SERVE_PORT={shlex.quote(port)}')
print(f'SERVE_HOST={shlex.quote(host)}')
print(f'SERVER_ARGS=({" ".join(shlex.quote(a) for a in server_args)})')
PYEOF
)"

# ── stop existing if managed ─────────────────────────────────────────────────
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing llama-server (PID $OLD_PID)..."
        kill "$OLD_PID"
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

# ── launch ────────────────────────────────────────────────────────────────────
echo "=== llama.cpp Metal Server ==="
echo "Profile  : ${PROFILE}"
echo "Binary   : ${LLAMA_BINARY}"
echo "Endpoint : http://${SERVE_HOST}:${SERVE_PORT}"
echo ""
echo "Command:"
echo "  ${LLAMA_BINARY} ${SERVER_ARGS[*]}" "$@"
echo ""

# Run in foreground by default (Ctrl-C to stop)
# Use --background flag to daemonize
if [[ "${1:-}" == "--background" || "${1:-}" == "-bg" ]]; then
    shift
    "${LLAMA_BINARY}" "${SERVER_ARGS[@]}" "$@" &
    SERVER_PID=$!
    echo "$SERVER_PID" > "$PID_FILE"
    echo "Started in background (PID $SERVER_PID)"
    echo ""

    # Wait for ready
    echo "Waiting for server on http://${SERVE_HOST}:${SERVE_PORT} ..."
    for i in $(seq 1 90); do
        if curl -sf "http://${SERVE_HOST}:${SERVE_PORT}/v1/models" >/dev/null 2>&1; then
            echo ""
            echo "Server ready at http://${SERVE_HOST}:${SERVE_PORT}"
            echo "  OpenAI API: http://${SERVE_HOST}:${SERVE_PORT}/v1/chat/completions"
            echo "  Web UI:     http://${SERVE_HOST}:${SERVE_PORT}"
            echo "  Stop:       $0 --stop"
            exit 0
        fi
        printf "."
        sleep 2
    done
    echo ""
    echo "Warning: Server did not respond after 3 min. Check: ps -p $SERVER_PID"
else
    exec "${LLAMA_BINARY}" "${SERVER_ARGS[@]}" "$@"
fi
