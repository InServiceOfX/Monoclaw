# AGENTS.md — Python/finance

## Scope

Local FastAPI backend and supporting scripts for the Schwab portfolio dashboard.

## Setup

```bash
cd Python/finance
uv sync
```

## Run

```bash
cd Python/finance
uv run uvicorn api.main:app --host 127.0.0.1 --port 8765
```

## Conventions

- Keep the API localhost-only.
- Reuse existing parsers and price-fetch helpers before adding new data access code.
- Prefer deterministic analytics over hardcoded account-specific assumptions.
- Match existing module style: dataclasses, type hints, `from __future__ import annotations`, module logger.

## Private Data Rules

- Private Schwab CSVs live outside the repo under `~/.openclaw/workspace/Data/Private/`.
- Never commit copied private CSV data, derived account values, screenshots, or logs.
- If a helper file must be seeded under the private data directory, verify it stays outside git.

## Do Not Commit

- `.venv/`, `__pycache__/`, generated CSVs, downloaded logs, local debug output.
- Anything under private data paths.

## Branching

- Work on feature/fix/chore branches only.
- Never commit or push to `master`/`main`.

## Completion

1. Run the relevant API check locally.
2. Update `PROGRESS.md`.
3. Review diffs for private data leakage before committing.
