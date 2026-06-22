# TASK-01 — Jetson interface bring-up & checkout (Act 1)

> Self-contained brief. Read [../AGENTS.md](../AGENTS.md), [../ARCHITECTURE.md](../ARCHITECTURE.md),
> [../INTERFACES.md](../INTERFACES.md), [../HARDWARE.md](../HARDWARE.md) first. Honor INTERFACES exactly.

## Objective
Bring up and **check out** the Jetson Orin Nano's communication interface to the EGSE: enumerate
the UART (MVP) and I²C (upgrade) on the 40-pin header, confirm they are electrically alive, and
emit a machine-readable **checkout report**. This is the "autonomous board bring-up & checkout" act.

## Why it matters (SpaceX mapping)
Board bring-up + checkout is the first thing an avionics test engineer does with new hardware:
prove the bus enumerates, the driver loads, and signals are electrically sound — *before* trusting it.

## Dependencies
None. Runs in parallel with TASK-02.

## Inputs (read these)
- Jetson pin map + `/dev` VERIFY items: [../HARDWARE.md](../HARDWARE.md) §2, §4, §5.
- Pinmux CSVs: `Embedded/JetsonOrinNano/output/sodimm_connector_pins.csv`, `T234_chip_down_pinmux.csv`.
- Transport + frame contract: [../INTERFACES.md](../INTERFACES.md) §3–5.

## Deliverables (create under `jetson/`)
- `jetson/bringup/check_interfaces.py` — enumerates UART + I²C, runs electrical checks, writes a report.
- `jetson/bringup/uart_loopback.py` — TX↔RX loopback self-test (port works before wiring to BBB).
- `jetson/bringup/README.md` — exact run steps + the confirmed `/dev` names.
- `reports/checkout_jetson.json` — machine-readable result (schema below).
- Update `config.yaml` (create from INTERFACES §8) with confirmed device names.

## Steps
1. **Create an on-target uv venv** on the Jetson (per AGENTS.md): `uv venv .venv && source .venv/bin/activate && uv pip install pyserial smbus2 pyyaml`.
2. **Enumerate devices.** `ls /dev/ttyTHS*`, `ls /dev/ttyACM*`, `i2cdetect -l`. Record which UART corresponds to 40-pin pins 8/10 and which `/dev/i2c-N` to pins 3/5. **Write the answers into STATUS.md VERIFY log and config.yaml.** (Cross-check against the pinmux CSV.)
3. **UART loopback self-test** (`uart_loopback.py`): jumper Jetson pin 8 → pin 10, open the port at 115200, write a known pattern, assert it reads back. This proves the UART works independent of the BBB.
4. **UART link check** (after BBB wired per HARDWARE §4): with TASK-02's `sensor_source` running on the BBB, read bytes, resync on the §3 magic `{0xA5,0x5A}`, validate CRC-16/CCITT, and confirm ≥N valid frames/sec. (If BBB not ready yet, this step is deferred — loopback is enough for first checkout.)
5. **I²C check (upgrade path only):** if `config.yaml: i2c_slave_enabled` is true and BBB presents 0x42, run `i2cdetect -y -r <bus>` and assert 0x42 appears. Otherwise mark this check `SKIPPED (UART transport)`.
6. **Emit checkout report** (`check_interfaces.py` → `reports/checkout_jetson.json`).
7. **Write `jetson/bringup/README.md`** with the confirmed device names and exact commands.
8. Update STATUS.md (task → DONE, VERIFY answers, changelog line).

## Checkout report schema (`reports/checkout_jetson.json`)
```json
{
  "board": "jetson-orin-nano",
  "timestamp": "ISO-8601",
  "checks": [
    {"id":"UART-ENUM","desc":"40-pin UART device present","status":"PASS","evidence":"/dev/ttyTHS1"},
    {"id":"UART-LOOPBACK","desc":"TX->RX loopback echoes pattern","status":"PASS","evidence":"256/256 bytes"},
    {"id":"UART-LINK","desc":"valid sensor frames from BBB","status":"PASS|SKIPPED","evidence":"49 frames/s, 0 CRC errors"},
    {"id":"I2C-ENUM","desc":"40-pin I2C bus enumerates","status":"PASS|SKIPPED","evidence":"i2cdetect -l"},
    {"id":"I2C-SLAVE-DETECT","desc":"BBB slave at 0x42","status":"PASS|SKIPPED","evidence":"..."}
  ],
  "summary": {"pass":0,"fail":0,"skipped":0}
}
```

## Acceptance criteria
- `ls /dev/ttyTHS*` and `i2cdetect -l` results recorded in STATUS.md + config.yaml.
- `uart_loopback.py` passes (bytes written == bytes read back).
- `reports/checkout_jetson.json` written with at least UART-ENUM + UART-LOOPBACK = PASS.
- `jetson/bringup/README.md` lets a fresh session reproduce the checkout in <5 min.

## Known unknowns / how to resolve
- **Exact `/dev` names** depend on the device tree → resolve by enumeration in step 2; record them.
- If the 40-pin UART is not exposed by default, enable it (`/boot/extlinux` overlay or `jetson-io`); document what you did in the bringup README.

## Definition of done
All acceptance criteria met; STATUS.md updated (state, VERIFY answers, changelog). Diagnose-and-fix
example captured if anything failed (that material feeds the Act-4 / report narrative).
