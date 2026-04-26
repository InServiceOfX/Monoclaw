# Mixxx integration: research + decision

## What Mixxx exposes today

Mixxx has a unified internal API called the **Control system** — every knob,
button, slider, deck, EQ, effect is a `(group, key)` pair you can read and
write. Examples:

| Group        | Key            | Type | Description              |
|--------------|----------------|------|--------------------------|
| `[Channel1]` | `play`         | bool | Deck 1 play/pause        |
| `[Channel1]` | `rate`         | -1..1| Pitch fader              |
| `[Channel1]` | `bpm`          | float| Current effective BPM    |
| `[Channel1]` | `playposition` | 0..1 | Relative play position   |
| `[Channel1]` | `beat_active`  | bool | True on a beat           |
| `[EqualizerRack1_[Channel1]_Effect1]` | `parameter1` | 0..1 | Low EQ |
| `[Master]`   | `crossfader`   | -1..1| Crossfader position      |
| `[Library]`  | `MoveTrack`    | rel  | Browse library           |

Source: <https://github.com/mixxxdj/mixxx/wiki/MixxxControls>

The Control system is reachable from:

1. **GUI** (the user clicking).
2. **MIDI / HID controller mappings** — XML mapping + accompanying JavaScript
   that runs inside Mixxx's `QJSEngine` (Qt's JS sandbox, ES7-ish, sample-rate
   timers via `engine.beginTimer`). This is the **primary scriptable surface**.
3. **OSC client (output only, unmerged branch)** — see "OSC" below.
4. **Keyboard mappings** (limited).

There is **no built-in TCP/HTTP/IPC API**. There is no "headless" Python or
JavaScript runner that talks to the Control system from outside Mixxx. You can
launch Mixxx with command-line flags (`--developer`, `--debug-assertions`, etc.)
but those don't take dynamic commands.

## The decision: virtual-MIDI bridge

We make the OS expose a virtual MIDI input port; we point Mixxx's
"controllers" preferences at it; we ship a controller mapping
(`clawdj.midi.xml` + `clawdj.scripts.js`) that knows how to interpret messages
from clawdj-core. Then any process that can write MIDI bytes can drive Mixxx.

Pros:
- Officially supported, stable interface.
- Zero patches to Mixxx itself (works against upstream stable releases).
- Same code path on macOS and Linux.
- The JS side runs *inside Mixxx* with low-latency access to the Control
  system, so timing-critical ops (EQ-kill on the beat, scratch motions) live
  there.

Cons:
- 7-bit values for raw MIDI CC (we use 14-bit CC pairs or pre-scaled JS lookups
  where precision matters).
- We have to invent and document our own command set.

### macOS — virtual MIDI

The OS ships an "IAC Driver" virtual MIDI bus. User enables it once in
Audio MIDI Setup → MIDI Studio → IAC Driver → "Device is online". We name a
bus `clawdj`. Mixxx sees it as `IAC Driver clawdj`. Our Rust core uses the
`midir` crate; on macOS `midir` can also create its *own* virtual port via
CoreMIDI without IAC, which is even cleaner.

### Linux — virtual MIDI

Two equivalent options:

- `snd-virmidi` kernel module (modprobe) → `hw:Virtual,0` etc.
- ALSA sequencer client created by `midir` directly — preferred (no root).

JACK users get `a2jmidid` for free.

## The OSC story (read-only state)

There is an old PR / fork that adds an OSC *client* to Mixxx. It only sends
state outward (which deck is playing, position, title, duration, volume). It
does **not** accept inbound OSC. It's not in mainline.

For state feedback we will:

1. Try the OSC fork **if** the user has built that branch locally.
2. Otherwise: poll Mixxx's running state via a **back-channel MIDI feedback
   mapping**. In Mixxx's JS we register `engine.connectControl("[Channel1]",
   "playposition", emitOurMidi)` which sends MIDI back out (to a second virtual
   port) so clawdj-core hears every position update without polling.

Decision: **MIDI feedback bus is the path of least resistance.** We avoid
custom Mixxx builds.

## Lyrics / transitions

Mixxx's library can store and display LRC files. We will:

- Look for `track.lrc` next to the audio file first.
- Fall back to scraping (`syncedlyrics` Python pkg, or LRCLIB API).
- Last resort: run whisper.cpp locally to time-align.

We store the synchronized lines in our own SQLite (`lyrics` table) — Mixxx
doesn't need to render them; the agent reads them to find a-cappella gaps,
hooks, and transition opportunities ("transition on the line `'one-two...'`
which falls on bar 32 beat 1").

## Why not other DJ apps?

| App                 | Scriptable? | FOSS? | Cross-plat? | Verdict |
|---------------------|-------------|-------|-------------|---------|
| Mixxx               | Yes (MIDI/JS) | GPL  | Mac+Lin+Win | ✅ |
| Rekordbox           | No (closed)   | No   | Mac/Win     | ❌ |
| Serato              | No (DVS only) | No   | Mac/Win     | ❌ |
| Traktor Pro         | Limited       | No   | Mac/Win     | ❌ |
| VirtualDJ           | Some scripts  | No   | Mac/Win     | ❌ |
| `nodejs-mix-tools`  | not a DJ app  | -    | -           | n/a |

There is no standalone "mlxxx" CLI/JS DJ tool that I can find — the user
likely meant Mixxx.

## What about MLX (Apple's `mlx` ML framework)?

The user's message says "powered using mlxxx". On second read this almost
certainly means **Mixxx**. MLX (Apple's `ml-explore/mlx`) is unrelated to DJing,
though it could later power local lyric/embedding analysis on Apple Silicon.
**Decision:** confirm with Ernest if he meant something else, but proceed with
Mixxx as the working assumption (matches the "live mix mp3/aac" story
perfectly).

## Open questions to confirm with Ernest

1. Did "mlxxx" mean **Mixxx**? (95% confidence yes.)
2. Are the AAC files DRM-free `.m4a` exports from Apple Music, or protected
   `.m4p`? Mixxx cannot decode protected AAC.
3. Do we want stems (DJ.com / Mixxx 2.5 stem support) or stay 2-deck classic?
4. MIDI/HID hardware controller in the loop too, or 100% software?
