# AvionicsHIL — STATUS (living board)

**Update this file whenever you finish a unit of work or learn a `VERIFY` answer.**
This is the first thing the next session reads after README.

Last updated: 2026-06-23 — by: claude-sonnet-4-6 — BBB EGSE running, cross-board UART link BLOCKED on physical wiring (open circuit).

---

## Task board

| Task | Act | State | Owner / session | Notes |
|------|-----|-------|-----------------|-------|
| Act 0 — knowledge ingestion | 0 | ✅ DONE | (prior sessions) | pinmux CSVs, BBB SRM, AoE resolved.md, inventory.json all exist |
| [TASK-01](tasks/TASK-01-jetson-i2c-bringup.md) Jetson bring-up & checkout | 1 | 🟡 IN PROGRESS | claude-sonnet-4-6 / 2026-06-23 | /dev/ttyTHS1 confirmed; pin orientation confirmed; hardware path proven (break test); UART-LINK SKIPPED (cross-board wiring open circuit) |
| [TASK-02](tasks/TASK-02-bbb-egse.md) BBB EGSE | 3 | 🔴 BLOCKED | claude-sonnet-4-6 / 2026-06-23 | EGSE running at 50 Hz (tx>2000), frames.py PASS, /dev/ttyS2 confirmed; blocked on physical wiring open circuit |
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
| BBB UART2 device + overlay enable | HARDWARE §3 | `/dev/ttyS2` (MMIO 0x48024000); enable: `config-pin P9.21 uart && config-pin P9.22 uart` (must re-run each boot — not persistent) | claude-sonnet-4-6 / 2026-06-23 (dmesg confirmed) |
| BBB I²C-slave (`i2c-slave-eeprom`) supported? | INTERFACES §5 | _TBD_ (deferred — UART transport selected first) | — |
| Desktop LAN IP for Isaac `:8282` | INTERFACES §7 | `192.168.86.91` (eno1 wired) | claude-sonnet-4-6 / 2026-06-23 (`ip addr` confirmed) |
| BBB LAN IP | — | USB gadget only: `192.168.7.2`; real eth0 DOWN (no Ethernet cable available) | claude-sonnet-4-6 / 2026-06-23 |
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
- 2026-06-23 — Hardware bring-up session (claude-sonnet-4-6 + Ernest):
  - **Jetson 40-pin header orientation CONFIRMED** by multimeter: even pins = INNER column,
    top = USB-C end. Pin 2=5V, 4=5V, 6=0V(GND), 8=3.36V(UART TX idle), 10=0.138V(TXB0108 pull-down).
  - **TXB0108 level translator** on Jetson carrier confirmed: handles UART direction automatically;
    self-loopback test inconclusive by design (expected artifact). Break test proved TX live.
  - **BBB kernel** 5.10.168-ti-r68 uses `/dev/ttyS*` not `/dev/ttyO*`. UART2 (P9_21/22) = `/dev/ttyS2`.
    config.yaml updated: `bbb.sensor_uart: "/dev/ttyS2"` (was ttyO2, which was wrong).
  - **config-pin P9.21 uart && config-pin P9.22 uart** — both confirm "Current mode: uart".
    NOTE: not persistent across reboots; must re-run each boot.
  - **BBB Python deps** installed offline (no internet on USB-only BBB): serial pre-installed,
    requests + PyYAML wheels pushed from desktop via rsync.
  - **frames.py self-test PASSES on BBB**: CRC=0x29B1, 32-byte sensor round-trip, 16-byte
    command round-trip, bad-CRC rejection — all pass.
  - **EGSE running**: `run_egse.py` confirmed live at 50 Hz, tx counter >2000 frames.
    Isaac unreachable (desktop 192.168.86.91:8282 not reachable from BBB USB-only) — expected,
    data_ready=False but frames transmit regardless.
  - **UART-LINK BLOCKED**: zero bytes in both directions (BBB→Jetson and Jetson→BBB).
    Software confirmed EGSE transmits and Jetson ttyTHS1 is open. Physical wire(s) open circuit.
    GND continuity check is the next step (most likely cause).

## Next action for whoever picks this up

**Immediate blocker: cross-board UART wiring open circuit.**

3 wires have been placed between Jetson J12 and BBB P9. Software confirms EGSE transmits
at 50 Hz and Jetson UART enumerates, but zero bytes cross in either direction.

Multimeter steps to unblock (do in order):

1. **GND continuity** — continuity mode, probe BBB P9 row 1 (either column) ↔ Jetson J12
   row 3 inner column (pin 6). Must beep. This is the most likely failure.
2. **BBB TX idle voltage** — DC voltage, BBB P9_1 (−) → P9_21 row 11 outer column (+).
   Must read ~3.3 V. Confirms UART pinmux active.
3. **Signal wire continuity** — continuity mode, BBB P9 row 11 outer (P9_21) ↔ Jetson J12
   row 5 inner (pin 10). Must beep.

Once wiring passes continuity:
- SSH BBB: `cd ~/AvionicsHIL/bbb/egse && config-pin P9.21 uart && config-pin P9.22 uart && PYTHONUNBUFFERED=1 nohup python3 -u run_egse.py --config ../../config.yaml > /tmp/egse.log 2>&1 &`
- SSH Jetson: `cd ~/AvionicsHIL/jetson/bringup && source .venv/bin/activate && python3 check_interfaces.py --config ../../config.yaml`
- Target: UART-LINK → PASS (valid frames counted).

After UART-LINK passes → TASK-03 (Jetson FSW reads frames, runs PD control law, sends commands).
