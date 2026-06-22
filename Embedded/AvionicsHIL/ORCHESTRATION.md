# AvionicsHIL — Orchestration

How the work is decomposed, the order to build it, and what can run in parallel. This mirrors
the orchestration pattern used in the ROSA project (`repos/rosa/ORCHESTRATION.md`).

---

## Task dependency graph

```
        ┌──────────────────────────────────────────────┐
        │ TASK-01  Jetson I²C/UART bring-up & checkout   │  (Act 1)
        │ TASK-02  BBB EGSE: sensor source + bridges     │  (Act 3 infra)
        └───────────────┬──────────────┬────────────────┘
                        │              │   (01 and 02 are INDEPENDENT — build in parallel)
                        ▼              ▼
              ┌─────────────────────────────────┐
              │ TASK-03  Jetson FSW + HIL close  │  (Act 3)  needs 01 (transport) + 02 (frames)
              └───────────────┬─────────────────┘
                              ├───────────────► TASK-04  Analog front-end (Act 2)   [needs 01; otherwise independent]
                              ├───────────────► TASK-05  Fault injection (Act 4)     [needs 02 + 03]
                              └───────────────► TASK-06  CI + Test Readiness Review   [needs 03; absorbs 04/05 as they land]
```

## Build order (recommended)

1. **Vertical slice (proves the concept):** TASK-01 + TASK-02 (parallel) → TASK-03.
   Outcome: a Starship landing in Isaac, flown by FSW on the Jetson, with sensors faked by the
   BBB. This alone is a complete, demoable story.
2. **TASK-05 (fault injection)** — the showstopper "the agent fixed it live" beat; small delta over TASK-02/03.
3. **TASK-04 (analog front-end)** — the unique differentiator (LLM designs a real circuit from
   Art of Electronics, parts from the vision-scanned bin).
4. **TASK-06 (CI + report)** — wraps everything into a Test Readiness Review artifact.

## Parallelization notes

- **TASK-01 and TASK-02 share no code** and run against [INTERFACES.md](INTERFACES.md). Two
  agents/sessions can take them simultaneously. Each touches a different board.
- **TASK-03** is the integration point; it should not start until the sensor frame format is
  settled (it is, in INTERFACES §3) — but coding the FSW control law and frame parsing can begin
  against the spec before the BBB is physically ready, using a recorded/synthetic frame stream.
- **TASK-04** is mostly desk work (circuit design from the textbook + inventory) plus a small
  bench build; it can proceed any time after TASK-01 establishes a sensor input path.

## Definition of "vertical slice complete"

- Jetson UART (or I²C) interface enumerated and checked out (TASK-01 acceptance).
- BBB streams valid 32-byte sensor frames derived from live Isaac telemetry (TASK-02 acceptance).
- Jetson FSW closes the loop: reads frames, runs the landing law, commands Isaac via the BBB,
  and the simulated vehicle achieves a soft touchdown (`|vz| < 2 m/s`) (TASK-03 acceptance).
- A first `reports/trr.json` exists with at least the bring-up + landing tests.

## Handoff protocol (because the model will change mid-project)

Every session, on finishing a unit of work:
1. Update **STATUS.md**: task state, any `VERIFY` answers discovered, new follow-ups.
2. If you changed a contract, update **INTERFACES.md** in the same commit.
3. Leave the working tree on a `feat/avionics-hil-*` branch; do not merge to main.
4. Write enough in STATUS.md that the next session needs only README → STATUS → its task brief.

## Suggested agent assignment (if running a fleet)

| Agent/session | Owns | Board it touches |
|---------------|------|------------------|
| A | TASK-01 (bring-up/checkout) | Jetson |
| B | TASK-02 (EGSE) | BeagleBone Black |
| A or C | TASK-03 (FSW + integration) | Jetson + bench |
| B or C | TASK-05 (fault injection) | BBB |
| any | TASK-04 (analog) | breadboard |
| any | TASK-06 (CI/report) | host |
