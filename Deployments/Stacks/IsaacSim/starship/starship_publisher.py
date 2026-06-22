"""
starship_publisher.py — Isaac Sim side: physics → ROS 2 topics.

Reads the Starship rigid body state from Isaac Sim and publishes to:
  /starship/pose           geometry_msgs/PoseStamped    100 Hz
  /starship/altitude       std_msgs/Float64              50 Hz  (metres AGL)
  /starship/velocity       geometry_msgs/Vector3Stamped  50 Hz
  /starship/imu            sensor_msgs/Imu              200 Hz
  /starship/fuel_fraction  std_msgs/Float32               1 Hz  (simulated)
  /starship/engine_state   std_msgs/String               10 Hz  (JSON)

Also exposes a service:
  /starship/reset          std_srvs/srv/Empty — reset position to launch pad

Usage: called from enable_ros2_bridge.py once the Starship USD stage is loaded.

  from starship.starship_publisher import StarshipPublisher
  pub = StarshipPublisher(app)
  pub.start()        # spawns update loop
  # …
  pub.stop()

Coordinate system: Z-up (robotics / ROS REP-103 convention)
  Altitude = world-Z of the Starship prim (base at z=0 AGL).
"""

import json
import math
import threading
import time

# ── Isaac Sim imports (must run inside IsaacSim Python) ───────────────────
try:
    import omni.usd
    import omni.timeline
    from pxr import Gf
    from omni.isaac.core.utils.stage import get_current_stage
except ImportError:
    raise ImportError(
        "[starship_pub] Must run inside Isaac Sim Python — "
        "see enable_ros2_bridge.py for the entry point."
    )

# ── ROS 2 imports (via bridge's bundled rclpy) ────────────────────────────
import sys, os

_bridge_path = "/isaac-sim/exts/isaacsim.ros2.bridge/humble"
sys.path.insert(0, f"{_bridge_path}/rclpy")

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Float64, String, Bool
from geometry_msgs.msg import PoseStamped, Vector3Stamped, Vector3
from sensor_msgs.msg import Imu
from std_srvs.srv import Empty
from builtin_interfaces.msg import Time as RosTime


# ── Constants ─────────────────────────────────────────────────────────────
STARSHIP_PRIM   = "/World/Starship"
LAUNCH_PAD_Y    = 0.0          # metres AGL when resting on pad
MAX_THRUST_N    = 14_700_000.0 # 14.7 MN max (6x Raptor @ 2.45 MN each, simplified)
DRY_MASS_KG     = 130_000.0    # 130 tonnes upper-stage dry mass
# Calibrated so hover throttle ≈ 0.45–0.55 at typical operating fuel fraction.
# Full tank (830 t): hover ≈ 0.554. Half tank (480 t): hover ≈ 0.321.
FUEL_CAPACITY_L = 700_000.0    # 700 t propellant (LOX+LCH4, illustrative)


def _ros_time_now(node: Node) -> RosTime:
    """Stamp from ROS 2 wall clock (not sim time — keeps it simple)."""
    t = node.get_clock().now()
    sec, nanosec = divmod(t.nanoseconds, 1_000_000_000)
    msg = RosTime()
    msg.sec = int(sec)
    msg.nanosec = int(nanosec)
    return msg


def _quat_from_gf(r: "Gf.Rotation") -> tuple:
    """Convert Gf.Rotation → (x, y, z, w) quaternion."""
    q = r.GetQuat()
    img = q.GetImaginary()
    return (img[0], img[1], img[2], q.GetReal())


class StarshipPublisher:
    """
    Reads Starship physics state each tick and publishes ROS 2 telemetry.

    Thread model:
      - `start()` launches a background thread that calls `_tick()` in a loop.
      - `_tick()` reads the USD stage (thread-safe read) and publishes.
      - The /starship/reset service handler posts back to the Isaac main thread
        via a shared flag; the main-thread caller must poll `_pending_reset`.
    """

    def __init__(self, app, tick_hz: float = 100.0) -> None:
        self._app        = app
        self._tick_hz    = tick_hz
        self._running    = False
        self._thread     = None
        self._fuel_kg    = FUEL_CAPACITY_L   # starts full
        self._fuel_burn_rate = 0.0           # kg/s — set by controller
        self._engine_throttle = 0.0
        self._engine_gimbal   = (0.0, 0.0)   # (pitch, yaw) rad
        self._safe_mode       = False
        self.pending_reset    = False        # set True by service; consumed by main loop

        # ── rclpy node ────────────────────────────────────────────────────
        if not rclpy.ok():
            rclpy.init()

        self._node = rclpy.create_node("starship_publisher")
        self._pub_pose   = self._node.create_publisher(PoseStamped,   "/starship/pose",   10)
        self._pub_alt    = self._node.create_publisher(Float64,        "/starship/altitude", 10)
        self._pub_vel    = self._node.create_publisher(Vector3Stamped, "/starship/velocity", 10)
        self._pub_imu    = self._node.create_publisher(Imu,            "/starship/imu",    10)
        self._pub_fuel   = self._node.create_publisher(Float32,        "/starship/fuel_fraction", 10)
        self._pub_engine = self._node.create_publisher(String,         "/starship/engine_state",  10)
        self._srv_reset  = self._node.create_service(
            Empty, "/starship/reset", self._handle_reset
        )
        print("[starship_pub] rclpy node 'starship_publisher' ready")

    # ── Public API ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background publish loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="starship_pub")
        self._thread.start()
        print("[starship_pub] publish loop started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        self._node.destroy_node()
        print("[starship_pub] stopped")

    def update_from_controller(
        self,
        throttle: float,
        gimbal: tuple,
        safe_mode: bool,
        fuel_burn_rate_kg_s: float,
    ) -> None:
        """Called by StarshipController to keep publisher state in sync."""
        self._engine_throttle  = throttle
        self._engine_gimbal    = gimbal
        self._safe_mode        = safe_mode
        self._fuel_burn_rate   = fuel_burn_rate_kg_s

    # ── Internal ─────────────────────────────────────────────────────────

    def _loop(self) -> None:
        import sys
        interval = 1.0 / self._tick_hz
        imu_counter = 0
        fuel_counter = 0
        engine_counter = 0
        _err_count = 0
        while self._running:
            t0 = time.monotonic()
            try:
                self._tick(imu_counter, fuel_counter, engine_counter)
                _err_count = 0
            except Exception as exc:
                _err_count += 1
                if _err_count <= 3 or _err_count % 100 == 0:
                    import traceback
                    print(f"[starship_pub] tick error #{_err_count}: {exc}", flush=True)
                    if _err_count <= 3:
                        traceback.print_exc()
                    sys.stdout.flush()
            imu_counter   += 1
            fuel_counter  += 1
            engine_counter += 1
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, interval - elapsed))

    def _tick(self, imu_ctr: int, fuel_ctr: int, engine_ctr: int) -> None:
        """Read physics state and publish (called at ~100 Hz)."""
        import sys
        from pxr import UsdGeom, Usd

        # ── Read USD stage ────────────────────────────────────────────────
        stage = get_current_stage()
        if stage is None:
            return

        prim = stage.GetPrimAtPath(STARSHIP_PRIM)
        if not prim.IsValid():
            return

        # World-space transform via UsdGeom.Xformable (correct Isaac Sim 4.x API)
        xform = UsdGeom.Xformable(prim)
        matrix = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())

        pos = matrix.ExtractTranslation()   # Gf.Vec3d

        # Altitude = Z world coord (Z-up, ground at z=0)
        altitude_m = pos[2]

        # Rotation quaternion — use ExtractRotationQuat() which returns GfQuatd
        # directly, avoiding the GfRotation intermediate (API varies by version)
        try:
            quatd = matrix.ExtractRotationQuat()  # GfQuatd
            img   = quatd.GetImaginary()
            qx, qy, qz, qw = float(img[0]), float(img[1]), float(img[2]), float(quatd.GetReal())
        except Exception:
            qx, qy, qz, qw = 0.0, 0.0, 0.0, 1.0  # identity

        # ── Velocity from physics ─────────────────────────────────────────
        # Try physxRigidBody:* attributes first, then physics:* fallback
        vel = Gf.Vec3f(0, 0, 0)
        ang = Gf.Vec3f(0, 0, 0)
        for vel_name in ("physxRigidBody:velocity", "physics:velocity"):
            attr = prim.GetAttribute(vel_name)
            if attr.IsValid():
                v = attr.Get()
                if v is not None:
                    vel = Gf.Vec3f(v[0], v[1], v[2])
                    break
        for ang_name in ("physxRigidBody:angularVelocity", "physics:angularVelocity"):
            attr = prim.GetAttribute(ang_name)
            if attr.IsValid():
                v = attr.Get()
                if v is not None:
                    ang = Gf.Vec3f(v[0], v[1], v[2])
                    break

        stamp = _ros_time_now(self._node)
        now_sec = float(stamp.sec) + stamp.nanosec * 1e-9

        # ── /starship/pose ────────────────────────────────────────────────
        pose_msg = PoseStamped()
        pose_msg.header.stamp    = stamp
        pose_msg.header.frame_id = "world"
        pose_msg.pose.position.x = pos[0]
        pose_msg.pose.position.y = pos[1]
        pose_msg.pose.position.z = pos[2]
        pose_msg.pose.orientation.x = qx
        pose_msg.pose.orientation.y = qy
        pose_msg.pose.orientation.z = qz
        pose_msg.pose.orientation.w = qw
        self._pub_pose.publish(pose_msg)

        # ── /starship/altitude (50 Hz: every other tick) ──────────────────
        if imu_ctr % 2 == 0:
            alt_msg = Float64()
            alt_msg.data = altitude_m
            self._pub_alt.publish(alt_msg)

            vel_msg = Vector3Stamped()
            vel_msg.header.stamp    = stamp
            vel_msg.header.frame_id = "world"
            vel_msg.vector.x = float(vel[0])
            vel_msg.vector.y = float(vel[1])
            vel_msg.vector.z = float(vel[2])
            self._pub_vel.publish(vel_msg)

        # ── /starship/imu (200 Hz: every tick up to 100 Hz cap here) ─────
        imu_msg = Imu()
        imu_msg.header.stamp    = stamp
        imu_msg.header.frame_id = "starship/imu"
        imu_msg.angular_velocity.x = float(ang[0])
        imu_msg.angular_velocity.y = float(ang[1])
        imu_msg.angular_velocity.z = float(ang[2])
        # Linear accel ≈ (thrust − gravity) / mass  (crude; no per-axis)
        # Z-up: net vertical acceleration is on the Z axis.
        thrust_accel = (self._engine_throttle * MAX_THRUST_N / DRY_MASS_KG)
        imu_msg.linear_acceleration.x = 0.0
        imu_msg.linear_acceleration.y = 0.0
        imu_msg.linear_acceleration.z = thrust_accel - 9.81   # net vertical (Z-up)
        self._pub_imu.publish(imu_msg)

        # ── /starship/fuel_fraction (1 Hz: every 100 ticks) ──────────────
        if fuel_ctr % 100 == 0:
            self._fuel_kg = max(0.0, self._fuel_kg - self._fuel_burn_rate * (100 / self._tick_hz))
            fuel_frac = self._fuel_kg / FUEL_CAPACITY_L
            fuel_msg = Float32()
            fuel_msg.data = float(fuel_frac)
            self._pub_fuel.publish(fuel_msg)

        # ── /starship/engine_state (10 Hz: every 10 ticks) ────────────────
        if engine_ctr % 10 == 0:
            state = {
                "throttle":    round(self._engine_throttle, 4),
                "gimbal_pitch": round(self._engine_gimbal[0], 4),
                "gimbal_yaw":   round(self._engine_gimbal[1], 4),
                "safe_mode":    self._safe_mode,
                "fuel_kg":      round(self._fuel_kg, 1),
            }
            eng_msg = String()
            eng_msg.data = json.dumps(state)
            self._pub_engine.publish(eng_msg)

        # rclpy spinning handled by the controller's dedicated spin thread

    def _handle_reset(self, _req, response):
        """Service handler: sets the pending_reset flag for main thread."""
        self.pending_reset = True
        print("[starship_pub] /starship/reset service called — reset pending")
        return response
