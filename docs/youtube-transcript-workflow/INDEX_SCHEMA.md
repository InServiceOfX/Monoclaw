# Index Schema (index.json)

## Root Structure

```json
{
  "videos": [VideoEntry, ...],
  "last_updated": "ISO8601 timestamp",
  "total_videos": integer
}
```

## VideoEntry Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `video_id` | string | Yes | 11-character YouTube video ID |
| `title` | string | Yes | Video title from yt-dlp |
| `channel` | string | Yes | Channel/uploader name |
| `url` | string | Yes | Canonical youtu.be URL |
| `duration` | string | Yes | Formatted as MM:SS or HH:MM:SS |
| `segment_count` | integer | Yes | Number of transcript segments |
| `language` | string | Yes | Language code (e.g., "en", "auto") |
| `filepath` | string | Yes | Relative filename in archive dir |
| `archived_at` | string | Yes | ISO8601 timestamp of archival |
| `tags` | string[] | No | Auto-extracted search tags |

## Example Entry

```json
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
  "tags": [
    "agent", "ai", "self-improving", "recursive", "loop",
    "yc", "workflow", "founder", "product", "rag"
  ]
}
```

## Field Details

### video_id
- Always 11 characters: `[a-zA-Z0-9_-]{11}`
- Extracted from URL patterns: `v=`, `youtu.be/`, `shorts/`, `embed/`, `live/`

### duration
- Format: `M:SS` or `H:MM:SS`
- Calculated from last segment: `start + duration`

### language
- `"auto"` if no language specified
- ISO 639-1 code if specified (e.g., `"en"`, `"tr"`)

### tags
Auto-generated from:
1. **Channel**: lowercased, hyphenated (e.g., `"y-combinator"`)
2. **Title keywords**: split on `[-_:|,.;]`, filtered (len > 3, not stopwords)
3. **Transcript tech terms** (first 5000 chars):
   - `ai`, `llm`, `gpt`, `claude`, `agent`, `agents`, `rag`, `embedding`
   - `vector`, `database`, `fine-tune`, `training`, `inference`, `prompt`
   - `transformer`, `attention`, `neural`, `machine learning`, `deep learning`
   - `startup`, `yc`, `y combinator`, `founder`, `product`, `market`
   - `self-improving`, `recursive`, `loop`, `automation`, `workflow`
   - `codex`, `copilot`, `cursor`, `vscode`, `api`, `openai`, `anthropic`
   - `langchain`, `llamaindex`, `mcp`, `function calling`, `tool use`

Max 20 tags per video, sorted alphabetically.

## Index Operations

### Load Index
```python
from common import load_index
index = load_index()  # Uses DEFAULT_INDEX_FILE
```

### Save Index
```python
from common import save_index
save_index(index)  # Updates last_updated and total_videos
```

### Add/Update Video
```python
from common import add_to_index
add_to_index(
    video_id="...",
    title="...",
    channel="...",
    url="...",
    duration="...",
    segment_count=...,
    language="...",
    filepath="...",
    transcript_text="..."  # for tag extraction
)
```

### Search Index
```python
from common import search_index
results = search_index(
    query="AI agent loops",
    channel="Y Combinator",
    recent_days=7,
    tag="self-improving",
    limit=20
)
```

## Versioning

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-14 | Initial schema |