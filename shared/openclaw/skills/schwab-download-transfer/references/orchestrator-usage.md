# Schwab orchestrator usage

## Purpose

Use `scripts/schwab_orchestrator.py` as the top-level operator command for Schwab exports. It ties together:

- browser export automation
- download collection
- log updates
- optional master CSV maintenance

## What it does

Depending on the task, it will:

1. inspect existing log state implicitly
2. derive the next incremental date range from `next_download_start`
3. run the Playwright export helper
4. collect downloaded files from the Downloads directory
5. update the corresponding `download-log.json`
6. optionally append the new CSVs into Monoclaw master files

## Important limits

- It still depends on a valid authenticated Schwab browser session.
- The browser automation uses best-effort selectors and may need repair when Schwab changes its UI.
- Realized Gain/Loss still requires a human-supplied `--last-closed-date` after export, unless a future parser is added for deriving it directly from the details CSV.

## Privacy rule

Assume every Schwab brokerage download is private.

- Use a private base directory.
- Move files out of `~/Downloads` into the private Schwab tree as soon as practical.
- Do not copy or mirror these files into public repo locations, public datasets, demo fixtures, or any path intended for sharing.

## Examples

### Positions only

```bash
python3 scripts/schwab_orchestrator.py positions \
  --base-dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage \
  --downloads-dir ~/Downloads \
  --user-data-dir ~/.cache/monoclaw-schwab \
  --headed
```

### Realized Gain/Loss incremental run

```bash
python3 scripts/schwab_orchestrator.py rgl \
  --base-dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage \
  --downloads-dir ~/Downloads \
  --user-data-dir ~/.cache/monoclaw-schwab \
  --headed \
  --last-closed-date 2026-03-18 \
  --update-masters
```

### Transactions incremental run

```bash
python3 scripts/schwab_orchestrator.py transactions \
  --base-dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage \
  --downloads-dir ~/Downloads \
  --user-data-dir ~/.cache/monoclaw-schwab \
  --headed \
  --update-masters
```

### First run bootstrap for transactions

```bash
python3 scripts/schwab_orchestrator.py transactions \
  --base-dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage \
  --downloads-dir ~/Downloads \
  --user-data-dir ~/.cache/monoclaw-schwab \
  --headed \
  --first-transactions-from 2022-02-22
```

### Dry run

```bash
python3 scripts/schwab_orchestrator.py all \
  --base-dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage \
  --downloads-dir ~/Downloads \
  --user-data-dir ~/.cache/monoclaw-schwab \
  --headed \
  --last-closed-date 2026-03-18 \
  --update-masters \
  --dry-run
```

## Suggested future upgrades

- parse `last_closed_date` automatically from the RGL details CSV
- add stronger file matching keyed to exact Schwab filename families
- add a run manifest so every session records which files were exported and processed
- add better waiting/selector strategies after one or two live Schwab validation runs
