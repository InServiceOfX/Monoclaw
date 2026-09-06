# Rust `youtube-transcript` CLI — Design Spec (ABANDONED)

> **Status: abandoned 2026-09-05. No implementation is retained.**
>
> A Rust implementation existed at `Rust/youtube-transcript/` and was deleted.
> It compiled but **never worked on any input** — every fetch returned
> "No transcript available for this video".
>
> The working YouTube transcript tooling is the Python workflow documented in
> this directory (`archive_transcript.py`, `search_index.py`), on branch
> `feat/youtube-transcript-workflow`. Use that.
>
> This file is kept for the design intent below, which is still sound. The
> spec is reproduced verbatim — including its acceptance-criteria checkmarks,
> which were never true.

## Why it failed

- **Dead fetch layer.** It called `youtube.com/api/timedtext`, which returns
  **HTTP 200 with a zero-byte body** without signed parameters (`pot` /
  signature). YouTube has required these since roughly 2021. No code path
  could succeed.
- **Requested JSON, parsed XML.** It asked for `fmt=json` but parsed the
  response with a regex over `<p t="...">` elements.
- **Half the fetch function was dead code** — `cargo build` emitted 6 warnings:
  unused `url`, `response`, `fallback_urls`, and three never-constructed
  structs. One dead URL contained corrupted text
  (`https://youtubetranscript.com/?server=im大殿&...`); a fallback pointed at
  `invidious.snopyta.org`, defunct for years.
- **Fabricated data.** Segment end times were invented as `start + 5.0s`, then
  printed as real ranges in search output.
- **Summarization was not summarization** — the first five sentences joined by
  a period, printed under `=== Video Summary ===`.
- **Bare video IDs were rejected**, though both the CLI help and the spec below
  claim support.
- No tests.

## If you rebuild it

The fetch layer is the whole problem; everything else is straightforward.
Pick one:

- Shell out to `yt-dlp --write-auto-sub --skip-download` and parse the VTT.
  Least code, and `yt-dlp` tracks YouTube's changes for you.
- Use the InnerTube API (`youtubei/v1/player`) with a proper client context to
  obtain caption base URLs, then fetch those.

Do not reach for `api/timedtext` unsigned again. Verify against a real video
before writing any acceptance criteria — that is the check this attempt
skipped.

---

# Original spec (verbatim, as written)


## Project Overview

- **Project name**: youtube-transcript
- **Type**: Rust CLI application
- **Core functionality**: Fetch YouTube video transcripts, enable searching within transcripts, and provide summarization
- **Target users**: Researchers, content creators, and anyone who needs to extract text from YouTube videos

## Functionality Specification

### Core Features

1. **Fetch Transcript**
   - Input: YouTube video URL or video ID
   - Output: Full transcript text with timestamps
   - Support for manual and auto-generated captions
   - Handle videos without available transcripts gracefully

2. **Search Transcript**
   - Input: YouTube URL + search query
   - Output: List of matching segments with timestamps
   - Case-insensitive search
   - Show context around matches

3. **Summarize Transcript**
   - Input: YouTube URL
   - Output: AI-generated summary of the transcript
   - Use local LLM or API for summarization
   - Configurable summary length

### CLI Interface

```bash
youtube-transcript <COMMAND> [OPTIONS] <VIDEO_URL>

Commands:
  transcript  Fetch and display the full transcript
  search      Search for specific text in the transcript
  summarize   Generate a summary of the video content
  help        Print this message or the help of the given subcommand(s)

Options:
  -l, --lang <LANG>    Specify transcript language (default: en)
  -o, --output <FILE>  Output to file instead of stdout
  -v, --verbose        Enable verbose logging
  -h, --help           Print help
  -V, --version        Print version
```

### Technical Approach

- Use HTTP requests to YouTube's transcript API endpoints
- Parse JSON responses to extract transcript segments
- For summarization, integrate with local MLX server or external API
- Store transcripts locally for quick repeated access

## Acceptance Criteria

1. ✅ Can fetch transcript from any YouTube video with available captions
2. ✅ Search returns relevant segments with timestamps
3. ✅ Summarize produces coherent summary
4. ✅ CLI is intuitive and well-documented
5. ✅ Handles errors gracefully with helpful messages
6. ✅ Builds cleanly on macOS with cargo build