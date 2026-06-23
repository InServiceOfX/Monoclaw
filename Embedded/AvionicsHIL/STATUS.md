# AvionicsHIL — STATUS (living board)

**Update this file whenever you finish a unit of work or learn a `VERIFY` answer.**
This is the first thing the next session reads after README.

Last updated: 2026-06-23 — by: Cyclonus / Codex — confirmed Jetson SSH over USB-C network, wired Ethernet, and Wi-Fi.

---

## Task board

| Task | Act | State | Owner / session | Notes |
|------|-----|-------|-----------------|-------|
| Act 0 — knowledge ingestion | 0 | ✅ DONE | (prior sessions) | pinmux CSVs, BBB SRM, AoE resolved.md, inventory.json all exist |
| [TASK-01](tasks/TASK-01-jetson-i2c-bringup.md) Jetson bring-up & checkout | 1 | 🟡 IN PROGRESS | claude-sonnet-4-6 / 2026-06-22 | scripts written; needs hardware to confirm /dev names + run loopback |
| [TASK-02](tasks/TASK-02-bbb-egse.md) BBB EGSE | 3 | 🟡 IN PROGRESS | claude-sonnet-4-6 / 2026-06-22 | all Python written + frames.py self-test passes; needs hardware for UART VERIFY |
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
| Jetson 40-pin UART `/dev/ttyTHS?` | HARDWARE §2 | `/dev/ttyTHS1` | claude-sonnet-4-6 / 2026-06-22 (check_interfaces.py PASS; pinmux CSV confirms UART1=pins 8/10) |
| Jetson 40-pin I²C `/dev/i2c-?` | HARDWARE §2 | `/dev/i2c-7` (`c250000.i2c`) | claude-sonnet-4-6 / 2026-06-22 (i2cdetect -l; not yet tested — UART transport selected) |
| BBB UART2 device + overlay enable | HARDWARE §3 | _TBD_ | — |
| BBB I²C-slave (`i2c-slave-eeprom`) supported? | INTERFACES §5 | _TBD_ | — |
| Desktop LAN IP for Isaac `:8282` | INTERFACES §7 | `192.168.86.91` (config.yaml default; verify Isaac is running) | — |
| BBB LAN IP | — | _TBD_ | — |
| Isaac continuous-throttle command route exists? | INTERFACES §7 | _TBD_ | — |
| Jetson USB-C network SSH | bringup README | `orin@192.168.55.1` (`l4tbr0`) | Cyclonus / 2026-06-23 |
| Jetson wired Ethernet SSH | bringup README | `orin@192.168.86.34` (`enP8p1s0`) | Cyclonus / 2026-06-23 |
| Jetson Wi-Fi SSH | bringup README | `orin@192.168.86.32` (`wlP1p1s0`, Jajsemtady 3) | Cyclonus / 2026-06-23 |

## Decisions log

- 2026-06-22: **Default sensor+command transport = UART** (guaranteed). I²C-slave is a
  verification-gated upgrade (BBB AM335x slave support uncertain). See INTERFACES §5.
- 2026-06-22: **Coordinate frame = Z-up**, reusing the existing Isaac stack.
- 2026-06-22: **Control law (MVP) = PD on vertical velocity** targeting soft touchdown.

## Changelog

- 2026-06-22 — Project created. Wrote README, AGENTS, ARCHITECTURE, INTERFACES, HARDWARE,
  ORCHESTRATION, STATUS, and TASK-01..06 briefs. No code yet. Vertical slice = TASK-01+02+03.
- 2026-06-22 — Build session (claude-sonnet-4-6). Wrote:
  - `bbb/egse/`: frames.py (CRC+pack/unpack verified), sensor_model.py, truth_bridge.py,
    fault_injector.py (stub), sensor_source.py, actuator_sink.py, run_egse.py, README.md.
  - `jetson/bringup/`: check_interfaces.py, uart_loopback.py, README.md.
  - `config.yaml` (skeleton with VERIFY items).
  - Isaac: added `throttle` HTTP route to enable_ros2_bridge.py + `set_throttle_direct()`
    to StarshipController (unblocks TASK-03 HIL close-loop).
  - frames.py self-test passes on desktop (CRC=0x29B1 ✓, 32/16-byte round-trips ✓).
  - Next: SSH into Jetson → confirm /dev/ttyTHS* → run uart_loopback.py. Then BBB UART.
- 2026-06-22 — Reboot session (Cyclonus / Codex). Jetson confirmed reachable before reboot at
  `orin@192.168.55.1` over the USB-C network; hostname reported `nvdia-desktop`. Sent
  `sudo /sbin/reboot` successfully. After reboot, `192.168.86.30` answered ping but refused SSH,
  and the desktop USB-C network interface (`192.168.55.100`/`192.168.55.1`) did not reappear
  during the wait window. Next human-visible check: confirm Jetson power/display state, then retry
  SSH or reconnect USB-C.
- 2026-06-23 — Ernest manually selected primary kernel option `1` on reboot and reconnected
  DisplayPort. Rechecked SSH: USB-C network works at `orin@192.168.55.1`; wired Ethernet works at
  `orin@192.168.86.34`; Wi-Fi also works at `orin@192.168.86.32`. Hostname is `nvdia-desktop`.
  No `/dev/ttyACM*` or `/dev/ttyUSB*` raw serial console device was visible on the desktop.

## Next action for whoever picks this up

Start the vertical slice: take **TASK-01** (Jetson) and **TASK-02** (BBB) — they're independent.
If solo, do TASK-01 first (it unblocks the transport), then TASK-02, then TASK-03.
Begin by reading README → AGENTS → ARCHITECTURE → INTERFACES, then your task brief.
