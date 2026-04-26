# clawdj — AI-driven live DJ harness on top of Mixxx

**Status:** planning · branch `feat/clawdj-mixxx-harness` · private (Monoclaw)
**Owner:** Ernest + Grimlock (OpenClaw main agent)
**Started:** 2026-04-25

> Live-mix hip-hop (and beyond) collaboratively: human + AI agent harness driving
> Mixxx via a virtual MIDI bridge. Cross-platform: macOS + Linux.

## TL;DR

- **DJ engine:** [Mixxx](https://mixxx.org) — open-source, scriptable, GPL.
- **Why Mixxx:** rich `[ControlGroup,key]` API, MIDI controller mappings, FOSS, runs on Mac + Linux.
- **Integration:** virtual MIDI port → Mixxx controller mapping (XML+JS) → Mixxx
  control surface. Any language that can send MIDI bytes can drive Mixxx.
- **Stack:**
  - `clawdj-core` (Rust, `midir` crate) — CLI + library: load tracks, send
    transport/EQ/crossfade commands.
  - `clawdj-analysis` (Python, `librosa` + `essentia`) — offline pre-analysis:
    BPM, key (Camelot), energy, beat grid, breakdown/drop detection, lyric
    timestamps. Cached to SQLite.
  - `clawdj-mapping` (Mixxx XML+JS) — translates our virtual MIDI events into
    Mixxx engine controls.
  - **Harness brain** — OpenClaw agent (Grimlock) for high-level set planning and
    live banter; sub-agents (Codex / Claude Code) implement specific tasks
    listed in `planning/TASKS.md`.

## Why not just use Mixxx's auto-DJ?

Mixxx auto-DJ is a fade timer. We want:

1. Harmonic mixing (Camelot wheel-aware transitions).
2. Phrase-aware beat-matching (drop into the next track on bar 8/16/32).
3. Lyric-aware transitions (use a known a-cappella moment as a transition cue).
4. Vibe steering via natural language ("take it darker", "build energy", "keep it
   '94 boom-bap").
5. Real-time human override — the human always has final say.

## Repo layout (this folder)

```
Projects/clawdj/
├── README.md               (you are here)
├── docs/
│   ├── ARCHITECTURE.md     (system diagram + data flow)
│   ├── MIXXX_INTEGRATION.md (how we drive Mixxx; MIDI/OSC research)
│   ├── ANALYSIS.md         (BPM/key/lyric/energy pipeline)
│   └── LIVE_LOOP.md        (real-time loop: chat ↔ harness ↔ Mixxx)
├── planning/
│   ├── ROADMAP.md          (milestones M0–M5)
│   ├── TASKS.md            (atomic tasks, sub-agent ready)
│   └── DECISIONS.md        (ADR-style log)
├── research/
│   ├── mixxx-controls.md   (catalog of [ControlGroup,key] we need)
│   └── prior-art.md        (similar projects, papers)
├── mixxx-mapping/          (XML + JS for our virtual MIDI controller)
├── core-rust/              (Rust CLI/lib, `midir`-based)
├── analysis-python/        (offline analysis, JSON/SQLite output)
└── examples/               (sample sets, lyric files, test mixes)
```

## Quick links

- 🗺️ Roadmap: [`planning/ROADMAP.md`](planning/ROADMAP.md)
- ✅ Pickable tasks: [`planning/TASKS.md`](planning/TASKS.md)
- 🏛️ Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- 🎛️ Mixxx integration deep-dive: [`docs/MIXXX_INTEGRATION.md`](docs/MIXXX_INTEGRATION.md)
- 🧠 Live loop: [`docs/LIVE_LOOP.md`](docs/LIVE_LOOP.md)
- 🎼 Analysis pipeline: [`docs/ANALYSIS.md`](docs/ANALYSIS.md)

## Public-vs-private

Monoclaw is **private**. Once `clawdj-core` is stable and free of any local-path
or personal-music-library coupling, fork a clean `clawdj` public repo under
`InServiceOfX/` for build-in-public. Until then: keep music paths, lyric dumps,
and any account/credential references *out of code* — read from
`~/.config/clawdj/config.toml` only.

## License posture

- Core code: **GPL-3.0** (matches Mixxx; we link conceptually + ship a Mixxx
  mapping, plus we may want to upstream improvements).
- Mappings: GPL-2+/MIT-style as Mixxx accepts.
- Analysis caches & user libraries: never committed.
