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
```bash
# Verify
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

### 3. Disk space
The Isaac Sim image is ~25 GB. Ensure the Docker data root has room.

---

## Quick Start

```bash
cd Monoclaw/Deployments/IsaacSim
cp .env.example .env   # set GPU_ID=1 on desktop, GPU_ID=0 on laptop

# Pull/build (first time — pulls ~25 GB)
docker compose build

# Start headless (default)
docker compose up -d

# Watch logs until you see: "omni.isaac.ros2_bridge loaded"
docker compose logs -f isaac

# From the sibling ROS container or host (once bridge is up):
ros2 topic list   # should show /tf, /tf_static, /clock
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
