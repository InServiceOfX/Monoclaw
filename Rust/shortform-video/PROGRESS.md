# PROGRESS.md — Rust/shortform-video

## Completed
| Item | Status | Notes |
|------|--------|-------|
| Crate scaffold + config (TOML + env) | ✅ | `~/.config/shortform-video/config.toml`, `SHORTFORM_*` overrides |
| LLM stage (script/terms/social) | ✅ | OpenAI-compatible; think-block strip; JSON recovery; prompts ported from MoneyPrinterTurbo |
| Materials (Pexels + Pixabay) | ✅ | orientation filter, min-duration, dedup, duration budgeting, attribution JSON |
| TTS: Edge neural (native Rust) | ✅ | msedge-tts WebSocket; word boundaries in 100 ns ticks; verified live 2026-09-02 |
| TTS: macOS `say` fallback | ✅ | offline; proportional subtitle timing |
| Subtitles (SRT) | ✅ | word-cue → script-line aggregation with proportional fallback; SRT read/write round-trip tested |
| Caption PNG rendering | ✅ | ab_glyph wrap/outline/rounded-bg; needed because homebrew ffmpeg lacks libass/drawtext |
| ffmpeg composition | ✅ | cover/contain fit, segment planning (round-robin, looping), concat demuxer, overlay enable-windows, BGM amix + 3 s fade-out |
| CLI (script/terms/tts/voices/social/run) | ✅ | clap derive |
| Unit tests (27) + clippy clean | ✅ | pure logic tests, no network |
| Offline E2E verified | ✅ | lavfi materials + `say` → 1080×1920 h264/aac, captions burned in, audio −19.5 dB mean |

## In Progress
| Item | Branch | Status | Notes |
|------|--------|--------|-------|
| — | | | |

## Not Started
| Item | Priority | Notes |
|------|----------|-------|
| xfade cross-transitions between segments | med | claw-dj `render_shorts.py` has the offset-chain pattern to port |
| Whisper subtitles for custom audio | low | whisper.cpp subprocess; only needed for bring-your-own narration |
| Coverr as a third stock source | low | port from MoneyPrinterTurbo material.py if Pexels/Pixabay prove thin |
| Ken Burns still-image mode | med | zoompan exists in this ffmpeg; enables image-only b-roll like MPT's openai_image source |

## Last Worked On
**2026-09-02** — Initial port from MoneyPrinterTurbo built and verified
(offline E2E + live Edge TTS). Uncommitted; needs a feature branch + commit.
