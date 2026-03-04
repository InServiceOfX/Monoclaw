import numpy as np

from hohmann import hohmann_transfer
from rk_integrators import integrate_rk4
from two_body import MU_EARTH, R_EARTH, two_body_rhs


def test_circular_orbit_radius_stays_near_constant_short_horizon():
    alt_km = 500.0
    r0 = R_EARTH + alt_km
    v0 = np.sqrt(MU_EARTH / r0)

    y0 = np.array([r0, 0.0, 0.0, 0.0, v0, 0.0])
    rhs = lambda t, y: two_body_rhs(t, y, mu=MU_EARTH, use_j2=False)

    t, y = integrate_rk4(rhs, 0.0, y0, tf=1200.0, dt=10.0)
    radii = np.linalg.norm(y[:, :3], axis=1)

    # over a short horizon, near-circular orbit should keep radius very close
    assert np.max(np.abs(radii - r0)) < 1.0  # km


def test_hohmann_delta_v_positive():
    r1 = R_EARTH + 500.0
    r2 = R_EARTH + 1000.0
    out = hohmann_transfer(r1, r2, MU_EARTH)

    assert out["dv1"] > 0.0
    assert out["dv2"] > 0.0
    assert out["dv_total"] > 0.0
    assert out["transfer_time"] > 0.0
