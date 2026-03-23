# TensorRT-LLM local serving (config-driven)

This folder provides a config-driven wrapper around `trtllm-serve` with a **base config + per-model profiles** layout, so model path, host/port, parsing mode, and model-specific limits are not hardcoded into ad-hoc commands.

## Files

- `trtllm_runner.py` — runs `trtllm-serve serve` or sends a probe request from YAML settings
- `trtllm_config.example.yml` — base shared defaults
- `profiles/` — per-model override files you switch with `--profile`
- `extra_llm_config.qwen3-0.6b.example.yml` — optional TensorRT-LLM YAML passed via `--config`
- `serve.sh` — thin wrapper around `trtllm_runner.py serve`
- `test-query.sh` — one-shot probe request
- `chat.sh` — interactive terminal chat client from the host or any shell with Python
- `health.sh` — check `/health`
- `models.sh` — check `/v1/models`

## Recommended layout

Best choice for your use case: **one generic base config plus separate model profile YAMLs**.

Why I think this is the right balance:

- shared defaults live in one place
- model-specific paths and limits stay isolated
- switching models is simple
- moving to another desktop just means editing or cloning a profile
- it avoids turning one giant YAML into a swamp

## Quick start

```bash
cd /home/ernest/.openclaw/workspace/workspace2/repos/Monoclaw/Deployments/Scripts/trtllm
cp trtllm_config.example.yml trtllm_config.yml
cp profiles/qwen3-0.6b.example.yml profiles/qwen3-0.6b.yml
```

Then edit `trtllm_config.yml` only for shared defaults, and edit `profiles/qwen3-0.6b.yml` for model-specific values.

Important config split:

**Base config (`trtllm_config.yml`)**
- shared command defaults
- shared endpoint defaults
- shared interactive/probe defaults
- shared modes

**Profile (`profiles/<name>.yml`)**
- `paths.model_path` = where the model exists from the point of view of `trtllm-serve`
  - inside a container this may be something like `/Data/Models/...`
- `paths.host_model_path` = optional note for the host-side real path on that machine
- `serve.served_model_name`
- model-specific batch/token/cache limits
- model-specific endpoint/port if you want

Host/client split still applies:
- `endpoint.host` / `endpoint.port` = where the host-side helper scripts should connect
- `serve.host` / `serve.port` = what `trtllm-serve` should bind to when launched via `serve.sh`

For a smoke test from another shell:

```bash
TRTLLM_PROFILE=qwen3-0.6b ./health.sh
TRTLLM_PROFILE=qwen3-0.6b ./models.sh
TRTLLM_PROFILE=qwen3-0.6b ./test-query.sh
```

Or override the prompt:

```bash
./test-query.sh --prompt "Where is New York?"
```

For interactive chatting from the host:

```bash
TRTLLM_PROFILE=qwen3-0.6b ./chat.sh
```

Inside the interactive chat client:

- type a message and press Enter
- `/reset` clears conversation history
- `/health` checks server health
- `/models` lists served models
- `/exit` or `/quit` leaves chat

## Why this setup

- Keeps your `trtllm-serve` invocation reproducible
- Separates shared defaults from per-model details
- Lets you keep host-side and container-side model paths in one profile
- Makes it easier to carry a known-good config into Docker wrappers later
- Gives a repeatable probe request instead of retyping curl payloads

## Profile selection

There are two easy ways to select a profile.

### Option A: environment variable

```bash
TRTLLM_PROFILE=qwen3-0.6b ./chat.sh
TRTLLM_PROFILE=qwen3-0.6b ./serve.sh
```

### Option B: direct runner usage

```bash
python3 trtllm_runner.py --config trtllm_config.yml --profile qwen3-0.6b chat
python3 trtllm_runner.py --config trtllm_config.yml --profile qwen3-0.6b serve
```

Profiles are resolved from:
- `profiles/<name>`
- `profiles/<name>.yml`
- `profiles/<name>.yaml`

You can also pass an explicit path to a YAML file.

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
