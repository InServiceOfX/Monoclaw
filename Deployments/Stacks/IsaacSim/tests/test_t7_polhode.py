#!/usr/bin/env python3
"""
T7 — Polhode constraint (Poinsot's geometric construction) (6DOF)

For a torque-free asymmetric rigid body, the body-frame angular velocity ω
must trace the intersection of two ellipsoids (Goldstein §5.5):

  Energy ellipsoid:   T_rot = 0.5*(I_x*wx² + I_y*wy² + I_z*wz²) = const
  Momentum ellipsoid: L²    = (I_x*wx)² + (I_y*wy)² + (I_z*wz)²  = const

Both quantities must be individually conserved. T4 checks angular momentum in
the inertial frame; T7 checks the body-frame dynamics directly — these are
complementary tests. A solver can conserve inertial-frame h while still
accumulating body-frame integration error.

Reference: Goldstein §5.5 "Poinsot's geometrical representation", Sidi §4.4.11

Run:
    docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/tests/test_t7_polhode.py
"""
import sys
import math
sys.path.insert(0, "/isaac-sim/tests")
sys.argv += ["--/rtx/materialDb/syncLoads=False", "--/rtx/hydra/materialSyncLoads=False"]

from isaacsim import SimulationApp
app = SimulationApp({"headless": True, "anti_aliasing": 0,
                     "experience": "/isaac-sim/apps/isaacsim.exp.physics.kit"})

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

# Initial omega in world frame (= body frame at t=0 with identity orientation)
# Place it in the "waist" of the energy ellipsoid (between min and max axes)
# so the polhode is a nontrivial closed curve
OMEGA0  = (3.0, 4.0, 2.0)    # rad/s

DT      = 1 / 240.0
N_STEPS = 6000      # 25 seconds

# T4 and T7 are sensitive: PhysX PGS at 240 Hz should hold these < 0.1%
T_TOL   = 2e-3      # relative drift in rotational KE
L2_TOL  = 2e-3      # relative drift in L^2


def _T_rot(omega_body):
    """Rotational kinetic energy from body-frame omega."""
    wx, wy, wz = omega_body[0], omega_body[1], omega_body[2]
    return 0.5 * (I_X * wx**2 + I_Y * wy**2 + I_Z * wz**2)


def _L2(omega_body):
    """Squared angular momentum magnitude from body-frame omega."""
    wx, wy, wz = omega_body[0], omega_body[1], omega_body[2]
    return (I_X * wx)**2 + (I_Y * wy)**2 + (I_Z * wz)**2


def run_test():
    stage = omni.usd.get_context().get_stage()
    setup_physics_scene(stage, gravity=0.0)

    body = spawn_rigid_box(
        stage, "/World/Body",
        pos=(0, 0, 0),
        half_extents=(1.0, 2.0, 3.0),
        mass=MASS,
        inertia=(I_X, I_Y, I_Z),
        init_ang_vel=OMEGA0,
        gyroscopic=True,
    )

    sim = get_simulation_context(DT)
    start_sim(sim)

    # Sample initial body-frame omega (world = body at t=0)
    state0 = get_state(body)
    omega_body0 = to_body_frame(state0["ang_vel"], state0["quat"])
    T0  = _T_rot(omega_body0)
    L20 = _L2(omega_body0)

    if T0 < 1e-6 or L20 < 1e-6:
        raise AssertionError("Initial KE or L^2 is zero — check initial conditions")

    max_T_drift  = 0.0
    max_L2_drift = 0.0
    max_T_step   = 0
    max_L2_step  = 0

    for step in range(N_STEPS):
        sim.step(render=False)
        state = get_state(body)
        omega_body = to_body_frame(state["ang_vel"], state["quat"])

        T  = _T_rot(omega_body)
        L2 = _L2(omega_body)

        T_drift  = abs(T  - T0)  / T0
        L2_drift = abs(L2 - L20) / L20

        if T_drift > max_T_drift:
            max_T_drift = T_drift
            max_T_step  = step
        if L2_drift > max_L2_drift:
            max_L2_drift = L2_drift
            max_L2_step  = step

        if T_drift > T_TOL:
            raise AssertionError(
                f"step {step} (t={step*DT:.2f}s): T_rot drift {T_drift:.4e} > {T_TOL} "
                f"(T={T:.6f}, T0={T0:.6f})"
            )
        if L2_drift > L2_TOL:
            raise AssertionError(
                f"step {step} (t={step*DT:.2f}s): L² drift {L2_drift:.4e} > {L2_TOL} "
                f"(L²={L2:.6f}, L²0={L20:.6f})"
            )

    print(f"  I_diag=({I_X},{I_Y},{I_Z})  omega0={OMEGA0}")
    print(f"  T0={T0:.4f} J   L²0={L20:.4f} (kg·m²/s)²")
    print(f"  max T_rot drift: {max_T_drift:.2e} at step {max_T_step} "
          f"(t={max_T_step*DT:.2f}s)")
    print(f"  max L²   drift: {max_L2_drift:.2e} at step {max_L2_step} "
          f"(t={max_L2_step*DT:.2f}s)")


try:
    run_test()
    print("T7 PASS — body-frame KE and L² conserved (polhode constraint holds)")
    _exit_code = 0
except AssertionError as e:
    print(f"T7 FAIL: {e}")
    _exit_code = 1
except Exception as e:
    import traceback
    print(f"T7 ERROR: {e}")
    traceback.print_exc()
    _exit_code = 2
finally:
    app.close()

sys.exit(_exit_code)
