# NVIDIA Isaac Sim — Docker Deployment

GPU simulation host for the rosa Rust rewrite's Starship stand-in demo.  
After setup, `ros2 topic list` from any DDS participant on domain 0 will show the `/starship/*` topics.

---

## Prerequisites

### 1. NGC API key (one time)
Isaac Sim images require an NVIDIA NGC account:
1. Go to [ngc.nvidia.com → Setup → Generate API Key](https://ngc.nvidia.com)
2. Login to the NGC registry:
   ```bash
   docker login nvcr.io
   # Username: $oauthtoken
   # Password: <your NGC API key>
   ```
Do **not** bake the key into any file.

### 2. NVIDIA container runtime

Verify the NVIDIA container toolkit is wired up using `ubuntu:22.04` (already on disk —
no pull needed). The toolkit injects `nvidia-smi` into any container when `--gpus all` is set:

```bash
docker run --rm --gpus all ubuntu:22.04 nvidia-smi
```

Expected: `nvidia-smi` table showing your GPUs (RTX 3060, RTX 3070, GTX 980 Ti).  
If you get `could not select device driver "" with capabilities: [[gpu]]`, the
NVIDIA container toolkit is not configured — see
[NVIDIA Container Toolkit install](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

> **Why not `nvidia/cuda:12.0-base-ubuntu22.04`?**  
> That Docker Hub tag doesn't exist — NVIDIA's CUDA images require a full semver
> like `12.0.0-base-ubuntu22.04`, and the authoritative source is NGC
> (`nvcr.io/nvidia/cuda`), not Docker Hub. `ubuntu:22.04` is simpler and already local.

### 3. Disk space
The Isaac Sim image is ~25 GB. Ensure the Docker data root has room.

```bash
df -h $(docker info --format '{{.DockerRootDir}}')
```

---

## Quick Start

The Isaac Sim image is the **official NVIDIA-published image** from NGC:
`nvcr.io/nvidia/isaac-sim` — this is what our Dockerfile builds from.
No custom base image needed; the Dockerfile is a thin wrapper that adds
CycloneDDS config and the `start_isaac.sh` launcher script.

```bash
cd Monoclaw/Deployments/IsaacSim
cp .env.example .env   # GPU_ID=1 on desktop (RTX 3060), GPU_ID=0 on laptop (RTX 3070)

# Must be logged in to NGC first (see Prerequisites § 1)
docker login nvcr.io

# Pull/build — first time pulls ~25 GB from NGC, subsequent builds are cached
docker compose build

# Start headless (default ISAAC_MODE=headless)
docker compose up -d

# Watch logs — wait for the ROS 2 bridge extension to load
# Look for: "[Info] [omni.isaac.ros2_bridge] ... loaded"
docker compose logs -f isaac

# Verify ROS 2 topics are visible from the sibling ROS container:
docker compose -f ../ROS/docker-compose.yml exec ros2 bash -ic "ros2 topic list"
# Expected: /tf  /tf_static  /clock  (Isaac Sim defaults)
```

---

## GPU Selection

| Machine   | GPU            | VRAM | `GPU_ID` |
|-----------|----------------|------|----------|
| Desktop   | RTX 3060       | 12 GB| `1`      |
| Laptop    | RTX 3070       | 8 GB | `0`      |
| Desktop   | GTX 980 Ti     | 6 GB | ❌ not supported (no RT cores) |

Set `GPU_ID` in `.env` before starting.

---

## Modes

| `ISAAC_MODE` | Use case                                   |
|--------------|--------------------------------------------|
| `headless`   | Default; no display needed; ROS 2 bridge active |
| `streaming`  | Browser viewer at `http://localhost:8211`  |
| `windowed`   | Full GUI via X11 (needs `xhost +local:docker`) |

---

## Starship Scene

The Starship stand-in lives in `./starship/` (volume-mounted into the container):

```
starship/
├── starship.usd              # Stage — populated by rosa task 07
├── starship_publisher.py     # Isaac Sim extension: physics → ROS 2 topics
└── starship_controller.py    # Subscribes to /starship/* commands
```

These files are created by rosa agent-task 07 (`agent-tasks/07-starship-sim-config.md`).

### ROS 2 topic contract

**Telemetry (published by Isaac):**
| Topic                     | Type                          | Rate   |
|---------------------------|-------------------------------|--------|
| `/starship/pose`          | `geometry_msgs/PoseStamped`   | 100 Hz |
| `/starship/imu`           | `sensor_msgs/Imu`             | 200 Hz |
| `/starship/altitude`      | `std_msgs/Float64`            | 50 Hz  |
| `/starship/velocity`      | `geometry_msgs/Vector3Stamped`| 50 Hz  |
| `/starship/fuel_fraction` | `std_msgs/Float32`            | 1 Hz   |
| `/starship/engine_state`  | `std_msgs/String` (JSON)      | 10 Hz  |

**Commands (subscribed by Isaac):**
| Topic                     | Type                      |
|---------------------------|---------------------------|
| `/starship/main_throttle` | `std_msgs/Float32` (0–1)  |
| `/starship/main_gimbal`   | `geometry_msgs/Vector3`   |
| `/starship/rcs/top`       | `geometry_msgs/Vector3`   |
| `/starship/rcs/mid_fwd`   | `geometry_msgs/Vector3`   |
| `/starship/rcs/mid_aft`   | `geometry_msgs/Vector3`   |
| `/starship/safe_mode`     | `std_msgs/Bool`           |

---

## Known Gotchas

1. **First boot is slow** — Omniverse compiles shaders; expect 2–5 min. The `isaac-cache` volume persists this across restarts.
2. **EGL / no DISPLAY** — headless mode uses `runheadless.native.sh`, not `isaac-sim.sh`. If you see display errors in headless mode, check the right script is running.
3. **DDS discovery** — if Isaac topics don't appear in the ROS container, verify `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` and `ROS_DOMAIN_ID=0` in **both** containers and the host shell.
4. **Ports clash** — if 8211/8011/8111 are in use, change them in docker-compose.yml.

---

## Relation to Other Stacks

| Stack           | Location               | Purpose              |
|-----------------|------------------------|----------------------|
| ROS 2 container | `Deployments/ROS/`     | ROS 2 + turtlesim    |
| This container  | `Deployments/IsaacSim/`| GPU sim + Starship   |
| rosa CLI        | `~/workspace2/repos/rosa/`| Rust LLM agent    |

See also:
- [`../ROS/README.md`](../ROS/README.md) — sibling ROS 2 container
- [`~/workspace2/repos/rosa/ORCHESTRATION.md`](../../../../workspace2/repos/rosa/ORCHESTRATION.md) — full project plan
- [`AGENT_BRIEF.md`](AGENT_BRIEF.md) — implementation brief for this container

---

*Created: 2026-05-24 — Net-new Isaac Sim deployment for rosa Rust rewrite*
