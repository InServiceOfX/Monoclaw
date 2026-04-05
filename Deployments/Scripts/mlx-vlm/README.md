# MLX-VLM Local Inference (config + profile driven)

This folder is a **dedicated wrapper** for `mlx_vlm` (multimodal) models, sibling to the text-only `mlx/` folder.

## Key Design Decisions

- `mlx_vlm_bin_dir`: points to the directory containing the `mlx_vlm.*` binaries (usually your venv `bin/`).
- `model_path` is **required** in every profile.
- `mlx_vlm_config.yml` holds **non-model-specific** settings (host, port, common KV cache tuning).
- Profile files (`profiles/*.yml`) hold **model-specific** settings (model path, temperature, max_tokens, kv quantization, image resize, thinking params, etc.).
- Strongly prefer `--profile <name>` over using the main config directly.

## Quick Start

```bash
cd Deployments/Scripts/mlx-vlm

# Start server with default profile
./serve.sh --profile gemma-4-e4b-it-4bit

# Chat (interactive)
./chat.sh --profile gemma-4-e4b-it-4bit

# Test the server
./test-query.sh
```

## Recommended for 32GB M5 MacBook Pro

Use conservative KV cache + prefill settings to stay under memory limits with margin.

See `profiles/gemma-4-e4b-it-4bit.yml` for tuned values.
