#!/bin/bash
# build.sh — Build the cadabra2-ubuntu:24.04 Docker image
#
# Usage:
#   ./build.sh              — builds the image
#   ./build.sh --check      — check prerequisites only (does not build)
#
# What this does:
#   1. Confirms build_configuration.yml exists in this directory
#   2. Finds the docker_builder binary (auto-detected or user-specified)
#   3. Confirms Docker daemon is running
#   4. Runs: docker_builder build .
#
# Requirements:
#   - Docker daemon running
#   - build_configuration.yml next to this script
#   - docker_builder binary (see "Finding docker_builder" below)
#
# NOTE ON PATHS: This script lives on a specific machine (Prop-dev/MS-7885)
# where the InServiceOfX repo happens to be at ${HOME}/Prop/InServiceOfX/.
# That path is NOT guaranteed on other machines. See BUILD.md for the
# machine-agnostic setup instructions.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/build_configuration.yml"

# ── Coloured output helpers ────────────────────────────────────────────────
info()    { echo -e "\033[34m[INFO]\033[0m  $*"; }
warn()    { echo -e "\033[33m[WARN]\033[0m  $*" >&2; }
error()   { echo -e "\033[31m[ERROR]\033[0m $*" >&2; }
success() { echo -e "\033[32m[OK]\033[0m    $*"; }

# ── 1. Check build_configuration.yml exists ────────────────────────────────
if [ ! -f "${CONFIG_FILE}" ]; then
    error "build_configuration.yml not found at: ${CONFIG_FILE}"
    error "This file should be in the same directory as this script."
    exit 1
fi
success "Found build_configuration.yml"

# ── 2. Find docker_builder binary ─────────────────────────────────────────
#
# Search order:
#   a. $DOCKER_BUILDER env var (user override — always respected)
#   b. docker_builder / docker_runner on $PATH
#   c. Give up (prompt user with setup instructions)
#
# NOTE on relative-path heuristics:
#   On Prop-dev/MS-7885 the InServiceOfX repo is at ${HOME}/Prop/InServiceOfX/
#   and docker_builder is at:
#     ${HOME}/Prop/InServiceOfX/RustLibraries/docker_builder/target/debug/docker_builder
#   This path is OUTSIDE the workspace tree and is NOT a reliable relative
#   path from this script (which lives in the Monoclaw repo inside workspace).
#   We do NOT assume this path on other machines.
#   If you have a similar setup, set $DOCKER_BUILDER or put the binary on PATH.

DOCKER_BUILDER="${DOCKER_BUILDER:-}"  # Read from env; empty if not set

# (a) User override via environment variable (must be set AND executable)
if [ -n "${DOCKER_BUILDER}" ] && [ -x "${DOCKER_BUILDER}" ]; then
    info "Using DOCKER_BUILDER from environment: ${DOCKER_BUILDER}"
elif [ -n "${DOCKER_BUILDER}" ]; then
    error "DOCKER_BUILDER is set but not executable: ${DOCKER_BUILDER}"
    exit 1
fi

# (b) Search PATH
if [ -z "${DOCKER_BUILDER}" ]; then
    for bin in docker_builder docker_runner; do
        if command -v "${bin}" &>/dev/null; then
            DOCKER_BUILDER="$(command -v "${bin}")"
            info "Found ${bin} on PATH: ${DOCKER_BUILDER}"
            break
        fi
    done
fi

# ── 3. Check Docker daemon ─────────────────────────────────────────────────
if ! docker info &>/dev/null; then
    error "Docker daemon is not running."
    error "Start Docker and re-run this script."
    exit 1
fi
success "Docker daemon: running"

# ── 4. docker_builder status ───────────────────────────────────────────────
if [ -z "${DOCKER_BUILDER}" ] || [ ! -x "${DOCKER_BUILDER}" ]; then
    warn "docker_builder binary not found."
    echo
    echo "  You need the docker_builder Rust binary to build this image."
    echo
    echo "  Setup steps:"
    echo "    1. git clone git@github.com:InServiceOfX/RustLibraries.git"
    echo "    2. cd RustLibraries/docker_builder"
    echo "    3. cargo build --release"
    echo
    echo "  Then either:"
    echo "    a) Put the binary on your PATH (docker_builder or docker_runner), OR"
    echo "    b) Set DOCKER_BUILDER env var and re-run:"
    echo "         export DOCKER_BUILDER=/path/to/docker_builder"
    echo "         ./build.sh"
    echo
    echo "  See BUILD.md for full details."
    echo

    if [ "${1:-}" = "--check" ]; then
        info "--check complete (docker_builder missing — see above)."
        exit 0
    else
        error "Cannot build without docker_builder."
        exit 1
    fi
fi

success "docker_builder: ${DOCKER_BUILDER}"

# ── 5. --check mode: just report status ───────────────────────────────────
if [ "${1:-}" = "--check" ]; then
    success "All prerequisites satisfied. Run ./build.sh without --check to build."
    exit 0
fi

# ── 6. Build ────────────────────────────────────────────────────────────────
info "Building cadabra2-ubuntu:24.04 ..."
info "Working directory: ${SCRIPT_DIR}"
echo

cd "${SCRIPT_DIR}"
"${DOCKER_BUILDER}" build .

success "Build complete: cadabra2-ubuntu:24.04"
info "Run './run.sh --help' to see how to use the image."
