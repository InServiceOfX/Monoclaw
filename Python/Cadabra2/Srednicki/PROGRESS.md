# PROGRESS.md — Srednicki Cadabra2 Chapter Status

## Completed Chapters

| Chapter | Topic | Script | Export/PDF | Notes |
|---------|-------|--------|------------|-------|
| Ch.34 | Left/Right Weyl Spinors | ✅ `ch34_left_right_spinors.py` | ✅ | Base chapter — metric (+,-,-,-), ε^{12}=+1 established |
| Ch.35 | σ-matrix Algebra | ✅ `ch35_sigma_algebra.py` | ✅ | σ^μ completeness, trace identities |
| Ch.36 | Weyl Lagrangian | ✅ `ch36_weyl_lagrangian.py` | ✅ | EOM, kinetic term, mass term |
| Ch.60 | Spinor Helicity / MHV | ✅ `ch60_spinor_helicity.py` | — | Twistors, angle/square brackets, polarization vectors, Fierz; no export script yet |

## Completed Chapters (cont.)

| Chapter | Topic | Script | Export/PDF | Notes |
|---------|-------|--------|------------|-------|
| Ch.37 | Canonical Quantization of Spinor Fields I | ✅ `ch37_canonical_quantization.py` | ✅ | CARs, mode expansion, basis spinors u^s v^s, normal-ordered H, spin-statistics |
| Ch.38 | Spinor Technology | ✅ `ch38_spinor_technology.py` | ✅ | σ completeness, 2-trace, 4-trace (+2iε sign), index gymnastics, Fierz |

## Not Started

| Chapter | Topic | Priority | Notes |
|---------|-------|----------|-------|
| Ch.37 export | LaTeX export for Ch.37 | high | needs `ch37_export_latex.py` |
| Ch.38 export | LaTeX export for Ch.38 | high | needs `ch38_export_latex.py` |
| Ch.48 | Spinors for Massless Particles | high | prerequisite for full spinor-helicity |
| Ch.60 export | LaTeX export for Ch.60 | medium | `ch60_spinor_helicity.py` exists, export script missing |
| BCFW recursion | On-shell recursion | low | after Ch.48 + Ch.60 are solid |

## Last Worked On

**2026-03-27** — Verified ch37 + ch38 scripts run clean in `cadabra2-ubuntu:24.04` Docker.
Fixed bugs: ch37 `Ex()` free-index-sum crash (mode expansion), ch38 unavailable
`DiagonalMetric`/`EpsilonTensor` API calls, ch38 4-trace ε sign (correct: +2i for
Tr[σσ̄σσ̄] with mostly-plus metric). All 9 numerical checks pass. Wrote
`ch37_export_latex.py` and `ch38_export_latex.py`; produced 6-page PDFs for both
chapters. Committed to `feat/srednicki-ch37-ch38-breakdown`, pushed.
Next task: Ch.48 (spinors for massless particles).

## Notes / Caveats

- `ch36_weyl_lagrangian.aux/.out/.toc` are LaTeX build artifacts in the working
  tree — not committed, safe to delete or ignore
- `MHV_research_survey.md` is a research notes file — not a chapter script
- `pol_fix_patch.py` is a one-off utility patch — not part of the chapter sequence
- Ch.60 was done out of order (before Ch.37/38) as a preview of MHV machinery
