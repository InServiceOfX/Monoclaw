#!/bin/bash
# run_gui.sh — Launch cadabra2 GUI notebook with X11 forwarding

set -e

IMAGE="cadabra2-ubuntu:24.04"
WORK_DIR="${1:-$(pwd)}"

echo "==> Enabling X11 access for Docker..."
xhost +local:docker

echo "==> Launching cadabra2 notebook UI..."
docker run --rm -it \
    -e DISPLAY="${DISPLAY:-:0}" \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v "${WORK_DIR}:/work" \
    "${IMAGE}" \
    cadabra2-gtk

echo "==> Restoring X11 access..."
xhost -local:docker
