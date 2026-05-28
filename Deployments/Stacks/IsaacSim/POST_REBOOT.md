# Post-reboot checklist — headless mode (Zephyrus G15 laptop)

**Confirmed 2026-05-27**: windowed and streaming both fail on this machine.
Headless is the only working Isaac Sim mode. See "Confirmed failures" at the bottom.

---

## 1. Re-add swapfile if lost on reboot

```bash
swapon --show   # if empty, swap is gone — re-add it:
sudo fallocate -l 8G /tmp/swapfile && sudo chmod 600 /tmp/swapfile && sudo mkswap /tmp/swapfile && sudo swapon /tmp/swapfile
free -h         # Swap row should show ~8–9G
```

Isaac Sim peaks at ~10 GB RAM during shader warm-up. Without swap it OOM-kills silently.

---

## 2. Start Isaac Sim (headless)

`.env` must have `ISAAC_MODE=headless`. Verify before starting:

```bash
cd ~/.openclaw/workspace/workspace2/repos/Monoclaw/Deployments/Stacks/IsaacSim
grep ISAAC_MODE .env    # must show: ISAAC_MODE=headless
```

Then start:

```bash
docker compose down
docker compose up -d
docker logs -f isaac-sim 2>&1 | grep -E "rosa|ready|Error|clock"
```

Wait for both:
```
[rosa] Isaac control API on http://0.0.0.0:8282
[rosa] Physics simulation started
```

First boot after swapfile loss: shader compilation can take 5-20 min (CPU at 200%+).
Warm cache: ~2-3 min.

Verify:
```bash
curl -s http://localhost:8282/health   # → {"status":"ok",...}
```

---

## 3. Load the Starship scene (first boot, or after code changes)

```bash
curl -s -X POST http://localhost:8282/starship/create-stage
docker compose restart isaac
# Wait ~2 min for restart
curl -s http://localhost:8282/health
```

If the USD already exists and you haven't changed `create_stage.py`, skip this — the
scene is pre-loaded via `ISAAC_SCENE_PATH` in `.env`.

---

## 4. Run the demo

```bash
cd ~/.openclaw/workspace/workspace2/repos/rosa
./run_demo.sh
```

`run_demo.sh` will start the `rosa-ros2` container if it's not already running.

---

## Confirmed failures — do not attempt on this laptop

| Mode | Command | Failure | Reason |
|------|---------|---------|--------|
| Windowed | `ISAAC_MODE=windowed` | `vkCreateSwapchainKHR failed` | RTX 3070 is compute-only in Docker; AMD iGPU drives the display — Vulkan can't create a swapchain for it |
| Streaming | `ISAAC_MODE=streaming` | Never starts | NvFBC GPU capture required; blocked on all GeForce/laptop GPUs by NVIDIA |
| PRIME sync | host X11 passthrough | N/A | PRIME render offload is a host-level X11 config; not viable inside Docker |

Windowed mode was confirmed broken 2026-05-27 even after `xhost +local:docker`.
The X server became accessible (no more "Authorization required") but the Vulkan
swapchain creation still fails because the RTX 3070 is not the display GPU.

---

## Demo prompts (see rosa/DEMO.md for full list)

```
> What is the current altitude, fuel fraction, and engine state?
> The vehicle is slowly climbing. Compute the precise hover throttle for the current fuel mass and apply it.
> Execute a controlled descent to 800 m, then hold station.
> ABORT! Emergency abort! Safe the vehicle immediately!
> Fuel is at 3% and we are at 400 m. What do you do?
```
