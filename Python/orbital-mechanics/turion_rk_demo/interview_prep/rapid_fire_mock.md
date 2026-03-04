# Turion Final — Rapid-Fire Mock (20 minutes)

Use this solo or with a friend. 60–90 sec per answer.

## Round A — Core Technical (10)

1. Explain the difference between RK4 and adaptive RK45 in mission terms.
2. Why can tight tolerances still produce wrong trajectories?
3. How would you structure a force-model pipeline for extensibility?
4. What invariants do you track in a 2-body validation test?
5. How do you detect a units/frame bug quickly?
6. How do you expose a C++ propagator to Python without performance death?
7. Show a clean CMake target structure for core lib + bindings + tests.
8. How do you choose between fixed-step and adaptive integration in production?
9. What should a CI gate include for numerical software?
10. How do you make numerical code reviewable for non-specialists?

## Round B — Astrodynamics/GNC (8)

11. State vector vs COE: when do you use each?
12. What does J2 physically do to an orbit over time?
13. Explain Hohmann transfer assumptions and failure cases.
14. How would you validate RAAN drift against expectation?
15. If a target capture window is missed, what software knobs do you inspect first?
16. How does attitude constraint coupling affect orbit-level mission planning?
17. What telemetry would you log from an onboard propagator?
18. How would you set up a Monte Carlo campaign for uncertainty analysis?

## Round C — Behavioral/Execution (6)

19. Describe a time feedback changed your technical approach.
20. A lead asks for speed, QA asks for more validation. What do you do?
21. How do you document assumptions so ops can trust your output?
22. You find a bug the day before milestone demo—what’s your plan?
23. How do you de-risk adding a new force model?
24. What does “make things that work” mean in your day-to-day coding?

---

## 30-second closer
"I focus on shipping reliable numerical software: clear assumptions, validated models, and testable interfaces. I can contribute across C++ core, Python bindings, and CI so the team can iterate fast without sacrificing trust in the outputs."
