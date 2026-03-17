# Gravitational Potential — Spherical Harmonics (SageMath)

Symbolic and numerical exploration of Earth's gravitational potential in the
spherical harmonics expansion, derived in `StormerRule.tex` (Propulsion repo,
Section 5). Companion to the LaTeX derivation on branch `feat/spherical-harmonics-j2`.

## Scripts

| Script | What it does |
|---|---|
| `01_legendre_polynomials.py` | Symbolic $P_n(x)$ for $n=0..6$, $P_{nm}(\cos\theta)$ for key $(n,m)$ pairs, orthogonality verification, plots |
| `02_gravitational_potential_symbolic.py` | Full symbolic $V$ through $J_3$, Cartesian form, gradient → $J_2$ acceleration |
| `03_transformation_matrix.py` | Transformation matrix $R(\theta,\phi)$, verify $R^TR=I$, gradient transform |
| `04_j2_numerical.py` | Numerical $J_2$ at ISS-like orbit, perturbation magnitude vs monopole, grid scan |
| `05_spherical_harmonics_visualization.py` | $Y_{lm}$ normalization checks, real harmonic forms |

## How to Run

From `Deployments/DockerBuilds/Math/SageMath/`:

```bash
# Run any script via the cli service
docker compose run --rm -v /home/propdev/.openclaw/workspace/repos/Monoclaw/Python/SageMath/GravitationalPotential:/work --entrypoint "" cli sage /work/01_legendre_polynomials.py

# Or drop into IPython and import manually
make python
# In [1]: exec(open('/path/to/script.py').read())
```

Or from this directory directly:
```bash
SCRIPTS_DIR=$(pwd)
docker run --rm -v "$SCRIPTS_DIR:/work" sagemath/sagemath:latest sage /work/01_legendre_polynomials.py
```

## Physics Background

All derivations reference `documents/StormerRule.tex` in the Propulsion repo:
- Coordinate conventions: §5.1
- Transformation matrix $R$: §5.2
- Multipole expansion: §5.3
- Legendre polynomials: §5.4
- Explicit terms through $J_3$: §5.5
- Gradient and acceleration: §5.6
