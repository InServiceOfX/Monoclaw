#!/usr/bin/env bash
# Like run_ocr.sh but for LARGE PDFs (books). Marker is run via the chunked
# driver (scripts/marker_chunked.py) so it doesn't OOM; Nougat runs as usual
# (it streams pages and doesn't OOM, though it drops/repeats on long books, so
# treat Marker as the backbone). Then reconcile with combine.py.
#
# Usage:
#   scripts/run_ocr_large.sh PDF [--out DIR] [--only marker|nougat] [--no-reconcile]
#
# Tuning (env): MARKER_CHUNK (pages/chunk, default 16), MARKER_REC_BATCH /
# MARKER_DET_BATCH / MARKER_LAYOUT_BATCH (VRAM). See marker_chunked.py.
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_paths.sh"

PDF=""; OUT=""; ONLY=""; RECONCILE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2;;
    --only) ONLY="$2"; shift 2;;
    --no-reconcile) RECONCILE=0; shift;;
    -h|--help) sed -n '2,12p' "$0"; exit 0;;
    *) PDF="$1"; shift;;
  esac
done
[ -n "$PDF" ] && [ -f "$PDF" ] || { echo "ERROR: pass a PDF path"; exit 1; }
PDF="$(cd "$(dirname "$PDF")" && pwd)/$(basename "$PDF")"
STEM="$(basename "${PDF%.*}")"
: "${OUT:=$OCR_PROJECT_DIR/out/$STEM}"
mkdir -p "$OUT" "$TORCH_HOME" "$MODEL_CACHE_DIR" "$HF_HOME"
V_NOUGAT="$OCR_VENV_DIR/venv-nougat"; V_MARKER="$OCR_VENV_DIR/venv-marker"
ocr_print_config; echo "  PDF=$PDF"; echo "  OUT=$OUT"; echo

run_marker() {
  [ -x "$V_MARKER/bin/python" ] || { echo "ERROR: marker venv missing — setup_envs.sh marker"; exit 1; }
  echo "==> Marker (chunked, complete-coverage backbone)"
  "$V_MARKER/bin/python" "$OCR_SCRIPTS_DIR/marker_chunked.py" "$PDF" "$OUT/$STEM.marker.md"
}
run_nougat() {
  [ -x "$V_NOUGAT/bin/nougat" ] || { echo "ERROR: nougat venv missing — setup_envs.sh nougat"; exit 1; }
  echo "==> Nougat (equation cross-check; unreliable on long books)"
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    "$V_NOUGAT/bin/nougat" "$PDF" -o "$OUT/nougat_out" --markdown
}

case "$ONLY" in
  marker) run_marker;;
  nougat) run_nougat;;
  "")     run_marker; run_nougat;;
  *) echo "unknown --only: $ONLY"; exit 1;;
esac

if [ "$RECONCILE" = 1 ] && [ -z "$ONLY" ]; then
  NMMD="$OUT/nougat_out/$STEM.mmd"; MMD="$OUT/$STEM.marker.md"
  if [ -f "$NMMD" ] && [ -f "$MMD" ]; then
    echo "==> Reconciling (combine.py)"
    python3 "$OCR_PROJECT_DIR/combine.py" "$NMMD" "$MMD" "$OUT/reconciled"
    echo "Next (resolve conflicts at scale): scripts/triage_conflicts.py $OUT/reconciled/equations.json $OUT/reconciled"
  else
    echo "WARN: missing $NMMD or $MMD; skipping reconcile"
  fi
fi
