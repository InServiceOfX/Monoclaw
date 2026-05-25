# ROS 2 Host Container

This is the **ROS 2 environment** for the rosa Rust rewrite.  
It hosts ROS 2 Humble + turtlesim. `rosa-cli` (a Rust binary) runs on the **host** and talks to this container via host-network DDS.

> **No LangChain. No Python LLM packages. No rosa Python source.**  
> See [`AGENT_BRIEF.md`](AGENT_BRIEF.md) for why.

---

## Quick Start

```bash
cd Monoclaw/Deployments/ROS
cp .env.example .env        # edit if needed

# Build (first time or after Dockerfile changes)
docker compose build

# Start the container
docker compose up -d

# Verify ROS 2 is healthy
# NOTE: use `bash -ic` so .bashrc is sourced and ros2 is in PATH.
# `docker compose exec ros2 ros2 ...` alone will fail with "not found in $PATH"
# because exec bypasses the ENTRYPOINT.
docker compose exec ros2 bash -ic "ros2 doctor"

# Launch turtlesim (requires X11 on the host)
xhost +local:docker
docker compose exec ros2 bash -ic "ros2 run turtlesim turtlesim_node"
```

> **Why `bash -ic`?**  
> `docker compose exec` starts a raw process — it does **not** run the container's `ENTRYPOINT`.  
> The `-i` flag tells bash to read `.bashrc`, which sources `/opt/ros/humble/setup.bash`  
> and puts `ros2` in `$PATH`. Alternatively, open a full shell with  
> `docker compose exec -it ros2 bash` — that also sources `.bashrc`.

From the **host** (with ROS 2 sourced, or in host-network mode):
```bash
ros2 topic list    # should see /turtle1/cmd_vel once turtlesim is running
```

---

## Running rosa

`rosa-cli` runs on the host and connects to this container via shared-host-network DDS. No socket tunnel needed.

```bash
# From the rosa repo (needs ANTHROPIC_API_KEY or OPENAI_API_KEY)
cd ~/workspace/workspace2/repos/rosa
cargo run --release --example turtle
# > Draw a 5-point star using the turtle.
```

---

## Environment Variables

| Variable         | Default        | Description                               |
|------------------|----------------|-------------------------------------------|
| `ROS_DISTRO`     | `humble`       | ROS 2 distribution                        |
| `ROS_DOMAIN_ID`  | `0`            | DDS domain — must match rosa-cli and Isaac|
| `CONTAINER_NAME` | `rosa-ros2`    | Docker container name                     |
| `DISPLAY`        | `:0`           | X11 display for turtlesim GUI             |

---

## How DDS works across host ↔ container

`network_mode: host` makes the container share the host's network stack. DDS multicast discovery works without any tunnel or bridging. If `ros2 topic list` on the host doesn't see the container's topics, the most common culprit is `RMW_IMPLEMENTATION` mismatch — both sides must use `rmw_cyclonedds_cpp`.

---

## Relation to other stacks

| Stack               | Location                             | Purpose               |
|---------------------|--------------------------------------|-----------------------|
| This container      | `Deployments/ROS/`                   | ROS 2 + turtlesim     |
| Isaac Sim container | `Deployments/IsaacSim/`              | GPU sim (Starship)    |
| rosa Rust binary    | `~/workspace2/repos/rosa/`           | LLM agent + tools     |

See also:
- [`../IsaacSim/AGENT_BRIEF.md`](../IsaacSim/AGENT_BRIEF.md) — GPU sim stack
- [`~/workspace2/repos/rosa/ORCHESTRATION.md`](../../../../workspace2/repos/rosa/ORCHESTRATION.md) — full project plan

---

*Updated: 2026-05-24 — langchain stripped, host-network DDS, Rust toolchain added*
