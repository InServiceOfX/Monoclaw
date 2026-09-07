# ocr-compare — Nougat + Marker PDF→LaTeX, reconciled

Parse math/physics PDFs (papers with no `.tex` source) into LaTeX/markdown by
running **two** local open-weight OCR models and reconciling their disagreements
into a single source of truth. Built for study notes where equation correctness
matters.

Why two models (see [COMPARISON.md](COMPARISON.md) for the evidence):

- **Marker** (`marker-pdf`) — complete page coverage, never silently drops
  content. The structural backbone.
- **Nougat** (Meta, arXiv-trained) — cleaner LaTeX + correct spinor indices on
  arXiv-style math, **but** drops pages and repeats equations. The per-equation
  cross-check, never trusted blind.
- **`combine.py`** aligns their equations by `\tag{N}`, classifies each as
  *agree / conflict / marker-only (nougat dropped) / nougat-only*, and emits a
  merged doc plus a machine-readable report.
- **`resolve.py`** (optional) renders each conflicting equation to PNG and asks a
  vision model (xAI Grok, or Claude Code via a manifest) which LaTeX matches the
  page.

Runs **locally on an NVIDIA GPU** (open weights downloaded once). Validated on an
RTX 3070 Laptop, 8 GB VRAM — the two models run sequentially because they don't
both fit.

## Layout

```
combine.py              pure-stdlib reconciler (Nougat+Marker -> merged.md, equations.json)
resolve.py              vision conflict-resolver tier (Grok / Claude judge)
COMPARISON.md           head-to-head findings on a real arXiv paper
requirements/           pinned deps (*.txt) + exact freezes (*.lock.txt)
scripts/
  setup_envs.sh         build the uv venvs (CUDA torch), configurable locations
  run_ocr.sh            run marker+nougat on a (small) PDF, then reconcile
  run_ocr_large.sh      same for BIG PDFs/books — chunked Marker (no OOM) + reconcile
  marker_chunked.py     Marker driver: models loaded once, page-range chunks, capped VRAM
  --- scanned books (no text layer): the page-accurate pipeline ---
  marker_book.py        Marker driver that keeps STRUCTURE: paginated markdown +
                        the JSON block tree + extracted figure crops, resumable
  assemble_book.py      chunks -> pages/page-NNNN.md + book.md + page_index.json
  build_page_map.py     book_spec.json -> page_map.json + toc.json, folio rule VERIFIED
  extract_artifacts.py  block tree -> equations/tables/figures (json, md, tex, csv)
  split_by_pages.py     chapters cut by exact PDF page range (not heading guessing)
  make_index.py         the greppable INDEX.md (section -> printed page -> PDF page)
  finalize_book.sh      runs the five above in order after a marker_book.py run
  triage_conflicts.py   book-scale conflict triage: auto-resolve the ~95% cosmetic,
                        rank the few that genuinely need a vision judge
  _paths.sh             shared env/path resolution (storage, weights, CUDA)
  env.sh.example        copy to env.sh to override paths locally
samples/sample.pdf      10-pg arXiv test paper
examples/               committed reference outputs (no GPU needed to inspect)
```

## Scanned books (no text layer)

`run_ocr_large.sh` assumes a born-digital PDF. A **scan** — page images, no text
layer — needs more, because there is nothing to fall back on when a page is
missed and the figures exist only as pixels. Use `marker_book.py` and then
`finalize_book.sh`:

```bash
. scripts/_paths.sh
# 1. OCR, resumable. Rerun the same command after a crash; done chunks are skipped.
"$OCR_VENV_DIR/venv-marker/bin/python" scripts/marker_book.py BOOK.pdf SLUG_DIR/ocr-compare/marker

# 2. Write SLUG_DIR/book_spec.json by hand: the TOC read off the scan, and the
#    folio rule (how a printed page number maps to a PDF page). Verify that rule
#    against the running heads on a handful of pages spread through the book --
#    build_page_map.py will then re-check it against every chapter heading.

# 3. Everything else.
scripts/finalize_book.sh SLUG_DIR "PDF stem without .pdf"
```

What that produces, and why each piece exists:

| Output | Why |
|---|---|
| `book.md` | the definitive text, one HTML anchor per PDF page |
| `pages/page-NNNN.md` | one file per PDF page; makes any citation checkable |
| `chapters/` | split at exact page boundaries from `toc.json` |
| `artifacts/equations.{json,md,tex}` | every display equation, carrying the book's own number (`Eq. (4.7a)`) |
| `artifacts/tables.{json,md}`, `artifacts/tables/*.csv` | tables as data, not just as text |
| `artifacts/figures.{json,md}` + `images/` | the graphs, cropped, with their captions |
| `INDEX.md`, `toc.json`, `page_map.json` | the three page numberings, resolved |

**Three page numberings.** Marker's `{K}` separator is a 0-based PDF page index;
filenames and anchors use the 1-based PDF page a viewer shows; a citation uses
the folio printed on the paper. `page_map.json` is the resolver, and mixing them
up is the easy mistake to make.

## Quickstart

```bash
cd Python/ocr-compare

# 1. Build the venvs (defaults put venvs + weights on the large disk).
#    Hard-assumes NVIDIA CUDA; installs the CUDA torch build.
scripts/setup_envs.sh                 # nougat + marker + resolve

# 2. Run both models on a PDF and reconcile.
scripts/run_ocr.sh samples/sample.pdf
#    -> out/sample/{marker_out,nougat_out,reconciled/}

# 3. (optional) Resolve remaining equation conflicts with a vision model.
#    Grok:        XAI_API_KEY=... venvs/venv-resolve/bin/python resolve.py \
#                   --pdf samples/sample.pdf --eqs out/sample/reconciled/equations.json \
#                   --merged out/sample/reconciled/merged.md --outdir out/sample/reconciled
#    Claude Code: same but --manifest, judge the PNGs, write verdicts.json, then --apply.
```

## Large PDFs / books (665-page textbook tested)

`marker_single` builds the whole document in memory and **OOMs on big PDFs**
(~10 GB RSS killed a 665-page run on a 15 GB box). Use the chunked path instead:

```bash
# chunked Marker (models loaded once) + Nougat + reconcile, in one go:
scripts/run_ocr_large.sh /path/to/Book.pdf --out /path/to/Book_dir
#   -> Book_dir/<stem>.marker.md, Book_dir/nougat_out/<stem>.mmd, Book_dir/reconciled/

# tune for your GPU (defaults fit 8 GB): pages/chunk + batch sizes
MARKER_CHUNK=16 MARKER_REC_BATCH=8 scripts/run_ocr_large.sh Book.pdf --out Book_dir
```

A book yields **thousands** of equations and ~hundreds of "conflicts" — but ~95%
are cosmetic (Nougat plain-TeX vs Marker LaTeX) or Nougat truncations, not real
disagreements. **Triage before resolving** so you only vision-judge the few that
matter:

```bash
scripts/triage_conflicts.py Book_dir/reconciled/equations.json Book_dir/reconciled
#   -> auto_verdicts.json (cosmetic/garble/misaligned -> Marker backbone, auto)
#   -> vision_todo.json  (the genuine "same eq, real symbol diff", ranked clearest-first)
```

Then render strips for the `vision_todo` tags and resolve them (Grok or Claude):
make an `equations.json` where only those tags are `status:"conflict"`, run
`resolve.py … --manifest`, judge the strips, write verdicts, merge into
`auto_verdicts.json`, and `resolve.py … --apply` to emit `resolved.md`.

For a **Claude Code judge**, don't read `pages/*.png` one-by-one — the strips are
~2161px wide and image judges reject multi-image requests near ~2000px. Batch
them into tall single-image contact sheets first:

```bash
scripts/build_sheets.py Book_dir/reconciled 6      # 6 strips/sheet, tag in header
#   -> reconciled/sheets/sheet_NNN.png + sheets_meta/sheet_NNN.json
# read one sheet per call, then record each batch of decisions:
scripts/record_verdicts.py Book_dir/reconciled batch.json   # appends verdicts.json
```

`--apply` resolves only the tags in the file you pass and rebuilds `resolved.md`
from `merged.md`, so apply the **union** of `auto_verdicts.json` + `verdicts.json`.
`equations_resolved.json` is the complete contract; `resolved.md` only shows inline
`⚠ CONFLICT`→`✓ RESOLVED` for conflicts that align to the Marker backbone.

> Lesson from the Srednicki run: **Nougat is unreliable on long scanned books**
> (it dropped whole late chapters and truncates), so Marker is the authoritative
> backbone — most resolutions come out "marker". Nougat's arXiv-trained edge only
> showed up on the short clean arXiv sample.

## Storage / weight locations (configurable)

The venvs (~5 GB each) and open weights (~4 GB) are large and live **outside**
the repo. Defaults target the big Samsung disk; override per-machine:

| Var | Default | Purpose |
|-----|---------|---------|
| `OCR_STORAGE` | `/media/ernest/Samsung980ProPCI/ocr-compare` | base for venvs + weights |
| `OCR_VENV_DIR` | `$OCR_STORAGE/venvs` | venv-nougat / venv-marker / venv-resolve |
| `OCR_WEIGHTS_DIR` | `$OCR_STORAGE/weights` | downloaded open weights |
| `CUDA_INDEX` | `…/whl/cu130` | torch CUDA wheel index |

`run_ocr.sh` wires these into the model caches: Nougat → `TORCH_HOME` /
`NOUGAT_CHECKPOINT`, Marker → `MODEL_CACHE_DIR` (surya) + `HF_HOME`. Copy
`scripts/env.sh.example` → `scripts/env.sh` to persist overrides.

## For other agents / sessions

`combine.py` is **pure stdlib** — any session can run it on two existing OCR
outputs with no venv:

```bash
python3 combine.py nougat_out/foo.mmd marker_out/foo/foo.md outdir/
```

It writes `equations.json` (machine-readable: per-equation status, dropped-page
ranges, nougat repetition artifacts) for downstream agents to act on. See
[AGENTS.md](AGENTS.md) for conventions.
