# Petlibro PLAF203 — Full API Endpoint Reference

Base URL: `https://api.us.petlibro.com`  
All requests: POST unless noted. JSON body. Auth via `token` header.

---

## Authentication

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/member/auth/login` | POST | ✅ UP | Login, get session token |
| `/member/auth/logout` | POST | ✅ UP | Logout, clear token |

### Login Request
```json
{
  "appId": 1,
  "appSn": "c35772530d1041699c87fe62348507a8",
  "country": "US",
  "email": "<email>",
  "password": "<md5(password)>",
  "phoneBrand": "",
  "phoneSystemVersion": "",
  "timezone": "America/Los_Angeles",
  "thirdId": null,
  "type": null
}
```
Headers: `source: ANDROID`, `language: EN`, `version: 1.3.45`

### Login Response (data field)
```json
{ "token": "<session_token>", ... }
```

---

## Device Management (READ)

| Endpoint | Method | Status | Payload | Description |
|----------|--------|--------|---------|-------------|
| `/device/device/list` | POST | ✅ UP | `{}` | List all devices on account |
| `/device/device/baseInfo` | POST | ✅ UP | `{id, deviceSn}` | Device base info |
| `/device/device/realInfo` | POST | ✅ UP | `{id, deviceSn}` | Real-time device state |
| `/data/data/realInfo` | POST | ✅ UP | `{id, deviceSn}` | Real-time data (food level etc.) |
| `/device/setting/getAttributeSetting` | POST | ✅ UP | `{id}` | All settings/attributes |
| `/device/setting/baseInfo` | POST | ✅ UP | `{id}` | Settings base info |
| `/device/ota/getUpgrade` | POST | ✅ UP | `{id}` | Firmware upgrade info |
| `/device/data/grainStatus` | POST | ✅ UP | `{id, deviceSn}` | Food grain status + today's totals |
| `/device/device/getDefaultMatrix` | GET | ✅ UP | `?deviceSn=<sn>` | Display matrix presets |

---

## Feeding Plans (READ)

| Endpoint | Method | Status | Payload | Description |
|----------|--------|--------|---------|-------------|
| `/device/feedingPlan/todayNew` | POST | ✅ UP | `{id, deviceSn}` | Today's feeding plan |
| `/device/feedingPlan/list` | POST | ✅ UP | `{id, deviceSn}` | All feeding plans |
| `/device/wetFeedingPlan/wetListV3` | POST | ✅ UP | `{id, deviceSn}` | Wet food plans |

---

## History & Events (READ)

| Endpoint | Method | Status | Payload | Description |
|----------|--------|--------|---------|-------------|
| `/data/event/deviceEventsV2` | POST | ✅ UP | `{id}` | Device events (motion, feed, etc.) |
| `/device/workRecord/list` | POST | ✅ UP | `{deviceSn, startTime, endTime, size, type[]}` | Work record (feeding history) |
| `/data/deviceDrinkWater/todayDrinkData` | POST | ✅ UP | `{id, deviceSn}` | Water consumption today (fountain only) |

### Work Record Request Example
```json
{
  "deviceSn": "AF0301310008EF40024DSJ",
  "startTime": 1740000000000,
  "endTime":   1772571000000,
  "size": 25,
  "type": ["GRAIN_OUTPUT_SUCCESS"]
}
```

---

## Device Control (WRITE)

| Endpoint | Method | Status | Payload | Description |
|----------|--------|--------|---------|-------------|
| `/device/device/manualFeeding` | POST | ✅ UP | `{deviceSn, grainNum, requestId}` | Trigger manual feed |
| `/device/setting/updateFeedingPlanSwitch` | POST | ✅ UP | `{deviceSn, enable}` | Enable/disable feeding plan |
| `/device/setting/updateChildLockSwitch` | POST | ✅ UP | `{deviceSn, enable}` | Child lock on/off |
| `/device/setting/updateLightEnableSwitch` | POST | ✅ UP | `{deviceSn, enable}` | Light feature enable |
| `/device/setting/updateLightSwitch` | POST | ✅ UP | `{deviceSn, enable}` | Light on/off |
| `/device/setting/updateSoundEnableSwitch` | POST | ✅ UP | `{deviceSn, enable}` | Sound feature enable |
| `/device/setting/updateSoundSwitch` | POST | ✅ UP | `{deviceSn, enable}` | Sound on/off |
| `/device/setting/updateVolumeSetting` | POST | ✅ UP | `{deviceSn, volume}` | Set volume |
| `/device/setting/updateCoverSetting` | POST | ✅ UP | `{deviceSn, coverOpenMode, coverCloseSpeed, closeDoorTimeSec}` | Lid settings |
| `/device/device/vacuum` | POST | ✅ UP | `{deviceSn, vacuumMode, requestId}` | Vacuum mode (fountain) |
| `/device/device/waterModeSetting` | POST | ✅ UP | `{deviceSn, useWaterType, requestId, ...}` | Water dispensing mode |
| `/device/setting/updateRadarSetting` | POST | ✅ UP | `{deviceSn, radarSensingLevel}` | Radar trigger level |
| `/device/setting/updateLowWaterSetting` | POST | ✅ UP | `{deviceSn, lowWater}` | Low water threshold |
| `/device/device/maintenanceFrequencySetting` | POST | ✅ UP | `{deviceSn, key, frequency, requestId, timeout}` | Maintenance cycles (desiccant, filter, cleaning) |
| `/device/device/displayMatrix` | POST | ✅ UP | `{deviceSn, screenDisplayId, screenDisplayMatrix, screenLetter}` | Display icon/text |
| `/device/wetFeedingPlan/manualFeedNow` | POST | ✅ UP | `{deviceSn, plate}` | Wet food manual open |
| `/device/wetFeedingPlan/stopFeedNow` | POST | ✅ UP | `{deviceSn, feedId}` | Wet food close |

---

## Video / Camera (BROKEN)

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/app/device/video` | POST | ❌ 503 | **TUTK P2P auth — returns Kalay UID + token** |
| `/app/device/camera` | POST | ❌ 503 | Camera control |
| `/app/video/token` | POST | ❌ 503 | Video token fetch |
| `/app/camera/liveStream` | POST | ❌ 503 | Live stream init |

**All `/app/*` paths return 503 as of 2026-03-03.**  
This is a separate AWS microservice from `/member/*` and `/device/*`.

---

## MQTT Topics (PLAF203S)

MQTT broker: `mqtt.us.petlibro.com:8883` (TLS) or `:1883` (plaintext, tried first)

| Topic Pattern | Direction | Description |
|---------------|-----------|-------------|
| `dl/plaf203/<SN>/device/service/sub` | Server → Device | Commands to device |
| `dl/plaf203/<SN>/device/service/post` | Device → Server | Device responses |
| `dl/plaf203/<SN>/device/event/post` | Device → Server | Device events |
| `dl/plaf203/<SN>/device/event/sub` | Server → Device | Event acks |
| `dl/plaf203/<SN>/device/heart/...` | Both | Heartbeat |
| `dl/plaf203/<SN>/device/ntp/...` | Both | NTP sync |
| `dl/plaf203/<SN>/device/ota/...` | Both | Firmware updates |
| `dl/plaf203/<SN>/device/config/sub` | Server → Device | Config push |

Message schema: `{ cmd: <type>, message_id: <uuid>, timestamp: <ms> }`

---

## TUTK / Kalay P2P Details

- SDK: ThroughTek Kalay (TUTK) — proprietary
- Protocol: UDP (direct P2P) or TCP relay via TUTK servers
- Known TUTK IPs from firmware: `44.211.92.174`
- TUTK relay domains: `iotcplatform.com`, `kalayservice.com`, `kalay.net.cn`
- Reference: https://github.com/taishanmayi/tutk_test/blob/master/include/AVAPIs.h
- No open-source client exists. Re-implementation required for local video.
- The TUTK UID is embedded in device firmware and printed to serial console on boot.

---

## Response Code Reference

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1009 | NOT_YET_LOGIN (token expired) |
| 1102 | ILLEGAL_PASSWORD |
