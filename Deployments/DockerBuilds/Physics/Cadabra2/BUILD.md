# Building cadabra2-ubuntu:24.04

This directory builds the `cadabra2-ubuntu:24.04` Docker image used for Cadabra2
symbolic physics computations (Srednicki QFT, spinor-helicity, MHV amplitudes).

---

## Quick Start

```bash
cd /path/to/Monoclaw/Deployments/DockerBuilds/Physics/Cadabra2
./build.sh
```

`./build.sh` will find the `docker_builder` binary, check prerequisites, and build.

Use `./build.sh --check` to verify everything is set up without triggering a build.

---

## Requirements

### Docker daemon

Must be running before building. `build.sh` checks this automatically.

### docker_builder binary

A Rust binary that wraps `docker build`. It lives in the
[InServiceOfX/RustLibraries](https://github.com/InServiceOfX/RustLibraries) repo
at `docker_builder/`.

**On this machine (Prop-dev/MS-7887):** The `InServiceOfX` repo is located at
`${HOME}/Prop/InServiceOfX/` as a sibling to the `Monoclaw` repo, following the
convention `../../../InServiceOfX/RustLibraries/...`. `build.sh` searches this
location automatically.

**On any other machine:** Do NOT assume any specific absolute path. The
`InServiceOfX` repo may be cloned or located anywhere. `build.sh` searches for
`docker_builder` in this order:

1. `$DOCKER_BUILDER` environment variable (if set and executable)
2. `docker_builder` or `docker_runner` anywhere on your `$PATH`
3. Relative to the script location (a heuristic — not guaranteed to exist)

If none of those find it, `build.sh` will tell you exactly what to do.

---

## Setting Up docker_builder (If build.sh Can't Find It)

```bash
# 1. Clone or locate InServiceOfX/RustLibraries
git clone git@github.com:InServiceOfX/RustLibraries.git
# (put it wherever you like — build.sh does not care about the parent path)

# 2. Build the Rust binary
cd RustLibraries/docker_builder
cargo build --release
# Result: target/debug/docker_builder  (or target/release/docker_builder)

# 3. Either put it on your PATH, or tell build.sh where it is:
export DOCKER_BUILDER=/path/to/RustLibraries/docker_builder/target/debug/docker_builder
./build.sh
```

---

## Files in this Directory

| File | Purpose |
|------|---------|
| `build_configuration.yml` | Input to `docker_builder` — names the image, lists Dockerfile components |
| `Dockerfile` | Layered Docker image definition (Ubuntu 24.04 + Cadabra2) |
| `docker-compose.yml` | (optional, for `docker compose`) |
| **`build.sh`** | **Recommended build entry point** — finds `docker_builder`, checks prereqs, builds |
| `run.sh` | Launcher for the built image (GUI, Jupyter, CLI) |

---

## Running the Built Image

After building:

```bash
./run.sh gui         # Cadabra2 GTK notebook (X11)
./run.sh jupyter     # JupyterLab at http://localhost:8888
./run.sh cli         # Bash shell inside container
./run.sh cli python3 /work/my_script.py  # Run a Python script
```

---

## What the Image Contains

- Ubuntu 24.04
- Cadabra2 (latest from GitHub)
- Python 3.x with numpy, scipy, pytest
- JupyterLab
- Cadabra2 Python bindings (`import cadabra2`)

The `Monoclaw` repo is mounted at `/Monoclaw` inside the container, and
the `notebooks/` directory (relative to this file) is mounted at `/work`.

---

## For Other OpenClaw Agents

If you are an OpenClaw agent on any machine and need to rebuild this image:

1. Read this file (`BUILD.md`) first
2. `cd` to this directory (wherever it is on the machine you are on)
3. Run `./build.sh --check`
4. If it says `docker_builder` not found:
   - Clone `git@github.com:InServiceOfX/RustLibraries.git` (anywhere you like)
   - `cd RustLibraries/docker_builder && cargo build --release`
   - `export DOCKER_BUILDER=/path/to/that/binary`
   - Re-run `./build.sh`
5. Never assume the `${HOME}/Prop/` directory structure — that is unique to
   the Prop-dev/MS-7885 setup. Use only relative or PATH-based references.

---

Last updated: 2026-04-07
