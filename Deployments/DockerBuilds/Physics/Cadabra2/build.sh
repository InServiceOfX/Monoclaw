#!/bin/bash
# build.sh — Build the cadabra2-ubuntu:24.04 Docker image
#
# Usage:
#   ./build.sh              — builds the image (recommended)
#   ./build.sh --check      — only checks prerequisites, don't build
#
# What this does:
#   1. Finds the docker_builder binary (auto-detected or user-specified)
#   2. Confirms build_configuration.yml exists in this directory
#   3. Runs: docker_builder build .
#
# Prerequisites:
#   - docker_builder binary (Rust binary, part of InServiceOfX/RustLibraries/docker_builder)
#   - Docker daemon running
#   - build_configuration.yml in the same directory as this script

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
DOCKER_BUILDER=""

# Candidate paths to check (ordered by priority)
CANDIDATES=(
    # InServiceOfX/RustLibraries — standard location
    "${HOME}/Prop/InServiceOfX/RustLibraries/docker_builder/target/debug/docker_builder"
    "${HOME}/Prop/InServiceOfX/RustLibraries/docker_builder/target/debug/docker_runner"
    # Alternative: workspace2 symlink
    "${HOME}/.openclaw/workspace/workspace2/repos/InServiceOfX/RustLibraries/docker_builder/target/debug/docker_builder"
    "${HOME}/.openclaw/workspace/workspace2/repos/InServiceOfX/RustLibraries/docker_builder/target/debug/docker_runner"
    # coding-agent skill location
    "${HOME}/.openclaw/workspace/repos/Monoclaw/Deployments/Scripts/TensorRTLLMFixed/docker_runner"
)

# Search PATH too
if command -v docker_builder &>/dev/null; then
    DOCKER_BUILDER="$(command -v docker_builder)"
    info "Found docker_builder on PATH: ${DOCKER_BUILDER}"
elif command -v docker_runner &>/dev/null; then
    DOCKER_BUILDER="$(command -v docker_runner)"
    info "Found docker_runner on PATH: ${DOCKER_BUILDER}"
else
    for candidate in "${CANDIDATES[@]}"; do
        if [ -f "${candidate}" ] && [ -x "${candidate}" ]; then
            DOCKER_BUILDER="${candidate}"
            info "Found docker_builder: ${DOCKER_BUILDER}"
            break
        fi
    done
fi

# ── 3. Not found — bail with a helpful message ──────────────────────────────
if [ -z "${DOCKER_BUILDER}" ] || [ ! -x "${DOCKER_BUILDER}" ]; then
    error "docker_builder binary not found."
    echo
    echo "  Expected one of:"
    for candidate in "${CANDIDATES[@]}"; do
        echo "    ${candidate}"
    done
    echo
    echo "  Fix: set the path to your docker_builder binary and re-run:"
    echo "    export DOCKER_BUILDER=/path/to/your/docker_builder"
    echo "    ./build.sh"
    echo
    echo "  Or clone and build it from:"
    echo "    git@github.com:InServiceOfX/RustLibraries.git"
    echo "    cd RustLibraries/docker_builder && cargo build --release"
    exit 1
fi

success "docker_builder: ${DOCKER_BUILDER}"

# ── 4. Check Docker daemon ───────────────────────────────────────────────────
if ! docker info &>/dev/null; then
    error "Docker daemon is not running."
    error "Start Docker and re-run this script."
    exit 1
fi
success "Docker daemon: running"

# ── 5. Check for --check flag (dry run) ─────────────────────────────────────
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
