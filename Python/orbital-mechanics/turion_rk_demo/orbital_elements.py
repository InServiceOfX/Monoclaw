"""Conversions between Cartesian state and classical orbital elements (COE).

COE fields:
- a: semi-major axis [km]
- e: eccentricity [-]
- i: inclination [rad]
- raan: right ascension of ascending node [rad]
- argp: argument of periapsis [rad]
- nu: true anomaly [rad]
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np


def state_to_coe(r: np.ndarray, v: np.ndarray, mu: float) -> Dict[str, float]:
    """Convert inertial Cartesian position/velocity to classical orbital elements."""

    r_norm = np.linalg.norm(r)
    v_norm = np.linalg.norm(v)

    h_vec = np.cross(r, v)
    h = np.linalg.norm(h_vec)

    k_hat = np.array([0.0, 0.0, 1.0])
    n_vec = np.cross(k_hat, h_vec)
    n = np.linalg.norm(n_vec)

    e_vec = (1.0 / mu) * ((v_norm**2 - mu / r_norm) * r - np.dot(r, v) * v)
    e = np.linalg.norm(e_vec)

    # Specific orbital energy -> semi-major axis
    eps = 0.5 * v_norm**2 - mu / r_norm
    a = -mu / (2.0 * eps) if abs(eps) > 1e-14 else np.inf

    i = np.arccos(np.clip(h_vec[2] / h, -1.0, 1.0))

    if n > 1e-14:
        raan = np.arccos(np.clip(n_vec[0] / n, -1.0, 1.0))
        if n_vec[1] < 0:
            raan = 2.0 * np.pi - raan
    else:
        raan = 0.0

    if n > 1e-14 and e > 1e-14:
        argp = np.arccos(np.clip(np.dot(n_vec, e_vec) / (n * e), -1.0, 1.0))
        if e_vec[2] < 0:
            argp = 2.0 * np.pi - argp
    else:
        argp = 0.0

    if e > 1e-14:
        nu = np.arccos(np.clip(np.dot(e_vec, r) / (e * r_norm), -1.0, 1.0))
        if np.dot(r, v) < 0:
            nu = 2.0 * np.pi - nu
    else:
        # Circular orbit: true anomaly undefined from e-vector; use node if possible.
        if n > 1e-14:
            nu = np.arccos(np.clip(np.dot(n_vec, r) / (n * r_norm), -1.0, 1.0))
            if r[2] < 0:
                nu = 2.0 * np.pi - nu
        else:
            nu = np.arctan2(r[1], r[0]) % (2.0 * np.pi)

    return {
        "a": float(a),
        "e": float(e),
        "i": float(i),
        "raan": float(raan),
        "argp": float(argp),
        "nu": float(nu),
    }


def coe_to_state(
    a: float,
    e: float,
    i: float,
    raan: float,
    argp: float,
    nu: float,
    mu: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Convert COE to inertial Cartesian state vectors."""

    p = a * (1.0 - e**2)

    r_pf = np.array(
        [
            p * np.cos(nu) / (1.0 + e * np.cos(nu)),
            p * np.sin(nu) / (1.0 + e * np.cos(nu)),
            0.0,
        ]
    )

    v_pf = np.array(
        [
            -np.sqrt(mu / p) * np.sin(nu),
            np.sqrt(mu / p) * (e + np.cos(nu)),
            0.0,
        ]
    )

    cO, sO = np.cos(raan), np.sin(raan)
    ci, si = np.cos(i), np.sin(i)
    cw, sw = np.cos(argp), np.sin(argp)

    # Perifocal -> inertial rotation R3(raan) * R1(i) * R3(argp)
    rot = np.array(
        [
            [cO * cw - sO * sw * ci, -cO * sw - sO * cw * ci, sO * si],
            [sO * cw + cO * sw * ci, -sO * sw + cO * cw * ci, -cO * si],
            [sw * si, cw * si, ci],
        ]
    )

    r_eci = rot @ r_pf
    v_eci = rot @ v_pf
    return r_eci, v_eci
