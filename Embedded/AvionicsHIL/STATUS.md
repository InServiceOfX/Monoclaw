# AvionicsHIL — STATUS (living board)

**Update this file whenever you finish a unit of work or learn a `VERIFY` answer.**
This is the first thing the next session reads after README.

Last updated: 2026-06-22 — by: claude-opus-4-8 (planning session) — created the project + all docs/briefs.

---

## Task board

| Task | Act | State | Owner / session | Notes |
|------|-----|-------|-----------------|-------|
| Act 0 — knowledge ingestion | 0 | ✅ DONE | (prior sessions) | pinmux CSVs, BBB SRM, AoE resolved.md, inventory.json all exist |
| [TASK-01](tasks/TASK-01-jetson-i2c-bringup.md) Jetson bring-up & checkout | 1 | ⬜ NOT STARTED | — | start here (parallel w/ 02) |
| [TASK-02](tasks/TASK-02-bbb-egse.md) BBB EGSE | 3 | ⬜ NOT STARTED | — | start here (parallel w/ 01) |
| [TASK-03](tasks/TASK-03-jetson-fsw-hil.md) Jetson FSW + HIL close | 3 | ⬜ NOT STARTED | — | needs 01 + 02 |
| [TASK-04](tasks/TASK-04-analog-frontend.md) Analog front-end (AoE) | 2 | ⬜ NOT STARTED | — | needs 01 |
| [TASK-05](tasks/TASK-05-fault-injection.md) Fault injection | 4 | ⬜ NOT STARTED | — | needs 02 + 03 |
| [TASK-06](tasks/TASK-06-ci-report.md) CI + Test Readiness Review | 5 | ⬜ NOT STARTED | — | needs 03 |

States: ⬜ NOT STARTED · 🟡 IN PROGRESS · ✅ DONE · 🔴 BLOCKED

## VERIFY log (hardware facts to confirm, then record here)

These are unknowns the plan flagged. Fill in the real answer the moment you confirm it on hardware;
copy the confirmed values into `config.yaml`.

| Unknown | Where | Confirmed value | Confirmed by/date |
|---------|-------|-----------------|-------------------|
| Jetson 40-pin UART `/dev/ttyTHS?` | HARDWARE §2 | _TBD_ | — |
| Jetson 40-pin I²C `/dev/i2c-?` | HARDWARE §2 | _TBD_ | — |
| BBB UART2 device + overlay enable | HARDWARE §3 | _TBD_ | — |
| BBB I²C-slave (`i2c-slave-eeprom`) supported? | INTERFACES §5 | _TBD_ | — |
| Desktop LAN IP for Isaac `:8282` | INTERFACES §7 | _TBD_ (memory says 192.168.86.91) | — |
| BBB LAN IP | — | _TBD_ | — |
| Isaac continuous-throttle command route exists? | INTERFACES §7 | _TBD_ | — |

## Decisions log

- 2026-06-22: **Default sensor+command transport = UART** (guaranteed). I²C-slave is a
  verification-gated upgrade (BBB AM335x slave support uncertain). See INTERFACES §5.
- 2026-06-22: **Coordinate frame = Z-up**, reusing the existing Isaac stack.
- 2026-06-22: **Control law (MVP) = PD on vertical velocity** targeting soft touchdown.

## Changelog

- 2026-06-22 — Project created. Wrote README, AGENTS, ARCHITECTURE, INTERFACES, HARDWARE,
  ORCHESTRATION, STATUS, and TASK-01..06 briefs. No code yet. Vertical slice = TASK-01+02+03.

## Next action for whoever picks this up

Start the vertical slice: take **TASK-01** (Jetson) and **TASK-02** (BBB) — they're independent.
If solo, do TASK-01 first (it unblocks the transport), then TASK-02, then TASK-03.
Begin by reading README → AGENTS → ARCHITECTURE → INTERFACES, then your task brief.
