#!/bin/bash
# monoclaw-dev.sh
# Starts/stops the Monoclaw development stack (Python backend + frontend)
# Usage:
#   ./scripts/monoclaw-dev.sh          # start both
#   ./scripts/monoclaw-dev.sh --start
#   ./scripts/monoclaw-dev.sh --stop

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDFILE="$REPO_ROOT/.monoclaw-dev.pids"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[monoclaw-dev]${NC} $1"; }
warn() { echo -e "${YELLOW}[monoclaw-dev]${NC} $1"; }
err() { echo -e "${RED}[monoclaw-dev]${NC} $1" >&2; }

start_services() {
    if [[ -f "$PIDFILE" ]]; then
        warn "PID file already exists. Use --stop first or remove $PIDFILE"
        exit 1
    fi

    log "Starting Python backend (uvicorn)..."
    (
        cd "$REPO_ROOT/Python/finance"
        PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/monoclaw-pycache}" uv run uvicorn api.main:app --host 127.0.0.1 --port 8765 > "$REPO_ROOT/.backend.log" 2>&1 &
        echo $! > "$REPO_ROOT/.backend.pid"
    )

    log "Starting frontend (npm run dev)..."
    (
        cd "$REPO_ROOT/JavaScript/portfolio-dashboard"
        npm run dev > "$REPO_ROOT/.frontend.log" 2>&1 &
        echo $! > "$REPO_ROOT/.frontend.pid"
    )

    BACKEND_PID=$(cat "$REPO_ROOT/.backend.pid")
    FRONTEND_PID=$(cat "$REPO_ROOT/.frontend.pid")

    echo "BACKEND_PID=$BACKEND_PID" > "$PIDFILE"
    echo "FRONTEND_PID=$FRONTEND_PID" >> "$PIDFILE"

    log "Backend PID:  $BACKEND_PID (logs: .backend.log)"
    log "Frontend PID: $FRONTEND_PID (logs: .frontend.log)"
    log "Both services started. Use --stop to shut down cleanly."
}

stop_services() {
    if [[ ! -f "$PIDFILE" ]]; then
        warn "No PID file found. Nothing to stop."
        return 0
    fi

    # shellcheck disable=SC1090
    source "$PIDFILE"

    if [[ -n "${BACKEND_PID:-}" ]]; then
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            log "Stopping backend (PID $BACKEND_PID)..."
            kill -TERM "$BACKEND_PID" || true
            wait "$BACKEND_PID" 2>/dev/null || true
        else
            warn "Backend PID $BACKEND_PID not running"
        fi
    fi

    if [[ -n "${FRONTEND_PID:-}" ]]; then
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            log "Stopping frontend (PID $FRONTEND_PID)..."
            kill -TERM "$FRONTEND_PID" || true
            wait "$FRONTEND_PID" 2>/dev/null || true
        else
            warn "Frontend PID $FRONTEND_PID not running"
        fi
    fi

    rm -f "$PIDFILE" "$REPO_ROOT/.backend.pid" "$REPO_ROOT/.frontend.pid"
    log "All services stopped cleanly."
}

case "${1:-start}" in
    --start|start)
        start_services
        ;;
    --stop|stop)
        stop_services
        ;;
    *)
        err "Unknown option: $1"
        echo "Usage: $0 [--start|--stop]"
        exit 1
        ;;
esac
