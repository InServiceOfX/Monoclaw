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
        if now - ts < _CACHE_TTL and not df.empty:
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
            return pd.DataFrame()

        # Ensure consistent column names
        df = df.rename(columns={"Adj Close": "AdjClose"})
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        _history_cache[cache_key] = (now, df)
        return df
    except Exception:
        return pd.DataFrame()


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
