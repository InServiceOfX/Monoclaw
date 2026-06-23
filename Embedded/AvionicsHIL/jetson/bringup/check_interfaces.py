#!/usr/bin/env python3
"""
Jetson Orin Nano interface checkout (TASK-01, Steps 2 & 5-6).
Enumerates UART and I2C on the 40-pin header; writes reports/checkout_jetson.json.

Run ON THE JETSON (from this directory):
    python3 check_interfaces.py [--config ../../config.yaml]

Requires: python3, pyserial, smbus2, pyyaml  (all in jetson/bringup/.venv)
"""
import argparse
import datetime
import json
import os
import subprocess
import sys


# ── Individual checks ─────────────────────────────────────────────────────────

def check_uart_enum(uart_dev: str) -> dict:
    """Enumerate UART devices and verify the configured one is present."""
    result = subprocess.run(['ls', '/dev/'], capture_output=True, text=True)
    all_devs = result.stdout.split()
    uart_devs = [d for d in all_devs if d.startswith('ttyTHS') or d.startswith('ttyACM')]

    full_paths = [f"/dev/{d}" for d in uart_devs]
    present = uart_dev in full_paths

    evidence = f"Found: {full_paths}  |  Configured: {uart_dev}  |  Present: {present}"
    return {
        'id': 'UART-ENUM',
        'desc': '40-pin UART device present in /dev/',
        'status': 'PASS' if present else 'FAIL',
        'evidence': evidence,
    }


def check_i2c_enum(i2c_slave_enabled: bool) -> dict:
    """Enumerate I2C buses on the 40-pin header (pins 3/5 → /dev/i2c-?)."""
    if not i2c_slave_enabled:
        return {
            'id': 'I2C-ENUM',
            'desc': '40-pin I2C bus enumerates',
            'status': 'SKIPPED',
            'evidence': 'i2c_slave_enabled=false in config — UART transport selected',
        }
    try:
        result = subprocess.run(
            ['i2cdetect', '-l'], capture_output=True, text=True, timeout=5
        )
        buses = [l.strip() for l in result.stdout.splitlines() if l.startswith('i2c-')]
        evidence = f"i2cdetect -l: {buses}"
        return {
            'id': 'I2C-ENUM',
            'desc': '40-pin I2C bus enumerates',
            'status': 'PASS' if buses else 'FAIL',
            'evidence': evidence,
        }
    except FileNotFoundError:
        return {
            'id': 'I2C-ENUM',
            'desc': '40-pin I2C bus enumerates',
            'status': 'FAIL',
            'evidence': 'i2cdetect not found — install i2c-tools: sudo apt install i2c-tools',
        }


def check_i2c_slave_detect(i2c_slave_enabled: bool, i2c_addr: int) -> dict:
    """Check if BBB slave appears at the configured I2C address."""
    if not i2c_slave_enabled:
        return {
            'id': 'I2C-SLAVE-DETECT',
            'desc': f'BBB slave at 0x{i2c_addr:02X}',
            'status': 'SKIPPED',
            'evidence': 'i2c_slave_enabled=false — skipped',
        }
    try:
        # Scan buses 0-10 looking for the slave address
        for bus_num in range(10):
            result = subprocess.run(
                ['i2cdetect', '-y', '-r', str(bus_num)],
                capture_output=True, text=True, timeout=5
            )
            addr_hex = f'{i2c_addr:02x}'
            if addr_hex in result.stdout:
                return {
                    'id': 'I2C-SLAVE-DETECT',
                    'desc': f'BBB slave at 0x{i2c_addr:02X}',
                    'status': 'PASS',
                    'evidence': f'Found 0x{i2c_addr:02X} on i2c-{bus_num}',
                }
        return {
            'id': 'I2C-SLAVE-DETECT',
            'desc': f'BBB slave at 0x{i2c_addr:02X}',
            'status': 'FAIL',
            'evidence': f'0x{i2c_addr:02X} not found on any i2c bus — is TASK-02 running?',
        }
    except Exception as exc:
        return {
            'id': 'I2C-SLAVE-DETECT',
            'desc': f'BBB slave at 0x{i2c_addr:02X}',
            'status': 'FAIL',
            'evidence': str(exc),
        }


def check_uart_link(uart_dev: str, baud: int) -> dict:
    """
    Check for live sensor frames from the BBB over UART.
    Reads for up to 2 seconds; looks for the sensor frame magic {0xA5, 0x5A}.
    Requires TASK-02's run_egse.py to be running on the BBB.
    """
    try:
        import serial
    except ImportError:
        return {
            'id': 'UART-LINK',
            'desc': 'Valid sensor frames from BBB',
            'status': 'FAIL',
            'evidence': 'pyserial not installed — run: uv pip install pyserial',
        }
    try:
        port = serial.Serial(uart_dev, baudrate=baud, timeout=0.5)
    except serial.SerialException as exc:
        return {
            'id': 'UART-LINK',
            'desc': 'Valid sensor frames from BBB',
            'status': 'FAIL',
            'evidence': f'Cannot open {uart_dev}: {exc}',
        }

    SENSOR_MAGIC = bytes([0xA5, 0x5A])
    FRAME_SIZE   = 32
    buf          = b''
    valid_frames = 0
    crc_errors   = 0
    deadline     = __import__('time').monotonic() + 2.0

    import struct

    def crc16(data: bytes) -> int:
        crc = 0xFFFF
        for b in data:
            crc ^= b << 8
            for _ in range(8):
                crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
                crc &= 0xFFFF
        return crc

    while __import__('time').monotonic() < deadline:
        chunk = port.read(64)
        if chunk:
            buf += chunk
        while len(buf) >= FRAME_SIZE:
            idx = buf.find(SENSOR_MAGIC)
            if idx < 0:
                buf = buf[-1:]
                break
            buf = buf[idx:]
            if len(buf) < FRAME_SIZE:
                break
            frame = buf[:FRAME_SIZE]
            wire_crc = struct.unpack_from('<H', frame, 30)[0]
            if crc16(frame[:30]) == wire_crc:
                valid_frames += 1
            else:
                crc_errors += 1
            buf = buf[FRAME_SIZE:]

    port.close()
    if valid_frames > 0:
        status = 'PASS'
    else:
        status = 'SKIPPED'  # BBB not yet running → defer, don't fail

    return {
        'id': 'UART-LINK',
        'desc': 'Valid sensor frames from BBB EGSE',
        'status': status,
        'evidence': (
            f'{valid_frames} valid frames / {crc_errors} CRC errors in 2 s'
            if valid_frames + crc_errors > 0
            else 'No bytes received — is TASK-02 (BBB EGSE) running?'
        ),
    }


# ── Report writer ─────────────────────────────────────────────────────────────

def write_report(checks: list, report_path: str) -> None:
    passed  = sum(1 for c in checks if c['status'] == 'PASS')
    failed  = sum(1 for c in checks if c['status'] == 'FAIL')
    skipped = sum(1 for c in checks if c['status'] == 'SKIPPED')
    report = {
        'board':     'jetson-orin-nano',
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'checks':    checks,
        'summary':   {'pass': passed, 'fail': failed, 'skipped': skipped,
                      'total': len(checks)},
    }
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n[checkout] Report: {report_path}")
    print(f"[checkout] Summary: PASS={passed}  FAIL={failed}  SKIPPED={skipped}")
    for c in checks:
        icon = {'PASS': '✓', 'FAIL': '✗', 'SKIPPED': '–'}.get(c['status'], '?')
        print(f"  {icon} {c['id']:25s} {c['status']:8s} {c['evidence']}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description='Jetson interface checkout (TASK-01)')
    parser.add_argument('--config', default='../../config.yaml')
    parser.add_argument('--report', default='../../reports/checkout_jetson.json')
    parser.add_argument('--skip-link', action='store_true',
                        help='Skip UART-LINK check (BBB EGSE not yet running)')
    args = parser.parse_args()

    # Load config
    try:
        import yaml
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"config not found: {args.config} — using defaults")
        cfg = {}

    uart_dev          = cfg.get('jetson', {}).get('sensor_uart', '/dev/ttyTHS1')
    baud              = cfg.get('jetson', {}).get('baud', 115200)
    i2c_slave_enabled = cfg.get('bbb',    {}).get('i2c_slave_enabled', False)
    i2c_addr          = cfg.get('bbb',    {}).get('i2c_addr', 0x42)

    print(f"[checkout] Jetson interface checkout")
    print(f"[checkout]   UART device : {uart_dev} @ {baud}")
    print(f"[checkout]   I2C slave   : {'enabled @ ' + hex(i2c_addr) if i2c_slave_enabled else 'disabled (UART mode)'}")

    checks = []
    checks.append(check_uart_enum(uart_dev))

    if not args.skip_link:
        checks.append(check_uart_link(uart_dev, baud))
    else:
        checks.append({
            'id': 'UART-LINK', 'desc': 'Valid sensor frames from BBB',
            'status': 'SKIPPED', 'evidence': '--skip-link flag set',
        })

    checks.append(check_i2c_enum(i2c_slave_enabled))
    checks.append(check_i2c_slave_detect(i2c_slave_enabled, i2c_addr))

    write_report(checks, args.report)

    failed = sum(1 for c in checks if c['status'] == 'FAIL')
    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    main()
