# Turion Space — Final Interview Prep Pack (Python/C++ Developer)

Candidate: **Ernest Yeung**  
Interview length: **~1 hour**  
Focus: **Python/C++, numerical methods, orbital mechanics, software quality, collaboration**

> Assumptions used here are intentionally public/plausible only: Turion Space works on spacecraft/software for space domain awareness and on-orbit operations, where correctness, reliability, and rapid iteration both matter.

---

## 1) 90-second pitch (tailored)

I’m a Python/C++ engineer focused on numerical software for orbital mechanics. I build tools that are fast enough for real workloads, but also testable and maintainable by a team under mission pressure.

My core strength is bridging **algorithmic correctness** and **production engineering**: implementing integrators and astrodynamics utilities in C++ for performance, then exposing clean Python interfaces for analysis, experimentation, and ops workflows. I’m comfortable with C++17/20, modern CMake, pybind11-style bindings, and CI pipelines that enforce reliability through unit tests, property checks, and regression baselines.

For orbit propagation, I think in terms of error budgets and operational constraints: pick the simplest model that meets accuracy needs, validate against known invariants and reference cases, and make behavior observable with clear metrics. I bias toward designs that scale from “research notebook” to “service in production” without rewriting everything.

What I’d bring to Turion is practical execution: shipping robust flight-dynamics-adjacent software, communicating tradeoffs clearly, and collaborating tightly across software, mission, and operations teams so we can move fast without compromising correctness.

---

## 2) 20 likely technical questions + strong concise answers

### C++17/20 + software design

1. **Q: Why C++ for orbital propagation, and where does Python fit?**  
   **A:** C++ gives deterministic performance and control over memory/layout for heavy numerics; Python is ideal for orchestration, analysis, and quick iteration. I keep the numeric kernels in C++ and provide Python bindings for productivity.

2. **Q: C++17/20 features you’d actually use here?**  
   **A:** `std::optional`/`std::variant` for explicit interfaces, structured bindings, `if constexpr` for compile-time selection, `std::span` for non-owning views, concepts (C++20) for template constraints, and ranges where they improve clarity without hidden overhead.

3. **Q: How do you avoid over-templating numeric code?**  
   **A:** Template only where it materially improves performance/reuse (e.g., scalar type, fixed-size vectors). Keep public APIs concrete and readable. Measure before generalizing.

4. **Q: Memory/performance pitfalls in vector-heavy code?**  
   **A:** Excess allocations, poor data locality, and accidental copies. I use preallocation, pass-by-reference/`span`, small fixed-size types for state vectors, and profiling to confirm hotspots.

5. **Q: Error handling strategy? Exceptions or status codes?**  
   **A:** Programmer errors: assertions/contracts. Recoverable runtime issues: explicit status/result types at boundaries. I avoid exception-heavy control flow in tight numeric loops.

### CMake/build/tooling

6. **Q: How would you structure CMake for a C++ core + Python module?**  
   **A:** Separate targets: `liborbit_core` (C++), `orbit_py` (bindings), `orbit_tests`. Use target-based includes/defs, exported compile features, and install rules. Keep transitive deps explicit.

7. **Q: How do you keep builds reproducible across dev/CI?**  
   **A:** Pin compiler/container versions in CI, lock dependency versions, use presets/toolchains, and run the same configure/test commands locally and in CI.

8. **Q: Static vs shared libs choice?**  
   **A:** Default to shared for Python extension interoperability and smaller rebuild impact; static can be useful for standalone tools. Decide per deployment target.

### Python bindings/interoperability

9. **Q: pybind11 best practices for numeric arrays?**  
   **A:** Accept NumPy arrays with dtype/contiguity checks, avoid copies where safe, document ownership/lifetime, and expose vectorized-friendly APIs instead of per-element calls.

10. **Q: How do you handle GIL with C++ compute kernels?**  
   **A:** Release GIL during long-running pure C++ computation (`gil_scoped_release` pattern), reacquire only when interacting with Python objects.

11. **Q: What causes segfaults in bindings, and how do you prevent them?**  
   **A:** Lifetime mismatches and invalid buffer assumptions. I enforce clear ownership, validate shapes/strides, and use sanitizers plus binding-focused tests.

### RK methods / numerics

12. **Q: RK4 vs adaptive RK45—when use which?**  
   **A:** RK4 for fixed-step deterministic workloads with predictable cost; RK45 for variable dynamics where error control matters more than uniform step spacing.

13. **Q: How do you choose timestep for LEO propagation?**  
   **A:** Start from required position/velocity error bounds over horizon, run convergence tests halving step size, and pick the coarsest step meeting tolerance with margin.

14. **Q: How do you verify an integrator implementation quickly?**  
   **A:** Compare against analytical two-body cases (where applicable), verify conservation behavior (energy/angular momentum trends), and cross-check with a trusted reference propagator.

15. **Q: What’s local truncation error vs global error?**  
   **A:** Local truncation error is per-step method error; global error accumulates over many steps and is typically one order lower in step size than local behavior for fixed-step methods.

16. **Q: Signs your propagation is numerically unstable?**  
   **A:** Nonphysical drift beyond expected model error, sensitivity explosions to small step changes, and failure of invariants in simplified scenarios.

### Astrodynamics domain

17. **Q: ECI vs ECEF handling in pipeline?**  
   **A:** Keep a canonical internal frame (usually inertial) and isolate frame transforms at interfaces. Test transforms with known epochs/vectors and document time standards (UTC/TT/etc.).

18. **Q: What perturbations matter first beyond two-body?**  
   **A:** Typically J2 first, then drag/SRP/third-body depending on altitude, area-to-mass, and mission horizon. Add complexity incrementally against requirements.

19. **Q: How do you communicate model fidelity to non-specialists?**  
   **A:** Tie model choices to operational outcomes: “This adds X compute cost and reduces along-track error by Y over Z hours.”

### Testing/CI/reliability

20. **Q: What does a solid CI gate for this code look like?**  
   **A:** Fast unit tests on every PR, numerical regression suite with tolerances, sanitizer builds (ASan/UBSan), lint/format checks, and at least one release-like build artifact validation.

---

## 3) 8 behavioral/collaboration questions with STAR bullet answers

1. **Tell me about a time you debugged a hard numerical bug.**  
   - **S:** Propagation output diverged from expected orbit over long horizon.  
   - **T:** Identify whether issue was model, integrator, or implementation bug.  
   - **A:** Built minimal repro, added invariant checks, bisected changes, compared against reference solver.  
   - **R:** Found frame-conversion mismatch at interface; fixed and added regression tests to prevent recurrence.

2. **Describe a tradeoff between speed and accuracy you made.**  
   - **S:** Needed near-real-time propagation for batch scenarios.  
   - **T:** Meet latency target without breaking mission-level error bounds.  
   - **A:** Benchmarked fixed-step RK4 vs adaptive scheme; tuned step size per use case; introduced configurable fidelity modes.  
   - **R:** Hit throughput target while staying within agreed error envelope.

3. **Example of cross-functional collaboration.**  
   - **S:** Software, mission analysis, and ops had conflicting priorities.  
   - **T:** Deliver one interface serving all three workflows.  
   - **A:** Ran short requirement sessions, defined shared input/output contract, added examples for each team.  
   - **R:** Reduced back-and-forth and enabled faster adoption.

4. **A time you improved code quality under deadline.**  
   - **S:** Delivery window was tight and test coverage was weak.  
   - **T:** Ship safely without blocking timeline.  
   - **A:** Added highest-risk tests first, set CI blockers only on critical checks, queued follow-up hardening tasks.  
   - **R:** On-time delivery with no critical post-release defects.

5. **How you handled disagreement on technical approach.**  
   - **S:** Team split on architecture for simulation pipeline.  
   - **T:** Reach decision quickly and objectively.  
   - **A:** Proposed evaluation criteria (latency, maintainability, testability), built spike prototypes, reviewed data together.  
   - **R:** Team aligned on evidence-backed choice; fewer subjective debates later.

6. **A failure and what you changed after.**  
   - **S:** Underestimated integration complexity for bindings release.  
   - **T:** Recover schedule and prevent repeat.  
   - **A:** Broke work into smaller milestones, added packaging checks to CI, improved release checklist.  
   - **R:** Subsequent releases were predictable and lower-stress.

7. **How you onboard to a new domain quickly.**  
   - **S:** Needed to contribute to unfamiliar astrodynamics module.  
   - **T:** Become productive within first sprint.  
   - **A:** Started with glossary + architecture map, reproduced key tests locally, paired with domain expert on first PRs.  
   - **R:** Shipped meaningful improvements early while building domain confidence.

8. **Handling ambiguity in requirements.**  
   - **S:** Requirement was “make propagation more reliable” without metrics.  
   - **T:** Convert ambiguity into executable plan.  
   - **A:** Defined measurable SLOs (error tolerance, runtime, failure rate), got stakeholder signoff, then implemented to those targets.  
   - **R:** Clear acceptance criteria and smoother review cycle.

---

## 4) Five high-signal “ask them” questions (systems thinking)

1. **Model fidelity roadmap:** How do you currently tier propagation fidelity (two-body/J2/drag/etc.) across mission phases, and where are the biggest accuracy pain points today?
2. **Operational feedback loop:** What telemetry or ops outcomes feed back into model/integration improvements, and how quickly can that loop close?
3. **Verification philosophy:** What’s your current strategy for truth data / reference comparisons and acceptance tolerances before software is trusted in operations?
4. **Architecture boundaries:** Where do you draw the boundary between high-performance core code and Python workflow glue, and what has worked/not worked so far?
5. **Team interface:** How do software, mission analysis, and operators coordinate during time-critical events when assumptions in the model are challenged?

---

## 5) Red flags / what to avoid in the interview

- Don’t imply “more complex physics is always better.” Emphasize requirement-driven fidelity.
- Don’t hand-wave coordinate frames/time standards; small mistakes there are mission-critical.
- Don’t present Python vs C++ as either/or; show layered architecture thinking.
- Don’t claim accuracy without validation method and test evidence.
- Don’t overfocus on clever algorithms while ignoring observability, CI, and maintainability.
- Don’t trash past teams/tools; frame tradeoffs constructively.
- Don’t answer behavioral questions abstractly—give concrete actions and outcomes.
- Don’t ask only perks/culture questions; include technical + operational system questions.

---

## 6) One-page day-of cram checklist

## A) 20-minute technical refresh
- Rehearse RK4 vs RK45 explanation (when and why).
- Rehearse error-control language: tolerance, convergence test, regression baseline.
- Review frame/time fundamentals: ECI/ECEF, epoch handling, transform boundaries.
- Refresh C++ talking points: memory layout, copies vs views, API clarity.
- Refresh pybind11 talking points: ownership, dtype/shape checks, GIL release.

## B) 15-minute story prep (STAR)
- Pick 3 strongest stories:
  1) numerical bug root-cause,
  2) cross-functional delivery,
  3) speed-vs-accuracy tradeoff.
- For each: one-sentence **Situation**, **Task**, **Action**, measurable **Result**.
- Prepare one “failure + lesson learned” story with concrete process improvement.

## C) 10-minute Turion alignment prep
- Why Turion: mission impact + software rigor in real operations.
- What you bring: C++/Python bridge, numerical reliability mindset, fast execution.
- One sentence on working style: data-driven, collaborative, low-ego debugging.

## D) 10-minute Q&A readiness
- Memorize 5 “ask them” questions above.
- Prepare concise compensation/logistics fallback if asked.
- Have a clear close: enthusiasm + fit + readiness to execute.

## E) 5-minute interview hygiene
- Confirm environment (audio/video, notes, repo/examples if needed).
- Keep answers concise: 60–120 seconds unless they ask for depth.
- Think out loud on tradeoffs, then state a recommendation.
- If unsure, say assumptions explicitly and proceed methodically.

## Final mental model
**Correctness first, then performance, then ergonomics—while keeping all three visible.**
That framing maps well to mission-critical engineering teams.
