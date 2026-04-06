# MLX Hardware Tuning Guide

> **Audience:** OpenClaw agents and human operators running MLX models on Apple Silicon.
> Covers `mlx_lm.server` (text) and `mlx_vlm.server` (vision) parameter tuning by
> hardware tier.

---

## Quick Reference: Recommended Settings by Hardware

### Mac mini M4 Pro (64 GB Unified Memory)

| Parameter | mlx_lm (text) | mlx_vlm (vision) |
|-----------|---------------|-------------------|
| `prefill_step_size` | 4096 | 8192 |
| `prompt_cache_size` | 4 | — (not supported) |
| `decode_concurrency` | 1–2 | — (not supported) |
| `prompt_concurrency` | 1 | — (not supported) |
| `kv_bits` | Avoid for RotatingKVCache models | ❌ Avoid (Gemma 4) |
| `max_kv_size` | 32768–65536 | 65536 |
| Comfortable models | 9B 4-bit, 9B 6-bit, 27B 4-bit | E4B 4-bit, E4B mxfp8 |
| Tight but works | 27B 6-bit (~18 GB) | — |

### MacBook Pro M5 (32 GB Unified Memory)

| Parameter | mlx_lm (text) | mlx_vlm (vision) |
|-----------|---------------|-------------------|
| `prefill_step_size` | 2048 | 4096 |
| `prompt_cache_size` | 2 | — |
| `decode_concurrency` | 1 | — |
| `prompt_concurrency` | 1 | — |
| `kv_bits` | Avoid for RotatingKVCache models | ❌ Avoid (Gemma 4) |
| `max_kv_size` | 16384–32768 | 32768 |
| Comfortable models | 4B 4-bit, 9B 4-bit | E4B 4-bit |
| Tight but works | 9B 6-bit (~8 GB) | E4B mxfp8 (~10 GB) |
| Avoid | 27B anything | — |

### MacBook Air / base MacBook Pro (16 GB Unified Memory)

| Parameter | mlx_lm (text) | mlx_vlm (vision) |
|-----------|---------------|-------------------|
| `prefill_step_size` | 1024 | 2048 |
| `prompt_cache_size` | 1 | — |
| `decode_concurrency` | 1 | — |
| `prompt_concurrency` | 1 | — |
| `kv_bits` | Avoid for RotatingKVCache models | ❌ Avoid (Gemma 4) |
| `max_kv_size` | 8192–16384 | 16384 |
| Comfortable models | 4B 4-bit (~2.5 GB) | E4B 4-bit (tight) |
| Avoid | 9B 6-bit, anything 27B | E4B mxfp8 |

---

## Parameter Deep Dive

### `prefill_step_size`

How many tokens the GPU processes per step when reading the prompt. Larger = fewer
kernel launches = faster prefill, but with a temporary memory spike.

**Rule of thumb:** Set as high as your memory allows. The spike is temporary (freed
after prefill completes).

| Memory | Recommended |
|--------|------------|
| 16 GB | 1024 |
| 32 GB | 2048–4096 |
| 64 GB | 4096–8192 |

**Diminishing returns:** Beyond ~4096, gains are marginal because Apple Silicon memory
bandwidth (~273 GB/s on M4 Pro) becomes the bottleneck, not kernel overhead.

### `prompt_cache_size` (mlx_lm only)

Number of distinct KV caches to keep in memory. When OpenClaw sends the same session
context repeatedly, the cached KV state means zero prefill cost on the second hit.

**Tradeoff:** Each cache slot costs `context_length × model_hidden_size × 2` bytes.
For a 9B model with 32k context, each slot is ~2 GB.

| Memory | Recommended |
|--------|------------|
| 16 GB | 1 |
| 32 GB | 2 |
| 64 GB | 4 |

### `max_kv_size`

Maximum number of tokens in the KV cache. Limits how much context the model can
actually attend to, regardless of what OpenClaw sends.

**For agent use:** OpenClaw can send 60–80k tokens of session context. If you set
`max_kv_size` lower, the server will truncate — which may cause incoherent responses.
Set it as high as your memory allows.

| Memory | Recommended |
|--------|------------|
| 16 GB | 8192–16384 |
| 32 GB | 16384–32768 |
| 64 GB | 32768–65536 |

### `kv_bits` — ⚠️ Read Before Using

Quantizes the KV cache at runtime (separate from model weight quantization).

**DO NOT USE with Gemma 4 or any model that uses RotatingKVCache (sliding window
attention).** You'll get `NotImplementedError: RotatingKVCache Quantization NYI`.

**How to check:** Look at the model's `config.json` for `sliding_window`. If present,
avoid `kv_bits`.

For models that support it (standard attention only), `kv_bits: 4` roughly halves KV
cache memory — useful on 16 GB machines.

### `decode_concurrency` / `prompt_concurrency` (mlx_lm only)

How many requests to batch together. Higher values improve throughput when multiple
requests arrive simultaneously, but increase per-request latency and memory.

**For single-user OpenClaw:** Keep both at 1. Only increase if you're serving multiple
agents/sessions simultaneously from the same model.

---

## Model Selection by Hardware

### Text Models (mlx_lm)

| Model | Quant | RAM (approx) | Quality | Speed | Best for |
|-------|-------|-------------|---------|-------|----------|
| Qwen3.5-4B Distilled | 4-bit | ~2.5 GB | Good | Fast | Agent fallback, quick queries |
| Qwen3.5-9B Distilled | 4-bit | ~5 GB | Very good | Medium | General agent use |
| Qwen3.5-9B Distilled | 6-bit | ~7 GB | Better | Medium | Quality-sensitive tasks |
| Qwen3.5-27B Distilled | 4-bit | ~15 GB | Excellent | Slow | When quality matters most |
| Qwen3.5-27B Distilled | 6-bit | ~18 GB | Best | Slowest | 64 GB machines only |

### Vision Models (mlx_vlm)

| Model | Quant | RAM (approx) | Quality | Best for |
|-------|-------|-------------|---------|----------|
| Gemma 4 E4B IT | 4-bit | ~5 GB | Good | General vision tasks |
| Gemma 4 E4B IT | mxfp8 | ~10 GB | Better | 32 GB+ machines |

### 32 GB MacBook Pro M5 — Recommended Combo

Run **both** servers simultaneously:
- `mlx_lm` on port 8080: **Qwen3.5-9B 4-bit** (~5 GB) or **4B 4-bit** (~2.5 GB)
- `mlx_vlm` on port 8081: **Gemma 4 E4B 4-bit** (~5 GB)

Total: ~10 GB, leaving ~22 GB for macOS + apps. Comfortable.

### 64 GB Mac mini M4 Pro — Recommended Combo

- `mlx_lm` on port 8080: **Qwen3.5-9B 6-bit** (~7 GB) for quality
- `mlx_vlm` on port 8081: **Gemma 4 E4B 4-bit** (~5 GB)

Total: ~12 GB. You could even run 27B 4-bit (~15 GB) and still have 40+ GB free.

---

## The Real Bottleneck: Context Size

The single biggest factor in response time is **how many tokens OpenClaw sends as
context**. A typical long session can accumulate 60–80k tokens.

At ~1000 tok/s prefill (Gemma 4 E4B 4-bit on M4 Pro), 80k tokens = **80 seconds** just
to read the prompt. No parameter tuning fixes this.

**Mitigations:**
1. Use fresh sessions for local model queries (don't carry 80k of Claude conversation)
2. Use local models as fallbacks, not primary (they kick in when Claude is unavailable)
3. Use `--mode instruct` (mlx_lm) to disable thinking chains — faster output
4. `prompt_cache_size > 1` (mlx_lm) — repeat queries to same context are free

---

## Gotchas & Lessons Learned

1. **HF slug vs snapshot path:** Always use the full local snapshot path as model ID in
   `openclaw.json`. See `mlx/OPENCLAW-MLX-SETUP.md` for details.

2. **RotatingKVCache + kv_bits:** Gemma 4 (and any model with `sliding_window` in
   config.json) will crash with `--kv-bits`. Leave it unset.

3. **mlx_lm vs mlx_vlm ports:** Run them on different ports (default: 8080 and 8081).
   Register them as separate providers in `openclaw.json` (`mlx-local` and `mlx-vlm`).

4. **Token naming:** The `model` field in API requests must match one of the IDs from
   `GET /v1/models`. The full snapshot path always works.

5. **Prefill is not generation:** `prefill_step_size` only affects prompt processing
   speed. Generation speed (tok/s for output) is determined by model size and hardware.

---

*Last updated: 2026-04-06 by TARS (Ernest's OpenClaw agent)*
