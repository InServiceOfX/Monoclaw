"""
load_starship_hook.py — Kit --exec startup hook for windowed/streaming mode.

Runs after the Kit app initialises. Full Starship setup in one shot:
  1. Opens ISAAC_SCENE_PATH (default: starship.usd)
  2. Starts StarshipPublisher  (physics → ROS 2 topics)
  3. Starts StarshipController (ROS 2 commands → physics forces)
  4. Hooks controller.apply_forces into the PhysX step (main thread, every frame)
  5. Starts the timeline

No Script Editor copy-paste needed — just start Isaac Sim and it's live.
"""

import asyncio
import os
import sys

sys.path.insert(0, "/isaac-sim/exts/starship")
sys.path.insert(0, "/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")

import omni.kit.app
import omni.physx
import omni.timeline
import omni.usd

_SCENE_PATH = (
    os.environ.get("ISAAC_SCENE_PATH")
    or "/isaac-sim/exts/starship/starship.usd"
)

# Module-level refs so the GC doesn't collect the subscription handle
_pub = None
_ctrl = None
_physx_sub = None


async def _setup() -> None:
    global _pub, _ctrl, _physx_sub

    app = omni.kit.app.get_app()

    # Wait for all extensions to finish loading before touching the stage
    for _ in range(120):
        await app.next_update_async()

    # ── Load stage ────────────────────────────────────────────────────────────
    if not _SCENE_PATH or not os.path.isfile(_SCENE_PATH):
        print(f"[starship-hook] ISAAC_SCENE_PATH={_SCENE_PATH!r} not found — empty stage")
        return

    print(f"[starship-hook] Opening stage: {_SCENE_PATH}")
    success = await omni.usd.get_context().open_stage_async(_SCENE_PATH)
    if not success:
        print("[starship-hook] WARNING: open_stage_async returned False — stage may not have loaded")
        return

    # Let the renderer fully hydrate the stage before starting physics threads
    for _ in range(30):
        await app.next_update_async()

    # ── Publisher (physics → ROS 2 topics) ───────────────────────────────────
    from starship_publisher import StarshipPublisher
    _pub = StarshipPublisher(app)
    _pub.start()

    # ── Controller (ROS 2 commands → physics forces) ─────────────────────────
    from starship_controller import StarshipController
    _ctrl = StarshipController(app, _pub)
    _ctrl.start()

    # ── Physics step hook — apply_forces MUST run on the main thread ─────────
    # subscribe_physics_step_events fires on the Isaac Sim main thread each
    # simulation step, which is the only safe place to call PhysX force APIs.
    def _on_physics_step(dt: float) -> None:
        _ctrl.apply_forces(dt)

    _physx_sub = omni.physx.get_physx_interface().subscribe_physics_step_events(
        _on_physics_step
    )

    # ── Start simulation ──────────────────────────────────────────────────────
    omni.timeline.get_timeline_interface().play()

    print("[starship-hook] Stage loaded and timeline playing.")
    print("[starship-hook] Publisher + controller + physics hook active.")
    print("[starship-hook] ROS 2 /starship/* topics live — ready for rosa commands.")


asyncio.ensure_future(_setup())
