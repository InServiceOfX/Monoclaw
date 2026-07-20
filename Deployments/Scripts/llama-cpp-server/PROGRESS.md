# PROGRESS.md — llama.cpp CUDA Server

## Completed

| Item | Status | Notes |
|---|---|---|
| Profile-driven CUDA launcher | ✅ | Global Docker config plus per-model YAML profiles |
| Qwen3.5 and Gemma profiles | ✅ | Existing text and multimodal examples |
| Qwythos-9B Q4/Q5 profiles | ✅ | Live-loaded on RTX 3070 at 32K/16K context; sampling defaults wired into launcher |
| Launcher dry-run mode | ✅ | Prints the exact Docker command without changing container state |

## In Progress

| Item | Branch | Status | Notes |
|---|---|---|---|
| None | — | — | — |

## Not Started

| Item | Priority | Notes |
|---|---|---|
| MTP profile | low | Requires a downloaded MTP GGUF and a recent image supporting draft MTP |
| Vision profile | low | Requires the full mmproj file rather than the current Git LFS pointer |

## Last Worked On

**2026-07-19** — Added Qwythos-9B Q4_K_M and Q5_K_M profiles, wired model-card
sampling defaults into `launch.sh`, and added `--dry-run`. Both profiles passed
YAML/shell validation and live CUDA model loading on the local 8 GB RTX 3070.
