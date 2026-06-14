# Quickstart: Monitoring Agent & Self-Improving Loop

## For Another Hermes Agent

### 1. Read This First
```
docs/self-improving-agents/MONITORING_AGENT_RESEARCH.md
```

### 2. Key Files to Reference

| File | Purpose |
|------|---------|
| `MONITORING_AGENT_RESEARCH.md` | Full research: monitoring agents, 5-layer loop, business strategies |
| `MONITORING_AGENT_RESEARCH.md#part-1-monitoring-agent-implementations` | GitHub projects with code |
| `MONITORING_AGENT_RESEARCH.md#part-2-5-layer-recursive-self-improving-loop` | YC/Blomfield architecture |
| `MONITORING_AGENT_RESEARCH.md#part-3-business-function-self-improvement-strategies` | Per-function applications |

### 3. Immediate Action Items

#### To Implement a Monitoring Agent (like YC's)
```bash
# 1. Install kayba-ai/recursive-improve (closest to YC description)
pip install "recursive-improve[all] @ git+https://github.com/kayba-ai/recursive-improve"

# 2. Or use SIA framework (more complete)
pip install 'sia-agent[claude]'
export ANTHROPIC_API_KEY="your-key"
sia --task lawbench --max_gen 5 --run_id 1
```

#### To Apply 5-Layer Loop to a Business Function
1. **Define Sensor Layer** — What raw signals exist? (tickets, telemetry, calls, emails)
2. **Define Policy Layer** — What can AI do autonomously vs. needs human?
3. **Build Tool Layer** — Deterministic APIs (query DB, run tests, deploy, send Slack)
4. **Set Quality Gates** — Auto-tests, eval suites, human review thresholds
5. **Deploy Monitoring Agent** — Watches all traces, finds patterns, proposes fixes overnight

### 4. Code Pattern to Replicate

```python
# Core monitoring loop (from research)
async def monitoring_agent_loop():
    while True:
        traces = await trace_store.get_recent(hours=24)
        patterns = await analyzer.analyze(traces)  # sandboxed code execution
        fixes = [await proposer.propose_fix(p) for p in patterns]
        validated = await evaluator.validate(fixes, traces)
        for fix in validated:
            await git.create_pr(fix)
            if await ci.passes():
                await git.merge_and_deploy()
        await asyncio.sleep(24 * 3600)
```

### 5. Business Functions Ready for Self-Improvement

| Function | Sensor | First Win |
|----------|--------|-----------|
| Customer Support | Tickets, chats, resolution time | Auto-KB updates from ticket clusters |
| Product Analytics | Funnel drops, feature usage | Overnight A/B test deployment |
| Engineering | Build failures, test flakes, PR comments | Self-healing CI + coding standards |
| Sales | Call transcripts, emails, deal stages | Auto battle cards from objections |
| Marketing | Campaign performance, SEO | Self-optimizing content variants |

### 6. Key Architectural Principles

1. **Record Everything** — "If not recorded, it didn't happen to the AI"
2. **Ephemeral Software, Precious Data** — Regenerate tools; store context/skills
3. **Humans at the Edge** — AI runs loops; humans do novel/ethical/high-stakes
4. **Token Maxing > Headcount** — Measure tokens/function/week
5. **Meta-Agent Evolves Too** — Monthly: evolve prompts, strategies, tool chains

### 7. Quick Test: Verify Understanding

Ask the agent:
> "Explain the 5-layer loop and give a concrete example for customer support"

Expected answer should cover:
- Sensor: tickets, chats, resolution times
- Policy: auto-reply known, escalate novel
- Tools: query KB, create tickets, draft responses
- Quality: human review for novel, safety filters
- Learning: monitoring agent clusters issues → writes KB → updates FAQ

---

## Related Workflows

- **YouTube Transcript Archive**: `docs/youtube-transcript-workflow/README.md`
- **Agent Loops Research**: `docs/agent-loops/` (in Monoclaw)

## Version

Created: 2026-06-14
Version: 1.0.0