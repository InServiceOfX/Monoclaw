# Mission Control Dashboard — Build Brief

## Goal
A TypeScript/React (Vite) dashboard for monitoring and switching LLMs with **verified, confirmed model switching**.

## Core Features

### 1. Model Switching (Critical)
- Dropdown/selector listing configured model endpoints
- On switch: send a test "echo" request to the new model, confirm it responds
- Display a clear "CONFIRMED ✓" badge only after the test succeeds
- If test fails: show error, revert to previous model indicator
- Never claim a model is active until round-trip verified

### 2. Model Info Panel
- Current active model name + provider
- Context window size
- Max tokens
- API endpoint / base URL
- Latency (ms) of last test ping

### 3. Token Usage Metrics
- Input tokens (session)
- Output tokens (session)
- Total tokens (session)
- Context window utilization bar (used / max, percentage)
- Estimated cost (if pricing config available)
- Reset session button

### 4. Status / Health
- Per-endpoint health check (green/yellow/red)
- Last checked timestamp
- Auto-refresh toggle (every 30s)

## Model Endpoints to Support
The app reads from a config file `src/config/models.ts`:

```ts
export const MODELS = [
  {
    id: "claude-sonnet-4-6",
    name: "Claude Sonnet 4.6",
    provider: "Anthropic",
    baseUrl: "https://api.anthropic.com/v1",
    apiKeyEnv: "VITE_ANTHROPIC_API_KEY",
    contextWindow: 200000,
    maxTokens: 8192,
    costPer1kInput: 0.003,
    costPer1kOutput: 0.015,
  },
  {
    id: "qwen3-1.7b",
    name: "Qwen3-1.7B (local)",
    provider: "SGLang",
    baseUrl: "http://localhost:30000/v1",
    apiKeyEnv: "",
    contextWindow: 163840,
    maxTokens: 8192,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
  {
    id: "moonshotai/kimi-k2.5",
    name: "Kimi K2.5 (NIM)",
    provider: "NVIDIA NIM",
    baseUrl: "https://integrate.api.nvidia.com/v1",
    apiKeyEnv: "VITE_NVIDIA_NIM_API_KEY",
    contextWindow: 262144,
    maxTokens: 16384,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
  {
    id: "grok-4-1-fast",
    name: "Grok 4.1 Fast",
    provider: "xAI",
    baseUrl: "https://api.x.ai/v1",
    apiKeyEnv: "VITE_XAI_API_KEY",
    contextWindow: 2000000,
    maxTokens: 65536,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
  {
    id: "openai/gpt-oss-20b",
    name: "GPT-OSS 20B",
    provider: "Groq",
    baseUrl: "https://api.groq.com/openai/v1",
    apiKeyEnv: "VITE_GROQ_API_KEY",
    contextWindow: 200000,
    maxTokens: 8192,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
]
```

## Model Switching Verification Flow
For OpenAI-compatible endpoints (SGLang, NIM, xAI, Groq):
1. POST /v1/chat/completions with `{"model": "<id>", "messages": [{"role":"user","content":"Reply with exactly: HANDSHAKE_OK"}], "max_tokens": 20}`
2. Check response contains "HANDSHAKE_OK" in content
3. Record latency, mark confirmed

For Anthropic:
1. POST /v1/messages with appropriate format
2. Same handshake check

## Stack
- Vite + React 18 + TypeScript
- Tailwind CSS for styling (dark theme, mission-control aesthetic)
- Recharts for the context window utilization bar/chart
- Zustand for state (active model, token counts, health status)
- No backend needed — pure frontend, talks directly to model APIs

## UX Notes
- Dark theme, monospace numbers, subtle green "confirmed" glow
- Context window bar: color shifts red as it fills up (green < 50%, yellow 50-80%, red > 80%)
- Provider logos/badges next to model names
- Token counter animates on update

## Project Setup
- `npm create vite@latest . -- --template react-ts` (already created dir)
- Add tailwind, recharts, zustand
- `.env.example` for API keys
- `README.md` documenting how to run and configure

## File Structure
```
JavaScript/mission-control/
├── src/
│   ├── config/models.ts        # Model configs (as above)
│   ├── components/
│   │   ├── ModelSelector.tsx   # Dropdown + switch + confirm flow
│   │   ├── ModelStatus.tsx     # Active model info panel
│   │   ├── TokenMetrics.tsx    # Token usage + cost
│   │   ├── ContextBar.tsx      # Context window utilization bar
│   │   └── HealthGrid.tsx      # Per-endpoint health indicators
│   ├── store/
│   │   └── useMissionStore.ts  # Zustand store
│   ├── api/
│   │   └── modelClient.ts      # API calls + handshake verification
│   ├── App.tsx
│   └── main.tsx
├── .env.example
├── package.json
└── README.md
```

## Done Criteria
- `npm run dev` starts the dashboard
- Model switching works and shows CONFIRMED only after real API round-trip
- Token metrics update correctly
- Context bar renders with color shifts
- Health grid shows live status
- All TypeScript, no `any` unless truly necessary

When completely finished, run this command to notify:
openclaw system event --text "Done: Mission Control dashboard built at JavaScript/mission-control — npm run dev to start" --mode now
