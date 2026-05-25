# Agent Brief — NVIDIA Isaac Sim Docker Deployment

**Owner role:** Sim + Docker agent (familiarity with NGC, Omniverse, ROS 2 bridge)
**Repo:** `Monoclaw` (net-new dir `Deployments/IsaacSim/`)
**Branch:** create `feat/isaacsim-deploy` from `master`.
**Estimate:** 4–8 hr first pass (mostly NGC auth + first successful headless boot)
**Blocks:** rosa task 07 (Starship sim)

## Goal

Stand up NVIDIA Isaac Sim 4.5+ as a Docker container that publishes ROS 2 topics on the host network, sharing the DDS domain with the sibling `Deployments/ROS` stack. Once up, the Isaac container is where the Starship-stand-in scene lives.

## Hardware reality check

Verified on this host (2026-05-24):

| GPU                 | VRAM   | Compute | Isaac Sim 4.5+ | Use |
|---------------------|--------|---------|----------------|-----|
| GTX 980 Ti (GPU 0)  | 6 GB   | 5.2     | ❌              | leave for the system display |
| RTX 3060 (GPU 1)    | 12 GB  | 8.6     | ✅              | **pin Isaac here on desktop** |
| RTX 3070 (laptop)   | 8 GB   | 8.6     | ✅              | OK on laptop; tight for big scenes |

Pin GPU 1 via `device_ids: ["1"]` and the existing UUID `GPU-61cb440a-b948-dd3e-eff7-26dd209d2411` (matches `Deployments/ROS/docker-compose.yml` NVIDIA_VISIBLE_DEVICES line). Host RAM 32 GB meets Isaac's recommendation. NVIDIA driver 580.x is fine (≥ 535 required).

If the 3060 can't sustain the Starship scene at interactive frame rate, drop visual quality in `app.config.json` (RTX → ray traced lighting → off) — the Starship MVP doesn't need pretty rendering, just physics + topics.

## NGC prereq

Isaac Sim images live on NVIDIA NGC and require login:

```bash
# One time — create an NGC API key at https://ngc.nvidia.com → Setup → Generate API Key
docker login nvcr.io   # username: $oauthtoken, password: <NGC_API_KEY>
```

Do not bake the key into any file. Document the prereq in the README; check the user has it set before `docker compose up`.

## What to create

```
Monoclaw/Deployments/IsaacSim/
├── README.md
├── AGENT_BRIEF.md            ← this file
├── docker-compose.yml
├── Dockerfile                ← thin wrapper on the NGC base if needed
├── .env.example
├── scripts/
│   ├── start_isaac.sh        # boots Isaac Sim headless with ROS 2 bridge enabled
│   └── enable_ros2_bridge.py # one-time: ensures omni.isaac.ros2_bridge ext is loaded
└── starship/                 # populated by rosa task 07 (USD + extension scripts)
```

### Dockerfile (sketch)

```Dockerfile
ARG ISAAC_VERSION=4.5.0
FROM nvcr.io/nvidia/isaac-sim:${ISAAC_VERSION}

# Isaac Sim image already has ROS 2 Humble bundled; just ensure CycloneDDS for parity
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    ACCEPT_EULA=Y \
    PRIVACY_CONSENT=Y \
    OMNI_KIT_ALLOW_ROOT=1

# Mount the starship scene at runtime via volume — don't COPY it into the image
WORKDIR /isaac-sim
COPY scripts/start_isaac.sh /usr/local/bin/start_isaac.sh
COPY scripts/enable_ros2_bridge.py /isaac-sim/scripts/enable_ros2_bridge.py
RUN chmod +x /usr/local/bin/start_isaac.sh

CMD ["/usr/local/bin/start_isaac.sh"]
```

### docker-compose.yml (sketch)

```yaml
services:
  isaac:
    build:
      context: .
      args:
        ISAAC_VERSION: ${ISAAC_VERSION:-4.5.0}
    container_name: ${CONTAINER_NAME:-isaac-sim}
    stdin_open: true
    tty: true
    network_mode: host
    ipc: host
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["${GPU_ID:-1}"]
              capabilities: [gpu, compute, utility, graphics]
    environment:
      - ACCEPT_EULA=Y
      - PRIVACY_CONSENT=Y
      - DISPLAY=${DISPLAY}
      - RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
      - ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}
      - OMNI_USER=admin
      - OMNI_PASS=admin
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
      - isaac-cache:/root/.cache/ov
      - isaac-data:/root/.local/share/ov/data
      - ./starship:/isaac-sim/exts/starship
    ports:
      - "8211:8211"   # Omniverse Streaming Client (optional)
      - "8011:8011"
      - "8111:8111"

volumes:
  isaac-cache:
  isaac-data:
```

`network_mode: host` matches the sibling ROS deployment; both containers + the host's rosa-cli end up on the same DDS domain.

### `scripts/start_isaac.sh` (sketch)

```bash
#!/bin/bash
set -e
# Headless or windowed?
MODE="${ISAAC_MODE:-headless}"   # headless | windowed | streaming

case "$MODE" in
  headless)
    exec /isaac-sim/runheadless.native.sh \
      --/exts/omni.isaac.ros2_bridge/publish_tf=true \
      --enable omni.isaac.ros2_bridge
    ;;
  streaming)
    exec /isaac-sim/runheadless.webrtc.sh \
      --enable omni.isaac.ros2_bridge
    ;;
  windowed)
    exec /isaac-sim/isaac-sim.sh \
      --enable omni.isaac.ros2_bridge
    ;;
esac
```

## Acceptance criteria

- [ ] `docker login nvcr.io` documented in README; user prompted to set up before first run.
- [ ] `docker compose build` succeeds.
- [ ] `docker compose up` starts Isaac Sim; logs show `omni.isaac.ros2_bridge` extension loaded.
- [ ] From the sibling ROS container (or the host), `ros2 topic list` shows Isaac's default `/tf`, `/tf_static`, `/clock`.
- [ ] On the host (or laptop), `nvidia-smi` inside the container shows the 3060 (GPU 1) bound, not the 980 Ti.
- [ ] Streaming mode (`ISAAC_MODE=streaming`) opens at `http://localhost:8211` if the user prefers browser viewing over X11.

## Acceptance criteria — second pass (after rosa task 07's USD lands)

- [ ] `./starship/starship.usd` loads into the scene.
- [ ] `/starship/pose` and `/starship/imu` show data when the scene is playing.
- [ ] Publishing `/starship/main_throttle = 0.5` from `ros2 topic pub` causes the vehicle to accelerate upward.

## Known gotchas

1. **EGL vs Vulkan**: Isaac Sim wants `--gpus all` *and* `--runtime nvidia` *and* X11/Wayland set up. If you see "no DISPLAY"-style errors in headless mode, double-check `runheadless.native.sh` is what's running (not `isaac-sim.sh`).
2. **DDS discovery**: if Isaac doesn't see the ROS container's topics, the issue is almost always RMW mismatch or `ROS_DOMAIN_ID` mismatch. Pin both to CycloneDDS and domain 0.
3. **First boot is slow**: Omniverse caches shaders on first scene load — expect 2–5 minutes the first time. Persist `isaac-cache` volume so subsequent boots are fast.
4. **Disk**: the NGC image is ~25 GB. Make sure the docker root has space.

## Fallback if Isaac Sim won't cooperate before Tue 5/26

Per the rosa task 07 brief, there's a pure-Rust physics-stub fallback that publishes the same `/starship/*` topic contract. That keeps the rosa demo runnable even without a working Isaac Sim container — which means *this brief is not on the interview-critical path*. Land what you can; the rosa demo can land with the stub.
