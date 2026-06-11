# Harness Engineering Research

**Captured:** 2026-06-09  
**Source:** Deep research session on Peter Steinberger's agent loop advocacy,
George (@odysseus0z)'s cybernetics framing, and OpenAI/Anthropic implementations.  
**For:** Any Claude Code or OpenClaw agent that needs full context on this topic.

---

## The Trigger

Peter Steinberger (@steipete), 2026-06-07:
> "Here's your monthly reminder that you shouldn't be prompting coding agents
> anymore. You should be designing loops that prompt your agents."

George (@odysseus0z) replied with a cybernetics framing:
> "Folks it is just control loop. Think of Kubernetes. You write desired
> state/spec, what to observe/status, the controller, and the kubelet. You let
> this whole control loop sense and actuate to prompt/drive the agent."

George's full article: "Harness Engineering Is Cybernetics"
https://x.com/odysseus0z/status/2030416758138634583

---

## The Conceptual Foundation

### The Core Equation

The field converged in early 2026 around one formulation: **Agent = Model + Harness**.
The harness is everything that is not the model — execution environment, tools,
instructions, feedback sensors, constraints.

The shift: engineer the *environment* so correct behavior becomes structurally
inevitable rather than probabilistically coaxed.

Mitchell Hashimoto (HashiCorp co-founder), 2026-02-05:
> "Anytime you find an agent makes a mistake, you take the time to engineer a
> solution such that the agent never makes that mistake again."

Every line of your AGENTS.md should trace to a specific thing that went wrong.

### The Three Cybernetic Waves (George's Framework)

| Wave | System | Sensor | Actuator | Human Role Shift |
|------|--------|--------|----------|-----------------|
| 1788 | Watt's centrifugal governor | Spinning fly-balls measure rotational speed | Steam valve | Stopped turning valve → designed the governor |
| 2014 | Kubernetes controllers | Probes observe actual pod state | Container scheduler | Stopped restarting services → wrote declarative specs |
| 2024+ | LLM agent harness | LLM reads code for intent and quality | LLM writes corrective code | Stopped writing code → designs the harness |

**The breakthrough in Wave 3:** LLMs are the first technology that can act as
both sensor and actuator at the *architectural* level. A syntax linter operates
on tokens. An LLM can evaluate whether a module serves a long-term system design
principle. The feedback loop closes on *intent*, not just syntax.

"You stop turning the valve. You steer." (κυβερνήτης — the same Greek root that
gave Kubernetes its name.)

### Why the Codebase Was the Holdout

Code had feedback loops at the lower levels:
- Compilers close a loop on syntax
- Test suites close a loop on behavior  
- Linters close a loop on style

These are real cybernetic controls — but they only operate on properties that can
be checked mechanically: does it compile, does it pass, does it follow the rules?

Everything above that — does this change fit the architecture? is this abstraction
going to cause problems as the codebase grows? — had no sensor and no actuator.
Only humans could operate at that level, on both sides.

LLMs changed both at once.

### Feedforward vs. Feedback (Martin Fowler's Synthesis)

Martin Fowler, `martinfowler.com/articles/harness-engineering.html`:

- **Feedforward guides** (preventive): AGENTS.md, architecture docs, test-how-to
  skills. Increase probability of quality on first attempt.
- **Feedback sensors** (corrective): Linters, type checkers, tests, code review
  agents. Enable self-correction loops.

Critical rule: sensors must produce output **optimized for LLM consumption**, not
humans. A message like `"You violated our module boundary rule; move this logic to
the Service layer"` is a feedback sensor that simultaneously rejects and coaches.

You get failure from using only one side: pure feedforward agents repeat structural
violations; pure feedback agents know what's wrong but have no preventing force.

---

## The Evidence

### OpenAI: 1 Million Lines, Zero Hand-Written

**Post:** `https://openai.com/index/harness-engineering/`  
**Author:** Ryan Lopopolo (OpenAI Frontier & Symphony)  
**Deep dive:** `https://www.latent.space/p/harness-eng`

Over 5 months starting ~August 2025: 3 engineers (growing to 7) shipped a beta
product with ~1 million lines of code, ~1,500 merged PRs, zero manually-written
source code. Throughput scaled from ~0.25 engineer-equivalents per person at start
to 3–10 engineer-equivalents per person.

**Key findings:**

1. **The "AI Slop" Friday Problem:** Initially spent every Friday cleaning up
   low-quality AI-generated code. Fix: wrote automated agents that scan for
   pattern violations and open cleanup PRs automatically. Cleanup became a loop.

2. **Custom Linter as Encoded Standard:** When agents repeatedly created duplicate
   helper functions, they wrote an ESLint rule banning that function from being
   defined anywhere except the approved location. The rule was written by the agent
   itself with 100% test coverage.

3. **Architectural Layering as CI Gate:** Dependency sequence enforced as structural
   tests: `Types → Config → Repo → Service → Runtime → UI`. CI fails on violation.
   Not a suggestion — a hard gate.

4. **Knowledge Infrastructure:**
   - `AGENTS.md` (~100 lines): pointers to deeper docs, not a dump
   - `ARCHITECTURE.md` (~200 lines): map of code pieces and connections
   - `docs/decisions/` — Architecture Decision Records (ADRs)
   - `core_beliefs.md`: product vision, engineering values
   - `tech_tracker.md`: agents review business logic against documented guardrails

5. **Self-Improving Harness:** Agents review session logs daily. Nightly agent loops
   scan failed builds and PR comments to update repository guardrails. Collective
   learning is automatic.

### Anthropic: 16 Parallel Agents Build a C Compiler

**Post:** `https://www.anthropic.com/engineering/building-c-compiler`  
**Author:** Nicholas Carlini (Anthropic)

A Rust-based C compiler capable of compiling PostgreSQL, Redis, FFmpeg, CPython,
and the Linux 6.9 kernel. Built by 16 parallel Claude agents, ~$20K API spend.

**Carlini's emphasis:**
> "Most of my effort went into designing the environment around Claude — the tests,
> the environment, the feedback."

Embarrassingly simple prompts. Carefully designed test infrastructure.

**The harness design:**

Core loop per agent:
```bash
while true; do
    claude --dangerously-skip-permissions \
           -p "$(cat AGENT_PROMPT.md)" \
           --model claude-opus-X-Y &> "$LOGFILE"
done
```
Sessions terminate and immediately restart. The prompt says "break it into small
pieces, keep going until it's perfect."

**Coordination:**
- Agents write `.txt` files to `current_tasks/` to claim work (lockfiles)
- Git forces conflict resolution when two agents attempt the same task
- Claude resolves merge conflicts autonomously

**Critical insight on test design:**
> "The task verifier is nearly perfect, otherwise Claude will solve the wrong
> problem."

Test constraints:
- Output only a few lines; errors explicitly marked (`ERROR: [reason]`)
- `--fast` flag runs a random 1–10% sample to prevent context exhaustion
- GCC used as ground-truth oracle for comparative testing

---

## Key Resources

### Must-Read Articles

| Source | URL | Key contribution |
|--------|-----|-----------------|
| Peter Steinberger | `https://x.com/steipete/status/2063697162748260627` | The original "design loops" framing |
| George (@odysseus0z) | `https://x.com/odysseus0z/status/2030416758138634583` | Cybernetics / Watt / Kubernetes lineage |
| Martin Fowler | `https://martinfowler.com/articles/harness-engineering.html` | Most rigorous framework; feedforward/feedback taxonomy |
| Mitchell Hashimoto | `https://mitchellh.com/writing/my-ai-adoption-journey` | Canonical practitioner account; ratchet principle |
| OpenAI harness post | `https://openai.com/index/harness-engineering/` | 1M LOC, 0 hand-written; ghost libraries; custom lints |
| Ryan Lopopolo (Latent Space) | `https://www.latent.space/p/harness-eng` | Deep implementation detail; Symphony system |
| Anthropic C compiler | `https://www.anthropic.com/engineering/building-c-compiler` | Best concrete parallel agent harness example |
| Addy Osmani: Loop Engineering | `https://addyosmani.com/blog/loop-engineering/` | 5 components: automations, worktrees, skills, plugins, sub-agents |
| HumanLayer | `https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents` | TypeScript/Biome hook implementation |
| Augment Code | `https://www.augmentcode.com/guides/harness-engineering-ai-coding-agents` | Golden principles, Plan-Execute-Verify loop |
| Epsilla cybernetics | `https://www.epsilla.com/blogs/from-coders-to-controllers-the-cybernetics-of-harness-engineering` | Historical progression detail |

### Key GitHub Repos

| Repo | What it demonstrates |
|------|---------------------|
| `github.com/strongdm/attractor` | Most explicit formalization of the observe/reconcile loop — read `coding-agent-loop-spec.md` |
| `github.com/Chachamaru127/claude-code-harness` | Plan→Work→Review cycle; spec.md as desired state; `/harness-plan`, `/harness-work`, `/harness-review` commands |
| `github.com/peteromallet/desloppify` | Automated anti-entropy scanner; `scan → next → resolve` loop; 29 languages |
| `github.com/intertwine/hive-orchestrator` | Git-native multi-agent; `.hive/tasks/*.md`; promotion policy as code |
| `github.com/langchain-ai/deepagents` | Batteries-included LangGraph harness; sub-agents, context compaction, MCP |
| `github.com/rasbt/mini-coding-agent` | Minimal 6-component reference; clean Python |
| `github.com/Aider-AI/aider-swe-bench` | Minimal test-driven loop: run until tests pass, max 3 attempts |
| `github.com/ai-boost/awesome-harness-engineering` | 250+ curated repos, tools, patterns, templates |

### Academic Papers

| Paper | arXiv | Key contribution |
|-------|-------|-----------------|
| Code as Agent Harness | `arXiv:2605.18747` | 2026 survey; 3-layer taxonomy: Harness Interface / Mechanisms / Scaling |
| Agentic Harness Engineering | `arXiv:2604.25850` | Observability-driven automatic harness evolution |
| SWE-agent (NeurIPS 2024) | `arXiv:2405.15793` | Agent-Computer Interface design; linting at edit-time; file viewer limits |

---

## The Minimal Loop (What It Looks Like in Code)

From the `attractor` spec — the formal observe/reconcile cycle:

```
FUNCTION process_input(session, user_input):
    session.history.APPEND(UserTurn(user_input))
    drain_steering(session)         # inject any queued guidance

    LOOP:
        response = llm.complete(session.history)
        session.history.APPEND(AssistantTurn(response))

        IF response.tool_calls IS EMPTY: BREAK     # natural completion

        results = execute_tool_calls(response.tool_calls)
        session.history.APPEND(ToolResultsTurn(results))
        drain_steering(session)

        IF detect_loop(session.history, window=N):
            inject_steering("You appear stuck. Try a different approach.")
```

The sophistication lives in `execute_tool_calls` — specifically whether tool
output is **optimized for LLM consumption** (instructions, not blame).

---

## Seven Key Principles

1. **Structural > Probabilistic.** A lint rule that blocks the PR is infinitely
   more reliable than a line in AGENTS.md that says "please don't." Use both,
   but favor structure.

2. **Sensors optimized for LLMs, not humans.** Error messages are injected into
   the agent's context. Write them as instructions:
   `"Move this to services/ per the architecture boundary rule in ARCHITECTURE.md"`
   not `"ESLint error: import violation."`

3. **Silent success, verbose failure.** Don't surface 4,000 passing test lines.
   Context window is finite. Exit 0 = silence. Exit non-zero = full output.

4. **AGENTS.md is a ratchet.** Never shrink it, only grow it. Each line is a
   hardened defense against a specific past mistake.

5. **Harness = feedforward + feedback.** Missing either breaks the loop.
   Prevention (guides) + detection (sensors) both required.

6. **High-quality tests are the primary oracle.** Carlini's finding: if the test
   verifier is wrong, the agent solves the wrong problem perfectly.

7. **Loop engineering is one floor above harness engineering.** The harness equips
   a single agent run. The loop schedules, spawns, and feeds itself. Start with
   harness; graduate to loop.
