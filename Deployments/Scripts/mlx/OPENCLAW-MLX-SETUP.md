# OpenClaw + MLX Local Model Setup Guide

> **Audience:** OpenClaw agents and human operators setting up a locally-served MLX model
> (via `mlx_lm.server`) and registering it in OpenClaw's config so it can be used as a
> fallback or primary model.

---

## ⚠️ CRITICAL: Always Use the Snapshot Path — Never the HF Slug

> **This is the single most important thing in this document.**

When adding a model to `openclaw.json`, the `id` field **must be the full absolute local
snapshot path**, NOT the HuggingFace repo slug.

| ❌ WRONG — triggers HF API call | ✅ CORRECT — local only, no network |
|---|---|
| `Jackrong/MLX-Qwen3.5-9B-...` | `/Users/you/.cache/.../snapshots/<hash>` |

**What goes wrong with the slug:** `mlx_lm.server` will call
`https://huggingface.co/api/models/<slug>/revision/main` on every request to validate the
model ID. This causes:
- Slow first response (network round-trip before inference even starts)
- 401/404 errors if HF is unreachable or the model is private
- Unnecessary re-fetching of tokenizer/config files even if already cached locally

**Confirmed in production logs (Ernest's Mac mini, 2026-04-06):**
```
# BAD — slug triggered HF lookup:
INFO - HTTP Request: GET https://huggingface.co/api/models/Jackrong/MLX-Qwen3.5-9B-.../revision/main "HTTP/1.1 200 OK"
Fetching 6 files: 100%|...| 6/6 [00:00<00:00, 30652.65it/s]  ← unnecessary!

# GOOD — snapshot path goes directly to inference, no network call
```

---

## How to Find the Snapshot Path

The fastest method is to ask the **running server** — it lists all valid IDs including
the full local path:

```bash
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool
```

Look for the entry whose `id` starts with `/` (absolute path). That's the one to use.

Alternatively, HF cache layout on disk:

```
~/.cache/huggingface/hub/
  models--<org>--<model-name>/
    snapshots/
      <hash>/               ← use this full path as the model id
        config.json
        *.safetensors / *.npz
        tokenizer.json
    refs/
      main                  ← contains the <hash> string for the active snapshot
```

```bash
# Read the active snapshot hash directly
cat ~/.cache/huggingface/hub/models--<org>--<model>/refs/main
# → 1b18b447b4d2e67b93ec4c0118b6d322657f455f  (example)

# Full path would be:
# ~/.cache/huggingface/hub/models--<org>--<model>/snapshots/<hash>
```

### Ernest's Mac mini — current snapshot paths

| Model | Snapshot path |
|-------|--------------|
| Qwen3.5-9B Claude Opus Distilled v2 4-bit | `/Users/ernestyeung/.cache/huggingface/hub/models--Jackrong--MLX-Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit/snapshots/1b18b447b4d2e67b93ec4c0118b6d322657f455f` |
| Qwen3.5-9B Claude Opus Distilled v2 6-bit | `/Users/ernestyeung/.cache/huggingface/hub/models--Jackrong--MLX-Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2-6bit/snapshots/ef7b7361f75713124828569d66fff516ff2d092f` |
| Qwen3.5-4B Claude Opus Distilled v2 4-bit | `/Users/ernestyeung/.cache/huggingface/hub/models--Jackrong--MLX-Qwen3.5-4B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit/snapshots/37404f5862c3f0b715b69204361d6cb9ade08e59` |

---

## openclaw.json: Three Places to Update

`openclaw.json` is typically at `~/.openclaw/openclaw.json`.

### 1. `models.providers.mlx-local.models`

```json
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
```

### 2. `agents.defaults.model.fallbacks`

```json
"fallbacks": [
  "anthropic/claude-opus-4-6",
  "anthropic/claude-haiku-4-5",
  "mlx-local//full/absolute/path/to/snapshots/<hash>"
]
```

Note the double `//` — that's `mlx-local/` + the absolute path starting with `/`.

### 3. `agents.defaults.models`

```json
"models": {
  "anthropic/claude-sonnet-4-6": {},
  "mlx-local//full/absolute/path/to/snapshots/<hash>": {}
}
```

---

## Performance: Dealing with Long Context

A 9B model processes ~2048 tokens every ~5 seconds during prefill on Apple Silicon.
If OpenClaw sends a 63k-token session context, that's **~2.5 minutes just reading the
prompt** before generating a single output token.

**Mitigations (all now set in the profiles):**

| Setting | What it does |
|---------|-------------|
| `prefill_step_size: 4096` | Larger chunks per prefill step — faster on Apple Silicon |
| `prompt_cache_size: 4` | Caches up to 4 KV states; repeated context is free after first hit |
| `max_tokens: 4096` | Caps output length — don't let thinking models ramble |
| `--mode instruct` | Disables thinking chain; ~3–5× faster responses for simple queries |

**Use the 4B model for agent fallback** — same architecture, ~2× faster prefill, ~2.5 GB
vs ~5 GB RAM, good enough for most assistant queries:

```bash
./serve.sh qwen35-4b-claude-opus-distilled-4bit
```

---

## Verifying It Works (No HF Lookup)

Start the server and watch the logs. A clean first-inference should look like:

```
INFO - Starting httpd at 127.0.0.1 on port 8080...
INFO - Prompt processing progress: 15/18
INFO - KV Caches: ...
```

**No** `HTTP Request: GET https://huggingface.co/...` lines. If you see those, the model
ID in your `openclaw.json` is still a slug — fix it to the snapshot path.

Quick curl test:

```bash
SNAP="/full/absolute/path/to/snapshots/<hash>"
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$SNAP\", \"messages\": [{\"role\": \"user\", \"content\": \"Say hello in 5 words.\"}], \"max_tokens\": 64}" \
  | python3 -m json.tool
```

A good response has `choices[0].message.content` and no `error` key.

After editing `openclaw.json`, restart the gateway:

```bash
openclaw gateway restart
```

---

## Serving

```bash
cd Deployments/Scripts/mlx
./serve.sh <profile-name>          # e.g. qwen35-4b-claude-opus-distilled-4bit
./serve.sh <profile> --mode instruct   # faster, no thinking chain
```

Profiles: `profiles/<name>.yml` (copy from `profiles/<name>.yml.example`).
Global config (host, port, `mlx_bin_dir`): `mlx_config.yml` (copy from `mlx_config.yml.example`).

---

*Last updated: 2026-04-06 by TARS (Ernest's OpenClaw agent)*
