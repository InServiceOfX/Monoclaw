"""Earnings impact analysis for portfolio positions.

Analyzes how each position historically reacts to earnings reports by
measuring price changes at multiple horizons (1, 5, 15, 30 trading days)
after each earnings date. Uses this historical pattern to estimate the
probability and magnitude of post-earnings moves for upcoming reports.

## Data source
All data comes from yfinance (Yahoo Finance):
  - Earnings dates + EPS estimates + reported EPS + surprise % via
    yf.Ticker.get_earnings_dates()
  - Historical daily prices via yf.Ticker.history()

## Statistical approach

For each symbol, we collect all past earnings events where we have both
the surprise % and enough subsequent price history. We then compute:

1. POST-EARNINGS RETURNS at 1, 5, 15, 30 trading days after the report.
   These are simple percentage returns: (P_t / P_0 - 1) * 100.

2. HISTORICAL STATISTICS across all past earnings:
   - Mean and median post-earnings return at each horizon
   - Win rate (% of times the stock went up)
   - Worst and best moves
   - Standard deviation of moves (volatility of the earnings reaction)

3. EARNINGS PLAY CLASSIFICATION based on historical patterns:
   - "strong_buy":  win rate >= 70% AND mean 30d return > 3%
   - "buy":         win rate >= 60% AND mean 30d return > 1%
   - "avoid":       win rate < 40% OR mean 30d return < -3%
   - "neutral":     everything else
   This is NOT a prediction — it's a summary of how the stock has
   historically behaved around earnings. Past performance does not
   guarantee future results, but it provides useful base rates.

4. UPCOMING EARNINGS FLAG:
   If the next earnings date is within 30 days, the position is flagged
   so the user can decide whether to hold through, add, or trim.

## Future improvements (see EARNINGS_IMPACT_PLAN.md)
- Bayesian model incorporating surprise magnitude + sector + macro regime
- Implied vol crush analysis (compare pre/post earnings IV)
- Correlation with market conditions (bull vs bear earnings reactions)
"""
from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# How many past earnings events to fetch per symbol. yfinance returns both
# future (upcoming) and past earnings. 40 gives us ~10 years of quarterly
# earnings for most stocks.
EARNINGS_HISTORY_LIMIT = 40

# Horizons (in trading days) at which we measure post-earnings price impact.
# 1d = immediate reaction, 5d = first week, 15d = two weeks, 30d = one month.
HORIZONS = [1, 5, 15, 30]

# Price history period to download. Must be long enough to cover the oldest
# earnings event we analyze plus the longest horizon.
PRICE_HISTORY_PERIOD = "10y"

# Minimum number of past earnings events required to compute statistics.
# Below this, the sample is too small for reliable win rates.
MIN_EARNINGS_EVENTS = 4


def _yahoo_symbol(sym: str) -> str:
    """Convert common symbol formats to Yahoo Finance tickers.
    e.g., BRK/B -> BRK-B
    """
    return sym.replace("/", "-")


def _compute_post_earnings_moves(
    earnings_dates,
    price_history,
    horizons: list[int] = HORIZONS,
) -> list[dict]:
    """For each past earnings date, compute the percentage price change
    at each horizon after the report.

    Parameters
    ----------
    earnings_dates : pd.DataFrame
        From yf.Ticker.get_earnings_dates(). Must have DatetimeIndex and
        columns 'EPS Estimate', 'Reported EPS', 'Surprise(%)'.
    price_history : pd.DataFrame
        From yf.Ticker.history(). Must have DatetimeIndex and 'Close' column.
    horizons : list[int]
        Trading days after earnings to measure (e.g., [1, 5, 15, 30]).

    Returns
    -------
    list[dict]
        One dict per earnings event with date, surprise, and price changes.
    """
    import pandas as pd
    import numpy as np

    today = datetime.date.today()
    past_earnings = earnings_dates[earnings_dates.index.date < today]

    events = []
    for dt in past_earnings.index:
        date = dt.date()
        row = past_earnings.loc[dt]

        surprise = row.get("Surprise(%)")
        if pd.isna(surprise):
            surprise = None
        else:
            surprise = float(surprise)

        eps_estimate = row.get("EPS Estimate")
        if pd.isna(eps_estimate):
            eps_estimate = None
        else:
            eps_estimate = float(eps_estimate)

        reported_eps = row.get("Reported EPS")
        if pd.isna(reported_eps):
            reported_eps = None
        else:
            reported_eps = float(reported_eps)

        # Find the earnings date (or next trading day) in price history.
        mask = price_history.index.date >= date
        if mask.sum() < max(horizons) + 1:
            continue

        future_prices = price_history.index[mask]
        p0 = float(price_history.loc[future_prices[0], "Close"])
        if p0 <= 0:
            continue

        moves = {}
        for h in horizons:
            if h < len(future_prices):
                p_h = float(price_history.loc[future_prices[h], "Close"])
                moves[f"{h}d_pct"] = round((p_h / p0 - 1) * 100, 2)
            else:
                moves[f"{h}d_pct"] = None

        events.append({
            "date": date.isoformat(),
            "eps_estimate": eps_estimate,
            "reported_eps": reported_eps,
            "surprise_pct": round(surprise, 2) if surprise is not None else None,
            **moves,
        })

    return events


def _compute_earnings_stats(events: list[dict], horizons: list[int] = HORIZONS) -> dict:
    """Compute aggregate statistics across all past earnings events.

    Returns win rates, mean/median moves, and worst/best at each horizon.
    """
    import numpy as np

    if len(events) < MIN_EARNINGS_EVENTS:
        return {"sufficient_data": False, "event_count": len(events)}

    stats: dict = {"sufficient_data": True, "event_count": len(events)}

    for h in horizons:
        key = f"{h}d_pct"
        values = [e[key] for e in events if e.get(key) is not None]
        if not values:
            stats[f"{h}d"] = None
            continue
        arr = np.array(values)
        stats[f"{h}d"] = {
            "mean": round(float(arr.mean()), 2),
            "median": round(float(np.median(arr)), 2),
            "std": round(float(arr.std()), 2),
            "win_rate_pct": round(float((arr > 0).mean() * 100), 1),
            "best": round(float(arr.max()), 2),
            "worst": round(float(arr.min()), 2),
            "count": len(values),
        }

    # Beat rate: how often does the company beat EPS estimates?
    surprises = [e["surprise_pct"] for e in events if e.get("surprise_pct") is not None]
    if surprises:
        sarr = np.array(surprises)
        stats["beat_rate_pct"] = round(float((sarr > 0).mean() * 100), 1)
        stats["avg_surprise_pct"] = round(float(sarr.mean()), 2)
    else:
        stats["beat_rate_pct"] = None
        stats["avg_surprise_pct"] = None

    return stats


def _classify_earnings_play(stats: dict) -> dict:
    """Classify whether this stock is historically good to hold through earnings.

    Returns a signal label and reasoning.
    """
    if not stats.get("sufficient_data"):
        return {"signal": "insufficient_data", "reason": "Too few earnings events to analyze"}

    d30 = stats.get("30d")
    d1 = stats.get("1d")
    if d30 is None or d1 is None:
        return {"signal": "insufficient_data", "reason": "Missing horizon data"}

    win_30d = d30["win_rate_pct"]
    mean_30d = d30["mean"]
    win_1d = d1["win_rate_pct"]
    std_1d = d1["std"]

    # Strong buy: historically almost always goes up after earnings
    if win_30d >= 70 and mean_30d > 3:
        return {
            "signal": "strong_buy",
            "reason": f"30d win rate {win_30d:.0f}%, avg gain {mean_30d:+.1f}%",
        }

    # Buy: more often up than down with positive drift
    if win_30d >= 60 and mean_30d > 1:
        return {
            "signal": "buy",
            "reason": f"30d win rate {win_30d:.0f}%, avg gain {mean_30d:+.1f}%",
        }

    # Avoid: stock usually drops or is too volatile around earnings
    if win_30d < 40 or mean_30d < -3:
        return {
            "signal": "avoid",
            "reason": f"30d win rate {win_30d:.0f}%, avg return {mean_30d:+.1f}%",
        }

    # High volatility warning: even if win rate is ok, moves are wild
    if std_1d > 8:
        return {
            "signal": "volatile",
            "reason": f"1d std dev {std_1d:.1f}% — big swings either way",
        }

    return {
        "signal": "neutral",
        "reason": f"30d win rate {win_30d:.0f}%, avg return {mean_30d:+.1f}%",
    }


def analyze_earnings_impact(symbols: list[str], descriptions: dict[str, str] | None = None) -> dict:
    """Run earnings impact analysis for a list of symbols.

    Parameters
    ----------
    symbols : list[str]
        Ticker symbols to analyze.
    descriptions : dict[str, str] | None
        Optional mapping of symbol -> company description.

    Returns
    -------
    dict
        JSON-serializable result with per-symbol analysis and upcoming alerts.
    """
    import pandas as pd
    import yfinance as yf

    descriptions = descriptions or {}
    results = []
    upcoming_alerts = []
    today = datetime.date.today()

    for sym in symbols:
        entry: dict = {
            "symbol": sym,
            "description": descriptions.get(sym, ""),
            "status": "ok",
        }

        try:
            ticker = yf.Ticker(_yahoo_symbol(sym))

            # Fetch earnings dates (includes future upcoming + past reported).
            earnings_df = ticker.get_earnings_dates(limit=EARNINGS_HISTORY_LIMIT)
            if earnings_df is None or earnings_df.empty:
                entry["status"] = "no_earnings_data"
                results.append(entry)
                continue

            if not isinstance(earnings_df.index, pd.DatetimeIndex):
                earnings_df.index = pd.to_datetime(earnings_df.index, utc=True)

            # Check for upcoming earnings.
            future = earnings_df[earnings_df.index.date >= today]
            if not future.empty:
                next_date = future.index[0].date()
                entry["next_earnings_date"] = next_date.isoformat()
                days_until = (next_date - today).days
                entry["days_until_earnings"] = days_until

                # Get EPS estimate for upcoming report.
                next_row = future.iloc[0]
                eps_est = next_row.get("EPS Estimate")
                entry["next_eps_estimate"] = None if pd.isna(eps_est) else float(eps_est)

                if days_until <= 30:
                    upcoming_alerts.append({
                        "symbol": sym,
                        "description": descriptions.get(sym, ""),
                        "date": next_date.isoformat(),
                        "days_until": days_until,
                        "eps_estimate": entry["next_eps_estimate"],
                    })
            else:
                entry["next_earnings_date"] = None
                entry["days_until_earnings"] = None
                entry["next_eps_estimate"] = None

            # Fetch price history for computing post-earnings moves.
            price_hist = ticker.history(period=PRICE_HISTORY_PERIOD)
            if price_hist is None or price_hist.empty or "Close" not in price_hist.columns:
                entry["status"] = "no_price_history"
                results.append(entry)
                continue

            # Compute post-earnings price moves at each horizon.
            events = _compute_post_earnings_moves(earnings_df, price_hist)
            entry["events"] = events

            # Compute aggregate statistics.
            stats = _compute_earnings_stats(events)
            entry["stats"] = stats

            # Classify the earnings play.
            classification = _classify_earnings_play(stats)
            entry["classification"] = classification

        except Exception as exc:
            logger.warning("Earnings analysis failed for %s: %s", sym, exc)
            entry["status"] = "error"
            entry["error"] = str(exc)

        results.append(entry)

    # Sort: upcoming earnings soonest first, then by 30d win rate.
    results.sort(key=lambda r: (
        r.get("days_until_earnings") is not None,
        -(r.get("days_until_earnings") or 9999),
    ), reverse=True)

    upcoming_alerts.sort(key=lambda a: a["days_until"])

    return {
        "positions": results,
        "upcoming_alerts": upcoming_alerts,
        "horizons": HORIZONS,
        "note": (
            "Earnings impact analysis based on historical post-earnings price moves from Yahoo Finance. "
            "Past performance does not predict future results. Signals are base-rate summaries, not recommendations."
        ),
    }
