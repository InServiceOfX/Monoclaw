#!/bin/bash
# Start Isaac Sim in the requested mode.
# ISAAC_MODE env var: headless (default) | windowed | streaming
#
# headless  — no display, no streaming; runs via isaacsim.SimulationApp with
#             headless=True. Loads ros2_bridge and plays an empty stage so
#             /clock and /tf_static are immediately visible on the ROS 2 network.
# streaming — WebRTC viewport at http://localhost:8211 (ISAAC_MODE=streaming)
# windowed  — full GUI via X11 (requires DISPLAY + xhost +local:docker on host)

set -e

: "${ISAAC_MODE:=headless}"
: "${ROS_DOMAIN_ID:=0}"
: "${RMW_IMPLEMENTATION:=rmw_cyclonedds_cpp}"

echo "Isaac Sim starting — mode: $ISAAC_MODE"
echo "  ROS_DOMAIN_ID : $ROS_DOMAIN_ID"
echo "  RMW           : $RMW_IMPLEMENTATION"
echo ""

case "$ISAAC_MODE" in
  headless)
    # Run via SimulationApp (headless=True). Loads the ROS 2 bridge and plays
    # an empty stage immediately so ROS topics appear on the network.
    exec /isaac-sim/python.sh /isaac-sim/scripts/enable_ros2_bridge.py
    ;;
  streaming)
    # WebRTC streaming client — viewport accessible at http://localhost:8211
    exec /isaac-sim/runheadless.sh \
      --enable isaacsim.ros2.bridge
    ;;
  windowed)
    # Full GUI via X11 (requires DISPLAY set and xhost +local:docker on host)
    exec /isaac-sim/isaac-sim.sh \
      --enable isaacsim.ros2.bridge
    ;;
  *)
    echo "ERROR: unknown ISAAC_MODE=$ISAAC_MODE (use: headless|windowed|streaming)" >&2
    exit 1
    ;;
esac
