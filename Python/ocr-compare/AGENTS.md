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
# pure-stdlib reconcile only, no venv:
python3 combine.py NOUGAT.mmd MARKER.md OUTDIR/
# triage book-scale conflicts before vision-resolving:
scripts/triage_conflicts.py reconciled/equations.json reconciled/
# vision-resolve the tier4 conflicts (render strips, then judge — see below):
venvs/venv-resolve/bin/python resolve.py --pdf BOOK.pdf --eqs tier4.json \
    --merged reconciled/merged.md --outdir reconciled/ --manifest
```

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
  `marker_chunked.py` / `run_ocr_large.sh` for books. Nougat is **unreliable on
  long scanned books** (drops whole chapters, truncates) — Marker is the backbone.

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
