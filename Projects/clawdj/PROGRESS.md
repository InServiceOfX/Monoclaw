# PROGRESS.md — clawdj

## Completed
| Item | Status | Notes |
|------|--------|-------|
| Planning scaffold + architecture docs | ✅ | README, architecture, roadmap, and task breakdown added on `feat/clawdj-mixxx-harness`. |
| Rust core skeleton + queue bootstrap | ✅ | Added `core-rust/` workspace with `clawdj` lib + `clawdj` CLI, MIDI command dispatch, Mixxx queue bootstrap, and automated tests. |

## In Progress
| Item | Branch | Status | Notes |
|------|--------|--------|-------|
| End-to-end Mixxx manual validation | feat/clawdj-core-rust-skeleton | 🔄 | Automated checks pass; T0.5 still needs Mixxx running with the mapping enabled. |

## Not Started
| Item | Priority | Notes |
|------|----------|-------|
| Analysis pipeline | medium | Blocked on M1 tasks after Rust skeleton. |

## Last Worked On
**2026-04-26** — Completed T0.4/T0.4b on `feat/clawdj-core-rust-skeleton`:
created the Rust workspace, added `setup` / `load` / `cmd` / `queue`
subcommands, implemented Mixxx queue writes limited to `Playlists` and
`PlaylistTracks`, and verified with `cargo fmt`, `cargo test`, `cargo clippy`,
plus a temp-DB CLI smoke test.
