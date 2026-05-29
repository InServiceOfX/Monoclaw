"""Historical daily price data with caching for timing analysis.

Phase 1 foundation for Transaction Grading System.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore

from .price_fetcher import _yahoo_symbol

# In-memory cache: (symbol, start, end) -> (timestamp, DataFrame)
_history_cache: dict[tuple[str, str, str], tuple[float, pd.DataFrame]] = {}
_CACHE_TTL = 3600.0  # 1 hour


def get_daily_history(
    symbol: str,
    start: str | datetime,
    end: str | datetime | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Fetch daily OHLCV history for a symbol.

    Returns DataFrame with columns: Open, High, Low, Close, Adj Close, Volume
    Index is DatetimeIndex (trading days only).

    Uses yfinance under the hood with in-memory caching.
    """
    if yf is None:
        return pd.DataFrame()

    yahoo_sym = _yahoo_symbol(symbol)
    if yahoo_sym is None:
        return pd.DataFrame()

    if isinstance(start, datetime):
        start = start.strftime("%Y-%m-%d")
    if end is None:
        end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    elif isinstance(end, datetime):
        end = end.strftime("%Y-%m-%d")

    cache_key = (yahoo_sym, start, end)
    now = time.time()

    if not force_refresh and cache_key in _history_cache:
        ts, df = _history_cache[cache_key]
        if now - ts < _CACHE_TTL:
            return df

    try:
        df = yf.download(
            yahoo_sym,
            start=start,
            end=end,
            progress=False,
            auto_adjust=False,
        )
        if df.empty:
            empty = pd.DataFrame()
            _history_cache[cache_key] = (now, empty)
            return empty

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

        # Ensure consistent column names
        df = df.rename(columns={"Adj Close": "AdjClose"})
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        _history_cache[cache_key] = (now, df)
        return df
    except Exception:
        empty = pd.DataFrame()
        _history_cache[cache_key] = (now, empty)
        return empty


def compute_forward_mfe_and_drawdown(
    symbol: str,
    sell_date: str | datetime,
    window_days: int = 30,
) -> dict[str, float | None]:
    """Compute Maximum Favorable Excursion (MFE) and max drawdown after a sell date.

    MFE = highest % gain from sell price in the forward window
    MaxDrawdown = largest % drop from sell price in the forward window (negative number)

    Returns dict with keys: mfe_pct, max_drawdown_pct, days_to_peak, days_to_trough
    """
    if isinstance(sell_date, str):
        sell_date = pd.to_datetime(sell_date)

    start = sell_date.strftime("%Y-%m-%d")
    end = (sell_date + timedelta(days=window_days + 5)).strftime("%Y-%m-%d")

    df = get_daily_history(symbol, start, end)
    if df.empty or "Close" not in df.columns:
        return {"mfe_pct": None, "max_drawdown_pct": None, "days_to_peak": None, "days_to_trough": None}

    # Find first trading day on or after sell_date
    try:
        sell_price = df.loc[df.index >= sell_date, "Close"].iloc[0]
    except IndexError:
        return {"mfe_pct": None, "max_drawdown_pct": None, "days_to_peak": None, "days_to_trough": None}

    forward_prices = df.loc[df.index > sell_date, "Close"]
    if forward_prices.empty:
        return {"mfe_pct": None, "max_drawdown_pct": None, "days_to_peak": None, "days_to_trough": None}

    gains = (forward_prices - sell_price) / sell_price * 100
    mfe_pct = float(gains.max())
    max_dd_pct = float(gains.min())

    days_to_peak = int((gains.idxmax() - sell_date).days)
    days_to_trough = int((gains.idxmin() - sell_date).days)

    return {
        "mfe_pct": round(mfe_pct, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "days_to_peak": days_to_peak,
        "days_to_trough": days_to_trough,
    }


def detect_local_peak(
    symbol: str,
    date: str | datetime,
    window: int = 20,
    prominence_pct: float = 8.0,
) -> bool:
    """Return True if `date` is near a local price peak for the symbol.

    Uses a simple rolling max approach for Phase 1.
    """
    if isinstance(date, str):
        date = pd.to_datetime(date)

    start = (date - timedelta(days=window * 2)).strftime("%Y-%m-%d")
    end = (date + timedelta(days=5)).strftime("%Y-%m-%d")

    df = get_daily_history(symbol, start, end)
    if df.empty or len(df) < window:
        return False

    df["rolling_max"] = df["Close"].rolling(window=window, center=True).max()
    df["is_peak"] = df["Close"] >= df["rolling_max"] * (1 - prominence_pct / 100)

    # Check if any peak exists within ±3 trading days of the date
    nearby = df.loc[(df.index >= date - timedelta(days=3)) & (df.index <= date + timedelta(days=3))]
    return bool(nearby["is_peak"].any())


def calculate_sell_quality(
    symbol: str,
    sell_date: str | datetime,
    realized_gain_pct: float | None = None,
    window_days: int = 30,
) -> dict[str, float | None]:
    """Calculate quality score for a sell transaction.

    Returns dict with:
        - quality_score: composite score (-100 to +100)
        - mfe_pct, max_drawdown_pct
        - avoided_drop_score, missed_gain_score
        - is_near_local_peak: bool
    """
    try:
        parsed_sell_date = pd.to_datetime(str(sell_date).split(" as of ", 1)[0], errors="coerce")
        if pd.isna(parsed_sell_date):
            return {
                "quality_score": None,
                "mfe_pct": None,
                "max_drawdown_pct": None,
                "avoided_drop_score": None,
                "missed_gain_score": None,
                "is_near_local_peak": False,
                "is_provisional": False,
            }

        if parsed_sell_date.to_pydatetime() > datetime.now() - timedelta(days=3):
            return {
                "quality_score": 0.0,
                "mfe_pct": None,
                "max_drawdown_pct": None,
                "avoided_drop_score": 0.0,
                "missed_gain_score": 0.0,
                "is_near_local_peak": False,
                "is_provisional": True,
            }

        metrics = compute_forward_mfe_and_drawdown(symbol, sell_date, window_days)
        is_peak = detect_local_peak(symbol, sell_date, window=20, prominence_pct=8.0)

        mfe = metrics.get("mfe_pct") or 0.0
        max_dd = metrics.get("max_drawdown_pct") or 0.0

        avoided_drop = max(0.0, -max_dd) * 1.2
        missed_gain = max(0.0, mfe) * 0.9
        profit_component = (realized_gain_pct or 0.0) * 0.5
        vol_penalty = min(15.0, abs(mfe - max_dd) * 0.15)

        quality = avoided_drop - missed_gain + profit_component - vol_penalty
        quality = max(-100.0, min(100.0, quality))

        return {
            "quality_score": round(quality, 1),
            "mfe_pct": metrics.get("mfe_pct"),
            "max_drawdown_pct": metrics.get("max_drawdown_pct"),
            "avoided_drop_score": round(avoided_drop, 1),
            "missed_gain_score": round(missed_gain, 1),
            "is_near_local_peak": is_peak,
            "is_provisional": False,
        }
    except Exception:
        # Fail gracefully
        return {
            "quality_score": None,
            "mfe_pct": None,
            "max_drawdown_pct": None,
            "avoided_drop_score": None,
            "missed_gain_score": None,
            "is_near_local_peak": False,
            "is_provisional": False,
        }
