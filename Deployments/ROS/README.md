# ROS 2 Host Container

This is the **ROS 2 environment** for the rosa Rust rewrite.  
It hosts ROS 2 Humble + turtlesim. `rosa-cli` (a Rust binary) runs on the **host** and talks to this container via host-network DDS.

> **No LangChain. No Python LLM packages. No rosa Python source.**  
> See [`AGENT_BRIEF.md`](AGENT_BRIEF.md) for why.

---

## Quick Start

> **Note on `bash -ic`:** `docker compose exec` starts a raw process and does **not** run the
> container's ENTRYPOINT. The `-i` flag makes bash read `.bashrc`, which sources
> `/opt/ros/humble/setup.bash` and puts `ros2` in `$PATH`. Every `exec` command below uses
> this pattern. To open a persistent shell instead: `docker compose exec -it ros2 bash`.

```bash
cd Monoclaw/Deployments/ROS
cp .env.example .env        # edit if needed (defaults work on desktop)

# 1. Build (first time, or after any Dockerfile change)
docker compose build

# 2. Start the container (detached)
docker compose up -d

# 3. Verify ROS 2 is healthy — expect "All 5 checks passed"
docker compose exec ros2 bash -ic "ros2 doctor"

# 4. Allow X11 connections from Docker (one time per host login session)
xhost +local:docker
```

### Launch turtlesim

`turtlesim_node` **blocks the terminal** while it runs. Choose one of:

**Option A — two terminals (recommended for keyboard control)**

```bash
# Terminal 1: start turtlesim (window opens on your desktop)
docker compose exec ros2 bash -ic "ros2 run turtlesim turtlesim_node"

# Terminal 2: keyboard teleop — arrow keys drive the turtle
docker compose exec ros2 bash -ic "ros2 run turtlesim turtle_teleop_key"
```

**Option B — background + one-shot publish (no second terminal)**

```bash
# Start turtlesim in the background
docker compose exec ros2 bash -ic "ros2 run turtlesim turtlesim_node &"

# Publish a single Twist command (move forward)
docker compose exec ros2 bash -ic "ros2 topic pub --once /turtle1/cmd_vel \
  geometry_msgs/msg/Twist '{linear: {x: 2.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'"

# Spin in place
docker compose exec ros2 bash -ic "ros2 topic pub --once /turtle1/cmd_vel \
  geometry_msgs/msg/Twist '{linear: {x: 0.0}, angular: {z: 1.57}}'"
```

**Option C — interactive shell (most convenient for exploration)**

```bash
docker compose exec -it ros2 bash
# Now inside the container — all ros2 commands work directly:
ros2 run turtlesim turtlesim_node &
ros2 topic list
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 2.0}, angular: {z: 0.0}}'
```

### Verify topics (from inside the container)

```bash
# Check topics while turtlesim is running — should include /turtle1/cmd_vel
docker compose exec ros2 bash -ic "ros2 topic list"
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
