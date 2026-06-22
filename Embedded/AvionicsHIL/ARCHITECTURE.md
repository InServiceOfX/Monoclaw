# AvionicsHIL — Architecture

This document describes the bench, the hardware-in-the-loop (HIL) control loop, the data
flow, and how each piece maps to a real avionics test rig. Read [INTERFACES.md](INTERFACES.md)
for the exact wire contracts referenced here.

---

## 1. The thesis, in engineering terms

A real avionics test rig replaces flight sensors with **simulated signals from Electrical
Ground Support Equipment (EGSE)** so the flight computer runs under realistic mission
conditions without the full flight vehicle. We build exactly that, and put an **AI agent in
the test-engineer seat**: it reads the board documentation, brings up the interfaces, writes
the firmware and the Python test automation, runs the loop, injects faults, diagnoses
failures, and produces the verification report.

The Jetson Orin Nano is the **flight computer / DUT** and never knows it is in a simulation —
it only ever talks to its physical buses. That fidelity is the whole point.

## 2. Bench topology

```
   ┌──────────────────────────────┐
   │  DESKTOP (RTX 3060, headless) │
   │  Isaac Sim Starship physics   │   "truth" vehicle dynamics (Z-up)
   │  HTTP :8282 telemetry+command │
   └───────────────▲──────────────┘
                    │ LAN (Ethernet)   GET /telemetry/latest  ·  POST /starship/command
                    │
   ┌────────────────┴───────────────────────────────────────────┐
   │  BeagleBone Black Rev C1  —  EGSE (test instrument)          │
   │  · truth_bridge   : poll Isaac → fill sensor model          │
   │  · sensor_source  : present sensor frames to the DUT        │
   │  · actuator_sink  : receive DUT commands → POST to Isaac    │
   │  · fault_injector : corrupt sensor values on command (Act4) │
   └───────▲─────────────────────────────────────────┬──────────┘
           │ SENSORS IN (BBB → Jetson)                │ ACTUATORS OUT (Jetson → BBB)
           │ default transport: UART @ 115200         │ default transport: UART
           │ (I²C-slave is a verification-gated        │
           │  upgrade — see INTERFACES §Transports)    │
   ┌───────┴─────────────────────────────────────────▼──────────┐
   │  NVIDIA Jetson Orin Nano  —  DUT / FLIGHT COMPUTER          │
   │  Flight Software (FSW): read sensors → control law →        │
   │  emit actuator command. Knows nothing about Isaac.          │
   └─────────────────────────────────────────────────────────────┘

   (Act 2 only) Breadboard analog front-end:
     thermistor / LM335Z → LM358 gain stage → ADC  → a real sensor channel the DUT reads
```

### Why the BBB is the sole bridge to Isaac
Keeping the BBB as the only thing that talks to Isaac means the Jetson FSW is a pure flight
computer: sensors in over one bus, actuator commands out over another. This is the honest HIL
architecture and it makes the "the DUT is unmodified flight code" claim true.

## 3. The control loop (one HIL tick)

1. **Isaac** advances physics; exposes truth state `{x,y,z, quaternion, v}` (Z-up, z = altitude). `GET /telemetry/latest`.
2. **BBB `truth_bridge`** polls truth, converts to engineering units, fills the **sensor model** (altitude, vertical velocity, accel, gyro).
3. **BBB `sensor_source`** serializes the sensor model into a **32-byte sensor frame** (INTERFACES §3) and sends it to the Jetson over the sensor transport.
4. **Jetson FSW** parses the frame, runs the **landing-burn control law**, produces a throttle + gimbal command.
5. **Jetson FSW** serializes a **16-byte command frame** (INTERFACES §4) over the actuator transport to the BBB.
6. **BBB `actuator_sink`** parses the command and `POST /starship/command` to Isaac (throttle/gimbal).
7. **Isaac** applies the force; loop repeats at the loop rate (target 50–100 Hz; see §6).

The loop is closed: physics → sensors → flight computer → actuators → physics.

## 4. Mapping to SpaceX Avionics Test responsibilities

| SpaceX JD bullet | Where it lives here |
|---|---|
| "embedded software on the avionics device under test" | Jetson FSW (`jetson/`) |
| "Python automation interacting with UUT, test equipment, instrumentation" | the agent's test harness + BBB EGSE (`bbb/`) |
| "test execution across HIL and virtualized hardware simulation" | Isaac (virtual) + physical bench (HIL) |
| "instrumentation device drivers" | BBB sensor_source / sensor model drivers |
| "analyze complex test data" | telemetry assertions + Test Readiness Review (TASK-06) |
| "drive product reliability and yield" | fault-injection campaign (TASK-05) |
| "analog and digital circuit boards" | breadboard analog front-end (TASK-04) |

## 5. Act 0 — Knowledge ingestion (already complete)

The agent has already converted all reference material into machine-readable form. This is the
"the agent read everything" proof and the foundation every later act builds on:

- **Jetson pinmux** → `Data/Public/embedded/NVIDIAJetsonOrinNano/output/*.csv` (parsed from the NVIDIA pinmux XLSM + carrier spec by `Embedded/JetsonOrinNano/parse_pdfs.py` + `parse_pinmux.py`).
- **BeagleBone Black** schematic/SRM → `Data/Public/embedded/BeagleBoneBlack/` (+ parseable with the JetsonOrinNano venv tooling).
- **Art of Electronics 3e** → `…/HorowitzHill-ArtOfElectronics3e/ocr-compare/reconciled/resolved.md` (OCR-reconciled, vision-verified equations).
- **Parts bin** → `Data/Public/embedded/HomeElectronicsInventory/inventory.json` (vision-scanned).

## 6. Design parameters and assumptions

- **Loop rate:** start at **50 Hz** (20 ms budget). UART @ 115200 moves a 32-byte frame in ~2.8 ms, leaving margin. Raise toward 100 Hz once stable.
- **Units:** SI at the physics boundary; fixed-point integers on the wire (see INTERFACES §3). Convert at the edges only.
- **Coordinate frame:** Z-up (ROS REP-103), matching the Isaac stack. z = altitude, +Z = up. Do not reintroduce Y-up.
- **Determinism:** the BBB timestamps every sensor frame; the FSW echoes the seq number in its command so latency and drops are measurable (this is the "deterministic verification of timing" story).
- **Control law (MVP):** a simple altitude/velocity landing-burn law (PD on vertical velocity targeting a soft touchdown). It does not need to be sophisticated to be a compelling HIL demo — it needs to close the loop and respond to injected faults. Refine later.

## 7. Open architectural questions (resolve as you build; log decisions in STATUS.md)

1. **Sensor transport:** UART (guaranteed) vs I²C-slave on BBB (better "bus" story, but AM335x Linux I²C-slave support must be verified — see INTERFACES §Transports and TASK-02). Default to UART for the MVP; treat I²C-slave as a gated upgrade.
2. **Isaac command API:** confirm whether a continuous throttle/gimbal command route exists or must be added to the Isaac control server (the existing stack has `action:"liftoff"`; continuous throttle is a known TODO in `STATUS_ZUP_PHYSICS.md`). TASK-03 handles this.
3. **FSW language:** reuse the existing Rust `jetson-fsw` (preferred — reuses its datagram parser) vs a Python FSW for speed of iteration. Recommend Rust for the "flight code" credibility; Python acceptable for a first loop-closure spike.
