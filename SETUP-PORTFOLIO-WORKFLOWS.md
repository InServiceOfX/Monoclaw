# Portfolio Workflows — Setup Guide

How to configure a new openclaw or Claude Code session to support the portfolio workflow triggers. Copy the relevant sections into your session's `TOOLS.md` (or equivalent instruction file), adapting paths to your local setup.

---

## Prerequisites

1. **Python environment**: `uv` installed, Python 3.10+
2. **Backend API** running at `localhost:8765`:
   ```bash
   cd <REPO>/Python/finance && uv run uvicorn api.main:app --port 8765
   ```
3. **Frontend** (optional, for dashboard):
   ```bash
   cd <REPO>/JavaScript/portfolio-dashboard && npm run dev
   ```
4. **Data directory** with Schwab brokerage exports organized as:
   ```
   <DATA_DIR>/schwab-brokerage/
   ├── positions/          # Point-in-time position snapshots
   ├── balances/           # Balance snapshots
   ├── realized-gain-loss/ # RGL summary + detail CSVs
   └── transactions/       # Transaction CSVs + JSONs
   ```
   Each subdirectory should have a `download-log.json` tracking `next_download_start`.

---

## Variables to Replace

Throughout this guide, replace these placeholders with your actual paths:

| Placeholder | Example |
|------------|---------|
| `<REPO>` | `~/.openclaw/workspace/repos/Monoclaw` |
| `<DATA_DIR>` | `~/.openclaw/workspace/Data/Private/finance` |
| `<WORKSPACE>` | `~/.openclaw/workspace` |

---

## Workflow 1: Schwab Download Date Ranges

**Trigger phrases:** "schwab download dates", "download ranges", "what dates to download"

Add to your TOOLS.md:

```markdown
### Quick: Get Download Date Ranges
When the user asks for Schwab download ranges, custom date ranges, or "what dates to download", run:
\```bash
cd <REPO>/Python/finance && uv run python schwab_download_ranges.py
\```
Works from any session. No external dependencies — stdlib only. Reads the download logs
and prints the custom date ranges for today.
```

**What it does:** Reads `download-log.json` in the transactions and realized-gain-loss directories, prints the `next_download_start → today` date ranges in MM/DD/YYYY format ready to paste into Schwab's custom date range fields.

---

## Workflow 2: Ingest Schwab Downloads

**Trigger phrases:** "ingest schwab", "process schwab downloads", "move schwab files"

Add to your TOOLS.md:

```markdown
### Quick: Ingest Schwab Downloads
When the user says "ingest schwab", "process schwab downloads", or similar — run this sequence:

**Step 1 — Move files from ~/Downloads to subdirectories:**
\```bash
DATA=<DATA_DIR>/schwab-brokerage
mv ~/Downloads/Joint\ Tenant-Positions-*.csv "$DATA/positions/" 2>/dev/null
mv ~/Downloads/*Balances*.CSV ~/Downloads/*Balances*.csv "$DATA/balances/" 2>/dev/null
mv ~/Downloads/*GainLoss_Realized*.csv "$DATA/realized-gain-loss/" 2>/dev/null
mv ~/Downloads/*Transactions*.csv ~/Downloads/*Transactions*.json "$DATA/transactions/" 2>/dev/null
\```
List any files that matched (or didn't) so the user can confirm.

**Step 2 — Rebuild all master CSVs** (idempotent, handles dedup):
\```bash
cd <REPO>/Python/finance
DATA=<DATA_DIR>/schwab-brokerage
uv run python schwab_positions_processor.py rebuild --dir "$DATA/positions"
uv run python schwab_balances_processor.py rebuild --dir "$DATA/balances"
uv run python schwab_rgl_processor.py rebuild --dir "$DATA/realized-gain-loss"
uv run python schwab_transactions_processor.py rebuild --dir "$DATA/transactions"
\```

**Step 3 — Update download logs:**
- Transactions: update `$DATA/transactions/download-log.json` — add history entry,
  set `last_data_point` and `next_download_start` to today
- Realized Gain/Loss: update `$DATA/realized-gain-loss/download-log.json` — add history
  entries, set `last_closed_date` to today and `next_download_start` to tomorrow

**Step 4 — Verify:**
\```bash
DATA=<DATA_DIR>/schwab-brokerage
wc -l "$DATA/positions/master-positions.csv"
wc -l "$DATA/balances/master-balances.csv"
wc -l "$DATA/realized-gain-loss/Joint_Tenant_GainLoss_Realized_Summary_MASTER.csv"
wc -l "$DATA/realized-gain-loss/Joint_Tenant_GainLoss_Realized_Details_MASTER.csv"
wc -l "$DATA/transactions/Joint_Tenant_Transactions_MASTER.csv"
\```
Confirm each was modified today and tail a few rows to verify new data appears.
```

**Download order** (always follow this sequence): Positions → Balances → RGL (Summary + Details) → Transactions (CSV + JSON)

---

## Workflow 3: Portfolio Outlook / Projections

**Trigger phrases:** "portfolio outlook", "portfolio projections", "projected portfolio value"

Add to your TOOLS.md:

```markdown
### Quick: Portfolio Outlook / Projections
When the user says "portfolio outlook", "portfolio projections", or similar — run:
\```bash
cd <REPO>/Python/finance && uv run python schwab_portfolio_outlook.py --out /tmp/outlook.json
\```
Takes ~90 seconds (Monte Carlo + DOI + earnings). Outputs JSON with:
- 3-month and 6-month projections (bear/median/bull percentiles)
- DOI deploy/hold/trim signals and index regime scores
- Upcoming earnings with historical win rates and classifications
- Winners and losers lists

Read `/tmp/outlook.json` and present a clear summary: total account projections at 3M
and 6M (include cash + equity), probability of gain, DOI regime signal, and upcoming
earnings catalysts.
```

**What it does:** Parses the latest positions snapshot, runs Monte Carlo (6-month, 5000 sims with Student-t fat tails and GARCH volatility), DOI (deploy/hold/trim scoring), and earnings impact analysis (top 40 holdings). Writes structured JSON.

---

## Workflow 4: Portfolio Moves / Swing Trade Actions

**Trigger phrases:** "portfolio moves", "what moves", "swing analysis", "what should I buy"

Add to your TOOLS.md:

```markdown
### Quick: Portfolio Moves / Swing Trade Actions
When the user says "portfolio moves", "what moves", "swing analysis", or similar — run:
\```bash
cd <REPO>/Python/finance && uv run python schwab_portfolio_outlook.py --out /tmp/outlook.json
\```
Then also fetch trade quality patterns (ensure the backend is running on localhost:8765):
\```bash
curl -s http://localhost:8765/grading/patterns
\```
Read both `/tmp/outlook.json` and the patterns response, then synthesize actionable
recommendations:
1. **Sells/trims** — positions with deep losses, leveraged decay, or low conviction
2. **Buys/adds** — based on Monte Carlo risk/reward scores, DOI deploy signals, earnings
   catalysts, and conviction scores
3. **Trade quality corrections** — check the patterns for symbols the user still holds
   where they historically sell too early (high MFE after sell). For those, recommend
   holding longer or using trailing stops instead of fixed targets. For symbols with
   good timing history, trust the existing sell signals.
4. **Bull case actions** — what specific trades would maximize upside
5. Use web search for current market conditions to contextualize the signals
6. Reference TRANSACTION-GRADING-SYSTEM.md and PLANS-schwab-portfolio.md for trading
   philosophy
```

**What it does:** Same data as outlook, but the agent synthesizes cross-system recommendations by combining Monte Carlo projections, DOI regime signals, earnings catalysts, and historical trade quality patterns into actionable buy/sell/trim decisions.

---

## Dashboard: Workflows Tab

The portfolio-dashboard frontend includes a **Workflows** tab that shows:
- Cards for each workflow with trigger phrases and timing hints
- Live data freshness panel (master CSV ages, row counts, color-coded recency badges)
- Download log next-download dates
- Last outlook run timestamp

This requires the backend `/workflows/status` endpoint to be running.

## Dashboard: Trade Quality Tab

The **Trade Quality** tab shows:
- Trader Score (median sell quality) and Avg Quality Score with explainer tooltips
- Per-sell grading table with MFE, max drawdown, near-peak detection
- Best/worst timed sells
- Per-symbol timing quality with edge ratings
- **Patterns & Corrections** section: rule-based analysis of recurring sell timing mistakes, cross-referenced with current holdings

This requires the backend `/grading/patterns` endpoint.

---

## Adapting to a New Machine

1. Clone the Monoclaw repo
2. Set up the Python environment: `cd <REPO>/Python/finance && uv venv --python 3.13 && uv pip install -r requirements.txt`
3. Organize your Schwab exports into `<DATA_DIR>/schwab-brokerage/` with the subdirectory structure above
4. Create `download-log.json` in the transactions and realized-gain-loss directories (see existing ones for format)
5. Copy the workflow sections above into your session's TOOLS.md, replacing `<REPO>` and `<DATA_DIR>` with your actual paths
6. Optionally create a `conviction.json` in your data directory mapping ticker symbols to conviction scores (0.0–1.0) for DOI weighting
7. Start the backend and frontend, then verify by navigating to the Workflows tab

---

## API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Backend health check |
| `/workflows/status` | GET | Master CSV freshness, download log dates, outlook info |
| `/grading/summary` | GET | Aggregate Trader Score and sell timing stats |
| `/grading/patterns` | GET | Rule-based sell timing patterns + corrections |
| `/grading/by-symbol` | GET | Per-symbol timing quality breakdown |
| `/grading/top-bottom` | GET | Best and worst timed sells |
| `/transactions/grading` | GET | Individual graded sell transactions |
| `/portfolio/monte-carlo` | GET | Monte Carlo simulation with position details |
| `/doi/snapshot` | GET | DOI deploy/hold/trim snapshot |
| `/portfolio/earnings-impact` | GET | Earnings impact analysis |
