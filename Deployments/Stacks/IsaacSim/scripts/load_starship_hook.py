"""
load_starship_hook.py — Kit --exec startup hook for streaming mode.

Runs after the Kit app (isaacsim.exp.full.streaming.kit) is initialised.
Opens ISAAC_SCENE_PATH (default: starship.usd) and starts the timeline so
the Starship is visible in the WebRTC viewport immediately.

Connection URL after Isaac starts:
    http://localhost:8211/streaming/webrtc-client/?server=localhost
"""

import asyncio
import os

import omni.kit.app
import omni.timeline
import omni.usd

_SCENE_PATH = os.environ.get(
    "ISAAC_SCENE_PATH",
    "/isaac-sim/exts/starship/starship.usd",
)


async def _load_scene() -> None:
    app = omni.kit.app.get_app()

    # Wait for Kit to finish extension loading before touching the stage.
    for _ in range(120):  # up to ~4 s at 30 fps
        await app.next_update_async()

    if not _SCENE_PATH or not os.path.isfile(_SCENE_PATH):
        print(f"[starship-hook] ISAAC_SCENE_PATH={_SCENE_PATH!r} not found — empty stage")
        return

    print(f"[starship-hook] Opening stage: {_SCENE_PATH}")
    success = await omni.usd.get_context().open_stage_async(_SCENE_PATH)
    if not success:
        print("[starship-hook] WARNING: open_stage_async returned False — stage may not have loaded")
        return

    # Wait a few more frames for the stage to fully hydrate in the renderer.
    for _ in range(30):
        await app.next_update_async()

    omni.timeline.get_timeline_interface().play()
    print("[starship-hook] Stage loaded and timeline playing — Starship should be visible")


asyncio.ensure_future(_load_scene())
