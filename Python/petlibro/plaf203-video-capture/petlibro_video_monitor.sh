#!/bin/bash
# Petlibro /app/* video service monitor
while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    -X POST https://api.us.petlibro.com/app/device/video \
    -H "Content-Type: application/json" \
    -H "source: ANDROID" \
    -d '{}' 2>/dev/null)
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S PST')
  echo "[$TIMESTAMP] /app/device/video -> HTTP $STATUS"
  if [ "$STATUS" != "503" ] && [ "$STATUS" != "000" ]; then
    echo "VIDEO SERVICE BACK: HTTP $STATUS at $TIMESTAMP" > /tmp/petlibro_video_up.flag
    exit 0
  fi
  sleep 120
done
