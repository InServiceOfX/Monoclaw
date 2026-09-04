---
name: short-form-video-assembly
description: >
  Assemble a complete faceless short-form video (TikTok/Reels/Shorts) from a
  subject or script: LLM narration script, TTS voiceover, stock b-roll,
  script-aligned burned-in captions, 9:16/16:9/1:1 render. Use when the user
  asks to "make a short", "generate a faceless video", "turn this script/topic
  into a video", "add captions + voiceover to b-roll", or runs
  /short-form-video-assembly. For virality structure use
  short-form-viral-content; for screen-recorded explainers use the OBS deck
  pipeline. This skill is the automated assembly path.
version: 0.1.0
author: Ernest + TARS
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [video, tiktok, shorts, reels, tts, ffmpeg, automation, content]
    related_skills: [short-form-viral-content]
---

# Short-Form Video Assembly

Drive the `shortform-video` Rust CLI (Monoclaw) to turn a subject or a
finished script into a rendered, captioned vertical video. The pipeline is:
script → search terms → TTS narration → subtitles → stock b-roll → ffmpeg
composition. Ported from MoneyPrinterTurbo; see
`Monoclaw/docs/shortform/MONEYPRINTERTURBO_ASSESSMENT.md` for provenance.

## The three short-form modes (pick the right one)

1. **Structure** (`short-form-viral-content` skill) — hook/retention/
   engagement design. Load it FIRST when the goal is reach; write the script
   with its rules, then feed that script to this pipeline via `--script-file`.
2. **Shoot** (Monoclaw `Projects/short-form-video-pipeline/`) — HTML deck +
   OBS live take, for equation/diagram explainers narrated by the human.
3. **Assemble** (this skill) — fully automated faceless video: TTS voice,
   stock footage, burned captions.

## Prerequisites

- Binary: `Monoclaw/Rust/shortform-video/target/release/shortform-video`
  (build with `cargo build --release` in that directory).
- `ffmpeg`/`ffprobe` on PATH. Slim builds are fine (captions don't need
  libass).
- LLM stages need an OpenAI-compatible endpoint (`SHORTFORM_LLM_BASE_URL`,
  `SHORTFORM_LLM_MODEL`; local llama-server/mlx/LiteLLM works; `<think>`
  blocks are stripped automatically).
- Stock sourcing needs `SHORTFORM_PEXELS_API_KEY` or
  `SHORTFORM_PIXABAY_API_KEY`. A local directory of clips works with no key:
  `--source /path/to/clips`.
- Edge TTS needs network; `SHORTFORM_TTS_BACKEND=say` is the offline macOS
  fallback (subtitle timing degrades from word-accurate to proportional).
- Config file (optional): `~/.config/shortform-video/config.toml` — see the
  crate README for the full schema.

## Procedure

1. **Structure first when reach matters.** Load `short-form-viral-content`,
   draft the script with a cold-open hook (no "welcome to this video" — the
   LLM prompt already forbids it, but hook quality is on you), and save it to
   a file.
2. **Assemble.**
   - From a finished script:
     `shortform-video run --subject "<subject>" --script-file script.txt --aspect portrait`
   - From just a subject (LLM writes the script):
     `shortform-video run --subject "<subject>" --aspect portrait`
   - Useful flags: `--source pexels|pixabay|<local-dir>`, `--concat
     sequential` (visuals follow script order; search terms are generated in
     narrative order), `--transition fade`, `--bgm music.mp3`,
     `--language zh-CN`, `--paragraphs 2`, `--task-dir out/`.
3. **QC before showing the human.** Play `final.mp4`. Check: captions match
   narration and fit on screen; audio present and voice louder than BGM
   (defaults: voice 1.0, bgm 0.2); aspect correct; no black tail at the end.
   Artifacts (script.txt, subtitle.srt, materials.json with attribution
   pages) are all in the task dir for inspection.
4. **Publishing metadata.**
   `shortform-video social --subject "..." --script-file script.txt --platform tiktok`
   gives title/caption/hashtags within per-platform limits.
5. **Publishing is human-gated. Never auto-post.** Present the video and
   metadata; the human uploads. Stock attribution pages are recorded in
   `materials.json` — surface them when a platform or license requires
   credit.

## Per-stage commands (for partial workflows)

```bash
shortform-video script --subject "..."            # script only
shortform-video terms --subject "..." --script-file s.txt --ordered
shortform-video tts --script-file s.txt --output narration.mp3 --srt
shortform-video voices --locale en-US             # list Edge voices
```

## Failure modes

- `edge TTS connection failed` → network/endpoint issue; retry or fall back:
  `SHORTFORM_TTS_BACKEND=say`.
- `no usable video materials` → missing/invalid stock API key, or terms too
  niche; retry with broader `--terms-amount`, the other provider, or a local
  clips directory.
- `no subtitle font found` → set `SHORTFORM_FONT_PATH` to any .ttf.
- LLM errors → check the endpoint is up (for local mlx: `./serve.sh` in
  `Monoclaw/Deployments/Scripts/mlx`).
