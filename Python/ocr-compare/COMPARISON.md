# Nougat vs Marker — PDF→LaTeX for math/physics papers (no .tex source)

Test doc: `2602.12176v1.pdf` — "Single-minus gluon tree amplitudes are nonzero" (10 pp, dense spinor-helicity math).
Ground truth: `arXiv-2602.12176v1/SMGA.tex` (exact v1 source).
Hardware: RTX 3070 Laptop, 8 GB VRAM. Run sequentially (8 GB can't hold both).

## Per-equation accuracy (where both captured the eq) — NOUGAT WINS on this arXiv sample
| Eq | Reference (SMGA.tex) | Nougat | Marker |
|----|----------------------|--------|--------|
| (2) | `|i]=\tilde\lambda_i=\omega_i(1,\tilde z_i)` | ✓ correct `|i]` | ✗ `|i\rangle` (wrong bracket) |
| (3) | `\epsilon_{\alpha\beta}\lambda_i^\alpha\lambda_j^\beta` | ✓ `\lambda_i^\alpha\lambda_j^\beta` | ✗ `\lambda_i^\alpha\lambda_i^\beta` (i should be j) |
| (5) | `\langle ij\rangle=z_{ij}, [ij]=\omega_i\omega_j\tilde z_{ij}` | ✓ correct | ✗ `z_{ii}` |
Nougat is the arXiv-trained specialist; it nails spinor indices/brackets here.

## Completeness & reliability — MARKER WINS decisively
- **Nougat DROPPED page 4 entirely** ("Skipping page 4 due to repetitions") → eqs ~20–32 LOST.
- **Nougat repeated** eqs 10–17 multiple times (tag{10}×4, tag{12}×4, tag{13}×4, tag{14}×4 …) — classic repetition/hallucination failure.
- **Marker captured all 10 pages** including the key formula (39) `A=1/2^{n-2} ∏(sg+sg)` and the whole page-4 derivation. 81 display-math blocks vs Nougat's 49 (many of Nougat's being duplicates).
- Marker downside: inconsistent equation numbering (often plain `(N)` text or none, vs Nougat's clean `\tag{N}`).

## Speed (this run: single 10-pg doc, 8 GB GPU)
- Nougat: ~58 s.  Marker: ~433 s.
- (Literature says Marker ~10× faster — that's batch mode on big GPUs. For one small doc on a small GPU, Marker's multi-model pipeline + first-run overhead lost.)

## Verdict for "parse math/physics PDF, no .tex, for study"
- **Marker = default workhorse**: never silently drops content; complete & robust. Then verify/patch equations against the PDF (you already do this per SOUL.md).
- **Nougat = per-equation cross-check** on clean arXiv pages where index correctness is critical — but UNRELIABLE (drops pages, repeats). Never trust it without checking page coverage.
- **True SOTA** (Chandra 9B / olmOCR-2 7B) would likely beat both but needs >8 GB VRAM → use Datalab/AI2 cloud API for those.

## Reproduce
```bash
# One command runs both models (sequentially) + reconciles:
scripts/setup_envs.sh                       # build venvs (CUDA torch), once
scripts/run_ocr.sh samples/sample.pdf       # -> out/sample/{marker_out,nougat_out,reconciled}
```
Under the hood (the pins below are load-bearing for nougat-ocr 0.1.17):
```bash
# Marker:  marker_single sample.pdf --output_dir marker_out --output_format markdown
# Nougat (transformers==4.38.2 albumentations==1.3.1 pypdfium2==4.30.0):
#   PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True nougat sample.pdf -o nougat_out --markdown
```
