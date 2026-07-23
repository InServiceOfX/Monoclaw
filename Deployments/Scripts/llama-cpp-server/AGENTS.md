# AGENTS.md — llama.cpp CUDA Server

## Scope

This directory contains a profile-driven Docker launcher for a local CUDA
`llama-server`. Keep model weights and machine-local `config.yml` outside git.

## Workflow

1. Read `README.md`, `PROGRESS.md`, and the target profile.
2. Validate shell with `bash -n launch.sh chat.sh`.
3. Validate YAML profiles with Python/PyYAML.
4. Use `./launch.sh` to list profiles. Do not start or stop a server unless the
   task calls for changing runtime state.

## Conventions

- Commit **templates only**: `profiles/<lowercase-name>.yml.example`.
- Local runtime files are `profiles/<name>.yml` and are **gitignored** (machine
  `host_model_path` / tuning). Copy from the example on each host.
- `model_path` is the path inside the container's `/models` mount.
- `host_model_path` documents the corresponding host file (not used by launch.sh).
- Use one profile per quantization when settings or memory needs differ.
- Prefer conservative single-user context defaults; document how to scale up.
- Never commit `config.yml`, local `profiles/*.yml`, model weights, logs, or
  generated outputs.
- Follow the repository rule: commits and pushes only from a feature branch.
