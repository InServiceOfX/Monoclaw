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
```

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

## Completing a Task

When your work is done:
1. Verify it runs / builds / tests pass
2. Update `PROGRESS.md` in the affected directory
3. Commit only source files (see above)
4. Push the feature branch
5. Do NOT merge to master

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
