#!/usr/bin/env bash
# Wait for run_ocr.sh to finish (OCR-STATE.txt), then run the bounded VLM source review (finish.py).
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")"
# _paths.sh lives in Monoclaw/Python/ocr-compare/scripts; a work directory copied elsewhere sets OCR_PATHS_SH.
source "${OCR_PATHS_SH:-$(dirname "$(readlink -f "$0")")/../scripts/_paths.sh}"
while true; do
  s="$(cat OCR-STATE.txt 2>/dev/null || true)"
  case "$s" in
    "OCR and comparison complete"*) break;;
    FAILED*) echo "OCR FAILED: $s"; exit 1;;
  esac
  sleep 60
done
echo "=== $(date -Is) REVIEW START hillpeterson ==="
"$OCR_VENV_DIR/venv-marker/bin/python" -B -u finish.py
echo "=== $(date -Is) REVIEW END exit=$? ==="
