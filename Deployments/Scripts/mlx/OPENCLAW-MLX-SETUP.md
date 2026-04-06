# OpenClaw + MLX Local Model Setup Guide

> **Audience:** OpenClaw agents and human operators setting up a locally-served MLX model
> (via `mlx_lm.server`) and registering it in OpenClaw's config so it can be used as a
> fallback or primary model — **without triggering a Hugging Face remote lookup**.

---

## The Key Problem: Avoiding HuggingFace Remote Lookups

When you register a model in `openclaw.json` under `models.providers.<provider>.models`,
the `id` field is what OpenClaw passes to the upstream API as the `model` parameter in
each request.

`mlx_lm.server` accepts **any** of the following as a valid model ID (you can verify by
calling `GET /v1/models` on the running server):

1. The short HF repo slug (e.g. `Jackrong/MLX-Qwen3.5-9B-...`) — **will trigger a HF
   network lookup** if mlx-lm tries to re-resolve it at inference time.
2. The full absolute path to the local snapshot directory (e.g.
   `/Users/you/.cache/huggingface/hub/models--Jackrong--MLX-.../snapshots/<hash>`) —
   **no network call, always safe**.

**Use the full absolute snapshot path as the model `id` in `openclaw.json`.**

### Why the snapshot path?

When `mlx_lm.server` loads a model, it resolves the path at startup and registers the
loaded model under *all* of the IDs listed above. But when a request comes in with a
short HF slug as `model`, mlx-lm may attempt to call the HF API to validate/resolve
the repo, causing a 401 or 404 if the network is unavailable or auth is missing.

Using the full local path bypasses this entirely — the server sees a path it already
has loaded and routes the request directly.

---

## How to Find the Right Snapshot Path

Models downloaded via `huggingface-cli` or `huggingface_hub` are stored in the HF cache:

```
~/.cache/huggingface/hub/
  models--<org>--<model-name>/
    snapshots/
      <hash>/          ← this is the directory with config.json, weights, tokenizer
        config.json
        *.safetensors (or *.npz for MLX)
        tokenizer.json
        ...
    refs/
      main             ← contains the hash of the "main" branch snapshot
```

**To find the correct snapshot directory:**

```bash
# Option 1: Read the refs/main file to get the active hash
cat ~/.cache/huggingface/hub/models--<org>--<model>/refs/main

# Option 2: List snapshots and pick the most recent one
ls -lt ~/.cache/huggingface/hub/models--<org>--<model>/snapshots/

# Option 3: Ask the running mlx_lm.server — it lists all valid IDs including the path
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool
```

The `/v1/models` response will include an entry whose `id` is the full absolute path —
use that exact string.

### Example (Ernest's Mac mini, Qwen3.5-9B 4-bit)

```
/Users/ernestyeung/.cache/huggingface/hub/models--Jackrong--MLX-Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit/snapshots/1b18b447b4d2e67b93ec4c0118b6d322657f455f
```

This path was obtained by running `curl -s http://127.0.0.1:8080/v1/models` and picking
the entry whose `id` starts with `/Users/`.

---

## openclaw.json: Where to Add the Model

`openclaw.json` is typically at:
- `~/.openclaw/openclaw.json` (standard install)
- Or wherever `OPENCLAW_CONFIG` points

You need to touch **three locations**:

### 1. `models.providers.<provider>.models` — register the model

```json
"models": {
  "providers": {
    "mlx-local": {
      "baseUrl": "http://127.0.0.1:8080/v1",
      "api": "openai-completions",
      "models": [
        {
          "id": "/full/absolute/path/to/snapshots/<hash>",
          "name": "Human-readable name (MLX Local)",
          "reasoning": true,
          "contextWindow": 131072,
          "maxTokens": 8192
        }
      ]
    }
  }
}
```

> ⚠️ The `id` **must be the full absolute path** — not the HF slug — to avoid
> triggering a remote lookup.

### 2. `agents.defaults.model.fallbacks` — add as a fallback

```json
"agents": {
  "defaults": {
    "model": {
      "primary": "anthropic/claude-sonnet-4-6",
      "fallbacks": [
        "anthropic/claude-opus-4-6",
        "anthropic/claude-haiku-4-5",
        "mlx-local/<full-snapshot-path>"
      ]
    }
  }
}
```

The fallback reference format is `<provider>/<model-id>`. Since the model ID contains
slashes (it's a path), this becomes `mlx-local//full/absolute/path/...`.

### 3. `agents.defaults.models` — allowlist the model

```json
"agents": {
  "defaults": {
    "models": {
      "anthropic/claude-sonnet-4-6": {},
      "mlx-local/<full-snapshot-path>": {}
    }
  }
}
```

---

## Verifying It Works

After editing `openclaw.json`, restart the gateway:

```bash
openclaw gateway restart
```

Then test the model directly against the running `mlx_lm.server`:

```bash
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/full/absolute/path/to/snapshots/<hash>",
    "messages": [{"role": "user", "content": "Say hello in exactly 5 words."}],
    "max_tokens": 64
  }' | python3 -m json.tool
```

A successful response will have `choices[0].message.content` populated and no `error` key.

---

## Serving the Model

Use the profile-based `serve.sh` in this directory:

```bash
cd Deployments/Scripts/mlx
./serve.sh <profile-name>
# e.g.
./serve.sh qwen35-9b-claude-opus-distilled-4bit
```

Profiles live in `profiles/<name>.yml` (copy from `profiles/<name>.yml.example`).
Global settings (host, port, mlx_bin_dir) live in `mlx_config.yml` (copy from
`mlx_config.yml.example`).

See the `profiles/*.yml.example` files for model-specific sampling defaults with
comments explaining the rationale.

---

## Quick Reference: Model ID Formats

| Format | Example | HF Lookup? | Use for |
|--------|---------|------------|---------|
| HF slug | `Jackrong/MLX-Qwen3.5-9B-...` | ✅ Yes (avoid) | Never in openclaw.json |
| Full snapshot path | `/Users/you/.cache/.../snapshots/<hash>` | ❌ No | openclaw.json `id` field |

---

*Last updated: 2026-04-06 by TARS (Ernest's OpenClaw agent)*
