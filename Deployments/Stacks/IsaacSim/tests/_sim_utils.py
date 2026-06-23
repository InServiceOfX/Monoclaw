"""
Shared helpers for PhysX rigid-body validation tests.

Run inside Isaac Sim's Python only:
    /isaac-sim/python.sh /isaac-sim/tests/test_tN_xxx.py

All coordinate systems are Z-up (same as the Starship stage).

Angular velocity unit note (Isaac Sim 4.5 / USD Physics):
  physics:angularVelocity is stored and read back in DEGREES/SECOND by PhysX,
  even though all other quantities use SI units.  spawn_rigid_box() and
  spawn_rigid_sphere() accept init_ang_vel in rad/s and convert to deg/s
  before writing the attribute.  get_state() converts the read-back deg/s
  back to rad/s so callers see consistent SI units throughout.
"""
import math
import sys

from pxr import Gf, Usd, UsdGeom, UsdPhysics

try:
    from pxr import PhysxSchema
    _HAS_PHYSX = True
except ImportError:
    PhysxSchema = None
    _HAS_PHYSX = False

_RAD2DEG = 180.0 / math.pi
_DEG2RAD = math.pi / 180.0

# SimulationApp config: physics-only kit avoids MDL warmup hang on GeForce headless.
APP_CONFIG = {
    "headless": True,
    "anti_aliasing": 0,
    "experience": "/isaac-sim/apps/isaacsim.exp.physics.kit",
}

# Extra CLI args appended AFTER SimulationApp's built-in args so they override.
# SimulationApp hardcodes --/rtx/materialDb/syncLoads=True and
# --/rtx/hydra/materialSyncLoads=True; without an Omniverse nucleus server
# these cause a ~30-minute connection-timeout stall during SimulationApp init.
# Passing False again at the end of the arg list overrides them.
EXTRA_ARGS = [
    "--/rtx/materialDb/syncLoads=False",
    "--/rtx/hydra/materialSyncLoads=False",
]


def get_simulation_context(physics_dt: float = 1 / 240.0):
    """Return a SimulationContext that respects the USD scene's gravity.

    SimulationContext's default (set_defaults=True) overrides any gravity set
    by setup_physics_scene() with 9.81 m/s².  set_defaults=False makes it
    honour the UsdPhysics.Scene gravity set before this call.
    """
    try:
        from isaacsim.core.api import SimulationContext
    except ImportError:
        from omni.isaac.core import SimulationContext
    return SimulationContext(
        physics_dt=physics_dt,
        stage_units_in_meters=1.0,
        set_defaults=False,
    )


def start_sim(sim) -> None:
    """
    Start the physics simulation without calling reset().

    reset() internally calls step(render=True) to flush the USD stage.
    In headless physics-only mode (asyncInit=true, present.enabled=false),
    the RTX renderer never produces that frame and the call deadlocks.

    stop() + play() is sufficient for fresh stages created in the same script:
    physics initializes lazily on the first step() call, no render required.
    """
    import omni.kit.app
    _app_iface = omni.kit.app.get_app()
    sim.stop()
    for _ in range(50):   # drain any pending Kit events
        _app_iface.update()
    sim.play()


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------

def setup_physics_scene(stage, gravity: float = 9.81,
                         gravity_dir: tuple = (0.0, 0.0, -1.0),
                         gpu_dynamics: bool = False) -> "Usd.Prim":
    """Define /World/PhysicsScene with given gravity. Returns the scene prim.

    gpu_dynamics=False (default) uses CPU PhysX — identical accuracy for small
    scenes and avoids the 29-minute CUDA/RTX context initialization that blocks
    sim.play() when GPU dynamics is enabled headlessly on GeForce.
    Pass gpu_dynamics=True only when benchmarking large multi-body scenes.
    """
    scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    scene.CreateGravityMagnitudeAttr(gravity)
    scene.CreateGravityDirectionAttr(Gf.Vec3f(*gravity_dir))
    if _HAS_PHYSX:
        ps = PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim())
        for fn_name in ("CreateGpuDynamicsEnabledAttr", "CreateEnableGPUDynamicsAttr"):
            fn = getattr(ps, fn_name, None)
            if fn:
                fn(gpu_dynamics)
                break
    return scene.GetPrim()


def spawn_rigid_sphere(stage, path: str,
                        pos: tuple = (0.0, 0.0, 0.0),
                        radius: float = 0.5,
                        mass: float = 1.0,
                        init_lin_vel: tuple = (0.0, 0.0, 0.0)) -> "Usd.Prim":
    """Spawn a sphere rigid body. Inertia auto-computed from geometry + mass."""
    xform = UsdGeom.Xform.Define(stage, path)
    xform.AddTranslateOp().Set(Gf.Vec3d(*pos))
    # xformOp:orient lets PhysX write the body's quaternion back to USD each step,
    # so get_state() can read the correct rotation for body-frame transforms.
    xform.AddOrientOp().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))

    sphere = UsdGeom.Sphere.Define(stage, path + "/Shape")
    sphere.CreateRadiusAttr(radius)

    rb = UsdPhysics.RigidBodyAPI.Apply(xform.GetPrim())
    rb.CreateVelocityAttr(Gf.Vec3f(*init_lin_vel))
    # physics:angularVelocity is in deg/s in Isaac Sim 4.5
    rb.CreateAngularVelocityAttr(Gf.Vec3f(0, 0, 0))

    mass_api = UsdPhysics.MassAPI.Apply(xform.GetPrim())
    mass_api.CreateMassAttr(mass)

    UsdPhysics.CollisionAPI.Apply(sphere.GetPrim())

    # Do NOT apply PhysxRigidBodyAPI here: its presence changes default damping
    # behaviour in ways that affect conservation tests.  PhysX defaults for
    # UsdPhysics.RigidBodyAPI bodies are linearDamping=0, angularDamping=0.05.
    # Sphere tests only check linear quantities so angular damping is irrelevant.

    return xform.GetPrim()


def spawn_rigid_box(stage, path: str,
                     pos: tuple = (0.0, 0.0, 0.0),
                     half_extents: tuple = (0.5, 0.5, 0.5),
                     mass: float = 1.0,
                     inertia: tuple | None = None,
                     init_lin_vel: tuple = (0.0, 0.0, 0.0),
                     init_ang_vel: tuple = (0.0, 0.0, 0.0),
                     gyroscopic: bool = True) -> "Usd.Prim":
    """
    Spawn a box rigid body with optional explicit principal inertia.
    inertia = (I_x, I_y, I_z) kg·m² in principal body axes (body-frame diagonal).
    If None, PhysX auto-computes from box geometry + density.
    """
    xform = UsdGeom.Xform.Define(stage, path)
    xform.AddTranslateOp().Set(Gf.Vec3d(*pos))
    # xformOp:orient lets PhysX write the body's quaternion back to USD each step.
    xform.AddOrientOp().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))

    box = UsdGeom.Cube.Define(stage, path + "/Shape")
    box.CreateSizeAttr(1.0)  # unit cube; scale via half_extents
    box.AddScaleOp().Set(Gf.Vec3f(half_extents[0] * 2,
                                   half_extents[1] * 2,
                                   half_extents[2] * 2))

    rb = UsdPhysics.RigidBodyAPI.Apply(xform.GetPrim())
    rb.CreateVelocityAttr(Gf.Vec3f(*init_lin_vel))
    # physics:angularVelocity is in deg/s in Isaac Sim 4.5; convert from rad/s
    rb.CreateAngularVelocityAttr(Gf.Vec3f(
        init_ang_vel[0] * _RAD2DEG,
        init_ang_vel[1] * _RAD2DEG,
        init_ang_vel[2] * _RAD2DEG,
    ))

    mass_api = UsdPhysics.MassAPI.Apply(xform.GetPrim())
    mass_api.CreateMassAttr(mass)
    if inertia is not None:
        mass_api.CreateDiagonalInertiaAttr(Gf.Vec3f(*inertia))

    UsdPhysics.CollisionAPI.Apply(box.GetPrim())

    if _HAS_PHYSX:
        physx_rb = PhysxSchema.PhysxRigidBodyAPI.Apply(xform.GetPrim())
        physx_rb.CreateEnableGyroscopicForcesAttr(gyroscopic)
        physx_rb.CreateLinearDampingAttr(0.0)
        physx_rb.CreateAngularDampingAttr(0.0)
        # SimulationContext overrides physics:scene gravity=0 with 9.81 m/s².
        # Disable gravity per-body so boxes don't fall into the default ground plane
        # and receive contact torques that corrupt angular dynamics tests.
        physx_rb.CreateDisableGravityAttr(True)

    return xform.GetPrim()


# ---------------------------------------------------------------------------
# State readback
# ---------------------------------------------------------------------------

def get_state(prim: "Usd.Prim") -> dict:
    """
    Read physics state of a rigid body prim.

    Returns dict with:
      pos     Gf.Vec3d  world-space position (m)
      quat    Gf.Quatd  body→world rotation quaternion (w,x,y,z)
      lin_vel Gf.Vec3f  world-space linear velocity (m/s)
      ang_vel Gf.Vec3f  world-space angular velocity (rad/s)
    """
    xform = UsdGeom.Xformable(prim)
    mat = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    pos = mat.ExtractTranslation()

    try:
        quat = mat.ExtractRotationQuat()  # GfQuatd
    except Exception:
        quat = Gf.Quatd(1, 0, 0, 0)

    def _read_vec(names):
        for name in names:
            attr = prim.GetAttribute(name)
            if attr.IsValid():
                v = attr.Get()
                if v is not None:
                    return Gf.Vec3f(v[0], v[1], v[2])
        return Gf.Vec3f(0, 0, 0)

    lin_vel = _read_vec(("physxRigidBody:velocity", "physics:velocity"))
    # physics:angularVelocity is in deg/s in Isaac Sim 4.5; convert to rad/s
    ang_vel_deg = _read_vec(("physxRigidBody:angularVelocity", "physics:angularVelocity"))
    ang_vel = Gf.Vec3f(
        ang_vel_deg[0] * _DEG2RAD,
        ang_vel_deg[1] * _DEG2RAD,
        ang_vel_deg[2] * _DEG2RAD,
    )

    return {"pos": pos, "quat": quat, "lin_vel": lin_vel, "ang_vel": ang_vel}


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def rotate_vec_by_quat(v: Gf.Vec3f, q: Gf.Quatd) -> Gf.Vec3d:
    """Rotate world-frame vector v by quaternion q (body→world). Returns Vec3d."""
    rot = Gf.Rotation(q)
    return rot.TransformDir(Gf.Vec3d(v[0], v[1], v[2]))


def to_body_frame(v_world: Gf.Vec3f, q_body_to_world: Gf.Quatd) -> Gf.Vec3d:
    """
    Rotate world-frame vector into body frame (inverse of q).
    q_body_to_world: quaternion that maps body→world (from getGlobalPose).
    """
    q_inv = Gf.Quatd(q_body_to_world.GetReal(),
                     -q_body_to_world.GetImaginary())
    rot = Gf.Rotation(q_inv)
    return rot.TransformDir(Gf.Vec3d(v_world[0], v_world[1], v_world[2]))


def inertial_h(ang_vel_world: Gf.Vec3f,
               q_body_to_world: Gf.Quatd,
               I_diag: tuple) -> Gf.Vec3d:
    """
    Compute angular momentum in inertial frame.

    h_inertial = R * diag(I) * R^T * omega_world
               = R * (diag(I) * omega_body)

    where omega_body = R^T * omega_world.

    I_diag = (I_x, I_y, I_z) principal moments in body frame.
    """
    omega_body = to_body_frame(ang_vel_world, q_body_to_world)
    h_body = Gf.Vec3f(I_diag[0] * omega_body[0],
                       I_diag[1] * omega_body[1],
                       I_diag[2] * omega_body[2])
    return rotate_vec_by_quat(h_body, q_body_to_world)


def body_frame_kinetic_energy(ang_vel_world: Gf.Vec3f,
                               q: Gf.Quatd,
                               I_diag: tuple,
                               mass: float,
                               lin_vel: Gf.Vec3f) -> float:
    """Total KE = 0.5*m*v^2 + 0.5*omega_body^T * I * omega_body."""
    omega_body = to_body_frame(ang_vel_world, q)
    T_rot = 0.5 * (I_diag[0] * omega_body[0] ** 2 +
                   I_diag[1] * omega_body[1] ** 2 +
                   I_diag[2] * omega_body[2] ** 2)
    v2 = lin_vel[0] ** 2 + lin_vel[1] ** 2 + lin_vel[2] ** 2
    T_lin = 0.5 * mass * v2
    return T_lin + T_rot


# ---------------------------------------------------------------------------
# Force / torque application
# ---------------------------------------------------------------------------

def apply_wrench(prim_path: str,
                  force: tuple = (0, 0, 0),
                  torque: tuple = (0, 0, 0),
                  mode: str = "Force") -> None:
    """
    Apply world-space force + torque to a rigid body.
    Must be called from the Isaac Sim main thread.
    mode: "Force" (N, continuous) | "Impulse" (N·s) | "Acceleration" | "VelocityChange"
    """
    import omni.physx
    import omni.usd
    import carb
    from pxr import PhysicsSchemaTools

    physx = omni.physx.get_physx_simulation_interface()
    stage_id = omni.usd.get_context().get_stage_id()
    body_int = PhysicsSchemaTools.sdfPathToInt(prim_path)

    if any(abs(f) > 0 for f in force):
        physx.apply_force_at_pos(
            stage_id, body_int,
            carb.Float3(float(force[0]), float(force[1]), float(force[2])),
            carb.Float3(0.0, 0.0, 0.0),
            mode,
        )
    if any(abs(t) > 0 for t in torque):
        physx.apply_torque(
            stage_id, body_int,
            carb.Float3(float(torque[0]), float(torque[1]), float(torque[2])),
            mode,
        )


# ---------------------------------------------------------------------------
# Assertion helper
# ---------------------------------------------------------------------------

def assert_rel(actual: float, expected: float, tol: float, label: str) -> None:
    """Assert |actual - expected| / |expected| < tol."""
    if abs(expected) < 1e-12:
        err = abs(actual - expected)
    else:
        err = abs(actual - expected) / abs(expected)
    if err > tol:
        raise AssertionError(
            f"{label}: relative error {err:.4e} > tol {tol:.4e} "
            f"(got {actual:.6g}, expected {expected:.6g})"
        )


def assert_abs(actual: float, expected: float, tol: float, label: str) -> None:
    err = abs(actual - expected)
    if err > tol:
        raise AssertionError(
            f"{label}: absolute error {err:.4e} > tol {tol:.4e} "
            f"(got {actual:.6g}, expected {expected:.6g})"
        )
