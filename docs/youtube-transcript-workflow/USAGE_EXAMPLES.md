# Usage Examples

## Basic Archival

### Single Video
```bash
python3 scripts/youtube-transcript/archive_transcript.py "https://youtu.be/X_JsIHUfUjc"
```

### With Language Preference
```bash
python3 scripts/youtube-transcript/archive_transcript.py "URL" --language en,tr
```

### Force Update (re-fetch metadata)
```bash
python3 scripts/youtube-transcript/archive_transcript.py "URL" --force
```

### Dry Run (preview only)
```bash
python3 scripts/youtube-transcript/archive_transcript.py "URL" --dry-run
```

## Searching

### Keyword Search (title, channel, tags, transcript)
```bash
python3 scripts/youtube-transcript/search_index.py "AI agent loops"
```

### Channel Filter
```bash
python3 scripts/youtube-transcript/search_index.py --channel "Y Combinator"
python3 scripts/youtube-transcript/search_index.py -c "Lex Fridman"
```

### Recent Videos
```bash
# Last 7 days
python3 scripts/youtube-transcript/search_index.py --recent 7

# Last 30 days
python3 scripts/youtube-transcript/search_index.py -r 30
```

### Tag Filter
```bash
python3 scripts/youtube-transcript/search_index.py --tag "self-improving"
python3 scripts/youtube-transcript/search_index.py -t "agent"
```

### Combined Filters
```bash
# YC videos about agents from last 30 days
python3 scripts/youtube-transcript/search_index.py "agent" -c "Y Combinator" -r 30

# All self-improving tagged videos
python3 scripts/youtube-transcript/search_index.py -t "self-improving" --list
```

### List All Videos
```bash
python3 scripts/youtube-transcript/search_index.py --list
python3 scripts/youtube-transcript/search_index.py -l
```

### Limit Results
```bash
python3 scripts/youtube-transcript/search_index.py "AI" --limit 50
python3 scripts/youtube-transcript/search_index.py "AI" -n 10
```

### Show Transcript Preview
```bash
python3 scripts/youtube-transcript/search_index.py "agent" --show-transcript
```

### Show File Paths
```bash
python3 scripts/youtube-transcript/search_index.py "AI" --show-path
```

### JSON Output (for scripting)
```bash
python3 scripts/youtube-transcript/search_index.py "AI" --json | jq '.[] | {title, channel, tags}'
```

## Advanced Workflows

### Batch Archive Multiple Videos
```bash
# From a file of URLs (one per line)
while IFS= read -r url; do
    python3 scripts/youtube-transcript/archive_transcript.py "$url"
done < video_urls.txt
```

### Find Videos by Channel and Export
```bash
python3 scripts/youtube-transcript/search_index.py -c "Y Combinator" --json | \
  jq -r '.[] | "\(.title)|\(.url)|\(.duration)"' > yc_videos.tsv
```

### Get Transcript for Specific Video
```bash
# Search to find the file
python3 scripts/youtube-transcript/search_index.py "self-improving" --json | \
  jq -r '.[0].filepath' | \
  xargs -I {} cat "/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/{}" | \
  jq '.timestamped_text'
```

### Search Transcript Content (full text)
```bash
# The index only searches title/channel/tags
# For full transcript search, grep the JSON files:
grep -l "recursive self-improving" /Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/*.json
```

### Archive with Custom Directory
```bash
python3 scripts/youtube-transcript/archive_transcript.py "URL" \
  --transcript-dir /custom/path \
  --index-file /custom/path/index.json
```

## Integration Examples

### In a Python Script
```python
import subprocess
import json

# Archive
result = subprocess.run([
    "python3", "scripts/youtube-transcript/archive_transcript.py",
    "https://youtu.be/VIDEO_ID"
], capture_output=True, text=True)

# Search
result = subprocess.run([
    "python3", "scripts/youtube-transcript/search_index.py",
    "AI agent", "--json"
], capture_output=True, text=True)
videos = json.loads(result.stdout)
```

### In Hermes Chat
```
> Archive this YouTube video: https://youtu.be/X_JsIHUfUjc
> Search my transcripts for "AI agent loops"
> Show all Y Combinator videos I've archived
> Get the transcript for the self-improving company video
```

### Cron Job for Daily Archival
```bash
# Add to crontab
0 2 * * * /usr/bin/python3 /path/to/scripts/youtube-transcript/archive_transcript.py "https://youtu.be/NEW_VIDEO_ID" >> /var/log/yt-archive.log 2>&1
```

## Troubleshooting Examples

### Video Not Found in Search
```bash
# Check if archived
python3 scripts/youtube-transcript/search_index.py --list | grep -i "partial title"

# Check index directly
cat /Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/index.json | jq '.videos[] | select(.title | contains("partial"))'
```

### Rebuild Index from Scratch
```bash
# If index corrupted, rebuild from transcript files
python3 -c "
import json, glob
from common import save_index, DEFAULT_INDEX_FILE, DEFAULT_TRANSCRIPT_DIR

index = {'videos': [], 'last_updated': None, 'total_videos': 0}
for f in glob.glob(str(DEFAULT_TRANSCRIPT_DIR / '*.json')):
    with open(f) as fp:
        data = json.load(fp)
    index['videos'].append({
        'video_id': data['video_id'],
        'title': data['title'],
        'channel': data['channel'],
        'url': data['url'],
        'duration': data['duration'],
        'segment_count': data['segment_count'],
        'language': data['language'],
        'filepath': f.name,
        'archived_at': data['archived_at'],
        'tags': []  # Re-extract if needed
    })
save_index(index)
"
```

### Export All Transcripts to Single File
```bash
python3 -c "
import json, glob
from pathlib import Path

dir = Path('/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts')
all_text = []
for f in dir.glob('*.json'):
    if f.name == 'index.json': continue
    with open(f) as fp:
        data = json.load(fp)
    all_text.append(f'=== {data[\"title\"]} ({data[\"channel\"]}) ===\n{data[\"timestamped_text\"]}\n')
Path('all_transcripts.txt').write_text('\n\n'.join(all_text))
"
```