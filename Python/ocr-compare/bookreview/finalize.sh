#!/usr/bin/env bash
# Post-review finalisation (CPU only, idempotent): triage -> promote unplaced agreement
# corrections -> region placements -> assemble -> publish.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
# _paths.sh lives in Monoclaw/Python/ocr-compare/scripts; a work directory copied elsewhere sets OCR_PATHS_SH.
source "${OCR_PATHS_SH:-$(dirname "$(readlink -f "$0")")/../scripts/_paths.sh}"
PY="$OCR_VENV_DIR/venv-marker/bin/python"
$PY -B scripts/augment_tables.py > /dev/null   # apply object-classification reviews (idempotent)
$PY -B scripts/triage_math.py > /dev/null
$PY -B -c "import sys,json;sys.path.insert(0,'scripts');from assemble import assemble;assemble(json.load(open('scripts/books.json'))['books'][0])" > /dev/null
$PY -B scripts/promote_agreement_placements.py
$PY -B scripts/fix_placements.py
$PY -B -c "import sys,json;sys.path.insert(0,'scripts');from assemble import assemble;s=assemble(json.load(open('scripts/books.json'))['books'][0]);print(json.dumps({k:s[k] for k in ['counts','unresolved_records','status','vision_job_status']}))"
# Second triage pass: fragment anchors are checked against the pages as just assembled (placements applied).
$PY -B scripts/triage_math.py > /dev/null
$PY -B -c "import sys,json;sys.path.insert(0,'scripts');from assemble import assemble;s=assemble(json.load(open('scripts/books.json'))['books'][0]);print(json.dumps({k:s[k] for k in ['counts','unresolved_records','status','vision_job_status']}))"
$PY -B scripts/publish_book.py
$PY -B scripts/publish_notation.py
