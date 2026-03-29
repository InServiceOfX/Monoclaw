# Memory Tab Setup Guide

## Why is the Memory Tab Empty?

The Memory tab requires:
1. A valid `mission-control.json` config with correct paths
2. Memory files in the expected locations
3. A generated `memory-index.json` file

## Step 1: Configure Memory Paths

In your `src/config/mission-control.json`:

```json
{
  "memory": {
    "memoryDir": "/home/yourname/.openclaw/workspace/memory",
    "memoryFile": "/home/yourname/.openclaw/workspace/MEMORY.md",
    "indexRefreshIntervalMinutes": 5
  }
}
```

## Step 2: Ensure Memory Files Exist

Your OpenClaw workspace should have:

```
~/.openclaw/workspace/
├── MEMORY.md              # Long-term curated memory
├── memory/
│   ├── 2026-03-27.md     # Daily memory logs
│   ├── 2026-03-26.md
│   └── ...
└── ...
```

## Step 3: Generate memory-index.json

The Memory tab reads from `public/memory-index.json`. This file must be generated.

### Option A: Use the provided script (if available)

```bash
npm run build:memory-index
```

### Option B: Manual generation

Create `public/memory-index.json`:

```json
{
  "generatedAt": "2026-03-27T22:00:00Z",
  "count": 2,
  "documents": [
    {
      "id": "memory-2026-03-27",
      "title": "2026-03-27",
      "path": "/home/yourname/.openclaw/workspace/memory/2026-03-27.md",
      "relativePath": "memory/2026-03-27.md",
      "updatedAt": "2026-03-27T20:00:00Z",
      "sizeBytes": 1500,
      "content": "...file contents here..."
    },
    {
      "id": "memory-md",
      "title": "MEMORY.md",
      "path": "/home/yourname/.openclaw/workspace/MEMORY.md",
      "relativePath": "MEMORY.md",
      "updatedAt": "2026-03-27T18:00:00Z",
      "sizeBytes": 5000,
      "content": "...file contents here..."
    }
  ]
}
```

## Step 4: Restart Mission Control

After creating/updating `memory-index.json`, restart the dev server:

```bash
npm run dev
```

## Troubleshooting

### "No matching memories" shown
- Check that `memory-index.json` exists in `public/`
- Verify the JSON is valid
- Check browser console for fetch errors

### Memory files not loading
- Verify paths in `mission-control.json` are absolute
- Ensure the paths exist on your filesystem
- Check file permissions

### Changes not appearing
- Regenerate `memory-index.json` after editing memory files
- The index is static - it doesn't auto-update
