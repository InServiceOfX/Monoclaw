# ROS 2 Host Container — rosa Rust rewrite
# This container's ONLY job is to host ROS 2 + turtlesim.
# rosa itself runs as a Rust binary on the host (or a sibling container).
# No langchain. No Python LLM packages. No rosa Python source.
#
# See: ~/workspace/workspace2/repos/rosa/ORCHESTRATION.md

ARG ROS_DISTRO=humble
FROM osrf/ros:${ROS_DISTRO}-desktop AS ros2-base

ENV DEBIAN_FRONTEND=noninteractive

# Tools needed by the agent's CLI tool-shellout layer + ROS 2 dev essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-${ROS_DISTRO}-turtlesim \
    ros-${ROS_DISTRO}-rmw-cyclonedds-cpp \
    curl \
    ca-certificates \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Rust toolchain (for native rosa-ros2 builds via the `ros2-native` feature)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

# CycloneDDS is the most reliable RMW for cross-container/host comms.
# Fast-DDS has known multicast issues when bridging host <-> container.
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Bake the ROS 2 environment into every shell that starts in this container.
# Without this, `docker compose exec ros2 ros2 ...` fails with
# "executable file not found in $PATH" because exec bypasses the ENTRYPOINT.
# ROS_DISTRO is set by the base image (osrf/ros:humble-desktop) so ${ROS_DISTRO}
# resolves correctly at build time.
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc && \
    echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bash_profile && \
    echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> /root/.bashrc && \
    echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> /root/.bash_profile

COPY ros2_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
