# AvionicsHIL — Interface Contracts (SOURCE OF TRUTH)

Everything that crosses a boundary is defined here. The BBB side (TASK-02) and the Jetson side
(TASK-03) are built independently against this file. **If you change a frame, register, or API
shape, update this file in the same commit and note it in STATUS.md.** A drift between the two
sides is the #1 way this demo silently breaks.

All multi-byte fields are **little-endian** unless stated. CRC is **CRC-16/CCITT-FALSE**
(poly 0x1021, init 0xFFFF) over all preceding bytes in the frame (magic included).

---

## 1. Logical sensor model (engineering units)

The shared mental model of "what the vehicle's sensors report." `truth_bridge` fills it from
Isaac; `sensor_source` serializes it (§3); the FSW reconstructs it.

| Field | Unit | Source from Isaac telemetry |
|-------|------|-----------------------------|
| `altitude` | metres (z, up) | `z` |
| `velocity_z` | m/s (up +) | `vz` |
| `accel_xyz` | m/s² (body or world; MVP: world) | finite-difference of `vx,vy,vz`, or 0 if unavailable |
| `gyro_xyz` | rad/s | derive from quaternion rate, or 0 for MVP |
| `status` | flags | data_ready / fault_active |

For the MVP, **altitude + velocity_z are the only fields the control law needs.** accel/gyro
may be zero-filled until the law uses them. Keep the wire fields present regardless.

## 2. Fixed-point wire encoding

| Quantity | Wire type | Scale | Example |
|----------|-----------|-------|---------|
| altitude | `i32` | millimetres | 996.4 m → 996400 |
| velocity_z | `i16` | cm/s | -52.3 m/s → -5230 |
| accel (each axis) | `i16` | milli-g (1 g = 9.80665 m/s²) | 1.0 g → 1000 |
| gyro (each axis) | `i16` | deci-deg/s | 12.0 deg/s → 120 |
| throttle | `f32` | 0.0–1.0 | 0.8 |
| gimbal angle | `i16` | milli-radian | 0.05 rad → 50 |

## 3. Sensor frame — BBB → Jetson (32 bytes)

```
off  size  field            type   notes
0    2     magic            u8[2]  {0xA5, 0x5A}
2    2     seq              u16    increments each frame, wraps
4    4     timestamp_ms     u32    BBB monotonic ms since loop start
8    4     altitude_mm      i32    §2
12   2     velocity_z_cms   i16    §2
14   2     reserved0        u16    0
16   6     accel_xyz_mg     i16[3] §2 (x,y,z)
22   6     gyro_xyz_ddps    i16[3] §2 (x,y,z)
28   1     status           u8     bit0 data_ready, bit1 fault_active
29   1     fault_code       u8     0=none; see §6
30   2     crc16            u16    CRC-16/CCITT-FALSE over bytes 0..29
```

## 4. Command frame — Jetson → BBB (16 bytes)

```
off  size  field            type   notes
0    2     magic            u8[2]  {0x5A, 0xA5}
2    2     seq              u16    ECHO of the sensor frame seq this command responds to
4    4     throttle         f32    0.0–1.0 main engine throttle
8    2     gimbal_pitch_mrad i16   §2
10   2     gimbal_yaw_mrad  i16    §2
12   2     flags            u16    bit0 engine_enable, bit1 abort
14   2     crc16            u16    CRC-16/CCITT-FALSE over bytes 0..13
```

Echoing `seq` lets the BBB measure round-trip latency and detect drops → the
"deterministic timing verification" deliverable.

## 5. Transports

### Default (MVP): UART — guaranteed both directions
- **Sensors (BBB→Jetson)** and **commands (Jetson→BBB)** each on a UART link, 115200 8N1.
- Frames are sent back-to-back; the receiver resynchronizes on the 2-byte magic and validates CRC. Drop and resync on CRC fail.
- Pins: see HARDWARE.md (BBB P9 UART ↔ Jetson 40-pin UART; **both 3.3 V, common ground, TX↔RX crossed**).
- Rationale: AM335x (BBB) UART is rock-solid in Linux userspace; no kernel/devicetree risk. Build the loop on this first.

### Upgrade (verification-gated): I²C with BBB as slave
- Better "avionics bus" story; lets the Jetson **master** the bus and read the BBB as a sensor (Act 1 checkout becomes "detect the sensor at 0x42").
- **RISK:** AM335x Linux I²C **slave** support (`i2c-slave-eeprom` backend, needs `I2C_FUNC_SLAVE`) is not guaranteed on the BBB's shipping kernel. **Verify before committing** (TASK-02 §Verify-I²C-slave). If unsupported, options: (a) PRU-based I²C slave (complex), (b) stay on UART, (c) flip to SPI with BBB as SPI slave (McSPI slave mode is more reliable).
- If adopted, the register map mirrors §3: register 0x00 = WHO_AM_I (0x5A), 0x01 = STATUS, 0x08–0x0B = altitude_mm, 0x0C–0x0D = velocity_z_cms, 0x10–0x1B = accel/gyro, 0xF0 = FAULT_INJECT.
- I²C address: **0x42**. 3.3 V bus, two 4.7 kΩ pull-ups (HARDWARE.md).

## 6. Fault codes (Act 4 — TASK-05)

| code | name | sensor_source behavior |
|------|------|------------------------|
| 0 | NONE | nominal |
| 1 | STUCK | freeze all fields at last value |
| 2 | NAN_ALT | altitude_mm = 0x7FFFFFFF (sentinel "invalid") |
| 3 | DROPOUT | stop sending frames for N ms |
| 4 | BITFLIP | flip one random bit in payload (CRC still valid → tests value-plausibility, not just CRC) |
| 5 | OUT_OF_RANGE | altitude jumps to an impossible value (e.g., +1e6 mm) |
| 6 | NOISE | add large random noise to velocity/accel |

The FSW must detect/handle each (reject, hold-last, safe-state, or abort) and the harness
asserts the correct response. `fault_active` (status bit1) and `fault_code` are set so the
test harness has ground truth about what was injected.

## 7. Isaac Sim API (existing stack)

Base URL: `http://<DESKTOP_IP>:8282` (host-networked; default desktop LAN IP per HARDWARE.md).

- `GET /telemetry/latest` → JSON `{x,y,z, qw,qx,qy,qz, vx,vy,vz}`; **z = altitude (Z-up)**, m and m/s.
- `POST /starship/command` → existing body `{"action":"liftoff","velocity":<f>}`.
  - **Continuous throttle/gimbal is a known TODO** in `Deployments/Stacks/IsaacSim/STATUS_ZUP_PHYSICS.md`. TASK-03 must confirm/extend the control server with e.g. `{"action":"throttle","value":0.0..1.0,"gimbal_pitch":<rad>,"gimbal_yaw":<rad>}` mapping to `starship_controller.py`.
- **Runtime gotcha (do not violate):** in physics-only headless mode, **never** call `/scene/load` or `/starship/create-stage` at runtime — it re-inits GLFW windowing and crashes the app. The scene auto-loads at boot via `ISAAC_SCENE_PATH`. To change the scene, edit USD on disk + restart the container.

## 8. Run configuration schema (`config.yaml`)

Each host reads a YAML config; create from this schema (do not hardcode IPs in code):

```yaml
isaac:
  base_url: "http://192.168.86.91:8282"   # desktop eno1 (verify per HARDWARE.md)
  poll_hz: 100
bbb:
  sensor_uart: "/dev/ttyO4"               # VERIFY which P9 UART is enabled
  actuator_uart: "/dev/ttyO4"             # may share or use a 2nd UART
  baud: 115200
  i2c_slave_enabled: false                # flip true only after slave support verified
  i2c_addr: 0x42
jetson:
  sensor_uart: "/dev/ttyTHS1"             # VERIFY Jetson 40-pin UART device
  actuator_uart: "/dev/ttyTHS1"
  baud: 115200
loop:
  rate_hz: 50
control:
  target_touchdown_velocity_mps: -2.0
  kp: 0.05
  kd: 0.3
```

Every `VERIFY` above is a real unknown — confirm on hardware and record the answer in STATUS.md.

## 9. Report schema (TASK-06)

Test Readiness Review = machine-readable `reports/trr.json` + human `reports/trr.md`:

```json
{
  "run_id": "ISO-8601",
  "git_sha": "...",
  "loop_rate_hz_measured": 49.7,
  "tests": [
    {"id":"BRINGUP-I2C-01","requirement":"I²C bus enumerates","status":"PASS","evidence":"i2cdetect output ..."},
    {"id":"HIL-LAND-01","requirement":"soft touchdown |vz|<2 m/s","status":"PASS","evidence":"final vz=-1.8"},
    {"id":"FAULT-DROPOUT-01","requirement":"FSW safe-states on dropout","status":"PASS","evidence":"..."}
  ],
  "summary": {"pass": 0, "fail": 0, "total": 0}
}
```
