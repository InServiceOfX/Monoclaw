# Monoclaw Documentation

## Overview

This directory contains reusable workflows, research, and patterns for Hermes agents and AI-native systems.

## Structure

```
docs/
├── youtube-transcript-workflow/     # YouTube transcript archival + search
│   ├── README.md                    # Main entry point
│   ├── SETUP.md                     # Installation & configuration
│   ├── NAMING_CONVENTION.md         # File naming rules
│   ├── INDEX_SCHEMA.md              # index.json structure
│   └── USAGE_EXAMPLES.md            # Common workflows & scripts
├── self-improving-agents/           # Monitoring agents & recursive loops
│   ├── MONITORING_AGENT_RESEARCH.md # Deep research: agents, 5-layer loop, strategies
│   └── QUICKSTART.md                # Quick reference for another agent
├── agent-loops/                     # Agent loop & harness engineering (existing)
│   ├── README.md
│   ├── harness-engineering-research.md
│   ├── harness-implementation-guide.md
│   └── harness-for-this-repo.md
└── ... (other existing docs)
```

---

## Quick Access

### YouTube Transcript Workflow
**Purpose**: Archive YouTube transcripts with timestamps, metadata, and searchable index.

```bash
# Archive a video
python3 ../scripts/youtube-transcript/archive_transcript.py "https://youtu.be/VIDEO_ID"

# Search
python3 ../scripts/youtube-transcript/search_index.py "AI agent loops"
```

**Key Files**:
- `README.md` — Complete overview
- `SETUP.md` — Dependencies, configuration, troubleshooting
- `NAMING_CONVENTION.md` — `{Channel}_{Title}.json` format
- `INDEX_SCHEMA.md` — `index.json` structure
- `USAGE_EXAMPLES.md` — Batch, filter, export, cron examples

**Scripts**: `../scripts/youtube-transcript/`
- `archive_transcript.py` — Fetch + save + index
- `search_index.py` — Query by keyword, channel, tag, recency
- `common.py` — Shared utilities (sanitization, index I/O, tagging)

---

### Self-Improving Agents / Monitoring Agent Research
**Purpose**: Research on monitoring agents that watch other agents, detect failures, and auto-fix overnight — plus the 5-layer recursive self-improving loop for AI-native companies (from Tom Blomfield / YC).

**Key Files**:
- `MONITORING_AGENT_RESEARCH.md` — **Complete research document**
  - Part 1: Monitoring Agent implementations (8+ GitHub projects with code)
  - Part 2: 5-Layer Loop (Sensor → Policy → Tools → Quality → Learning)
  - Part 3: Business function strategies (support, product, sales, eng, marketing, HR)
  - Part 4: Implementation roadmap
- `QUICKSTART.md` — Quick reference for another agent

**Key GitHub Projects Referenced**:
| Project | Description |
|---------|-------------|
| `kayba-ai/recursive-improve` | Captures traces → analyzes patterns → applies fixes (closest to YC) |
| `kayba-ai/agentic-context-engine` | Stanford's Agentic Context Engineering — Recursive Reflector |
| `hexo-ai/sia` | Meta/Target/Feedback agent architecture with harness & weight updates |
| `lsdefine/GenericAgent` | Skill tree evolution from 3.3K-line seed |
| `EvoAgentX/EvoAgentX` | Self-evolving agent ecosystem |
| `devswarm` | Monthly evolution: telemetry → prompts → decomposition → tools |
| `Memento-Skills` | Skills as persistent markdown, read-write learning loop |
| `TextGrad` | Autograd engine for textual gradients |

---

## For Another Hermes Agent

### To Set Up YouTube Transcript Workflow
1. Read: `youtube-transcript-workflow/README.md`
2. Run: `SETUP.md` steps (install deps, configure paths)
3. Use: `archive_transcript.py` and `search_index.py`

### To Get Monitoring Agent / Self-Improving Context
1. Read: `self-improving-agents/MONITORING_AGENT_RESEARCH.md`
2. Reference: `QUICKSTART.md` for immediate action items
3. Implement: Start with `kayba-ai/recursive-improve` or `hexo-ai/sia`

### To Understand Agent Loop Patterns
1. Read: `agent-loops/README.md` (entry point)
2. Deep dive: `harness-engineering-research.md`
3. Implementation: `harness-implementation-guide.md`

---

## Environment Variables

| Variable | Default | Used By |
|----------|---------|---------|
| `YT_TRANSCRIPT_DIR` | `~/.openclaw/workspace/Data/Public/youtube-transcripts` | YouTube workflow |
| `YT_INDEX_FILE` | `~/.openclaw/workspace/Data/Public/youtube-transcripts/index.json` | YouTube workflow |

---

## Version

Updated: 2026-06-14