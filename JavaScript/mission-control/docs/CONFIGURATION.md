# Mission Control Configuration Guide

## Quick Start

1. **Copy the example config:**
   ```bash
   cd src/config
   cp mission-control.json.example mission-control.json
   ```

2. **Edit `mission-control.json`** with your instance-specific paths.

3. **Never commit `mission-control.json`** - it's already in `.gitignore`.

## Configuration Sections

### `openclaw.workspaceDir`
Path to your OpenClaw workspace directory. The Memory tab uses this to locate:
- `memory/` directory (daily logs)
- `MEMORY.md` (long-term memory)

### `memory`
Controls the Memory tab behavior:
- `memoryDir`: Path to daily memory logs (`memory/YYYY-MM-DD.md`)
- `memoryFile`: Path to `MEMORY.md` (long-term curated memory)
- `indexRefreshIntervalMinutes`: How often to refresh the memory index

### `models`
API-based models. Add/remove as needed for your API keys.

### `localLLM`
Local TensorRT-LLM server configuration:
- `enabled`: Set to `true` to show the Local LLM tab
- `trtllmScriptDir`: Path to your TensorRT-LLM launch scripts
- `port`: Port where the local server runs (default: 30000)
- `profiles`: Available model profiles

## Platform-Specific Notes

### macOS
- TensorRT-LLM is **not available** on macOS
- Set `localLLM.enabled: false`
- Use API-based models (Anthropic, NVIDIA NIM, xAI, Groq)

### Linux with NVIDIA GPU
- Can use TensorRT-LLM for local inference
- Set `localLLM.enabled: true`
- Update `trtllmScriptDir` to your scripts location

## Environment Variables

Create a `.env` file in the project root:

```bash
VITE_ANTHROPIC_API_KEY=your_key_here
VITE_NVIDIA_NIM_API_KEY=your_key_here
VITE_XAI_API_KEY=your_key_here
VITE_GROQ_API_KEY=your_key_here
```

See `.env.example` for the template.
