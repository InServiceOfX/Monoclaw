#!/usr/bin/env python3
"""
Jetson FSW main loop — AvionicsHIL TASK-03.

Reads 32-byte sensor frames from UART, runs the landing-burn PD control law,
and writes 16-byte command frames back. Designed to run on the Jetson Orin Nano
but also testable on the desktop via the pty loopback harness.

Usage (Jetson):
    python3 fsw_main.py [--config ../../config.yaml] [--uart /dev/ttyTHS1]

Usage (desktop loopback test — see desktop_hil_loop.py):
    python3 fsw_main.py --uart /dev/pts/N [--config ...]
"""
import argparse
import json
import os
import sys
import time
import serial
import yaml
from pathlib import Path
from dataclasses import asdict

# Frames and control live alongside this file.
sys.path.insert(0, str(Path(__file__).parent))
from frames import (
    SensorFrame, CommandFrame,
    pack_command_frame, unpack_sensor_frame, find_magic,
    SENSOR_MAGIC, SENSOR_FRAME_SIZE, CMD_FRAME_SIZE,
    FLAGS_ENGINE_ENABLE, FLAGS_ABORT, STATUS_FAULT_ACTIVE,
)
from control import ControlConfig, ControlOutput, run_control


def parse_args():
    p = argparse.ArgumentParser(description="Jetson FSW — landing burn HIL loop")
    p.add_argument("--config", default="../../config.yaml")
    p.add_argument("--uart",   default=None, help="Override UART device")
    p.add_argument("--log",    default="/tmp/fsw_run.jsonl", help="JSONL telemetry log")
    p.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0=run forever)")
    return p.parse_args()


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    args  = parse_args()
    cfg   = load_config(args.config)
    uart_dev = args.uart or cfg["jetson"]["sensor_uart"]
    baud     = cfg["jetson"]["baud"]

    ctrl_cfg = ControlConfig(
        target_touchdown_velocity_mps=cfg["control"]["target_touchdown_velocity_mps"],
        kp=cfg["control"]["kp"],
        kd=cfg["control"]["kd"],
    )

    print(f"[fsw] Opening UART {uart_dev} @ {baud} baud", flush=True)
    ser = serial.Serial(uart_dev, baudrate=baud, timeout=0.1)

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    frames_rx  = 0
    frames_bad = 0
    loop_times = []
    buf = b""
    last_ctrl  = ControlOutput(throttle=0.21, engine_enable=False, abort=False, landed=False)
    start_time = time.monotonic()

    print(f"[fsw] Running. Log → {log_path}", flush=True)

    with open(log_path, "w") as log_f:
        while True:
            t0 = time.monotonic()

            # Read available bytes, accumulate into buffer
            chunk = ser.read(SENSOR_FRAME_SIZE * 2)
            if chunk:
                buf += chunk

            # Resync on magic, consume complete frames
            while True:
                idx = find_magic(buf, SENSOR_MAGIC)
                if idx < 0 or len(buf) - idx < SENSOR_FRAME_SIZE:
                    # Discard bytes before any magic to keep buffer lean
                    if idx < 0 and len(buf) > 2:
                        buf = buf[-2:]
                    break

                frame_bytes = buf[idx: idx + SENSOR_FRAME_SIZE]
                buf = buf[idx + SENSOR_FRAME_SIZE:]

                sf = unpack_sensor_frame(frame_bytes)
                if sf is None:
                    frames_bad += 1
                    continue

                frames_rx += 1
                fault_active = bool(sf.status & STATUS_FAULT_ACTIVE)

                ctrl = run_control(
                    altitude_mm=sf.altitude_mm,
                    velocity_z_cms=sf.velocity_z_cms,
                    fault_active=fault_active,
                    cfg=ctrl_cfg,
                )
                last_ctrl = ctrl

                flags = 0
                if ctrl.engine_enable:
                    flags |= FLAGS_ENGINE_ENABLE
                if ctrl.abort:
                    flags |= FLAGS_ABORT

                cmd = CommandFrame(
                    seq=sf.seq,
                    throttle=ctrl.throttle,
                    gimbal_pitch_mrad=0,
                    gimbal_yaw_mrad=0,
                    flags=flags,
                )
                ser.write(pack_command_frame(cmd))

                # Telemetry log entry
                elapsed = time.monotonic() - start_time
                entry = {
                    "t":          round(elapsed, 4),
                    "seq":        sf.seq,
                    "alt_m":      sf.altitude_mm / 1000.0,
                    "vz_mps":     sf.velocity_z_cms / 100.0,
                    "throttle":   round(ctrl.throttle, 4),
                    "engine_on":  ctrl.engine_enable,
                    "abort":      ctrl.abort,
                    "landed":     ctrl.landed,
                    "fault":      fault_active,
                    "fault_code": sf.fault_code,
                }
                log_f.write(json.dumps(entry) + "\n")
                log_f.flush()

                dt = time.monotonic() - t0
                loop_times.append(dt)

                if ctrl.landed:
                    final_vz = sf.velocity_z_cms / 100.0
                    print(f"[fsw] LANDED — vz={final_vz:.2f} m/s  alt={sf.altitude_mm/1000:.1f} m  "
                          f"frames_rx={frames_rx}  frames_bad={frames_bad}", flush=True)
                    _write_report(log_path, loop_times, frames_rx, frames_bad, entry)
                    return

                if frames_rx % 50 == 0:
                    rate = frames_rx / max(elapsed, 0.001)
                    print(f"[fsw] t={elapsed:.1f}s  seq={sf.seq}  "
                          f"alt={sf.altitude_mm/1000:.1f}m  vz={sf.velocity_z_cms/100:.2f}m/s  "
                          f"thr={ctrl.throttle:.3f}  rate={rate:.1f}Hz", flush=True)

                if args.max_frames and frames_rx >= args.max_frames:
                    print(f"[fsw] Reached max-frames={args.max_frames}, exiting.", flush=True)
                    _write_report(log_path, loop_times, frames_rx, frames_bad, entry)
                    return


def _write_report(log_path: Path, loop_times, frames_rx, frames_bad, last_entry):
    if not loop_times:
        return
    avg_hz = 1.0 / (sum(loop_times) / len(loop_times)) if loop_times else 0
    report = {
        "run_id":              time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "loop_rate_hz_measured": round(avg_hz, 2),
        "frames_rx":           frames_rx,
        "frames_bad":          frames_bad,
        "final_alt_m":         last_entry.get("alt_m"),
        "final_vz_mps":        last_entry.get("vz_mps"),
        "landed":              last_entry.get("landed", False),
        "soft_touchdown":      last_entry.get("landed") and abs(last_entry.get("vz_mps", 99)) < 2.0,
    }
    report_path = log_path.with_suffix(".report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[fsw] Report → {report_path}", flush=True)
    verdict = "PASS ✓" if report["soft_touchdown"] else "FAIL ✗"
    print(f"[fsw] Soft touchdown: {verdict}  final vz={report['final_vz_mps']} m/s", flush=True)


if __name__ == "__main__":
    main()
