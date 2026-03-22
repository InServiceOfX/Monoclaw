#!/usr/bin/env bash
# SGLang Direct Launcher
# Usage: ./launch.sh [profile]
#   profile: fast (default) | longctx | lowvram
#
# Replaces docker_builder / run_configuration.yml approach.
# Docker orchestration lives here; SGLang server args live in sglang_configs/.

set -euo pipefail

PROFILE="${1:-fast}"
CONFIGS_DIR="$(cd "$(dirname "$0")/sglang_configs" && pwd)"

# ── profile → config file + model path ───────────────────────────────────────
case "$PROFILE" in
    fast|longctx|lowvram)
        CONFIG_FILE="sglang_configs/qwen35_9b_awq_${PROFILE}.yaml"
        MODEL_HOST_PATH="/media/propdev/9dc1a908-7eff-4e1c-8231-ext4/home/propdev/Data/Models/LLM/cyankiwi/Qwen3.5-9B-AWQ-4bit"
        MODEL_CONTAINER_PATH="/models/Qwen3.5-9B-AWQ-4bit"
        ;;
    qwen3-4b)
        CONFIG_FILE="sglang_configs/qwen3_4b_instruct.yaml"
        MODEL_HOST_PATH="/media/propdev/9dc1a908-7eff-4e1c-8231-ext4/home/propdev/Data/Models/LLM/Qwen/Qwen3-4B-Instruct-2507"
        MODEL_CONTAINER_PATH="/models/Qwen3-4B-Instruct-2507"
        ;;
    qwen35-2b)
        CONFIG_FILE="sglang_configs/qwen35_2b.yaml"
        MODEL_HOST_PATH="/media/propdev/9dc1a908-7eff-4e1c-8231-ext4/home/propdev/Data/Models/LLM/Qwen/Qwen3.5-2B"
        MODEL_CONTAINER_PATH="/models/Qwen3.5-2B"
        ;;
    nanbeige)
        CONFIG_FILE="sglang_configs/nanbeige41_3b.yaml"
        MODEL_HOST_PATH="/media/propdev/9dc1a908-7eff-4e1c-8231-ext4/home/propdev/Data/Models/LLM/Nanbeige/Nanbeige4.1-3B"
        MODEL_CONTAINER_PATH="/models/Nanbeige4.1-3B"
        ;;
    *)
        echo "ERROR: unknown profile: $PROFILE"
        echo "Available profiles: fast, longctx, lowvram, qwen3-4b, qwen35-2b, nanbeige"
        exit 1
        ;;
esac

# ── image ────────────────────────────────────────────────────────────────────
# Tag strategy (see README.md for details):
#   dev-cu13                        = nightly main branch, CUDA 13, mutable
#   nightly-dev-cu13-YYYYMMDD-SHA   = pinned dated snapshot, CUDA 13, immutable
#
# Use the pinned nightly for reproducibility. Update by changing the tag here
# after validating the new nightly on this model.
#
# Host: CUDA 13.0, driver 580.76, RTX 3060 (device=1)
# Qwen3.5 requires SGLang main branch — do NOT use latest-cu130.
#
# Current pinned tag: nightly-dev-cu13-20260321-94194537
# To update: docker pull lmsysorg/sglang:dev-cu13 (gets latest nightly)
#            then re-pin to the corresponding nightly-dev-cu13-YYYYMMDD-SHA tag.
# Qwen3.5 hybrid arch requires the nightly (GDN kernel support).
# Standard BF16 models use latest-cu130 — the nightly's Triton deadlocks on first inference.
case "$PROFILE" in
    fast|longctx|lowvram|qwen35-2b)
        DOCKER_IMAGE="lmsysorg/sglang:nightly-dev-cu13-20260321-94194537"
        ;;
    *)
        DOCKER_IMAGE="lmsysorg/sglang:latest-cu130"
        ;;
esac

# ── validation ───────────────────────────────────────────────────────────────
if [[ ! -f "$(dirname "$0")/${CONFIG_FILE}" ]]; then
    echo "ERROR: config not found: ${CONFIG_FILE}"
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
    -v "/home/propdev/.cache/triton_sglang:/root/.triton:rw" \
    -e "TRITON_CACHE_DIR=/root/.triton" \
    -e "TOKENIZERS_PARALLELISM=false" \
    -e "TRITON_DISABLE_LINE_INFO=1" \
    "${DOCKER_IMAGE}" \
    python3 -m sglang.launch_server \
        --config "/sglang_configs/$(basename "${CONFIG_FILE}")"
