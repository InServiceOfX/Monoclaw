#!/bin/bash
set -e

source /opt/ros/${ROS_DISTRO}/setup.bash

echo "ROS 2 ${ROS_DISTRO} ready."
echo "  DDS domain : ${ROS_DOMAIN_ID:-0}"
echo "  RMW        : $RMW_IMPLEMENTATION"
echo ""
echo "Useful commands:"
echo "  ros2 run turtlesim turtlesim_node   (needs X11 on host: xhost +local:docker)"
echo "  ros2 topic list"
echo "  ros2 doctor"
echo ""

exec "$@"
