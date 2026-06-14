#!/usr/bin/env python3
"""
Search the YouTube transcript archive index.

Usage:
    python3 search_index.py "AI agent loops"
    python3 search_index.py --channel "Y Combinator"
    python3 search_index.py --recent 7
    python3 search_index.py --list
    python3 search_index.py --tag "ai"

Environment Variables:
    YT_INDEX_FILE     - Index file path (default: ~/.openclaw/workspace/Data/Public/youtube-transcripts/index.json)
    YT_TRANSCRIPT_DIR - Archive directory (default: ~/.openclaw/workspace/Data/Public/youtube-transcripts)
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for common module
sys.path.insert(0, str(Path(__file__).parent))
from common import (
    DEFAULT_INDEX_FILE,
    DEFAULT_TRANSCRIPT_DIR,
    search_index,
    load_index,
    get_video_transcript_file,
)


def format_duration(duration: str) -> str:
    """Ensure duration is formatted nicely."""
    return duration


def print_video_summary(video: dict, show_tags: bool = True, show_path: bool = False):
    """Print a formatted video summary."""
    print(f"  📹 {video['title']}")
    print(f"     Channel: {video['channel']} | Duration: {video['duration']} | Segments: {video['segment_count']}")
    print(f"     Video ID: {video['video_id']} | URL: {video['url']}")
    print(f"     Archived: {video['archived_at'][:10]}")
    if show_tags and video.get('tags'):
        print(f"     Tags: {', '.join(video['tags'][:10])}")
    if show_path:
        print(f"     File: {video['filepath']}")
    print()


def print_transcript_preview(filepath: str, lines: int = 10):
    """Print first N lines of timestamped transcript."""
    data = get_video_transcript_file(filepath)
    if data and data.get('timestamped_text'):
        newline = '\n'
        preview_lines = data['timestamped_text'].split(newline)[:lines]
        print("     Transcript preview:")
        for line in preview_lines:
            print(f"       {line}")
        total_lines = len(data['timestamped_text'].split(newline))
        if total_lines > lines:
            print(f"       ... ({total_lines} total lines)")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Search YouTube transcript archive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 search_index.py "AI agent loops"
  python3 search_index.py --channel "Y Combinator"
  python3 search_index.py --recent 7
  python3 search_index.py --tag "ai"
  python3 search_index.py --list
  python3 search_index.py "agent" --show-transcript
        """
    )
    parser.add_argument("query", nargs="?", default="", help="Search query (matches title, channel, tags)")
    parser.add_argument("--channel", "-c", default="", help="Filter by channel name")
    parser.add_argument("--recent", "-r", type=int, default=0, help="Show videos from last N days")
    parser.add_argument("--tag", "-t", default="", help="Filter by tag")
    parser.add_argument("--list", "-l", action="store_true", help="List all videos (ignores query)")
    parser.add_argument("--limit", "-n", type=int, default=20, help="Max results (default: 20)")
    parser.add_argument("--show-transcript", action="store_true", help="Show transcript preview")
    parser.add_argument("--show-path", action="store_true", help="Show file paths")
    parser.add_argument("--index-file", default=str(DEFAULT_INDEX_FILE), help=f"Index file (default: {DEFAULT_INDEX_FILE})")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    index_file = Path(args.index_file)

    if not index_file.exists():
        print(f"Index not found: {index_file}")
        print("Run archive_transcript.py first to create the index.")
        sys.exit(1)

    # Determine if we're doing a broad list
    is_list_all = args.list or (not args.query and not args.channel and not args.recent and not args.tag)

    results = search_index(
        query=args.query,
        channel=args.channel,
        recent_days=args.recent,
        tag=args.tag,
        index_file=index_file,
        limit=args.limit
    )

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    if not results:
        print("No videos found matching criteria.")
        return

    index = load_index(index_file)
    print(f"Found {len(results)} of {index['total_videos']} videos\n")

    for i, video in enumerate(results, 1):
        print(f"{i}. ", end="")
        print_video_summary(video, show_path=args.show_path)

        if args.show_transcript:
            print_transcript_preview(video['filepath'])

    # Summary
    channels = set(v['channel'] for v in results)
    if len(channels) > 1:
        print(f"Channels: {', '.join(sorted(channels))}")

    all_tags = set()
    for v in results:
        all_tags.update(v.get('tags', []))
    if all_tags:
        print(f"Common tags: {', '.join(sorted(all_tags)[:15])}")


if __name__ == "__main__":
    main()