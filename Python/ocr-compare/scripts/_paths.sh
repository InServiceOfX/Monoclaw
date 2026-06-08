#!/usr/bin/env bash
# Shared path + env resolution for ocr-compare scripts. Source this; don't run it.
#
# Override any of these by exporting them, or by copying scripts/env.sh.example
# to scripts/env.sh (gitignored) and editing it. Storage defaults to the big
# Samsung disk because the root disk is small — the venvs are ~5 GB each and the
# weights ~4 GB total.

# Resolve project root (parent of this scripts/ dir), following symlinks.
_SELF="${BASH_SOURCE[0]}"
while [ -h "$_SELF" ]; do _SELF="$(readlink "$_SELF")"; done
OCR_SCRIPTS_DIR="$(cd "$(dirname "$_SELF")" && pwd)"
OCR_PROJECT_DIR="$(cd "$OCR_SCRIPTS_DIR/.." && pwd)"
export OCR_SCRIPTS_DIR OCR_PROJECT_DIR

# Local, uncommitted overrides.
[ -f "$OCR_SCRIPTS_DIR/env.sh" ] && . "$OCR_SCRIPTS_DIR/env.sh"

# Where the heavy artifacts live. Configurable; defaults to the large disk.
: "${OCR_STORAGE:=/media/ernest/Samsung980ProPCI/ocr-compare}"
: "${OCR_VENV_DIR:=$OCR_STORAGE/venvs}"        # holds venv-nougat / venv-marker / venv-resolve
: "${OCR_WEIGHTS_DIR:=$OCR_STORAGE/weights}"   # holds downloaded open weights
: "${OCR_PYTHON:=3.10}"                         # nougat + marker pin Python 3.10
export OCR_STORAGE OCR_VENV_DIR OCR_WEIGHTS_DIR OCR_PYTHON

# CUDA torch. HARD assumption: an NVIDIA GPU + CUDA is present. We always install
# the CUDA wheel build, never the CPU build. cu130 matches the captured RTX 3070
# environment (torch 2.12.0+cu130); change CUDA_INDEX if you move to another CUDA.
: "${TORCH_SPEC:=torch==2.12.0 torchvision==0.27.0}"
: "${CUDA_INDEX:=https://download.pytorch.org/whl/cu130}"
export TORCH_SPEC CUDA_INDEX

# Weight-cache wiring, read by nougat and marker at RUNTIME (see run_ocr.sh).
# Nougat: torch.hub dir -> checkpoint lands in $TORCH_HOME/hub/nougat-0.1.0-small.
#         NOUGAT_CHECKPOINT can point straight at a checkpoint dir to bypass it.
# Marker: surya reads MODEL_CACHE_DIR; HF_HOME catches any huggingface downloads.
export TORCH_HOME="${TORCH_HOME:-$OCR_WEIGHTS_DIR/torch}"
export NOUGAT_CHECKPOINT="${NOUGAT_CHECKPOINT:-$TORCH_HOME/hub/nougat-0.1.0-small}"
export MODEL_CACHE_DIR="${MODEL_CACHE_DIR:-$OCR_WEIGHTS_DIR/datalab/models}"
export HF_HOME="${HF_HOME:-$OCR_WEIGHTS_DIR/huggingface}"

ocr_print_config() {
  cat <<EOF
ocr-compare config
  OCR_PROJECT_DIR  = $OCR_PROJECT_DIR
  OCR_STORAGE      = $OCR_STORAGE
  OCR_VENV_DIR     = $OCR_VENV_DIR
  OCR_WEIGHTS_DIR  = $OCR_WEIGHTS_DIR
  OCR_PYTHON       = $OCR_PYTHON
  TORCH_SPEC       = $TORCH_SPEC
  CUDA_INDEX       = $CUDA_INDEX
  TORCH_HOME       = $TORCH_HOME
  NOUGAT_CHECKPOINT= $NOUGAT_CHECKPOINT
  MODEL_CACHE_DIR  = $MODEL_CACHE_DIR
  HF_HOME          = $HF_HOME
EOF
}
