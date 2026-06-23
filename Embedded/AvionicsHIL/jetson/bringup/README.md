# Jetson Bringup — run guide (TASK-01)

All steps run ON THE JETSON ORIN NANO.

## 1. SSH into the Jetson

```bash
ssh user@tyvakorindev.lan    # or 192.168.86.34 (wired LAN, confirmed 2026-06-23)
# Jetson USB-C IP: 192.168.55.1 (only available when NOT booting with explicit FDT in extlinux.conf)
```

Confirmed 2026-06-23 after manual reboot / primary kernel option `1`:

```bash
ssh orin@192.168.55.1    # USB-C network / l4tbr0
ssh orin@192.168.86.34   # wired Ethernet / enP8p1s0
ssh orin@192.168.86.32   # Wi-Fi / wlP1p1s0
```

## 2. Copy the project to the Jetson (or clone)

Easiest: rsync from desktop:
```bash
# On desktop:
rsync -av --exclude='.venv' --exclude='target' \
  /media/propdev/Expansion/openclaw/.openclaw/workspace/repos/Monoclaw/Embedded/AvionicsHIL/ \
  user@tyvakorindev.lan:~/AvionicsHIL/
```

## 3. Set up venv on Jetson

```bash
cd ~/AvionicsHIL/jetson/bringup
# Install uv on Jetson if not present:
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.cargo/env   # or wherever uv installs

uv venv .venv
source .venv/bin/activate
uv pip install pyserial smbus2 pyyaml
```

## 4. Find the 40-pin UART device (VERIFY step 2)

```bash
ls /dev/ttyTHS*
# Expected: /dev/ttyTHS1  (40-pin pins 8/10)
# If missing, the UART may need enabling via jetson-io or extlinux overlay.

i2cdetect -l
# Lists all I2C buses. The 40-pin I2C (pins 3/5) is typically i2c-7 or i2c-1.
```

**Record the actual device names in `../../STATUS.md` and `../../config.yaml`.**

## 5. UART loopback self-test (VERIFY step 3)

**Hardware setup (30 seconds):**
1. Power the Jetson OFF.
2. Jumper a Dupont wire: 40-pin **pin 8** (TX) → 40-pin **pin 10** (RX).
   (Both are on the same connector row — pin 8 is on the right side, pin 10 next to it.)
3. Power ON.

```bash
source .venv/bin/activate
python3 uart_loopback.py --port /dev/ttyTHS1   # replace with confirmed device
```

Expected output:
```
[loopback] Burst 1/4: 256 bytes MATCH
[loopback] Burst 2/4: 256 bytes MATCH
[loopback] Burst 3/4: 256 bytes MATCH
[loopback] Burst 4/4: 256 bytes MATCH
[loopback] Total: sent=1024 B  received=1024 B  result=PASS
```

If FAIL:
- Confirm the jumper is on pins **8** and **10** (not 6 and 8).
- Try `stty -F /dev/ttyTHS1 115200 raw` then re-run.
- Try `/dev/ttyTHS0` if `ttyTHS1` is absent.

Remove the loopback jumper before connecting to the BBB.

## 6. Full interface checkout

```bash
python3 check_interfaces.py --config ../../config.yaml
# add --skip-link if BBB EGSE is not yet running
```

Report written to `../../reports/checkout_jetson.json`.

## Confirmed device names (fill in after steps 4–5)

| Item | Default | Confirmed |
|------|---------|-----------|
| 40-pin UART | /dev/ttyTHS1 | _TBD_ |
| 40-pin I2C  | /dev/i2c-7   | _TBD_ |
