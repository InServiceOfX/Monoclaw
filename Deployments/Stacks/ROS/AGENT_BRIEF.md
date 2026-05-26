# Agent Brief — ROS 2 Docker Deployment

**Owner role:** any agent (Docker + shell)
**Repo:** `Monoclaw` (untracked dir `Deployments/Stacks/ROS/`)
**Branch:** create `feat/ros2-deploy-strip-langchain` from `master`. Do not commit to `master`.
**Estimate:** 1–2 hr
**Blocks:** rosa task 06 (turtle demo)

## Goal

Rewrite this directory so the ROS 2 container is **ROS 2 + Rust toolchain only** — no langchain, no Python LLM packages, no rosa Python source. The new rosa is a Rust binary that connects from the host (or a sibling container) to this container's ROS 2 DDS. This container's job is to *host ROS 2*, not host rosa.

## Why

The current `Dockerfile` (read it first — `/home/propdev/.openclaw/workspace/repos/Monoclaw/Deployments/Stacks/ROS/Dockerfile`) pip-installs `langchain`, `langchain-community`, `langchain-core`, `langchain-openai`, etc. and mounts a deprecated ROSA source tree. That entire layer is dead per the rosa rewrite plan (see `/home/propdev/.openclaw/workspace/workspace2/repos/rosa/ORCHESTRATION.md`).

## What to change

### `Dockerfile` — replace with this shape

```Dockerfile
ARG ROS_DISTRO=humble
FROM osrf/ros:${ROS_DISTRO}-desktop AS ros2-base

ENV DEBIAN_FRONTEND=noninteractive

# Tools needed by the agent's CLI tool-shellout layer + ROS 2 dev essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-${ROS_DISTRO}-turtlesim \
    ros-${ROS_DISTRO}-rmw-cyclonedds-cpp \
    curl ca-certificates build-essential pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Rust toolchain (for native rosa-ros2 builds via the `ros2-native` feature)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

# CycloneDDS is the most reliable RMW for cross-container/host comms
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

COPY ros2_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
```

No `pip install langchain*`. No COPY of rosa source. No `python3` install unless something we know we need pulls it.

### `docker-compose.yml` — simplify

```yaml
services:
  ros2:
    build:
      context: .
      args:
        ROS_DISTRO: ${ROS_DISTRO:-humble}
    container_name: ${CONTAINER_NAME:-rosa-ros2}
    stdin_open: true
    tty: true
    network_mode: host           # required for DDS discovery to host-side rosa-cli
    ipc: host
    environment:
      - ROS_DISTRO=${ROS_DISTRO:-humble}
      - ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}
      - RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
      - DISPLAY=${DISPLAY}
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
      # No rosa source mount — rosa runs outside this container.
    command: ["bash", "-lc", "exec /entrypoint.sh"]
```

`network_mode: host` is the key change — DDS discovery does not survive the docker bridge by default; host-mode is the cleanest way to let rosa-cli (running on the host or in a separate container) see the topics.

Drop the GPU/nvidia runtime block from this compose — the ROS 2 container does not need a GPU. GPU lives in the IsaacSim compose (see sibling brief).

### `ros2_entrypoint.sh` — simplify

```bash
#!/bin/bash
set -e
source /opt/ros/${ROS_DISTRO}/setup.bash
echo "ROS 2 ${ROS_DISTRO} ready. DDS domain ${ROS_DOMAIN_ID:-0}, RMW=$RMW_IMPLEMENTATION"
echo "Try: ros2 run turtlesim turtlesim_node"
exec "$@"
```

Remove the `ros2 run rqt_topic --` background launch — caller decides what to run.

### `README.md` — rewrite

Replace the existing README (which still references langchain installs and the deprecated rosa mount) with a doc that:

1. Names this as the ROS 2 host container for the rosa Rust rewrite.
2. Documents the env vars (`ROS_DISTRO`, `ROS_DOMAIN_ID`).
3. Gives the three runtime commands:
   - `docker compose up -d`
   - `docker compose exec ros2 ros2 run turtlesim turtlesim_node` (needs X11; on Linux: `xhost +local:docker` first)
   - From the host: `rosa ask "list ROS 2 topics"` (uses host-network DDS)
4. Links to `../IsaacSim/AGENT_BRIEF.md` for the GPU-side stack.
5. Links to `/home/propdev/.openclaw/workspace/workspace2/repos/rosa/ORCHESTRATION.md`.

### `.env.example` — create

```
ROS_DISTRO=humble
ROS_DOMAIN_ID=0
CONTAINER_NAME=rosa-ros2
DISPLAY=:0
```

## Acceptance criteria

- [ ] `docker compose build` succeeds with no `langchain*` strings anywhere in the build log.
- [ ] `docker compose up -d` starts; `docker compose exec ros2 ros2 doctor` reports OK.
- [ ] `xhost +local:docker && docker compose exec ros2 ros2 run turtlesim turtlesim_node` opens the turtle window on the host.
- [ ] From host (with ROS 2 source'd OR a sibling host-mode container): `ros2 topic list` shows `/turtle1/cmd_vel` while turtlesim runs in the container. This proves DDS crosses the boundary.
- [ ] `grep -ri langchain Dockerfile docker-compose.yml README.md ros2_entrypoint.sh` returns nothing.
- [ ] PR opened on branch `feat/ros2-deploy-strip-langchain`.

## Why CycloneDDS over the default

Fast-DDS (the default RMW in Humble) has well-known multicast issues when bridging host ↔ container ↔ Isaac Sim container. CycloneDDS handles loopback + host-network reliably. If you hit DDS discovery problems, double-check `RMW_IMPLEMENTATION` is set in **every** participant (host shell, ROS container, Isaac container, rosa-cli env).

## Out of scope

- Multi-distro support beyond Humble. Iron/Jazzy can land later.
- ROS 1 — dropped (Noetic EOL'd April 2025).
- LLM keys / config — those belong to rosa-cli on the host, not this container.
