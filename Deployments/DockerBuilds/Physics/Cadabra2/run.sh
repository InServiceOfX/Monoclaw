#!/bin/bash
# run.sh — Cadabra2 launcher
#
# Usage:
#   ./run.sh gui              — cadabra2-gtk notebook (X11)
#   ./run.sh jupyter          — JupyterLab on localhost:8888
#   ./run.sh cli              — bash shell inside container
#   ./run.sh cli <cmd...>     — run a command inside container
#                               e.g.: ./run.sh cli cadabra2-cli
#                               e.g.: ./run.sh cli python3 spinors/01_weyl_spinors.py
#
# Notebooks/files are mounted from ./notebooks (created if missing)

set -e

IMAGE="cadabra2-ubuntu:24.04"
NOTEBOOKS_DIR="${NOTEBOOKS:-$(dirname "$0")/notebooks}"
MODE="${1:-help}"

mkdir -p "${NOTEBOOKS_DIR}"

case "$MODE" in

  # ── GUI: cadabra2-gtk with X11 ──────────────────────────────────────────
  gui)
    echo "==> Enabling X11 access for Docker..."
    xhost +local:docker 2>/dev/null || true

    echo "==> Launching cadabra2-gtk..."
    echo "    (Notebooks directory: ${NOTEBOOKS_DIR})"

    docker run --rm -it \
      --security-opt seccomp=unconfined \
      -e DISPLAY="${DISPLAY:-:0}" \
      -e WEBKIT_DISABLE_COMPOSITING_MODE=1 \
      -e GDK_RENDERING=image \
      -e LIBGL_ALWAYS_SOFTWARE=1 \
      -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
      -v "${NOTEBOOKS_DIR}:/work" \
      "${IMAGE}" \
      cadabra2-gtk

    xhost -local:docker 2>/dev/null || true
    ;;

  # ── Jupyter: JupyterLab on port 8888 ────────────────────────────────────
  jupyter)
    echo "==> Starting JupyterLab..."
    echo "    Open: http://localhost:8888"
    echo "    Notebooks directory: ${NOTEBOOKS_DIR}"
    echo "    Use Ctrl+C to stop."

    docker run --rm -it \
      -p 8888:8888 \
      -e JUPYTER_ALLOW_INSECURE_WRITES=1 \
      -v "${NOTEBOOKS_DIR}:/work" \
      -w /work \
      "${IMAGE}" \
      jupyter lab \
        --ip=0.0.0.0 \
        --port=8888 \
        --no-browser \
        --allow-root \
        --NotebookApp.token='' \
        --NotebookApp.password=''
    ;;

  # ── CLI: shell or command ────────────────────────────────────────────────
  cli)
    shift  # remove 'cli' from args
    if [ $# -eq 0 ]; then
      echo "==> Opening bash shell in cadabra2 container..."
      echo "    Available commands: cadabra2, cadabra2-cli, python3"
      echo "    Notebooks directory mounted at /work"
      docker run --rm -it \
        -v "${NOTEBOOKS_DIR}:/work" \
        -w /work \
        "${IMAGE}" \
        /bin/bash
    else
      echo "==> Running: $*"
      # Check if stdin is a TTY to decide on -it flags
      if [ -t 0 ]; then
        docker run --rm -it \
          -v "${NOTEBOOKS_DIR}:/work" \
          -w /work \
          "${IMAGE}" \
          "$@"
      else
        docker run --rm \
          -v "${NOTEBOOKS_DIR}:/work" \
          -w /work \
          "${IMAGE}" \
          "$@"
      fi
    fi
    ;;

  # ── Help ─────────────────────────────────────────────────────────────────
  *)
    cat <<EOF
Cadabra2 Docker Launcher

Usage: ./run.sh <mode> [args]

Modes:
  gui                   cadabra2-gtk notebook (requires X11 / display)
  jupyter               JupyterLab on http://localhost:8888
  cli                   bash shell inside container
  cli <cmd> [args...]   run command inside container

Examples:
  ./run.sh gui
  ./run.sh jupyter
  ./run.sh cli
  ./run.sh cli cadabra2-cli
  ./run.sh cli python3 spinors/01_weyl_spinors.py

Environment:
  NOTEBOOKS=<path>      host directory mounted as /work (default: ./notebooks)
  DISPLAY               X11 display (default: :0)

Image: ${IMAGE}
EOF
    ;;
esac
