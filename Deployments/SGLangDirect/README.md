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

**Why `lmsysorg/sglang:latest` not `latest-cu130`?**
- Qwen3.5 requires SGLang from the main branch (per model card).
- `latest-cu130` is a pinned older build. `latest` tracks the release.
- If you need reproducibility, pin to a specific SHA or tag after confirming compatibility.

## Vision / Multimodal

The model has a vision encoder. SGLang will load it (`--enable-multimodal` not required —
`Qwen3_5ForConditionalGeneration` is detected as multimodal automatically). To use images,
pass them via the standard `image_url` field in OpenAI-compatible requests. Vision encoder
is NOT quantized (AWQ ignore list explicitly excludes `model.visual.*`).
