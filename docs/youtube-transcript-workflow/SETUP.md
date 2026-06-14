# Detailed Setup Instructions

## Prerequisites

- Python 3.8+
- `pip` package manager
- Internet access for YouTube API

## Step 1: Install Dependencies

```bash
# Option A: User install (recommended)
pip3 install --user youtube-transcript-api yt-dlp

# Option B: Virtual environment
python3 -m venv ~/.venv/yt-archive
source ~/.venv/yt-archive/bin/activate
pip install youtube-transcript-api yt-dlp
```

## Step 2: Verify Installation

```bash
# Test youtube-transcript-api
python3 -c "from youtube_transcript_api import YouTubeTranscriptApi; print('OK')"

# Test yt-dlp
/Users/ernestyeung/Library/Python/3.9/bin/yt-dlp --version
# or if in PATH:
yt-dlp --version
```

## Step 3: Configure Archive Location

The workflow uses these defaults:
- Archive: `/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/`
- Index: `/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/index.json`

To customize, set environment variables:

```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.profile
export YT_TRANSCRIPT_DIR="/your/custom/path/youtube-transcripts"
export YT_INDEX_FILE="/your/custom/path/youtube-transcripts/index.json"
```

Then reload:
```bash
source ~/.bashrc  # or ~/.zshrc
```

## Step 4: Test the Workflow

```bash
# Archive a test video (Rick Astley - short, has transcript)
python3 scripts/youtube-transcript/archive_transcript.py "https://youtu.be/dQw4w9WgXcq"

# Search for it
python3 scripts/youtube-transcript/search_index.py "never gonna"

# List all
python3 scripts/youtube-transcript/search_index.py --list
```

## Step 5: Verify Archive Structure

```bash
ls -la /Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/
# Should show:
# index.json
# Rick_Astley_Never_Gonna_Give_You_Up.json  (or similar)
```

## Troubleshooting

### "yt-dlp: command not found"
The script tries multiple paths. If yt-dlp installed via `pip3 install --user`:
```bash
# Add to PATH
export PATH="$PATH:/Users/ernestyeung/Library/Python/3.9/bin"
# Or use full path in script (already handled)
```

### "Transcripts are disabled for this video"
Some videos have transcripts disabled by the uploader. Try:
```bash
# Specify language explicitly
python3 scripts/youtube-transcript/archive_transcript.py "URL" --language en
```

### "No transcript found"
Video may not have captions. Check on YouTube: CC button → "Show transcript"

### Permission denied on index.json
```bash
chmod 644 /Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/index.json
```

### ModuleNotFoundError: youtube_transcript_api
```bash
pip3 install --user youtube-transcript-api
# Or ensure correct Python environment
which python3
pip3 show youtube-transcript-api
```

## For Hermes Agent Setup

If another Hermes agent needs this:

1. **Copy scripts** to their skill directory or workspace
2. **Set environment variables** in their session
3. **Run archive_transcript.py** with the video URL
4. **Use search_index.py** to query

The skill `youtube-transcript-archive` at `~/.hermes/skills/media/youtube-transcript-archive/` has all scripts pre-installed.

## Directory Permissions

Ensure the archive directory is writable:
```bash
mkdir -p /Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts
chmod 755 /Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts
```

## Scheduled/Cron Archival

To auto-archive on a schedule, add a cron job:
```bash
# Edit crontab
crontab -e

# Add: archive new videos daily at 2 AM
0 2 * * * /path/to/python3 /path/to/scripts/youtube-transcript/archive_transcript.py "NEW_VIDEO_URL"
```

Or use Hermes cron:
```bash
hermes cron create "0 2 * * *" "Archive YouTube video: https://youtu.be/NEW_ID"
```