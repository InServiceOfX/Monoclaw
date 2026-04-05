# MLX Local Inference (config-driven)

This folder now uses a **YAML config + Python runner** so model paths and sampling are not hardcoded in shell scripts.

## Files

- `mlx_runner.py` — runs `mlx_lm.chat` or `mlx_lm.server` from YAML settings
- `mlx_config.example.yml` — baseline example config (includes recommended mode presets)
- `mlx_config.qwen35-opus-6bit.example.yml` — annotated 6bit example with source-linked rationale
- `mlx_config.qwen35-opus-4bit.example.yml` — annotated 4bit example for lighter local runs
- `mlx_config.yml` — your local config (created automatically from example on first run)
- `chat.sh` — thin wrapper around `mlx_runner.py chat`
- `serve.sh` — thin wrapper around `mlx_runner.py serve`
- `test-query.sh` — curl smoke test (still useful for per-request overrides)

## Quick start

```bash
cd /Users/ernestyeung/.openclaw/workspace/repos/Monoclaw/Deployments/Scripts/mlx

# first run auto-copies mlx_config.example.yml -> mlx_config.yml
./chat.sh
./serve.sh
```

### Profile-based quick switching (new)

```bash
# Start server with specific model
./serve.sh --profile qwen35-9b-claude-opus-distilled-6bit
./serve.sh --profile gemma-4-e4b-it

# Chat mode
./chat.sh --profile qwen35-9b-claude-opus-distilled-6bit --mode instruct
./chat.sh --profile gemma-4-e4b-it
```

Available profiles live in `profiles/`.

## Modes

Supported aliases:

- `thinking` → `thinking_general`
- `coding` → `thinking_coding`
- `instruct` / `no-think` → `instruct_general`
- `reasoning` → `instruct_reasoning`

Examples:

```bash
./chat.sh --coding
./chat.sh --instruct

./serve.sh --coding --port 8090
./serve.sh --instruct --host 0.0.0.0
```

## Why this setup

- Easy to swap 4bit/6bit (or any model) without editing scripts
- Centralized sampling presets from model cards
- Keeps shell scripts minimal and stable

## Important model guardrails

For this model family:

- Keep `max_tokens >= 4096` (runner clamps values below 4096)
- Use `repetition_penalty=1.15` for quantized reasoning (set **per request** in client payloads)

`mlx_lm.server` default params can be overridden by each request, so treat config values as defaults, not hard limits.
