# Monoclaw Monorepo

Multi-lang hub (Rust/Python/C++/JavaScript).

Monoclaw is intended to be a public demonstration repo for local,
semi-autonomous coding workflows. Some tools may read private local data at
runtime, but private data must not be committed or quoted in public artifacts.
See [PRIVACY.md](PRIVACY.md) before working with private local files.

## Structure
- **Rust/**: Cargo crates
- **Python/**: Poetry pkgs
  - **Python/ocr-compare/**: local Nougat+Marker PDF→LaTeX OCR, reconciled (GPU)
- **Cpp/**: CMake projects
- **JavaScript/**: Static/web tools (HTML, JS, CSS)
- **examples/**: Demos
- **shared/**: Protos/FFI

## Usage
`git checkout -b feat/xxx`
Build per-lang.

## Prompt-Driven Development

To adopt PDD for a new project, paste this once into the AI agent:

```text
Set this project up to use Prompt-Driven Development. I’ll describe the product
in ordinary language; preserve my requests and handle the PDD mechanics for me.
```

Then describe the product normally. See
[`docs/pdd/PDD_NEW_PROJECT_PROMPT.md`](docs/pdd/PDD_NEW_PROJECT_PROMPT.md) for
the one-page handoff and
[`docs/pdd/PDD_START_HERE.md`](docs/pdd/PDD_START_HERE.md) for the beginner
explanation. After setup, read
[`docs/pdd/PDD_AFTER_SETUP.md`](docs/pdd/PDD_AFTER_SETUP.md) for the practical
meaning of “stay in prompt space”: the human keeps talking normally while the
agent maintains versioned `.prompt` source, stories, tests, and generated code.
For why the collective prompt suite maps to the project—and why a C++ `.h` and
`.cpp` may form one logical regeneration unit—see
[`docs/pdd/PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md`](docs/pdd/PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md).
