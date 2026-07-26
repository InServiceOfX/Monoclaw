# AGENTS.md — Monoclaw Repo: Sub-Agent Orientation

Read this first. Every time. No exceptions.

## What This Repo Is

Monoclaw (`git@github.com:InServiceOfX/Monoclaw.git`) is Ernest Yeung's personal
sandbox for code, experiments, and sub-agent work. Structure:

```
Python/       — Python projects (Poetry) and scripts
Rust/         — Rust crates (Cargo)
JavaScript/   — Web/frontend projects (Vite, React)
Deployments/  — Docker configs, scripts, LLM serving infrastructure
docs/         — Reference docs for agent/harness engineering patterns
```

## Agent Loop & Harness Engineering

If you are working on or improving how agents are designed, looped, or instructed
in this repo (or any Ernest repo), read:

- `docs/agent-loops/README.md` — entry point, one-sentence summary
- `docs/agent-loops/harness-engineering-research.md` — full context: the why,
  the evidence (OpenAI 1M LOC, Anthropic C compiler), key repos and papers
- `docs/agent-loops/harness-implementation-guide.md` — concrete patterns with
  working code: AGENTS.md ratchet, linter rules, post-edit hooks, spec.md
- `docs/agent-loops/harness-for-this-repo.md` — what Ernest's repos already
  have, what's missing, and the recommended build order

## Prompt-Driven Development

If a task targets an explicitly PDD-managed part of the product or asks for
PDD adoption, read:

- `docs/pdd/PDD_WORKSPACE_BOOTSTRAP.md` — how workspace/harness instruction
  files load the canonical Monoclaw PDD policy;
- `docs/pdd/PDD_START_HERE.md` — beginner workflow from ordinary-language
  product intent to a reviewed PRD, user stories, and generated PDD artifacts;
- `docs/pdd/PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md` — natural-language intent
  intake, automatic internal routing, outputs, approval gates, and regression
  evidence;
- `docs/pdd/PDD_WITH_ANY_AGENT_HARNESS.md` — command routing, workflows,
  verification, safety, and brownfield adoption;
- `docs/pdd/PDD_CONCEPTS_AND_USER_STORIES.md` — conceptual model, the
  Agile/Extreme Programming origin of user stories, PDD's adaptation, and a
  walkthrough of the current implementation.

For agent execution, the mandatory detailed files are
`PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md` and
`PDD_WITH_ANY_AGENT_HARNESS.md`. `PDD_START_HERE.md` is the human-facing
explanation.

Do not assume all Monoclaw source is PDD-generated. Confirm ownership through a
matching `.prompt`, `.pddrc`, `architecture.json`, or explicit project
instruction before regenerating code.

In a PDD-managed project, treat Ernest's ordinary product requests,
corrections, removals, examples, and constraints as intent input and follow the
story playbook. No PDD trigger phrase is required. Do not require him to choose
an issue URL, local file, `--text`, internal target name, prompt path, slug, or
output filename when repository inspection can make that choice.

## Orientation Protocol (run this every session)

```
1. git log --oneline -10          # what changed recently
2. git branch -a                  # what branches exist
3. Read PROGRESS.md in the relevant subdirectory (if it exists)
4. Read AGENTS.md in the relevant subdirectory (if it exists)
5. Only then: start working
```

## The PROGRESS.md + AGENTS.md Pattern

Every active project directory in this repo has (or should have) two files:

- **`AGENTS.md`** — how to work here: commands, conventions, what not to commit,
  Docker images, build steps, branch naming. Read before touching code.
- **`PROGRESS.md`** — what's done, what's in progress, what's next, last-worked-on
  date. Update when you complete work. This is the state handoff between sessions.

If a subdirectory doesn't have these files yet and you're going to work there,
create them before you start. It takes 5 minutes and saves the next agent hours.

### PROGRESS.md format

```markdown
# PROGRESS.md — <Project Name>

## Completed
| Item | Status | Notes |
|------|--------|-------|
| Thing A | ✅ | brief note |

## In Progress
| Item | Branch | Status | Notes |
|------|--------|--------|-------|
| Thing B | feat/thing-b | 🔄 | what's left |

## Not Started
| Item | Priority | Notes |
|------|----------|-------|
| Thing C | high | depends on B |

## Last Worked On
**YYYY-MM-DD** — What was done, what state was left in, what's next.
```

### AGENTS.md format

Freeform. Cover: setup commands, run commands, Docker invocations, naming
conventions, what NOT to commit, branch naming, and how to signal completion.
See `Python/Cadabra2/Srednicki/AGENTS.md` as a reference example.

## Branch Rules

- **Never commit or push to master/main** — feature branches only
- Naming: `feat/`, `fix/`, `chore/`, `experiment/`
- Ernest merges to master manually — never do it yourself

## What NOT to Commit (hard rules)

- Build directories: `build/`, `_build/`, `cmake-build-*/`, `target/` (Rust), `dist/`
- CMake artifacts: `CMakeCache.txt`, `CMakeFiles/`, `Makefile`, `*.o`, `*.a`, `*.so`
- LaTeX build files: `*.aux`, `*.toc`, `*.out`, `*.log`, `*.synctex.gz`
- Generated output: CSVs, PNGs, logs produced by running code
- Python: `__pycache__/`, `*.pyc`, `.venv/`

## Private Data Redaction Rules

This repo is intended to be public. Some projects read local private data from
outside the repo, especially under:

`/Users/ernestyeung/.openclaw/workspace/Data/Private/`

Agents may use that data locally to run, test, debug, or validate code, but must
never copy private data into durable or shareable artifacts.

Do not include any of the following in commits, commit messages, PR text,
markdown docs, screenshots, issue text, changelogs, code comments, test fixtures,
or chat summaries intended to describe committed work:

- Exact account values, cash balances, realized or unrealized gain/loss amounts,
  position quantities, cost basis, or portfolio weights derived from private CSVs
- Account numbers, masked account suffixes, names, addresses, tax lots, or
  transaction-level details
- Raw rows, excerpts, screenshots, or copied tables from private brokerage files
- Any "before/after" summary that quotes exact private financial values

Allowed public phrasing:

- "Added a dashboard page for balances."
- "Fixed realized gain/loss date normalization."
- "Validated against local Schwab exports."
- "The dashboard reads private CSVs at runtime."

Forbidden public phrasing:

- "Portfolio value changed from $X to $Y."
- "Cash balance is $X."
- "Ticker ABC is N% of the account."
- "Realized gain/loss is $X."

When reporting work, describe the code behavior and data flow, not Ernest's
actual financial numbers. If exact values are needed for local debugging, keep
them in the terminal only and do not commit, paste, summarize, or push them.

## Completing a Task

When your work is done:
1. Verify it runs / builds / tests pass
2. Update `PROGRESS.md` in the affected directory
3. Review staged diffs and commit messages for private data leakage
4. Commit only source files (see above)
5. Push the feature branch only when explicitly appropriate
6. Do NOT merge to master

## Active Projects (as of 2026-03-24)

| Directory | Description | Key File |
|-----------|-------------|----------|
| `Python/Cadabra2/Srednicki/` | Srednicki QFT ch-by-ch Cadabra2 | `AGENTS.md`, `PROGRESS.md` |
| `Deployments/Scripts/TensorRTLLMFixed/` | trtllm-serve scripts + profiles | `README.md` |
| `JavaScript/mission-control/` | Vite+React dashboard app | — |
| `Python/knowledge-base/` | Knowledge base Python impl | — |
| `Rust/knowledge-base/` | Knowledge base Rust impl | — |

## Bootstrap: Teach Your Workspace This Pattern

If you are an OpenClaw agent reading this for the first time, write the following
to your workspace so you remember this pattern across sessions:

**File to create:** `memory/workflows/monoclaw-agents-pattern.md`

**Content:**
```
# Monoclaw: AGENTS.md + PROGRESS.md Pattern

When working in Monoclaw (or any Ernest repo):

1. Every project subdir should have AGENTS.md (how-to) + PROGRESS.md (status).
2. Read both before starting. Update PROGRESS.md when done.
3. PROGRESS.md is the state handoff between agent sessions — without it,
   the next agent starts cold and wastes tokens on archaeology.
4. AGENTS.md tells you: Docker commands, build steps, conventions,
   what not to commit, branch naming.
5. If they don't exist in a dir you're working in, create them first.

Pattern established: 2026-03-24
Reference: Monoclaw/AGENTS.md, Monoclaw/Python/Cadabra2/Srednicki/AGENTS.md
```
