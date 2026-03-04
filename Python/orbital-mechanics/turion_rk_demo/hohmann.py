"""Hohmann transfer helpers for coplanar circular orbits."""

from __future__ import annotations

from typing import Dict

import numpy as np


def hohmann_transfer(r1: float, r2: float, mu: float) -> Dict[str, float]:
    """Return delta-v and transfer time for a 2-impulse Hohmann transfer.

    Args:
        r1: initial circular orbit radius [km]
        r2: target circular orbit radius [km]
        mu: gravitational parameter [km^3/s^2]
    """

    if r1 <= 0 or r2 <= 0:
        raise ValueError("Orbit radii must be positive")

    a_t = 0.5 * (r1 + r2)

    v1 = np.sqrt(mu / r1)
    v2 = np.sqrt(mu / r2)

    v_peri_t = np.sqrt(mu * (2.0 / r1 - 1.0 / a_t))
    v_apo_t = np.sqrt(mu * (2.0 / r2 - 1.0 / a_t))

    dv1 = abs(v_peri_t - v1)
    dv2 = abs(v2 - v_apo_t)
    dv_total = dv1 + dv2

    transfer_time = np.pi * np.sqrt(a_t**3 / mu)  # half period of transfer ellipse

    return {
        "dv1": float(dv1),
        "dv2": float(dv2),
        "dv_total": float(dv_total),
        "transfer_time": float(transfer_time),
    }
