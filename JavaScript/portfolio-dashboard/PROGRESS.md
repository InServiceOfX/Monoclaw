# Portfolio Dashboard — Progress

**Last Updated:** 2026-04-18
**Status:** MVP Complete, analytics polish phase

---

## What's Built

### Pages

| Page | Status | Features |
|------|--------|----------|
| **Overview** | ✅ Complete | Stat cards, top 10 donut chart, timeseries area chart w/ SPY benchmark |
| **Positions** | ✅ Complete | Sortable/filterable table, live prices, stale indicator |
| **Transactions** | ✅ Complete | Filterable by date/symbol/action, capped at 500 rows |
| **RGL** | ✅ Complete | Summary cards, monthly bar chart, cumulative chart, per-symbol table, ISO month labels |
| **Balances** | ✅ Complete | Snapshot cards, account/cash/securities trend, balances table |
| **Context** | ✅ First pass | Local risk flags, YTD realized tax snapshot, top holdings context, earnings watch |
| **Monte Carlo** | ✅ First pass | Portfolio percentile bands, current holdings simulation, optional watchlist candidate runs |

### Backend API

All endpoints functional in `Python/finance/api/main.py`:

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /portfolio/summary` | ✅ | Total value, cost basis, unrealized G/L, day change |
| `GET /positions/current` | ✅ | Current positions + Yahoo Finance prices |
| `GET /portfolio/history` | ✅ | All snapshots over time |
| `GET /portfolio/timeseries?period=` | ✅ | Current holdings × historical prices |
| `GET /transactions?...` | ✅ | Filtered transactions |
| `GET /rgl/summary?...` | ✅ | Realized G/L summary |
| `GET /rgl/details?...` | ✅ | Lot-level RGL |
| `GET /balances` | ✅ | Balance snapshots + numeric fields |
| `GET /portfolio/context` | ✅ | Local deterministic risk/tax/holdings context |
| `GET /portfolio/earnings?limit=` | ✅ | Earnings watch for top holdings via yfinance |
| `GET /portfolio/monte-carlo?...` | ✅ | Monte Carlo risk bands + watchlist candidate ranking |

---

## Known Issues

### Critical

**1. First Load Performance (30-90 seconds)**
- **What:** Fetching Yahoo Finance prices for ~129 symbols
- **Impact:** Users see empty page for a minute+
- **Fix Ideas:**
  - Parallel batch fetching (instead of single `yf.Tickers` call)
  - Stream positions first, then prices
  - Better loading UX (progress bar)
- **Location:** `Python/finance/api/price_fetcher.py` and `main.py`

**2. First-pass earnings coverage**
- **What:** Earnings watch uses yfinance/Yahoo; ETFs/funds have no earnings, and some symbols may be missing.
- **Impact:** Treat as a catalyst calendar, not a complete fundamentals database.
- **Fix Ideas:**
  - Add optional Alpha Vantage/Nasdaq-backed provider with an API key
  - Cache earnings snapshots to a local JSON file for faster reloads
  - Add sector/asset-type metadata to skip non-operating-company symbols earlier

**3. Monte Carlo model limitations**
- **What:** Current implementation uses recent historical log returns/correlation from Yahoo and geometric simulation.
- **Impact:** It can be useful for scenario shape but can understate regime changes, gap risk, and leveraged ETF path-dependence.
- **Fix Ideas:**
  - Add stress scenarios separate from Monte Carlo
  - Add local cached historical returns to avoid repeated Yahoo downloads
  - Add sector/factor/benchmark overlays
  - Add explicit leveraged ETF warnings

### Fixed 2026-04-18

- Backend date filtering now parses Schwab `MM/DD/YYYY`, `YYYY-MM-DD`, and transaction `as of` dates before comparing.
- Transactions receive `date_iso`; RGL summary/details receive `closed_date_iso`.
- RGL monthly and cumulative charts use ISO month keys so labels no longer truncate into fragments like `/2`.
- Added `/balances` endpoint and Balances tab.
- Added local Context tab with risk flags, YTD realized tax summary, top holdings context, and earnings watch.
- Added `lxml` to the finance Python dependencies because yfinance earnings-date parsing requires it.
- Earnings endpoint no longer caches transient per-symbol errors for 6 hours.
- Moved stray hardcoded Monte Carlo script into shared backend logic at `Python/finance/api/monte_carlo.py`.
- Replaced `schwab_portfolio_mc.py` with a CLI wrapper around the shared module.
- Added Monte Carlo dashboard tab and `/portfolio/monte-carlo` endpoint.
