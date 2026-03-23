# TensorRT-LLM local serving (config-driven)

This folder provides a small config-driven wrapper around `trtllm-serve` so model path, host/port, parsing mode, and conservative single-GPU limits are not hardcoded into ad-hoc commands.

## Files

- `trtllm_runner.py` — runs `trtllm-serve serve` or sends a probe request from YAML settings
- `trtllm_config.example.yml` — baseline example config for local Qwen3 serving
- `extra_llm_config.qwen3-0.6b.example.yml` — optional TensorRT-LLM YAML passed via `--config`
- `serve.sh` — thin wrapper around `trtllm_runner.py serve`
- `test-query.sh` — thin wrapper around `trtllm_runner.py probe`

## Quick start

Inside the environment or container where `trtllm-serve` exists:

```bash
cd /home/ernest/.openclaw/workspace/workspace2/repos/Monoclaw/Deployments/Scripts/trtllm

# first run auto-copies trtllm_config.example.yml -> trtllm_config.yml
./serve.sh
```

Then edit `trtllm_config.yml` and set the exact paths and limits you want.

For a smoke test from another shell:

```bash
./test-query.sh
```

Or override the prompt:

```bash
./test-query.sh --prompt "Where is New York?"
```

## Why this setup

- Keeps your `trtllm-serve` invocation reproducible
- Moves model path and serve knobs into YAML
- Makes it easier to carry a known-good config into Docker wrappers later
- Gives a repeatable probe request instead of retyping curl payloads

## Recommended first stable baseline for 8 GB-ish VRAM

For `Qwen3-0.6B` on a constrained GPU, start conservatively:

- `backend: pytorch`
- `host: 0.0.0.0`
- `port: 30000`
- `max_batch_size: 32`
- `max_num_tokens: 2048`
- `max_seq_len: 8192`
- `kv_cache_free_gpu_memory_fraction: 0.72`
- no chunked prefill initially
- no custom template initially unless needed

This is intentionally less aggressive than the defaults you saw in the logs (`max_num_requests=2048`, `max_batch_size=2048`, inferred `max_seq_len=40960`). Those defaults can be valid, but they are not what I would choose as a first debug target on a ~8 GB card.

## Likely reason your curl failed

Your request shape is probably fine. More likely causes are:

1. **Server not actually bound on localhost**
   - if `trtllm-serve` was started inside a Docker container without `-p 30000:30000`, host-side `curl localhost:30000` cannot reach it.
   - if the server bound to `127.0.0.1` inside the container, even publishing the port may still not expose it correctly; use `--host 0.0.0.0`.

2. **Server not ready yet when curl was sent**
   - `INFO: Application startup complete.` is good, but wait until it is fully idle and then probe `/health` or `/v1/models` first.

3. **Serve command syntax mismatch across versions**
   - docs show the subcommand form: `trtllm-serve serve [OPTIONS] MODEL`
   - your direct invocation used `trtllm-serve /Data/... --port 30000`
   - that may still work through compatibility handling, but I want us on the explicit `serve` form to reduce ambiguity.

4. **Process crashed on first request**
   - `connection reset by peer` usually means something accepted the TCP connection and then died or forcibly closed it.
   - if that happens again, the server terminal logs immediately after the request are the important clue.

## Suggested manual debug order

Inside the container, prefer this explicit form:

```bash
trtllm-serve serve /Data/Models/LLM/Qwen/Qwen3-0.6B \
  --host 0.0.0.0 \
  --port 30000 \
  --backend pytorch \
  --served_model_name Qwen3-0.6B \
  --max_batch_size 32 \
  --max_num_tokens 2048 \
  --max_seq_len 8192 \
  --free_gpu_memory_fraction 0.72
```

Then, from inside the same container first:

```bash
curl -sS http://127.0.0.1:30000/health
curl -sS http://127.0.0.1:30000/v1/models
```

If those work, test chat from inside the container.
Only after that, test from the host — and only if Docker published the port.

## Host/container networking reminder

If the server runs inside Docker and you want host-side access, the container run command needs port publishing, for example:

```bash
docker run ... -p 30000:30000 ...
```

Your logged `docker run` command had **Ports: 0** and no `-p` flags, so host-side `curl http://localhost:30000/...` would not be expected to work.

That is the first thing I would fix.
