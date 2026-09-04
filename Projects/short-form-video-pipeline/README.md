# README — Short-Form Video Pipeline (HTML deck + OBS, single live take)

One sentence: build the whole visual side of a vertical STEM explainer as one
self-contained HTML file, record it live in one take with OBS (screen capture
of that file + your own narration), verify the HTML with Playwright before
you ever hit record — not a full video-editor pipeline.

Read `WORKFLOW.md` in this folder for the full writeup: the technique, the
exact OBS settings that worked, every bug actually hit while building this
(and the fix), and an honest time-cost accounting for whether this is
actually faster than a conventional record-then-edit workflow.

Origin: built 2026-07-04 while producing Episode 1 of Ernest's "Attention Is
All You Need" series (`InServiceOfX/CUDALibraries/CuLLM/Documents/AttentionSeries.md`).
Generalizes past that one series — anyone producing a short, vertical,
equation/diagram-heavy explainer video can reuse this pattern.

## Related: virality structure (hook / retention / engagement)

This folder is **how to shoot** (HTML deck + OBS). For **what to put in the
video so it earns distribution** (Noe Murillo Part 1 fundamentals — hook,
retention, “viral tokens”), use the shared skill:

- `shared/openclaw/skills/short-form-viral-content/SKILL.md`
- Framework notes: `shared/openclaw/skills/short-form-viral-content/references/noe-murillo-pt1-framework.md`
- Source archive: `Data/Public/Videos/TikTok/NoeMurillo_How-to-be-a-Successful-Content-Creator-pt1_7670717441508429070.md`

Grok also loads the same skill from `~/.grok/skills/short-form-viral-content/`
(`/short-form-viral-content`).

## Related: automated faceless assembly (Rust pipeline)

This folder is **how to shoot** with your own narration on camera-less decks.
For fully automated faceless videos — TTS voiceover, stock b-roll, burned-in
captions — use the Rust pipeline instead:

- Crate: `Rust/shortform-video/` (see its README for CLI and config)
- Skill: `shared/openclaw/skills/short-form-video-assembly/SKILL.md`
- Provenance: `docs/shortform/MONEYPRINTERTURBO_ASSESSMENT.md`

Structure (viral-content skill) → then either **shoot** (this folder) or
**assemble** (`shortform-video`).
