"""
Isaac Sim headless startup script.

Launches SimulationApp in headless mode, enables the ROS 2 bridge extension,
creates an OmniGraph Action Graph to publish /clock (and optionally /tf_static),
then opens a stage and starts the simulation timeline.

In Isaac Sim 4.x the ROS 2 bridge no longer auto-publishes /clock when the
extension is enabled.  Topics are only produced by OmniGraph nodes wired to an
OnPlaybackTick event.  This script builds the minimum graph required:

    OnPlaybackTick  ──execIn──►  ROS2PublishClock
    ROS2Context     ──context──► ROS2PublishClock
    IsaacReadSimulationTime ─► ROS2PublishClock

Usage (via start_isaac.sh):
    /isaac-sim/python.sh /isaac-sim/scripts/enable_ros2_bridge.py

Environment variables:
    ISAAC_SCENE_PATH   — optional: absolute path to a USD scene to load
    ROS_DOMAIN_ID      — forwarded from container env (default 0)
    RMW_IMPLEMENTATION — forwarded from container env (default rmw_cyclonedds_cpp)
"""

import os
import time

# SimulationApp must be created before any other omni imports.
from isaacsim import SimulationApp

CONFIG = {
    "headless": True,
    "anti_aliasing": 0,       # disable MSAA in headless — saves VRAM
    "renderer": "RayTracedLighting",
    "width": 1280,
    "height": 720,
}

print("[rosa] Starting Isaac Sim headless...")
app = SimulationApp(CONFIG)

# ── Extensions ────────────────────────────────────────────────────────────────
import omni.kit.app

manager = omni.kit.app.get_app().get_extension_manager()

# Enable the ROS 2 bridge (name changed from omni.isaac.ros2_bridge in 4.x)
bridge_enabled = False
for ext_name in ("isaacsim.ros2.bridge", "omni.isaac.ros2_bridge"):
    if manager.is_extension_enabled(ext_name):
        print(f"[rosa] {ext_name} already enabled")
        bridge_enabled = True
        break
    if manager.set_extension_enabled_immediate(ext_name, True):
        print(f"[rosa] Enabled extension: {ext_name}")
        bridge_enabled = True
        break

if not bridge_enabled:
    print("[rosa] WARNING: could not enable ROS 2 bridge extension — topics may not publish")

# ── Stage ─────────────────────────────────────────────────────────────────────
import omni.usd

scene_path = os.environ.get("ISAAC_SCENE_PATH", "")
if scene_path and os.path.isfile(scene_path):
    print(f"[rosa] Loading scene: {scene_path}")
    omni.usd.get_context().open_stage(scene_path)
    # Give the stage loader time to finish
    for _ in range(30):
        app.update()
        time.sleep(0.1)
    print("[rosa] Scene loaded")
else:
    if scene_path:
        print(f"[rosa] ISAAC_SCENE_PATH={scene_path!r} not found — using empty stage")
    else:
        print("[rosa] No scene path set — using empty stage (ROS bridge + clock only)")

# ── OmniGraph: wire /clock publisher ──────────────────────────────────────────
# In Isaac Sim 4.x, simply enabling the bridge extension does NOT publish
# /clock.  Topics are produced only by OmniGraph nodes triggered by
# OnPlaybackTick.  We build the minimum graph here programmatically.
if bridge_enabled:
    try:
        import omni.graph.core as og

        og.Controller.edit(
            {"graph_path": "/ActionGraph/ROS_Clock", "evaluator_name": "execution"},
            {
                og.Controller.Keys.CREATE_NODES: [
                    ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                    ("ReadSimTime",    "isaacsim.core.nodes.IsaacReadSimulationTime"),
                    ("Context",        "isaacsim.ros2.bridge.ROS2Context"),
                    ("PublishClock",   "isaacsim.ros2.bridge.ROS2PublishClock"),
                ],
                og.Controller.Keys.CONNECT: [
                    ("OnPlaybackTick.outputs:tick",         "PublishClock.inputs:execIn"),
                    ("Context.outputs:context",             "PublishClock.inputs:context"),
                    ("ReadSimTime.outputs:simulationTime",  "PublishClock.inputs:timeStamp"),
                ],
            },
        )
        # Run a few frames so the graph evaluates and the publisher registers.
        for _ in range(10):
            app.update()
        print("[rosa] OmniGraph /clock publisher created")
    except Exception as exc:
        print(f"[rosa] WARNING: could not create clock OmniGraph: {exc}")

# ── Timeline: start playing so /clock ticks ───────────────────────────────────
import omni.timeline
timeline = omni.timeline.get_timeline_interface()
timeline.play()
print("[rosa] Simulation timeline started")
print("[rosa] /clock should now be visible on the ROS 2 network")
print("[rosa] ROS_DOMAIN_ID =", os.environ.get("ROS_DOMAIN_ID", "0"))
print("[rosa] RMW           =", os.environ.get("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp"))
print("[rosa] Isaac Sim running — Ctrl-C or SIGTERM to stop")

# ── Main loop ─────────────────────────────────────────────────────────────────
try:
    while app.is_running():
        app.update()
except KeyboardInterrupt:
    print("\n[rosa] Caught interrupt — shutting down")
finally:
    timeline.stop()
    app.close()
    print("[rosa] Isaac Sim stopped")
