# PROGRESS.md — Srednicki Cadabra2 Chapter Status

## Completed Chapters

| Chapter | Topic | Script | Export/PDF | Notes |
|---------|-------|--------|------------|-------|
| Ch.34 | Left/Right Weyl Spinors | ✅ `ch34_left_right_spinors.py` | ✅ | Base chapter — metric (+,-,-,-), ε^{12}=+1 established |
| Ch.35 | σ-matrix Algebra | ✅ `ch35_sigma_algebra.py` | ✅ | σ^μ completeness, trace identities |
| Ch.36 | Weyl Lagrangian | ✅ `ch36_weyl_lagrangian.py` | ✅ | EOM, kinetic term, mass term |
| Ch.60 | Spinor Helicity / MHV | ✅ `ch60_spinor_helicity.py` | — | Twistors, angle/square brackets, polarization vectors, Fierz; no export script yet |

## In Progress / Spawned

| Chapter | Topic | Branch | Status | Notes |
|---------|-------|--------|--------|-------|
| Ch.37 | Canonical Quantization of Spinor Fields I | `feat/srednicki-ch37` | 🔄 script exists, not verified complete | Anticommutation relations, mode expansion, basis spinors u^s v^s |
| Ch.38 | Spinor Technology | `feat/srednicki-ch38` | 🔄 script exists, not verified complete | σ^μ completeness, trace identities, Fierz, van der Waerden index gymnastics |

## Not Started

| Chapter | Topic | Priority | Notes |
|---------|-------|----------|-------|
| Ch.37 export | LaTeX export for Ch.37 | high | needs `ch37_export_latex.py` |
| Ch.38 export | LaTeX export for Ch.38 | high | needs `ch38_export_latex.py` |
| Ch.48 | Spinors for Massless Particles | high | prerequisite for full spinor-helicity |
| Ch.60 export | LaTeX export for Ch.60 | medium | `ch60_spinor_helicity.py` exists, export script missing |
| BCFW recursion | On-shell recursion | low | after Ch.48 + Ch.60 are solid |

## Last Worked On

**2026-03-24** — Added `AGENTS.md` and `PROGRESS.md`. Ch.37 and Ch.38 scripts
exist on `feat/srednicki-ch37`/`feat/srednicki-ch38` branches but completion
status of those scripts is unverified (spawned to sub-agent, not confirmed to
run cleanly). Next task: verify ch37 + ch38 scripts run without error in Docker,
write export scripts, then proceed to Ch.48.

## Notes / Caveats

- `ch36_weyl_lagrangian.aux/.out/.toc` are LaTeX build artifacts in the working
  tree — not committed, safe to delete or ignore
- `MHV_research_survey.md` is a research notes file — not a chapter script
- `pol_fix_patch.py` is a one-off utility patch — not part of the chapter sequence
- Ch.60 was done out of order (before Ch.37/38) as a preview of MHV machinery
