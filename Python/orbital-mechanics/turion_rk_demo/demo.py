"""Demo script: RK propagation, energy drift comparison, and Hohmann transfer.

Run:
    python demo.py
"""

from __future__ import annotations

import numpy as np

from hohmann import hohmann_transfer
from rk_integrators import integrate_rk4, integrate_rk45_adaptive
from two_body import MU_EARTH, R_EARTH, specific_orbital_energy, two_body_rhs


def main() -> None:
    # Simple near-circular LEO setup
    altitude_km = 500.0
    r0_mag = R_EARTH + altitude_km
    v0_mag = np.sqrt(MU_EARTH / r0_mag)

    r0 = np.array([r0_mag, 0.0, 0.0])
    v0 = np.array([0.0, v0_mag, 0.0])
    y0 = np.hstack((r0, v0))

    # Orbital period of circular orbit
    period = 2.0 * np.pi * np.sqrt(r0_mag**3 / MU_EARTH)
    tf = 6.0 * period

    print("=== Turion RK Orbital Demo ===")
    print(f"Initial circular LEO radius: {r0_mag:.3f} km")
    print(f"Approx period: {period:.3f} s ({period / 60.0:.2f} min)")

    rhs = lambda t, y: two_body_rhs(t, y, mu=MU_EARTH, use_j2=False)

    # Fixed-step RK4
    dt_rk4 = 20.0
    t_rk4, y_rk4 = integrate_rk4(rhs, 0.0, y0, tf, dt=dt_rk4)

    # Adaptive RK45-style
    adaptive = integrate_rk45_adaptive(
        rhs,
        0.0,
        y0,
        tf,
        dt_init=30.0,
        rtol=1e-9,
        atol=1e-12,
        dt_min=1e-4,
        dt_max=200.0,
    )

    # Energy drift comparison
    eps0 = specific_orbital_energy(y0, MU_EARTH)
    eps_rk4 = np.array([specific_orbital_energy(s, MU_EARTH) for s in y_rk4])
    eps_adp = np.array([specific_orbital_energy(s, MU_EARTH) for s in adaptive.y])

    drift_rk4 = eps_rk4 - eps0
    drift_adp = eps_adp - eps0

    print("\nEnergy drift (specific orbital energy, km^2/s^2):")
    print(
        f"RK4:     max |drift| = {np.max(np.abs(drift_rk4)):.3e}, "
        f"final drift = {drift_rk4[-1]:.3e}"
    )
    print(
        f"Adaptive: max |drift| = {np.max(np.abs(drift_adp)):.3e}, "
        f"final drift = {drift_adp[-1]:.3e}, "
        f"accepted/rejected = {adaptive.accepted_steps}/{adaptive.rejected_steps}"
    )

    # Hohmann transfer example: 500 km -> 1000 km circular orbit
    r1 = R_EARTH + 500.0
    r2 = R_EARTH + 1000.0
    h = hohmann_transfer(r1, r2, MU_EARTH)

    print("\nHohmann transfer (circular, coplanar):")
    print(f"r1 = {r1:.3f} km, r2 = {r2:.3f} km")
    print(
        f"dv1 = {h['dv1']:.6f} km/s, dv2 = {h['dv2']:.6f} km/s, "
        f"dv_total = {h['dv_total']:.6f} km/s"
    )
    print(f"transfer_time = {h['transfer_time']:.3f} s ({h['transfer_time'] / 60.0:.2f} min)")

    # Orbit plot
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 7))
        ax.plot(y_rk4[:, 0], y_rk4[:, 1], label="RK4", lw=1.5)
        ax.plot(adaptive.y[:, 0], adaptive.y[:, 1], label="Adaptive RK45", lw=1.2, alpha=0.8)

        earth = plt.Circle((0.0, 0.0), R_EARTH, color="tab:blue", alpha=0.2, label="Earth")
        ax.add_patch(earth)

        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("x [km]")
        ax.set_ylabel("y [km]")
        ax.set_title("LEO propagation: RK4 vs Adaptive RK45")
        ax.grid(True, alpha=0.3)
        ax.legend()

        out_path = "orbit_demo.png"
        fig.tight_layout()
        fig.savefig(out_path, dpi=160)
        print(f"\nSaved plot: {out_path}")
    except Exception as exc:  # pragma: no cover (best-effort plotting)
        print(f"\nPlotting skipped: {exc}")


if __name__ == "__main__":
    main()
