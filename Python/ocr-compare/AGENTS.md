# AGENTS.md — Python/ocr-compare

## Scope

Two-model PDF→LaTeX OCR (Marker + Nougat) with a reconciliation + conflict-
resolution pipeline, for math/physics papers that have no `.tex` source. Runs
local open weights on an NVIDIA GPU.

## Setup

```bash
cd Python/ocr-compare
scripts/setup_envs.sh                 # builds uv venvs (CUDA torch). Subset: ... nougat marker
```

## Run

```bash
# small PDF (paper):
scripts/run_ocr.sh PDF [--out DIR] [--only marker|nougat] [--no-reconcile]
# BIG PDF (book): marker_single OOMs — use the chunked path:
scripts/run_ocr_large.sh PDF --out DIR        # tune: MARKER_CHUNK, MARKER_REC_BATCH
# SCANNED book (no text layer): the page-accurate path, then post-process:
"$OCR_VENV_DIR/venv-marker/bin/python" scripts/marker_book.py PDF SLUG/ocr-compare/marker
scripts/finalize_book.sh SLUG "PDF stem"      # pages, chapters, artifacts, INDEX
# pure-stdlib reconcile only, no venv:
python3 combine.py NOUGAT.mmd MARKER.md OUTDIR/
# triage book-scale conflicts before vision-resolving:
scripts/triage_conflicts.py reconciled/equations.json reconciled/
# vision-resolve the tier4 conflicts (render strips, then judge — see below):
venvs/venv-resolve/bin/python resolve.py --pdf BOOK.pdf --eqs tier4.json \
    --merged reconciled/merged.md --outdir reconciled/ --manifest
```

## Scanned books

A scan has **no text layer**, so two things change. First, Marker is not merely
the better of two backbones — it is the only source of the text, and Nougat is
a cross-check on equations and nothing more. Second, structure has to be
captured on the single OCR pass, because re-running it costs hours of GPU:
`marker_book.py` therefore builds each chunk's `Document` **once** and renders
it **twice**, markdown and JSON block tree, and saves the figure crops, all in
that one pass.

Consequences worth knowing before touching this path:

- **`paginate_output` is what makes it page-accurate.** Marker's `{K}` separator
  carries a 0-based PDF page index. Filenames and anchors here use the 1-based
  PDF page; a citation uses the printed folio. Three numberings; `page_map.json`
  resolves them, and confusing them is the standard bug.
- **Marker strips running heads**, leaving `PageHeader` blocks empty. So the
  printed folio cannot be recovered from the OCR — it comes from a folio rule in
  `book_spec.json`, hand-verified against the scan, and `build_page_map.py`
  re-checks that rule against every chapter heading. Never assume the offset is
  constant without checking both ends of the book.
- **Equation numbers arrive two ways.** Usually `\tag{4.7a}`; sometimes only as
  trailing text `(4.6)`. `extract_artifacts.py` handles both — keep it that way.
- **Marker keys its image dict by `BlockId` objects, not strings**, and the JSON
  renderer hangs base64 payloads off picture blocks. Both break `model_dump()`;
  serialize the block tree by hand (`block_to_dict`).
- **Resume is per chunk**, via `chunks/done/*.ok`. Rerunning the same command
  after a crash skips finished chunks; delete a sentinel to redo one.

## Vision-judging at book scale

`resolve.py --manifest` renders each conflict to a strip at `scale=5.0`
(~2161px wide). Don't feed those strips to an image-reading judge one-per-call or
several-at-once: judges commonly **reject multi-image requests whose dimensions
approach ~2000px** ("many-image" limit), so the naive "read each `pages/*.png`"
loop stalls. A single *tall* image loads fine, so batch them:

```bash
# stack ~6 strips into one <=1500px-wide sheet each (tag burned into a header):
venvs/venv-resolve/bin/python scripts/build_sheets.py reconciled/ 6
# -> reconciled/sheets/sheet_NNN.png + reconciled/sheets_meta/sheet_NNN.json
# read ONE sheet per call, compare nougat vs marker against the printed eq, then:
scripts/record_verdicts.py reconciled/ batch.json   # appends to verdicts.json
# when neither candidate is right, pass an explicit "latex" override in batch.json
# finally, merge with auto_verdicts and apply:
venvs/venv-resolve/bin/python resolve.py --eqs reconciled/equations.json \
    --merged reconciled/merged.md --outdir reconciled/ --apply combined_verdicts.json
```

`--apply` rebuilds `resolved.md` fresh from `merged.md` and resolves ONLY the tags
in the verdicts file passed — so apply the **union** of `auto_verdicts.json` +
`verdicts.json`, not the vision pass alone. `merged.md` carries inline
`⚠ CONFLICT` markers for the subset of conflicts that align to the Marker
backbone; the rest are still resolved in `equations_resolved.json` (the contract).

## Hard assumptions

- **NVIDIA GPU + CUDA is present.** Scripts always install the CUDA torch build
  (`CUDA_INDEX`, default cu130), never CPU. Don't add CPU fallbacks.
- **Open weights run locally**, downloaded once to `OCR_WEIGHTS_DIR`.
- **8 GB VRAM**: marker and nougat run **sequentially**, not concurrently.
- **Big PDFs OOM** under `marker_single` (whole-doc in RAM). Always use
  `marker_chunked.py` / `run_ocr_large.sh` for books, or `marker_book.py` for
  scans. Nougat is **unreliable on long scanned books** (drops whole chapters,
  truncates) — Marker is the backbone.

## Conventions

- Heavy artifacts (venvs, weights, `out/`) live OUTSIDE the repo and are
  gitignored. Never commit them. Change locations via env vars in
  `scripts/_paths.sh` / `scripts/env.sh`, not by hardcoding paths.
- The nougat pins (`transformers==4.38.2`, `albumentations==1.3.1`,
  `pypdfium2==4.30.0`) are load-bearing — don't bump them without re-validating;
  newer versions break `nougat-ocr 0.1.17`.
- `combine.py` stays pure stdlib so any session can run it without a venv.
- `equations.json` is the machine-readable contract (status per eq, dropped-page
  ranges, repetition artifacts). Prefer reading it over re-parsing the markdown.
- Treat Nougat output as untrusted: always check page coverage + repetition flags
  before relying on its equations.

## Reproducibility

- `requirements/*.txt` = direct pins; `requirements/*.lock.txt` = exact freezes
  from the validated RTX 3070 environment (torch 2.12.0+cu130, Python 3.10).

## Branching

- Work on feature/fix/chore branches only. Never commit to `master`/`main`.
