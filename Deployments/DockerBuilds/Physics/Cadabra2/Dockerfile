FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install build dependencies for cadabra2
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools
    cmake \
    g++ \
    make \
    git \
    pkg-config \
    # Python
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    # Core math/string libraries
    libpcre3-dev \
    libgmp-dev \
    uuid-dev \
    # Boost (cadabra2 needs boost-python3)
    libboost-all-dev \
    libboost-python-dev \
    # HTTP/WebSocket/SSL for server backend
    libmicrohttpd-dev \
    libwebsocketpp-dev \
    libssl-dev \
    # SQLite for notebook storage
    libsqlite3-dev \
    # GTK3 + gtkmm for the graphical notebook UI
    libgtk-3-dev \
    libgtk-3-0 \
    libgtkmm-3.0-dev \
    libglibmm-2.4-dev \
    libsigc++-2.0-dev \
    libcairomm-1.0-dev \
    libpangomm-1.4-dev \
    libatkmm-1.6-dev \
    # OpenGL (needed for gtkmm/gtk)
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    # Python scientific stack
    python3-matplotlib \
    python3-sympy \
    python3-requests \
    # nlohmann-json (header-only, may be needed)
    nlohmann-json3-dev \
    # Misc
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Clone cadabra2 from source
WORKDIR /opt
RUN git clone --depth 1 https://github.com/kpeeters/cadabra2.git cadabra2

# Build cadabra2 from source
WORKDIR /opt/cadabra2
RUN mkdir build && cd build && \
    cmake \
        -DCMAKE_BUILD_TYPE=Release \
        -DENABLE_MATHEMATICA=OFF \
        -DENABLE_JUPYTER=OFF \
        -DENABLE_FRONTEND=ON \
        .. && \
    make -j$(nproc) && \
    make install

# Verify installation
RUN cadabra2 --version || true
RUN which cadabra2

# Install Python packages useful for physics/QFT
RUN pip3 install --break-system-packages \
    numpy \
    scipy

WORKDIR /work

CMD ["/bin/bash"]
