"""
EGSE main entry point — wires truth_bridge + sensor_source + actuator_sink
into one process driven by config.yaml.

Usage (on BBB, from this directory):
    python3 run_egse.py [--config ../../config.yaml]

Prints a 1 Hz status line: frames sent, commands received, last altitude.
Ctrl-C to stop.
"""
import argparse
import sys
import time

import serial
import yaml


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="AvionicsHIL BBB EGSE")
    parser.add_argument('--config', default='../../config.yaml',
                        help='Path to config.yaml (default: ../../config.yaml)')
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        print(f"[run_egse] config not found: {args.config}")
        sys.exit(1)

    isaac_url  = cfg['isaac']['base_url']
    isaac_poll = cfg['isaac']['poll_hz']
    uart_dev   = cfg['bbb']['sensor_uart']
    baud       = cfg['bbb']['baud']
    rate_hz    = cfg['loop']['rate_hz']

    # ── Open UART (single full-duplex port for both sensor TX and cmd RX) ──
    print(f"[run_egse] Opening UART {uart_dev} @ {baud} baud")
    try:
        port = serial.Serial(uart_dev, baudrate=baud, timeout=0.1)
    except serial.SerialException as exc:
        print(f"[run_egse] Cannot open {uart_dev}: {exc}")
        print("  Did you enable the UART? Run: config-pin P9.21 uart; config-pin P9.22 uart")
        sys.exit(1)

    # ── Instantiate components ──────────────────────────────────────────────
    from sensor_model import SensorModel
    from fault_injector import FaultInjector
    from truth_bridge import TruthBridge
    from sensor_source import SensorSource
    from actuator_sink import ActuatorSink

    model    = SensorModel()
    injector = FaultInjector(model)
    bridge   = TruthBridge(model, isaac_url, poll_hz=isaac_poll)
    source   = SensorSource(model, injector, port, rate_hz=rate_hz)
    sink     = ActuatorSink(port, isaac_url)

    # ── Start all threads ───────────────────────────────────────────────────
    print(f"[run_egse] Connecting to Isaac at {isaac_url}")
    bridge.start()
    source.start()
    sink.start()
    print(f"[run_egse] EGSE running at {rate_hz:.0f} Hz — Ctrl-C to stop")

    try:
        while True:
            time.sleep(1.0)
            state = model.snapshot()
            print(
                f"[egse] alt={state['altitude_m']:8.1f} m  "
                f"vz={state['velocity_z_mps']:6.2f} m/s  "
                f"data_ready={state['data_ready']}  "
                f"tx={source.frames_sent}  rx={sink.commands_received}  "
                f"crc_err={sink.crc_errors}  dropped={source.frames_dropped}"
            )
    except KeyboardInterrupt:
        print("\n[run_egse] Stopping…")
    finally:
        bridge.stop()
        source.stop()
        sink.stop()
        port.close()
        print("[run_egse] Stopped.")


if __name__ == "__main__":
    main()
