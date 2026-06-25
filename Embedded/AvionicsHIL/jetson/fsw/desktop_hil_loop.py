#!/usr/bin/env python3
"""
Desktop HIL loopback — closes the full control loop without physical UART.

Architecture:
    Isaac Sim HTTP :8282
        ↕  (poll telemetry / POST throttle)
    [EGSE thread]  — sensor frames → [pty master fd]
                                            ↕  virtual serial
                                     [pty slave fd] → [FSW thread] → command frames
                                            ↕
    [EGSE thread] ← command frames ← [pty master fd]
        ↕
    Isaac Sim HTTP :8282  (POST /starship/command throttle)

The pty pair gives a real byte-stream serial channel so all magic-sync,
CRC, and framing code runs exactly as it will on hardware.

Usage:
    cd Embedded/AvionicsHIL
    python3 jetson/fsw/desktop_hil_loop.py [--config config.yaml] [--duration 120]

Requires: pyserial, requests, pyyaml  (same deps as bbb/egse)
"""
import argparse
import json
import os
import sys
import threading
import time
import pty
import serial
import requests
import yaml
from pathlib import Path

# Pull in EGSE helpers and FSW frames/control from sibling dirs
ROOT = Path(__file__).resolve().parents[2]   # AvionicsHIL/
sys.path.insert(0, str(ROOT / "bbb" / "egse"))
sys.path.insert(0, str(Path(__file__).parent))

from frames import (
    SensorFrame, CommandFrame,
    pack_sensor_frame, pack_command_frame,
    unpack_sensor_frame, unpack_command_frame,
    find_magic, SENSOR_MAGIC, CMD_MAGIC,
    SENSOR_FRAME_SIZE, CMD_FRAME_SIZE,
    STATUS_DATA_READY, STATUS_FAULT_ACTIVE, FLAGS_ENGINE_ENABLE, FLAGS_ABORT,
)
from sensor_model import SensorModel
from control import ControlConfig, run_control


def parse_args():
    p = argparse.ArgumentParser(description="Desktop HIL loopback test")
    p.add_argument("--config",   default=str(ROOT / "config.yaml"))
    p.add_argument("--duration", type=float, default=120.0, help="Run for N seconds")
    p.add_argument("--log",      default=str(ROOT / "reports" / "hil_desktop.jsonl"))
    p.add_argument("--no-isaac", action="store_true",
                   help="Skip Isaac HTTP (use free-fall sim instead)")
    p.add_argument("--start-alt",  type=float, default=1000.0,
                   help="Initial altitude in metres (--no-isaac only)")
    p.add_argument("--start-vz",   type=float, default=0.0,
                   help="Initial vertical velocity m/s (--no-isaac only; negative = downward)")
    return p.parse_args()


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ── Shared state ──────────────────────────────────────────────────────────────
_lock          = threading.Lock()
_telem         = {"z": 1000.0, "vz": 0.0, "ok": False}
_last_throttle = 0.21
_log_entries   = []
_stop          = threading.Event()


# ── Isaac truth poller ────────────────────────────────────────────────────────
def isaac_poller(base_url: str, poll_hz: float):
    interval = 1.0 / poll_hz
    while not _stop.is_set():
        try:
            r = requests.get(f"{base_url}/telemetry/latest", timeout=0.5)
            if r.ok:
                d = r.json()
                with _lock:
                    _telem["z"]  = float(d.get("z",  _telem["z"]))
                    _telem["vz"] = float(d.get("vz", _telem["vz"]))
                    _telem["ok"] = True
        except Exception:
            pass
        time.sleep(interval)


def freefall_sim(dt: float = 0.02):
    """Minimal physics sim when Isaac isn't available."""
    MARS_G = 3.72
    while not _stop.is_set():
        with _lock:
            thr = _last_throttle
            z   = _telem["z"]
            vz  = _telem["vz"]
        # Engine thrust vs gravity (hover at 0.21 for Starship full-mass)
        net_accel = (thr - 0.21) * (MARS_G / 0.21)  # m/s²; 0 at hover
        vz_new = vz + net_accel * dt
        z_new  = max(0.0, z + vz_new * dt)
        with _lock:
            _telem["z"]  = z_new
            _telem["vz"] = vz_new
            _telem["ok"] = True
        time.sleep(dt)


def isaac_commander(base_url: str, throttle: float):
    try:
        requests.post(
            f"{base_url}/starship/command",
            json={"action": "throttle", "value": throttle,
                  "gimbal_pitch": 0.0, "gimbal_yaw": 0.0},
            timeout=0.5,
        )
    except Exception:
        pass


# ── EGSE thread (sensor frames out, command frames in) ───────────────────────
def egse_thread(master_fd: int, cfg: dict, use_isaac: bool):
    """
    Writes sensor frames at loop.rate_hz, reads command frames, applies throttle.
    Mirrors bbb/egse/run_egse.py but talks to the pty master fd.
    """
    global _last_throttle
    rate_hz  = cfg["loop"]["rate_hz"]
    interval = 1.0 / rate_hz
    base_url = cfg["isaac"]["base_url"]
    model    = SensorModel()
    seq      = 0
    buf      = b""
    t_start  = time.monotonic()

    # os.read/write on the master fd directly
    import os, select

    while not _stop.is_set():
        t0 = time.monotonic()

        with _lock:
            z  = _telem["z"]
            vz = _telem["vz"]
            ok = _telem["ok"]

        alt_mm  = int(z  * 1000)
        vz_cms  = int(vz * 100)
        status  = STATUS_DATA_READY if ok else 0

        model.altitude_mm    = alt_mm
        model.velocity_z_cms = vz_cms

        sf = SensorFrame(
            seq=seq & 0xFFFF,
            timestamp_ms=int((time.monotonic() - t_start) * 1000) & 0xFFFFFFFF,
            altitude_mm=alt_mm,
            velocity_z_cms=vz_cms,
            accel_x_mg=0, accel_y_mg=0, accel_z_mg=-372,  # Mars g ≈ 372 milli-g
            gyro_x_ddps=0, gyro_y_ddps=0, gyro_z_ddps=0,
            status=status,
            fault_code=0,
        )
        try:
            os.write(master_fd, pack_sensor_frame(sf))
        except OSError:
            break

        # Non-blocking read for command frames
        rlist, _, _ = select.select([master_fd], [], [], 0)
        if rlist:
            try:
                buf += os.read(master_fd, CMD_FRAME_SIZE * 4)
            except OSError:
                break

        while True:
            idx = find_magic(buf, CMD_MAGIC)
            if idx < 0 or len(buf) - idx < CMD_FRAME_SIZE:
                if idx < 0 and len(buf) > 2:
                    buf = buf[-2:]
                break
            cf = unpack_command_frame(buf[idx: idx + CMD_FRAME_SIZE])
            buf = buf[idx + CMD_FRAME_SIZE:]
            if cf is None:
                continue
            with _lock:
                _last_throttle = cf.throttle
            if use_isaac:
                isaac_commander(base_url, cf.throttle)
            entry = {
                "t":        round(time.monotonic() - t_start, 4),
                "seq":      cf.seq,
                "alt_m":    alt_mm / 1000.0,
                "vz_mps":   vz_cms / 100.0,
                "throttle": round(cf.throttle, 4),
                "engine":   bool(cf.flags & FLAGS_ENGINE_ENABLE),
                "abort":    bool(cf.flags & FLAGS_ABORT),
            }
            _log_entries.append(entry)

            # Terminal status line
            if seq % 50 == 0:
                src = "Isaac" if use_isaac else "sim"
                print(f"[egse→{src}] seq={seq:5d}  alt={alt_mm/1000:7.1f}m  "
                      f"vz={vz_cms/100:+6.2f}m/s  thr={cf.throttle:.3f}  "
                      f"eng={'ON ' if cf.flags & FLAGS_ENGINE_ENABLE else 'OFF'}",
                      flush=True)

            if z <= 2.0 and abs(vz) < 3.0:
                verdict = "PASS ✓" if abs(vz) < 2.0 else "FAIL ✗"
                print(f"\n[egse] TOUCHDOWN  vz={vz:.2f} m/s  {verdict}", flush=True)
                _stop.set()

        seq += 1
        elapsed = time.monotonic() - t0
        sleep_t = interval - elapsed
        if sleep_t > 0:
            time.sleep(sleep_t)


# ── FSW thread (sensor frames in, command frames out) ─────────────────────────
def fsw_thread(slave_dev: str, cfg: dict):
    """Runs the Jetson FSW against the slave end of the pty pair."""
    import subprocess, os
    fsw_script = Path(__file__).parent / "fsw_main.py"
    log_path   = Path(cfg.get("_log", "/tmp/fsw_hil.jsonl"))
    cmd = [
        sys.executable, str(fsw_script),
        "--config", cfg["_config_path"],
        "--uart",   slave_dev,
        "--log",    str(log_path),
    ]
    proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
    _stop.wait()
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()
    cfg  = load_config(args.config)
    cfg["_config_path"] = args.config
    cfg["_log"]         = args.log

    Path(args.log).parent.mkdir(parents=True, exist_ok=True)

    # Create pty pair: master ↔ slave
    master_fd, slave_fd = pty.openpty()
    slave_dev = os.ttyname(slave_fd)
    os.close(slave_fd)   # FSW subprocess will open by name
    print(f"[hil] pty pair: master_fd={master_fd}  slave={slave_dev}", flush=True)

    use_isaac = not args.no_isaac
    base_url  = cfg["isaac"]["base_url"]

    # Start Isaac truth source
    if use_isaac:
        print(f"[hil] Connecting to Isaac at {base_url} …", flush=True)
        t = threading.Thread(target=isaac_poller,
                             args=(base_url, cfg["isaac"]["poll_hz"]), daemon=True)
        t.start()
        time.sleep(0.5)
        with _lock:
            ok = _telem["ok"]
        if ok:
            print(f"[hil] Isaac reachable — initial alt={_telem['z']:.1f}m", flush=True)
        else:
            print("[hil] Isaac unreachable — falling back to local sim", flush=True)
            use_isaac = False

    if not use_isaac:
        print(f"[hil] Using built-in free-fall sim — alt={args.start_alt}m  vz={args.start_vz}m/s",
              flush=True)
        # Pre-arm throttle so freefall_sim brakes immediately on high-speed entry
        # before the first FSW command frame arrives over the pty.
        if args.start_vz < -3.0:
            global _last_throttle
            _last_throttle = 0.85
        t = threading.Thread(target=freefall_sim, daemon=True)
        t.start()
        with _lock:
            _telem["z"]  = args.start_alt
            _telem["vz"] = args.start_vz
            _telem["ok"] = True

    # Start EGSE thread (pty master side)
    t_egse = threading.Thread(target=egse_thread,
                              args=(master_fd, cfg, use_isaac), daemon=True)
    t_egse.start()

    # Start FSW subprocess (pty slave side)
    t_fsw = threading.Thread(target=fsw_thread,
                             args=(slave_dev, cfg), daemon=True)
    t_fsw.start()

    print(f"[hil] HIL loop running — duration={args.duration}s  "
          f"(Ctrl-C or wait for touchdown)", flush=True)
    print(f"[hil] {'Isaac physics' if use_isaac else 'Built-in sim'}  "
          f"loop={cfg['loop']['rate_hz']} Hz", flush=True)
    print()

    deadline = time.monotonic() + args.duration
    try:
        while not _stop.is_set() and time.monotonic() < deadline:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[hil] Interrupted.", flush=True)

    _stop.set()
    time.sleep(1)

    # Write log
    log_path = Path(args.log)
    with open(log_path, "w") as f:
        for entry in _log_entries:
            f.write(json.dumps(entry) + "\n")

    # Summary
    if _log_entries:
        last = _log_entries[-1]
        soft = last.get("landed") or abs(last.get("vz_mps", 99)) < 2.0 and last.get("alt_m", 99) < 2.0
        print(f"\n[hil] Run complete — {len(_log_entries)} frames logged → {log_path}")
        print(f"[hil] Final: alt={last['alt_m']:.1f}m  vz={last['vz_mps']:.2f}m/s  "
              f"thr={last['throttle']:.3f}")
        print(f"[hil] Soft touchdown: {'PASS ✓' if soft else 'FAIL ✗  (tune gains in config.yaml)'}")

        report = {
            "run_id": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": "isaac" if (not args.no_isaac) else "freefall_sim",
            "frames_logged": len(_log_entries),
            "final_alt_m": last["alt_m"],
            "final_vz_mps": last["vz_mps"],
            "soft_touchdown": bool(soft),
            "tests": [
                {
                    "id": "HIL-LAND-01",
                    "requirement": "soft touchdown |vz| < 2 m/s",
                    "status": "PASS" if soft else "FAIL",
                    "evidence": f"final vz={last['vz_mps']:.2f} m/s",
                }
            ],
        }
        rpt_path = log_path.with_suffix("").with_suffix(".report.json")
        with open(rpt_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"[hil] Report → {rpt_path}")

    os.close(master_fd)


if __name__ == "__main__":
    main()
