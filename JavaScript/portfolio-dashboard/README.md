# Schwab Portfolio Dashboard

A local-only portfolio dashboard that displays real-time data from Schwab brokerage CSV exports. **No financial data is hardcoded — everything is read from local files at runtime.**

## Architecture

```
┌──────────────────────┐       ┌──────────────────────────────────┐
│  React Frontend      │       │  FastAPI Backend                 │
│  (Vite + Mantine)    │──────▶│  (Python, localhost:8765)        │
│  localhost:5173       │       │                                  │
│                      │       │  Reads from:                     │
│  • Overview          │       │  ~/.openclaw/workspace/Data/     │
│  • Positions         │       │    Private/finance/              │
│  • Balances          │       │    schwab-brokerage/             │
│  • Transactions      │       │                                  │
│  • Realized G/L      │       │                                  │
│  • Context           │       │                                  │
│  • Monte Carlo       │       │                                  │
│                      │       │  Fetches live prices from:       │
└──────────────────────┘       │  Yahoo Finance (yfinance)        │
                               └──────────────────────────────────┘
```

- **Frontend:** React 19 + TypeScript + Vite 8 + Mantine UI 9 + Recharts
- **Backend:** FastAPI + uvicorn + yfinance + pandas
- **Data:** CSV files in `~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/`
- **Binding:** Both services bind to `localhost` / `127.0.0.1` only. No external access.

## Quick Start

### 1. Start the Backend API

```bash
cd /Users/ernestyeung/.openclaw/workspace/repos/Monoclaw/Python/finance
uv run uvicorn api.main:app --host 127.0.0.1 --port 8765
```

The backend requires Python ≥3.11 and uses `uv` for dependency management. On first run, `uv` creates a venv and installs dependencies from `pyproject.toml`.

**Verify:** `curl http://127.0.0.1:8765/health`

### 2. Start the Frontend

```bash
cd /Users/ernestyeung/.openclaw/workspace/repos/Monoclaw/JavaScript/portfolio-dashboard
npm install   # only needed first time or after changes
npm run dev
```

**Open:** `http://localhost:5173`

### Both Together (one terminal each)

```bash
# Terminal 1 — Backend
cd /Users/ernestyeung/.openclaw/workspace/repos/Monoclaw/Python/finance
uv run uvicorn api.main:app --host 127.0.0.1 --port 8765

# Terminal 2 — Frontend
cd /Users/ernestyeung/.openclaw/workspace/repos/Monoclaw/JavaScript/portfolio-dashboard
npm run dev
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHWAB_BASE_DIR` | `~/.openclaw/workspace/Data/Private/finance/schwab-brokerage` | Path to data directory |
| `VITE_API_BASE` | `http://localhost:8765` | Backend API URL (frontend) |

## Dashboard Pages

### Overview
- **Stat cards:** Total portfolio value, unrealized G/L ($ and %), day change, position count
- **Top 10 Holdings:** Donut chart + legend table with symbol, value, % of portfolio
- **Performance Chart:** Current holdings × historical prices (via yfinance) with SPY benchmark overlay
- Period selector: 1M / 3M / 6M / 1Y / 2Y

### Positions
- Sortable table of all current holdings
- Columns: Symbol, Name, Qty, Price, Market Value, Cost Basis, Unrealized G/L ($), Unrealized G/L (%), Day %, % of Account
- Filter by symbol or name
- Stale prices marked with orange badge
- Auto-refreshes every 60 seconds

### Transactions
- Searchable/filterable transaction history from master CSV
- Filter by date range, symbol, action type
- Capped at 500 rows in view (use filters to narrow)
- Date filters use backend-normalized dates so Schwab `MM/DD/YYYY` and `as of` entries compare correctly

### Balances
- Latest account value, day change, cash, and securities cards
- Account/cash/securities trend chart as snapshots accumulate
- Balance snapshot table with available cash, settled funds, and withdrawable cash

### Realized G/L
- Summary cards: Total, Long-Term, Short-Term gains/losses
- Monthly bar chart (gain vs loss stacked)
- Cumulative G/L area chart
- Per-symbol aggregation table
- Filter by date range
- Chart month labels use normalized ISO dates

### Context
- Local deterministic risk flags from current holdings and realized G/L data
- YTD realized tax snapshot with short-term, long-term, and wash-sale counts
- Top holdings context with weights, unrealized gains/losses, ratings, and asset type
- Earnings watch for top holdings via yfinance/Yahoo. ETFs/funds are marked not applicable.

### Monte Carlo
- Portfolio percentile bands for current holdings read from local Schwab CSVs
- Watchlist input for symbols you are considering but do not currently hold
- Standalone candidate table with expected return, downside band, volatility, gain probability, and risk/reward score
- Uses historical Yahoo log returns and correlation; this is scenario/risk context, not a trading recommendation

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check + base_dir path |
| `/positions/current` | GET | Latest positions snapshot + live Yahoo prices |
| `/portfolio/summary` | GET | Aggregated portfolio totals |
| `/portfolio/history` | GET | All position snapshots over time |
| `/portfolio/timeseries?period=` | GET | Current holdings × historical prices (1m/3m/6m/1y/2y) |
| `/transactions?from_date=&to_date=&symbol=&action=` | GET | Filtered transactions |
| `/rgl/summary?from_date=&to_date=` | GET | Realized G/L summary rows |
| `/rgl/details?symbol=&from_date=&to_date=` | GET | Realized G/L lot-level details |
| `/balances` | GET | Balance snapshots with parsed numeric fields |
| `/portfolio/context` | GET | Local risk/tax/top-holdings context |
| `/portfolio/earnings?limit=` | GET | Earnings watch for top holdings via yfinance |
| `/portfolio/monte-carlo?symbols=&days=&simulations=&period=&max_positions=` | GET | Monte Carlo risk bands for current holdings plus optional watchlist symbols |

## Data Source

The backend reads from CSV master files in the data directory. See `~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/README.md` for full data documentation.

**Key files used:**
- `positions/*.csv` — individual snapshots (latest is used for current view)
- `positions/master-positions.csv` — all snapshots combined
- `transactions/Joint_Tenant_Transactions_MASTER.csv` — deduplicated transaction history
- `realized-gain-loss/Joint_Tenant_GainLoss_Realized_Summary_MASTER.csv`
- `realized-gain-loss/Joint_Tenant_GainLoss_Realized_Details_MASTER.csv`
- `balances/master-balances.csv` — balance snapshots

## Performance Notes

- **First load of /positions/current or /portfolio/summary:** Slow (~30-90s) because yfinance fetches prices for ~130 symbols. Subsequent calls use a 60-second cache.
- **Timeseries endpoint:** Also slow on first call (downloads historical data from Yahoo). Cached per session.
- **Earnings endpoint:** Uses yfinance/Yahoo for top holdings and caches results in memory for 6 hours.
- **Monte Carlo endpoint:** Downloads public history for up to `max_positions` holdings plus watchlist symbols, then runs local numpy simulations. Larger runs can take several seconds.
- All other endpoints (transactions, RGL) are fast — pure CSV reads.

## Security

- **localhost only** — both frontend and backend bind to 127.0.0.1
- **CORS restricted** — backend only allows requests from local Vite dev ports
- **No hardcoded data** — all financial values come from CSV files at runtime
- **Repo is safe to push** — no account numbers, balances, or position data in source code
- **Data dir is gitignored** — never commit CSV files

## Known Limitations

1. **Timeseries is approximate** — uses current holdings × historical prices, not actual historical portfolio value (positions you've sold are excluded)
2. **Earnings coverage is incomplete** — yfinance/Yahoo can miss symbols or provide delayed/missing estimates
3. **No authentication** — anyone on localhost can access the API
4. **Yahoo Finance rate limits** — if you reload rapidly, yfinance may throttle or return stale data
5. **Context tab is rule-based** — it is a local summary and risk flagger, not investment advice
6. **Monte Carlo is model risk** — it assumes recent return/correlation behavior is informative and can understate tail events
