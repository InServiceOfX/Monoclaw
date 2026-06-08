#!/usr/bin/env bash
# Run Marker + Nougat on a PDF (locally, on the GPU) and reconcile them.
#
# Runs the two models SEQUENTIALLY — on an 8 GB GPU they don't both fit. Weight
# locations come from scripts/_paths.sh (TORCH_HOME/NOUGAT_CHECKPOINT for nougat,
# MODEL_CACHE_DIR/HF_HOME for marker); first run downloads the open weights to
# OCR_WEIGHTS_DIR, later runs reuse them.
#
# Usage:
#   scripts/run_ocr.sh PDF [--out DIR] [--only marker|nougat] [--no-reconcile]
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

V_NOUGAT="$OCR_VENV_DIR/venv-nougat"
V_MARKER="$OCR_VENV_DIR/venv-marker"
ocr_print_config; echo "  PDF              = $PDF"; echo "  OUT              = $OUT"; echo

run_marker() {
  [ -x "$V_MARKER/bin/marker_single" ] || { echo "ERROR: marker venv missing — run setup_envs.sh marker"; exit 1; }
  echo "==> Marker (complete-coverage backbone)"
  "$V_MARKER/bin/marker_single" "$PDF" --output_dir "$OUT/marker_out" --output_format markdown
}

run_nougat() {
  [ -x "$V_NOUGAT/bin/nougat" ] || { echo "ERROR: nougat venv missing — run setup_envs.sh nougat"; exit 1; }
  echo "==> Nougat (arXiv equation specialist)"
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
  NMMD="$OUT/nougat_out/$STEM.mmd"
  MMD="$OUT/marker_out/$STEM/$STEM.md"
  if [ -f "$NMMD" ] && [ -f "$MMD" ]; then
    echo "==> Reconciling (combine.py)"
    python3 "$OCR_PROJECT_DIR/combine.py" "$NMMD" "$MMD" "$OUT/reconciled"
    echo "Reconciled outputs in $OUT/reconciled/ (merged.md, equations.json, reconciliation_report.md)"
  else
    echo "WARN: missing $NMMD or $MMD; skipping reconcile"
  fi
fi
