# Petlibro PLAF203 — Reverse Engineering Notes

Device: Granary Smart Camera Feeder  
Model: PLAF203  
SN: AF0301310008EF40024DSJ  
MAC: FC:23:CD:1C:BC:E9  
Firmware: 3.1.4.8  
IP (local): 192.168.86.22  

---

## Architecture Overview

```
Phone App
  │
  ├─► api.us.petlibro.com   (HTTPS, REST)
  │     /member/*  → auth, account         [UP]
  │     /device/*  → control, status       [UP]
  │     /data/*    → history, events       [UP]
  │     /app/*     → VIDEO auth (TUTK)     [503 as of 2026-03-03]
  │
  ├─► mqtt.us.petlibro.com:8883  (MQTTS)   [UP]
  │     Device control/status over MQTT
  │     Topics: dl/plaf203/<SN>/device/{service,event}/{sub,post}
  │
  └─► ThroughTek Kalay P2P (TUTK)
        Video/audio stream (P2P or relay)
        Relay IPs: 44.211.92.174, iotcplatform.com, kalayservice.com
        Auth token obtained from: POST /app/device/video  ← BROKEN
```

## App Credentials (from HA integration source)
- APPID: 1
- APPSN: c35772530d1041699c87fe62348507a8
- Auth header: `token: <session_token>`
- Common headers: source=ANDROID, language=EN, version=1.3.45, Content-Type=application/json

## Video Stream Flow
1. App → POST /app/device/video  (BROKEN — 503)
   Request: { deviceSn: <SN>, token: <auth_token> }
   Response: { tutk_uid: ..., tutk_token: ..., ... }  ← NEED TO CAPTURE
2. App → ThroughTek Kalay P2P servers (UDP hole-punch or relay)
3. Video streams device↔app via TUTK protocol

## Goal
Capture the TUTK UID + session token from step 1 using mitmproxy.
Then implement a local TUTK client to stream video without cloud dependency.
See: capture_tutk.py, verify_intercept.py
