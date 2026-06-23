#!/usr/bin/env python3
"""
T3 — Linear momentum conservation (3DOF)

Part A: no forces → |p| = const
Part B: constant force F → p(t) = p0 + F*t  (impulse-momentum theorem)

Catches: numerical dissipation, force accumulation errors, wrong mass.
Goldstein §1.3.

Run:
    docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/tests/test_t3_lin_momentum.py
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
    setup_physics_scene, spawn_rigid_sphere, get_state,
    get_simulation_context, start_sim, apply_wrench, assert_rel, assert_abs,
)

DT      = 1 / 240.0
MASS    = 20.0          # kg
V0      = (3.0, -2.0, 5.0)  # initial velocity m/s (arbitrary direction)
F_EXT   = (10.0, -5.0, 8.0) # constant external force N
N_FREE  = 2000          # steps with no force
N_FORCE = 1000          # steps with constant force
MOM_TOL = 1e-4          # relative momentum drift tolerance (conservative)
IMP_TOL = 2e-3          # impulse-momentum tolerance (force integration error)


def _momentum(state):
    v = state["lin_vel"]
    return (MASS * float(v[0]), MASS * float(v[1]), MASS * float(v[2]))


def _mag(v3):
    return math.sqrt(v3[0]**2 + v3[1]**2 + v3[2]**2)


def run_test():
    omni.usd.get_context().new_stage()   # create_new_stage=False skips this in SimulationApp
    stage = omni.usd.get_context().get_stage()

    # Part A: no gravity, no forces
    setup_physics_scene(stage, gravity=0.0)
    body = spawn_rigid_sphere(stage, "/World/Body",
                               pos=(0, 0, 0), mass=MASS,
                               init_lin_vel=V0)

    sim = get_simulation_context(DT)
    start_sim(sim)

    # Flush the double-step (first sim.step() runs flush+actual) so the reference
    # p0 is taken from PhysX's stable post-init state, not the pre-run USD value.
    N_WARMUP = 3
    for _ in range(N_WARMUP):
        sim.step(render=False)

    state0 = get_state(body)
    p0 = _momentum(state0)
    p0_mag = _mag(p0)
    max_drift = 0.0

    for step in range(N_FREE):
        sim.step(render=False)
        st = get_state(body)
        p = _momentum(st)
        drift = abs(_mag(p) - p0_mag) / p0_mag
        max_drift = max(max_drift, drift)
        if drift > MOM_TOL:
            raise AssertionError(
                f"Part A step {step}: momentum drift {drift:.4e} > {MOM_TOL}"
            )

    print(f"  Part A: max momentum drift over {N_FREE} free steps: {max_drift:.2e}")

    # Part B: constant external force — check p(t) = p(0) + F*t
    # Continue from where part A left off (p0 is now the current momentum)
    state_b0 = get_state(body)
    pb0 = _momentum(state_b0)
    t = 0.0
    max_imp_err = 0.0

    for step in range(N_FORCE):
        apply_wrench("/World/Body", force=F_EXT)
        sim.step(render=False)
        t += DT
        st = get_state(body)
        p = _momentum(st)

        p_theory = tuple(pb0[i] + F_EXT[i] * t for i in range(3))
        for i, axis in enumerate("xyz"):
            err = abs(p[i] - p_theory[i])
            max_imp_err = max(max_imp_err, err)
            if err > IMP_TOL * MASS * max(abs(F_EXT[i]) * t, 0.1):
                raise AssertionError(
                    f"Part B step {step} axis {axis}: p={p[i]:.4f} "
                    f"theory={p_theory[i]:.4f} err={err:.4e}"
                )

    print(f"  Part B: max impulse-momentum error over {N_FORCE} forced steps: {max_imp_err:.2e}")


try:
    run_test()
    print(f"T3 PASS — linear momentum conserved and impulse-momentum theorem holds", flush=True)
    _exit_code = 0
except AssertionError as e:
    print(f"T3 FAIL: {e}", flush=True)
    _exit_code = 1
except Exception as e:
    import traceback
    print(f"T3 ERROR: {e}", flush=True)
    traceback.print_exc()
    _exit_code = 2
# Skip app.close() — it blocks 26+ min on GeForce (RTX MDL shader compilation
# in a background thread). The --rm container releases GPU resources via cgroup.
import os; os._exit(_exit_code)
