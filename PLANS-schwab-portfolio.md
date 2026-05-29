# Schwab Portfolio: Task Plans for AI Agents

**Created:** 2026-04-16  
**Last Updated:** 2026-05-28  
**Author:** Grimlock (OpenClaw agent) for Ernest Yeung
**Purpose:** Break down portfolio dashboard, data layer, and analytics into discrete tasks that can be delegated to Claude Code, Codex, or other OpenClaw agents.

> **Related Document:** See `TRANSACTION-GRADING-SYSTEM.md` for the detailed design of the transaction timing / opportunity cost scoring system (added 2026-05-28).

---

## Data Inventory (what we have)

All data lives under:
```
~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/
```

### Positions (`positions/`)
- 9 snapshot CSVs (2026-02-03 through 2026-04-16) + 1 `master-positions.csv` (769 rows)
- Schema: `SnapshotDate, Symbol, Description, Qty, Price, Cost/Share, Price Chng $, Price Chng %, Mkt Val, Day Chng $, Day Chng %, Cost Basis, Gain $, Gain %, Ratings, Reinvest?, Reinvest Capital Gains?, % of Acct, Security Type`
- Each raw CSV has a header line like `"Positions for account Joint Tenant ...231 as of 03:14 PM ET, 2026/04/16"` before the actual column headers
- Master CSV adds `SnapshotDate` column, strips the account header

### Transactions (`transactions/`)
- 6 incremental CSVs + 6 JSONs + 1 `Joint_Tenant_Transactions_MASTER.csv` (22,427 rows)
- CSV schema: `Date, Action, Symbol, Description, Quantity, Price, Fees & Comm, Amount`
- JSON schema: structured with `FromDate`, `ToDate`, and transaction array
- Master CSV adds `source_file` column
- Date range covered: 2022-02-22 → 2026-04-15
- `download-log.json` tracks: `last_data_point = 2026-04-15`, `next_download_start = 2026-04-16`

### Realized Gain/Loss (`realized-gain-loss/`)
- 23 CSVs total (Summary + Details pairs), no master file yet
- Summary schema: `Symbol, Name, Closed Date, Quantity, Closing Price, Cost Basis Method, Proceeds, Cost Basis, Total Gain/Loss ($), Total Gain/Loss (%), LT Gain/Loss ($), LT Gain/Loss (%), ST Gain/Loss ($), ST Gain/Loss (%), Wash Sale?, Disallowed Loss, ...`
- Details schema: `Symbol, Name, Closed Date, Opened Date, Quantity, Proceeds/Share, Cost/Share, Proceeds, Cost Basis, Gain/Loss ($), Gain/Loss (%), LT Gain/Loss, ST Gain/Loss, Term, Unadjusted Cost Basis, Wash Sale?, Disallowed Loss, ...`
- Both have a descriptive header line before column headers
- `download-log.json` tracks: `last_closed_date = 2026-04-15`, `next_download_start = 2026-04-16`

### Key data constraints
- All data is **private** — never hardcode values, never expose to external services
- CSVs have quirky Schwab formatting: dollar signs in values (`$260.88`), percentage signs, quoted fields
- Positions are point-in-time snapshots (not incremental)
- Transactions and RGL are incremental with overlap tracking via download logs

---

## Task 1: Data Layer — Master Files & Storage Decision

### Decision: CSV Master Files vs PostgreSQL

**Recommendation: Start with CSV masters, add PostgreSQL later if needed.**

Rationale:
- Current data volume is small (~22K transaction rows, ~800 position snapshots, maybe ~5K RGL lots)
- CSV masters already exist for positions and transactions
- No concurrent writers; single-user local machine
- PostgreSQL adds operational complexity (install, migrations, backups) for marginal benefit at this scale
- CSV is directly readable by pandas, Rust polars, or any dashboard without a DB driver
- **Upgrade trigger:** If data exceeds ~500K rows, or if we need complex joins/aggregations in real-time, or if multiple agents need concurrent write access — then migrate to PostgreSQL

### Task 1a: Create RGL Master CSV (Codex/Claude Code)

**Priority:** High — this is the missing piece
**Language:** Python
**Location:** `Monoclaw/Python/finance/`
**Branch:** `feat/rgl-master-csv`

Instructions:
1. Read all `*GainLoss_Realized_Details_*.csv` files from `realized-gain-loss/`
2. Parse Schwab's quirky CSV format (skip descriptive header line, handle `$` and `%` in values)
3. Add `source_file` column (like the transactions master does)
4. Deduplicate on `(Symbol, Closed Date, Opened Date, Quantity, Proceeds, Cost Basis)` — overlapping date ranges in incremental downloads will produce duplicates
5. Sort by `Closed Date` descending, then `Symbol`
6. Write to `realized-gain-loss/Joint_Tenant_RGL_Details_MASTER.csv`
7. Also create a summary master from `*GainLoss_Realized_*.csv` (non-Details files): `realized-gain-loss/Joint_Tenant_RGL_Summary_MASTER.csv`
8. Support `append` mode: given a new Details+Summary pair, append only new rows to the master

**Testing:** Run against the 23 existing CSVs; verify no duplicate rows; verify row count makes sense vs source files.

### Task 1b: Update Transactions Master with Latest Download (Codex/Claude Code)

**Priority:** High
**Language:** Python
**Location:** `Monoclaw/Python/finance/`
**Branch:** `feat/update-tx-master`

Instructions:
1. The existing `Joint_Tenant_Transactions_MASTER.csv` covers through 2026-03-02
2. Append the new `Joint_Tenant_XXX231_Transactions_20260416-151633.csv` (covers 03/03–04/15)
3. Deduplicate on `(Date, Action, Symbol, Quantity, Price, Amount)` to handle any overlap
4. Preserve `source_file` column

### Task 1c: Update Positions Master with Latest Snapshot (Codex/Claude Code)

**Priority:** High
**Language:** Python
**Location:** `Monoclaw/Python/finance/`
**Branch:** `feat/update-pos-master`

Instructions:
1. The existing `master-positions.csv` covers through 2026-03-02
2. Parse `Joint Tenant-Positions-2026-04-16-151421.csv`, extract snapshot date from header, add as `SnapshotDate` column
3. Append to master
4. No dedup needed — each snapshot is a distinct point in time

---

## Task 2: Real-Time Price Lookup Module

**Priority:** High — needed for dashboard and portfolio valuation
**Language:** Python (or Rust if performance matters later)
**Location:** `Monoclaw/Python/finance/price_lookup.py`
**Branch:** `feat/price-lookup`

### Task 2a: Build Price Fetcher (Codex/Claude Code)

Instructions:
1. Use `yfinance` (free, no API key) to fetch real-time/delayed quotes
2. Given a list of ticker symbols, return current price, day change, day change %
3. Handle edge cases:
   - Cash/money market entries (symbol like `--` or blank in positions CSV) — skip or return 1.0
   - Schwab-specific symbols that may differ from Yahoo (e.g., BRK/B vs BRK-B)
   - Symbols that Yahoo doesn't recognize — return None with a warning
4. Expose as a simple function: `get_prices(symbols: list[str]) -> dict[str, PriceInfo]`
5. Cache results for 60 seconds to avoid hammering Yahoo
6. Add a CLI mode: `python price_lookup.py AAPL MSFT TSLA` prints a table

**Testing:** Run against the ~50–80 unique symbols from the latest positions CSV.

### Task 2b: Symbol Mapping Table (Codex/Claude Code or OpenClaw agent)

Instructions:
1. Extract all unique symbols from positions master
2. For each, verify it resolves on Yahoo Finance
3. Create a `symbol_map.json` mapping any Schwab-specific tickers to Yahoo tickers
4. This file lives in `Monoclaw/Python/finance/` (NOT in the private data dir)

---

## Task 3: Portfolio Reconstruction Engine

**Priority:** Medium — needed for historical analysis and buy/sell/hold signals
**Language:** Python first, Rust later if performance matters
**Location:** `Monoclaw/Python/finance/portfolio_engine.py`
**Branch:** `feat/portfolio-engine`

### Task 3a: Current Portfolio Valuation (Codex/Claude Code)

Instructions:
1. Read the latest positions CSV (most recent snapshot)
2. Parse all holdings: symbol, quantity, cost basis per share, total cost basis
3. Fetch real-time prices (using Task 2's price fetcher)
4. Compute for each position:
   - Current market value = quantity × current price
   - Unrealized gain/loss = market value − cost basis
   - Unrealized gain/loss %
   - Weight in portfolio (% of total)
5. Compute portfolio totals:
   - Total market value
   - Total cost basis
   - Total unrealized gain/loss
   - Day change (total)
6. Output as structured data (JSON or dataclass), not just printed text

### Task 3b: Historical Portfolio Reconstruction (Codex/Claude Code)

This is the harder, more interesting task.

Instructions:
1. Starting from the oldest positions snapshot OR from the transactions history, reconstruct daily portfolio state
2. Approach A (simpler): Use the 9 position snapshots as anchor points, interpolate between them using transactions (buys add shares, sells remove shares)
3. Approach B (from-scratch): Start from earliest transaction, replay all buys/sells to build position history
4. For each reconstructed day:
   - Holdings: which symbols, how many shares
   - Would need historical prices (yfinance supports `history()` for this)
   - Portfolio value on that day
5. Map realized gains/losses from the RGL data to the corresponding sell transactions
6. Output: a time series of `(date, total_value, positions_dict, realized_gl_cumulative)`

**Note:** Approach B is more accurate but much harder. Start with Approach A. Historical price data from yfinance is free but rate-limited.

### Task 3c: Buy/Sell/Hold Signal Generation (Codex/Claude Code — stretch goal)

Instructions:
1. Using current positions + realized gains history, compute basic signals:
   - **Winners:** positions with highest unrealized gain % → consider taking profits
   - **Losers:** positions with deepest unrealized loss % → consider tax-loss harvesting
   - **Overweight:** positions > X% of portfolio → consider trimming
   - **Underweight:** positions < Y% but with strong ratings → consider adding
   - **Wash sale risk:** positions sold at a loss in last 30 days that were rebought
2. These are informational signals, NOT trading recommendations
3. Factor in the `Ratings` column from Schwab (A/B/C/D/F) as a secondary signal
4. Output as a ranked list with reasoning

---

## Task 4: Interactive Dashboard

**Priority:** High
**Language:** TypeScript/React (Vite) or Python (Streamlit/Dash)
**Location:** `Monoclaw/JavaScript/portfolio-dashboard/` (if React) or `Monoclaw/Python/portfolio-dashboard/` (if Streamlit)
**Branch:** `feat/portfolio-dashboard`

### Framework Decision

| Option | Pros | Cons |
|--------|------|------|
| **React + Vite + Recharts** | Rich interactivity, Ernest has JS experience (mission-control exists), customizable | More setup, needs API backend |
| **Streamlit** | Fast to build, pandas-native, single file can work | Less customizable, feels like a prototype |
| **Dash (Plotly)** | Good charts, Python-native, production-ready | Steeper learning curve than Streamlit |

**Recommendation:** React + Vite if Ernest wants something polished and maintainable. Streamlit if we want something fast and functional within a day.

### Task 4a: Dashboard Backend / Data API (Codex/Claude Code)

Instructions:
1. Create a local-only API (FastAPI or Express) that reads from the master CSVs
2. Endpoints:
   - `GET /positions/current` — latest position snapshot + real-time prices
   - `GET /positions/history` — all position snapshots over time
   - `GET /transactions?from=&to=` — filtered transaction history
   - `GET /rgl?from=&to=` — filtered realized gains/losses
   - `GET /portfolio/summary` — total value, total gain/loss, day change
   - `GET /portfolio/timeseries` — historical portfolio value (from Task 3b)
3. **CRITICAL: No hardcoded data.** All data read from local CSV files at runtime.
4. **CRITICAL: Bind to localhost only.** This is private financial data.
5. CORS allowed only for localhost dev server

### Task 4b: Dashboard Frontend (Codex/Claude Code)

Instructions:
1. Pages/views:
   - **Overview:** Total portfolio value, day change, total gain/loss (big numbers at top). Portfolio allocation pie/donut chart. Portfolio value over time line chart.
   - **Positions:** Table of all current holdings with: symbol, name, qty, current price, market value, cost basis, unrealized G/L ($), unrealized G/L (%), day change, % of portfolio. Sortable columns. Color-code gains green, losses red.
   - **Transactions:** Searchable/filterable table. Filter by date range, symbol, action type (Buy/Sell/Dividend/etc).
   - **Realized Gains/Losses:** Summary view (per-symbol totals) + detail drill-down (lot-level). Filter by date range. Show ST vs LT breakdown.
   - **Signals:** Buy/sell/hold indicators from Task 3c (if implemented). Overweight/underweight alerts. Wash sale warnings.
2. **CRITICAL: No hardcoded financial data anywhere in the frontend code.**
   - All data fetched from the local API
   - No account numbers, balances, or position data in source code
   - The repo should be safe to push to GitHub without leaking anything
3. Charts library: Recharts (if React) or Plotly
4. Responsive but desktop-primary (Ernest uses a MacBook Pro)

### Task 4c: Dashboard Deployment Config (Codex/Claude Code)

Instructions:
1. Single `docker-compose.yml` or simple `npm run dev` + `python run api` setup
2. Local only — no cloud deployment
3. Document startup in a README

---

## Task 5: Ongoing Data Pipeline (OpenClaw Agent — not coding)

### Task 5a: Automate Regular Downloads (OpenClaw main agent)

Instructions:
1. Set up a cron job or heartbeat task to remind Ernest to download Schwab data weekly
2. Or: revisit the Playwright automation once Schwab's bot detection is understood better
3. Or: investigate granting `openclaw-gateway` Screen Recording + Accessibility permissions so Peekaboo can drive Chrome directly
4. After each download, auto-run the master CSV updaters

### Task 5b: Grant Peekaboo Permissions to openclaw-gateway (OpenClaw agent)

Instructions:
1. The blocker today was that `openclaw-gateway` (the Node.js daemon) doesn't have Screen Recording or Accessibility permissions
2. Research: can we add `/opt/homebrew/bin/node` or the specific `openclaw-gateway` binary to macOS TCC programmatically?
3. Or: run peekaboo through a helper that does have permissions
4. This would unlock fully automated Schwab downloads without manual browser interaction

### Task 5c: Fix Schwab Download Logs Fragility (Codex/Claude Code)

Instructions:
1. Both `download-log.json` files had broken JSON (duplicate array brackets) — likely from manual editing or a buggy append
2. Add a JSON validation step to `update_download_log.py` — after writing, re-read and validate
3. Add a `--repair` flag to `inspect_download_log.py` that can fix common structural issues
4. Location: `Monoclaw/shared/openclaw/skills/schwab-download-transfer/scripts/`
5. Branch: `fix/download-log-validation`

---

## Task Dependency Graph

```
Task 1a (RGL Master) ─────────┐
Task 1b (Update TX Master) ───┤
Task 1c (Update Pos Master) ──┼──> Task 3a (Current Valuation) ──> Task 4b (Dashboard)
Task 2a (Price Fetcher) ──────┘         │
Task 2b (Symbol Map) ─────────────────┘ │
                                         ├──> Task 3c (Signals)
Task 3b (Historical Reconstruction) ────┘

Task 4a (Backend API) ──> Task 4b (Dashboard Frontend) ──> Task 4c (Deploy Config)

Task 5a,5b,5c are independent maintenance tasks
```

## Suggested Execution Order

1. **First batch (parallel, Codex/Claude Code):**
   - Task 1a: RGL Master CSV
   - Task 1b: Update Transactions Master
   - Task 1c: Update Positions Master
   - Task 2a: Price Fetcher
   - Task 5c: Fix download log validation

2. **Second batch (after batch 1):**
   - Task 2b: Symbol Mapping
   - Task 3a: Current Portfolio Valuation
   - Task 4a: Dashboard Backend API

3. **Third batch (after batch 2):**
   - Task 4b: Dashboard Frontend
   - Task 3b: Historical Reconstruction (can run in parallel)

4. **Stretch / ongoing:**
   - Task 3c: Buy/Sell/Hold Signals
   - Task 4c: Deployment Config
   - Task 5a: Automated Downloads
   - Task 5b: Peekaboo Permissions

---

## Balances Data — Master CSV Workflow

### What is a Schwab balance snapshot?

Each time you export balances from Schwab, you get a key-value CSV like:

```
"Balances for account XXXX-8231 as of 04/22/2026 02:50 AM ET"

Account Value,"$299,625.78"
Day Change,"-$1,727.77"
Day Change %,"-0.57%"
Cash & Cash Investments,"$135,458.02"
Market Value,"$164,167.76"
...
Funds Available,
To Trade,
Cash & Cash Investments,"$134,694.44"
Settled Funds,"$134,694.44"
To Withdraw,
Cash & Cash Investments,"$134,694.44"
```

This is **not a columnar CSV** — each file is one snapshot in key-value format.
Files are named `XXXX8231_Balances_YYYYMMDD-HHMMSS.CSV`.

### master-balances.csv

The processor converts all individual snapshots into a single columnar master:

```
SnapshotDate, SnapshotTime, Account Value, Day Change, Day Change %,
Cash & Cash Investments, Market Value (Securities), Available to Trade (Cash),
Settled Funds, Available to Withdraw, source_file
```

**Location:** `Data/Private/finance/schwab-brokerage/balances/master-balances.csv`
**Script:** `Monoclaw/Python/finance/schwab_balances_processor.py`

### Parser notes for AI agents

- The header line `"Balances for account ... as of MM/DD/YYYY HH:MM AM/PM ET"` contains the snapshot date/time.
- `"Cash & Cash Investments"` appears **three times** in the raw file:
  - First occurrence (top-level summary) → `Cash & Cash Investments` column — **first occurrence wins**
  - Under `To Trade,` subsection → `Available to Trade (Cash)` column
  - Under `To Withdraw,` subsection → `Available to Withdraw` column
- Use **section tracking**: when a line has a key but no value, it sets the current subsection name.
- `"Market Value"` appears twice; first occurrence = securities market value → `Market Value (Securities)`.
- Strip `$`, `%`, and commas before parsing numbers; negative values are like `"-$1,727.77"`.
- Deduplication key = `SnapshotDate`. If multiple files share a date, the lexicographically latest filename wins (filename encodes the download timestamp).

### Commands

**Rebuild master from scratch** (after moving new files to the balances dir):

```bash
python Python/finance/schwab_balances_processor.py rebuild \
  --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/balances
```

**Append one new file** (faster, only processes the new snapshot):

```bash
python Python/finance/schwab_balances_processor.py append \
  --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/balances \
  --csv ~/Downloads/XXXX8231_Balances_20260430-183000.CSV
```

**Using the `.venv` at the Monoclaw repo root:**

```bash
/path/to/Monoclaw/.venv/bin/python Python/finance/schwab_balances_processor.py rebuild \
  --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/balances
```

### API priority

The `/balances` endpoint checks in this order:
1. `master-balances.csv` (preferred — fast, single read, columnar)
2. Individual `*.csv` / `*.CSV` files in the balances dir (fallback for machines that haven't run the processor yet)

Always run the processor after moving new balance files — this keeps the master current and makes the API faster.

### Download workflow (after downloading a new snapshot from Schwab)

1. Move the file from `~/Downloads/` to `Data/Private/finance/schwab-brokerage/balances/`
2. Run `append` (or `rebuild` if unsure):
   ```bash
   python Python/finance/schwab_balances_processor.py append \
     --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/balances \
     --csv ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/balances/XXXX8231_Balances_YYYYMMDD-HHMMSS.CSV
   ```
3. No API restart needed — the API re-reads the master on every request.

---

## Rules for All Coding Tasks

1. **Never commit to main/master.** Use feature branches. Ernest merges.
2. **Never hardcode private data.** All data read from `Data/Private/...` at runtime.
3. **Never expose data externally.** localhost-only servers. No cloud APIs.
4. **Handle Schwab CSV quirks:** `$` in values, `%` in values, quoted fields, descriptive header lines before column headers.
5. **All work in `Monoclaw/` repo** unless otherwise specified.
6. **Test with real data** but never commit real data to the repo.
