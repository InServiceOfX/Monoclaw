#!/usr/bin/env bash
# Create the ocr-compare virtual environments with uv.
#
# HARD ASSUMPTION: this machine has an NVIDIA GPU + CUDA. We always install the
# CUDA build of torch (never CPU). Open weights are downloaded and run locally.
#
# Usage:
#   scripts/setup_envs.sh                 # build all three venvs (nougat marker resolve)
#   scripts/setup_envs.sh nougat marker   # build a subset
#   OCR_VENV_DIR=/other/disk scripts/setup_envs.sh nougat
#
# Venv + weights locations are controlled by env vars (see scripts/_paths.sh and
# scripts/env.sh.example). Defaults put both on the large Samsung disk.
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_paths.sh"

command -v uv >/dev/null || { echo "ERROR: uv not found. Install: https://docs.astral.sh/uv/"; exit 1; }

TARGETS=("$@"); [ ${#TARGETS[@]} -eq 0 ] && TARGETS=(nougat marker resolve)
REQ="$OCR_PROJECT_DIR/requirements"
mkdir -p "$OCR_VENV_DIR" "$OCR_WEIGHTS_DIR"
ocr_print_config; echo

# uv pip install into an explicit interpreter.
pipi() { uv pip install --python "$1/bin/python" "${@:2}"; }

make_venv() {
  local venv="$OCR_VENV_DIR/venv-$1"
  echo "==> uv venv ($1, py$OCR_PYTHON) -> $venv" >&2   # log to stderr; stdout = path only
  uv venv --python "$OCR_PYTHON" "$venv" >&2
  echo "$venv"
}

install_torch_cuda() {  # $1 = venv path
  echo "==> installing CUDA torch ($TORCH_SPEC) from $CUDA_INDEX" >&2
  # shellcheck disable=SC2086  # TORCH_SPEC is intentionally word-split
  pipi "$1" $TORCH_SPEC --index-url "$CUDA_INDEX"
}

for t in "${TARGETS[@]}"; do
  case "$t" in
    nougat)
      v=$(make_venv nougat); install_torch_cuda "$v"
      pipi "$v" -r "$REQ/nougat.txt"
      "$v/bin/python" -c "import torch;assert torch.cuda.is_available(),'CUDA not available!';print('  nougat torch',torch.__version__,'cuda',torch.cuda.is_available())"
      ;;
    marker)
      v=$(make_venv marker); install_torch_cuda "$v"   # pre-seed so marker-pdf reuses the +cu130 build
      pipi "$v" -r "$REQ/marker.txt"
      "$v/bin/python" -c "import torch;assert torch.cuda.is_available(),'CUDA not available!';print('  marker torch',torch.__version__,'cuda',torch.cuda.is_available())"
      ;;
    resolve)
      v=$(make_venv resolve)                            # CPU-only API/render tier, no torch
      pipi "$v" -r "$REQ/resolve.txt"
      ;;
    *) echo "unknown target: $t (want: nougat marker resolve)"; exit 1;;
  esac
done

echo
echo "Done. Venvs in $OCR_VENV_DIR. Next:"
echo "  scripts/run_ocr.sh $OCR_PROJECT_DIR/samples/sample.pdf"
