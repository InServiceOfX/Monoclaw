#!/usr/bin/env bash
# trtllm_launch.sh — Launch trtllm-serve inside the TensorRTLLMFixed container.
#
# Usage:
#   ./trtllm_launch.sh <profile> [--thinking|--no-think|--instruct|--coding]
#
# Examples:
#   ./trtllm_launch.sh qwen3-1.7b
#   ./trtllm_launch.sh qwen3-1.7b --thinking
#   ./trtllm_launch.sh qwen3-4b --no-think
#   ./trtllm_launch.sh nanbeige4.1-3b
#
# Docker and model settings live in trtllm_config.yml (docker: section).
# Model/serve settings live in profiles/<profile>.yml.
# Stop: Ctrl-C or  docker stop trtllm-serve

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── parse args ────────────────────────────────────────────────────────────────
PROFILE=""
MODE="thinking"

for arg in "$@"; do
    case "$arg" in
        --thinking)          MODE="thinking" ;;
        --no-think|--instruct) MODE="instruct" ;;
        --coding)            MODE="coding" ;;
        --*)                 echo "Unknown flag: $arg" >&2; exit 1 ;;
        *)
            if [[ -z "$PROFILE" ]]; then PROFILE="$arg"
            else echo "Unexpected argument: $arg" >&2; exit 1; fi ;;
    esac
done

if [[ -z "$PROFILE" ]]; then
    echo "Usage: $0 <profile> [--thinking|--no-think|--instruct|--coding]"
    echo ""
    echo "Available profiles:"
    ls "$SCRIPT_DIR/profiles/"*.yml 2>/dev/null \
        | xargs -I{} basename {} .yml \
        | grep -v '^extra_llm' \
        | grep -v '\.example$' \
        | sed 's/^/  /'
    exit 1
fi

PROFILE_FILE="$SCRIPT_DIR/profiles/${PROFILE}.yml"
if [[ ! -f "$PROFILE_FILE" ]]; then
    echo "❌ Profile not found: $PROFILE_FILE"
    exit 1
fi

# ── build docker run command + trtllm-serve args (Python) ─────────────────────
eval "$(python3 - "$SCRIPT_DIR" "$PROFILE_FILE" "$MODE" <<'PYEOF'
import sys, yaml, shlex
from pathlib import Path

script_dir = Path(sys.argv[1])
profile_path = Path(sys.argv[2])
mode = sys.argv[3]

# Load base config
base_cfg = yaml.safe_load((script_dir / "trtllm_config.yml").read_text()) or {}
# Load profile, merge over base
prof_cfg = yaml.safe_load(profile_path.read_text()) or {}

def deep_merge(base, override):
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged

cfg = deep_merge(base_cfg, prof_cfg)

# ── docker settings ──────────────────────────────────────────────────────────
docker = cfg.get("docker", {})
image = docker.get("image", "tensorrt-llm-fixed/release:1.3.0rc0")
gpu_id = str(docker.get("gpu_id", 1))
name = docker.get("container_name", "trtllm-serve")

vol_args = []
for v in docker.get("volumes", []):
    ro = ":ro" if v.get("readonly") else ""
    vol_args += ["-v", f"{v['host']}:{v['container']}{ro}"]

env_args = []
for k, v in docker.get("env", {}).items():
    env_args += ["-e", f"{k}={v}"]

# ── trtllm-serve args ─────────────────────────────────────────────────────────
paths = cfg.get("paths", {})
serve = cfg.get("serve", {})

model_path = paths.get("model_path", "")
if not model_path:
    print(f'echo "❌ no paths.model_path in {profile_path}"; exit 1', file=sys.stdout)
    sys.exit(0)

serve_args = [model_path]

host = serve.get("host", "0.0.0.0")
port = str(serve.get("port", 30000))
serve_args += ["--host", host, "--port", port]

backend = serve.get("backend", "pytorch")
serve_args += ["--backend", backend]

if serve.get("served_model_name"):
    serve_args += ["--served_model_name", serve["served_model_name"]]
if serve.get("gpus_per_node"):
    serve_args += ["--gpus_per_node", str(serve["gpus_per_node"])]
if serve.get("kv_cache_free_gpu_memory_fraction"):
    serve_args += ["--kv_cache_free_gpu_memory_fraction",
                   str(serve["kv_cache_free_gpu_memory_fraction"])]
if serve.get("max_batch_size"):
    serve_args += ["--max_batch_size", str(serve["max_batch_size"])]
if serve.get("max_num_tokens"):
    serve_args += ["--max_num_tokens", str(serve["max_num_tokens"])]
if serve.get("max_seq_len"):
    serve_args += ["--max_seq_len", str(serve["max_seq_len"])]
if serve.get("trust_remote_code"):
    serve_args += ["--trust_remote_code"]
if serve.get("log_level"):
    serve_args += ["--log_level", serve["log_level"]]

# extra_llm_config (--config flag, path inside container)
extra_llm = paths.get("extra_llm_config")
if extra_llm:
    serve_args += ["--config", extra_llm]

# reasoning_parser based on mode
mode_aliases = {
    "thinking": "thinking_general",
    "coding": "thinking_coding",
    "instruct": "instruct_general",
    "no-think": "instruct_general",
}
resolved_mode = mode_aliases.get(mode, mode)
modes = cfg.get("modes", {})
mode_cfg = modes.get(resolved_mode, {})
reasoning_parser = mode_cfg.get("reasoning_parser") or (
    serve.get("reasoning_parser") if resolved_mode != "instruct_general" else None
)
if reasoning_parser:
    serve_args += ["--reasoning_parser", reasoning_parser]

# ── emit shell variables ───────────────────────────────────────────────────────
docker_args = (
    ["--rm", "--name", name,
     "--gpus", f"device={gpu_id}",
     "--network", "host",
     "--ipc=host",
     "--ulimit", "memlock=-1",
     "--ulimit", "stack=67108864"]
    + env_args
    + vol_args
    + [image]
    + ["trtllm-serve", "serve"]
    + serve_args
)

# Export as shell vars
print(f'DOCKER_IMAGE={shlex.quote(image)}')
print(f'CONTAINER_NAME={shlex.quote(name)}')
print(f'SERVE_PORT={shlex.quote(port)}')
docker_cmd = "docker run " + " ".join(shlex.quote(a) for a in docker_args[:-len(serve_args)-2])
print(f'DOCKER_RUN_BASE={shlex.quote(docker_cmd)}')
print(f'TRTLLM_CMD={shlex.quote("trtllm-serve serve " + " ".join(shlex.quote(a) for a in serve_args))}')
print(f'FULL_CMD={shlex.quote("docker run " + " ".join(shlex.quote(a) for a in docker_args))}')
PYEOF
)"

# ── stop existing container ───────────────────────────────────────────────────
if docker ps -q --filter "name=${CONTAINER_NAME}" | grep -q .; then
    echo "⚠️  Stopping existing container: ${CONTAINER_NAME}"
    docker stop "${CONTAINER_NAME}" >/dev/null
fi

# ── launch ────────────────────────────────────────────────────────────────────
echo "=== TensorRT-LLM Serve ==="
echo "Profile  : ${PROFILE}"
echo "Mode     : ${MODE}"
echo "Image    : ${DOCKER_IMAGE}"
echo "trtllm   : ${TRTLLM_CMD}"
echo ""

eval "${FULL_CMD}" &
DOCKER_PID=$!

# ── wait for ready ─────────────────────────────────────────────────────────────
echo "Waiting for server on http://localhost:${SERVE_PORT} ..."
for i in $(seq 1 150); do
    if curl -sf "http://localhost:${SERVE_PORT}/v1/models" >/dev/null 2>&1; then
        echo ""
        echo "✅ Server ready at http://localhost:${SERVE_PORT}"
        echo "   Chat: TRTLLM_PROFILE=${PROFILE} ./chat.sh"
        echo "   Stop: docker stop ${CONTAINER_NAME}  (or Ctrl-C)"
        wait $DOCKER_PID
        exit 0
    fi
    printf "."
    sleep 2
done

echo ""
echo "⚠️  Server did not respond after 5 min."
echo "   Logs: docker logs ${CONTAINER_NAME}"
wait $DOCKER_PID
