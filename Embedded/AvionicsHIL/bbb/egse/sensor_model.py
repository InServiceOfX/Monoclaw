"""
Logical sensor model (INTERFACES.md §1) + fixed-point wire encoding (§2).
truth_bridge writes to this; sensor_source reads and serializes.
"""
import threading
import time

_G_MPS2     = 9.80665      # 1 g in m/s²
_RAD_TO_DEG = 57.29577951308232


class SensorModel:
    """Thread-safe container for current vehicle sensor state."""

    def __init__(self):
        self._lock = threading.Lock()
        self._altitude_m       = 0.0
        self._velocity_z_mps   = 0.0
        self._accel_x_mps2     = 0.0
        self._accel_y_mps2     = 0.0
        self._accel_z_mps2     = 0.0
        self._gyro_x_radps     = 0.0
        self._gyro_y_radps     = 0.0
        self._gyro_z_radps     = 0.0
        self._data_ready       = False
        self._fault_active     = False
        self._fault_code       = 0
        self._updated_at       = 0.0

    def update(
        self,
        altitude_m: float,
        velocity_z_mps: float,
        accel_xyz_mps2: tuple = (0.0, 0.0, 0.0),
        gyro_xyz_radps: tuple = (0.0, 0.0, 0.0),
    ) -> None:
        with self._lock:
            self._altitude_m     = altitude_m
            self._velocity_z_mps = velocity_z_mps
            self._accel_x_mps2   = accel_xyz_mps2[0]
            self._accel_y_mps2   = accel_xyz_mps2[1]
            self._accel_z_mps2   = accel_xyz_mps2[2]
            self._gyro_x_radps   = gyro_xyz_radps[0]
            self._gyro_y_radps   = gyro_xyz_radps[1]
            self._gyro_z_radps   = gyro_xyz_radps[2]
            self._data_ready     = True
            self._updated_at     = time.monotonic()

    def set_stale(self) -> None:
        """Called when Isaac is unreachable; receiver should hold last + clear data_ready."""
        with self._lock:
            self._data_ready = False

    def set_fault(self, fault_code: int) -> None:
        with self._lock:
            self._fault_active = fault_code != 0
            self._fault_code   = fault_code

    def clear_fault(self) -> None:
        with self._lock:
            self._fault_active = False
            self._fault_code   = 0

    def snapshot(self) -> dict:
        """Return a copy of the current state as a plain dict."""
        with self._lock:
            return {
                'altitude_m':     self._altitude_m,
                'velocity_z_mps': self._velocity_z_mps,
                'accel_x_mps2':   self._accel_x_mps2,
                'accel_y_mps2':   self._accel_y_mps2,
                'accel_z_mps2':   self._accel_z_mps2,
                'gyro_x_radps':   self._gyro_x_radps,
                'gyro_y_radps':   self._gyro_y_radps,
                'gyro_z_radps':   self._gyro_z_radps,
                'data_ready':     self._data_ready,
                'fault_active':   self._fault_active,
                'fault_code':     self._fault_code,
                'updated_at':     self._updated_at,
            }


# ── Fixed-point encoding (INTERFACES.md §2) ──────────────────────────────────
# Each function clamps to the wire type's integer range.

def altitude_to_wire(altitude_m: float) -> int:
    """metres → millimetres (i32)."""
    val = round(altitude_m * 1000.0)
    return max(-2_147_483_648, min(2_147_483_647, val))


def velocity_z_to_wire(velocity_mps: float) -> int:
    """m/s → cm/s (i16)."""
    val = round(velocity_mps * 100.0)
    return max(-32768, min(32767, val))


def accel_to_wire(accel_mps2: float) -> int:
    """m/s² → milli-g (i16).  1 g = 9.80665 m/s²."""
    val = round(accel_mps2 / _G_MPS2 * 1000.0)
    return max(-32768, min(32767, val))


def gyro_to_wire(gyro_radps: float) -> int:
    """rad/s → deci-deg/s (i16).  1 rad/s = 57.296 deg/s → 572.96 ddps."""
    val = round(gyro_radps * _RAD_TO_DEG * 10.0)
    return max(-32768, min(32767, val))


def wire_altitude_to_si(altitude_mm: int) -> float:
    """millimetres → metres."""
    return altitude_mm / 1000.0


def wire_velocity_z_to_si(velocity_cms: int) -> float:
    """cm/s → m/s."""
    return velocity_cms / 100.0


def wire_accel_to_si(accel_mg: int) -> float:
    """milli-g → m/s²."""
    return accel_mg / 1000.0 * _G_MPS2


def wire_gyro_to_si(gyro_ddps: int) -> float:
    """deci-deg/s → rad/s."""
    return gyro_ddps / 10.0 / _RAD_TO_DEG
