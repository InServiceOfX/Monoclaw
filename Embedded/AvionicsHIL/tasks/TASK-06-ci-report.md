# TASK-06 — CI/CD + Test Readiness Review report (Act 5)

> Self-contained brief. Read [../AGENTS.md](../AGENTS.md), [../INTERFACES.md](../INTERFACES.md) first.

## Objective
Wrap the bring-up, HIL, analog, and fault tests into a repeatable pipeline that emits a single
**Test Readiness Review (TRR)** artifact — every test traced to a requirement, pass/fail, with evidence.

## Why it matters (SpaceX mapping)
"Test execution across multiple environments" + "analyze complex test data," delivered with the
artifact discipline real avionics test orgs require (traceability, repeatability, sign-off).

## Dependencies
- TASK-03 (HIL loop) at minimum. Absorbs TASK-01/04/05 outputs as they land.

## Inputs
- Report schema: [../INTERFACES.md](../INTERFACES.md) §9.
- Per-act reports already produced: `reports/checkout_jetson.json`, `reports/hil_run.json`, `reports/analog_check.json`, `reports/fault_campaign.json`.

## Deliverables
- `ci/run_all.sh` (or a Python runner) — boots Isaac (physics-only), starts the BBB EGSE, runs the FSW, executes bring-up → HIL → fault campaign → analog check, collects every per-act report.
- `ci/build_trr.py` — merges per-act reports into `reports/trr.json` (INTERFACES §9) + renders `reports/trr.md` (human-readable, requirement-traced table).
- `.github/workflows/` or a documented local CI entry (note: hardware-in-the-loop steps need the bench; gate those behind a `--with-hardware` flag and run pure-sim/unit parts in CI).
- `reports/trr.md` — the demo's closing artifact.

## Steps
1. `run_all.sh`: orchestrate boot → tests → collect, honoring the Isaac runtime gotchas (no runtime `/scene/load`; physics-only kit; GPU 1). Make hardware-dependent steps opt-in.
2. `build_trr.py`: assign each check a requirement id; merge into `trr.json`; render `trr.md` with a PASS/FAIL summary + measured loop rate/latency + fault-campaign matrix.
3. Make it idempotent and re-runnable; stamp `run_id` + `git_sha`.
4. Split CI: unit/sim parts (frame round-trips, control-law-in-sim, report build) run anywhere; HIL parts require `--with-hardware`.
5. Update STATUS.md.

## Acceptance criteria
- One command produces `reports/trr.json` + `reports/trr.md`.
- Every test traces to a requirement id; summary counts are correct.
- Sim/unit portion runs without hardware; HIL portion documented + gated.

## Definition of done
Acceptance met; STATUS.md updated; `reports/trr.md` is presentable as the demo's verification sign-off.
