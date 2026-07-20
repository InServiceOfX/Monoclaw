# llama.cpp CUDA Server Deployment

Configurable Docker-based launcher for [llama.cpp HTTP server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) with CUDA acceleration.

Mirrors the TensorRTLLMFixed deployment pattern: global `config.yml` + per-model `profiles/*.yml`.

## Quick Start

```bash
# 1. Copy and edit config
cp config.yml.example config.yml

# 2. Launch a model
./launch.sh qwen35-9b-distilled

# Preview the exact Docker/llama-server command without starting anything
./launch.sh --dry-run qwen35-9b-distilled

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

Supported profile sampling defaults include `temperature`, `top_p`, `top_k`,
`min_p`, and `repeat_penalty`. API clients may override them per request.

## Qwythos-9B

Two local text-only profiles are included:

```bash
# Recommended on the local 8 GB RTX 3070: Q4_K_M with 32K context
./launch.sh qwythos-9b-q4

# Higher-quality Q5_K_M with a safer 16K context
./launch.sh qwythos-9b-q5
```

Both use the model-card sampling defaults (`temperature=0.6`, `top_p=0.95`,
`top_k=20`, `repeat_penalty=1.05`), one server slot, Flash Attention, and q4_0
KV cache. The GGUF embeds YaRN scaling for up to 1M tokens, but that context is
not practical on an 8 GB GPU. To experiment with more context, override the
profile value and increase gradually:

```bash
./launch.sh qwythos-9b-q4 -c 65536
```

Vision and MTP profiles are intentionally omitted until their full GGUF files
are downloaded. A ~135-byte `*.gguf` is only a Git LFS pointer, not a loadable
model or projector.

## Docker Image

Uses the lightweight CUDA server image:
```
ghcr.io/ggml-org/llama.cpp:server-cuda
```

We always point to local GGUF files — never rely on llama.cpp to download models.
We always use CUDA — no CPU-only mode.
