#!/usr/bin/env python3
"""
T6 — Intermediate-axis instability / tennis-racket theorem (6DOF)

An asymmetric rigid body (I_x < I_y < I_z) spun about each principal axis:
  - Near I_x (min) and I_z (max): rotation is stable — angle between omega
    and the initial spin axis stays small.
  - Near I_y (intermediate): rotation is UNSTABLE — the body tumbles, angle
    grows large.

This is the hardest test for the Euler-equation coupling terms (I_j - I_k)*w_j*w_k.
A solver that gets energy and momentum right can still get the cross-coupling sign
wrong and produce incorrect stability behavior.

Reference: Sidi §4.4 (stability conditions 4.4.10-4.4.12), Goldstein §5.5
           (Dzhanibekov / tennis-racket theorem)

Run:
    docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/tests/test_t6_instability.py
"""
import sys
import math
sys.path.insert(0, "/isaac-sim/tests")

from isaacsim import SimulationApp
app = SimulationApp({"headless": True, "anti_aliasing": 0,
                     "experience": "/isaac-sim/apps/isaacsim.exp.physics.kit"})

import omni.usd
from pxr import Gf
from _sim_utils import (
    setup_physics_scene, spawn_rigid_box, get_state,
    get_simulation_context, start_sim, to_body_frame,
)

# Asymmetric: I_x < I_y < I_z  (well-separated to make instability clear)
MASS    = 50.0
I_X     = 500.0     # kg·m²  min
I_Y     = 1500.0    # kg·m²  intermediate
I_Z     = 4000.0    # kg·m²  max

OMEGA_SPIN = 8.0    # rad/s spin rate
EPS        = 0.05   # rad/s small perturbation off principal axis

DT      = 1 / 240.0
N_STEPS = 4800      # 20 seconds — enough to see instability develop

STABLE_MAX_ANGLE_DEG   = 20.0   # stable runs: angle from initial axis stays < 20°
UNSTABLE_MIN_ANGLE_DEG = 60.0   # unstable run: angle must exceed 60° at some point


def _angle_deg(v1, v2):
    """Angle in degrees between two 3-vectors (Gf.Vec3d)."""
    n1 = Gf.Vec3d(v1).GetNormalized()
    n2 = Gf.Vec3d(v2).GetNormalized()
    dot = max(-1.0, min(1.0, float(n1.GetDot(n2))))
    return math.degrees(math.acos(dot))


def run_case(stage, sim, body, prim_path, init_omega, label):
    """
    Run one stability test case.
    Returns (max_angle_deg, final_angle_deg).
    """
    # Initial body-frame omega at t=0 IS the world-frame omega (identity orientation).
    init_vec = Gf.Vec3d(*init_omega)

    state0 = get_state(body)
    omega_world0 = state0["ang_vel"]
    q0 = state0["quat"]
    omega_body0 = to_body_frame(omega_world0, q0)
    initial_dir = Gf.Vec3d(omega_body0).GetNormalized()

    max_angle = 0.0

    for step in range(N_STEPS):
        sim.step(render=False)
        state = get_state(body)
        omega_world = state["ang_vel"]
        q = state["quat"]
        omega_body = to_body_frame(omega_world, q)
        angle = _angle_deg(omega_body, initial_dir)
        if angle > max_angle:
            max_angle = angle

    return max_angle


def run_test():
    stage = omni.usd.get_context().get_stage()
    setup_physics_scene(stage, gravity=0.0)

    results = {}

    for axis_label, init_omega in [
        ("min-axis (I_x, STABLE)",  (OMEGA_SPIN, EPS, EPS)),
        ("mid-axis (I_y, UNSTABLE)", (EPS, OMEGA_SPIN, EPS)),
        ("max-axis (I_z, STABLE)",  (EPS, EPS, OMEGA_SPIN)),
    ]:
        # Recreate body each run with fresh orientation and angular velocity
        import omni.usd as _ousd
        _stage = _ousd.get_context().get_stage()
        prim_path = "/World/Body"

        # Remove previous body if it exists
        existing = _stage.GetPrimAtPath(prim_path)
        if existing.IsValid():
            _stage.RemovePrim(prim_path)

        body = spawn_rigid_box(
            _stage, prim_path,
            pos=(0, 0, 0),
            half_extents=(1.0, 1.5, 2.5),
            mass=MASS,
            inertia=(I_X, I_Y, I_Z),
            init_ang_vel=init_omega,
            gyroscopic=True,
        )

        sim = get_simulation_context(DT)
        start_sim(sim)

        max_angle = run_case(_stage, sim, body, prim_path, init_omega, axis_label)
        results[axis_label] = max_angle
        print(f"  {axis_label}: max angle from initial axis = {max_angle:.1f}°")

    # Stability assertions
    min_stable = results["min-axis (I_x, STABLE)"]
    mid_unstable = results["mid-axis (I_y, UNSTABLE)"]
    max_stable = results["max-axis (I_z, STABLE)"]

    if min_stable > STABLE_MAX_ANGLE_DEG:
        raise AssertionError(
            f"min-axis (STABLE) should stay < {STABLE_MAX_ANGLE_DEG}° "
            f"but reached {min_stable:.1f}°"
        )
    if max_stable > STABLE_MAX_ANGLE_DEG:
        raise AssertionError(
            f"max-axis (STABLE) should stay < {STABLE_MAX_ANGLE_DEG}° "
            f"but reached {max_stable:.1f}°"
        )
    if mid_unstable < UNSTABLE_MIN_ANGLE_DEG:
        raise AssertionError(
            f"mid-axis (UNSTABLE) should tumble past {UNSTABLE_MIN_ANGLE_DEG}° "
            f"but only reached {mid_unstable:.1f}° after {N_STEPS} steps — "
            f"gyroscopic cross-coupling may be missing or too weak"
        )

    print(f"  I_diag = ({I_X}, {I_Y}, {I_Z}) kg·m²  omega_spin={OMEGA_SPIN} rad/s")


try:
    run_test()
    print("T6 PASS — intermediate-axis instability confirmed (tennis-racket theorem)")
    _exit_code = 0
except AssertionError as e:
    print(f"T6 FAIL: {e}")
    _exit_code = 1
except Exception as e:
    import traceback
    print(f"T6 ERROR: {e}")
    traceback.print_exc()
    _exit_code = 2
finally:
    app.close()

sys.exit(_exit_code)
