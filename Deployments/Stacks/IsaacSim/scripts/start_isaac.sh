#!/bin/bash
# Start Isaac Sim in the requested mode.
# ISAAC_MODE env var: headless (default) | windowed | streaming
#
# headless  — no display, no streaming; runs via isaacsim.SimulationApp with
#             headless=True. Loads scene from ISAAC_SCENE_PATH and starts the
#             HTTP control server + StarshipPublisher/Controller threads.
# streaming — WebRTC via runheadless.sh (isaacsim.exp.full.streaming.kit).
#             NOTE: requires NvFBC for capture — NOT supported on GeForce/laptop GPUs.
#             Use windowed mode on consumer hardware. Streaming works on A/H-series GPUs.
# windowed  — full GUI via X11 (requires DISPLAY + xhost +local:docker on host)

set -e

: "${ISAAC_MODE:=headless}"
: "${ROS_DOMAIN_ID:=0}"
: "${RMW_IMPLEMENTATION:=rmw_cyclonedds_cpp}"
: "${ISAAC_SCENE_PATH:=}"

echo "Isaac Sim starting — mode: $ISAAC_MODE"
echo "  ROS_DOMAIN_ID    : $ROS_DOMAIN_ID"
echo "  RMW              : $RMW_IMPLEMENTATION"
echo "  ISAAC_SCENE_PATH : ${ISAAC_SCENE_PATH:-(none)}"
echo ""

case "$ISAAC_MODE" in
  headless)
    # Pure physics/topics mode — no visual output.
    # enable_ros2_bridge.py handles scene loading (ISAAC_SCENE_PATH), OmniGraph
    # /clock, HTTP control server, and StarshipPublisher/Controller threads.
    exec /isaac-sim/python.sh /isaac-sim/scripts/enable_ros2_bridge.py
    ;;
  streaming)
    # WebRTC via runheadless.sh (isaacsim.exp.full.streaming.kit).
    # Requires NvFBC GPU capture — NOT available on GeForce/laptop GPUs.
    # On those GPUs, switch to ISAAC_MODE=windowed instead.
    exec /isaac-sim/runheadless.sh \
      --enable isaacsim.ros2.bridge \
      --exec /isaac-sim/scripts/load_starship_hook.py
    ;;
  windowed)
    # Full GUI via X11.
    # Host prereq: xhost +local:docker  (run once per session before docker compose up)
    # --exec auto-loads the Starship stage so it appears in the viewport on startup.
    exec /isaac-sim/isaac-sim.sh \
      --enable isaacsim.ros2.bridge \
      --exec /isaac-sim/scripts/load_starship_hook.py
    ;;
  *)
    echo "ERROR: unknown ISAAC_MODE=$ISAAC_MODE (use: headless|windowed|streaming)" >&2
    exit 1
    ;;
esac
