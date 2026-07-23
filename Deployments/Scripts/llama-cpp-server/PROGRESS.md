# PROGRESS.md — llama.cpp CUDA Server

## Completed

| Item | Status | Notes |
|---|---|---|
| Profile-driven CUDA launcher | ✅ | Global Docker config plus per-model YAML profiles |
| Qwen3.5 and Gemma profiles | ✅ | Existing text and multimodal examples |
| Qwythos-9B Q4/Q5 profiles | ✅ | Live-loaded on RTX 3070 at 32K/16K context; sampling defaults wired into launcher |
| Qwythos-9B Q6 profile | ✅ | Template + local MS-7885 path; ~6.9 GB Q6_K weights |
| Profile .yml.example pattern | ✅ | Machine paths stay local; only examples committed |
| Launcher dry-run mode | ✅ | Prints the exact Docker command without changing container state |

## In Progress

| Item | Branch | Status | Notes |
|---|---|---|---|
| Qwythos Q5 load on MS-7885 | feat/llama-cpp-qwythos-profile-examples | active | Real Q5/Q6 GGUFs present; Q4 still LFS pointer |

## Not Started

| Item | Priority | Notes |
|---|---|---|
| MTP profile | low | Requires a downloaded MTP GGUF and a recent image supporting draft MTP |
| Vision profile | low | Requires the full mmproj file rather than the current Git LFS pointer |
| Full Q4_K_M download on MS-7885 | low | Only ~135 B LFS pointer on disk today |

## Last Worked On

**2026-07-22** — Converted Qwythos profiles to the `.yml.example` + gitignored
local `.yml` pattern (same as Qwen/Gemma). Fixed `host_model_path` for MS-7885
(`/media/propdev/9dc1a908-.../Data/Models/LLM/...`). Added Q6_K profile.
Q5 (6.1G) and Q6 (6.9G) are real GGUFs on this host; Q4 remains an LFS pointer.

**2026-07-19** — Added Qwythos-9B Q4_K_M and Q5_K_M profiles, wired model-card
sampling defaults into `launch.sh`, and added `--dry-run`. Both profiles passed
YAML/shell validation and live CUDA model loading on the local 8 GB RTX 3070.
