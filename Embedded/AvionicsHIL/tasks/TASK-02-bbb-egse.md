# TASK-02 — BeagleBone Black EGSE: sensor source + Isaac bridges (Act 3 infra)

> Self-contained brief. Read [../AGENTS.md](../AGENTS.md), [../ARCHITECTURE.md](../ARCHITECTURE.md),
> [../INTERFACES.md](../INTERFACES.md), [../HARDWARE.md](../HARDWARE.md) first. Honor INTERFACES exactly.

## Objective
Turn the BeagleBone Black into **EGSE**: it polls Isaac's truth telemetry, converts it to the
logical sensor model, streams **32-byte sensor frames** to the Jetson, receives **16-byte command
frames** back, and relays those commands to Isaac. (Fault injection is added later in TASK-05; build
the hook now but leave it inert.)

## Why it matters (SpaceX mapping)
This is the "simulated signals from EGSE" + "instrumentation device drivers" core of any HIL rig.

## Dependencies
None to start coding (build against INTERFACES + a synthetic/recorded telemetry source). Physical
loop closure needs the Isaac stack reachable and TASK-03's FSW on the other end.

## Inputs
- Frame formats + fixed-point encoding + fault codes: [../INTERFACES.md](../INTERFACES.md) §1–6.
- Isaac API + runtime gotchas: [../INTERFACES.md](../INTERFACES.md) §7.
- BBB pin map + UART/I²C wiring: [../HARDWARE.md](../HARDWARE.md) §3–5.
- Isaac stack to point at: `repos/Monoclaw/Deployments/Stacks/IsaacSim/` (+ its `STATUS_ZUP_PHYSICS.md`).

## Deliverables (create under `bbb/`)
- `bbb/egse/sensor_model.py` — the logical sensor model + unit conversions (INTERFACES §1–2).
- `bbb/egse/frames.py` — pack/unpack of the 32-byte sensor frame and 16-byte command frame + CRC-16/CCITT. **Shared contract; mirror exactly on the Jetson side (TASK-03).**
- `bbb/egse/truth_bridge.py` — poll `GET <isaac>/telemetry/latest` → fill sensor_model.
- `bbb/egse/sensor_source.py` — serialize sensor frames → write to the sensor transport at loop rate.
- `bbb/egse/actuator_sink.py` — read command frames from the transport → `POST <isaac>/starship/command`.
- `bbb/egse/fault_injector.py` — inert stub now (INTERFACES §6 codes); TASK-05 fills it in.
- `bbb/egse/run_egse.py` — wires the above into one process driven by `config.yaml`.
- `bbb/egse/README.md` — exact run steps + confirmed BBB device names.

## Steps
1. **On-target uv venv** on the BBB: `uv venv .venv && source .venv/bin/activate && uv pip install pyserial requests pyyaml`. (If `uv` is unavailable on the BBB's old userspace, document the fallback and still use a venv via `python3 -m venv` — never system pip.)
2. **Enable + confirm the UART** (HARDWARE §3): `config-pin P9.21 uart; config-pin P9.22 uart`, confirm `/dev/ttyO*`. Record the device in STATUS.md + config.yaml.
3. **Implement `frames.py`** to the byte layouts in INTERFACES §3–4. Include a CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF). Add a round-trip unit test (`pack(unpack(x)) == x`).
4. **Implement `sensor_model.py`** conversions: altitude m→mm (i32), vz m/s→cm/s (i16), accel→milli-g (i16), gyro→deci-deg/s (i16) per INTERFACES §2.
5. **Implement `truth_bridge.py`:** poll Isaac telemetry; map `z→altitude`, `vz→velocity_z`; derive accel by finite-difference (or 0); gyro 0 for MVP. Handle Isaac being unreachable gracefully (hold last + set a status flag).
6. **Implement `sensor_source.py`:** at `loop.rate_hz`, serialize the current model to a 32-byte frame (incrementing seq, BBB monotonic timestamp_ms) and write to the sensor UART.
7. **Implement `actuator_sink.py`:** read 16-byte command frames (resync on magic `{0x5A,0xA5}`, validate CRC), and `POST /starship/command`. Map throttle/gimbal to the Isaac command body (coordinate with TASK-03 on whether the route exists/needs adding — see INTERFACES §7).
8. **`run_egse.py`:** start truth_bridge + sensor_source + actuator_sink (threads or asyncio) from config.yaml. Print a 1 Hz status line (frames sent, commands recv'd, last altitude).
9. **Bench test without the Jetson:** loop sensor_source TX → BBB's own RX and confirm valid frames; mock Isaac with a local HTTP stub serving a descending-altitude telemetry so you can exercise truth_bridge offline.
10. Update STATUS.md (VERIFY answers, state, changelog).

## VERIFY: I²C-slave upgrade (do this check, then decide)
Before promising the I²C transport, confirm BBB Linux I²C **slave** support:
- Check `i2cdetect -F <bus>` for `I2C_FUNC_SLAVE`, and whether `i2c-slave-eeprom` can bind (device-tree overlay declaring a slave at 0x42).
- If supported: implement an `i2c_slave_source.py` that keeps the §5 register map in the slave EEPROM backing buffer (truth_bridge writes registers instead of UART frames). Set `i2c_slave_enabled: true`.
- If **not** supported: record that in STATUS.md and **stay on UART** (the MVP path). Do not sink days into PRU I²C-slave for the demo.

## Acceptance criteria
- `frames.py` round-trip unit test passes; CRC matches an independent reference (cross-check vs the Jetson side once TASK-03 exists).
- With a mock Isaac telemetry source, `run_egse.py` emits ≥ `rate_hz` valid sensor frames/sec for 60 s with monotonic seq + timestamps.
- `actuator_sink.py` parses a known-good command frame and issues the correct Isaac POST (verified against a request log or a stub).
- BBB UART device name recorded in STATUS.md + config.yaml.

## Definition of done
Acceptance met; `bbb/egse/README.md` reproduces the run; STATUS.md updated. Fault hook present but inert.
