#!/usr/bin/env python3
"""Shared utilities for YouTube transcript archive."""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Configuration - can be overridden by environment variables
DEFAULT_TRANSCRIPT_DIR = Path(
    os.getenv(
        "YT_TRANSCRIPT_DIR",
        "/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts"
    )
)
DEFAULT_INDEX_FILE = Path(
    os.getenv(
        "YT_INDEX_FILE",
        "/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/index.json"
    )
)

# Ensure directory exists
DEFAULT_TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)


def extract_video_id(url_or_id: str) -> str:
    """Extract the 11-character video ID from various YouTube URL formats."""
    url_or_id = url_or_id.strip()
    patterns = [
        r'(?:v=|youtu\.be/|shorts/|embed/|live/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return url_or_id


def sanitize_filename(text: str, max_length: int = 80) -> str:
    """Sanitize text for use in filename."""
    # Replace special characters
    text = re.sub(r'[<>:\"/\\|?*]', '_', text)
    # Replace whitespace runs with single underscore
    text = re.sub(r'\s+', '_', text)
    # Remove leading/trailing underscores and dots
    text = text.strip('_.')
    # Limit length
    if len(text) > max_length:
        text = text[:max_length].rstrip('_-')
    return text


def generate_filename(channel: str, title: str) -> str:
    """Generate filename from channel and title."""
    safe_channel = sanitize_filename(channel, 40)
    safe_title = sanitize_filename(title, 100)
    return f"{safe_channel}_{safe_title}.json"


def load_index(index_file: Path = DEFAULT_INDEX_FILE) -> dict:
    """Load the search index."""
    if index_file.exists():
        try:
            with open(index_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"videos": [], "last_updated": None, "total_videos": 0}


def save_index(index: dict, index_file: Path = DEFAULT_INDEX_FILE) -> None:
    """Save the search index."""
    index["last_updated"] = datetime.utcnow().isoformat() + "Z"
    index["total_videos"] = len(index["videos"])
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def find_video_in_index(video_id: str, index_file: Path = DEFAULT_INDEX_FILE) -> Optional[dict]:
    """Check if video already exists in index."""
    index = load_index(index_file)
    for video in index["videos"]:
        if video["video_id"] == video_id:
            return video
    return None


def add_to_index(
    video_id: str,
    title: str,
    channel: str,
    url: str,
    duration: str,
    segment_count: int,
    language: str,
    filepath: str,
    transcript_text: str = "",
    index_file: Path = DEFAULT_INDEX_FILE
) -> dict:
    """Add or update a video in the index."""
    index = load_index(index_file)

    # Extract basic tags from title, channel, and transcript
    tags = extract_tags(channel, title, transcript_text)

    video_entry = {
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "url": url,
        "duration": duration,
        "segment_count": segment_count,
        "language": language,
        "filepath": filepath,
        "archived_at": datetime.utcnow().isoformat() + "Z",
        "tags": tags
    }

    # Update existing or add new
    for i, v in enumerate(index["videos"]):
        if v["video_id"] == video_id:
            index["videos"][i] = video_entry
            save_index(index, index_file)
            return video_entry

    index["videos"].append(video_entry)
    save_index(index, index_file)
    return video_entry


def extract_tags(channel: str, title: str, transcript_text: str = "") -> list[str]:
    """Extract tags from metadata and transcript."""
    tags = set()

    # Channel as tag
    tags.add(sanitize_filename(channel).lower().replace('_', '-'))

    # Title keywords (split on common separators)
    title_words = re.split(r'[_\-:|,.;]+', title.lower())
    for word in title_words:
        word = word.strip()
        if len(word) > 3 and word not in {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'how', 'what', 'why', 'when', 'where', 'who'}:
            tags.add(word)

    # Common tech/AI terms from transcript (first 5000 chars)
    if transcript_text:
        tech_terms = [
            'ai', 'llm', 'gpt', 'claude', 'agent', 'agents', 'rag', 'embedding',
            'vector', 'database', 'fine-tune', 'training', 'inference', 'prompt',
            'transformer', 'attention', 'neural', 'machine learning', 'deep learning',
            'startup', 'yc', 'y combinator', 'founder', 'product', 'market',
            'self-improving', 'recursive', 'loop', 'automation', 'workflow',
            'codex', 'copilot', 'cursor', 'vscode', 'api', 'openai', 'anthropic',
            'langchain', 'llamaindex', 'mcp', 'function calling', 'tool use'
        ]
        transcript_lower = transcript_text[:5000].lower()
        for term in tech_terms:
            if term in transcript_lower:
                tags.add(term.replace(' ', '-'))

    return sorted(tags)[:20]  # Limit tags


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def search_index(
    query: str = "",
    channel: str = "",
    recent_days: int = 0,
    tag: str = "",
    index_file: Path = DEFAULT_INDEX_FILE,
    limit: int = 20
) -> list[dict]:
    """Search the index with various filters."""
    index = load_index(index_file)
    results = index["videos"]

    query_lower = query.lower()
    channel_lower = channel.lower()
    tag_lower = tag.lower()

    cutoff_time = None
    if recent_days > 0:
        cutoff_time = datetime.utcnow() - timedelta(days=recent_days)

    filtered = []
    for video in results:
        # Text search in title, channel, tags
        if query_lower:
            searchable = f"{video['title']} {video['channel']} {' '.join(video.get('tags', []))}".lower()
            if query_lower not in searchable:
                continue

        # Channel filter
        if channel_lower and channel_lower not in video['channel'].lower():
            continue

        # Tag filter
        if tag_lower:
            video_tags = [t.lower() for t in video.get('tags', [])]
            if tag_lower not in video_tags:
                continue

        # Recent filter
        if cutoff_time:
            try:
                archived_at = datetime.fromisoformat(video['archived_at'].replace('Z', '+00:00'))
                if archived_at < cutoff_time:
                    continue
            except ValueError:
                pass

        filtered.append(video)

    # Sort by most recent first
    filtered.sort(key=lambda v: v['archived_at'], reverse=True)
    return filtered[:limit]


def get_video_transcript_file(filepath: str, transcript_dir: Path = DEFAULT_TRANSCRIPT_DIR) -> Optional[dict]:
    """Load a saved transcript JSON file."""
    full_path = transcript_dir / filepath
    if full_path.exists():
        try:
            with open(full_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return None