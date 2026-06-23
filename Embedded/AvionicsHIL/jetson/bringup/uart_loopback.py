#!/usr/bin/env python3
"""
UART loopback self-test (TASK-01, Step 3).

HARDWARE SETUP REQUIRED:
    Jumper Jetson 40-pin  pin 8 (UART TX)  →  pin 10 (UART RX).
    Do NOT connect to the BBB yet.  This test proves the Jetson UART
    works in isolation before wiring to external hardware.

Run ON THE JETSON (from this directory):
    python3 uart_loopback.py [--port /dev/ttyTHS1] [--baud 115200]

Exit code 0 = PASS, 1 = FAIL.
"""
import argparse
import sys
import time

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: uv pip install pyserial")
    sys.exit(1)


PATTERN_SIZE   = 256    # bytes to send in each burst
BURST_COUNT    = 4      # number of bursts
READ_TIMEOUT_S = 1.0    # wait up to this long for echo


def run_loopback(port_dev: str, baud: int) -> bool:
    print(f"[loopback] Opening {port_dev} @ {baud} baud")
    try:
        port = serial.Serial(port_dev, baudrate=baud, timeout=READ_TIMEOUT_S)
    except serial.SerialException as exc:
        print(f"[loopback] FAIL — cannot open {port_dev}: {exc}")
        print("  Verify the UART device name with:  ls /dev/ttyTHS*")
        return False

    port.reset_input_buffer()
    port.reset_output_buffer()

    total_sent = 0
    total_recv = 0
    passed = True

    for burst in range(BURST_COUNT):
        pattern = bytes(range(PATTERN_SIZE))
        port.write(pattern)
        total_sent += len(pattern)

        # Read back with timeout
        received = b''
        deadline = time.monotonic() + READ_TIMEOUT_S
        while len(received) < len(pattern) and time.monotonic() < deadline:
            chunk = port.read(len(pattern) - len(received))
            received += chunk

        total_recv += len(received)

        if received == pattern:
            print(f"[loopback] Burst {burst + 1}/{BURST_COUNT}: {len(pattern)} bytes MATCH")
        else:
            passed = False
            print(f"[loopback] Burst {burst + 1}/{BURST_COUNT}: MISMATCH — "
                  f"sent {len(pattern)} B, got {len(received)} B")
            # Show first diff
            for i, (s, r) in enumerate(zip(pattern, received)):
                if s != r:
                    print(f"  First diff at byte {i}: sent 0x{s:02X} got 0x{r:02X}")
                    break
            if len(received) < len(pattern):
                print(f"  Truncated: missing {len(pattern) - len(received)} bytes")
                print("  Check: is the TX→RX jumper on pins 8 and 10?")

    port.close()

    print(f"\n[loopback] Total: sent={total_sent} B  received={total_recv} B  "
          f"result={'PASS' if passed else 'FAIL'}")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description='Jetson UART loopback self-test')
    parser.add_argument('--port', default='/dev/ttyTHS1',
                        help='UART device (default: /dev/ttyTHS1 — VERIFY first)')
    parser.add_argument('--baud', type=int, default=115200)
    args = parser.parse_args()

    print(f"[loopback] UART loopback test")
    print(f"[loopback] SETUP: jumper Jetson 40-pin pin 8 (TX) → pin 10 (RX)")
    print(f"[loopback] Press Ctrl-C to abort if TX→RX is NOT jumpered\n")

    passed = run_loopback(args.port, args.baud)
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
