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

### First time (build + start)

```bash
cd Monoclaw/Deployments/IsaacSim
cp .env.example .env   # GPU_ID=1 on desktop (RTX 3060), GPU_ID=0 on laptop (RTX 3070)

# Must be logged in to NGC first (see Prerequisites § 1)
docker login nvcr.io

# Pull/build — first time pulls ~25 GB from NGC, subsequent builds are cached
docker compose build

# Start headless (default ISAAC_MODE=headless)
docker compose up -d
```

### Every time — watch for bridge ready

The startup log is very verbose (hundreds of deprecation warnings — all harmless).
Use the filtered command so you only see what matters:

```bash
docker compose logs -f isaac 2>&1 | grep -E 'ros2\.bridge|ROS2 Bridge|app ready|\[Error\]|LD_LIBRARY'
```

**Success looks like** (order matters):

```
[ext: isaacsim.ros2.bridge-4.1.15] startup      ← bridge extension loading
[25s] app ready                                   ← Isaac Sim fully up
                                                  ← NO "ROS2 Bridge startup failed" line
```

**Failure looks like** (the LD_LIBRARY_PATH gotcha — see Known Gotchas § 5):
```
Error getting RMW implementation ... librmw_cyclonedds_cpp.so: No such file or directory
[Error] ROS2 Bridge startup failed
```

### Verify ROS 2 topics (from the sibling ROS container)

Run this in a second terminal **while Isaac is running**:

```bash
docker compose -f ../ROS/docker-compose.yml exec ros2 bash -ic "ros2 topic list"
```

**Expected once the bridge is up** — you should see Isaac's default topics
alongside anything else running (e.g. turtlesim):

```
/clock
/tf
/tf_static
/parameter_events
/rosout
```

If you only see `/parameter_events` and `/rosout` (no `/clock` or `/tf`),
the bridge did not start — check the filtered logs above.

### Restart only (no rebuild needed for config changes)

When you change `.env` or `docker-compose.yml` environment variables,
a rebuild is **not** needed — just restart:

```bash
docker compose down && docker compose up -d
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

1. **First boot is slow** — Omniverse compiles shaders; expect 2–5 min. The `isaac-cache` volume persists this across restarts. Subsequent `docker compose up -d` starts in ~25 seconds.

2. **EGL / no DISPLAY** — headless mode uses `runheadless.native.sh`, not `isaac-sim.sh`. If you see display errors in headless mode, check the right script is running.

3. **DDS discovery** — if Isaac topics don't appear in the ROS container, check in order:
   - `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` set in **both** containers ✓ (already in compose)
   - `LD_LIBRARY_PATH` includes the bundled libs (see § 5 below) ✓ (already in compose)
   - `ROS_DOMAIN_ID=0` matches in both containers ✓ (already in compose)
   - Both containers using `network_mode: host` ✓ (already in compose)

4. **Ports clash** — `8211/8011/8111` are only used in `streaming` mode. In headless mode they're harmless. Change them in `docker-compose.yml` if something else holds those ports.

5. **`librmw_cyclonedds_cpp.so: No such file or directory` / ROS2 Bridge startup failed** —
   Isaac Sim bundles its own ROS 2 Humble libs at:
   ```
   /isaac-sim/exts/isaacsim.ros2.bridge/humble/lib
   ```
   Without `LD_LIBRARY_PATH` pointing here, the dynamic linker can't find `librmw_cyclonedds_cpp.so`
   even though `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` is set. This is already fixed in
   `docker-compose.yml` but recorded here because Isaac Sim's own log tells you the fix if
   you ever see it again.

6. **Deprecation warnings** — The log contains hundreds of `omni.isaac.X has been deprecated in favor of isaacsim.Y` lines. These are all harmless — NVIDIA renamed internal APIs in 4.5. Ignore them.

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
