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
│   ├── *.yml.example          # Committed templates (portable)
│   └── *.yml                  # Local copies (gitignored; machine paths)
└── README.md
```

## Configuration

- `config.yml` — Docker image, model volumes, GPU device (**gitignored**; copy from `config.yml.example`)
- `profiles/<name>.yml` — Model-specific: GGUF path, context size, GPU layers, KV cache, etc.

**Profiles are machine-local.** Commit only `profiles/*.yml.example`. On each host:

```bash
cp profiles/qwythos-9b-q5.yml.example profiles/qwythos-9b-q5.yml
# edit host_model_path; ensure config.yml volumes cover that host directory
```

`model_path` is the path **inside** the container under the `/models` mount.
`host_model_path` is documentation only (launch.sh does not read it). Different
machines almost always need different `host_model_path` values even when
`model_path` stays the same.

Profiles expose the **most useful** server params. For the full list (60+ options), see:
https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

Supported profile sampling defaults include `temperature`, `top_p`, `top_k`,
`min_p`, and `repeat_penalty`. API clients may override them per request.

## Qwythos-9B

Text-only profiles (copy each `*.yml.example` → `*.yml` before first launch):

```bash
# Q4_K_M — lightest; needs a full download (LFS pointer alone will not load)
./launch.sh qwythos-9b-q4

# Q5_K_M — higher quality (~6.1 GB); good default on 8–12 GB GPUs
./launch.sh qwythos-9b-q5

# Q6_K — best local quality (~6.9 GB); prefer 12 GB VRAM
./launch.sh qwythos-9b-q6
```

All use model-card sampling defaults (`temperature=0.6`, `top_p=0.95`,
`top_k=20`, `repeat_penalty=1.05`, `n_predict`/`max_new_tokens=16384`), one
server slot, Flash Attention, and q4_0 KV cache.

**Context vs generation**

| Setting | Meaning | Model card | Local MS-7885 (RTX 3060 12GB) |
|---|---|---|---|
| `ctx_size` (`-c`) | Prompt + history + generation room | max **1,048,576** (YaRN) | Q5 **589824**, Q6 **524288** (VRAM-limited; 1M OOMs) |
| `n_predict` (`-n`) | Default max **new** tokens | **16384** for `<think>`+answer | keep **16384**; raise per-request `max_tokens` if needed |

The GGUF embeds YaRN for up to 1M tokens. Full 1M needs multi-GPU or KV
offload (card: H100 class ~256k–512k comfortably). On this desktop, raise
context in the local `profiles/*.yml` (gitignored), not by setting
`n_predict` to 1M — generation budget is independent of window size.

```bash
# one-off override without editing the profile
./launch.sh qwythos-9b-q5 -c 262144
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
