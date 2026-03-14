# MLX Local Inference — Qwen3.5-27B-Claude-4.6-Opus-Distilled

Local LLM inference on Apple Silicon via [mlx-lm](https://github.com/ml-explore/mlx-lm).

## Model

| Key | Value |
|-----|-------|
| **HF repo** | `mlx-community/Qwen3.5-27B-Claude-4.6-Opus-Distilled-MLX-4bit` |
| **Local cache** | `~/.cache/huggingface/hub/models--mlx-community--Qwen3.5-27B-Claude-4.6-Opus-Distilled-MLX-4bit/snapshots/5f690e9b35c3ebdb7563cdeef0485cefaa2dde62` |
| **Type** | Reasoning/thinking model (Claude 4.6 Opus distilled) |
| **Quant** | 4-bit MLX |
| **Context** | 32 768 tokens |
| **Toolchain** | `/Users/ernestyeung/Prop/openclaw/.venv/bin/mlx_lm.*` |

---

## Scripts

### `chat.sh` — Interactive REPL

Runs `mlx_lm.chat` locally. Context is preserved for the lifetime of the REPL session.

```bash
./chat.sh                  # thinking mode (default)
./chat.sh --no-think       # instruct/non-thinking mode
```

### `serve.sh` — OpenAI-compatible HTTP server

Runs `mlx_lm.server` on `localhost:8080`. Exposes the OpenAI Chat Completions API.

```bash
./serve.sh                 # thinking mode defaults (temp 1.0)
./serve.sh --port 8090     # custom port
./serve.sh --no-think      # instruct mode defaults (temp 0.7)
```

### `test-query.sh` — Quick curl smoke-test

Fires a single request at the running server.

```bash
./test-query.sh                          # default test prompt
./test-query.sh "Explain entropy"        # custom prompt
./test-query.sh "Write a sort" --stream  # streaming
```

---

## Sampling Parameters Reference

This model is a **thinking/reasoning model** distilled from Claude Opus 4.6.
Always give it room to think — `<think>` blocks can consume 300–800 tokens alone.

### Thinking mode (default, recommended)

| Param | Value | Why |
|-------|-------|-----|
| `temperature` | 1.0 | Exploration in reasoning |
| `top_p` | 0.95 | Nucleus sampling |
| `top_k` | 20 | Limits vocabulary breadth |
| `min_p` | 0.0 | Off — top_k handles it |
| `presence_penalty` | 1.5 | Prevents topic repetition |
| `repetition_penalty` | 1.15 | **Critical** for 4-bit quant — prevents looping |
| `max_tokens` | 8192 | Min 4096; 8192 for complex tasks |

### Thinking mode — coding / precision tasks

| Param | Value |
|-------|-------|
| `temperature` | 0.6 |
| `top_p` | 0.95 |
| `top_k` | 20 |
| `presence_penalty` | 0.0 |
| `repetition_penalty` | 1.15 |
| `max_tokens` | 8192 |

### Instruct/non-thinking mode

| Param | Value |
|-------|-------|
| `temperature` | 0.7 |
| `top_p` | 0.8 |
| `top_k` | 20 |
| `presence_penalty` | 1.5 |
| `repetition_penalty` | 1.15 |
| `max_tokens` | 4096 |

> ⚠️ **Never set `max_tokens` below 4096.** The `<think>` block alone can hit 800 tokens.
> If the limit is reached before `</think>` is emitted, the model loops indefinitely.

---

## API Examples (server running)

### Basic completion
```bash
curl localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is entropy?"}],
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 20,
    "repetition_penalty": 1.15,
    "presence_penalty": 1.5,
    "max_tokens": 8192
  }'
```

### Streaming
```bash
curl localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Write a quicksort in Python"}],
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "repetition_penalty": 1.15,
    "max_tokens": 8192,
    "stream": true
  }'
```

### Disable thinking (instruct mode)
Pass `enable_thinking: false` via `chat_template_args` — or set in `serve.sh --no-think`.

### List models
```bash
curl localhost:8080/v1/models
```

---

## OpenClaw Integration (coming later)

To use this server as a provider in OpenClaw, you'll add a custom provider entry
pointing to `http://localhost:8080/v1` with model name
`mlx-community/Qwen3.5-27B-Claude-4.6-Opus-Distilled-MLX-4bit`.
See `openclaw.json` docs once server is validated.
