# Monitoring Agent & Self-Improving Systems Research

**Comprehensive research on monitoring agents, recursive improvement loops, and AI-native company architectures.**

## Overview

This document captures research on:
1. **Monitoring Agent implementations** — Systems that watch other agents, detect failures, and auto-fix
2. **5-Layer Recursive Self-Improving Loop** — Universal architecture for AI-native organizations (from Tom Blomfield / YC)
3. **Business Function Self-Improvement Strategies** — Applying the loop to product, support, sales, engineering, etc.

---

## Part 1: Monitoring Agent Implementations

### Core Pattern: Meta-Agent Observes → Diagnoses → Fixes → Deploys

```
┌─────────────────────────────────────────────────────────────┐
│                    WORKER AGENT(S)                          │
│  (executes tasks, generates execution traces)               │
└─────────────────────┬───────────────────────────────────────┘
                      │ execution traces
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              MONITORING / FEEDBACK AGENT                    │
│  • Captures ALL traces (not just failures)                  │
│  • Runs pattern analysis (sandboxed code execution)         │
│  • Identifies: missing tools, bad prompts, skill gaps       │
│  • Proposes targeted fixes with keep-or-revert evaluation   │
└─────────────────────┬───────────────────────────────────────┘
                      │ fixes (code/prompt/skill changes)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              DEPLOYMENT / EVOLUTION LOOP                    │
│  • Creates PRs → auto-review → merge → deploy               │
│  • Runs nightly / per-generation                            │
│  • Tracks improvement metrics across generations            │
└─────────────────────────────────────────────────────────────┘
```

### Key GitHub Projects

| Project | Description | Key Innovation |
|---------|-------------|----------------|
| **kayba-ai/recursive-improve** ⭐ | *"Every LLM call captured. Agent analyzes traces, identifies failure patterns, applies targeted fixes."* | **Recursive Reflector** — writes & executes Python in sandbox to search patterns, isolate errors, iterate until fixed |
| **kayba-ai/agentic-context-engine** | Implements Stanford's "Agentic Context Engineering" | Recursive Reflector analyzes traces via sandboxed code execution |
| **hexo-ai/sia** (SIA) | Self-Improving Agent with **Meta-Agent + Target-Agent + Feedback-Agent** | Feedback-Agent reads full trajectory → picks harness rewrite OR weight update → diff successive versions |
| **lsdefine/GenericAgent** | *"Grows skill tree from 3.3K-line seed, 6x less token consumption"* | Skill tree evolution + contextual information density maximization |
| **EvoAgentX/EvoAgentX** | Self-evolving agent ecosystem | Construction → Assessment → Optimization loop |
| **devswarm** (Issue #355) | Monthly evolution: collect telemetry → evolve prompts → evolve decomposition → evolve tool chains | **Meta-agent must also be evolvable** |
| **Memento-Skills** (Zhou et al. 2026) | *"Treats markdown skills as persistent memory, read–write learning loop"* | Failure attribution → selective skill rewriting → new skill discovery |
| **TextGrad** (zou-group/textgrad) | *"Autograd engine for textual gradients"* — PyTorch-style API | Forward pass → loss → backward LLM critiques → textual gradient → prompt rewrite |
| **SkillGrad** (2026) | Optimizes agent skills like gradient descent | Rewrites base skills substantially based on failure feedback |

### Monitoring Agent Code Pattern (Simplified)

```python
async def monitoring_agent_loop():
    while True:
        # 1. COLLECT: Get all execution traces from last period
        traces = await trace_store.get_recent(hours=24)
        
        # 2. ANALYZE: Find failure patterns (run in sandbox)
        patterns = await analyzer.analyze(traces)
        # patterns = [
        #   {"type": "missing_tool", "frequency": 47, "query": "office hours scheduling"},
        #   {"type": "skill_outdated", "frequency": 23, "skill": "intro_matching"},
        # ]
        
        # 3. PROPOSE FIXES: For each pattern, generate targeted fix
        fixes = []
        for pattern in patterns:
            fix = await proposer.propose_fix(pattern)
            fixes.append(fix)  # e.g., new tool, updated skill, prompt tweak
        
        # 4. VALIDATE: Run eval suite on proposed fixes
        validated = await evaluator.validate(fixes, traces)
        
        # 5. DEPLOY: Create PRs, auto-merge if passing
        for fix in validated:
            await git.create_pr(fix)
            await ci.run_tests()
            if ci.passed:
                await git.merge_and_deploy()
        
        await asyncio.sleep(24 * 3600)  # Run nightly
```

---

## Part 2: 5-Layer Recursive Self-Improving Loop (YC / Tom Blomfield)

### The Universal Architecture

> "A company can be seen as a set of recursive self-improving AI loops. Each loop has a sensor layer, a policy layer, a tool layer, a quality gate, and a learning mechanism." — AGO Blog / Tom Blomfield

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECURSIVE SELF-IMPROVING LOOP                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │ 1. SENSOR   │───▶│ 2. POLICY   │───▶│ 3. TOOL     │        │
│   │   LAYER     │    │   LAYER     │    │   LAYER     │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│        │                   │                   │                │
│        ▼                   ▼                   ▼                │
│   Raw signals:         Rules:              Deterministic       │
│   • Support tickets    • What AI can do    APIs:              │
│   • Product telemetry  • What needs human  • Query DB         │
│   • Churn events       • What must log     • Check calendar   │
│   • Sales calls        • Escalation rules  • Run tests        │
│   • Code changes       • Safety boundaries • Deploy preview   │
│   • Customer emails    • Rate limits       • Send Slack       │
│   • Cancellations                                               │
│                                                                 │
│        │                   │                   │                │
│        └───────────────────┼───────────────────┘                │
│                            ▼                                    │
│                   ┌─────────────────┐                           │
│                   │ 4. QUALITY GATE │                           │
│                   └─────────────────┘                           │
│                            │                                    │
│              ┌─────────────┼─────────────┐                      │
│              ▼             ▼             ▼                      │
│         Auto tests      Eval suites   Safety filters            │
│         Human review    (high-risk)   Canary deploy             │
│              │             │             │                       │
│              └─────────────┼─────────────┘                      │
│                            ▼                                    │
│                   ┌─────────────────┐                           │
│                   │ 5. LEARNING     │◀─── MONITORING AGENT      │
│                   │   MECHANISM     │      (watches all,        │
│                   └─────────────────┘       diagnoses, fixes)   │
│                            │                                    │
│                            └──────────┬────────────────────────┘
│                                       │ feedback
│                                       ▼
│                              ┌─────────────────┐
│                              │  LOOP RESTARTS  │
│                              │  (overnight)    │
│                              └─────────────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Quotes from Blomfield Talk

- **"The aha moment for me came when we put a monitoring agent on top of that, which looked at every single query every single YC employee was doing and saw when it worked and when it did not work."**
- **"When it did not work, it's like, oh, why not? What would have made this query work? Do we need different deterministic tools? Do we need to update the skills file? Do we need a different database for you? Do we need a new index? And this happened... literally happens overnight now."**
- **"For me, that was like the holy [__] [__] But that's not just AI making you 20 or 30% more valuable, it is the AI going through this loop to figure out how to self-improve."**
- **"If you can identify parts of your company that work like this and eliminate as much of have the human in kind of a monitoring or supervisory capacity, you can just throw tokens at this problem and your company will get better."**
- **"Burn tokens, not headcount. We are seeing companies get to demo day with about 5x more revenue per employee than they did 18 months ago."**
- **"I think middle management is done. I just don't think you need middle management for this coordination problem. I think AI should be doing it."**
- **"Make the entire organization legible to AI. What does that mean? It means you've got to record everything... If it is recorded, it happened to the AI. If it did not get recorded, it did not happen to your intelligence."**
- **"Software is ephemeral. The valuable part is the comprehension inside people's heads... The models get smarter in a month or two. Throw the software away. Give it your original set of instructions and regenerate the software."**

---

## Part 3: Business Function Self-Improvement Strategies

### Applying the 5-Layer Loop to Each Function

| Function | Sensor Input | Policy Rules | Tool Layer | Quality Gate | Learning Mechanism |
|----------|--------------|--------------|------------|--------------|-------------------|
| **Product Analytics** | Funnel drop-offs, feature usage, cohort retention | Auto-test variants < 5% traffic | Query analytics DB, create A/B tests, deploy variants | Statistical significance, no regression on core metrics | Monitoring agent finds highest-friction step → researches best practices → writes test → deploys winner |
| **Customer Support** | Incoming tickets, chat logs, resolution times, CSAT | Auto-reply known issues, escalate novel | Query KB, create tickets, draft responses, update FAQ | Human review for novel issues, safety filters | Clusters issues → drafts KB articles → updates FAQ → suggests product fixes |
| **Sales** | Call transcripts, email threads, deal stages, win/loss | Auto-send follow-ups, flag at-risk | Query CRM, generate battle cards, update templates | Human approval for pricing, legal review | Finds objection patterns → generates battle cards → updates outreach templates |
| **Engineering** | Build failures, test flakes, PR comments, incidents | Auto-fix lint/style, escalate logic bugs | Query codebase, run tests, create PRs, deploy preview | CI passes, code review, staging deploy | Categorizes failures → writes fixes/prevention → updates CI/checks |
| **Marketing** | Campaign performance, SEO rankings, engagement | Auto-pause underperforming, scale winners | Query analytics, generate content variants, A/B test | Statistical significance, brand review | Identifies winning angles → generates variants → tests → scales winners |
| **HR/Recruiting** | Candidate feedback, interview scores, hire quality | Auto-screen qualified, flag bias | Query ATS, generate rubrics, schedule interviews | Human review for final decisions, compliance | Finds bias/gaps → updates rubrics → generates better screeners |
| **Finance** | Expense anomalies, forecast variance, cash flow | Auto-flag unusual, approve routine | Query ERP, generate reports, reconcile | Human approval for large items, audit trail | Learns patterns → improves categorization → predicts cash flow |

### Additional Self-Improving Strategies (Beyond User Manual)

1. **Living Documentation** (YC User Manual pattern)
   - Record all meetings/decisions → diarize → synthesize → regenerate docs monthly
   - Applies to: architecture decisions, product specs, onboarding guides, runbooks

2. **Ephemeral Internal Tools** (Blomfield: "Software is ephemeral, context is valuable")
   - Codex/agents one-shot dashboards, admin panels, workflow tools
   - Regenerate when models improve; store only the *instructions/context*

3. **Token Maxing as Metric** ("Burn tokens, not headcount")
   - Measure: tokens spent per function per week
   - Directionally indicates who's pushing the loop forward

4. **Humans at the Edge** (Blomfield)
   - AI runs the loop; humans handle: novel situations, ethics, high-stakes (co-founder breakups), sales relationships

5. **Meta-Agent Evolution** (devswarm, SIA)
   - The monitoring agent itself gets improved by a higher-level loop
   - Monthly: evolve prompts, decomposition strategies, tool chains

6. **Persistent Skill Memory** (Memento-Skills)
   - Treat skills as mutable markdown files
   - On failure: attribute to skill → rewrite skill → persist

---

## Part 4: Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Set up trace capture for all agent interactions
- [ ] Implement basic monitoring agent (pattern detection)
- [ ] Create sensor layer for one business function (e.g., support tickets)

### Phase 2: First Loop (Week 3-4)
- [ ] Connect monitoring agent → policy → tools → quality gate → learning
- [ ] Run nightly on support function
- [ ] Measure: failure rate reduction, auto-fix success rate

### Phase 3: Expand Functions (Month 2)
- [ ] Apply to product analytics (self-optimizing funnel)
- [ ] Apply to engineering (self-healing CI)
- [ ] Build shared infrastructure (trace store, deployment pipeline)

### Phase 4: Meta-Evolution (Month 3+)
- [ ] Implement meta-agent that evolves the monitoring agent
- [ ] Monthly prompt/strategy evolution
- [ ] Cross-function learning transfer

---

## References

### Papers & Articles
- **Reflexion** (Shinn et al. 2023) — Self-reflection via natural language feedback
- **TextGrad** (Yuksekgonul et al. 2024) — Autograd for textual gradients (Nature)
- **Memento-Skills** (Zhou et al. 2026) — Agents designing agents via skill rewriting
- **SkillGrad** (2026) — Optimizing agent skills like gradient descent
- **GEPA** (2024) — Genetic-Pareto prompt evolution
- **Agentic Context Engineering** (Stanford 2025) — Recursive Reflector pattern

### Talks
- **Tom Blomfield (YC)** — "How to Build a Self-Improving Company with AI" (2026)
- **Diana (YC)** — Related talk referenced by Blomfield

### GitHub Repos (Starred)
- kayba-ai/recursive-improve
- kayba-ai/agentic-context-engine
- hexo-ai/sia
- lsdefine/GenericAgent
- EvoAgentX/EvoAgentX
- zou-group/textgrad
- justrach/devswarm (Issue #355)
- ShengranHu/ADAS (Meta Agent Search)

---

## Version

Created: 2026-06-14
Version: 1.0.0
Source: Research compiled from GitHub, papers, YC talk transcript (X_JsIHUfUjc)