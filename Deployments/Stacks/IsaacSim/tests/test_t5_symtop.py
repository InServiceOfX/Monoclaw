#!/usr/bin/env python3
"""
T5 — Torque-free symmetric top: exact body-frame precession rate (6DOF)

For a symmetric body with I_x = I_y = I_T, I_z = I_A (axial):
  - Spin component omega_z stays constant (verified).
  - Transverse magnitude |omega_perp| stays constant (verified).
  - Body-frame omega precesses about the symmetry axis (z) at rate:
      lambda = omega_z * (I_A - I_T) / I_T       [Sidi 4.5.3, Goldstein 5.6]
  - We measure lambda from the zero-crossing period of omega_x(t) and compare.

Notes:
  - Initial omega_z must be nonzero (spin axis).
  - omega_perp must be small relative to omega_z for the linearised solution to
    hold without beating from higher harmonics.
  - Body-frame omega_x(t) = omega_perp * cos(lambda*t), so its period = 2*pi/lambda.

Reference: Sidi §4.5 eqs (4.5.1)-(4.5.7), Goldstein §5.6

Run:
    docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/tests/test_t5_symtop.py
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
    get_simulation_context, start_sim, to_body_frame, assert_rel,
)

# ── Body: oblate symmetric top  (I_T < I_A → prograde precession) ───────────
MASS    = 50.0
I_T     = 1000.0           # kg·m²  transverse  (I_x = I_y)
I_A     = 3000.0           # kg·m²  axial        (I_z)
OMEGA_Z = 10.0             # rad/s spin about symmetry (+z) axis
OMEGA_X0 = 0.5            # rad/s small initial transverse perturbation

# Predicted precession rate (body frame) — Sidi (4.5.3)
LAMBDA_THEORY = OMEGA_Z * (I_A - I_T) / I_T     # rad/s
PERIOD_THEORY = 2 * math.pi / abs(LAMBDA_THEORY)

DT      = 1 / 240.0
# Run for ~6 full precession periods
N_STEPS = int(6 * PERIOD_THEORY / DT) + 100
LAMBDA_TOL  = 0.05    # 5% frequency tolerance
SPIN_TOL    = 1e-3    # omega_z must stay constant within 0.1%
PERP_TOL    = 1e-3    # |omega_perp| must stay constant within 0.1%


def run_test():
    stage = omni.usd.get_context().get_stage()
    setup_physics_scene(stage, gravity=0.0)

    # I_x = I_y = I_T (symmetric), I_z = I_A — achieved by equal x/y extents
    # We set diagonal inertia explicitly so geometry doesn't matter
    body = spawn_rigid_box(
        stage, "/World/Body",
        pos=(0, 0, 0),
        half_extents=(1.0, 1.0, 2.0),   # symmetric in x/y, different z
        mass=MASS,
        inertia=(I_T, I_T, I_A),
        init_ang_vel=(OMEGA_X0, 0.0, OMEGA_Z),   # world frame at t=0 = body frame
        gyroscopic=True,
    )

    sim = get_simulation_context(DT)
    start_sim(sim)

    # Collect body-frame omega over time for zero-crossing analysis
    omega_x_body_series = []
    omega_z_body_series = []
    omega_perp_body_series = []

    for step in range(N_STEPS):
        sim.step(render=False)
        state = get_state(body)
        omega_world = state["ang_vel"]
        q = state["quat"]

        omega_body = to_body_frame(omega_world, q)
        ox, oy, oz = float(omega_body[0]), float(omega_body[1]), float(omega_body[2])

        omega_x_body_series.append(ox)
        omega_z_body_series.append(oz)
        omega_perp_body_series.append(math.sqrt(ox**2 + oy**2))

    # ── Check 1: omega_z (spin) stays constant ────────────────────────────────
    oz_mean  = sum(omega_z_body_series) / len(omega_z_body_series)
    oz_drift = max(abs(oz - oz_mean) for oz in omega_z_body_series) / abs(oz_mean)
    if oz_drift > SPIN_TOL:
        raise AssertionError(
            f"omega_z (spin) drift {oz_drift:.4e} > {SPIN_TOL}; "
            f"mean={oz_mean:.4f} expected ~{OMEGA_Z}"
        )
    print(f"  Check 1 OK: omega_z mean={oz_mean:.4f} drift={oz_drift:.2e}")

    # ── Check 2: |omega_perp| stays constant ─────────────────────────────────
    perp_mean  = sum(omega_perp_body_series) / len(omega_perp_body_series)
    perp_drift = max(abs(p - perp_mean) for p in omega_perp_body_series) / perp_mean
    if perp_drift > PERP_TOL:
        raise AssertionError(
            f"|omega_perp| drift {perp_drift:.4e} > {PERP_TOL}; "
            f"mean={perp_mean:.4f} expected ~{OMEGA_X0}"
        )
    print(f"  Check 2 OK: |omega_perp| mean={perp_mean:.4f} drift={perp_drift:.2e}")

    # ── Check 3: precession rate from zero-crossings of omega_x_body ─────────
    # omega_x(t) = omega_perp * cos(lambda*t) — count half-period from sign changes
    crossings = []
    for i in range(1, len(omega_x_body_series)):
        if omega_x_body_series[i-1] * omega_x_body_series[i] < 0:
            # Linear interpolation for sub-step timing
            frac = abs(omega_x_body_series[i-1]) / (
                abs(omega_x_body_series[i-1]) + abs(omega_x_body_series[i]))
            crossings.append((i - 1 + frac) * DT)

    if len(crossings) < 6:
        raise AssertionError(
            f"Too few zero-crossings ({len(crossings)}) — "
            f"expected ~{int(6*PERIOD_THEORY/DT / (PERIOD_THEORY/(2*DT))):.0f}. "
            f"Check that N_STEPS={N_STEPS} covers enough periods."
        )

    half_periods = [crossings[i+1] - crossings[i] for i in range(len(crossings)-1)]
    hp_mean = sum(half_periods) / len(half_periods)
    lambda_meas = math.pi / hp_mean   # lambda = pi / half-period

    print(f"  lambda theory={LAMBDA_THEORY:.4f} rad/s  "
          f"measured={lambda_meas:.4f} rad/s  "
          f"period theory={PERIOD_THEORY:.4f}s  measured={2*hp_mean:.4f}s")
    print(f"  zero-crossings={len(crossings)}")

    assert_rel(lambda_meas, LAMBDA_THEORY, LAMBDA_TOL, "precession rate lambda")


try:
    run_test()
    print("T5 PASS — symmetric top precession rate matches Sidi (4.5.3)")
    _exit_code = 0
except AssertionError as e:
    print(f"T5 FAIL: {e}")
    _exit_code = 1
except Exception as e:
    import traceback
    print(f"T5 ERROR: {e}")
    traceback.print_exc()
    _exit_code = 2
finally:
    app.close()

sys.exit(_exit_code)
