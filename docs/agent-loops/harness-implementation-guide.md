# Harness Implementation Guide

**For:** Any Claude Code or OpenClaw agent implementing agent control loops.  
**Companion to:** `harness-engineering-research.md` (the why/what)  
**This file:** The how — concrete patterns with working code.

---

## Pattern 1: AGENTS.md as an Error Ratchet

The file starts small and grows reactively. Every rule traces to a specific
past failure. Never remove lines — only add them.

```markdown
# AGENTS.md

## Stack
- Python 3.12, FastAPI, React 19 + TypeScript

## Build & Test (run these before marking any task done)
- Backend: `uv run pytest -x --tb=short`
- Frontend: `npm run typecheck && npm test -- --run`
- Lint:     `uv run ruff check . && npx eslint src/`

## Architecture (import boundaries — CI enforces these)
- `api/routers/`    → no business logic; call services only
- `api/services/`   → business logic; no direct DB calls
- `api/repositories/` → all DB access lives here
- Never import from `frontend/` into `backend/`

## Anti-patterns (each line = a documented past failure)
- Never use `print()`; use `logger.info("event", **data)`
- Never define date helpers outside `lib/utils/dates.ts`
- Never write raw SQL; use the repository layer
- Never suppress lint inline (`# noqa`, `// eslint-disable`); fix the root cause

## Verification checklist
- [ ] Tests pass: `uv run pytest -x`
- [ ] Types pass: `npm run typecheck`
- [ ] Lint clean: `uv run ruff check . && npx eslint src/`
- [ ] PROGRESS.md updated
- [ ] No private data in any committed file
```

**The ratchet rule:** when an agent makes a mistake, add a line. When you
find yourself explaining the same thing twice, it should be in AGENTS.md.

---

## Pattern 2: Custom Linter with LLM-Optimized Remediation

The error message is injected into the agent's context window. Write it
as an instruction, not a complaint.

### ESLint (TypeScript/React)

```javascript
// .eslintrc.js — all violations are "error", never "warn"
module.exports = {
  rules: {
    "no-restricted-syntax": [
      "error",
      {
        selector: "CallExpression[callee.name='console']",
        message: "Use logger.info({event: 'name', ...data}) from lib/logger.ts. Import: import { logger } from '@/lib/logger'"
      },
      {
        selector: "ImportDeclaration[source.value=/^\\.\\.\\/.*backend/]",
        message: "Frontend cannot import from backend/. Add an API endpoint instead and fetch from the frontend."
      }
    ],
    "max-lines-per-function": ["error", {
      "max": 60,
      "message": "Function exceeds 60 lines. Extract sub-functions. Single-responsibility principle applies."
    }]
  }
}
```

### Ruff (Python)

```toml
# pyproject.toml
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]
# All violations are errors by default in ruff

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # Allow assert in tests only
```

For architecture boundary enforcement in Python, add a custom pre-commit hook:

```bash
#!/usr/bin/env bash
# .git/hooks/pre-commit (or pre-commit config)
# Prevent business logic from leaking into routers

if git diff --cached --name-only | grep -q "api/routers/"; then
    if git diff --cached -- "api/routers/" | grep -qE "^\\+.*\\.query\(|^\\+.*session\."; then
        echo "ERROR: DB calls detected in api/routers/. Move to api/repositories/."
        echo "See docs/agent-loops/harness-engineering-research.md Pattern 2."
        exit 1
    fi
fi
```

---

## Pattern 3: Post-Edit Hook (Claude Code)

The most important structural change. Runs after every file edit. Silent on
success (no wasted context). Exits 2 with full output on failure, which
re-engages the agent automatically.

```bash
#!/usr/bin/env bash
# .claude/hooks/post-edit.sh
# Silent success. Verbose failure. Exit 2 re-engages Claude.

set -euo pipefail
CHANGED=$(git diff --name-only HEAD 2>/dev/null || true)

run_check() {
    local label="$1"
    shift
    OUTPUT=$("$@" 2>&1)
    if [ $? -ne 0 ]; then
        echo "=== HARNESS FAILURE: $label ===" >&2
        echo "$OUTPUT" >&2
        echo "Fix the above before continuing." >&2
        exit 2
    fi
    # Success = silence
}

# Backend checks
if echo "$CHANGED" | grep -q "^Python/\|^backend/"; then
    run_check "Python types"  uv run mypy . --no-error-summary
    run_check "Python lint"   uv run ruff check .
    run_check "Python tests"  uv run pytest -x --tb=short -q
fi

# Frontend checks
if echo "$CHANGED" | grep -qE "^JavaScript/|^frontend/"; then
    run_check "TypeScript" npm --prefix JavaScript/portfolio-dashboard run typecheck
    run_check "ESLint"     npm --prefix JavaScript/portfolio-dashboard run lint
fi
```

Wire it in `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": ".claude/hooks/post-edit.sh" }]
      }
    ]
  }
}
```

---

## Pattern 4: spec.md as Desired State

Before giving an agent a non-trivial task, write the spec first. The agent's
job is to reconcile actual codebase state against this spec until all
checkboxes pass. This is the Kubernetes controller pattern applied to code.

```markdown
# spec.md — [Feature Name]

## Goal
One sentence: what this feature does and why.

## Acceptance Criteria (all must pass before done)
- [ ] `uv run pytest tests/feature/ -v` exits 0
- [ ] `npm run typecheck` exits 0
- [ ] `uv run ruff check .` exits 0
- [ ] [Specific behavior A works as described]
- [ ] [Specific behavior B works as described]
- [ ] No private data in any committed file

## Architectural Constraints
- [Layer boundary rules that apply]
- [Specific files that must/must not be touched]

## Out of Scope (do not implement)
- [Thing A]
- [Thing B]

## Stop Conditions
- If any acceptance criterion cannot be met without scope expansion: STOP and report
- Do not modify [specific critical files] — add new files instead
```

Agent instruction when handing off a spec:
> "Read spec.md. Reconcile the codebase against it. Do not mark done until
> all checkboxes pass. If you hit a stop condition, report instead of expanding."

---

## Pattern 5: ARCHITECTURE.md

The map agents use to understand what goes where. Without it, they make
plausible-but-wrong architectural decisions at machine speed.

```markdown
# ARCHITECTURE.md

## Layer Diagram

```
Request → api/routers/ → api/services/ → api/repositories/ → Database
                    ↓
              api/models/  (shared types, no logic)
```

## Rules (enforced by CI)
1. Routers call services only — no business logic, no DB calls
2. Services call repositories only — no direct SQL, no HTTP calls
3. Repositories own all DB access — no business logic
4. Models are pure data types — no methods, no imports from other layers

## Key Files
- `api/main.py` — FastAPI app init, middleware, CORS only
- `api/routers/` — HTTP interface: parse request, call service, return response
- `api/services/` — Business logic: validation, orchestration, computation
- `api/repositories/` — Data access: all SQLAlchemy/pandas reads and writes
- `api/models/` — Pydantic models and TypedDicts

## What Goes Where (common mistakes)
| Code | Wrong location | Right location |
|------|---------------|----------------|
| Date parsing logic | `routers/` | `services/` |
| CSV reading | `services/` | `repositories/` |
| HTTP status codes | `services/` | `routers/` |
| Business rules | `main.py` | `services/` |

## Dependency Direction (never reverse these)
routers → services → repositories → models
```

---

## Pattern 6: Anti-Entropy Loop (Automated Friday Cleanup)

OpenAI automated their manual Friday cleanup into a scheduled agent loop.
The open-source equivalent is `desloppify`:

```bash
# Install
pip install "desloppify[full]"

# One-time scan
desloppify scan --path .

# Continuous loop until quality threshold met
while desloppify status --json | python3 -c "import sys,json; sys.exit(0 if json.load(sys.stdin)['score']>=95 else 1)"; do
    :
done

# Fix next priority issue (agent runs this, implements fix, calls resolve)
desloppify next
# [agent implements the fix]
desloppify resolve

# CI gate
desloppify scan --path . --profile ci
```

For a custom version without the dependency: a nightly GitHub Actions workflow
that runs your linter + tests, opens a PR for each class of violation found,
and assigns it to the team. The PR body is the lint output — LLM-readable.

---

## Pattern 7: The Minimal Control Loop (Python Implementation)

For building a custom agent loop from scratch:

```python
# agent_loop.py — minimal observe/reconcile loop
import subprocess
from anthropic import Anthropic

client = Anthropic()

def run_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return output optimized for LLM consumption."""
    if tool_name == "bash":
        result = subprocess.run(
            tool_input["command"], shell=True,
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            # Verbose on failure — this re-engages the agent
            return f"ERROR (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
        # Silent on success — don't waste context
        return result.stdout[-2000:] if result.stdout else "OK"
    raise ValueError(f"Unknown tool: {tool_name}")

def run_agent(task: str, max_iterations: int = 20) -> str:
    """Run agent loop until natural completion or max iterations."""
    messages = [{"role": "user", "content": task}]
    tools = [{
        "name": "bash",
        "description": "Run a shell command",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"]
        }
    }]

    for iteration in range(max_iterations):
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=8096,
            tools=tools,
            messages=messages
        )

        # Add assistant response to history
        messages.append({"role": "assistant", "content": response.content})

        # Natural completion
        if response.stop_reason == "end_turn":
            return next(b.text for b in response.content if hasattr(b, "text"))

        # Execute tool calls and feed results back
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })

        messages.append({"role": "user", "content": tool_results})

        # Loop detection (same command 3 times in a row)
        recent_commands = [
            b.input.get("command")
            for m in messages[-6:]
            for b in (m.get("content") if isinstance(m["content"], list) else [])
            if hasattr(b, "type") and b.type == "tool_use"
        ]
        if len(recent_commands) >= 3 and len(set(recent_commands[-3:])) == 1:
            messages.append({
                "role": "user",
                "content": "You appear stuck in a loop. Try a completely different approach."
            })

    return "Max iterations reached."

if __name__ == "__main__":
    result = run_agent(
        "Run the test suite, fix any failures, run again until clean. "
        "Report what you fixed."
    )
    print(result)
```

---

## Quick-Start Checklist

When setting up a new repo or onboarding an existing one to harness engineering:

**Week 1 — Make the harness legible:**
- [ ] `AGENTS.md` exists at repo root (10–20 lines max initially)
- [ ] `ARCHITECTURE.md` exists with layer diagram and what-goes-where table
- [ ] Tests run headlessly with a single command
- [ ] All linter rules are `error`, not `warn`
- [ ] Agent can `git clone` and run tests without asking questions

**Week 1-2 — Instrument the feedback loop:**
- [ ] `.claude/hooks/post-edit.sh` runs silently on success, exits 2 on failure
- [ ] Hook covers: type checking + linting + fast tests for changed files
- [ ] Hook output is LLM-readable (instructions, not blame)

**Week 2 — Encode your first anti-patterns:**
- [ ] 3 most common agent mistakes encoded as lint rules with fix instructions
- [ ] Each rule added to AGENTS.md with a one-line note on why

**Month 2+ — Graduate to loops:**
- [ ] `spec.md` discipline for non-trivial features
- [ ] Architecture boundary enforcement in CI (not just lint)
- [ ] Scheduled anti-entropy scan (cron or GitHub Actions)
- [ ] Self-improving harness: nightly agent updates AGENTS.md from session logs
