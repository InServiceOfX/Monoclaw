# Recommendation Tracker

A lightweight closed-loop system to log AI-generated portfolio recommendations,
match them against actual Schwab transactions, and measure forward performance
against a benchmark.

## Why

We generate buy/sell/hold recommendations regularly (from Monte Carlo output,
qualitative analysis, earnings impact, etc.). Without a feedback loop we have
no idea whether they actually work. This tracker captures every recommendation
along with the metrics that justified it, then later checks: did the user act
on it, and did the position move in the predicted direction?

## Components

```
Python/finance/scripts/
├── log_recommendation.py     # Append a recommendation to the JSONL log
├── match_recommendations.py  # Match recs to Schwab buy/sell transactions
└── compute_performance.py    # Compute forward returns + alpha vs SPY
```

The scripts read/write under a configurable data root. By default they expect:

```
<data root>/
├── recommendations.jsonl     # Append-only log (one JSON per line)
├── snapshots/                # MC snapshots saved at time of recommendation
├── reports/                  # Generated match and performance reports
└── .price_cache.json         # yfinance cache (regenerable)
```

The Schwab transactions master CSV is read from a separate, private location.

The scripts default to a private data path; override with environment variables
or by editing the `REC_DIR` / `TXN_FILE` constants near the top of each script
to point at your own setup.

## Schema (recommendations.jsonl)

One JSON object per line. Required fields are minimal; the rest are best-effort.

```json
{
  "id": "rec_YYYYMMDD_HHMMSS_SYMBOL",
  "timestamp": "ISO-8601",
  "symbol": "TICKER",
  "action": "buy | add | hold | trim | sell",
  "conviction": "strong_buy | buy | hold | weak_hold | trim | sell",
  "source": {
    "agent": "<which AI agent or harness made this rec>",
    "model": "<provider/model id>",
    "method": "monte_carlo_backend | monte_carlo_script | qualitative | earnings_analysis | mixed",
    "mc_params": { "days": 90, "simulations": 5000, "period": "1y" }
  },
  "metrics": {
    "risk_reward_score": 2.41,
    "annual_return_pct": 68.0,
    "sharpe_like": 2.12,
    "probability_gain_pct": 87.0,
    "expected_return_pct": 28.5,
    "p05_pct": -14.0,
    "p50_pct": 27.0,
    "p95_pct": 92.0,
    "var_5": 312.0,
    "garch_vol": 0.026,
    "implied_vol_annual": 0.45
  },
  "position_context": {
    "current_market_value": 2480.00,
    "current_price": 248.00,
    "portfolio_weight_pct": 0.82,
    "suggested_action_size": "add 1 share",
    "suggested_price_target": 240.00
  },
  "rationale": "free-form short note",
  "mc_snapshot_file": "snapshots/mc_2026-04-27_044500.json"
}
```

### Conviction → R/R thresholds (initial mapping)

| Conviction   | Risk/Reward score |
| ------------ | ----------------- |
| `strong_buy` | > 2.0             |
| `buy`        | 1.0 – 2.0         |
| `hold`       | 0.3 – 1.0         |
| `weak_hold`  | 0.0 – 0.3         |
| `trim`       | -0.1 – 0.0        |
| `sell`       | < -0.1            |

These are starting values. Recalibrate against realized win rates once you have
a few months of data.

## Matching rules

`match_recommendations.py` walks each recommendation and looks for a Schwab
buy/sell transaction in the same symbol with an agreeing direction within a
configurable window (default 7 days):

| Window         | Attribution           |
| -------------- | --------------------- |
| Same day       | `followed`            |
| Within 3 days  | `partially_followed`  |
| 4–7 days       | `partially_followed`  |
| Opposite ≤ 3d  | `contrary`            |
| No match in 7d | `ignored`             |

Trades that exist with no matching recommendation in the window are tagged
`discretionary` (the user acted on their own).

## Performance computation

`compute_performance.py` for each recommendation:

1. Picks a reference price (in priority order):
   - matched trade execution price
   - `position_context.current_price` from the rec snapshot
   - yfinance lookup for the rec date
2. Pulls daily close prices for the symbol and SPY benchmark across the full
   range needed.
3. Computes forward return at each requested horizon (default 1 / 7 / 30 / 90
   days) and **alpha vs SPY** (`return_pct - spy_return_pct`).
4. Aggregates by `action`, `conviction`, and matched-vs-unmatched buckets:
   `n`, `avg_return_pct`, `median_return_pct`, `win_rate_pct`,
   `avg_alpha_pct`.

Prices are cached in `.price_cache.json` keyed by `symbol__start__end` to keep
re-runs cheap. Delete the file to force a refresh.

## Usage

From `Python/finance/`:

```bash
# Log a single recommendation
uv run python3 scripts/log_recommendation.py \
    --symbol MU --action buy --conviction strong_buy \
    --model "anthropic/claude-opus-4-7" --method monte_carlo_backend \
    --rr 10.45 --sharpe 3.15 --pgain 92.1 --ann-ret 184.6 \
    --rationale "Highest R/R in portfolio, Sharpe > 3"

# Or in Python
from scripts.log_recommendation import log_rec, log_batch_from_mc
log_rec(symbol="MU", action="buy", conviction="strong_buy", ...)

# Match recs to actual trades
uv run python3 scripts/match_recommendations.py

# Custom horizons
uv run python3 scripts/compute_performance.py --horizons 1,5,30,90
```

Output reports land in `<data root>/reports/` as
`match_<DATE>.json` and `performance_<DATE>.json`.

## Design notes

- **JSONL, not a database.** Append-only is friendly to multiple agents
  (OpenClaw, Claude Code, Codex) writing concurrently and to git diffing
  if you ever want to track the file.
- **Tolerate ambiguity.** Some user trades will have no matching rec and
  some recs will be ignored. Don't force false attribution.
- **Snapshots are ground truth.** The full MC JSON saved to `snapshots/` lets
  you re-derive any `metrics` field after the fact. Delete the entry in the
  log if you mis-fired; never edit it in place.
- **Time zones matter.** Always store ISO-8601 timestamps with offset.
  Markets are open ~6:30 AM – 1:00 PM PT; running performance scripts before
  market close on a given day will under-report that day.

## Suggested next work

- API endpoints in `api/main.py` to log/list/report recommendations.
- A Recommendations tab in the dashboard frontend.
- Recalibration: once 6+ months of data exist, re-fit the conviction → R/R
  thresholds against realized win rates.
- Hypothetical "what if I'd followed every rec" portfolio simulation.
- Detect rec drift: when does conviction flip for the same symbol?
