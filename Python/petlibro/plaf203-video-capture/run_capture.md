# Run Real Petlibro Video Capture (Phone)

## 1) Start mitmproxy addon
```bash
mitmdump -s ~/.openclaw/workspace/petlibro/capture_tutk.py -p 8080
```

## 2) Configure phone Wi‑Fi proxy
- Proxy host: your desktop LAN IP (e.g. `192.168.86.91`)
- Proxy port: `8080`

## 3) Trust mitmproxy CA on phone
- On phone browser (while proxy is enabled), open: `http://mitm.it`
- Install certificate for your OS
- On Android 7+, user CAs are not trusted by all apps by default. If Petlibro app ignores user CAs, use:
  - rooted trust-store install, or
  - LSPosed/JustTrustMe/Magisk module, or
  - capture with Frida SSL unpinning.

## 4) Trigger video request
- Open Petlibro app
- Open PLAF203 live camera page
- This should call `/app/device/video`

## 5) Inspect captures
```bash
cat ~/.openclaw/workspace/petlibro/captures/latest_video_bootstrap.json | jq
```

and
```bash
tail -n 20 ~/.openclaw/workspace/petlibro/captures/petlibro_video_flows.jsonl
```

## Expected payload fields (examples)
Look for keys like:
- `tutk*`
- `kalay*`
- `uid`
- `token`
- `relay/server`

These are the credentials needed for direct TUTK stream bootstrap.
