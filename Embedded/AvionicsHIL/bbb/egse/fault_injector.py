"""
Fault injector (INTERFACES.md §6).
Inert stub now — TASK-05 fills in the inject/clear implementation.
The apply() method is called by sensor_source before each frame is sent.
"""
import copy
import random
import threading
import time

from sensor_model import SensorModel

FAULT_NONE         = 0
FAULT_STUCK        = 1
FAULT_NAN_ALT      = 2
FAULT_DROPOUT      = 3
FAULT_BITFLIP      = 4
FAULT_OUT_OF_RANGE = 5
FAULT_NOISE        = 6

FAULT_NAMES = {
    FAULT_NONE:         "NONE",
    FAULT_STUCK:        "STUCK",
    FAULT_NAN_ALT:      "NAN_ALT",
    FAULT_DROPOUT:      "DROPOUT",
    FAULT_BITFLIP:      "BITFLIP",
    FAULT_OUT_OF_RANGE: "OUT_OF_RANGE",
    FAULT_NOISE:        "NOISE",
}


class FaultInjector:
    """
    Mutates a SensorFrame copy just before it is serialized.
    Thread-safe: set_fault/clear_fault can be called from any thread.
    """

    def __init__(self, model: SensorModel):
        self._model          = model
        self._lock           = threading.Lock()
        self._active_fault   = FAULT_NONE
        self._dropout_until  = 0.0   # monotonic time; 0 = indefinite
        self._stuck_snapshot = None  # frozen copy for FAULT_STUCK

    # ── Public control API ────────────────────────────────────────────────

    def set_fault(self, fault_code: int, duration_ms: int = 0) -> None:
        """
        Activate a fault.
        duration_ms > 0 is only meaningful for FAULT_DROPOUT
        (how long to suppress frames); 0 = until clear_fault().
        """
        with self._lock:
            self._active_fault   = fault_code
            self._stuck_snapshot = None
            if fault_code == FAULT_DROPOUT and duration_ms > 0:
                self._dropout_until = time.monotonic() + duration_ms / 1000.0
            else:
                self._dropout_until = 0.0
        self._model.set_fault(fault_code)
        print(f"[fault_injector] INJECT {FAULT_NAMES.get(fault_code, fault_code)}"
              f"{f'  duration={duration_ms} ms' if duration_ms else ''}")

    def clear_fault(self) -> None:
        with self._lock:
            self._active_fault   = FAULT_NONE
            self._stuck_snapshot = None
            self._dropout_until  = 0.0
        self._model.clear_fault()
        print("[fault_injector] CLEARED")

    @property
    def active_fault(self) -> int:
        with self._lock:
            return self._active_fault

    # ── Frame mutation ────────────────────────────────────────────────────

    def apply(self, frame):
        """
        Apply the current fault to a SensorFrame copy.
        Returns the (possibly mutated) frame, or None for DROPOUT (suppress send).
        The caller must not use the original frame after calling this.
        """
        with self._lock:
            code    = self._active_fault
            until   = self._dropout_until
            snap    = self._stuck_snapshot

        if code == FAULT_NONE:
            return frame

        frame = copy.copy(frame)
        frame.status    |= 0x02         # set fault_active bit
        frame.fault_code = code

        if code == FAULT_STUCK:
            if snap is None:
                # First call: freeze this frame and return it
                with self._lock:
                    self._stuck_snapshot = copy.copy(frame)
                return frame
            # Subsequent calls: return the frozen values
            frame.altitude_mm    = snap.altitude_mm
            frame.velocity_z_cms = snap.velocity_z_cms
            frame.accel_x_mg     = snap.accel_x_mg
            frame.accel_y_mg     = snap.accel_y_mg
            frame.accel_z_mg     = snap.accel_z_mg
            frame.gyro_x_ddps    = snap.gyro_x_ddps
            frame.gyro_y_ddps    = snap.gyro_y_ddps
            frame.gyro_z_ddps    = snap.gyro_z_ddps

        elif code == FAULT_NAN_ALT:
            frame.altitude_mm = 0x7FFFFFFF  # sentinel "invalid"

        elif code == FAULT_DROPOUT:
            if until == 0.0 or time.monotonic() < until:
                return None  # suppress — do not send this frame

        elif code == FAULT_BITFLIP:
            # Flip a random bit in altitude_mm (bytes 8-11 of the frame).
            # CRC will still be valid (packed from the mutated value) so the FSW
            # must catch it via value-plausibility checks.
            frame.altitude_mm ^= (1 << random.randint(0, 30))

        elif code == FAULT_OUT_OF_RANGE:
            frame.altitude_mm = 1_000_000_000  # 1e6 m — impossible altitude

        elif code == FAULT_NOISE:
            frame.velocity_z_cms = max(-32768, min(32767,
                frame.velocity_z_cms + random.randint(-5000, 5000)))
            frame.accel_z_mg = max(-32768, min(32767,
                frame.accel_z_mg + random.randint(-10000, 10000)))

        return frame
