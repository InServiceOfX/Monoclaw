# LATER — pick up here

Living crib-sheet so Grimlock (future me) and Ernest can resume the clawdj
project at home / next session without rereading the whole tree.

## Last touched

**2026-04-25 21:54 PDT** — Ernest about to put laptop to sleep.

## What's done

- [x] Branch `feat/clawdj-mixxx-harness` on Monoclaw (private).
- [x] Full planning + research docs in `Projects/clawdj/`.
- [x] All 4 open questions answered (Mixxx, .m4a, 2-deck, software-only).
- [x] Mixxx mapping XML + JS written.
- [x] Mapping **copied into the Mixxx sandbox controllers/ dir.**
- [x] `scripts/install-mapping-macos.sh` so the install is reproducible.
- [x] MEMORY.md updated.

## What's NOT done

- [ ] Inside Mixxx: Preferences → Controllers → enable IAC Driver clawdj
      and load the `clawdj` mapping. (User-facing step; can't be scripted
      without UI automation.)
- [ ] Smoke test: send a MIDI message from `swift` or a tiny Rust binary to
      `IAC Driver clawdj` and confirm Mixxx logs the inbound event.
- [ ] **T0.4** — Rust core skeleton (`clawdj` binary with `setup` and `load`
      subcommands). Spawn cmd is below.

## Resume checklist (in order)

1. Open Mixxx. Preferences → Controllers → 'IAC Driver clawdj' →
   Enabled ✓ → Load Mapping → 'clawdj' → Apply. Watch the Mixxx log
   (`~/Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/mixxx.log`)
   for the line `[clawdj] init: clawdj mapping loaded`.

2. **Manual smoke test (no Rust yet) — sends a Note On to play deck 1:**
   ```bash
   # First, load any track into deck 1 manually (drag-drop in Mixxx).
   # Then send a play command from terminal:
   python3 - <<'PY'
   import mido
   names = mido.get_output_names()
   port = next(n for n in names if 'clawdj' in n)
   out = mido.open_output(port)
   # Channel 16 (=15 zero-indexed), note 0x02 = play deck 1
   out.send(mido.Message('note_on', channel=15, note=0x02, velocity=127))
   PY
   ```
   `pip install mido python-rtmidi` first if needed.

3. Verify the feedback bus: while a deck plays, `python3 -c "import mido;
   p=mido.open_input(next(n for n in mido.get_input_names() if 'clawdj' in n));
   [print(m) for m in p]"` should print beat ticks (note 0x40/0x41 ch16).

4. Spawn Codex to build the Rust skeleton. Spawn command:

   ```
   cd ~/.openclaw/workspace/repos/Monoclaw && \
   codex --pty "
     Read Projects/clawdj/README.md and Projects/clawdj/docs/ARCHITECTURE.md
     and Projects/clawdj/planning/TASKS.md (sections T0.4 and T0.4b only).

     Implement task T0.4 (core-rust-skeleton):
     - cd Projects/clawdj/core-rust
     - Create a Cargo workspace with two crates:
         clawdj/         (library)
         clawdj-cli/     (binary that depends on clawdj)
     - Dependencies: midir, clap (derive), anyhow, serde, serde_json, tracing,
       tracing-subscriber, rusqlite (for T0.4b), once_cell.
     - Edition 2024, MSRV 1.79+.
     - Implement subcommands:
         clawdj setup
             Lists all CoreMIDI/ALSA ports and prints whether 'clawdj' is
             present; exits 0 on success.
         clawdj load <deck:1|2> <track_id:int>
             Sends the appropriate Note On (channel 16, note 0x00 for deck 1
             or 0x01 for deck 2) to the 'clawdj' MIDI output. Track-id
             plumbing for now is just logged; T0.4b will add the queue insert.
         clawdj cmd <json>
             Parses {op, deck, ...} JSON and dispatches accordingly. Supports
             ops: load, play, pause, cue, crossfade.
     - Tests: a unit test that constructs the MIDI byte sequence for each op
       (no live MIDI) and an integration test gated on env CLAWDJ_LIVE=1 that
       opens the real port if present.
     - rustfmt + clippy clean. README in core-rust/ with build instructions.

     Then T0.4b (clawdj-queue-bootstrap):
     - clawdj queue init  → opens Mixxx's mixxxdb.sqlite (path from
       env CLAWDJ_MIXXX_DB or default macOS sandbox path), creates hidden
       Playlist '__clawdj_queue' if missing.
     - clawdj queue set <deck> <track_id> → upserts row 0 of __clawdj_queue.
     - clawdj queue clear.
     - SQLite WAL mode + busy_timeout 5000ms; never write to library or
       track_locations; only Playlists / PlaylistTracks rows we own.
     - Test against a temp copy of mixxxdb.sqlite (do NOT use the live one).

     Commit on a sub-branch feat/clawdj-core-rust-skeleton, push, open PR
     against feat/clawdj-mixxx-harness.
   "
   ```

5. After Codex finishes, do an end-to-end demo:
   - Pick a known track_id from `mixxxdb.sqlite library` table (any of the
     1,033 tracks).
   - `clawdj queue set 1 <track_id>` then `clawdj load 1` then
     `clawdj cmd '{"op":"play","deck":1}'`.
   - Mixxx should load and start playing the track. 🎉

## Known things to watch out for

- **Mixxx file watch on the controllers folder is per-file.** If you edit
  `clawdj.scripts.js`, Mixxx reloads it instantly — but XML changes need
  re-loading the mapping in Preferences → Apply.

- **Sandbox-clawdj.scripts.js is NOT a symlink.** `cp` copied the file, so
  edits in the repo do NOT propagate until you re-run
  `scripts/install-mapping-macos.sh`. Consider symlinking later:
  `ln -s "$REPO/.../clawdj.scripts.js" "$SANDBOX/.../clawdj.scripts.js"` —
  but the sandbox may reject the symlink target. Test before committing to
  this.

- **`MoveTrack -1` loop** in `_loadFromQueue` is brute-force; will be
  replaced when we figure out the proper sidebar focus API.

- **Mixxx DB is held by Mixxx with WAL.** Our writes use the same WAL with
  busy_timeout. Run while Mixxx is alive should be fine; if locks get nasty
  fall back to writing only when Mixxx is closed.

## Conversational state for Grimlock to remember

- Ernest's laptop is the M5 MacBook Pro.
- He likes hip-hop, especially West Coast (313 tracks of it).
- He prefers Rust > Python > C++; "build in public" is a goal, but private
  first because of past mistakes.
- He has SpaceX Leetcode prep, grokicad, Tesla/xAI/SpaceX career goals as
  *higher* priority than this — clawdj is a side project he wants me to
  keep moving on autonomously while we focus on the big rocks together.
- This project should NOT consume his focused-work time. I drive it; he
  approves milestones.
