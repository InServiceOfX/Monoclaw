# BBB EGSE — run guide

Run these steps on the BeagleBone Black.

## 1. First-time: set up venv

```bash
cd Embedded/AvionicsHIL/bbb/egse
uv venv .venv --python 3.11    # BBB may not have 3.13; use whatever python3 is available
source .venv/bin/activate
uv pip install pyserial requests pyyaml
```

If `uv` is not on the BBB:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyserial requests pyyaml
```

## 2. Enable UART pins (run once per boot)

```bash
config-pin P9.21 uart   # UART2_TXD
config-pin P9.22 uart   # UART2_RXD
ls /dev/ttyO*           # should show /dev/ttyO2 (or ttyO4 depending on overlay)
```

Record the actual device name in `../../STATUS.md` VERIFY log and `../../config.yaml`.

## 3. Verify UART device name in config.yaml

Edit `../../config.yaml`:
```yaml
bbb:
  sensor_uart: "/dev/ttyO2"     # set to whatever ls /dev/ttyO* showed
  actuator_uart: "/dev/ttyO2"
```

## 4. Run the self-test (no hardware connected)

```bash
python3 frames.py       # round-trip + CRC check — must print "All tests passed."
```

## 5. Run EGSE (Jetson connected via UART)

Ensure wiring per HARDWARE.md §4:
- Jetson pin 8  (TX) → BBB P9_22 (RX)
- Jetson pin 10 (RX) → BBB P9_21 (TX)
- Jetson pin 6  (GND) → BBB P9_1 (GND)

```bash
source .venv/bin/activate
python3 run_egse.py --config ../../config.yaml
```

Expected 1 Hz status line:
```
[egse] alt=   1000.0 m  vz= -10.00 m/s  data_ready=True  tx=50  rx=0  crc_err=0  dropped=0
```

`rx=0` is expected until the Jetson FSW (TASK-03) is running.

## 6. Offline test (mock Isaac, no hardware)

```bash
# Terminal 1 — minimal Isaac stub
python3 -c "
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, math, time

t0 = time.monotonic()
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        t = time.monotonic() - t0
        z = max(0, 1000 - 0.5 * t**2)
        body = json.dumps({'x':0,'y':0,'z':z,'qw':1,'qx':0,'qy':0,'qz':0,'vx':0,'vy':0,'vz':-t}).encode()
        self.send_response(200); self.send_header('Content-Type','application/json')
        self.send_header('Content-Length', len(body)); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'{\"status\":\"ok\"}')
HTTPServer(('0.0.0.0', 8282), H).serve_forever()
"

# Terminal 2 — run EGSE pointing at localhost (no real Isaac needed)
# Edit config.yaml: isaac.base_url = "http://127.0.0.1:8282"
python3 run_egse.py
```

## Confirmed device names (fill in after hardware verify)

| Item | Configured | Confirmed |
|------|-----------|-----------|
| BBB UART | /dev/ttyO2 | _TBD_ |
| BBB I2C  | /dev/i2c-2 | _TBD_ (upgrade path only) |
