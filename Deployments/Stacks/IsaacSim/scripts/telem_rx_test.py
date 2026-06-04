#!/usr/bin/env python3
"""
UDP telemetry receiver — local test / TX2i stand-in.

Usage:
    python3 telem_rx_test.py [port]   default port 50505

Packet layout (little-endian, 64 bytes):
    uint32  seq              packet counter
    float64 sim_time         simulation clock (s)
    float32 x, y, z         position (m, USD Y-up)
    float32 qw,qx,qy,qz     orientation quaternion (w first)
    float32 vx,vy,vz        linear velocity (m/s)
    float32 wx,wy,wz        angular velocity (rad/s)
"""
import socket
import struct
import sys
import time

PORT   = int(sys.argv[1]) if len(sys.argv) > 1 else 50505
FMT    = "<Id13f"
EXPECT = struct.calcsize(FMT)  # 64 bytes

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
sock.settimeout(5.0)

print(f"Listening on UDP :{PORT}  (expecting {EXPECT}-byte packets)")
print(f"{'SEQ':>8}  {'SIM_T':>8}  {'Y(m)':>9}  {'Vy(m/s)':>9}  {'ATTITUDE_ERR_DEG':>16}  DROPS")
print("-" * 75)

last_seq = None
t0 = time.monotonic()
count = 0

try:
    while True:
        try:
            data, addr = sock.recvfrom(256)
        except socket.timeout:
            elapsed = time.monotonic() - t0
            print(f"  [timeout after {elapsed:.1f}s — no packet received]")
            break

        if len(data) != EXPECT:
            print(f"  [bad packet: {len(data)} bytes, expected {EXPECT}]")
            continue

        fields = struct.unpack(FMT, data)
        seq, t, x, y, z, qw, qx, qy, qz, vx, vy, vz, wx, wy, wz = fields

        drops = (seq - last_seq - 1) if last_seq is not None else 0
        last_seq = seq
        count += 1

        import math
        att_err = 2.0 * math.degrees(math.acos(min(1.0, abs(qw))))

        print(f"{seq:>8}  {t:>8.4f}  {y:>9.3f}  {vy:>9.4f}  {att_err:>16.2f}  {drops}")

        if count >= 20:
            print(f"\n  Received {count} packets — UDP pipeline confirmed.")
            break

except KeyboardInterrupt:
    pass
finally:
    sock.close()
