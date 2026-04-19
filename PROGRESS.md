# Monoclaw — Project Progress

**Last Updated:** 2026-04-19

---

## Active Work Areas

### 1. Schwab Portfolio Dashboard (Python + React)

**Status:** Functional, analytics polish in progress

**What's Working:**
- ✅ Data pipeline: All 4 data types downloading, logging, and mastered
- ✅ Backend API (FastAPI): All endpoints functional, localhost:8765
- ✅ Frontend (React + Mantine): 7 pages (Overview, Positions, Balances, Transactions, RGL, Context, Monte Carlo)
- ✅ Real-time prices via Yahoo Finance (yfinance)
- ✅ Timeseries chart with SPY benchmark
- ✅ RGL charts and aggregation
- ✅ Balances page and API
- ✅ Local context/risk/tax summary and earnings watch
- ✅ Monte Carlo risk bands for current holdings and optional watchlist symbols

**Current Data State (as of 2026-04-17):**
| Data Type | Master File | Rows | Last Update |
|-----------|-------------|------|-------------|
| Positions | master-positions.csv | 1,028 | 2026-04-17 |
| Transactions | Joint_Tenant_Transactions_MASTER.csv | 23,775 | 2026-04-17 (thru 04/17) |
| RGL Details | Joint_Tenant_GainLoss_Realized_Details_MASTER.csv | 11,514 | 2026-04-17 (thru 04/17) |
| RGL Summary | Joint_Tenant_GainLoss_Realized_Summary_MASTER.csv | 5,394 | 2026-04-17 (thru 04/17) |
| Balances | master-balances.csv | 1 | 2026-04-17 (first) |

**Known Limitations:**
1. First page load slow (30-90s) — fetches Yahoo prices for ~129 symbols
2. Earnings watch depends on yfinance/Yahoo coverage and can be incomplete
3. No historical portfolio reconstruction — timeseries uses current holdings × historical prices
4. Context tab is deterministic rule-based analysis, not an LLM-generated recommendation engine
5. Monte Carlo uses historical returns from yfinance and is risk context only, not a trading prediction engine

---

## Completed Tasks

### ✅ Data Layer — Complete
- All download logs updated and valid
- All master CSVs current through 2026-04-17
- Balances infrastructure created (new data type)
- Documentation written:
  - `Data/Private/finance/schwab-brokerage/README.md`
  - `Data/Private/finance/schwab-brokerage/*/AGENTS.md`

### ✅ Dashboard — MVP Complete
- Backend API serving all data endpoints
- Frontend with 7 working views
- CORS configured, localhost-only security
- Data pulled from CSV at runtime (no hardcoding)
- Documentation written:
  - `JavaScript/portfolio-dashboard/README.md`
  - `JavaScript/portfolio-dashboard/AGENTS.md`

### ✅ Dashboard Polish — 2026-04-18
- Fixed backend date filtering for Schwab `MM/DD/YYYY` and transaction `as of` dates
- Added ISO date fields for transactions and realized G/L rows
- Fixed RGL monthly/cumulative chart date labels
- Added `/balances` API and Balances tab
- Added `/portfolio/context` local risk/tax/top-holdings context
- Added `/portfolio/earnings` yfinance-backed earnings watch for top holdings
- Added `/portfolio/monte-carlo` correlated simulation endpoint for current holdings plus watchlist candidates
- Added Monte Carlo dashboard tab with portfolio fan chart, risk summary, and candidate metrics

---

## Next Tasks (Prioritized)

### High Priority — Quick Wins

**Task: Improve Earnings Provider**
- yfinance earnings coverage is useful but incomplete
- Add optional Alpha Vantage/Nasdaq provider behind an API key if higher coverage is needed
- Cache earnings snapshots locally to avoid repeated network calls

**Task: Monte Carlo Calibration**
- Current simulation uses yfinance historical adjusted closes and geometric return sampling
- Add configurable benchmark comparison, volatility regimes, and clearer scenario explanations
- Consider persisting recent simulation snapshots if repeated runs become slow

### Medium Priority — UX Improvements

**Task: Add Refresh Button**
- Currently only auto-refreshes every 60s
- Manual refresh button in header would be nice
- Should invalidate React Query cache

**Task: Parallel Price Fetching**
- Yahoo Finance fetching 129 symbols sequentially is slow
- Could batch into groups of 10-20 and fetch parallel
- Location: `Python/finance/api/price_fetcher.py`

**Task: Loading States for Slow Endpoints**
- Positions/summary take 30-90s first load
- Better loading UX (progress bar? streaming?)
- Consider SSR or progressive loading

### Lower Priority — Feature Work

**Task: True Historical Portfolio Reconstruction**
- Current timeseries: current holdings × historical prices
- Better: Replay transactions to build actual historical state
- Location: `Python/finance/api/main.py` — `/portfolio/timeseries`
- Harder but more accurate

**Task: Buy/Sell/Hold Signals**
- Based on unrealized G/L, portfolio weights, RGL tax implications
- Location: New endpoint + Overview tab addition

**Task: PostgreSQL Migration**
- CSV works fine now (~25K rows)
- PG would help if >500K rows or concurrent writes needed
- Current recommendation: Stay with CSV until scale demands PG

---

## Running the Dashboard

```bash
# Terminal 1 — Backend
cd Monoclaw/Python/finance
uv run uvicorn api.main:app --host 127.0.0.1 --port 8765

# Terminal 2 — Frontend
cd Monoclaw/JavaScript/portfolio-dashboard
npm run dev
# → http://localhost:5173
```

---

## Documentation Tree

For detailed instructions, see:

- `Data/Private/finance/schwab-brokerage/README.md` — Data layer overview
- `Data/Private/finance/schwab-brokerage/*/AGENTS.md` — Per-data-type guides
- `JavaScript/portfolio-dashboard/README.md` — User guide
- `JavaScript/portfolio-dashboard/AGENTS.md` — Developer guide
- `Python/finance/api/*.py` — Well-commented code
- `PLANS-schwab-portfolio.md` — Original task breakdown (may be outdated)

---

## Context for Next Agent

**If you're picking up this work:**

1. Read `JavaScript/portfolio-dashboard/AGENTS.md` for code structure
2. Read `Data/Private/finance/schwab-brokerage/README.md` for data docs
3. Check this file (PROGRESS.md) for current priorities
4. Start with the High Priority tasks above
5. Never commit to master — use feature branches (`feat/balances-page`, etc.)
6. Never hardcode financial data — all values come from CSV at runtime
7. Never expose data externally — localhost only

**Branch naming:** `feat/`, `fix/`, `chore/`
**Git rule:** Ernest merges to master. Never push directly to master.

---

## Notes

- Yahoo Finance rate limits can cause stale prices (orange badge in UI)
- Data is PRIVATE — never paste values in public channels or commits
- Schwab data location: `~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/`
- Account: Joint Tenant ...231 (XXXX-8231)
