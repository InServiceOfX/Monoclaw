# Personal Files — agent instructions

Native Rust/GTK 3 Ubuntu desktop application. Work on feature branches; never
commit to master/main. The current branch is `feat/personal-files`.

Read `docs/PRODUCT_INTENT.md`, `user_stories/story__personal_places.md`, the
affected `.prompt` source, and `PROGRESS.md` before changing behavior. The repo's
mandatory PDD playbooks live at `../../docs/pdd/`. User corrections are intent
input; maintain prompt meaning, implementation, and independent acceptance tests
together. Do not require another PDD trigger phrase or another approval of the
already accepted first-version meaning.

- Rust edition 2021; dependencies are gtk-rs GTK 3, serde, serde_json.
- `./build.sh` builds release into the user cache, never the source tree.
- `./launch.sh [PATH]` runs the cached build. After source edits, run build.sh
  explicitly before launch.sh so the cache is fresh.
- `./install.sh` installs the current release for the current Ubuntu user.
- `cargo fmt --check`; `cargo clippy --locked --all-targets -- -D warnings`;
  `cargo test --locked` for deterministic acceptance.
- `cargo test --locked desktop_story -- --ignored --nocapture` explicitly runs
  real GTK tests. Use one GUI test thread; GTK belongs to its initial thread.
  Missing display must fail this opt-in test, not count as a pass.
- See README for local GTK development metadata and CARGO_TARGET_DIR exports.
- Scans stay on a single worker, GTK stays on main thread. Ignore stale results.
- Runtime history and preferences stay outside Git. Do not read user document
  contents to choose themes. Preserve symlink aliases in displayed/copied paths.
- Never hand-edit generated story contracts. The first iteration has a reviewed
  human story and behavioral tests; automated contract generation, semantic
  detection and PDD sync were not completed and must not be claimed as passed.
- Never stage binaries, target/, runtime JSON, screenshots, caches or build logs.
- Python was a temporary reference, explicitly retired after Rust parity. Do not
  restore a second maintained Python application.

Update `PROGRESS.md` and verification evidence after material work. The human
owns product meaning; the agent owns paths, prompt wiring, implementation and
verification mechanics.
