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
    # WebKit2GTK — required for cadabra2-gtk notebook rendering
    libwebkit2gtk-4.1-dev \
    libwebkit2gtk-4.1-0 \
    # OpenGL (needed for GTK/webkit compositing)
    libgl1-mesa-dev \
    libgl1-mesa-dri \
    libglu1-mesa-dev \
    # Python scientific stack
    python3-matplotlib \
    python3-sympy \
    python3-requests \
    # nlohmann-json
    nlohmann-json3-dev \
    # Fonts (needed for webkit/LaTeX rendering)
    fonts-liberation \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    # GTK themes / icon themes for proper rendering
    adwaita-icon-theme \
    gnome-themes-extra \
    # dbus (webkit subprocess needs it)
    dbus \
    dbus-x11 \
    at-spi2-core \
    # Misc
    ca-certificates \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Jupyter + scientific Python stack before building cadabra2
# (cadabra2's ENABLE_JUPYTER cmake build needs jupyter_client available)
RUN pip3 install --break-system-packages \
    jupyter \
    jupyterlab \
    notebook \
    ipykernel \
    numpy \
    scipy \
    sympy \
    matplotlib

# Clone cadabra2 from source
WORKDIR /opt
RUN git clone --depth 1 https://github.com/kpeeters/cadabra2.git cadabra2

# Build cadabra2 from source — with Jupyter kernel support enabled
WORKDIR /opt/cadabra2
RUN mkdir build && cd build && \
    cmake \
        -DCMAKE_BUILD_TYPE=Release \
        -DENABLE_MATHEMATICA=OFF \
        -DENABLE_JUPYTER=ON \
        -DENABLE_FRONTEND=ON \
        .. && \
    make -j$(nproc) && \
    make install

# Refresh font cache
RUN fc-cache -f -v

# Verify installation
RUN cadabra2 --version
RUN cadabra2-cli --version 2>/dev/null || true
RUN jupyter kernelspec list

# Create default work directory
WORKDIR /work

# Expose Jupyter port
EXPOSE 8888

CMD ["/bin/bash"]
