"""
Polls Isaac Sim GET /telemetry/latest and writes the result to SensorModel.
Derives acceleration by finite-differencing consecutive velocity samples.
Handles Isaac being unreachable: holds last valid state + clears data_ready.
"""
import threading
import time

import requests

from sensor_model import SensorModel


class TruthBridge:
    def __init__(self, model: SensorModel, base_url: str, poll_hz: float = 100.0):
        self._model         = model
        self._base_url      = base_url.rstrip('/')
        self._poll_interval = 1.0 / poll_hz
        self._running       = False
        self._thread        = None

        # For finite-difference acceleration estimation
        self._prev_vx   = 0.0
        self._prev_vy   = 0.0
        self._prev_vz   = 0.0
        self._prev_time = None

        self._consecutive_failures = 0

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name='truth_bridge'
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def _loop(self) -> None:
        session = requests.Session()
        while self._running:
            t0 = time.monotonic()
            try:
                resp = session.get(
                    f"{self._base_url}/telemetry/latest",
                    timeout=0.1,
                )
                if resp.status_code == 200:
                    self._on_telemetry(resp.json())
                    self._consecutive_failures = 0
                else:
                    self._on_failure(f"HTTP {resp.status_code}")
            except Exception as exc:
                self._on_failure(str(exc))
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, self._poll_interval - elapsed))

    def _on_telemetry(self, data: dict) -> None:
        altitude_m = float(data.get('z', 0.0))
        vx = float(data.get('vx', 0.0))
        vy = float(data.get('vy', 0.0))
        vz = float(data.get('vz', 0.0))

        now = time.monotonic()
        if self._prev_time is not None:
            dt = now - self._prev_time
            if dt > 0.001:
                ax = (vx - self._prev_vx) / dt
                ay = (vy - self._prev_vy) / dt
                az = (vz - self._prev_vz) / dt
            else:
                ax = ay = az = 0.0
        else:
            ax = ay = az = 0.0

        self._prev_vx, self._prev_vy, self._prev_vz = vx, vy, vz
        self._prev_time = now

        self._model.update(
            altitude_m=altitude_m,
            velocity_z_mps=vz,
            accel_xyz_mps2=(ax, ay, az),
            gyro_xyz_radps=(0.0, 0.0, 0.0),  # MVP: quaternion-rate gyro deferred
        )

    def _on_failure(self, reason: str) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures <= 3 or self._consecutive_failures % 100 == 0:
            print(f"[truth_bridge] Isaac unreachable (n={self._consecutive_failures}): {reason}")
        self._model.set_stale()
