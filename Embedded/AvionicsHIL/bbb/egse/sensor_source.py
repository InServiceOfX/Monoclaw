"""
Serializes sensor frames to the UART at the configured loop rate.
Reads from SensorModel, applies fault injection, packs the 32-byte frame,
writes to the shared serial port.
"""
import threading
import time

import serial

from sensor_model import (
    SensorModel,
    altitude_to_wire, velocity_z_to_wire, accel_to_wire, gyro_to_wire,
)
from fault_injector import FaultInjector
from frames import SensorFrame, pack_sensor_frame, STATUS_DATA_READY, STATUS_FAULT_ACTIVE


class SensorSource:
    def __init__(
        self,
        model: SensorModel,
        injector: FaultInjector,
        port: serial.Serial,
        rate_hz: float = 50.0,
    ):
        self._model    = model
        self._injector = injector
        self._port     = port
        self._interval = 1.0 / rate_hz
        self._running  = False
        self._thread   = None

        self.frames_sent  = 0
        self.frames_dropped = 0  # suppressed by fault injector (DROPOUT)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name='sensor_source'
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def _loop(self) -> None:
        seq = 0
        loop_start = time.monotonic()

        while self._running:
            t0 = time.monotonic()
            timestamp_ms = int((t0 - loop_start) * 1000.0) & 0xFFFFFFFF

            state = self._model.snapshot()

            status = 0
            if state['data_ready']:
                status |= STATUS_DATA_READY
            if state['fault_active']:
                status |= STATUS_FAULT_ACTIVE

            frame = SensorFrame(
                seq=seq & 0xFFFF,
                timestamp_ms=timestamp_ms,
                altitude_mm=altitude_to_wire(state['altitude_m']),
                velocity_z_cms=velocity_z_to_wire(state['velocity_z_mps']),
                accel_x_mg=accel_to_wire(state['accel_x_mps2']),
                accel_y_mg=accel_to_wire(state['accel_y_mps2']),
                accel_z_mg=accel_to_wire(state['accel_z_mps2']),
                gyro_x_ddps=gyro_to_wire(state['gyro_x_radps']),
                gyro_y_ddps=gyro_to_wire(state['gyro_y_radps']),
                gyro_z_ddps=gyro_to_wire(state['gyro_z_radps']),
                status=status,
                fault_code=state['fault_code'],
            )

            frame = self._injector.apply(frame)
            if frame is not None:
                try:
                    self._port.write(pack_sensor_frame(frame))
                    self.frames_sent += 1
                except serial.SerialException as exc:
                    print(f"[sensor_source] UART write error: {exc}")
            else:
                self.frames_dropped += 1

            seq += 1
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, self._interval - elapsed))
