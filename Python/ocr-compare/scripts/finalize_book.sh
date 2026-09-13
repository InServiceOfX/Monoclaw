#!/usr/bin/env bash
# Post-process a finished marker_book.py run into the full slug layout.
#
# Usage: finalize_book.sh SLUG_DIR PDF_STEM
#   SLUG_DIR   the book's directory, holding book_spec.json and ocr-compare/marker/
#   PDF_STEM   the source PDF's basename without .pdf (for the compatibility
#              <stem>.marker.md that run_batch_ocr.sh and the dashboard expect)
#
# Every step is idempotent; rerun it after adding chunks.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SLUG_DIR="${1:?usage: finalize_book.sh SLUG_DIR PDF_STEM}"
STEM="${2:?usage: finalize_book.sh SLUG_DIR PDF_STEM}"
MARKER="$SLUG_DIR/ocr-compare/marker"
SLUG="$(basename "$SLUG_DIR")"

echo "=== 1/6 assemble pages + book.md ==="
python3 "$HERE/assemble_book.py" "$MARKER" "$SLUG_DIR" \
        --page-map "$SLUG_DIR/page_map.json" || exit 1

echo "=== 2/6 page map + TOC, verified against the OCR text ==="
python3 "$HERE/build_page_map.py" "$SLUG_DIR/book_spec.json" "$SLUG_DIR" \
        --pages-dir "$SLUG_DIR/pages" || exit 1

echo "=== 3/6 equations / tables / figures ==="
python3 "$HERE/extract_artifacts.py" "$MARKER" "$SLUG_DIR/artifacts" \
        --page-map "$SLUG_DIR/page_map.json" || exit 1

echo "=== 4/6 chapter split by page range ==="
python3 "$HERE/split_by_pages.py" "$SLUG_DIR" || exit 1

echo "=== 5/6 INDEX.md ==="
python3 "$HERE/make_index.py" "$SLUG_DIR" || exit 1

echo "=== 6/6 compatibility artifacts ==="
# run_batch_ocr.sh, combine.py and the reading-room dashboard all look for a
# flat <stem>.marker.md backbone; give them one alongside the page-accurate build.
cp -f "$SLUG_DIR/book.md" "$SLUG_DIR/ocr-compare/$STEM.marker.md"
cp -f "$SLUG_DIR/book.md" "$SLUG_DIR/$SLUG.md"
if command -v pandoc >/dev/null 2>&1; then
  pandoc -f markdown+tex_math_dollars -t latex --standalone \
         -o "$SLUG_DIR/$SLUG.tex" "$SLUG_DIR/book.md" 2>/dev/null \
    && echo "  wrote $SLUG.tex" \
    || echo "  WARN pandoc failed; skipping .tex"
else
  echo "  WARN pandoc not installed; skipping .tex"
fi

echo
echo "=== layout ==="
du -sh "$SLUG_DIR"/* 2>/dev/null | sort -k2
