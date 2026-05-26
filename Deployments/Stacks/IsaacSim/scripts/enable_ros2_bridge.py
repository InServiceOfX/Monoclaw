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
else:
    if scene_path:
        print(f"[rosa] ISAAC_SCENE_PATH={scene_path!r} not found — using empty stage")
    else:
        print("[rosa] No scene path set — using empty stage (ROS bridge + clock only)")

# ── OmniGraph: wire /clock publisher ──────────────────────────────────────────
# In Isaac Sim 4.x, enabling the bridge extension does NOT publish /clock.
# Topics are produced only by OmniGraph nodes triggered by OnPlaybackTick.
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
                    ("OnPlaybackTick.outputs:tick",        "PublishClock.inputs:execIn"),
                    ("Context.outputs:context",            "PublishClock.inputs:context"),
                    ("ReadSimTime.outputs:simulationTime", "PublishClock.inputs:timeStamp"),
                ],
            },
        )
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
            _cmd_queue.put({"type": "load_scene", "path": path})
            self._send_json({"status": "queued", "path": path})
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
    elif cmd_type == "load_scene":
        path = cmd.get("path", "")
        if path:
            print(f"[rosa] Loading scene from API: {path}")
            omni.usd.get_context().open_stage(path)


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
        app.update()

except KeyboardInterrupt:
    print("\n[rosa] Caught interrupt — shutting down")
finally:
    timeline.stop()
    app.close()
    print("[rosa] Isaac Sim stopped")
