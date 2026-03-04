"""Two-body dynamics with optional J2 perturbation."""

from __future__ import annotations

import numpy as np

# Earth constants in km, s units
MU_EARTH = 398600.4418  # km^3 / s^2
R_EARTH = 6378.1363  # km
J2_EARTH = 1.08262668e-3


def two_body_accel(r: np.ndarray, mu: float = MU_EARTH) -> np.ndarray:
    """Central gravity acceleration a = -mu * r / |r|^3."""

    r_norm = np.linalg.norm(r)
    return -mu * r / (r_norm**3)


def j2_accel(
    r: np.ndarray,
    mu: float = MU_EARTH,
    r_eq: float = R_EARTH,
    j2: float = J2_EARTH,
) -> np.ndarray:
    """J2 perturbation acceleration for an oblate primary.

    Formula (component form):
        a_J2 = (3/2) * J2 * mu * Re^2 / r^5 * [
            x*(5*z^2/r^2 - 1),
            y*(5*z^2/r^2 - 1),
            z*(5*z^2/r^2 - 3)
        ]
    """

    x, y, z = r
    r2 = np.dot(r, r)
    r1 = np.sqrt(r2)
    z2_over_r2 = (z * z) / r2

    factor = 1.5 * j2 * mu * (r_eq**2) / (r1**5)

    ax = factor * x * (5.0 * z2_over_r2 - 1.0)
    ay = factor * y * (5.0 * z2_over_r2 - 1.0)
    az = factor * z * (5.0 * z2_over_r2 - 3.0)
    return np.array([ax, ay, az])


def two_body_rhs(
    t: float,
    state: np.ndarray,
    mu: float = MU_EARTH,
    use_j2: bool = False,
    r_eq: float = R_EARTH,
    j2: float = J2_EARTH,
) -> np.ndarray:
    """State derivative for [x, y, z, vx, vy, vz]."""

    _ = t  # autonomous dynamics; keep argument for ODE solver interface

    r = state[:3]
    v = state[3:]

    a = two_body_accel(r, mu)
    if use_j2:
        a = a + j2_accel(r, mu=mu, r_eq=r_eq, j2=j2)

    return np.hstack((v, a))


def specific_orbital_energy(state: np.ndarray, mu: float = MU_EARTH) -> float:
    """Specific orbital energy: eps = v^2/2 - mu/r."""

    r = state[:3]
    v = state[3:]
    return 0.5 * np.dot(v, v) - mu / np.linalg.norm(r)
