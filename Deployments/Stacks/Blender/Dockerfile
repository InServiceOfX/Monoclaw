# Blender 4.2 LTS — real-time EEVEE viewer for Starship telemetry.
#
# Renders on the host's display GPU via X11 passthrough (no Blender on host).
# The NVIDIA Container Toolkit injects the real GL driver when the container is
# run with NVIDIA_DRIVER_CAPABILITIES including `graphics` (see compose / README).
#
# Maxwell (GTX 980 Ti) is the *minimum* arch Blender 4.2 supports — exactly our
# display GPU. The Starship scene (~4.5k tris + slab + 2 lights) is trivial for it.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# X11 client + GL/EGL dispatch libs. The actual libGLX_nvidia / libEGL_nvidia
# are mounted in by the container toolkit at runtime — these are the glvnd
# dispatchers + the X libraries Blender links against.
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl xz-utils ca-certificates \
      libglvnd0 libgl1 libegl1 libgles2 libglx0 \
      libxi6 libxxf86vm1 libxfixes3 libxrender1 libxext6 libsm6 \
      libxkbcommon0 libxrandr2 libxinerama1 libxcursor1 \
      libfreetype6 libgomp1 libtinfo6 \
 && rm -rf /var/lib/apt/lists/*

# Official Blender 4.2 LTS (bundles its own Python — stdlib socket/urllib only,
# so the driver script needs no pip installs).
ARG BLENDER_VERSION=4.2.3
RUN curl -fsSL "https://download.blender.org/release/Blender4.2/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
      | tar -xJ -C /opt \
 && ln -s "/opt/blender-${BLENDER_VERSION}-linux-x64/blender" /usr/local/bin/blender

WORKDIR /work
ENTRYPOINT ["blender"]
