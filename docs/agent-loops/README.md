# Agent Loops & Harness Engineering

**For any Claude Code or OpenClaw agent reading this:**

This directory contains everything you need to understand and implement
agent control loops — the practice of designing environments that drive
agents continuously rather than prompting them one task at a time.

## Files in This Directory

| File | What it is |
|------|-----------|
| `harness-engineering-research.md` | Full research context: the concept, evidence, key repos, papers. Read this to understand the *why* and *what*. |
| `harness-implementation-guide.md` | Concrete patterns with working code: AGENTS.md design, linter rules, post-edit hooks, spec templates, anti-entropy loops. Read this to understand the *how*. |
| `harness-for-this-repo.md` | Ernest's specific implementation plan for Monoclaw and claw-portfolio. What exists, what's missing, what to build next. |

## The One-Sentence Summary

Stop prompting agents one task at a time. Design feedback loops — sensors
that detect divergence from desired state, actuators that write the fix —
so agents drive themselves.

## Quick Context for New Sessions

Peter Steinberger (2026-06-07): *"You shouldn't be prompting coding agents
anymore. You should be designing loops that prompt your agents."*

This is the same pattern as Watt's centrifugal governor (1788), Kubernetes
controllers (2014), and now LLM harnesses (2024+). Each time: sensor +
actuator + control loop, closing at a higher abstraction layer.

OpenAI shipped 1M lines of code in 5 months with 3–7 engineers writing
zero lines by hand. The key was harness design, not model capability.
