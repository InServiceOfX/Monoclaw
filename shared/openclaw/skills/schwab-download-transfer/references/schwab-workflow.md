# Schwab workflow reference

## Purpose

Teach another OpenClaw how to perform Schwab brokerage downloads safely and incrementally.

## Sensitivity and storage policy

- Treat all Schwab data as private financial data.
- Assume any file downloaded from a Schwab brokerage account is private by default.
- Store exports only under a private finance directory.
- Never redirect these files into a public/shared data area.
- Never use Schwab exports as sample data in a public repo, demo folder, or public dataset location.
- Transfer workflow knowledge, scripts, and log structure freely inside a trusted repo, but do not copy real brokerage exports into the skill.

## Canonical directory layout

```text
<private-base>/finance/schwab-brokerage/
  positions/
  realized-gain-loss/
    download-log.json
  transactions/
    download-log.json
```

## Browser method

Use an authenticated browser session via browser relay / attached browser automation. This workflow assumes a logged-in Schwab session in Chrome or an equivalent attached browser.

## Export order

Always perform downloads in this sequence:

1. Positions
2. Realized Gain/Loss
3. Transactions

This order reduces confusion and matches the established operational habit.

## Positions workflow

### Page

`https://client.schwab.com/app/accounts/positions/#/`

### Procedure

1. Open Positions.
2. Click **Export**.
3. Confirm the export dialog.
4. Download the CSV.
5. Move the downloaded file into `positions/`.
6. Keep Schwab's original filename.

### Notes

- Positions is a snapshot, not an incremental feed.
- No dedup logic is required.
- Each exported file is a point-in-time record.

## Realized Gain/Loss workflow

### Page

`https://client.schwab.com/app/accounts/RGL/#/RGL`

### Pre-check

Read `realized-gain-loss/download-log.json` before exporting.

Interpretation:

- If no prior log or no `next_download_start` exists, use a broad historical range.
- Otherwise use:
  - From = `next_download_start`
  - To = today

### Procedure

1. Open Realized Gain/Loss.
2. Set the custom date range.
3. Click **Export**.
4. Export **Summary Only**.
5. Re-open **Export**.
6. Export **Details Only**.
7. Move both CSV files into `realized-gain-loss/`.
8. Update `download-log.json`.

### Log semantics

The log should preserve enough information to determine the next incremental range:

- exported filenames
- export time
- covered date range
- `last_closed_date`
- `next_download_start` = day after `last_closed_date`

### UI quirks

If browser automation is flaky:

- radio button ids may matter:
  - `summary-card-radio`
  - `details-card-radio`
- date inputs may use:
  - `fromdaterange-datepicker-input`
  - `todaterange-datepicker-input`

Keep these as hints, not guarantees.

## Transactions workflow

### Page

`https://client.schwab.com/app/accounts/history/#/`

### Pre-check

Read `transactions/download-log.json` before exporting.

Interpretation:

- If no prior log or no `next_download_start` exists, export full history / All.
- Otherwise use:
  - From = `next_download_start`
  - To = today

### Procedure

1. Open Transaction History.
2. Set the date range.
3. Click **Export**.
4. Export CSV.
5. Re-open or switch format.
6. Export JSON.
7. Move both files into `transactions/`.
8. Update `download-log.json`.

### Log semantics

Track at least:

- exported filenames
- export time
- covered date range
- `last_data_point`
- `next_download_start`

## Suggested log shape

The exact JSON can vary, but another agent should be able to recover these fields without ambiguity:

```json
{
  "history": [
    {
      "filename": "example.csv",
      "format": "csv",
      "downloaded_at": "2026-03-20T16:00:00-07:00",
      "date_range": {
        "from": "2026-03-01",
        "to": "2026-03-20"
      }
    }
  ],
  "last_data_point": "2026-03-20",
  "next_download_start": "2026-03-21"
}
```

For realized gain/loss, replace `last_data_point` with `last_closed_date`.

## Teaching another agent

When handing this off, make sure the receiving OpenClaw understands:

- where files go
- which logs control incrementality
- which exports are snapshots vs incremental
- the exact export order
- that filenames should usually remain unchanged
- that private financial data should not be copied into public locations

## Extension ideas

After the base workflow is documented and stable, an agent may add:

- browser automation helpers
- a log updater script
- file movers/organizers
- validation that confirms all expected files for a run were captured

Do that after the manual procedure is clear, not before.