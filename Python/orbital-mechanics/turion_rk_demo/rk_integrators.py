"""Runge-Kutta integrators used by the orbital demo.

State convention: y is a 1D numpy array.
ODE convention: f(t, y) returns dy/dt with same shape as y.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Tuple

import numpy as np


ODEFunc = Callable[[float, np.ndarray], np.ndarray]


@dataclass
class AdaptiveResult:
    t: np.ndarray
    y: np.ndarray
    accepted_steps: int
    rejected_steps: int


def rk4_step(f: ODEFunc, t: float, y: np.ndarray, h: float) -> np.ndarray:
    """Single fixed RK4 step.

    y_{n+1} = y_n + h/6 * (k1 + 2k2 + 2k3 + k4)
    """

    k1 = f(t, y)
    k2 = f(t + 0.5 * h, y + 0.5 * h * k1)
    k3 = f(t + 0.5 * h, y + 0.5 * h * k2)
    k4 = f(t + h, y + h * k3)
    return y + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def integrate_rk4(
    f: ODEFunc,
    t0: float,
    y0: np.ndarray,
    tf: float,
    dt: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Integrate with fixed-step RK4 from t0 to tf."""

    if dt <= 0.0:
        raise ValueError("dt must be positive")

    t_values: List[float] = [t0]
    y_values: List[np.ndarray] = [np.array(y0, dtype=float)]

    t = float(t0)
    y = np.array(y0, dtype=float)

    while t < tf:
        h = min(dt, tf - t)
        y = rk4_step(f, t, y, h)
        t += h
        t_values.append(t)
        y_values.append(y.copy())

    return np.array(t_values), np.vstack(y_values)


def rk45_step_dopri54(
    f: ODEFunc,
    t: float,
    y: np.ndarray,
    h: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Single Dormand-Prince 5(4) step.

    Returns:
        y5: 5th-order solution
        err: estimate of local truncation error (y5 - y4)
    """

    k1 = f(t, y)
    k2 = f(t + h * (1 / 5), y + h * ((1 / 5) * k1))
    k3 = f(t + h * (3 / 10), y + h * ((3 / 40) * k1 + (9 / 40) * k2))
    k4 = f(
        t + h * (4 / 5),
        y + h * ((44 / 45) * k1 + (-56 / 15) * k2 + (32 / 9) * k3),
    )
    k5 = f(
        t + h * (8 / 9),
        y
        + h
        * (
            (19372 / 6561) * k1
            + (-25360 / 2187) * k2
            + (64448 / 6561) * k3
            + (-212 / 729) * k4
        ),
    )
    k6 = f(
        t + h,
        y
        + h
        * (
            (9017 / 3168) * k1
            + (-355 / 33) * k2
            + (46732 / 5247) * k3
            + (49 / 176) * k4
            + (-5103 / 18656) * k5
        ),
    )
    k7 = f(
        t + h,
        y
        + h
        * (
            (35 / 384) * k1
            + (500 / 1113) * k3
            + (125 / 192) * k4
            + (-2187 / 6784) * k5
            + (11 / 84) * k6
        ),
    )

    # 5th-order (accepted solution)
    y5 = y + h * (
        (35 / 384) * k1
        + (500 / 1113) * k3
        + (125 / 192) * k4
        + (-2187 / 6784) * k5
        + (11 / 84) * k6
    )

    # 4th-order (embedded)
    y4 = y + h * (
        (5179 / 57600) * k1
        + (7571 / 16695) * k3
        + (393 / 640) * k4
        + (-92097 / 339200) * k5
        + (187 / 2100) * k6
        + (1 / 40) * k7
    )

    return y5, (y5 - y4)


def integrate_rk45_adaptive(
    f: ODEFunc,
    t0: float,
    y0: np.ndarray,
    tf: float,
    dt_init: float,
    rtol: float = 1e-9,
    atol: float = 1e-12,
    dt_min: float = 1e-6,
    dt_max: float = 200.0,
) -> AdaptiveResult:
    """Adaptive integration using Dormand-Prince 5(4) error control.

    Error norm: RMS over scaled componentwise errors
        scale_i = atol + rtol * max(|y_i|, |y_i(new)|)
    """

    if dt_init <= 0.0:
        raise ValueError("dt_init must be positive")

    t = float(t0)
    y = np.array(y0, dtype=float)
    h = min(dt_init, tf - t0)

    t_values: List[float] = [t]
    y_values: List[np.ndarray] = [y.copy()]

    accepted = 0
    rejected = 0

    safety = 0.9
    exponent = 1.0 / 5.0  # method order control from 5th-order solution

    while t < tf:
        h = min(h, tf - t)
        if h < dt_min:
            raise RuntimeError("Adaptive step size fell below dt_min")

        y_new, err = rk45_step_dopri54(f, t, y, h)

        scale = atol + rtol * np.maximum(np.abs(y), np.abs(y_new))
        err_norm = np.sqrt(np.mean((err / scale) ** 2))

        if err_norm <= 1.0:
            # accept
            t += h
            y = y_new
            t_values.append(t)
            y_values.append(y.copy())
            accepted += 1

            if err_norm == 0.0:
                growth = 2.0
            else:
                growth = safety * err_norm ** (-exponent)
            h = min(dt_max, h * np.clip(growth, 0.2, 5.0))
        else:
            # reject, retry with smaller h
            rejected += 1
            shrink = safety * err_norm ** (-exponent)
            h = max(dt_min, h * np.clip(shrink, 0.1, 0.5))

    return AdaptiveResult(
        t=np.array(t_values),
        y=np.vstack(y_values),
        accepted_steps=accepted,
        rejected_steps=rejected,
    )
