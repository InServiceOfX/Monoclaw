#!/bin/bash
# Start Isaac Sim in the requested mode.
# ISAAC_MODE env var: headless (default) | windowed | streaming
set -e

: "${ISAAC_MODE:=headless}"

echo "Isaac Sim starting — mode: $ISAAC_MODE"
echo "  ROS_DOMAIN_ID : ${ROS_DOMAIN_ID:-0}"
echo "  RMW           : $RMW_IMPLEMENTATION"
echo ""

case "$ISAAC_MODE" in
  headless)
    # Headless native (no display) + ROS 2 bridge extension enabled
    exec /isaac-sim/runheadless.native.sh \
      --/exts/omni.isaac.ros2_bridge/publish_tf=true \
      --enable omni.isaac.ros2_bridge
    ;;
  streaming)
    # WebRTC streaming client at http://localhost:8211
    exec /isaac-sim/runheadless.webrtc.sh \
      --enable omni.isaac.ros2_bridge
    ;;
  windowed)
    # Full GUI via X11 (requires DISPLAY and xhost +local:docker on host)
    exec /isaac-sim/isaac-sim.sh \
      --enable omni.isaac.ros2_bridge
    ;;
  *)
    echo "ERROR: unknown ISAAC_MODE=$ISAAC_MODE (use: headless|windowed|streaming)" >&2
    exit 1
    ;;
esac
