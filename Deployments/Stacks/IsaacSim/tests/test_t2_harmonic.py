#!/usr/bin/env python3
"""
T2 — Harmonic oscillator (3DOF)

A spring restoring force F = -k*(z - z0) is applied externally each step
(tests the force integrator, not PhysX joint springs).

Physics: z(t) = A*cos(omega_n*t),  omega_n = sqrt(k/m),  T = 2*pi/omega_n
Energy:  E = 0.5*k*A^2 = const

Catches: integrator energy drift, incorrect dt scaling of forces,
         systematic force-accumulation errors.

Run:
    docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/tests/test_t2_harmonic.py
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
    get_simulation_context, start_sim, apply_wrench, assert_rel,
)

# ── Test parameters ──────────────────────────────────────────────────────────
K       = 500.0         # N/m spring constant
MASS    = 10.0          # kg
Z0      = 0.0           # rest position (m)
A       = 2.0           # initial displacement (m)
DT      = 1 / 240.0
OMEGA_N = math.sqrt(K / MASS)          # natural frequency rad/s
PERIOD  = 2 * math.pi / OMEGA_N        # seconds
N_STEPS = int(5 * PERIOD / DT)         # 5 full periods
FREQ_TOL   = 0.02       # 2% frequency error allowed
# Symplectic Euler oscillates standard energy by ~0.5*K*DT*|x*v|_max/E0 ≈ 1.5%
# for these parameters; 2% gives margin while still catching gross errors
# (e.g. force applied twice per step, wrong DT scaling).
ENERGY_TOL = 2e-2       # 2% energy oscillation allowed over 5 periods
BODY_PATH  = "/World/Body"


def run_test():
    omni.usd.get_context().new_stage()   # create_new_stage=False skips this in SimulationApp
    stage = omni.usd.get_context().get_stage()

    # No gravity — pure spring oscillation along Z
    setup_physics_scene(stage, gravity=0.0, gravity_dir=(0, 0, -1))
    body = spawn_rigid_sphere(stage, BODY_PATH,
                               pos=(0.0, 0.0, Z0 + A),  # displaced by A
                               radius=0.3, mass=MASS)

    sim = get_simulation_context(DT)
    start_sim(sim)

    # The first sim.step() after play() runs a flush step + actual step (2 physics
    # ticks). Consume it with throwaway steps (no spring applied yet) so the main
    # loop starts on clean single-advance steps and E0 is taken from stable state.
    N_WARMUP = 3
    for _ in range(N_WARMUP):
        sim.step(render=False)

    state0 = get_state(body)
    z0_ref  = float(state0["pos"][2])
    vz0_ref = float(state0["lin_vel"][2])
    A_actual = z0_ref - Z0   # actual initial displacement from rest position

    E0 = 0.5 * K * A_actual**2 + 0.5 * MASS * vz0_ref**2
    zero_crossings = []     # track z=0 crossings to measure period
    last_z = Z0 + A
    max_E_err = 0.0

    for step in range(N_STEPS):
        state = get_state(body)
        z = float(state["pos"][2])
        vz = float(state["lin_vel"][2])

        # Restoring force toward Z0
        displacement = z - Z0
        fz = -K * displacement
        apply_wrench(BODY_PATH, force=(0, 0, fz))

        sim.step(render=False)

        state2 = get_state(body)
        z2 = float(state2["pos"][2])
        vz2 = float(state2["lin_vel"][2])

        # Detect zero-crossing (z changes sign relative to Z0)
        disp2 = z2 - Z0
        if (z - Z0) * disp2 < 0 and step > 5:
            zero_crossings.append(step * DT)

        # Energy check (KE + spring PE)
        E = 0.5 * MASS * vz2**2 + 0.5 * K * disp2**2
        E_err = abs(E - E0) / E0
        max_E_err = max(max_E_err, E_err)
        if E_err > ENERGY_TOL:
            raise AssertionError(
                f"step {step}: energy drift {E_err:.4e} > {ENERGY_TOL}"
            )

    # Need at least 8 zero-crossings for 4 half-periods to measure frequency
    if len(zero_crossings) < 8:
        raise AssertionError(
            f"Too few zero crossings ({len(zero_crossings)}) — oscillation may have died"
        )

    # Measure average half-period from consecutive crossings
    half_periods = [zero_crossings[i+1] - zero_crossings[i]
                    for i in range(len(zero_crossings) - 1)]
    measured_half_period = sum(half_periods) / len(half_periods)
    measured_period = 2 * measured_half_period
    measured_omega = 2 * math.pi / measured_period

    print(f"  omega_n theory={OMEGA_N:.4f}  measured={measured_omega:.4f}  "
          f"period theory={PERIOD:.4f}s  measured={measured_period:.4f}s")
    print(f"  max energy drift: {max_E_err:.2e}  zero crossings: {len(zero_crossings)}")

    assert_rel(measured_omega, OMEGA_N, FREQ_TOL, "natural frequency omega_n")


try:
    run_test()
    print(f"T2 PASS — harmonic oscillator frequency and energy within tolerance", flush=True)
    _exit_code = 0
except AssertionError as e:
    print(f"T2 FAIL: {e}", flush=True)
    _exit_code = 1
except Exception as e:
    import traceback
    print(f"T2 ERROR: {e}", flush=True)
    traceback.print_exc()
    _exit_code = 2
# Skip app.close() — it blocks 26+ min on GeForce (RTX MDL shader compilation
# in a background thread). The --rm container releases GPU resources via cgroup.
import os; os._exit(_exit_code)
