"""Yahoo Finance price fetcher with 60-second cache."""
from __future__ import annotations

import time
from typing import Optional

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore

# Schwab symbol → Yahoo Finance symbol overrides
SYMBOL_MAP: dict[str, Optional[str]] = {
    "BRK/B": "BRK-B",
    "BRK/A": "BRK-A",
    "--": None,
    "": None,
}

_cache: dict[str, tuple[float, dict]] = {}  # symbol -> (timestamp, data)
_CACHE_TTL = 60.0


def _yahoo_symbol(schwab_sym: str) -> Optional[str]:
    s = schwab_sym.strip()
    if s in SYMBOL_MAP:
        return SYMBOL_MAP[s]
    return s


def get_prices(symbols: list[str]) -> dict[str, dict]:
    """Fetch current price data for a list of Schwab symbols.

    Returns dict keyed by original symbol with:
        current_price, day_change, day_change_pct, as_of, stale (bool)
    """
    if yf is None:
        return {s: {"current_price": None, "day_change": None, "day_change_pct": None, "as_of": None, "stale": True} for s in symbols}

    now = time.time()
    result: dict[str, dict] = {}
    to_fetch: list[tuple[str, str]] = []  # (original, yahoo)

    for sym in symbols:
        yahoo_sym = _yahoo_symbol(sym)
        if yahoo_sym is None:
            # Cash / money market
            result[sym] = {"current_price": 1.0, "day_change": 0.0, "day_change_pct": 0.0, "as_of": None, "stale": False}
            continue
        if sym in _cache and (now - _cache[sym][0]) < _CACHE_TTL:
            result[sym] = _cache[sym][1]
            continue
        to_fetch.append((sym, yahoo_sym))

    if to_fetch:
        yahoo_syms = [y for _, y in to_fetch]
        try:
            tickers = yf.Tickers(" ".join(yahoo_syms))
            for orig_sym, yahoo_sym in to_fetch:
                try:
                    info = tickers.tickers[yahoo_sym].fast_info
                    price = getattr(info, "last_price", None)
                    prev_close = getattr(info, "previous_close", None)
                    day_change = (price - prev_close) if (price is not None and prev_close is not None) else None
                    day_change_pct = (day_change / prev_close * 100) if (day_change is not None and prev_close) else None
                    data = {
                        "current_price": price,
                        "day_change": day_change,
                        "day_change_pct": day_change_pct,
                        "as_of": None,
                        "stale": price is None,
                    }
                except Exception:
                    data = {"current_price": None, "day_change": None, "day_change_pct": None, "as_of": None, "stale": True}
                _cache[orig_sym] = (now, data)
                result[orig_sym] = data
        except Exception:
            for orig_sym, _ in to_fetch:
                data = {"current_price": None, "day_change": None, "day_change_pct": None, "as_of": None, "stale": True}
                result[orig_sym] = data

    return result
