# Building cadabra2-ubuntu:24.04

This directory builds the `cadabra2-ubuntu:24.04` Docker image used for Cadabra2
symbolic physics computations (Srednicki QFT, spinor-helicity, MHV amplitudes).

---

## Quick Start

```bash
cd /home/propdev/.openclaw/workspace/repos/Monoclaw/Deployments/DockerBuilds/Physics/Cadabra2
./build.sh
```

That's it. `./build.sh` will:
1. Find the `docker_builder` binary (auto-detected or prompt you)
2. Confirm `build_configuration.yml` is present
3. Check Docker daemon is running
4. Run `docker_builder build .`

---

## Prerequisites

### docker_builder binary

A Rust binary that wraps `docker build`. Source at:
```
git@github.com:InServiceOfX/RustLibraries.git
  → docker_builder/
```

Build it once:
```bash
cd ~/Prop/InServiceOfX/RustLibraries/docker_builder
cargo build --release
# binary → target/debug/docker_builder  (or target/release/docker_builder)
```

The `build.sh` script auto-detects it at these locations (in order):
1. `$HOME/Prop/InServiceOfX/RustLibraries/docker_builder/target/debug/docker_builder`
2. `$HOME/Prop/InServiceOfX/RustLibraries/docker_builder/target/debug/docker_runner`
3. Any `docker_builder` or `docker_runner` on your `$PATH`

If it's not at any of those paths, set it explicitly:
```bash
export DOCKER_BUILDER=/path/to/your/docker_builder
./build.sh
```

### Docker daemon

Must be running. `build.sh` checks this before building.

---

## Files in this Directory

| File | Purpose |
|------|---------|
| `build_configuration.yml` | Input to `docker_builder` — names the image, lists Dockerfile components |
| `Dockerfile` | Layered Docker image definition (Ubuntu 24.04 + Cadabra2) |
| `docker-compose.yml` | (for `docker compose` based running, optional) |
| `build.sh` | **Recommended build entry point** — wraps `docker_builder` |
| `run.sh` | Launcher for the built image (GUI, Jupyter, CLI) |
| `run_gui.sh` | Shortcuts for GUI mode |

---

## Running the Built Image

After building, use `run.sh`:

```bash
./run.sh gui         # Cadabra2 GTK notebook (X11)
./run.sh jupyter     # JupyterLab at http://localhost:8888
./run.sh cli         # Bash shell inside container
./run.sh cli python3 /work/my_script.py  # Run a Python script
```

---

## Image Contents

The Docker image includes:
- Ubuntu 24.04
- Cadabra2 (latest from GitHub)
- Python 3.x with numpy, scipy
- JupyterLab
- Cadabra2 Python bindings (`import cadabra2`)

The Monoclaw repo is mounted at `/Monoclaw` inside the container.

---

## For Other OpenClaw Agents

If you are an OpenClaw agent and need to rebuild this image:

1. Read this file (`BUILD.md`) first
2. Run `cd /home/propdev/.openclaw/workspace/repos/Monoclaw/Deployments/DockerBuilds/Physics/Cadabra2`
3. Run `./build.sh`
4. If `./build.sh` says `docker_builder` not found:
   - Clone `git@github.com:InServiceOfX/RustLibraries.git`
   - `cd RustLibraries/docker_builder && cargo build --release`
   - Set `export DOCKER_BUILDER=/path/to/binary` and re-run `build.sh`

---

Last updated: 2026-04-07
