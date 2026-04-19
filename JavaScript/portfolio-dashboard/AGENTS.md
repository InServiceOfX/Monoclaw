# Portfolio Dashboard — Agent Instructions

## Repo Location

- **Frontend:** `Monoclaw/JavaScript/portfolio-dashboard/`
- **Backend:** `Monoclaw/Python/finance/`
- **Data:** `~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/` (NEVER in this repo)

## Tech Stack

### Frontend
- **Framework:** React 19 + TypeScript
- **Build:** Vite 8
- **UI Library:** Mantine 9 (Core + Charts + Dates + Hooks)
- **Charts:** Mantine Charts (wraps Recharts 3)
- **State/Data:** TanStack React Query v5
- **Routing:** react-router-dom v7 (currently unused — tabs, not routes)
- **Theme:** Dark mode, Indigo primary color

### Backend
- **Framework:** FastAPI
- **Server:** uvicorn
- **Prices:** yfinance
- **Data processing:** pandas (transitive via yfinance), numpy
- **Earnings parsing:** yfinance/Yahoo, with lxml available for HTML-backed calendars
- **Python version:** ≥3.11
- **Package manager:** uv (reads `pyproject.toml`)

## How to Run

```bash
# Backend (Terminal 1)
cd Monoclaw/Python/finance
uv run uvicorn api.main:app --host 127.0.0.1 --port 8765

# Frontend (Terminal 2)
cd Monoclaw/JavaScript/portfolio-dashboard
npm install  # if needed
npm run dev
# → http://localhost:5173
```

## Code Structure

### Frontend (`src/`)
```
src/
├── main.tsx          # Entry point: MantineProvider (dark theme), React Query
├── App.tsx           # AppShell with tab navigation (Overview, Positions, Balances, Transactions, RGL, Context, Monte Carlo)
├── api.ts            # API client: all fetch calls + TypeScript interfaces
├── fmt.ts            # Formatting utilities: usd(), pct(), num(), glColor()
├── index.css         # Minimal global styles
└── pages/
    ├── Overview.tsx   # Stat cards + donut chart (top 10) + timeseries area chart
    ├── Positions.tsx  # Sortable/filterable positions table
    ├── Balances.tsx   # Account balance snapshots and allocation breakdown
    ├── Transactions.tsx # Filterable transactions table (date, symbol, action)
    ├── RGL.tsx        # Realized G/L summary cards + monthly bar chart + cumulative chart + table
    ├── Insights.tsx   # Local portfolio context, concentration, tax, and earnings watch
    └── MonteCarlo.tsx # Portfolio and watchlist Monte Carlo analysis
```

### Backend (`api/`)
```
Python/finance/api/
├── __init__.py
├── main.py           # FastAPI app: all endpoints, CORS, data reading
├── monte_carlo.py    # Shared Monte Carlo simulation engine for API and CLI use
├── schwab_parser.py  # CSV parsing for positions, transactions, RGL (handles Schwab quirks)
└── price_fetcher.py  # Yahoo Finance price lookup with 60s cache + symbol mapping
```

## Key Patterns

### API Client (`api.ts`)
- Base URL from `VITE_API_BASE` env var or defaults to `http://localhost:8765`
- All interfaces are typed: `Position`, `PortfolioSummary`, `Transaction`, `RGLSummaryRow`, `HistorySnapshot`, `PortfolioContext`, `EarningsEvent`, `MonteCarloResponse`
- React Query handles caching, refetching (60s interval for positions/summary)

### CSV Parsing (`schwab_parser.py`)
- **`_read_raw(path, skip_meta)`**: Core reader. `skip_meta=True` skips line 1 (Schwab metadata header) and blank lines. Auto-pads short rows.
- **`parse_positions_csv`**: Extracts snapshot date from metadata, returns `(date, headers, rows)`
- **`parse_transactions_csv`**: No metadata line (direct CSV headers)
- **`parse_rgl_csv`**: Auto-detects whether to skip metadata (checks if first cell is "Symbol")

### Price Fetcher (`price_fetcher.py`)
- Symbol mapping: `BRK/B` → `BRK-B`, `--` → `None` (cash)
- Batch fetches via `yf.Tickers()`
- 60-second in-memory cache per symbol
- Returns `{current_price, day_change, day_change_pct, stale}`

## Development Guidelines

1. **NEVER hardcode financial data** — not even for testing. Use the real CSV files.
2. **NEVER commit CSVs or financial data** to the repo.
3. **localhost only** — no remote access, no cloud deployment.
4. **Don't commit to main/master** — use feature branches (`feat/`, `fix/`).
5. **Test with real data** but never include real data in commits.

## What Needs Work (Priority Order)

### High Priority
1. **Price fetch timeout** — First load fetches ~130 symbols from Yahoo Finance, takes 30-90s. Consider:
   - Fetching prices in parallel batches
   - Showing positions immediately with CSV prices, then updating with live prices
   - Adding a loading indicator to the frontend
2. **Earnings provider quality** — yfinance/Yahoo coverage can be delayed or missing. Consider Alpha Vantage, Nasdaq, or a cached local snapshot behind an optional API key.
3. **Monte Carlo calibration** — Current simulation is historical-return based. Consider adding benchmark comparison, volatility regime selection, and persisted recent runs.

### Medium Priority
4. **Add a refresh button** — currently relies on 60s auto-refresh. Manual refresh would be nice.
5. **Search/sort for RGL table** — Positions and Transactions have filters; RGL only has date range.
6. **Better loading states for slow endpoints** — Context, earnings, and Monte Carlo depend on external market data.

### Nice to Have
7. **PostgreSQL backend** — current CSV reads work fine at ~25K rows but may need DB for larger datasets or faster queries. See `PLANS-schwab-portfolio.md` Task 1 discussion.
8. **Historical portfolio reconstruction** — `PLANS-schwab-portfolio.md` Task 3b. Replay transactions to build true historical portfolio value (vs current hack of current holdings × historical prices).
9. **Buy/Sell/Hold signals** — `PLANS-schwab-portfolio.md` Task 3c.

## Debugging Tips

- **Backend not starting?** Check that port 8765 isn't already in use: `lsof -i :8765`
- **Frontend shows empty?** Check browser console for API errors. Backend must be running first.
- **Stale prices everywhere?** Yahoo Finance may be rate-limiting. Wait 60s and reload.
- **CSV parsing errors?** Schwab changed column names around April 2026 (`Security Type` → `Asset Type`). The parser handles both.
- **Server killed?** `yfinance` can consume significant memory when fetching many symbols. If macOS kills the process, reduce the number of holdings or add pagination.

## Branching

All work must go on feature branches. Examples:
```
feat/balances-page
feat/price-fetch-parallel  
fix/date-filter-format
```

Ernest reviews and merges to master.
