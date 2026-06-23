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

All three bodies run SIMULTANEOUSLY on the same stage and SimulationContext to
avoid deadlocks from multiple SimulationContext instantiations.

Reference: Sidi §4.4 (stability conditions 4.4.10-4.4.12), Goldstein §5.5
           (Dzhanibekov / tennis-racket theorem)

Run:
    docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/tests/test_t6_instability.py
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
# N_STEPS must be short: symplectic Euler amplifies stable-axis oscillations at
# rate sqrt(1+(λDT)²) per step, where λ=3.42·Ω=27.3 rad/s for max-axis (I_z).
# At 4800 steps the max-axis grows by e^31 — catastrophic.  At 300 steps (1.25 s)
# it grows by e^1.94=7x, giving a final deflection ~4.7° << STABLE_MAX_ANGLE.
# Mid-axis (real exponential instability μ=8.94 rad/s) tumbles past 60° in ~130
# steps, so 300 steps is ample to detect instability.
N_STEPS = 300       # 1.25 seconds — see comment above

STABLE_MAX_ANGLE_DEG   = 20.0   # stable runs: angle from initial axis stays < 20°
UNSTABLE_MIN_ANGLE_DEG = 60.0   # unstable run: angle must exceed 60° at some point


def _angle_deg(v1, v2):
    """Angle in degrees between two 3-vectors (Gf.Vec3d)."""
    n1 = Gf.Vec3d(v1).GetNormalized()
    n2 = Gf.Vec3d(v2).GetNormalized()
    dot = max(-1.0, min(1.0, float(n1.GetDot(n2))))
    return math.degrees(math.acos(dot))


def run_test():
    omni.usd.get_context().new_stage()
    stage = omni.usd.get_context().get_stage()
    setup_physics_scene(stage, gravity=0.0)

    # Spawn all three test bodies simultaneously so we only need one
    # SimulationContext / start_sim call.  Space them far apart (100 m) so
    # they never interact.
    # Spawn heights: SimulationContext applies gravity 9.81 m/s².  At N_STEPS=300
    # (1.25 s), free-fall = 0.5*9.81*1.25² ≈ 7.7 m.  z=20 m keeps all bodies
    # above the ground plane (box half-z=2.5 m, so clearance = 20-7.7-2.5 = 9.8 m).
    cases = [
        ("min-axis (I_x, STABLE)",   (OMEGA_SPIN, EPS,        EPS),        "/World/BodyMin",  20.0),
        ("mid-axis (I_y, UNSTABLE)", (EPS,        OMEGA_SPIN, EPS),        "/World/BodyMid",  30.0),
        ("max-axis (I_z, STABLE)",   (EPS,        EPS,        OMEGA_SPIN), "/World/BodyMax",  40.0),
    ]

    bodies = {}
    for label, init_omega, path, z0 in cases:
        bodies[label] = spawn_rigid_box(
            stage, path,
            pos=(0.0, 0.0, z0),
            half_extents=(1.0, 1.5, 2.5),
            mass=MASS,
            inertia=(I_X, I_Y, I_Z),
            init_ang_vel=init_omega,
            gyroscopic=True,
        )

    sim = get_simulation_context(DT)
    start_sim(sim)

    # Warmup — flush triple-step so initial_dir is taken from stable PhysX state
    N_WARMUP = 3
    for _ in range(N_WARMUP):
        sim.step(render=False)

    # Record initial body-frame spin direction for each body
    initial_dirs = {}
    for label, _, _, _ in cases:
        body = bodies[label]
        state0 = get_state(body)
        omega_body0 = to_body_frame(state0["ang_vel"], state0["quat"])
        initial_dirs[label] = Gf.Vec3d(omega_body0).GetNormalized()

    max_angles = {label: 0.0 for label, _, _, _ in cases}

    for step in range(N_STEPS):
        sim.step(render=False)
        for label, _, _, _ in cases:
            state = get_state(bodies[label])
            omega_body = to_body_frame(state["ang_vel"], state["quat"])
            angle = _angle_deg(omega_body, initial_dirs[label])
            if angle > max_angles[label]:
                max_angles[label] = angle

    for label, _, _, _ in cases:
        print(f"  {label}: max angle = {max_angles[label]:.1f}°")

    min_stable   = max_angles["min-axis (I_x, STABLE)"]
    mid_unstable = max_angles["mid-axis (I_y, UNSTABLE)"]
    max_stable   = max_angles["max-axis (I_z, STABLE)"]

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
    print(f"T6 PASS — intermediate-axis instability confirmed (tennis-racket theorem)", flush=True)
    _exit_code = 0
except AssertionError as e:
    print(f"T6 FAIL: {e}", flush=True)
    _exit_code = 1
except Exception as e:
    import traceback
    print(f"T6 ERROR: {e}", flush=True)
    traceback.print_exc()
    _exit_code = 2
# Skip app.close() — it blocks 26+ min on GeForce (RTX MDL shader compilation
# in a background thread). The --rm container releases GPU resources via cgroup.
import os; os._exit(_exit_code)
