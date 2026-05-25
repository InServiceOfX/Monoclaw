# NVIDIA Isaac Sim — Docker container for rosa Starship sim
# Base image: NGC Isaac Sim (requires NGC login: docker login nvcr.io)
# See README.md for NGC API key setup.

ARG ISAAC_VERSION=4.5.0
FROM nvcr.io/nvidia/isaac-sim:${ISAAC_VERSION}

# Accept EULA / privacy required by Isaac Sim
ENV ACCEPT_EULA=Y \
    PRIVACY_CONSENT=Y \
    OMNI_KIT_ALLOW_ROOT=1

# Use CycloneDDS for parity with the sibling ROS 2 container.
# Fast-DDS multicast issues across containers; CycloneDDS on loopback is reliable.
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

WORKDIR /isaac-sim

COPY scripts/start_isaac.sh /usr/local/bin/start_isaac.sh
COPY scripts/enable_ros2_bridge.py /isaac-sim/scripts/enable_ros2_bridge.py
RUN chmod +x /usr/local/bin/start_isaac.sh

# Starship scene is mounted at runtime via volume (not baked into image)
# so the USD can be iterated without rebuilds.

CMD ["/usr/local/bin/start_isaac.sh"]
