# Turion Final Interview — Night-Before Packet (1 page)

## 1) 60-second opening (say this first)
I’m a C++/Python engineer with strong numerical methods and astrodynamics focus. I’ve built and worked with Runge–Kutta ODE tooling (fixed and adaptive), and I care about correctness, testability, and production reliability. For this role, I’m particularly excited about implementing C++ library features with Python bindings, improving validation and CI, and helping ship tools that mission operators can trust under real constraints.

---

## 2) Top 10 technical questions to expect (with tight answer direction)

1. **Why adaptive RK vs fixed RK4 for orbit propagation?**  
   Adaptive RK controls local truncation error and step size, giving better accuracy/runtime tradeoff across varying dynamics.

2. **How do you validate an orbit propagator?**  
   Conservation checks (energy/angular momentum in 2-body), analytical baselines (Keplerian period), regression tests, tolerances, and known scenarios.

3. **How would you add J2 perturbation safely?**  
   Add force model as modular term, unit-test acceleration expression, compare RAAN/arg-perigee drift trends vs reference cases.

4. **How do you expose C++ to Python?**  
   pybind11 bindings, narrow stable API surface, convert Eigen/std::vector carefully, release GIL for heavy loops if safe.

5. **C++17/20 features you’d use here?**  
   `std::optional`, structured bindings, `constexpr`, `std::span`-style interfaces, concepts/static assertions where useful.

6. **Modern CMake essentials?**  
   Target-based CMake (`target_link_libraries`, `target_compile_features`), interface/public/private usage, reproducible toolchain settings.

7. **How do you handle numerical instability?**  
   Scale states, robust tolerances, monitor error estimators, detect step rejections, and add fail-fast diagnostics.

8. **How do you design tests for numerical code?**  
   Property/sanity tests, invariant checks, benchmark snapshots, and tolerance windows (not exact equality).

9. **How do you improve CI/CD for this stack?**  
   Matrix builds (compiler/Python versions), fast unit tests first, heavier numerical integration tests gated/nightly, artifacted plots/logs.

10. **How do you debug bad ephemeris output?**  
   Reproduce minimal case, inspect force-model toggles, compare integrator states/step sizes, isolate frame/unit mismatches first.

---

## 3) Behavioral signals they likely care about
- Can you work with leads and convert feedback into issues and shipped code?
- Can you explain tradeoffs clearly without ego?
- Do you document and test before claiming “done”?
- Are you practical under mission constraints ("make things that work")?

---

## 4) Your “ask them” short list
1. What are the highest-priority reliability pain points in the Tychee pipeline today?  
2. Where do C++ and Python boundaries currently create friction?  
3. What does “great first 90 days” look like for this role?  
4. Which force models and validation references are considered source-of-truth internally?  
5. How do you currently stage numerical changes to production confidence?

---

## 5) Day-of checklist (10 min)
- Confirm your 90-second intro once out loud
- Rehearse RK4 vs adaptive RK in 2 sentences
- Rehearse validation strategy (invariants + regression + references)
- Rehearse one collaboration story (lead feedback -> shipped improvement)
- Open demo repo path + run command ready

---

## 6) Quick commands (if asked to show work)
```bash
cd ~/.openclaw/workspace/repos/Monoclaw/Python/orbital-mechanics/turion_rk_demo
python3 demo.py
```

Expected: prints propagation/energy stats + Hohmann transfer outputs + saves `orbit_demo.png`.
