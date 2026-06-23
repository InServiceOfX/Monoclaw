"""
Wire frame pack/unpack + CRC-16/CCITT-FALSE.
Implements INTERFACES.md §3 (sensor frame, 32 B) and §4 (command frame, 16 B).
All multi-byte fields are little-endian.

CRC-16/CCITT-FALSE: poly=0x1021, init=0xFFFF, non-reflected, XorOut=0x0000.
Check value (CRC of b"123456789") = 0x29B1.
"""
import struct
from dataclasses import dataclass
from typing import Optional

SENSOR_MAGIC = (0xA5, 0x5A)
CMD_MAGIC    = (0x5A, 0xA5)
SENSOR_FRAME_SIZE = 32
CMD_FRAME_SIZE    = 16

STATUS_DATA_READY  = 0x01
STATUS_FAULT_ACTIVE = 0x02

FLAGS_ENGINE_ENABLE = 0x0001
FLAGS_ABORT         = 0x0002

# Struct formats over the non-CRC payload bytes (little-endian, no padding).
# Sensor: 30 bytes (bytes 0-29); CRC appended separately as '<H'.
#   BB  H  I  i  h  H  h h h  h h h  B B
#   ^   ^  ^  ^  ^  ^  ^^^^^^^  ^^^^^^^  ^ ^
#   mag seq ts alt vz res  accel   gyro  st fc
_SENSOR_BODY_FMT = '<BBHIihHhhhhhhBB'  # 30 bytes

# Command: 14 bytes (bytes 0-13); CRC appended separately as '<H'.
#   BB  H  f  h  h  H
#   mag seq th gp gy fl
_CMD_BODY_FMT = '<BBHfhhH'  # 14 bytes


def crc16_ccitt_false(data: bytes) -> int:
    """CRC-16/CCITT-FALSE over `data`. Returns 16-bit integer."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


@dataclass
class SensorFrame:
    seq: int             # u16 — increments each frame, wraps
    timestamp_ms: int    # u32 — BBB monotonic ms since loop start
    altitude_mm: int     # i32 — metres × 1000
    velocity_z_cms: int  # i16 — m/s × 100
    accel_x_mg: int      # i16 — m/s² / 9.80665 × 1000
    accel_y_mg: int      # i16
    accel_z_mg: int      # i16
    gyro_x_ddps: int     # i16 — deg/s × 10
    gyro_y_ddps: int     # i16
    gyro_z_ddps: int     # i16
    status: int          # u8  — bit0 data_ready, bit1 fault_active
    fault_code: int      # u8  — 0=NONE; see INTERFACES §6


@dataclass
class CommandFrame:
    seq: int               # u16 — echo of sensor frame seq
    throttle: float        # f32 — 0.0–1.0
    gimbal_pitch_mrad: int # i16 — milliradians
    gimbal_yaw_mrad: int   # i16 — milliradians
    flags: int             # u16 — bit0 engine_enable, bit1 abort


def pack_sensor_frame(frame: SensorFrame) -> bytes:
    """Serialize a SensorFrame to exactly 32 bytes."""
    body = struct.pack(
        _SENSOR_BODY_FMT,
        SENSOR_MAGIC[0], SENSOR_MAGIC[1],
        frame.seq & 0xFFFF,
        frame.timestamp_ms & 0xFFFFFFFF,
        frame.altitude_mm,
        frame.velocity_z_cms,
        0,  # reserved0
        frame.accel_x_mg,
        frame.accel_y_mg,
        frame.accel_z_mg,
        frame.gyro_x_ddps,
        frame.gyro_y_ddps,
        frame.gyro_z_ddps,
        frame.status & 0xFF,
        frame.fault_code & 0xFF,
    )
    assert len(body) == 30
    crc = crc16_ccitt_false(body)
    return body + struct.pack('<H', crc)


def unpack_sensor_frame(data: bytes) -> Optional[SensorFrame]:
    """Deserialize 32 bytes into a SensorFrame; returns None on bad magic or CRC."""
    if len(data) < SENSOR_FRAME_SIZE:
        return None
    if data[0] != SENSOR_MAGIC[0] or data[1] != SENSOR_MAGIC[1]:
        return None
    computed_crc = crc16_ccitt_false(data[:30])
    wire_crc = struct.unpack_from('<H', data, 30)[0]
    if computed_crc != wire_crc:
        return None
    fields = struct.unpack(_SENSOR_BODY_FMT, data[:30])
    # fields: mag0 mag1 seq ts alt vz res ax ay az gx gy gz status fault_code
    _, _, seq, timestamp_ms, altitude_mm, velocity_z_cms, _res, \
        ax, ay, az, gx, gy, gz, status, fault_code = fields
    return SensorFrame(
        seq=seq,
        timestamp_ms=timestamp_ms,
        altitude_mm=altitude_mm,
        velocity_z_cms=velocity_z_cms,
        accel_x_mg=ax, accel_y_mg=ay, accel_z_mg=az,
        gyro_x_ddps=gx, gyro_y_ddps=gy, gyro_z_ddps=gz,
        status=status,
        fault_code=fault_code,
    )


def pack_command_frame(frame: CommandFrame) -> bytes:
    """Serialize a CommandFrame to exactly 16 bytes."""
    body = struct.pack(
        _CMD_BODY_FMT,
        CMD_MAGIC[0], CMD_MAGIC[1],
        frame.seq & 0xFFFF,
        float(frame.throttle),
        frame.gimbal_pitch_mrad,
        frame.gimbal_yaw_mrad,
        frame.flags & 0xFFFF,
    )
    assert len(body) == 14
    crc = crc16_ccitt_false(body)
    return body + struct.pack('<H', crc)


def unpack_command_frame(data: bytes) -> Optional[CommandFrame]:
    """Deserialize 16 bytes into a CommandFrame; returns None on bad magic or CRC."""
    if len(data) < CMD_FRAME_SIZE:
        return None
    if data[0] != CMD_MAGIC[0] or data[1] != CMD_MAGIC[1]:
        return None
    computed_crc = crc16_ccitt_false(data[:14])
    wire_crc = struct.unpack_from('<H', data, 14)[0]
    if computed_crc != wire_crc:
        return None
    _, _, seq, throttle, gimbal_pitch, gimbal_yaw, flags = struct.unpack(_CMD_BODY_FMT, data[:14])
    return CommandFrame(
        seq=seq,
        throttle=throttle,
        gimbal_pitch_mrad=gimbal_pitch,
        gimbal_yaw_mrad=gimbal_yaw,
        flags=flags,
    )


def find_magic(buffer: bytes, magic: tuple) -> int:
    """Return index of first occurrence of magic bytes in buffer, or -1."""
    for i in range(len(buffer) - 1):
        if buffer[i] == magic[0] and buffer[i + 1] == magic[1]:
            return i
    return -1


if __name__ == "__main__":
    # Round-trip self-test — run with: python3 frames.py
    print("CRC check: 0x29B1 ==", hex(crc16_ccitt_false(b"123456789")))
    assert crc16_ccitt_false(b"123456789") == 0x29B1, "CRC implementation wrong"

    sf = SensorFrame(
        seq=42, timestamp_ms=12345,
        altitude_mm=500_000, velocity_z_cms=-500,
        accel_x_mg=0, accel_y_mg=0, accel_z_mg=-1000,
        gyro_x_ddps=0, gyro_y_ddps=0, gyro_z_ddps=0,
        status=STATUS_DATA_READY, fault_code=0,
    )
    packed = pack_sensor_frame(sf)
    assert len(packed) == SENSOR_FRAME_SIZE, f"size={len(packed)}"
    unpacked = unpack_sensor_frame(packed)
    assert unpacked is not None
    assert unpacked.seq == sf.seq
    assert unpacked.altitude_mm == sf.altitude_mm
    assert unpacked.velocity_z_cms == sf.velocity_z_cms
    print(f"Sensor frame round-trip PASS ({SENSOR_FRAME_SIZE} bytes)")

    cf = CommandFrame(seq=42, throttle=0.75, gimbal_pitch_mrad=50, gimbal_yaw_mrad=-30,
                      flags=FLAGS_ENGINE_ENABLE)
    packed_cmd = pack_command_frame(cf)
    assert len(packed_cmd) == CMD_FRAME_SIZE, f"size={len(packed_cmd)}"
    unpacked_cmd = unpack_command_frame(packed_cmd)
    assert unpacked_cmd is not None
    assert unpacked_cmd.seq == cf.seq
    assert abs(unpacked_cmd.throttle - cf.throttle) < 1e-5
    assert unpacked_cmd.gimbal_pitch_mrad == cf.gimbal_pitch_mrad
    print(f"Command frame round-trip PASS ({CMD_FRAME_SIZE} bytes)")

    # Corrupt CRC → None
    bad = bytearray(packed)
    bad[30] ^= 0xFF
    assert unpack_sensor_frame(bytes(bad)) is None
    print("Bad CRC rejection PASS")

    print("All tests passed.")
