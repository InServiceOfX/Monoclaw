#!/usr/bin/env python3
"""
T8 — Quaternion normalization drift (numerical hygiene, 6DOF)

Spin a rigid body at high angular rate for many steps. The orientation
quaternion returned by PhysX must remain unit-norm throughout:
  |q|² - 1 < epsilon

Also verify that the recovered rotation matrix R = R(q) satisfies:
  |R^T R - I|_F < epsilon  (orthogonality)

If PhysX renormalizes per step (it should) this test is a no-op — which is the
desired result. If it does NOT renormalize, long runs produce nonsensical
orientations and tests T5–T7 become meaningless.

Reference: Sidi §7.2–7.3 (quaternion kinematic equation and normalization)

Run:
    docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/tests/test_t8_quat_drift.py
"""
import sys
import math
sys.path.insert(0, "/isaac-sim/tests")
from isaacsim import SimulationApp
app = SimulationApp({
    "headless": True,
    "anti_aliasing": 0,
    "width": 640,
    "height": 360,
    "renderer": "RayTracedLighting",
    "headless_egl": True,
    "sync_loads": False,
    # Skip _wait_for_viewport() — blocks until RTX PSO compilation (~26 min).
    "create_new_stage": False,
    "experience": "/isaac-sim/apps/isaacsim.exp.physics.kit",
})

import omni.usd
from pxr import Gf
from _sim_utils import (
    setup_physics_scene, spawn_rigid_box, get_state,
    get_simulation_context, start_sim,
)

# High spin rate to stress the quaternion integrator
MASS        = 10.0
I_DIAG      = (100.0, 150.0, 200.0)   # kg·m²
OMEGA_SPIN  = (5.0, 8.0, 12.0)        # rad/s — fast, multi-axis spin
DT          = 1 / 240.0
N_STEPS     = 12000    # 50 seconds

NORM_TOL    = 1e-4     # |q|² - 1 must stay < 1e-4
ORTH_TOL    = 1e-3     # |R^T*R - I|_F must stay < 1e-3


def _quat_norm_sq(q: Gf.Quatd) -> float:
    """Return |q|² = w² + x² + y² + z²."""
    w = float(q.GetReal())
    img = q.GetImaginary()
    x, y, z = float(img[0]), float(img[1]), float(img[2])
    return w*w + x*x + y*y + z*z


def _rotation_matrix(q: Gf.Quatd) -> Gf.Matrix3d:
    """Convert unit quaternion to 3×3 rotation matrix."""
    return Gf.Matrix3d(Gf.Rotation(q))


def _frobenius_orth_error(R: Gf.Matrix3d) -> float:
    """||R^T * R - I||_F — should be zero for a rotation matrix."""
    # R^T * R
    Rt_R = R.GetTranspose() * R
    # Subtract identity
    err = 0.0
    for i in range(3):
        for j in range(3):
            ref = 1.0 if i == j else 0.0
            d = Rt_R[i][j] - ref
            err += d * d
    return math.sqrt(err)


def run_test():
    omni.usd.get_context().new_stage()   # create_new_stage=False skips this in SimulationApp
    stage = omni.usd.get_context().get_stage()
    setup_physics_scene(stage, gravity=0.0)

    body = spawn_rigid_box(
        stage, "/World/Body",
        pos=(0, 0, 0),
        half_extents=(0.5, 0.7, 1.0),
        mass=MASS,
        inertia=I_DIAG,
        init_ang_vel=OMEGA_SPIN,
        gyroscopic=True,
    )

    sim = get_simulation_context(DT)
    start_sim(sim)

    max_norm_err = 0.0
    max_orth_err = 0.0
    max_norm_step = 0
    max_orth_step = 0

    # Check at start, midpoint, end, and every 500 steps in between
    check_interval = 100

    for step in range(N_STEPS):
        sim.step(render=False)

        if step % check_interval != 0 and step != N_STEPS - 1:
            continue

        state = get_state(body)
        q = state["quat"]

        norm_sq = _quat_norm_sq(q)
        norm_err = abs(norm_sq - 1.0)
        if norm_err > max_norm_err:
            max_norm_err = norm_err
            max_norm_step = step

        R = _rotation_matrix(q)
        orth_err = _frobenius_orth_error(R)
        if orth_err > max_orth_err:
            max_orth_err = orth_err
            max_orth_step = step

        if norm_err > NORM_TOL:
            raise AssertionError(
                f"step {step} (t={step*DT:.2f}s): |q|²-1 = {norm_err:.4e} > {NORM_TOL} "
                f"(|q|²={norm_sq:.8f})"
            )
        if orth_err > ORTH_TOL:
            raise AssertionError(
                f"step {step} (t={step*DT:.2f}s): |R^T R - I|_F = {orth_err:.4e} > {ORTH_TOL}"
            )

    print(f"  omega_spin={OMEGA_SPIN} rad/s over {N_STEPS} steps ({N_STEPS*DT:.0f}s)")
    print(f"  max |q|²-1:       {max_norm_err:.2e} at step {max_norm_step}")
    print(f"  max |R^T R - I|_F: {max_orth_err:.2e} at step {max_orth_step}")


try:
    run_test()
    print(f"T8 PASS — quaternion norm and rotation matrix orthogonality maintained", flush=True)
    _exit_code = 0
except AssertionError as e:
    print(f"T8 FAIL: {e}", flush=True)
    _exit_code = 1
except Exception as e:
    import traceback
    print(f"T8 ERROR: {e}", flush=True)
    traceback.print_exc()
    _exit_code = 2
# Skip app.close() — it blocks 26+ min on GeForce (RTX MDL shader compilation
# in a background thread). The --rm container releases GPU resources via cgroup.
import os; os._exit(_exit_code)
