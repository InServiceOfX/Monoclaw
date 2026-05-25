# llama.cpp Native Server (macOS / Metal)

Run llama.cpp HTTP server natively on Apple Silicon with Metal acceleration. No Docker.

Sibling to `../llama-cpp-server/` (Docker + CUDA for Linux).

## Quick Start

```bash
# 1. Copy and edit config
cp config.yml.example config.yml

# 2. Copy a profile
cp profiles/qwen35-9b-distilled-q4.yml.example profiles/qwen35-9b-distilled-q4.yml

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
│   ├── qwen35-9b-distilled-q4.yml     # Q4_K_M profile
│   └── qwen35-9b-distilled-q5.yml     # Q5_K_M profile
└── README.md
```

## Requirements

- `llama-server` binary in PATH (via `brew install llama.cpp` or build from source)
- Python 3 with PyYAML (`pip install pyyaml`)
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
