# Harness Engineering: Ernest's Repos

**For:** Any Claude Code or OpenClaw agent working in Monoclaw or claw-portfolio.  
**Purpose:** Map the harness engineering concepts to what Ernest actually has,
what's missing, and what to build next.

---

## What Ernest Already Has (The Foundation)

Remarkably, the core feedforward infrastructure is already in place across
both repos. This is ahead of most codebases.

### Feedforward Guides (Already Built)

| Artifact | Location | What it does |
|----------|----------|-------------|
| `AGENTS.md` | Monoclaw root | Orientation, branch rules, what not to commit |
| `AGENTS.md` | claw-portfolio root | Repo orientation, stack, data rules, branch rules |
| `PROGRESS.md` | Per-project subdirs | State handoff between agent sessions |
| `PORTFOLIO-AGENT.md` | claw-portfolio root | Dedicated portfolio subagent identity |
| `SETUP-PORTFOLIO-WORKFLOWS.md` | claw-portfolio root | Workflow trigger phrases → commands |
| `SETUP.md` | claw-portfolio root | Cross-machine onboarding |
| `TRANSACTION-GRADING-SYSTEM.md` | claw-portfolio root | Design doc: desired state for grading feature |

The PROGRESS.md + AGENTS.md pattern per subdirectory is the ratchet principle
applied: each session adds to these files, they never shrink.

### Proto-Loops (Already Working)

The portfolio workflows are proto-loops — trigger phrase → script → structured
output → agent synthesis:

| Trigger | What fires | Output |
|---------|-----------|--------|
| "schwab download dates" | `schwab_download_ranges.py` | Date ranges for Schwab site |
| "ingest schwab" | `Scripts/ingest-schwab.sh` | Moves files, rebuilds masters, prints row counts |
| "portfolio outlook" | `schwab_portfolio_outlook.py` | Monte Carlo + DOI + earnings JSON → agent summary |
| "portfolio moves" | outlook + `/grading/patterns` | Cross-system buy/sell/trim synthesis |

These already follow the cybernetic pattern: sense (read CSVs, fetch prices)
→ actuate (compute signals) → report (structured output for agent to synthesize).

---

## What's Missing (The Gaps)

### Gap 1: No Feedback Sensors (Highest Priority)

There are no post-edit hooks. When an agent edits Python or TypeScript, there's
no automatic feedback loop. The agent can introduce type errors, lint violations,
or broken tests without knowing.

**What to build:**
```bash
# .claude/hooks/post-edit.sh in claw-portfolio
# Silent success. Exit 2 + output on failure.

CHANGED=$(git diff --name-only HEAD 2>/dev/null || true)

if echo "$CHANGED" | grep -q "^Python/"; then
    uv run ruff check . 2>&1 || exit 2
    uv run pytest -x --tb=short -q 2>&1 || exit 2
fi

if echo "$CHANGED" | grep -q "^JavaScript/"; then
    npm --prefix JavaScript/portfolio-dashboard run typecheck 2>&1 || exit 2
fi
```

Wire in `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{ "type": "command", "command": ".claude/hooks/post-edit.sh" }]
    }]
  }
}
```

### Gap 2: No ARCHITECTURE.md

Agents working in `Python/finance/` have to reverse-engineer the layer
structure from reading code. The layer boundaries are real and enforced
informally (business logic in services, DB access in repositories) but
not documented.

**What to build:** `Python/finance/ARCHITECTURE.md` with the layer diagram,
what-goes-where table, and the most common mistakes.

Key boundary that agents violate:
- Business logic leaking into `api/main.py` (it already has some — `REC_FILE`,
  `REC_REPORTS_DIR` were hardcoded there until recently)
- CSV reading happening in routers instead of being abstracted

### Gap 3: No spec.md Discipline

Tasks are handed to agents conversationally. There's no acceptance criteria
contract before work starts, which means agents interpret scope freely and
stopping conditions are fuzzy.

**What to build:** A `docs/templates/spec.md` template (see
`harness-implementation-guide.md` Pattern 4) and a habit of writing it
before any non-trivial feature.

### Gap 4: Transaction Grading Loop Not Closed

`calculate_sell_quality()` in `Python/finance/api/price_history.py` fails
silently for most real transactions. The dashboard tab shows "No graded sells
yet." This is a classic unclosed feedback loop: the sensor (yfinance price
fetch) fails, the actuator (quality score) gets no input, the loop produces
no output.

See `claw-portfolio/TRANSACTION-GRADING-STATUS.md` for full detail.

**What to build:** Debug endpoint that shows how many sells are processed
vs. skipped, plus disk cache for price history so yfinance failures don't
silently kill the whole scoring run.

### Gap 5: No Anti-Entropy Loop

There's no scheduled scan that catches quality drift. OpenAI automated their
Friday cleanup into a recurring agent loop. This is currently manual (or
doesn't happen).

**What to build eventually:** A GitHub Actions workflow or cron job that runs
ruff + eslint on a schedule, opens a PR for any class of violation found. 
Not urgent, but the natural endpoint of the harness maturation path.

---

## Recommended Build Order

### Immediate (next session)

1. **Post-edit hook for claw-portfolio** — biggest leverage for the least work.
   One shell script + one settings.json change. Every future session benefits.
   See `harness-implementation-guide.md` Pattern 3.

2. **`Python/finance/ARCHITECTURE.md`** — the layer diagram exists mentally,
   just needs to be written down. 30 minutes. Prevents the same architectural
   mistakes from recurring.

### Near-term

3. **Fix transaction grading data flow** — add debug logging to
   `price_history.py`, add disk cache, make `calculate_sell_quality()` more
   lenient when yfinance data is partial. See `TRANSACTION-GRADING-STATUS.md`.

4. **spec.md template** — create `docs/templates/spec.md` and use it for
   the next feature (E*Trade integration is the obvious candidate).

### Later

5. **Architecture boundary enforcement in CI** — once ARCHITECTURE.md is
   written, encode the layer rules as tests or lint rules.

6. **Anti-entropy cron** — GitHub Actions nightly scan opening fix PRs.

7. **E*Trade integration** — when adding a new brokerage, the spec.md
   discipline will be especially valuable (large, well-defined scope).

---

## The One Change With Highest ROI

If you only do one thing from this list: **add the post-edit hook.**

It closes the feedback loop that's currently missing from every coding session.
Every agent edit gets automatically type-checked and linted. Failures are
immediately visible with actionable remediation. The agent self-corrects
instead of accumulating errors across multiple edits.

Everything else on this list is valuable. This one changes how every future
session works.
