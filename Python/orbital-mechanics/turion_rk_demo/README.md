# Turion RK Orbital Demo

A small, interview-friendly orbital mechanics demo showing practical Runge–Kutta integration patterns.

## What this demonstrates

- **Numerical methods:** classic fixed-step RK4 and adaptive RK45-style stepping (Dormand–Prince 5(4)).
- **Physics modeling:** two-body orbital dynamics with optional Earth J2 perturbation.
- **Orbital analysis:** energy drift comparison and circular-orbit Hohmann transfer sizing.
- **Engineering clarity:** modular code, clear equations, light dependencies.

This is intended as a compact portfolio piece to discuss:

1. tradeoffs between fixed vs adaptive integration,
2. numerical stability and error control,
3. practical astrodynamics utility functions.

## Files

- `rk_integrators.py` - RK4 and adaptive RK45-style integrators
- `two_body.py` - two-body state derivatives and specific orbital energy
- `orbital_elements.py` - Cartesian state <-> classical orbital elements (COE)
- `hohmann.py` - two-impulse transfer delta-v and transfer time
- `demo.py` - runnable script producing diagnostics and an orbit plot
- `tests/test_basic.py` - lightweight sanity tests

## Quick start

```bash
cd Python/orbital-mechanics/turion_rk_demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python demo.py
```

Run tests:

```bash
pytest -q
```

## Expected demo output

- Orbital period estimate
- Energy drift stats for RK4 and adaptive RK
- Hohmann transfer delta-v and transfer time
- A generated plot: `orbit_demo.png`

## Units

Unless noted otherwise:

- distance: **km**
- time: **s**
- gravitational parameter \(\mu\): **km^3/s^2**
