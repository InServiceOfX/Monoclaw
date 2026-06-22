# AvionicsHIL — Autonomous Avionics Bring-up, Test & Checkout

**Codename:** GROUND CONTROL
**One-line thesis:** *An AI agent harness performs the full avionics test-engineering loop — reads the datasheets, designs the circuit, writes the firmware AND the test automation, runs hardware-in-the-loop (HIL) against a physics sim, injects faults, diagnoses failures, and signs the verification report — autonomously.*

This is a demo built to (1) impress SpaceX's Avionics Test org, and (2) prove AI agents
(Claude Code, OpenClaw, hermes-agent) can autonomously own embedded bring-up, test, and
checkout. The **NVIDIA Jetson Orin Nano is the "flight computer" (the Device Under Test, DUT)**.

---

## START HERE (for any agent picking this up)

1. Read **[AGENTS.md](AGENTS.md)** — non-negotiable working conventions (venvs, git, wiring style). Violating these wastes the user's time.
2. Read **[ARCHITECTURE.md](ARCHITECTURE.md)** — the bench, the HIL loop, data flow.
3. Read **[INTERFACES.md](INTERFACES.md)** — the wire contracts. This is the source of truth that lets the BBB side and Jetson side be built independently. **Do not change a frame format without updating this file and STATUS.md.**
4. Read **[ORCHESTRATION.md](ORCHESTRATION.md)** — the task DAG and build order.
5. Check **[STATUS.md](STATUS.md)** — what is done, what is in progress, what is next. **Update it when you finish a unit of work.**
6. Pick the lowest-numbered `tasks/TASK-*.md` whose dependencies are met. Each brief is self-contained.

## The five acts (demo narrative)

| Act | Name | Task brief | Build priority |
|-----|------|-----------|----------------|
| 0 | Knowledge ingestion (datasheets, textbook, parts bin) | *done* (see ARCHITECTURE §Act 0) | ✅ complete |
| 1 | Autonomous board bring-up & checkout (Jetson I²C) | [TASK-01](tasks/TASK-01-jetson-i2c-bringup.md) | **1st** |
| 3 | Closed-loop HIL (Isaac ⇄ BBB-EGSE ⇄ Jetson FSW) | [TASK-02](tasks/TASK-02-bbb-egse.md), [TASK-03](tasks/TASK-03-jetson-fsw-hil.md) | **1st (vertical slice)** |
| 2 | Circuit design from Art of Electronics + parts bin | [TASK-04](tasks/TASK-04-analog-frontend.md) | 2nd (differentiator) |
| 4 | Fault injection & autonomous diagnosis | [TASK-05](tasks/TASK-05-fault-injection.md) | 3rd (showstopper) |
| 5 | CI/CD + Test Readiness Review report | [TASK-06](tasks/TASK-06-ci-report.md) | 4th |

**Vertical slice that proves the concept end-to-end = TASK-01 + TASK-02 + TASK-03.** Build that first.

## Hardware (the bench)

| Device | Role | Notes |
|--------|------|-------|
| NVIDIA Jetson Orin Nano | **DUT / flight computer** | runs the flight software (FSW) |
| BeagleBone Black Rev C1 | **EGSE** — sensor emulator + Isaac bridge + fault injector | the "test instrument" |
| Desktop (RTX 3060) | **Physics** — Isaac Sim Starship dynamics (Z-up, physics-only) | already built; see `Deployments/Stacks/IsaacSim` |
| Breadboard + LM358 + thermistor + NTE R/C | **Analog front-end under test** (Act 2) | parts from the vision-scanned bin |

Full bill of materials, pin assignments, wiring, and safety: **[HARDWARE.md](HARDWARE.md)**.

## Repo layout

```
Embedded/AvionicsHIL/
├── README.md            ← you are here
├── AGENTS.md            ← working conventions (read before doing anything)
├── ARCHITECTURE.md      ← system design, the HIL loop
├── INTERFACES.md        ← wire contracts (frame formats, register map, Isaac API, config schema)
├── HARDWARE.md          ← BOM, pin maps, wiring, safety
├── ORCHESTRATION.md     ← task DAG, build order, parallelization
├── STATUS.md            ← living status board (UPDATE THIS)
├── tasks/               ← self-contained task briefs (TASK-01 … TASK-06)
├── bbb/                 ← BeagleBone Black EGSE code (created by TASK-02)
├── jetson/              ← Jetson FSW + bring-up/test code (created by TASK-01, TASK-03)
├── analog/              ← Act 2 circuit design + verification (created by TASK-04)
└── reports/             ← generated checkout & verification reports
```

## What already exists and is reused (do not rebuild)

- **Isaac Sim Starship physics** (Z-up, physics-only headless, verified): `Deployments/Stacks/IsaacSim/`. Telemetry at `http://<desktop>:8282/telemetry/latest`. See its `STATUS_ZUP_PHYSICS.md`.
- **Jetson FSW skeleton** (Rust, UDP datagram parser): `~/.openclaw/workspace/jetson-fsw/`. Adapt, don't restart.
- **Jetson pinmux, parsed to CSV**: `Embedded/JetsonOrinNano/output/` (`sodimm_connector_pins.csv`, `T234_chip_down_pinmux.csv`).
- **BBB schematic/SRM**: `Data/Public/embedded/BeagleBoneBlack/`.
- **Parts inventory** (vision-scanned): `Data/Public/embedded/HomeElectronicsInventory/inventory.json`.
- **Art of Electronics 3e** (OCR-resolved): `Data/Public/books/EngineeringPhysics/HorowitzHill-ArtOfElectronics3e/ocr-compare/reconciled/resolved.md`.
