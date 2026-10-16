# Verification — first Ubuntu Rust iteration

The maintained app uses Rust 2021 with gtk-rs GTK 3. On this Ubuntu machine:
Rust 1.97.1, GTK runtime 3.24; Cargo.lock pins dependencies. Build artifacts are
outside the repository. The installed application requires no Python process.

## Behavioral evidence

- `cargo test --locked`: **15 acceptance tests passed**. They check path
  resolution, symlink aliases, Unicode/spaces, hidden and broken-link entries,
  missing/permission failures, all sort orders with folders first, actual POSIX
  shell round-trip quoting without command execution, restart persistence,
  0600 state, independent Recent/Frequent/Favorites, bounded history, corrupt
  and invalid state recovery, disconnected favorites, automatic themes and
  atomic-save failure preserving previous bytes.
- Explicit opt-in `cargo test --locked desktop_story -- --ignored --nocapture`:
  **1 real GTK test passed**, containing **15 interaction scenarios**: startup
  and hidden files; absolute/relative address-entry signals; star/sidebar
  activation; real desktop clipboard; context-menu copying; column sorting;
  row activation/file-path selection; failed navigation; back/forward/refresh;
  drag URI payload and favorite handler; skins and image validation; actual
  folder monitoring; stale scan rejection; fresh-window restart; clearing
  visits while retaining favorites. Fixtures and preferences are temporary.

The desktop test is deliberately ignored in ordinary cargo test and was run
separately on the real Ubuntu display. URI/drop handler coverage does not prove
every external file manager's physical mouse-driven drag behavior. Default
document opening is delegated to GIO and inspected; tests do not open real user
documents or assert all installed external applications work.

A window-only fixture screenshot was inspected locally; screenshots and test
logs are not committed. The installed application is intended for interactive
feedback and further iteration.

## Build and installation checks

`cargo fmt --check`, `cargo clippy --locked --all-targets -- -D warnings`,
Bash syntax checks, eight prompt/output mappings and three story links passed.
The installed Desktop Entry passed desktop-file-validate. The release binary is
a stripped native ELF linked only to installed system libraries (no /tmp or
Python dependency). Its hash matches the built release. The installed app was
opened at the requested Physics folder; the live process and saved successful
visit were confirmed. Build files are in the user cache, outside the repo.

## PDD evidence and limits

The exact original request was planned read-only, reviewed by the human and
approved. `intent apply` captured its immutable event/Product Intent and ran
architecture step 1, then was explicitly stopped during step 2 of 19 to bound
the provider workflow. Its local status was not marked as successfully applied.
Provider usage/cost at interruption was not reported and is not invented here.

The subsequent Rust correction was planned in the Rust project scope. The
agent authored and reviewed the final versioned prompts, architecture mapping,
human story and Rust port directly. PDD story inventory discovered the story and all three linked prompts. Its
Python-oriented regression inventory reports `missing`; the Rust behavioral
suite above was run explicitly and is not claimed as a PDD-emitted regression.

No machine-generated story contract, provider-backed semantic story detection,
or automated PDD sync was completed. Those layers are not counted as passing.
The temporary Python reference passed its 26 checks before the port; Rust's
own evidence above, rather than Python's results, establishes Rust parity.
