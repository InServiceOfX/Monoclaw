# Mission Control — Setup

Mission Control reads its model list and settings from a **per-instance config file** that is not committed to git. This means each OpenClaw installation has its own config pointing at its own models and memory.

## Quick start

```bash
cd JavaScript/mission-control

# 1. Auto-generate config from your OpenClaw installation
node scripts/sync-openclaw-config.js

# 2. Build memory index from your local workspace
npm run memory:build

# 3. Copy .env.example → .env and fill in your API keys
cp .env.example .env

# 4. Start
npm run dev
```

## What gets generated (gitignored, local only)

| File | Description |
|------|-------------|
| `src/config/mission-control.json` | Your model list, workspace path, TRT-LLM config |
| `public/memory-index.json` | Index of your local memory files |

## Manual config

If you prefer to configure manually, copy the example:

```bash
cp src/config/mission-control.example.json src/config/mission-control.json
# Edit src/config/mission-control.json with your models + paths
```

## Adding a model

Edit `src/config/mission-control.json` and add to the `models` array:

```json
{
  "id": "provider/model-id",
  "displayName": "Human-readable name",
  "provider": "Provider Name",
  "baseUrl": "https://api.example.com/v1",
  "apiKeyEnv": "VITE_EXAMPLE_API_KEY",
  "contextWindow": 128000,
  "maxTokens": 8192,
  "costPer1kInput": 0.001,
  "costPer1kOutput": 0.002
}
```

## Re-syncing after openclaw.json changes

```bash
node scripts/sync-openclaw-config.js
```
