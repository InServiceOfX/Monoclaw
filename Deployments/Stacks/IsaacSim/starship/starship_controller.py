"""
starship_controller.py — Isaac Sim side: ROS 2 commands → physics forces.

Subscribes to ROS 2 command topics and applies external forces/torques to
the Starship rigid body each simulation step.

Command topics (write-only from rosa agent):
  /starship/main_throttle  std_msgs/Float32           0.0–0.85
  /starship/main_gimbal    geometry_msgs/Vector3      pitch/yaw rad
  /starship/rcs/top        geometry_msgs/Vector3      impulse x/y/z
  /starship/rcs/mid_fwd    geometry_msgs/Vector3      impulse x/y/z
  /starship/rcs/mid_aft    geometry_msgs/Vector3      impulse x/y/z
  /starship/safe_mode      std_msgs/Bool              engage/disengage

Usage: called from enable_ros2_bridge.py once the Starship USD stage is loaded.

  from starship.starship_controller import StarshipController
  ctrl = StarshipController(app, publisher)   # publisher = StarshipPublisher instance
  ctrl.start()
  # … in the main app.update() loop:
  ctrl.apply_forces(sim_dt)
  # …
  ctrl.stop()

Force model (Y-up, Isaac Sim units = metres/kg):
  - Main engine thrust: F_y = throttle × MAX_THRUST_N  (vertical, world-Y)
  - Gimbal torque: T = gimbal_angle × I_moment  (approx.)
  - RCS impulse: per-step delta-v = impulse × RCS_FORCE_N × dt / mass
"""

import math
import threading
import time

# ── Isaac Sim imports ─────────────────────────────────────────────────────
try:
    import carb
    import omni.usd
    from pxr import Gf, UsdPhysics, PhysxSchema
    from omni.isaac.core.utils.stage import get_current_stage
except ImportError:
    raise ImportError(
        "[starship_ctrl] Must run inside Isaac Sim Python — "
        "see enable_ros2_bridge.py for the entry point."
    )

# ── ROS 2 imports ─────────────────────────────────────────────────────────
import sys
sys.path.insert(0, "/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Bool
from geometry_msgs.msg import Vector3


# ── Constants ─────────────────────────────────────────────────────────────
STARSHIP_PRIM   = "/World/Starship"
MAX_THRUST_N    = 14_700_000.0   # 14.7 MN peak thrust
DRY_MASS_KG     = 130_000.0
MOMENT_OF_INERTIA = 5e9          # kg·m² (rough for 50m × 9m capsule)
RCS_FORCE_N     = 50_000.0       # 50 kN per RCS thruster group
MAX_THROTTLE    = 0.85           # FSW hard limit (mirrored in Rust)
FUEL_BURN_RATE_KG_S = 2_000.0    # kg/s at 100% throttle (simplified)


class StarshipController:
    """
    Receives ROS 2 commands and applies physics forces to the Starship body.

    Thread model:
      - `start()` launches a subscriber thread that spins rclpy.
      - `apply_forces(dt)` must be called from the Isaac Sim main thread each frame.
        It reads the latest commands (thread-safe via locks) and calls the
        PhysX force-application APIs.
    """

    def __init__(self, app, publisher=None) -> None:
        self._app        = app
        self._publisher  = publisher   # optional StarshipPublisher for state sync
        self._running    = False
        self._thread     = None
        self._lock       = threading.Lock()

        # Latest command state (written by subscriber thread, read by main thread)
        self._throttle   = 0.0
        self._gimbal     = Gf.Vec3f(0.0, 0.0, 0.0)   # (pitch, yaw, unused) rad
        self._rcs_top     = Gf.Vec3f(0.0, 0.0, 0.0)
        self._rcs_mid_fwd = Gf.Vec3f(0.0, 0.0, 0.0)
        self._rcs_mid_aft = Gf.Vec3f(0.0, 0.0, 0.0)
        self._safe_mode  = False

        # ── rclpy node ────────────────────────────────────────────────────
        if not rclpy.ok():
            rclpy.init()

        self._node = rclpy.create_node("starship_controller")

        self._sub_throttle = self._node.create_subscription(
            Float32, "/starship/main_throttle", self._cb_throttle, 10
        )
        self._sub_gimbal = self._node.create_subscription(
            Vector3, "/starship/main_gimbal", self._cb_gimbal, 10
        )
        self._sub_rcs_top = self._node.create_subscription(
            Vector3, "/starship/rcs/top", self._cb_rcs_top, 10
        )
        self._sub_rcs_mid_fwd = self._node.create_subscription(
            Vector3, "/starship/rcs/mid_fwd", self._cb_rcs_mid_fwd, 10
        )
        self._sub_rcs_mid_aft = self._node.create_subscription(
            Vector3, "/starship/rcs/mid_aft", self._cb_rcs_mid_aft, 10
        )
        self._sub_safe = self._node.create_subscription(
            Bool, "/starship/safe_mode", self._cb_safe_mode, 10
        )
        self._sub_refuel = self._node.create_subscription(
            Float32, "/starship/refuel", self._cb_refuel, 10
        )
        print("[starship_ctrl] rclpy node 'starship_controller' ready")

    # ── Public API ────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._spin, daemon=True, name="starship_ctrl"
        )
        self._thread.start()
        print("[starship_ctrl] subscriber thread started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        self._node.destroy_node()
        print("[starship_ctrl] stopped")

    def apply_forces(self, sim_dt: float) -> None:
        """
        Apply accumulated ROS commands as PhysX forces/torques.
        Must be called from the Isaac Sim MAIN THREAD each simulation step.
        `sim_dt` is the physics step size in seconds.
        """
        stage = get_current_stage()
        if stage is None:
            return

        prim = stage.GetPrimAtPath(STARSHIP_PRIM)
        if not prim.IsValid():
            return

        with self._lock:
            throttle   = self._throttle
            gimbal     = Gf.Vec3f(self._gimbal)
            rcs_top    = Gf.Vec3f(self._rcs_top)
            rcs_mf     = Gf.Vec3f(self._rcs_mid_fwd)
            rcs_ma     = Gf.Vec3f(self._rcs_mid_aft)
            safe_mode  = self._safe_mode

        if safe_mode:
            # Zero out all commands in safe mode
            throttle = 0.0
            gimbal   = Gf.Vec3f(0.0, 0.0, 0.0)
            rcs_top  = Gf.Vec3f(0.0, 0.0, 0.0)
            rcs_mf   = Gf.Vec3f(0.0, 0.0, 0.0)
            rcs_ma   = Gf.Vec3f(0.0, 0.0, 0.0)

        # ── Main engine thrust (world-Y axis) ─────────────────────────────
        thrust_n   = throttle * MAX_THRUST_N
        # Gimbal deflects thrust into X/Z:  pitch → X tilt, yaw → Z tilt
        # Small-angle approx: sin(θ) ≈ θ
        pitch_rad = gimbal[0]
        yaw_rad   = gimbal[1]
        force_world = Gf.Vec3f(
            thrust_n * math.sin(pitch_rad),
            thrust_n * math.cos(pitch_rad) * math.cos(yaw_rad),
            thrust_n * math.sin(yaw_rad),
        )

        # ── Gimbal torque (differential vector) ──────────────────────────
        # Simple model: torque = gimbal_angle × thrust × moment_arm (5 m to CoM)
        moment_arm = 5.0   # metres (engine plane to CoM)
        torque = Gf.Vec3f(
            -thrust_n * moment_arm * math.sin(yaw_rad),   # roll-axis torque
             0.0,                                          # yaw (handled by force offset)
             thrust_n * moment_arm * math.sin(pitch_rad), # pitch-axis torque
        )

        # ── RCS forces (applied in vehicle body frame) ────────────────────
        # Each group applies a fixed force, scaled by unit impulse vector
        rcs_force_world = (
            _scale_vec(rcs_top,  RCS_FORCE_N) +
            _scale_vec(rcs_mf,   RCS_FORCE_N) +
            _scale_vec(rcs_ma,   RCS_FORCE_N)
        )

        total_force  = force_world  + rcs_force_world
        total_torque = torque

        # ── Apply via PhysX ───────────────────────────────────────────────
        try:
            _apply_force_torque(prim, total_force, total_torque)
        except Exception as exc:
            print(f"[starship_ctrl] PhysX force apply error: {exc}")

        # ── Notify publisher of current state ────────────────────────────
        if self._publisher is not None:
            fuel_burn = throttle * FUEL_BURN_RATE_KG_S
            self._publisher.update_from_controller(
                throttle=throttle,
                gimbal=(float(gimbal[0]), float(gimbal[1])),
                safe_mode=safe_mode,
                fuel_burn_rate_kg_s=fuel_burn,
            )

        # ── One-shot RCS decay (don't accumulate impulse) ─────────────────
        with self._lock:
            self._rcs_top     = Gf.Vec3f(0.0, 0.0, 0.0)
            self._rcs_mid_fwd = Gf.Vec3f(0.0, 0.0, 0.0)
            self._rcs_mid_aft = Gf.Vec3f(0.0, 0.0, 0.0)

    # ── Subscriber callbacks (run in subscriber thread) ───────────────────

    def _cb_throttle(self, msg: Float32) -> None:
        val = max(0.0, min(MAX_THROTTLE, float(msg.data)))
        with self._lock:
            self._throttle = val

    def _cb_gimbal(self, msg: Vector3) -> None:
        pitch = max(-0.26, min(0.26, float(msg.x)))
        yaw   = max(-0.26, min(0.26, float(msg.y)))
        with self._lock:
            self._gimbal = Gf.Vec3f(pitch, yaw, 0.0)

    def _cb_rcs_top(self, msg: Vector3) -> None:
        with self._lock:
            self._rcs_top = Gf.Vec3f(
                max(-1.0, min(1.0, float(msg.x))),
                max(-1.0, min(1.0, float(msg.y))),
                max(-1.0, min(1.0, float(msg.z))),
            )

    def _cb_rcs_mid_fwd(self, msg: Vector3) -> None:
        with self._lock:
            self._rcs_mid_fwd = Gf.Vec3f(
                max(-1.0, min(1.0, float(msg.x))),
                max(-1.0, min(1.0, float(msg.y))),
                max(-1.0, min(1.0, float(msg.z))),
            )

    def _cb_rcs_mid_aft(self, msg: Vector3) -> None:
        with self._lock:
            self._rcs_mid_aft = Gf.Vec3f(
                max(-1.0, min(1.0, float(msg.x))),
                max(-1.0, min(1.0, float(msg.y))),
                max(-1.0, min(1.0, float(msg.z))),
            )

    def _cb_safe_mode(self, msg: Bool) -> None:
        with self._lock:
            self._safe_mode = bool(msg.data)
        mode_str = "ENGAGED" if msg.data else "disengaged"
        print(f"[starship_ctrl] safe_mode {mode_str}")

    def _cb_refuel(self, msg: Float32) -> None:
        from pxr import UsdGeom, Usd
        stage = get_current_stage()
        if stage is None:
            print("[starship_ctrl] refuel rejected: no stage")
            return
        prim = stage.GetPrimAtPath(STARSHIP_PRIM)
        if not prim.IsValid():
            print("[starship_ctrl] refuel rejected: Starship prim not found")
            return
        altitude_m = UsdGeom.Xformable(prim) \
            .ComputeLocalToWorldTransform(Usd.TimeCode.Default()) \
            .ExtractTranslation()[1]
        if altitude_m > 5.0:
            print(f"[starship_ctrl] refuel rejected: airborne at {altitude_m:.1f} m")
            return
        fraction = max(0.0, min(1.0, float(msg.data)))
        fuel_kg = fraction * 700_000.0
        if self._publisher is not None:
            self._publisher._fuel_kg = fuel_kg
            print(f"[starship_ctrl] refueled → {fraction:.1%} ({fuel_kg:.0f} kg)")

    # ── Spin thread ───────────────────────────────────────────────────────

    def _spin(self) -> None:
        while self._running and rclpy.ok():
            rclpy.spin_once(self._node, timeout_sec=0.01)


# ── Helpers ───────────────────────────────────────────────────────────────


def _scale_vec(v: Gf.Vec3f, scale: float) -> Gf.Vec3f:
    return Gf.Vec3f(v[0] * scale, v[1] * scale, v[2] * scale)


def _apply_force_torque(prim, force: Gf.Vec3f, torque: Gf.Vec3f) -> None:
    """
    Apply a world-space force and torque to a PhysX rigid body prim.

    Isaac Sim 4.x apply_force_at_pos signature:
      (body_path: str, force: carb.Float3, pos: carb.Float3, mode: str='Force') -> None
    mode='Force' applies a continuous world-space force; 'Impulse' for one-shot.
    """
    try:
        import omni.physx
        import carb
        physx = omni.physx.get_physx_simulation_interface()
        prim_path_str = str(prim.GetPath())
        physx.apply_force_at_pos(
            prim_path_str,
            carb.Float3(float(force[0]), float(force[1]), float(force[2])),
            carb.Float3(0.0, 0.0, 0.0),  # at CoM
            "Force",                      # world-space continuous force
        )
        if torque.GetLength() > 0.01:
            physx.apply_torque(
                prim_path_str,
                carb.Float3(float(torque[0]), float(torque[1]), float(torque[2])),
                "Force",
            )
    except Exception as exc:
        # Only print the first few occurrences to avoid log spam
        if not hasattr(_apply_force_torque, "_err_count"):
            _apply_force_torque._err_count = 0
        _apply_force_torque._err_count += 1
        if _apply_force_torque._err_count <= 3:
            print(f"[starship_ctrl] force apply error #{_apply_force_torque._err_count}: {exc}", flush=True)
