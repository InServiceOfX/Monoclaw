# Jetson FSW — AvionicsHIL TASK-03

Landing-burn flight software for the Jetson Orin Nano (DUT).

## Files

| File | Purpose |
|------|---------|
| `frames.py` | Wire frame pack/unpack — identical contract to `bbb/egse/frames.py` |
| `control.py` | PD landing-burn control law |
| `fsw_main.py` | Main loop: read sensor UART → control → write command UART |
| `desktop_hil_loop.py` | Desktop loopback test: closes full loop via pty without physical UART |

## Desktop HIL loopback (no hardware needed)

Closes the full control loop on the desktop using a pty pair instead of physical UART.
Works with or without Isaac Sim running.

```bash
cd Embedded/AvionicsHIL

# With Isaac Sim (recommended — real physics):
python3 jetson/fsw/desktop_hil_loop.py --config config.yaml

# Without Isaac (built-in Mars free-fall sim):
python3 jetson/fsw/desktop_hil_loop.py --config config.yaml --no-isaac

# Short run (tune gains):
python3 jetson/fsw/desktop_hil_loop.py --config config.yaml --duration 60
```

Output:
- `reports/hil_desktop.jsonl` — per-frame telemetry trace
- `reports/hil_desktop.report.json` — PASS/FAIL verdict

## Running on Jetson (hardware)

Requires: physical UART wiring BBB↔Jetson (see STATUS.md for wiring debug steps).

```bash
# On Jetson — install deps first (offline):
pip install pyserial pyyaml

# Start FSW:
cd ~/AvionicsHIL
python3 jetson/fsw/fsw_main.py --config config.yaml

# On BBB (separate SSH) — start EGSE:
cd ~/AvionicsHIL/bbb/egse
config-pin P9.21 uart && config-pin P9.22 uart
python3 run_egse.py --config ../../config.yaml
```

## Control law

PD controller on vertical velocity targeting soft touchdown at `config.yaml:control.target_touchdown_velocity_mps` (default -2.0 m/s).

```
error_v  = target_v - vz          # +ve when falling faster than target
throttle = HOVER_THROTTLE + kd × error_v + altitude_ramp_term
throttle = clamp(throttle, 0.0, 0.85)
```

Tune `kp` and `kd` in `config.yaml`. Increase `kd` for harder braking; decrease if oscillating.

## Acceptance criteria (TASK-03)

- [ ] `frames.py` golden-bytes cross-check: frame from BBB parsed correctly, vice versa
- [ ] Desktop HIL loop runs ≥ 60 s without desync
- [ ] Descent ends in soft touchdown: `|vz| < 2 m/s` at `alt ≈ 0`
- [ ] `reports/hil_desktop.report.json` shows PASS
