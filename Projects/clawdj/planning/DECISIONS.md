# Decisions log (ADR-lite)

Each entry: short title, date, context, decision, consequences.

---

### 2026-04-25 · Use Mixxx, not a custom JS DJ engine

**Context.** User asked for an mlxxx-powered DJ. Web research turned up no
"mlxxx" CLI/JS DJ tool; the only fit is **Mixxx** — open-source, scriptable,
cross-platform, AAC/MP3-capable. Confidence ~95%; flagged for confirmation.

**Decision.** Build atop Mixxx 2.5 stable.

**Consequences.** GPL-3 license posture for our code. We inherit Mixxx's audio
engine, time-stretching, beatgrids, hardware-controller plumbing for free.

---

### 2026-04-25 · Drive Mixxx via virtual MIDI, not patches/forks

**Context.** Mixxx's only sanctioned external write API is its MIDI/HID
controller mapping system (XML + JS in QJSEngine). The OSC client is
unmerged + output-only. There is no IPC API.

**Decision.** Create a virtual MIDI port (CoreMIDI/`midir` on macOS,
ALSA/`midir` on Linux) plus a custom Mixxx mapping (`mixxx-mapping/`) that
interprets our messages.

**Consequences.** Works on stock Mixxx. Hard real-time recipes live inside
Mixxx's JS sandbox, not in our Rust code — IPC happens at the *intent* level.

---

### 2026-04-25 · Rust core, Python sidecar for analysis

**Context.** Ernest prefers Rust. Music analysis libraries (essentia, madmom,
librosa, whisper) are richest in Python.

**Decision.** Rust = library DB, planner, MIDI bridge, scheduler, CLI.
Python = offline analyzer subprocess only. JSON over stdio is the contract.

**Consequences.** Two language toolchains. Rust ships fast; Python is
gated to offline batch work so its slowness never hits the live loop. Future
port of analysis to Rust (`aubio-rs` etc.) is non-breaking — same JSON
contract.

---

### 2026-04-25 · Repo: Monoclaw private branch first, public split later

**Context.** User wants build-in-public, but past mistakes hardcoded private
info. Music libraries are also personal.

**Decision.** Develop on `feat/clawdj-mixxx-harness` in private Monoclaw.
Plan a clean public split (`InServiceOfX/clawdj`) once a `lint-no-private-paths`
hook is enforced and config (paths, library locations) is fully externalized.

**Consequences.** Slower public release, much less risk of accidentally
publishing music-library or account state.

---

### 2026-04-25 · State feedback over a second virtual MIDI port

**Context.** We need to know "which deck is playing, what's the position,
what's the BPM" without polling Mixxx via a custom build (OSC fork is
unmaintained mainline).

**Decision.** A second virtual MIDI port (`clawdj-feedback`) into which our
mapping JS emits status messages. Rust core listens.

**Consequences.** No custom Mixxx build needed; ~10 ms feedback granularity
which is fine for our scheduler (we only need beat-precise).

---

### TBD — `[Open]` Stems vs 2-deck classic for v1

Pending Ernest input. Recommend: classic 2-deck for M0–M3, stems in M5+.

---

### TBD — `[Open]` Whisper local vs LRCLIB for lyrics

Pending. Recommend: LRC file → LRCLIB API → whisper.cpp local, in that order.

---

### Template for new entries

```
### YYYY-MM-DD · short title

**Context.**

**Decision.**

**Consequences.**
```
