# Monoclaw Monorepo

Multi-lang hub (Rust/Python/C++/JavaScript).

Monoclaw is intended to be a public demonstration repo for local,
semi-autonomous coding workflows. Some tools may read private local data at
runtime, but private data must not be committed or quoted in public artifacts.
See [PRIVACY.md](PRIVACY.md) before working with private local files.

## Structure
- **Rust/**: Cargo crates
- **Python/**: Poetry pkgs
- **Cpp/**: CMake projects
- **JavaScript/**: Static/web tools (HTML, JS, CSS)
- **examples/**: Demos
- **shared/**: Protos/FFI

## Usage
`git checkout -b feat/xxx`
Build per-lang.
