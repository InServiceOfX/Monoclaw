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
  run_ocr.sh            run marker+nougat on a PDF, then reconcile
  _paths.sh             shared env/path resolution (storage, weights, CUDA)
  env.sh.example        copy to env.sh to override paths locally
samples/sample.pdf      10-pg arXiv test paper
examples/               committed reference outputs (no GPU needed to inspect)
```

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
