"""
Isaac Sim headless startup script.

Launches SimulationApp in headless mode, enables the ROS 2 bridge extension,
creates an OmniGraph Action Graph to publish /clock, and starts an HTTP control
server so the external rosa-isaac Rust tools can control the simulation.

In Isaac Sim 4.x the ROS 2 bridge no longer auto-publishes /clock when the
extension is enabled.  Topics are only produced by OmniGraph nodes wired to an
OnPlaybackTick event.  This script builds the minimum graph required:

    OnPlaybackTick ──execIn──► ROS2PublishClock
    ROS2Context    ──context──► ROS2PublishClock
    IsaacReadSimulationTime ──► ROS2PublishClock

HTTP control server (default port 8282, override with ISAAC_CONTROL_PORT):
    GET  /health          — health check (always 200)
    GET  /diagnostics     — sim stats JSON (fps, sim_time, running, physics_dt)
    GET  /scene/list      — list known USD scene paths
    POST /timeline/play   — start timeline
    POST /timeline/stop   — stop timeline (rewinds to t=0)
    POST /timeline/pause  — pause timeline (keeps state)
    POST /scene/load      — load a USD scene, body: {"path": "/...usd"}

Usage (via start_isaac.sh):
    /isaac-sim/python.sh /isaac-sim/scripts/enable_ros2_bridge.py

Environment variables:
    ISAAC_SCENE_PATH    — optional: absolute path to a .usd file to preload
    ISAAC_CONTROL_PORT  — HTTP control server port (default 8282)
    ROS_DOMAIN_ID       — forwarded from container env (default 0)
    RMW_IMPLEMENTATION  — forwarded from container env (default rmw_cyclonedds_cpp)
"""

import json
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# SimulationApp must be created before any other omni imports.
from isaacsim import SimulationApp

CONFIG = {
    "headless": True,
    "anti_aliasing": 0,       # disable MSAA in headless — saves VRAM
    "renderer": "RayTracedLighting",
    "width": 1280,
    "height": 720,
    # Pre-declare the ROS 2 bridge as a startup extension so it loads as part
    # of SimulationApp initialization rather than as a post-init call.
    # This may reduce boot time by loading the bridge in parallel with other
    # startup extensions rather than serially after app.ready().
    "/isaac/startup/ros_bridge_extension": "isaacsim.ros2.bridge",
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
    for _ in range(30):
        app.update()
        time.sleep(0.1)
    print("[rosa] Scene loaded")
    # Start Starship sim modules if starship.usd was preloaded
    # (deferred to after OmniGraph clock is created — we do it after the loop below)
    _preload_scene_path = scene_path
else:
    _preload_scene_path = ""
    if scene_path:
        print(f"[rosa] ISAAC_SCENE_PATH={scene_path!r} not found — using empty stage")
    else:
        print("[rosa] No scene path set — using empty stage (ROS bridge + clock only)")

# ── OmniGraph: wire /clock publisher ──────────────────────────────────────────
# In Isaac Sim 4.x, enabling the bridge extension does NOT publish /clock.
# Topics are produced only by OmniGraph nodes triggered by OnPlaybackTick.
# This must be called once on startup AND again after any open_stage() call
# (a new stage wipes out all OmniGraph nodes in the previous stage).

def _create_clock_omnigraph() -> bool:
    """Create/recreate the OmniGraph clock publisher. Returns True on success."""
    if not bridge_enabled:
        return False
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
                    ("OnPlaybackTick.outputs:tick",        "PublishClock.inputs:execIn"),
                    ("Context.outputs:context",            "PublishClock.inputs:context"),
                    ("ReadSimTime.outputs:simulationTime", "PublishClock.inputs:timeStamp"),
                ],
            },
        )
        print("[rosa] OmniGraph /clock publisher created")
        return True
    except Exception as exc:
        print(f"[rosa] WARNING: could not create clock OmniGraph: {exc}")
        return False

if _create_clock_omnigraph():
    for _ in range(10):
        app.update()

# ── Timeline: start playing so /clock ticks ───────────────────────────────────
import omni.timeline
timeline = omni.timeline.get_timeline_interface()
timeline.play()
print("[rosa] Simulation timeline started")
print("[rosa] /clock should now be visible on the ROS 2 network")
print("[rosa] ROS_DOMAIN_ID =", os.environ.get("ROS_DOMAIN_ID", "0"))
print("[rosa] RMW           =", os.environ.get("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp"))

# ── HTTP control server ───────────────────────────────────────────────────────
# All Isaac Sim API calls MUST happen on the main thread.
# The HTTP handler writes commands into a thread-safe queue; the main loop
# (below) drains the queue after each frame.

_cmd_queue: "queue.Queue[dict]" = queue.Queue()

# Shared diagnostics dict — written by main thread, read by HTTP handler.
# A small race condition exists on reads; acceptable for diagnostics.
_diag: dict = {
    "running":    False,
    "sim_time":   0.0,
    "fps":        0.0,
    "physics_dt": 0.0,
}

# Known USD scene paths (populated on startup; also lists /scene/list-known dirs)
_SCENE_DIRS = [
    "/isaac-sim/exts/starship",
    "/isaac-sim/Assets/Isaac/4.5",
]

def _list_usd_scenes() -> list[str]:
    scenes: list[str] = []
    for d in _SCENE_DIRS:
        if os.path.isdir(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.endswith((".usd", ".usda", ".usdc")):
                        scenes.append(os.path.join(root, f))
    return scenes


class _ControlHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for the Isaac Sim control API."""

    def log_message(self, fmt, *args):  # suppress default access log
        pass

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length).decode()) if length else {}

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok"})
        elif self.path == "/diagnostics":
            self._send_json(dict(_diag))
        elif self.path == "/scene/list":
            self._send_json({"scenes": _list_usd_scenes()})
        elif self.path == "/starship/stage-status":
            exists = os.path.isfile(_STARSHIP_USD_PATH)
            self._send_json({
                "path": _STARSHIP_USD_PATH,
                "exists": exists,
                "size_bytes": os.path.getsize(_STARSHIP_USD_PATH) if exists else 0,
            })
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path in ("/timeline/play", "/timeline/stop", "/timeline/pause"):
            action = self.path.rsplit("/", 1)[-1]   # play | stop | pause
            _cmd_queue.put({"type": "timeline", "action": action})
            self._send_json({"status": "queued", "action": action})
        elif self.path == "/scene/load":
            body = self._read_json_body()
            path = body.get("path", "")
            if not path:
                self._send_json({"error": "'path' field required"}, 400)
                return
            if not os.path.isfile(path):
                self._send_json({"error": f"file not found: {path}"}, 404)
                return
            _cmd_queue.put({"type": "load_scene", "path": path})
            self._send_json({"status": "queued", "path": path})
        elif self.path == "/starship/create-stage":
            # Create the Starship USD stage from within the running SimulationApp
            # (pxr is only available inside the Kit runtime process).
            _cmd_queue.put({"type": "create_starship_stage"})
            self._send_json({"status": "queued", "output": _STARSHIP_USD_PATH})
        else:
            self._send_json({"error": "not found"}, 404)


def _run_control_server(port: int) -> None:
    server = HTTPServer(("0.0.0.0", port), _ControlHandler)
    print(f"[rosa] Isaac control API on http://0.0.0.0:{port}")
    server.serve_forever()


control_port = int(os.environ.get("ISAAC_CONTROL_PORT", "8282"))
_server_thread = threading.Thread(
    target=_run_control_server, args=(control_port,), daemon=True
)
_server_thread.start()


# ── Helpers for main-thread command execution ─────────────────────────────────

# ── Starship sim modules (optional — loaded when starship.usd is active) ─────
_starship_publisher  = None
_starship_controller = None
_STARSHIP_USD_PATH   = "/isaac-sim/exts/starship/starship.usd"


def _maybe_start_starship(stage_path: str) -> None:
    """Load Starship publisher + controller if the Starship USD is active."""
    global _starship_publisher, _starship_controller
    if _STARSHIP_USD_PATH not in stage_path:
        return
    if _starship_publisher is not None:
        return  # already running

    try:
        import sys, importlib
        starship_dir = "/isaac-sim/exts/starship"
        if starship_dir not in sys.path:
            sys.path.insert(0, starship_dir)
        # Force re-import from disk (volume-mounted scripts may have changed)
        for mod_name in ("starship_publisher", "starship_controller"):
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
        from starship_publisher import StarshipPublisher
        from starship_controller import StarshipController

        _starship_publisher  = StarshipPublisher(app)
        _starship_controller = StarshipController(app, _starship_publisher)
        _starship_publisher.start()
        _starship_controller.start()
        print("[rosa] Starship publisher + controller started")
    except Exception as exc:
        print(f"[rosa] WARNING: could not start Starship sim modules: {exc}")


def _create_starship_stage_inline() -> None:
    """
    Generate /isaac-sim/exts/starship/starship.usd from within the running
    SimulationApp process where pxr (USD Python bindings) is available.
    Mirrors the logic in starship/create_stage.py but runs in-process.
    """
    try:
        from pxr import Gf, UsdGeom, UsdPhysics, Sdf, Usd, PhysxSchema

        out = _STARSHIP_USD_PATH
        os.makedirs(os.path.dirname(out), exist_ok=True)

        stage = Usd.Stage.CreateNew(out)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)

        world = UsdGeom.Xform.Define(stage, "/World")
        stage.SetDefaultPrim(world.GetPrim())

        physics_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
        physics_scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, -1.0, 0.0))
        physics_scene.CreateGravityMagnitudeAttr(9.81)
        physx_scene = PhysxSchema.PhysxSceneAPI.Apply(physics_scene.GetPrim())
        # Enable GPU dynamics if the API supports it (Isaac Sim 4.5 attribute name varies)
        for attr_name in ("CreateGpuDynamicsEnabledAttr", "CreateEnableGPUDynamicsAttr"):
            fn = getattr(physx_scene, attr_name, None)
            if fn:
                fn(True)
                break

        # Ground plane: use a Cube slab — PhysX handles box primitives reliably.
        # 1000×1×1000 m slab centered at y=-0.5 so top face is exactly at y=0.
        ground_xform = UsdGeom.Xform.Define(stage, "/World/GroundPlane")
        ground_xform.AddTranslateOp().Set(Gf.Vec3d(0, -0.5, 0))
        ground_cube = UsdGeom.Cube.Define(stage, "/World/GroundPlane/Geom")
        ground_cube.CreateSizeAttr(1.0)
        ground_cube.AddScaleOp().Set(Gf.Vec3f(1000.0, 1.0, 1000.0))
        ground_cube.CreateDisplayColorAttr([Gf.Vec3f(0.3, 0.3, 0.3)])
        UsdPhysics.CollisionAPI.Apply(ground_cube.GetPrim())

        starship_xform = UsdGeom.Xform.Define(stage, "/World/Starship")
        # Center at y=29.5 so base is at y=0 (ground level).
        # Capsule: cylinder height=50m + 2x hemisphere radius=4.5m → total 59m.
        # Bottom = center_y − (height/2 + radius) = 29.5 − (25+4.5) = 0 ✓
        starship_xform.AddTranslateOp().Set(Gf.Vec3d(0, 29.5, 0))
        capsule = UsdGeom.Capsule.Define(stage, "/World/Starship/Body")
        capsule.CreateRadiusAttr(4.5)
        capsule.CreateHeightAttr(50.0)
        capsule.CreateAxisAttr("Y")
        capsule.CreateDisplayColorAttr([Gf.Vec3f(0.8, 0.8, 0.85)])
        UsdPhysics.RigidBodyAPI.Apply(starship_xform.GetPrim())
        UsdPhysics.CollisionAPI.Apply(capsule.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(starship_xform.GetPrim())
        mass_api.CreateMassAttr(130000.0)

        camera_xform = UsdGeom.Xform.Define(stage, "/World/Starship/Camera")
        camera_xform.AddTranslateOp().Set(Gf.Vec3d(0, 27, 0))
        camera_xform.AddRotateXYZOp().Set(Gf.Vec3f(-90, 0, 0))
        camera = UsdGeom.Camera.Define(stage, "/World/Starship/Camera/Sensor")
        camera.CreateProjectionAttr(UsdGeom.Tokens.perspective)
        camera.CreateFocalLengthAttr(24.0)
        camera.CreateHorizontalApertureAttr(20.955)
        camera.CreateVerticalApertureAttr(15.2908)
        camera.CreateClippingRangeAttr(Gf.Vec2f(0.1, 10000.0))

        stage.GetPrimAtPath("/World/Starship").SetCustomDataByKey(
            "ros2_topic_namespace", "starship"
        )
        stage.Save()
        print(f"[rosa] Starship stage created: {out}")

    except Exception as exc:
        print(f"[rosa] ERROR creating Starship stage: {exc}")


def _handle_cmd(cmd: dict) -> None:
    cmd_type = cmd.get("type")
    if cmd_type == "timeline":
        action = cmd.get("action")
        if action == "play":
            timeline.play()
        elif action == "stop":
            timeline.stop()
        elif action == "pause":
            timeline.pause()
    elif cmd_type == "create_starship_stage":
        _create_starship_stage_inline()
    elif cmd_type == "load_scene":
        path = cmd.get("path", "")
        if path:
            if not os.path.isfile(path):
                print(f"[rosa] load_scene SKIPPED — path not found: {path!r}")
                return
            print(f"[rosa] Loading scene from API: {path}")
            omni.usd.get_context().open_stage(path)
            # Stop → ensures PhysX resets all rigid bodies to their USD-defined
            # initial positions (t=0).  Then play restarts the simulation.
            timeline.stop()
            # Wait for stage to settle, then restore /clock OmniGraph
            # (open_stage wipes all OmniGraph nodes from the previous stage)
            for _ in range(30):
                app.update()
            _create_clock_omnigraph()
            timeline.play()
            for _ in range(10):
                app.update()
            _maybe_start_starship(path)


def _update_diag() -> None:
    """Refresh _diag with current sim stats (called every frame)."""
    try:
        import carb
        _diag["running"]  = timeline.is_playing()
        _diag["sim_time"] = timeline.get_current_time()
        # fps from kit settings (not always available — best-effort)
        fps = carb.settings.get_settings().get("/app/runLoops/main/rateLimitFrequency")
        if fps:
            _diag["fps"] = float(fps)
    except Exception:
        pass


# ── Starship modules: start if stage was preloaded via ISAAC_SCENE_PATH ───────
if _preload_scene_path:
    _maybe_start_starship(_preload_scene_path)

# ── Main loop ─────────────────────────────────────────────────────────────────
print("[rosa] Isaac Sim running — Ctrl-C or SIGTERM to stop")

try:
    while app.is_running():
        # Drain command queue (max 10 per frame to avoid starvation).
        for _ in range(10):
            try:
                _handle_cmd(_cmd_queue.get_nowait())
            except queue.Empty:
                break

        _update_diag()

        # Apply Starship forces before physics step
        if _starship_controller is not None:
            _starship_controller.apply_forces(_diag.get("physics_dt", 1.0 / 60.0))

        # Handle pending reset from /starship/reset service
        if _starship_publisher is not None and _starship_publisher.pending_reset:
            _starship_publisher.pending_reset = False
            print("[rosa] Resetting Starship to launch-pad position")
            try:
                from pxr import Gf
                stage = omni.usd.get_context().get_stage()
                if stage:
                    prim = stage.GetPrimAtPath("/World/Starship")
                    if prim.IsValid():
                        from pxr import UsdGeom
                        xform = UsdGeom.Xformable(prim)
                        ops = xform.GetOrderedXformOps()
                        for op in ops:
                            if "translate" in op.GetOpName():
                                op.Set(Gf.Vec3d(0, 25, 0))
                        # Zero velocity via physics attrs
                        vel_attr = prim.GetAttribute("physics:velocity")
                        if vel_attr.IsValid():
                            vel_attr.Set(Gf.Vec3f(0, 0, 0))
                        ang_attr = prim.GetAttribute("physics:angularVelocity")
                        if ang_attr.IsValid():
                            ang_attr.Set(Gf.Vec3f(0, 0, 0))
            except Exception as exc:
                print(f"[rosa] Reset error: {exc}")

        app.update()

except KeyboardInterrupt:
    print("\n[rosa] Caught interrupt — shutting down")
finally:
    if _starship_controller is not None:
        _starship_controller.stop()
    if _starship_publisher is not None:
        _starship_publisher.stop()
    timeline.stop()
    app.close()
    print("[rosa] Isaac Sim stopped")
