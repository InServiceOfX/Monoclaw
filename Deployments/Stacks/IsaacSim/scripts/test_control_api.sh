#!/bin/bash
# Test the Isaac Sim HTTP control API (enable_ros2_bridge.py, port 8282).
#
# Run this from the host AFTER Isaac Sim is fully booted and the control
# server is listening.  Requires curl and jq.
#
# Usage:
#   ./scripts/test_control_api.sh [HOST:PORT]
#   HOST:PORT defaults to localhost:8282

set -e

BASE="${1:-http://localhost:8282}"
PASS=0
FAIL=0

_check() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [ "$actual" = "$expected" ]; then
        echo "✅ $label"
        PASS=$((PASS+1))
    else
        echo "❌ $label — expected '$expected', got '$actual'"
        FAIL=$((FAIL+1))
    fi
}

echo "=== Isaac Sim control API smoke test ==="
echo "    target: $BASE"
echo ""

# ── /health ───────────────────────────────────────────────────────────────────
STATUS=$(curl -sf "$BASE/health" | jq -r .status 2>/dev/null || echo "FAIL")
_check "GET /health → status=ok" "ok" "$STATUS"

# ── /diagnostics ──────────────────────────────────────────────────────────────
DIAG=$(curl -sf "$BASE/diagnostics" 2>/dev/null || echo "{}")
RUNNING=$(echo "$DIAG" | jq -r 'if .running then "true" else "false" end' 2>/dev/null || echo "FAIL")
echo "    diagnostics: $DIAG"
# sim might be running or paused at test time — just check the key exists
HAS_KEY=$(echo "$DIAG" | jq 'has("running")' 2>/dev/null || echo "false")
_check "GET /diagnostics → has 'running' key" "true" "$HAS_KEY"

# ── /scene/list ───────────────────────────────────────────────────────────────
SCENES=$(curl -sf "$BASE/scene/list" 2>/dev/null || echo "{}")
HAS_SCENES=$(echo "$SCENES" | jq 'has("scenes")' 2>/dev/null || echo "false")
_check "GET /scene/list → has 'scenes' key" "true" "$HAS_SCENES"
echo "    scenes: $(echo $SCENES | jq -c .scenes 2>/dev/null)"

# ── /timeline/pause ───────────────────────────────────────────────────────────
PAU=$(curl -sf -X POST "$BASE/timeline/pause" 2>/dev/null | jq -r .status 2>/dev/null || echo "FAIL")
_check "POST /timeline/pause → status=queued" "queued" "$PAU"

# ── /timeline/play ────────────────────────────────────────────────────────────
PLAY=$(curl -sf -X POST "$BASE/timeline/play" 2>/dev/null | jq -r .status 2>/dev/null || echo "FAIL")
_check "POST /timeline/play → status=queued" "queued" "$PLAY"

# ── /scene/load (bad path → 404, safe: server validates before touching stage) ─
LOAD_CODE=$(curl -so /dev/null -w "%{http_code}" -X POST "$BASE/scene/load" \
              -H "Content-Type: application/json" \
              -d '{"path": "/nonexistent/test.usd"}' 2>/dev/null || echo "000")
_check "POST /scene/load (bad path) → HTTP 404" "404" "$LOAD_CODE"

# ── /scene/load (missing path field) ─────────────────────────────────────────
LOAD_EMPTY=$(curl -so /dev/null -w "%{http_code}" -X POST "$BASE/scene/load" \
               -H "Content-Type: application/json" \
               -d '{}' 2>/dev/null || echo "000")
_check "POST /scene/load (no path) → HTTP 400" "400" "$LOAD_EMPTY"

# ── unknown route → 404 ───────────────────────────────────────────────────────
HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" "$BASE/nonexistent" 2>/dev/null || echo "000")
_check "GET /nonexistent → HTTP 404" "404" "$HTTP_CODE"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
