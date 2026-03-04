# Turion Final — 5 Likely Whiteboard Problems (with answer outlines)

## 1) Two-body propagator step function
**Prompt:** Given state `[r,v]`, write one integrator step for `dr/dt=v`, `dv/dt=-mu*r/|r|^3`.

**What they want:** clean math -> clean code mapping, units discipline.

**Strong outline:**
- Define derivative function `f(t, y)` where `y=[rx,ry,rz,vx,vy,vz]`
- Compute `r_norm = sqrt(rx^2+ry^2+rz^2)`
- `a = -mu * r / r_norm^3`
- Return `[vx,vy,vz,ax,ay,az]`
- Mention SI vs km units consistency

---

## 2) RK4 vs adaptive RK45 choice
**Prompt:** For onboard/ground propagation, when would you use RK4 vs adaptive RK45?

**Strong outline:**
- RK4: deterministic step count, simple, good for fixed-rate loops
- Adaptive RK45: better error control and efficiency on variable dynamics
- Tradeoff: adaptive has control logic complexity, possible nondeterminism in step counts
- Practical decision: fixed-rate onboard control loops may favor fixed step; planning/analysis usually adaptive

---

## 3) Add J2 perturbation
**Prompt:** Extend 2-body acceleration with J2.

**Strong outline:**
- Keep force model modular (`a_total = a_2body + a_J2 + ...`)
- J2 acceleration terms depend on Earth radius, J2, and z/r ratio
- Validate by checking secular trends (e.g., RAAN precession sign/magnitude direction)
- Unit test J2 can be toggled on/off and compared against 2-body baseline

---

## 4) Design Python bindings for a C++ propagator
**Prompt:** You have a C++ astrodynamics kernel; expose it to Python users.

**Strong outline:**
- Use pybind11 for thin bindings
- Keep core numerics in C++, orchestration in Python
- Define stable typed interfaces: vectors/matrices + config structs
- Add docstrings and input validation at boundary
- Release GIL during long propagation loops if thread-safe
- Mirror tests: same scenario in C++ and Python wrapper

---

## 5) Validation plan for mission-critical numerics
**Prompt:** How do you prove propagator changes are safe?

**Strong outline:**
- Layered tests:
  1) unit tests for force model math
  2) invariant checks (energy/angular momentum under 2-body)
  3) reference trajectory regression tests
  4) tolerance-based CI gates
- Compare against known analytical/simplified cases first
- Add runtime telemetry diagnostics (step size, reject count, error estimates)
- Ship behind feature flag for shadow runs before full adoption

---

## 30-second answer style template
1. Clarify assumptions
2. Give concise model/equation
3. Show implementation structure
4. Explain validation and failure modes
5. End with tradeoff rationale
