# Headless Isaac Sim on RTX 3060 + Display on GTX 980 Ti

## Goal
Run Isaac Sim **headless** (EGL, no X11) on the RTX 3060 (compute GPU) while keeping the 980 Ti free for normal desktop use.

## Current Setup (already supported)
- `docker-compose.yml` pins GPU via `device_ids: ["${GPU_ID:-1}"]`
- `ISAAC_MODE=headless` (default)
- No `DISPLAY` variable (prevents X auth crashes)
- Uses EGL directly on the 3060

## Recommended .env for this machine
```env
GPU_ID=1                    # RTX 3060 (compute)
ISAAC_MODE=headless
ISAAC_VERSION=4.5.0
ROS_DOMAIN_ID=0
```

## Viewing / Controlling the Scene from the 980 Ti Host

### Option 1: NVIDIA Omniverse Streaming (easiest)
- The container already exposes ports 8211, 8011, 8111.
- Use the **Omniverse Streaming Client** (or web client) on the 980 Ti machine to connect to the headless Isaac Sim.
- You get a live rendered view + input.

### Option 2: ROS 2 / UDP Control (recommended for this project)
- The `starship_publisher.py` already publishes full 6DOF telemetry (`/starship/pose`, `/starship/imu` with angular_velocity).
- Run `rosa-cli` or your custom `jetson-fsw` / UDP receiver on the host.
- Send commands back via ROS 2 or the UDP telemetry channel.
- This decouples rendering from simulation.

### Option 3: Open Source USD Viewing (limited live support)
- `usdview` (from Pixar USD) can open the `starship.usd` file statically.
- Live remote rendering of USD from headless Isaac Sim is not well supported in fully open-source tools.
- Best you can do today: copy the `.usd` periodically or use NVIDIA streaming.

## Recommendation for your workflow
1. Run Isaac Sim headless on 3060 (compute).
2. Use ROS 2 topics + UDP (jetson-fsw / rosa) for control and telemetry.
3. For visual inspection, either:
   - Use Omniverse streaming client on the 980 Ti, or
   - Open the `starship.usd` locally with `usdview` for static inspection.

This keeps the heavy physics on the 3060 while the 980 Ti stays responsive for normal work.