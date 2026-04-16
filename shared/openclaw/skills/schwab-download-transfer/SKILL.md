---
name: schwab-download-transfer
description: Transfer and apply procedural knowledge for downloading Schwab brokerage exports with OpenClaw. Use when an agent needs to automate, document, or hand off the Schwab download workflow, including browser-relay or Playwright-driven exports, incremental date-range selection, download-log interpretation, safe file placement under private finance directories, and packaging the workflow as reusable notes/scripts for another OpenClaw.
---

# Schwab Download Transfer

Capture and reuse the Schwab brokerage download workflow without leaking sensitive data. Prefer this skill when teaching another OpenClaw how to perform the downloads, inspect what still needs to be downloaded, or reconstruct the process in a new repo.

## Core rules

- Treat Schwab data as private financial data.
- Assume all data downloaded from any Schwab brokerage account is private by default.
- Keep all downloaded artifacts under a private finance directory, never a public/shared export location.
- Never place Schwab account downloads in any public directory, temporary public staging area, sample-data folder, or repo path intended for public sharing.
- Preserve Schwab's original filenames unless the user explicitly asks otherwise.
- Follow the export order exactly:
  1. Positions
  2. Realized Gain/Loss
  3. Transactions
- Use an authenticated browser session. Browser relay or a persistent Playwright profile is acceptable.
- Read the appropriate `download-log.json` before choosing an incremental date range.
- When handing the workflow to another agent, transfer procedure and helper code, not raw account data.

## Workflow

### 1. Gather the local operating context

Before writing or automating anything, confirm or record:

- private base directory for Schwab files
- browser/relay method used for authenticated export
- current log file paths
- expected export order
- whether this is a first download or an incremental download

If the exact local paths are already documented in workspace notes, reuse them instead of inventing new ones.

### 2. Teach the file layout first

Document the canonical folder structure clearly. The minimum useful structure is:

```text
<private-base>/
  positions/
  realized-gain-loss/
    download-log.json
  transactions/
    download-log.json
```

Explain the difference:

- `positions/`: point-in-time snapshots, no dedup logic required
- `realized-gain-loss/`: incremental exports using `last_closed_date` and `next_download_start`
- `transactions/`: incremental exports using `last_data_point` and `next_download_start`

### 3. Encode the procedural sequence

Teach the workflow in the same order the operator should execute it.

#### Positions

- Navigate to Schwab Positions.
- Export CSV.
- Move the downloaded file into `positions/`.
- Keep the original filename.
- Do not deduplicate; each file is a dated snapshot.

#### Realized Gain/Loss

- Read `realized-gain-loss/download-log.json` first.
- If no prior log exists, use a broad/full historical range.
- Otherwise set custom date range:
  - From = `next_download_start`
  - To = today
- Export twice:
  - Summary only
  - Details only
- Move both files into `realized-gain-loss/`.
- Update the log with exported filenames, covered range, and new `last_closed_date` / `next_download_start`.

#### Transactions

- Read `transactions/download-log.json` first.
- If no prior log exists, use full history / All.
- Otherwise set custom date range:
  - From = `next_download_start`
  - To = today
- Export both CSV and JSON.
- Move both files into `transactions/`.
- Update the log with exported filenames, covered range, and new `last_data_point` / `next_download_start`.

### 4. Separate stable knowledge from local secrets

Put reusable operating knowledge in the skill. Keep local account names, exact machine paths, relay quirks, and other environment-specific values in a local notes file or deployment config.

### 5. Use the bundled helpers

Use scripts for the deterministic parts agents repeatedly get wrong.

#### Inspect the current log state

```bash
python3 scripts/inspect_download_log.py /path/to/download-log.json
python3 scripts/inspect_download_log.py /path/to/download-log.json --kind transactions
python3 scripts/inspect_download_log.py /path/to/download-log.json --kind realized-gain-loss
```

#### Run browser-assisted export automation

This script is an operator-assisted Playwright skeleton. It expects an authenticated browser profile or manual login.

```bash
python3 scripts/schwab_export_playwright.py positions --user-data-dir ~/.cache/monoclaw-schwab --headed
python3 scripts/schwab_export_playwright.py rgl --user-data-dir ~/.cache/monoclaw-schwab --headed --from-date 03/01/2026 --to-date 03/20/2026
python3 scripts/schwab_export_playwright.py transactions --user-data-dir ~/.cache/monoclaw-schwab --headed --from-date 03/01/2026 --to-date 03/20/2026
```

#### Move exported files from Downloads into the private Schwab tree

```bash
python3 scripts/collect_downloads.py \
  --downloads ~/Downloads \
  --base-dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage
```

Use `--dry-run` first if you want a preview.

#### Update the incremental log after moving files

Transactions example:

```bash
python3 scripts/update_download_log.py \
  --log ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/transactions/download-log.json \
  --kind transactions \
  --from 2026-03-01 \
  --to 2026-03-20 \
  --file ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/transactions/Joint_Tenant_Transactions_2026-03-20.csv \
  --file ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/transactions/Joint_Tenant_Transactions_2026-03-20.json
```

Realized Gain/Loss example:

```bash
python3 scripts/update_download_log.py \
  --log ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/realized-gain-loss/download-log.json \
  --kind realized-gain-loss \
  --from 2026-03-01 \
  --to 2026-03-20 \
  --last-closed-date 2026-03-18 \
  --file ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/realized-gain-loss/Joint_Tenant_GainLoss_Realized_2026-03-20.csv \
  --file ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/realized-gain-loss/Joint_Tenant_GainLoss_Realized_Details_2026-03-20.csv
```

## Bundled resources

### `references/schwab-workflow.md`
Read this when you need the concrete Schwab procedure, export order, directory policy, or log semantics.

### `scripts/inspect_download_log.py`
Inspect a Schwab download log and print the next download state.

### `scripts/schwab_export_playwright.py`
Operator-assisted browser automation for authenticated export flows. Expect selector maintenance over time.

### `scripts/collect_downloads.py`
Move newly downloaded Schwab exports from a Downloads folder into canonical private destinations.

### `scripts/update_download_log.py`
Append download history and update `next_download_start` for transactions or realized gain/loss.

## Handoff pattern

When transferring this workflow into another repo or another OpenClaw instance:

1. Copy this skill folder.
2. Adapt any environment-specific paths in local notes, not in the core procedure.
3. Keep the sensitive-data warning intact.
4. Add repo-specific automation only after the baseline manual workflow is documented.
5. Keep browser selectors and export behavior close to the workflow reference so another agent can repair them.

## Output expectations

A good transfer artifact should give another OpenClaw enough information to:

- know where files belong
- know what to download next
- know the order of operations
- avoid duplicating incremental ranges unnecessarily
- avoid leaking private financial data
- extend the workflow with automation later
