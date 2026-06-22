# TASK-05 — Fault injection & autonomous diagnosis (Act 4, the showstopper)

> Self-contained brief. Read [../AGENTS.md](../AGENTS.md), [../INTERFACES.md](../INTERFACES.md) first.

## Objective
Make the EGSE inject sensor faults on command, verify the FSW detects/handles each correctly, and
demonstrate the agent **autonomously diagnosing and fixing** an induced failure — live.

## Why it matters (SpaceX mapping)
"Drive product reliability and yield" = fault campaigns. The "agent fixed it while you watched"
moment is the most memorable beat of the whole demo and the strongest autonomy proof.

## Dependencies
- TASK-02 (EGSE with the inert fault hook) and TASK-03 (FSW + closed loop) complete.

## Inputs
- Fault codes + frame semantics: [../INTERFACES.md](../INTERFACES.md) §6 (and §3 `status`/`fault_code`).

## Deliverables
- `bbb/egse/fault_injector.py` — implement the §6 faults; controllable at runtime (CLI/HTTP/file flag). Sets `status.fault_active` + `fault_code` so the harness has ground truth.
- `jetson/fsw/` fault handling — FSW must detect/handle each fault (reject + hold-last, safe-state, or abort) without crashing or commanding a crash.
- `tests/fault_campaign.py` (host) — for each fault: command it, observe FSW response, assert the correct behavior; record results.
- `reports/fault_campaign.json` — per-fault verdicts.
- `analog/` or `docs/` writeup of one **autonomous diagnosis** episode (the showstopper script).

## Steps
1. Implement faults per INTERFACES §6: STUCK, NAN_ALT, DROPOUT, BITFLIP, OUT_OF_RANGE, NOISE.
2. Define + implement FSW responses (e.g., NAN/OUT_OF_RANGE → reject + hold-last; DROPOUT → safe-state after T ms; BITFLIP → plausibility/rate check; NOISE → filter or flag).
3. `fault_campaign.py`: iterate faults during a descent; assert the FSW keeps the vehicle safe (no crash, no runaway) and flags the fault. Record PASS/FAIL each.
4. **Scripted autonomous-diagnosis demo:** intentionally leave one bug (or inject a fault the FSW does *not* yet handle). Have the agent read the FSW logs + telemetry, cross-reference INTERFACES/HARDWARE/pinmux, form a hypothesis, apply a fix, and re-run to green — capturing the transcript as the showstopper artifact.
5. Update STATUS.md.

## Acceptance criteria
- All six faults injectable at runtime and observable via `status`/`fault_code`.
- FSW survives every fault (no crash; vehicle never commanded into the ground by a bad reading).
- `reports/fault_campaign.json` records a verdict per fault.
- One documented end-to-end autonomous diagnose-and-fix episode.

## Definition of done
Acceptance met; STATUS.md updated; the diagnosis episode transcript saved for the demo narrative.
