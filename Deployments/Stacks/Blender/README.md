# Blender — real-time EEVEE viewer for Starship telemetry

Renders the Starship scene live in **EEVEE on the host display GPU (GTX 980 Ti)**,
driven by telemetry from the headless Isaac Sim physics sim (RTX 3060). Nothing
is installed on the host except the NVIDIA driver + container toolkit (already
present for the IsaacSim stack). The image is portable to any laptop with an
NVIDIA GPU + the toolkit.

```
  RTX 3060 (GPU 1)              GTX 980 Ti (GPU 0, drives DISPLAY=:0)
  ┌────────────────┐  telemetry  ┌──────────────────────────────┐
  │ Isaac Sim       │  HTTP :8282 │ Blender (this container)      │
  │ headless physics├────────────►│ wm.usd_import(starship.usd)   │
  │ (Stacks/IsaacSim)│  or UDP    │ timer: pose → object xform    │
  └────────────────┘  :50505     │ EEVEE viewport → your monitor │
                                  └──────────────────────────────┘
```

## Prerequisites
- NVIDIA driver + `nvidia-container-toolkit` (verify: `docker run --rm --gpus all ubuntu:22.04 nvidia-smi`)
- An **X11** session (this desktop is X11, `DISPLAY=:0`). Wayland: see note below.
- The IsaacSim stack's `starship/starship.usd` exists (mounted read-only from `../IsaacSim/starship`).

## Run

```bash
cd Deployments/Stacks/Blender
cp .env.example .env            # defaults are fine on this desktop

xhost +local:root               # let the container talk to your X server (per login)

docker compose build            # first time (~Blender download)
docker compose up               # foreground — Blender window opens on the 980 Ti
```

Compose opens the pre-baked **`starship.blend`** (steel hull + rust-red Mars +
lighting, EEVEE engine) and then runs the driver, which finds the Starship object
and drives it from telemetry. In Blender, if it's not already rendered, set a 3D
viewport's shading to **Rendered**. Then drive the sim from the rosa side
(liftoff / descent / abort) and watch it move here in real time.

### Why a baked `.blend` (not USD import at startup)
Importing a USD from a `--python` script *at GUI startup* is flaky — the import
lands in a startup context the visible window doesn't show, so you get the default
cube and an empty-looking outliner. Opening a `.blend` is rock-solid. Regenerate it
after editing the IsaacSim USD with:

```bash
./bake_scene.sh        # imports ../IsaacSim/starship/starship.usd -> starship.blend
```

### Manual / pick-your-own-scene
You can drive this by hand instead of via compose's command:
- **`File ▸ Open ▸ starship.blend`** — note `File ▸ Open` only lists `.blend` files
  (that's why browsing the `starship/` folder showed just `__pycache__` — the `.usd`
  was filtered out).
- To load a raw USD by hand: **`File ▸ Import ▸ Universal Scene Description (.usd)`**.
- Either way, run the driver afterward via the **Scripting** workspace (open
  `blender_starship_driver.py`, press ▶) — it attaches to telemetry and drives
  whatever Starship object is in the scene.

To capture for a demo video: **OBS → Window Capture → the Blender window**
(same OBS you used for the ROSA captures).

### Telemetry source
- `TELEM_SOURCE=http` (default) — polls `/telemetry/latest`. Non-invasive: it does
  **not** consume the UDP stream, so the Jetson HIL leg keeps working unchanged.
- `TELEM_SOURCE=udp` — binds `:50505` and unpacks the 64-byte `<Id13f` datagram.
  Lowest latency, but point-to-point: only use it when the Jetson isn't also
  consuming that stream. Requires `TELEMETRY_UDP_HOST=127.0.0.1` on the Isaac side.

### Coordinate frames (the one fiddly bit)
Isaac/USD is **Y-up**, Blender is **Z-up**. The driver maps the live pose by
`R = Rx(+90°)`: `location → (x,-z,y)`, `orientation → R·q·R⁻¹`. If attitude looks
mirrored, flip to the `LEFT_MULTIPLY` branch in `blender_starship_driver.py` and/or
re-import the USD with up-axis conversion off. Verify with a known attitude
(USD identity quaternion = nose-up → should point +Z in Blender).

### Wayland
If `echo $XDG_SESSION_TYPE` says `wayland`, Blender runs as an XWayland client and
the `/tmp/.X11-unix` mount still works; if the window misbehaves add
`-e GDK_BACKEND=x11`.

## Why this is a *Stack* (not DockerBuilds / Scripts)
It mirrors `Stacks/IsaacSim/` exactly: a self-contained unit with its own
Dockerfile + compose + scene + driver, that pairs with the IsaacSim stack and
shares its scene asset. The Dockerfile is *local to the stack* just like Isaac's
is — the build is incidental to the stack, not a standalone reusable image, so it
doesn't belong in `DockerBuilds/`. It's not wrapping a pre-existing image either,
so it isn't `Scripts/`.

## compose vs. the Rust `docker_runner`
Three different jobs, not competitors:

| Tool | Job |
|------|-----|
| `docker build` / `docker_builder` | Dockerfile → image (one-time) |
| `docker run` / `docker_runner` (`run_configuration.yml`) | launch **one** container from an image |
| `docker compose up` | declaratively bring up / tear down a **stack** (1+ containers): networks, named volumes, GPU reservations, lifecycle (`up`/`down`/`logs`/`restart`) |

We reach for **compose** here because (a) the sibling stacks (IsaacSim, ROS) are
compose, so this is consistent and can later join the same compose project /
share state, (b) it persists the GPU reservation + volumes declaratively, and (c)
`up`/`down`/`logs` lifecycle is free — which matters when the demo is Isaac + ROS +
Blender together.

Your **`docker_runner` is a perfectly good peer** for launching just this one
container — `run_configuration.yml` here is the exact equivalent. Compose isn't
"better at running a container"; it's better at orchestrating a *set* and
reproducing it declaratively. For Blender-alone, the typed-YAML runner is arguably
nicer. The only gap today: `RunConfiguration` has no `network` field, so the runner
can't do `--network host`; the config works around it by reaching the host via the
bridge gateway `172.17.0.1`. Adding `network: Option<String>` (mirroring the
existing `ipc` field in `run_configuration.rs` + `build_run_command.rs`) would
close the gap and let it use host networking like compose.
