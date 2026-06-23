"""
Reads 16-byte command frames from the Jetson over UART, relays them to Isaac.
Resyncs on CMD_MAGIC {0x5A, 0xA5}; rejects bad CRC; maps throttle/gimbal to
POST /starship/command {"action":"throttle", ...}.
"""
import threading
import time

import requests
import serial

from frames import (
    CommandFrame, unpack_command_frame,
    CMD_MAGIC, CMD_FRAME_SIZE, FLAGS_ABORT,
)


class ActuatorSink:
    def __init__(self, port: serial.Serial, isaac_base_url: str):
        self._port     = port
        self._base_url = isaac_base_url.rstrip('/')
        self._running  = False
        self._thread   = None
        self._session  = requests.Session()

        self.commands_received = 0
        self.crc_errors        = 0
        self.isaac_post_errors = 0

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name='actuator_sink'
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def _loop(self) -> None:
        buf = b''
        while self._running:
            try:
                waiting = self._port.in_waiting
                if waiting > 0:
                    buf += self._port.read(waiting)
                else:
                    time.sleep(0.001)
                    continue
            except serial.SerialException as exc:
                print(f"[actuator_sink] UART read error: {exc}")
                time.sleep(0.01)
                continue

            # Drain all complete frames from the buffer
            while len(buf) >= CMD_FRAME_SIZE:
                # Find magic
                idx = -1
                for i in range(len(buf) - 1):
                    if buf[i] == CMD_MAGIC[0] and buf[i + 1] == CMD_MAGIC[1]:
                        idx = i
                        break
                if idx < 0:
                    # No magic found; keep last byte in case magic straddles a read
                    buf = buf[-1:]
                    break
                if idx > 0:
                    buf = buf[idx:]  # skip garbage before magic
                if len(buf) < CMD_FRAME_SIZE:
                    break  # wait for more bytes

                frame = unpack_command_frame(buf[:CMD_FRAME_SIZE])
                if frame is not None:
                    self._on_command(frame)
                    self.commands_received += 1
                    buf = buf[CMD_FRAME_SIZE:]
                else:
                    # Bad CRC — skip one byte and retry
                    self.crc_errors += 1
                    buf = buf[1:]

    def _on_command(self, frame: CommandFrame) -> None:
        if frame.flags & FLAGS_ABORT:
            body = {'action': 'abort'}
        else:
            body = {
                'action':       'throttle',
                'value':        float(frame.throttle),
                'gimbal_pitch': frame.gimbal_pitch_mrad / 1000.0,
                'gimbal_yaw':   frame.gimbal_yaw_mrad  / 1000.0,
            }
        try:
            self._session.post(
                f"{self._base_url}/starship/command",
                json=body,
                timeout=0.05,
            )
        except Exception as exc:
            self.isaac_post_errors += 1
            if self.isaac_post_errors <= 3 or self.isaac_post_errors % 100 == 0:
                print(f"[actuator_sink] Isaac POST error (n={self.isaac_post_errors}): {exc}")
