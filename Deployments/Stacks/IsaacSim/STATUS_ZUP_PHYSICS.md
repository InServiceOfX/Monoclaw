# Isaac Sim Starship — Z-up + Physics-Only Headless (session handoff)

Status as of 2026-06-20. Everything below is **done and verified** unless marked TODO.

## TL;DR
- The stage is now **Z-up** (ROS REP-103: +Z = up, altitude = world-Z), not Y-up.
- The Starship mesh has a **proper pointed nose** (`starship_v2_pointednose.stl`).
- New **physics-only headless mode** (`ISAAC_PHYSICS_ONLY=1`, now the default in `.env`)
  boots in **~15 s** instead of hanging. This is the big fix.
- **Verified**: with engines off the vehicle falls straight down −Z from z=1000 m,
  accelerating at ~3.76 m/s² (= Mars gravity 3.72), x/y ≈ 0, lands and rests at z≈1.5.

## The boot-hang fix (root cause)
Headless Isaac on the RTX 3060 hung forever at ~30 s (`carb.tasking is likely stuck`).
Cause: `isaacsim.exp.base.kit` sets `rtx.hydra.mdlMaterialWarmup = true`, which
synchronously precompiles MDL shaders during startup — pathological on headless
GeForce. We render in Blender, so Isaac needs only PhysX + USD.

Fix: a custom experience kit **`starship/isaacsim.exp.physics.kit`** that inherits
`isaacsim.exp.base` but sets `rtx.hydra.mdlMaterialWarmup = false` (+ DLSS/NGX off,
no frame present). It's mounted into `/isaac-sim/apps/` so its `${app}/../exts`
paths resolve like the stock kits. `enable_ros2_bridge.py` selects it as the
SimulationApp `experience` when `ISAAC_PHYSICS_ONLY=1`.

## How to run
```bash
cd Deployments/Stacks/IsaacSim
docker compose up -d            # physics-only is the default now (.env)
# wait ~15-20 s, then:
curl -s http://localhost:8282/telemetry/latest    # {x,y,z,qw..,vx..}; z is altitude
```
The scene auto-loads from `ISAAC_SCENE_PATH` and the timeline starts automatically —
**do NOT call `/scene/load` or `/starship/create-stage` at runtime in physics-only
mode**: a runtime stage reload tries to re-init windowing (GLFW) and shuts the app
down. To change the scene, edit/regenerate `starship.usd` on disk and restart.

The fall is fast (Mars: 1000 m in ~23 s), so to *see* it, sample telemetry within
the first ~20 s after boot, or it'll already be resting at z≈1.5.

## Files changed this session
- `starship/create_stage.py` — Z-up stage (upAxis Z, gravity −Z, spawn z=1000,
  ground in X-Y, mesh rotated +90° about X, capsule/camera on Z); default STL is
  `starship_v2_pointednose.stl`; PhysxSchema guarded + env-overridable paths so it
  can run standalone (usd-core) to regenerate without Isaac.
- `starship/make_pointed_nose.py` — builds `starship_v2_pointednose.stl` from
  `starship_v2.stl` (cuts the broken inverted-funnel nose, grafts a pointed cone).
- `starship/isaacsim.exp.physics.kit` — physics-only experience (MDL warmup off).
- `scripts/enable_ros2_bridge.py` — `ISAAC_PHYSICS_ONLY` toggle; reset positions
  fixed to Z-up; liftoff velocity on +Z.
- `starship/starship_publisher.py` — altitude = pos[2]; IMU vertical accel on Z.
- `starship/starship_controller.py` — thrust on +Z; gimbal torque axes remapped;
  `apply_force_at_pos` updated to the Isaac 4.5 signature `(stage_id, body_path:int,
  force, pos, mode)` via `PhysicsSchemaTools.sdfPathToInt`.
- `docker-compose.yml` + `.env` — `ISAAC_PHYSICS_ONLY` env (default 1).

## Blender side (sibling stack `../Blender`)
- `starship.blend` re-baked from the Z-up pointed-nose USD; driver uses identity
  pose mapping (USD Z-up = Blender Z-up). Reload with `docker compose down && up`.

## Known issues / TODO
- **`sim_time` reads ~0** in `/diagnostics` (timeline animation time; the stage has
  no time range). Physics still steps in real time (the fall proves it) — cosmetic.
  Could set stage timeCodes or report wall/physics time instead.
- **Thrust/hover/gimbal** (controller force path) fixed for the 4.5 API but only
  lightly tested — verify a non-trivial throttle actually arrests the fall (needs
  the ROS stack to publish `/starship/main_throttle`, or add an HTTP throttle route).
- Live **Isaac→Blender** visual (driver polling `:8282`) is wired but not yet
  watched end-to-end on the display; should "just work" since the endpoint is live.
