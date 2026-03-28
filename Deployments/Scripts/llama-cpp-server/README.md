# llama.cpp CUDA Server Deployment

Configurable Docker-based launcher for [llama.cpp HTTP server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) with CUDA acceleration.

Mirrors the TensorRTLLMFixed deployment pattern: global `config.yml` + per-model `profiles/*.yml`.

## Quick Start

```bash
# 1. Copy and edit config
cp config.yml.example config.yml

# 2. Launch a model
./launch.sh qwen35-9b-distilled

# 3. Stop
./launch.sh --stop
```

API endpoint: `http://localhost:<port>/v1/chat/completions` (OpenAI-compatible)

## Structure

```
llama-cpp-server/
├── launch.sh                  # Launcher script
├── config.yml.example         # Global config template (→ config.yml)
├── chat.sh                    # Interactive chat client
├── profiles/
│   └── qwen35-9b-distilled.yml  # Per-model profile
└── README.md
```

## Configuration

- `config.yml` — Docker image, model volumes, GPU device
- `profiles/<name>.yml` — Model-specific: GGUF path, context size, GPU layers, KV cache, etc.

Profiles expose the **most useful** server params. For the full list (60+ options), see:
https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

## Docker Image

Uses the lightweight CUDA server image:
```
ghcr.io/ggml-org/llama.cpp:server-cuda
```

We always point to local GGUF files — never rely on llama.cpp to download models.
We always use CUDA — no CPU-only mode.
