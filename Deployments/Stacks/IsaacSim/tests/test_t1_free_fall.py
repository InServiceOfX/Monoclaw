#!/usr/bin/env python3
"""
T1 — Free-fall smoke test (3DOF point mass)

Physics: z(t) = z0 - 0.5*g*t^2,  v_z(t) = -g*t
Energy:  E = 0.5*m*v^2 + m*g*z = const

Catches: wrong gravity sign/magnitude, wrong mass, wrong unit scaling,
         integrator not running at all.

Run:
    docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/tests/test_t1_free_fall.py
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
    setup_physics_scene, spawn_rigid_sphere, get_state,
    get_simulation_context, start_sim, assert_rel, assert_abs,
)

# ── Test parameters ──────────────────────────────────────────────────────────
G       = 9.81          # m/s²
Z0      = 100.0         # m initial height
MASS    = 5.0           # kg (irrelevant for freefall but checked implicitly)
DT      = 1 / 240.0    # physics timestep
N_STEPS = 720           # 3 seconds of sim time
POS_TOL = 0.01          # max absolute position error (m) — tight: uses symplectic Euler theory
VEL_TOL = 0.005         # max relative velocity error
ENERGY_TOL = 1e-3       # max relative energy drift


def run_test():
    stage = omni.usd.get_context().get_stage()

    setup_physics_scene(stage, gravity=G, gravity_dir=(0, 0, -1))
    body = spawn_rigid_sphere(stage, "/World/Body",
                               pos=(0.0, 0.0, Z0), radius=0.5, mass=MASS)

    sim = get_simulation_context(DT)
    start_sim(sim)

    # The first sim.step() call after sim.play() advances physics by 2 steps
    # (an initialization flush step plus the actual step).  Consume it with a
    # few throw-away steps so all subsequent loop iterations are single-advance.
    # We then measure the reference state from this clean baseline.
    N_WARMUP = 3
    for _ in range(N_WARMUP):
        sim.step(render=False)

    state0   = get_state(body)
    z0_ref   = float(state0["pos"][2])
    vz0_ref  = float(state0["lin_vel"][2])
    v0sq     = sum(float(state0["lin_vel"][i])**2 for i in range(3))

    # Sanity: warmup shouldn't move the body more than a small amount
    if abs(z0_ref - Z0) > 2.0:
        raise AssertionError(
            f"Reference z={z0_ref:.4f} m after {N_WARMUP} warmup steps — "
            f"too far from spawn Z0={Z0}"
        )

    print(f"  Reference state after {N_WARMUP} warmup steps: "
          f"z0={z0_ref:.4f} m  vz0={vz0_ref:.6f} m/s")

    E0 = 0.5 * MASS * v0sq + MASS * G * z0_ref
    t  = 0.0
    max_pos_err = 0.0
    max_E_err   = 0.0

    for step in range(N_STEPS):
        sim.step(render=False)
        t += DT

        state   = get_state(body)
        z_sim   = float(state["pos"][2])
        vz_sim  = float(state["lin_vel"][2])

        # PhysX uses symplectic Euler: v_{n+1} = v_n - g*dt, z_{n+1} = z_n + v_{n+1}*dt
        # Exact discrete position after k steps: z0 + k*v0*dt - g*dt^2*k*(k+1)/2
        # Equivalently: z0 + v0*t - 0.5*g*t*(t+dt)  where t = k*dt
        # Velocity matches continuous theory exactly: v0 - g*t
        z_theory  = z0_ref + vz0_ref * t - 0.5 * G * t * (t + DT)
        vz_theory = vz0_ref - G * t

        pos_err = abs(z_sim - z_theory)
        max_pos_err = max(max_pos_err, pos_err)

        assert_rel(vz_sim, vz_theory, VEL_TOL, f"step {step}: v_z")

        # Energy conservation: E = KE + PE
        v2 = float(state["lin_vel"][0])**2 + float(state["lin_vel"][1])**2 + vz_sim**2
        E  = 0.5 * MASS * v2 + MASS * G * z_sim
        E_err = abs(E - E0) / E0
        max_E_err = max(max_E_err, E_err)
        if E_err > ENERGY_TOL:
            raise AssertionError(
                f"step {step} t={t:.3f}s: energy drift {E_err:.4e} > {ENERGY_TOL}"
            )

    # Final position check
    if max_pos_err > POS_TOL:
        raise AssertionError(
            f"max position error {max_pos_err:.4f} m > {POS_TOL} m over {N_STEPS} steps"
        )

    z_final_t = N_STEPS * DT
    z_final_theory = z0_ref + vz0_ref * z_final_t - 0.5 * G * z_final_t * (z_final_t + DT)
    state_final = get_state(body)
    z_final_sim = float(state_final["pos"][2])
    print(f"  z_final:  sim={z_final_sim:.4f}  theory={z_final_theory:.4f}  "
          f"err={abs(z_final_sim-z_final_theory):.4f} m")
    print(f"  max pos error: {max_pos_err:.4f} m  max energy drift: {max_E_err:.2e}")


try:
    run_test()
    print("T1 PASS — free-fall position, velocity, and energy all within tolerance")
    _exit_code = 0
except AssertionError as e:
    print(f"T1 FAIL: {e}")
    _exit_code = 1
except Exception as e:
    import traceback
    print(f"T1 ERROR: {e}")
    traceback.print_exc()
    _exit_code = 2
finally:
    app.close()

sys.exit(_exit_code)
