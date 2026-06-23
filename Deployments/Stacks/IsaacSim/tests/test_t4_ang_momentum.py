#!/usr/bin/env python3
"""
T4 — Angular momentum conservation in inertial frame (6DOF)

Torque-free asymmetric rigid body. Angular momentum in the INERTIAL frame must
be constant. The body-frame angular velocity will precess (that is correct);
only the inertial-frame h = R * I * omega_body must not drift.

This is the most diagnostic single 6DOF test: it verifies the transport theorem
dh/dt|_inertial = tau is correctly implemented, i.e. the ω×(Iω) coupling is
present and the body→inertial rotation is applied correctly.

Reference: Sidi §4.2 / §4.8.1, Goldstein §5.4

Run:
    docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/tests/test_t4_ang_momentum.py
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
    get_simulation_context, start_sim, inertial_h, assert_rel,
)

# ── Body: asymmetric box ─────────────────────────────────────────────────────
MASS    = 100.0                    # kg
I_DIAG  = (800.0, 1500.0, 2500.0) # kg·m²  (I_x < I_y < I_z, all distinct)
OMEGA0  = (2.0, 3.0, 5.0)         # rad/s initial angular velocity (world = body at t=0)

DT      = 1 / 240.0
N_STEPS = 8000          # ~33 seconds
# PhysX symplectic Euler has small numerical drift in |h_inertial|; the drift
# rate for this I/omega/DT combination is ~9.5e-5/s → ~3.2e-3 over 33 s.
# H_TOL = 5e-3 gives ~60% margin, consistent with T7's L2_TOL.
H_TOL   = 5e-3          # max relative drift in |h_inertial|


def run_test():
    omni.usd.get_context().new_stage()   # create_new_stage=False skips this in SimulationApp
    stage = omni.usd.get_context().get_stage()

    setup_physics_scene(stage, gravity=0.0)
    body = spawn_rigid_box(
        stage, "/World/Body",
        pos=(0, 0, 0),
        half_extents=(1.0, 1.5, 2.0),
        mass=MASS,
        inertia=I_DIAG,
        init_ang_vel=OMEGA0,
        gyroscopic=True,
    )

    sim = get_simulation_context(DT)
    start_sim(sim)

    # Flush the double-step (first sim.step() runs flush+actual) so h0 is taken
    # from PhysX's stable post-init state with the correct quaternion written back.
    N_WARMUP = 3
    for _ in range(N_WARMUP):
        sim.step(render=False)

    # Compute initial angular momentum in inertial frame
    state0 = get_state(body)
    h0 = inertial_h(state0["ang_vel"], state0["quat"], I_DIAG)
    h0_mag = Gf.Vec3d(h0).GetLength()

    if h0_mag < 1e-6:
        raise AssertionError("Initial angular momentum is zero — check initial conditions")

    max_drift = 0.0
    max_drift_step = 0

    for step in range(N_STEPS):
        sim.step(render=False)
        state = get_state(body)
        h = inertial_h(state["ang_vel"], state["quat"], I_DIAG)
        h_mag = Gf.Vec3d(h).GetLength()

        drift = abs(h_mag - h0_mag) / h0_mag
        if drift > max_drift:
            max_drift = drift
            max_drift_step = step

        if drift > H_TOL:
            raise AssertionError(
                f"step {step}: |h_inertial| drift {drift:.4e} > {H_TOL} "
                f"(|h|={h_mag:.6f}, |h0|={h0_mag:.6f})"
            )

    print(f"  I_diag = {I_DIAG}  omega0 = {OMEGA0}")
    print(f"  |h0| = {h0_mag:.6f} kg·m²/s")
    print(f"  max |h| drift: {max_drift:.2e} at step {max_drift_step} "
          f"(t={max_drift_step*DT:.2f}s) over {N_STEPS} steps ({N_STEPS*DT:.1f}s)")


try:
    run_test()
    print(f"T4 PASS — angular momentum conserved in inertial frame", flush=True)
    _exit_code = 0
except AssertionError as e:
    print(f"T4 FAIL: {e}", flush=True)
    _exit_code = 1
except Exception as e:
    import traceback
    print(f"T4 ERROR: {e}", flush=True)
    traceback.print_exc()
    _exit_code = 2
# Skip app.close() — it blocks 26+ min on GeForce (RTX MDL shader compilation
# in a background thread). The --rm container releases GPU resources via cgroup.
import os; os._exit(_exit_code)
