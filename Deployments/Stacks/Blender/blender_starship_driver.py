#!/usr/bin/env python3
"""
blender_starship_driver.py — drive the imported Starship object from live
Isaac Sim telemetry and render it in real-time EEVEE on the host display GPU
(GTX 980 Ti). Runs inside Blender:

    blender --python blender_starship_driver.py

The script (1) imports starship.usd if not already present, (2) starts a
background thread that reads telemetry, and (3) registers a Blender timer that
applies the latest pose to the Starship object each frame. bpy is only touched
from the timer (main thread); the producer thread never calls bpy.

Telemetry source — env TELEM_SOURCE:
  http  (default) Poll  http://$TELEM_HTTP_HOST:$TELEM_HTTP_PORT/telemetry/latest
                  Non-invasive: Isaac always serves this and it does NOT consume
                  the UDP stream the Jetson HIL leg may be using.
  udp             Bind 0.0.0.0:$TELEM_UDP_PORT and unpack the 64-byte
                  little-endian datagram ('<Id13f') Isaac sends when
                  TELEMETRY_UDP_HOST is set on the Isaac container. Lowest latency,
                  but it's point-to-point — don't fight the Jetson for it.

Coordinate frames:
  Isaac/USD is now Z-up (ROS REP-103) and so is Blender, so the import needs no
  axis conversion — the "World" root empty is identity and the Starship object
  sits directly in world Z-up coords. We set its pose straight from telemetry
  (identity mapping), no axis math. Sanity check: a USD identity quaternion is
  nose-up; the vehicle points +Z and altitude is the Z coordinate.
"""

import bpy
import os
import json
import socket
import struct
import threading
import time
from urllib.request import urlopen

# ── Config (env-driven; matches docker-compose.yml) ───────────────────────────
USD_PATH   = os.environ.get("STARSHIP_USD", "/work/starship/starship.usd")
OBJ_HINT   = os.environ.get("STARSHIP_OBJECT", "Starship")
SOURCE     = os.environ.get("TELEM_SOURCE", "http").lower()
HTTP_URL   = (f"http://{os.environ.get('TELEM_HTTP_HOST', '127.0.0.1')}"
              f":{os.environ.get('TELEM_HTTP_PORT', '8282')}/telemetry/latest")
UDP_PORT   = int(os.environ.get("TELEM_UDP_PORT", "50505"))
FPS        = float(os.environ.get("DRIVER_FPS", "60"))

# 64-byte packet from enable_ros2_bridge.py:
#   uint32 seq, float64 sim_time, f32 x y z, f32 qw qx qy qz, f32 vx vy vz, f32 wx wy wz
UDP_FMT  = "<Id13f"
UDP_SIZE = struct.calcsize(UDP_FMT)  # 64


# ── Import the scene if it isn't loaded yet ───────────────────────────────────
def _find_ship():
    for obj in bpy.data.objects:
        if OBJ_HINT.lower() in obj.name.lower() and obj.type in {"MESH", "EMPTY"}:
            return obj
    return None


if _find_ship() is None and os.path.isfile(USD_PATH):
    try:
        bpy.ops.wm.usd_import(filepath=USD_PATH)
        print(f"[driver] imported {USD_PATH}", flush=True)
    except Exception as exc:
        print(f"[driver] USD import failed: {exc}", flush=True)

ship = _find_ship()
if ship is None:
    raise RuntimeError(
        f"No object matching '{OBJ_HINT}'. Set STARSHIP_OBJECT or check the USD import."
    )
ship.rotation_mode = "QUATERNION"

# Best-effort: put a 3D viewport into rendered EEVEE so you see it immediately.
try:
    bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.shading.type = "RENDERED"
except Exception as exc:
    print(f"[driver] viewport setup skipped ({exc}) — set shading to Rendered manually",
          flush=True)


# ── Telemetry producer (background thread; never touches bpy) ─────────────────
_latest = None          # (x, y, z, qw, qx, qy, qz) in USD Y-up frame
_lock = threading.Lock()


def _produce():
    global _latest
    if SOURCE == "udp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", UDP_PORT))
        print(f"[driver] UDP telemetry on :{UDP_PORT}", flush=True)
        while True:
            try:
                buf, _ = sock.recvfrom(4096)
                if len(buf) >= UDP_SIZE:
                    v = struct.unpack(UDP_FMT, buf[:UDP_SIZE])
                    with _lock:
                        _latest = (v[2], v[3], v[4], v[5], v[6], v[7], v[8])
            except OSError:
                pass
    else:
        period = 1.0 / FPS
        print(f"[driver] HTTP telemetry poll {HTTP_URL}", flush=True)
        while True:
            try:
                with urlopen(HTTP_URL, timeout=0.2) as resp:
                    d = json.loads(resp.read().decode())
                if d.get("prim_valid", True):
                    with _lock:
                        _latest = (d["x"], d["y"], d["z"],
                                   d["qw"], d["qx"], d["qy"], d["qz"])
            except Exception:
                pass
            time.sleep(period)


threading.Thread(target=_produce, daemon=True, name="telem").start()


# ── Apply latest pose (Blender main thread) ───────────────────────────────────
def _apply(pose):
    x, y, z, qw, qx, qy, qz = pose
    # Blender's USD importer parents the scene under a "World" empty rotated +90deg
    # about X to convert Y-up->Z-up. The Starship object therefore lives in the USD
    # (Y-up) frame, and its parent does the conversion — so we set its LOCAL pose
    # straight from telemetry (identity), no axis math here.
    ship.location = (x, y, z)
    ship.rotation_quaternion = (qw, qx, qy, qz)


def _tick():
    with _lock:
        pose = _latest
    if pose is not None:
        _apply(pose)
    return 1.0 / FPS


bpy.app.timers.register(_tick, first_interval=0.5)
print("[driver] running — if you don't see it, set a 3D viewport to 'Rendered' (EEVEE)",
      flush=True)
