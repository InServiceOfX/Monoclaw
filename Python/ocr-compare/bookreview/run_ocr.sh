#!/usr/bin/env bash
# OCR both engines for the book in scripts/books.json: inventory (PDFium native text, 1x renders, hashes)
# ‖ Marker in 16-page chunks (forced OCR unless books.json force_ocr=false) → extract.py (page-scoped
# objects, crops, tables, inline math) ‖ Nougat per page → math_tokens.rs + reconcile.py (page-local
# equation alignment, review jobs). Holds gpu.lock; never run two GPU jobs at once. Writes OCR-STATE.txt.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
# _paths.sh lives in Monoclaw/Python/ocr-compare/scripts; a work directory copied elsewhere sets OCR_PATHS_SH.
source "${OCR_PATHS_SH:-$(dirname "$(readlink -f "$0")")/../scripts/_paths.sh}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
exec 9>gpu.lock
flock -n 9
book_root="$(python3 -c 'import json;print(json.load(open("scripts/books.json"))["books"][0]["root"])')"
book_pdf="$(python3 -c 'import json;print(json.load(open("scripts/books.json"))["books"][0]["pdf"])')"
force_ocr="$(python3 -c 'import json;print(json.load(open("scripts/books.json"))["books"][0]["force_ocr"])')"
marker_flag=""
if [ "$force_ocr" = "False" ]; then marker_flag="--no-force-ocr"; fi
mkdir -p "$book_root/logs"
trap 'echo "FAILED at line $LINENO" > OCR-STATE.txt' ERR
echo 'Marker and source inventory running' > OCR-STATE.txt
"$OCR_VENV_DIR/venv-marker/bin/python" -B -u scripts/inventory.py > "$book_root/logs/inventory.log" 2>&1 &
inventory_pid=$!
"$OCR_VENV_DIR/venv-marker/bin/python" -B -u scripts/marker_book.py "$book_pdf" "$book_root/sources/marker" $marker_flag --chunk 16 > "$book_root/logs/marker.log" 2>&1
wait "$inventory_pid"
echo 'Marker complete; structural extraction and Nougat running' > OCR-STATE.txt
"$OCR_VENV_DIR/venv-marker/bin/python" -B -u scripts/extract.py > "$book_root/logs/extract.log" 2>&1 &
extract_pid=$!
"$OCR_VENV_DIR/venv-nougat/bin/python" -B -u scripts/nougat_pages.py "$book_pdf" "$book_root/sources/nougat" --batch 8 > "$book_root/logs/nougat.log" 2>&1
wait "$extract_pid"
echo 'Both OCR passes complete; reconciliation preparation running' > OCR-STATE.txt
rustc -O scripts/math_tokens.rs -o scripts/math_tokens
"$OCR_VENV_DIR/venv-marker/bin/python" -B -u scripts/reconcile.py > "$book_root/logs/reconcile.log" 2>&1
echo 'OCR and comparison complete; source review and packaging remain' > OCR-STATE.txt
