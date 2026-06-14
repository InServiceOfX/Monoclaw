# YouTube Transcript Archive Workflow

**Complete setup for archiving YouTube transcripts with searchable index.**

## Quick Start for Another Hermes Agent

```bash
# 1. Install dependencies
pip3 install --user youtube-transcript-api yt-dlp

# 2. Set environment variables (or use defaults)
export YT_TRANSCRIPT_DIR="/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts"
export YT_INDEX_FILE="/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/index.json"

# 3. Archive a video
python3 scripts/youtube-transcript/archive_transcript.py "https://youtu.be/VIDEO_ID"

# 4. Search the archive
python3 scripts/youtube-transcript/search_index.py "AI agent loops"
```

## File Structure

```
Monoclaw/
├── docs/youtube-transcript-workflow/
│   ├── README.md                    # This file
│   ├── SETUP.md                     # Detailed setup instructions
│   ├── NAMING_CONVENTION.md         # File naming rules
│   ├── INDEX_SCHEMA.md              # Index.json structure
│   └── USAGE_EXAMPLES.md            # Common workflows
├── scripts/youtube-transcript/
│   ├── archive_transcript.py        # Main archive script
│   ├── search_index.py              # Search script
│   └── common.py                    # Shared utilities
└── Data/Public/youtube-transcripts/ # Archive destination (auto-created)
    ├── index.json                   # Searchable index
    └── {Channel}_{Title}.json       # Individual transcripts
```

## Required Files for Another Agent

| File | Purpose |
|------|---------|
| `scripts/youtube-transcript/archive_transcript.py` | Fetches transcript + metadata, saves to archive, updates index |
| `scripts/youtube-transcript/search_index.py` | Searches index by query, channel, tag, recency |
| `scripts/youtube-transcript/common.py` | Shared: filename sanitization, index I/O, tag extraction |
| `docs/youtube-transcript-workflow/NAMING_CONVENTION.md` | File naming rules: `{Channel}_{Title_Sanitized}.json` |
| `docs/youtube-transcript-workflow/INDEX_SCHEMA.md` | Index.json structure and field definitions |

## Naming Convention

```
{Channel_Name}_{Video_Title_Sanitized}.json
```

Examples:
- `Y_Combinator_How_to_Build_a_Self-Improving_Company_with_AI.json`
- `Lex_Fridman_Sam_Altman_on_GPT5_and_Future_of_AI.json`

Rules:
- Channel and title sanitized: special chars → `_`, spaces → `_`
- Max 80 chars for channel, 100 for title
- No leading/trailing `_` or `.`

## Index Schema (index.json)

```json
{
  "videos": [
    {
      "video_id": "X_JsIHUfUjc",
      "title": "How to Build a Self-Improving Company with AI",
      "channel": "Y Combinator",
      "url": "https://youtu.be/X_JsIHUfUjc",
      "duration": "13:29",
      "segment_count": 415,
      "language": "en",
      "filepath": "Y_Combinator_How_to_Build_a_Self-Improving_Company_with_AI.json",
      "archived_at": "2026-06-14T00:05:38.934026Z",
      "tags": ["agent", "ai", "self-improving", "recursive", "loop", "yc", "workflow", "founder"]
    }
  ],
  "last_updated": "2026-06-14T00:05:38.934026Z",
  "total_videos": 1
}
```

## Auto-Tagging

Tags extracted from:
1. Channel name (lowercase, hyphenated)
2. Title keywords (split on `_`, `-`, `:`, `|`, `,`, `;`, `.`)
3. Transcript tech terms (first 5000 chars): `ai`, `llm`, `agent`, `rag`, `self-improving`, `recursive`, `loop`, `yc`, `founder`, `codex`, `copilot`, etc.

## Common Workflows

### Archive a new video
```bash
python3 scripts/youtube-transcript/archive_transcript.py "https://youtu.be/X_JsIHUfUjc"
```

### Force re-archive (update metadata)
```bash
python3 scripts/youtube-transcript/archive_transcript.py "URL" --force
```

### Dry run (preview without saving)
```bash
python3 scripts/youtube-transcript/archive_transcript.py "URL" --dry-run
```

### Search by keyword
```bash
python3 scripts/youtube-transcript/search_index.py "AI agent loops"
```

### Filter by channel
```bash
python3 scripts/youtube-transcript/search_index.py --channel "Y Combinator"
```

### Recent videos (last 7 days)
```bash
python3 scripts/youtube-transcript/search_index.py --recent 7
```

### Filter by tag
```bash
python3 scripts/youtube-transcript/search_index.py --tag "self-improving"
```

### List all
```bash
python3 scripts/youtube-transcript/search_index.py --list
```

### Show transcript preview
```bash
python3 scripts/youtube-transcript/search_index.py "agent" --show-transcript
```

### JSON output (for piping)
```bash
python3 scripts/youtube-transcript/search_index.py "AI" --json
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `YT_TRANSCRIPT_DIR` | `~/.openclaw/workspace/Data/Public/youtube-transcripts` | Archive directory |
| `YT_INDEX_FILE` | `~/.openclaw/workspace/Data/Public/youtube-transcripts/index.json` | Index file path |

## Dependencies

```bash
pip3 install --user youtube-transcript-api yt-dlp
```

- `youtube-transcript-api` — fetches transcript segments with timestamps
- `yt-dlp` — fetches video metadata (title, channel) for proper naming

## Integration with Hermes

In Hermes chat, just say:
> "Archive this YouTube video: https://youtu.be/..."
> "Search my transcripts for 'AI agent loops'"
> "Show all Y Combinator videos I've archived"

The skill `youtube-transcript-archive` in `~/.hermes/skills/media/youtube-transcript-archive/` provides the same scripts.

## Version

Created: 2026-06-14
Version: 1.0.0