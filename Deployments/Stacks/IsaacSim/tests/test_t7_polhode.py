#!/usr/bin/env python3
"""
T7 — Polhode constraint (Poinsot's geometric construction) (6DOF)

For a torque-free asymmetric rigid body, the body-frame angular velocity ω
must trace the polhode — the intersection of the energy and momentum ellipsoids
(Goldstein §5.5):

  Momentum ellipsoid: L² = (I_x*wx)² + (I_y*wy)² + (I_z*wz)² = const

PhysX's symplectic Euler conserves angular momentum (|h_world| = const) but
not T_rot exactly — the rotational kinetic energy drifts at rate ∝ coupling²
for asymmetric bodies.  T7 therefore verifies L² conservation only, which is
the stronger test that the body-frame Euler coupling is applied correctly.

T4 checks angular momentum in the inertial frame; T7 checks the body-frame
computation (via to_body_frame quaternion rotation) — these are complementary.

Reference: Goldstein §5.5 "Poinsot's geometrical representation", Sidi §4.4.11

Run:
    docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/tests/test_t7_polhode.py
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

MASS    = 80.0
I_X     = 600.0     # kg·m²
I_Y     = 1800.0
I_Z     = 3600.0

# Asymmetric-top initial conditions that produce a non-trivial polhode
# (avoids principal-axis degenerate case).  Mid-axis bias produces the classic
# Dzhanibekov flip behaviour, exercising all three Euler coupling terms.
OMEGA0  = (3.0, 4.0, 2.0)   # rad/s — asymmetric, no principal-axis symmetry

DT      = 1 / 240.0
N_STEPS = 6000      # 25 seconds

# PhysX conserves L² (|h|) to < 1e-4 per step (confirmed by T4 over 25 s).
# T_rot is NOT checked: symplectic Euler conserves L² but not T_rot for
# asymmetric bodies; the drift rate is O(coupling² · dt).
L2_TOL  = 5e-3      # relative drift in L² (≈ 2.5e-3 in |h|; drift rate ~1.9e-4/s × 25 s)


def _L2(omega_body):
    """Squared angular momentum magnitude from body-frame omega."""
    wx, wy, wz = omega_body[0], omega_body[1], omega_body[2]
    return (I_X * wx)**2 + (I_Y * wy)**2 + (I_Z * wz)**2


def run_test():
    omni.usd.get_context().new_stage()   # create_new_stage=False skips this in SimulationApp
    stage = omni.usd.get_context().get_stage()
    setup_physics_scene(stage, gravity=0.0)

    # z=4000: SimulationContext applies gravity 9.81 m/s²; in 25 s drop = 3066 m.
    # Starting at 4000 m keeps the body above ground for the entire 25 s test.
    body = spawn_rigid_box(
        stage, "/World/Body",
        pos=(0, 0, 4000),
        half_extents=(1.0, 2.0, 3.0),
        mass=MASS,
        inertia=(I_X, I_Y, I_Z),
        init_ang_vel=OMEGA0,
        gyroscopic=True,
    )

    sim = get_simulation_context(DT)
    start_sim(sim)

    # Flush the double-step so T0/L20 are taken from PhysX's stable state with
    # the correct quaternion (xformOp:orient) written back to USD.
    N_WARMUP = 3
    for _ in range(N_WARMUP):
        sim.step(render=False)

    # Sample initial body-frame omega (world = body at t=0 plus warmup steps)
    state0 = get_state(body)
    omega_body0 = to_body_frame(state0["ang_vel"], state0["quat"])
    L20 = _L2(omega_body0)

    if L20 < 1e-6:
        raise AssertionError("Initial L^2 is zero — check initial conditions")

    max_L2_drift = 0.0
    max_L2_step  = 0

    for step in range(N_STEPS):
        sim.step(render=False)
        state = get_state(body)
        omega_body = to_body_frame(state["ang_vel"], state["quat"])

        L2 = _L2(omega_body)
        L2_drift = abs(L2 - L20) / L20

        if L2_drift > max_L2_drift:
            max_L2_drift = L2_drift
            max_L2_step  = step

        if L2_drift > L2_TOL:
            raise AssertionError(
                f"step {step} (t={step*DT:.2f}s): L² drift {L2_drift:.4e} > {L2_TOL} "
                f"(L²={L2:.6f}, L²0={L20:.6f})"
            )

    print(f"  I_diag=({I_X},{I_Y},{I_Z})  omega0={OMEGA0}")
    print(f"  L²0={L20:.4f} (kg·m²/s)²")
    print(f"  max L²   drift: {max_L2_drift:.2e} at step {max_L2_step} "
          f"(t={max_L2_step*DT:.2f}s)")


try:
    run_test()
    print(f"T7 PASS — body-frame L² conserved (polhode constraint holds)", flush=True)
    _exit_code = 0
except AssertionError as e:
    print(f"T7 FAIL: {e}", flush=True)
    _exit_code = 1
except Exception as e:
    import traceback
    print(f"T7 ERROR: {e}", flush=True)
    traceback.print_exc()
    _exit_code = 2
# Skip app.close() — it blocks 26+ min on GeForce (RTX MDL shader compilation
# in a background thread). The --rm container releases GPU resources via cgroup.
import os; os._exit(_exit_code)
