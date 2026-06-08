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
scripts/run_ocr.sh PDF [--out DIR] [--only marker|nougat] [--no-reconcile]
# pure-stdlib reconcile only, no venv:
python3 combine.py NOUGAT.mmd MARKER.md OUTDIR/
```

## Hard assumptions

- **NVIDIA GPU + CUDA is present.** Scripts always install the CUDA torch build
  (`CUDA_INDEX`, default cu130), never CPU. Don't add CPU fallbacks.
- **Open weights run locally**, downloaded once to `OCR_WEIGHTS_DIR`.
- **8 GB VRAM**: marker and nougat run **sequentially**, not concurrently.

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
