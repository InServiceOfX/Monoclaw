# llama.cpp Native Server (macOS / Metal)

Run llama.cpp HTTP server natively on Apple Silicon with Metal acceleration. No Docker.

Sibling to `../llama-cpp-server/` (Docker + CUDA for Linux).

## Quick Start

```bash
# 1. Copy and edit config
cp config.yml.example config.yml

# 2. Copy a profile
cp profiles/qwen35-9b-distilled-q4.yml.example profiles/qwen35-9b-distilled-q4.yml
# or:
cp profiles/qwen35-9b-distilled-q8.yml.example profiles/qwen35-9b-distilled-q8.yml

# 3. Launch (foreground — Ctrl-C to stop)
./launch.sh qwen35-9b-distilled-q4

# 4. Or launch in background
./launch.sh qwen35-9b-distilled-q4 --background
./launch.sh --stop
```

API endpoint: `http://localhost:8080/v1/chat/completions` (OpenAI-compatible)

## Structure

```
llama-cpp-server-macos/
├── launch.sh                           # Launcher (runs binary directly)
├── config.yml.example                  # Global config template
├── profiles/
│   ├── qwen35-9b-distilled-q4.yml.example
│   ├── qwen35-9b-distilled-q5.yml.example
│   └── qwen35-9b-distilled-q8.yml.example
└── README.md
```

## Requirements

- `llama-server` binary in PATH (via `brew install llama.cpp` or build from source)
- uv virtual environment at the repo root with PyYAML installed:
  `uv venv && uv pip install pyyaml`
- Model GGUF files downloaded locally

## Differences from Docker/CUDA version

| | Docker (Linux) | Native (macOS) |
|---|---|---|
| GPU | NVIDIA CUDA | Apple Metal |
| Runtime | Docker container | Direct binary |
| Model paths | Container volume mounts | Absolute local paths |
| Stop | `docker stop` | `kill` / `--stop` |
| Default mode | Background (detached) | Foreground (exec) |

## Using with --hf vs local paths

This setup prefers local file paths over `--hf`/`--hf-file` flags. After downloading a model with `huggingface-cli download` or letting llama-server cache it, reference the local GGUF directly in `model_path`.

Typical HuggingFace cache path:
```
~/.cache/huggingface/hub/models--<org>--<repo>/snapshots/<hash>/<file>.gguf
```

## Supported Profile Options

The launcher maps common YAML keys to `llama-server` flags:

```yaml
n_gpu_layers: 99        # -ngl 99
ctx_size: 262144        # -c 262144, 256 * 1024
batch_size: 2048        # -b 2048
ubatch_size: 2048       # -ub 2048
parallel: 4             # -np 4
flash_attn: "on"        # -fa on
cache_type_k: q8_0      # --cache-type-k q8_0
cache_type_v: q8_0      # --cache-type-v q8_0
cont_batching: true     # --cont-batching
cache_ram: 8192         # --cache-ram 8192, prompt cache limit in MiB
jinja: true             # --jinja
priority: 1             # --prio 1
```

## Memory Notes

`ctx_size` is a capacity setting, not a guarantee that every Mac should run the
model at that length. For this 9B Qwen profile with Q8 KV cache, 256K context is
roughly a 19GB KV-cache budget before model weights, prompt cache, checkpoints,
Metal overhead, and macOS memory pressure.

Suggested starting points:

- Mac mini M4 Pro / 64GB: Q5 or Q8 at `ctx_size: 262144`, `parallel: 4`,
  `cache_ram: 8192`.
- MacBook Pro M5 / 32GB, Q5: start with `ctx_size: 131072`, `parallel: 1`,
  `cache_ram: 2048`; try `parallel: 2` if memory pressure stays low.
- MacBook Pro M5 / 32GB, Q8: prefer Q5 for long context. If you need Q8,
  start with `ctx_size: 65536`, `parallel: 1`, `cache_ram: 1024`, then test
  `ctx_size: 131072` only if there is enough headroom.

`spec_default: true` maps to `--spec-default`; keep it opt-in and benchmark it
for the model/workload before leaving it on. For newly-added llama.cpp flags,
use `extra_args`:

```yaml
extra_args:
  - --slots
```
