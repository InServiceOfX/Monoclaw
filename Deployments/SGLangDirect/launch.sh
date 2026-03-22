#!/usr/bin/env bash
# SGLang Direct Launcher
# Usage: ./launch.sh [profile]
#   profile: fast (default) | longctx | lowvram
#
# Replaces docker_builder / run_configuration.yml approach.
# Docker orchestration lives here; SGLang server args live in sglang_configs/.

set -euo pipefail

PROFILE="${1:-fast}"
CONFIG_FILE="sglang_configs/qwen35_9b_awq_${PROFILE}.yaml"

# ── paths ────────────────────────────────────────────────────────────────────
MODEL_HOST_PATH="/media/propdev/9dc1a908-7eff-4e1c-8231-ext4/home/propdev/Data/Models/LLM/cyankiwi/Qwen3.5-9B-AWQ-4bit"
MODEL_CONTAINER_PATH="/models/Qwen3.5-9B-AWQ-4bit"
CONFIGS_DIR="$(cd "$(dirname "$0")/sglang_configs" && pwd)"

# ── image ────────────────────────────────────────────────────────────────────
# Qwen3.5 requires SGLang from main branch (not latest-cu130).
# lmsysorg/sglang:latest pulls the most recent release image.
DOCKER_IMAGE="lmsysorg/sglang:latest"

# ── validation ───────────────────────────────────────────────────────────────
if [[ ! -f "$(dirname "$0")/${CONFIG_FILE}" ]]; then
    echo "ERROR: config not found: ${CONFIG_FILE}"
    echo "Available profiles: fast, longctx, lowvram"
    exit 1
fi

if [[ ! -d "$MODEL_HOST_PATH" ]]; then
    echo "ERROR: model path not found: $MODEL_HOST_PATH"
    exit 1
fi

echo "=== SGLang Direct ==="
echo "Profile   : $PROFILE"
echo "Config    : $CONFIG_FILE"
echo "Image     : $DOCKER_IMAGE"
echo "Model     : $MODEL_HOST_PATH"
echo ""

docker run \
    --rm \
    --gpus "device=1" \
    --shm-size 16g \
    --ipc=host \
    -p 30000:30000 \
    -v "${MODEL_HOST_PATH}:${MODEL_CONTAINER_PATH}:ro" \
    -v "${CONFIGS_DIR}:/sglang_configs:ro" \
    "${DOCKER_IMAGE}" \
    python3 -m sglang.launch_server \
        --config "/sglang_configs/qwen35_9b_awq_${PROFILE}.yaml"
