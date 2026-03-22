# SGLangDirect — Qwen3.5-9B AWQ 4-bit

Optimized SGLang deployment for `cyankiwi/Qwen3.5-9B-AWQ-4bit` on RTX 3060 (device=1, 12 GB).

No `docker_builder` / `run_configuration.yml` required — just `launch.sh`.

## Model

| Property | Value |
|---|---|
| Architecture | Qwen3_5ForConditionalGeneration (VLM) |
| Weights | AWQ INT4 (compressed-tensors), ~5-6 GB on GPU |
| Vision encoder | Present (Qwen3.5 VL), NOT quantized (~1 GB) |
| Native context | 262,144 tokens |
| Quant method | `compressed-tensors` (auto-detected by SGLang) |
| SGLang requirement | Main branch: `lmsysorg/sglang:latest` |

## Usage

```bash
# Interactive / coding (default)
./launch.sh fast

# Long document / research (131K context)
./launch.sh longctx

# Low VRAM / running alongside other GPU processes
./launch.sh lowvram
```

API endpoint: `http://localhost:30000/v1` (OpenAI-compatible)

## Profiles

| Profile | Context | mem-fraction-static | chunked-prefill | max-requests | Notes |
|---|---|---|---|---|---|
| `fast` | 32768 | 0.82 | 8192 | auto | Interactive, lowest latency |
| `longctx` | 131072 | 0.78 | 4096 | 4 | Long docs, research |
| `lowvram` | 16384 | 0.72 | 2048 | 2 | Co-existing with other GPU work |

## Tuning

After startup, check logs for:
```
available_gpu_mem=X.XX GB
```
- 5–8 GB = good
- >8 GB = increase `mem-fraction-static` in 0.01 steps
- OOM = decrease `mem-fraction-static` or switch to `lowvram` profile

If prefill OOMs → reduce `chunked-prefill-size` to 2048.
If decode OOMs → reduce `max-running-requests`.

## Design Notes

**Why `launch.sh` instead of `docker_builder`?**
- docker_builder is a Rust binary that parses `run_configuration.yml` to construct `docker run`.
- The same result is a 20-line shell script with no binary dependency.
- Easier to read, diff, and audit — the full `docker run` command is visible.

**Why two files (launch.sh + sglang_configs/*.yaml)?**
- `launch.sh` owns Docker concerns: image, GPU, ports, volumes, shm.
- `sglang_configs/*.yaml` owns SGLang concerns: memory, context, scheduling.
- SGLang's native `--config` support makes this first-class.
- Swap profiles by passing a different argument, not editing a command list.

**Image tag strategy**

`lmsysorg/sglang` tags on Docker Hub:

| Tag pattern | What it is | Stable? |
|---|---|---|
| `latest` | Last release build, CUDA 12.x | Opaque — don't use |
| `latest-cu130` | Pinned release build, CUDA 13.0 | Yes, but old |
| `dev` | Nightly main branch, CUDA 12.x | Rolling, mutable |
| `dev-cu13` | Nightly main branch, CUDA 13.x | Rolling, mutable |
| `nightly-dev-cu13-YYYYMMDD-SHA` | Pinned dated nightly, CUDA 13.x | Yes — use this |

**Use `nightly-dev-cu13-YYYYMMDD-SHA`**: pinned, CUDA 13, main branch. Check the current tag in `launch.sh`.

Qwen3.5 requires the main branch — `latest-cu130` and `latest` are release builds that predate Qwen3.5 support.

To update to a newer nightly:
```bash
docker pull lmsysorg/sglang:dev-cu13   # pulls latest nightly
# Then note the Digest and find the matching nightly-dev-cu13-YYYYMMDD-SHA tag on Docker Hub
# Update DOCKER_IMAGE in launch.sh to the pinned tag
```

## Troubleshooting

### `size_n = 32 is not divisible by tile_n_size = 64`

Full error path: `compressed_tensors_wNa16.py → process_weights_after_loading → gptq_marlin_repack → RuntimeError`

**Cause:** The Marlin GPTQ repack kernel requires `size_n` to be a multiple of 64. Qwen3.5's Gated DeltaNet layers have `in_proj_a` / `in_proj_b` projections with `n=32`. The AWQ recipe correctly excludes these from quantization (they're in the ignore list), but older SGLang release builds try to quantize them anyway via `compressed-tensors` path.

**Fix:** Use `lmsysorg/sglang:nightly-dev-cu13-YYYYMMDD-SHA` (main branch nightly). The main branch has updated `compressed_tensors` handling for hybrid architectures. If the error persists on a new nightly, open an issue on the SGLang repo.

**Also required:** `trust-remote-code: true` in the SGLang config. Qwen3.5's `Qwen3_5ForConditionalGeneration` architecture is not in the standard transformers release — the custom model code correctly handles the DeltaNet layers.

### `Parameter model.layers.N.linear_attn.in_proj_a.weight not found`

These are INFO-level warnings, not errors. The DeltaNet `in_proj_a/b` weights are excluded from the AWQ checkpoint by design (see `recipe.yaml` ignore list). SGLang initializes them as zeros/identity — this is expected behavior for this model variant.

## Vision / Multimodal

The model has a vision encoder. SGLang will load it (`--enable-multimodal` not required —
`Qwen3_5ForConditionalGeneration` is detected as multimodal automatically). To use images,
pass them via the standard `image_url` field in OpenAI-compatible requests. Vision encoder
is NOT quantized (AWQ ignore list explicitly excludes `model.visual.*`).
