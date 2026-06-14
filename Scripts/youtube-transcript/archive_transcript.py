#!/usr/bin/env python3
"""
Archive a YouTube transcript with metadata and update searchable index.

Usage:
    python3 archive_transcript.py <url_or_video_id> [--language en,tr] [--dry-run]
    python3 archive_transcript.py "https://youtu.be/X_JsIHUfUjc"

Environment Variables:
    YT_TRANSCRIPT_DIR - Archive directory (default: ~/.openclaw/workspace/Data/Public/youtube-transcripts)
    YT_INDEX_FILE     - Index file path (default: ~/.openclaw/workspace/Data/Public/youtube-transcripts/index.json)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for common module
sys.path.insert(0, str(Path(__file__).parent))
from common import (
    DEFAULT_TRANSCRIPT_DIR,
    DEFAULT_INDEX_FILE,
    extract_video_id,
    generate_filename,
    find_video_in_index,
    add_to_index,
    format_timestamp,
    load_index,
    save_index,
)


def fetch_transcript(video_id: str, languages: list = None):
    """Fetch transcript segments from YouTube."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("Error: youtube-transcript-api not installed. Run: pip install youtube-transcript-api", file=sys.stderr)
        sys.exit(1)

    api = YouTubeTranscriptApi()
    if languages:
        result = api.fetch(video_id, languages=languages)
    else:
        result = api.fetch(video_id)

    return [
        {"text": seg.text, "start": seg.start, "duration": seg.duration}
        for seg in result
    ]


def fetch_video_metadata(video_id: str) -> dict:
    """Fetch video metadata (title, channel) using yt-dlp."""
    # Try multiple possible yt-dlp locations
    yt_dlp_paths = [
        "yt-dlp",
        "/Users/ernestyeung/Library/Python/3.9/bin/yt-dlp",
        os.path.expanduser("~/.local/bin/yt-dlp"),
        os.path.expanduser("~/Library/Python/3.9/bin/yt-dlp"),
    ]

    for yt_dlp in yt_dlp_paths:
        try:
            import subprocess
            result = subprocess.run(
                [yt_dlp, "--dump-json", "--no-download", f"https://youtu.be/{video_id}"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "title": data.get("title", ""),
                    "channel": data.get("uploader", data.get("channel", "")),
                }
        except Exception:
            continue
    return {}


def main():
    parser = argparse.ArgumentParser(
        description="Fetch YouTube transcript and archive with searchable index",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 archive_transcript.py "https://youtu.be/X_JsIHUfUjc"
  python3 archive_transcript.py "VIDEO_ID" --language en,tr
  python3 archive_transcript.py "URL" --dry-run
        """
    )
    parser.add_argument("url", help="YouTube URL or video ID")
    parser.add_argument("--language", "-l", default=None,
                        help="Comma-separated language codes (e.g. en,tr). Default: auto")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be saved without writing")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Overwrite existing archive")
    parser.add_argument("--transcript-dir", default=str(DEFAULT_TRANSCRIPT_DIR),
                        help=f"Output directory (default: {DEFAULT_TRANSCRIPT_DIR})")
    parser.add_argument("--index-file", default=str(DEFAULT_INDEX_FILE),
                        help=f"Index file (default: {DEFAULT_INDEX_FILE})")

    args = parser.parse_args()

    transcript_dir = Path(args.transcript_dir)
    index_file = Path(args.index_file)
    transcript_dir.mkdir(parents=True, exist_ok=True)

    video_id = extract_video_id(args.url)
    languages = [l.strip() for l in args.language.split(",")] if args.language else None

    # Check if already archived
    existing = find_video_in_index(video_id, index_file)
    if existing and not args.force:
        print(f"⚠ Already archived: {existing['filepath']}")
        print(f"   Title: {existing['title']}")
        print(f"   Channel: {existing['channel']}")
        print(f"   Use --force to re-archive")
        sys.exit(0)

    print(f"Fetching transcript for video: {video_id}...")

    try:
        segments = fetch_transcript(video_id, languages)
    except Exception as e:
        error_msg = str(e)
        if "disabled" in error_msg.lower():
            print("Error: Transcripts are disabled for this video.", file=sys.stderr)
        elif "no transcript" in error_msg.lower():
            print(f"Error: No transcript found. Try specifying a language with --language.", file=sys.stderr)
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)

    if not segments:
        print("Error: Empty transcript", file=sys.stderr)
        sys.exit(1)

    # Fetch metadata (title, channel)
    print("Fetching video metadata...")
    metadata = fetch_video_metadata(video_id)

    # Build transcript data
    full_text = " ".join(seg["text"] for seg in segments)
    timestamped_text = "\n".join(
        f"{format_timestamp(seg['start'])} {seg['text']}" for seg in segments
    )

    duration = format_timestamp(segments[-1]["start"] + segments[-1]["duration"]) if segments else "0:00"
    segment_count = len(segments)
    detected_language = languages[0] if languages else "auto"

    # Use metadata or fallbacks
    title = metadata.get("title") or (existing["title"] if existing else f"Video_{video_id}")
    channel = metadata.get("channel") or (existing["channel"] if existing else "Unknown_Channel")
    url = f"https://youtu.be/{video_id}"

    # Generate filename
    filename = generate_filename(channel, title)
    filepath = transcript_dir / filename

    # Prepare archive data
    archive_data = {
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "url": url,
        "duration": duration,
        "segment_count": segment_count,
        "language": detected_language,
        "full_text": full_text,
        "timestamped_text": timestamped_text,
        "archived_at": __import__('datetime').datetime.utcnow().isoformat() + "Z"
    }

    if args.dry_run:
        print(f"\n--- DRY RUN ---")
        print(f"Would save to: {filepath}")
        print(f"Title: {title}")
        print(f"Channel: {channel}")
        print(f"Duration: {duration}")
        print(f"Segments: {segment_count}")
        print(f"Language: {detected_language}")
        print(f"Filename: {filename}")
        return

    # Save transcript
    with open(filepath, 'w') as f:
        json.dump(archive_data, f, indent=2, ensure_ascii=False)

    # Update index
    add_to_index(
        video_id=video_id,
        title=title,
        channel=channel,
        url=url,
        duration=duration,
        segment_count=segment_count,
        language=detected_language,
        filepath=filename,
        transcript_text=full_text,
        index_file=index_file
    )

    print(f"✓ Archived: {filename}")
    print(f"  Title: {title}")
    print(f"  Channel: {channel}")
    print(f"  Duration: {duration} | Segments: {segment_count}")
    print(f"  Index updated: {index_file}")


if __name__ == "__main__":
    main()