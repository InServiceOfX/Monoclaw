# Mission Control — LLM Dashboard

A TypeScript/React dashboard for monitoring and switching LLMs with **verified, confirmed model switching**.

## Features

- **Verified model switching** — sends a HANDSHAKE_OK round-trip before marking a model as active
- **Model info panel** — context window, max tokens, endpoint, latency
- **Session token metrics** — input/output token counts, estimated cost, reset button
- **Context window utilization bar** — color-coded (green → yellow → red as it fills)
- **Endpoint health grid** — per-endpoint health checks with auto-refresh every 30s

## Quick Start

```bash
# 1. Copy environment file and add your API keys
cp .env.example .env
# Edit .env with your keys

# 2. Install dependencies (requires Node 18+)
npm install

# 3. Start dev server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## Configuration

Models are defined in `src/config/models.ts`. Each model has:

| Field | Description |
|---|---|
| `id` | Model ID sent in API requests |
| `name` | Display name |
| `provider` | Provider name (`Anthropic`, `SGLang`, `NVIDIA NIM`, `xAI`, `Groq`) |
| `baseUrl` | API base URL |
| `apiKeyEnv` | `VITE_*` env var holding the API key (empty for local models) |
| `contextWindow` | Maximum context tokens |
| `maxTokens` | Maximum output tokens |
| `costPer1kInput` | Cost per 1k input tokens (USD, 0 for free/local) |
| `costPer1kOutput` | Cost per 1k output tokens (USD, 0 for free/local) |

## Model Switching Verification

When you click **Switch**, the dashboard:

1. Sends a test prompt: `Reply with exactly: HANDSHAKE_OK`
2. Waits for the API response (15s timeout)
3. Checks the response contains `HANDSHAKE_OK`
4. Shows **CONFIRMED** (with latency) only if the round-trip succeeds
5. If it fails, reverts to the previous model and shows the error

## SGLang Local Server

For the Qwen3-1.7B local model, start an SGLang server:

```bash
pip install sglang[all]
python -m sglang.launch_server \
  --model Qwen/Qwen3-1.7B \
  --port 30000 \
  --host 0.0.0.0
```

No API key required.

## Stack

- [Vite](https://vite.dev) + React 19 + TypeScript
- [Tailwind CSS v3](https://tailwindcss.com) — dark mission-control theme
- [Zustand](https://zustand-demo.pmnd.rs) — global state
- No backend required — direct browser-to-API calls

## Build

```bash
npm run build     # TypeScript check + Vite production build
npm run preview   # Preview production build locally
```
