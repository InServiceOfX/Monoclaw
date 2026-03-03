#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$HOME/.openclaw/workspace/petlibro"
CAPTURE="$BASE_DIR/capture_tutk.py"
LOG="$BASE_DIR/mitmdump_test.log"

mkdir -p "$BASE_DIR/captures"
rm -f "$BASE_DIR/captures/petlibro_video_flows.jsonl" "$BASE_DIR/captures/latest_video_bootstrap.json" "$LOG"

mitmdump -s "$CAPTURE" -p 8080 > "$LOG" 2>&1 &
MPID=$!
sleep 2

echo "[1/3] Sending test request through proxy to video endpoint..."
curl -sS -k -x http://127.0.0.1:8080 -X POST https://api.us.petlibro.com/app/device/video \
  -H 'Content-Type: application/json' \
  -H 'source: ANDROID' \
  -H 'language: EN' \
  -H 'version: 1.3.45' \
  -H 'token: TEST_TOKEN_123' \
  -d '{"deviceSn":"AF0301310008EF40024DSJ"}' > /tmp/petlibro_intercept_test_response.json || true

sleep 2
kill "$MPID" || true
sleep 1

echo "[2/3] Checking mitmdump log..."
if grep -q "\[PETLIBRO\] captured /app/device/video" "$LOG"; then
  echo "PASS: mitmproxy addon captured target endpoint"
else
  echo "FAIL: target endpoint not captured"
  echo "--- mitmdump log ---"
  cat "$LOG"
  exit 1
fi

echo "[3/3] Checking output files..."
if [[ -f "$BASE_DIR/captures/latest_video_bootstrap.json" ]] && [[ -s "$BASE_DIR/captures/latest_video_bootstrap.json" ]]; then
  echo "PASS: capture JSON written"
else
  echo "FAIL: capture JSON not written"
  exit 1
fi

echo "Intercept chain verified."
