# AGENTS.md — clawdj

## Scope

`Projects/clawdj/` contains the Mixxx-based AI DJ harness. Keep this directory
portable: no hardcoded music-library paths, no credentials, no committed caches.

## Structure

- `core-rust/` — Rust workspace for CLI + library.
- `mixxx-mapping/` — Mixxx XML/JS controller mapping.
- `analysis-python/` — offline feature extraction pipeline.
- `docs/` — architecture, setup, and operational notes.
- `planning/` — roadmap, atomic tasks, architecture decisions.

## Setup

- Read `README.md`, `docs/ARCHITECTURE.md`, and the relevant task in
  `planning/TASKS.md` before editing.
- Rust work happens inside `core-rust/`.
- Mixxx DB path comes from `CLAWDJ_MIXXX_DB` or defaults to the macOS sandbox
  location under `~/Library/Containers/org.mixxx.mixxx/.../Mixxx/mixxxdb.sqlite`.

## Common Commands

- Build: `cd Projects/clawdj/core-rust && cargo build --workspace`
- Test: `cd Projects/clawdj/core-rust && cargo test --workspace`
- Lint: `cd Projects/clawdj/core-rust && cargo clippy --workspace --all-targets -- -D warnings`
- Format: `cd Projects/clawdj/core-rust && cargo fmt --all`
- Live MIDI probe: `cd Projects/clawdj/core-rust && CLAWDJ_LIVE=1 cargo test -p clawdj --test live_midi -- --nocapture`

## Conventions

- Branch from `feat/clawdj-mixxx-harness` using `feat/`, `fix/`, `chore/`, or
  `experiment/` prefixes.
- Update `PROGRESS.md` when work completes or when leaving the tree in a useful
  partial state.
- Queue writes must be limited to Mixxx `Playlists` / `PlaylistTracks` rows owned
  by `__clawdj_queue`; never modify `library` or `track_locations`.

## Do Not Commit

- Generated audio analysis caches, SQLite copies, logs, screenshots, or music.
- Build artifacts such as `target/`.
- Any local private music paths or account-like identifiers.

## Completion Signal

1. `cargo fmt --all`
2. `cargo clippy --workspace --all-targets -- -D warnings`
3. `cargo test --workspace`
4. Update `PROGRESS.md`
