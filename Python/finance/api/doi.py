"""Deployment Opportunity Index analytics for local portfolio holdings.

This module computes a cash-aware "deploy vs hold vs trim" score per ticker
using local holdings plus Yahoo Finance market data. It intentionally avoids
hardcoded account-specific values and reads conviction overrides from a private
JSON file outside the repo when available.
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError:  # pragma: no cover - handled at runtime
    np = None  # type: ignore[assignment]
    pd = None  # type: ignore[assignment]
    yf = None  # type: ignore[assignment]


CONVICTION_PATH = Path(
    os.environ.get(
        "CONVICTION_JSON_PATH",
        "~/.openclaw/workspace/Data/Private/finance/conviction.json",
    )
).expanduser()
HISTORY_CACHE_TTL = 6 * 60 * 60
HISTORY_PERIOD = "1y"
INDEX_SYMBOLS = {"SPX": "^GSPC", "QQQ": "QQQ", "DJI": "^DJI"}
VIX_SYMBOL = "^VIX"
DEFAULT_CONVICTION = {
    "tickers": {
        "NVDA": 1.0,
        "TSM": 1.0,
        "ASML": 1.0,
        "MSFT": 0.9,
        "META": 0.9,
        "AVGO": 0.85,
        "GOOGL": 0.8,
        "AMZN": 0.7,
        "AAPL": 0.6,
        "TSLA": 0.6,
    },
    "default": 0.3,
}
_HISTORY_CACHE: dict[str, tuple[float, Any]] = {}


@dataclass(frozen=True)
class DOIInputs:
    holdings: list[dict[str, Any]]
    cash_value: float
    total_account_value: float


@dataclass(frozen=True)
class DOIWeights:
    w1: float = 0.30
    w2: float = 0.20
    w3: float = 0.15
    w4: float = 0.20
    w5: float = 0.10
    w6: float = 0.05


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _yahoo_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace("/", "-")


def _seed_conviction_file() -> None:
    CONVICTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONVICTION_PATH.write_text(json.dumps(DEFAULT_CONVICTION, indent=2) + "\n", encoding="utf-8")


def _load_conviction() -> dict[str, Any]:
    """Load ticker conviction weights, seeding a private JSON file if missing."""
    if not CONVICTION_PATH.exists():
        logger.info("Seeding conviction file at %s", CONVICTION_PATH)
        _seed_conviction_file()
    try:
        payload = json.loads(CONVICTION_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load conviction file %s: %s", CONVICTION_PATH, exc)
        return DEFAULT_CONVICTION

    tickers = payload.get("tickers")
    default = _finite_or_none(payload.get("default"))
    if not isinstance(tickers, dict):
        logger.warning("Conviction file missing ticker map, using defaults")
        return DEFAULT_CONVICTION
    return {
        "tickers": {str(k).strip().upper(): _clip(_finite_or_none(v) or 0.0, 0.0, 1.0) for k, v in tickers.items()},
        "default": _clip(default if default is not None else DEFAULT_CONVICTION["default"], 0.0, 1.0),
    }


def _fetch_close_history(symbol: str) -> Any:
    if yf is None or pd is None:
        return None

    yahoo_symbol = _yahoo_symbol(symbol)
    now = time.time()
    cached = _HISTORY_CACHE.get(yahoo_symbol)
    if cached and (now - cached[0]) < HISTORY_CACHE_TTL:
        return cached[1]

    try:
        history = yf.Ticker(yahoo_symbol).history(period=HISTORY_PERIOD, interval="1d", auto_adjust=True)
    except Exception as exc:
        logger.warning("History fetch failed for %s: %s", symbol, exc)
        _HISTORY_CACHE[yahoo_symbol] = (now, None)
        return None

    if history is None or history.empty or "Close" not in history:
        logger.warning("History fetch returned no close data for %s", symbol)
        _HISTORY_CACHE[yahoo_symbol] = (now, None)
        return None

    close = history["Close"].dropna()
    if close.empty:
        logger.warning("History close series empty for %s", symbol)
        _HISTORY_CACHE[yahoo_symbol] = (now, None)
        return None

    _HISTORY_CACHE[yahoo_symbol] = (now, close)
    return close


def _prefetch_histories(symbols: list[str]) -> None:
    if yf is None or pd is None:
        return

    now = time.time()
    missing_pairs: list[tuple[str, str]] = []
    for symbol in symbols:
        yahoo_symbol = _yahoo_symbol(symbol)
        cached = _HISTORY_CACHE.get(yahoo_symbol)
        if cached and (now - cached[0]) < HISTORY_CACHE_TTL:
            continue
        missing_pairs.append((symbol, yahoo_symbol))

    if not missing_pairs:
        return

    yahoo_symbols = [yahoo_symbol for _, yahoo_symbol in missing_pairs]
    try:
        data = yf.download(
            yahoo_symbols,
            period=HISTORY_PERIOD,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by="ticker",
        )
    except Exception as exc:
        logger.warning("Bulk history fetch failed, falling back to per-symbol requests: %s", exc)
        for symbol, _ in missing_pairs:
            _fetch_close_history(symbol)
        return

    for original_symbol, yahoo_symbol in missing_pairs:
        close = None
        if data is not None and not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                if yahoo_symbol in data.columns.get_level_values(0):
                    frame = data[yahoo_symbol]
                    if "Close" in frame:
                        close = frame["Close"].dropna()
                    elif "Adj Close" in frame:
                        close = frame["Adj Close"].dropna()
            else:
                if "Close" in data:
                    close = data["Close"].dropna()
                elif "Adj Close" in data:
                    close = data["Adj Close"].dropna()
        if close is None or close.empty:
            logger.warning("Bulk history fetch returned no close data for %s", original_symbol)
            _HISTORY_CACHE[yahoo_symbol] = (now, None)
            continue
        _HISTORY_CACHE[yahoo_symbol] = (now, close)


def _moving_average(close, window: int) -> float | None:
    if close is None or len(close) < window:
        return None
    return _finite_or_none(close.tail(window).mean())


def _rolling_std(close, window: int) -> float | None:
    if close is None or len(close) < window:
        return None
    return _finite_or_none(close.tail(window).std(ddof=0))


def _rsi14(close) -> float | None:
    if close is None or len(close) < 15 or pd is None:
        return None

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

    last_gain = _finite_or_none(avg_gain.iloc[-1])
    last_loss = _finite_or_none(avg_loss.iloc[-1])
    if last_gain is None or last_loss is None:
        return None
    if last_loss == 0:
        return 100.0 if last_gain > 0 else 50.0

    rs = last_gain / last_loss
    return _finite_or_none(100.0 - (100.0 / (1.0 + rs)))


def _drawdown_score(current_price: float, high_52w: float) -> float | None:
    if high_52w <= 0:
        return None
    dd = max(0.0, (high_52w - current_price) / high_52w)
    return _clip(1.0 - math.exp(-3.0 * dd), 0.0, 1.0)


def _momentum_exhaustion(close) -> float | None:
    rsi = _rsi14(close)
    if rsi is None:
        return None
    return _clip(max(0.0, (rsi - 50.0) / 50.0), 0.0, 1.0)


def _index_regime(close) -> float | None:
    current_price = _finite_or_none(close.iloc[-1]) if close is not None and len(close) else None
    ma20 = _moving_average(close, 20)
    std20 = _rolling_std(close, 20)
    if current_price is None or ma20 is None or std20 is None or std20 <= 0:
        return None
    return _clip(-math.tanh((current_price - ma20) / (2.0 * std20)), -1.0, 1.0)


def _local_top_probability(close, vix_close) -> float | None:
    current_price = _finite_or_none(close.iloc[-1]) if close is not None and len(close) else None
    ma20 = _moving_average(close, 20)
    std20 = _rolling_std(close, 20)
    rsi = _rsi14(close)
    vix_value = _finite_or_none(vix_close.iloc[-1]) if vix_close is not None and len(vix_close) else None
    if current_price is None or ma20 is None or std20 is None or std20 <= 0 or rsi is None:
        return None
    complacency = 1.0 if vix_value is not None and vix_value < 15.0 else 0.0
    value = ((current_price - ma20) / std20) + (0.05 * (rsi - 70.0)) + (0.5 * complacency)
    return _clip(_sigmoid(value), 0.0, 1.0)


def _breadth_deterioration(holdings: list[dict[str, Any]]) -> float:
    ranked = sorted(
        [holding for holding in holdings if _finite_or_none(holding.get("market_value")) is not None],
        key=lambda holding: _finite_or_none(holding.get("market_value")) or 0.0,
        reverse=True,
    )[:20]
    below_count = 0
    evaluated = 0
    for holding in ranked:
        close = _fetch_close_history(holding.get("symbol", ""))
        current_price = _finite_or_none(holding.get("current_price"))
        ma50 = _moving_average(close, 50)
        if close is None or ma50 is None:
            continue
        if current_price is None:
            current_price = _finite_or_none(close.iloc[-1])
        if current_price is None:
            continue
        evaluated += 1
        if current_price < ma50:
            below_count += 1
    return (below_count / evaluated) if evaluated else 0.0


def _portfolio_weight(holding: dict[str, Any], total_account_value: float) -> float:
    pct_of_account = _finite_or_none(holding.get("pct_of_account"))
    if pct_of_account is not None:
        return max(0.0, pct_of_account / 100.0)
    market_value = _finite_or_none(holding.get("market_value")) or 0.0
    if total_account_value <= 0:
        return 0.0
    return max(0.0, market_value / total_account_value)


def compute_doi(inputs: DOIInputs, weights: DOIWeights | None = None) -> dict[str, Any]:
    """Compute DOI snapshot data for the current portfolio."""
    weights = weights or DOIWeights()
    _prefetch_histories(list(INDEX_SYMBOLS.values()) + [VIX_SYMBOL] + [holding.get("symbol", "") for holding in inputs.holdings])
    conviction = _load_conviction()
    conviction_map = conviction.get("tickers", {})
    conviction_default = _finite_or_none(conviction.get("default")) or DEFAULT_CONVICTION["default"]
    cash_pct = (inputs.cash_value / inputs.total_account_value) if inputs.total_account_value > 0 else 0.0
    cash_score = _clip(cash_pct / 0.10, 0.0, 1.0)

    index_payload: dict[str, dict[str, float | None]] = {}
    index_regime_values: list[float] = []
    vix_close = _fetch_close_history(VIX_SYMBOL)
    for label, symbol in INDEX_SYMBOLS.items():
        close = _fetch_close_history(symbol)
        regime_score = _index_regime(close)
        local_top_prob = _local_top_probability(close, vix_close)
        if regime_score is not None:
            index_regime_values.append(regime_score)
        index_payload[label] = {
            "local_top_prob": local_top_prob,
            "regime_score": regime_score,
        }
    index_regime_score = sum(index_regime_values) / len(index_regime_values) if index_regime_values else 0.0

    breadth_deterioration = _clip(max(0.0, _breadth_deterioration(inputs.holdings) - 0.4) / 0.6, 0.0, 1.0)
    ticker_payload: list[dict[str, Any]] = []
    weighted_doi_sum = 0.0
    has_deploy_signal = False

    for holding in sorted(inputs.holdings, key=lambda item: _finite_or_none(item.get("market_value")) or 0.0, reverse=True):
        symbol = str(holding.get("symbol", "")).strip().upper()
        if not symbol:
            continue

        close = _fetch_close_history(symbol)
        current_price = _finite_or_none(holding.get("current_price"))
        if current_price is None and close is not None and len(close):
            current_price = _finite_or_none(close.iloc[-1])
        high_52w = _finite_or_none(close.max()) if close is not None and len(close) else None
        drawdown_score = _drawdown_score(current_price, high_52w) if current_price is not None and high_52w is not None else None
        momentum_exhaustion = _momentum_exhaustion(close)
        conviction_score = _clip(
            _finite_or_none(conviction_map.get(symbol, conviction_default)) or conviction_default,
            0.0,
            1.0,
        )

        doi_value = None
        action = "data_missing"
        size_hint = 0.0
        if drawdown_score is not None and momentum_exhaustion is not None:
            doi_value = (
                (weights.w1 * drawdown_score)
                + (weights.w2 * index_regime_score)
                + (weights.w3 * cash_score)
                + (weights.w4 * conviction_score)
                - (weights.w5 * momentum_exhaustion)
                - (weights.w6 * breadth_deterioration)
            )
            doi_value = _clip(doi_value, -1.0, 1.0)
            if doi_value > 0.5:
                action = "deploy"
                has_deploy_signal = True
                size_hint = max(0.0, inputs.cash_value * doi_value)
            elif doi_value < -0.5:
                action = "trim"
            else:
                action = "hold"

            weighted_doi_sum += doi_value * _portfolio_weight(holding, inputs.total_account_value)
        else:
            logger.warning("DOI data missing for %s", symbol)

        ticker_payload.append(
            {
                "symbol": symbol,
                "current_price": current_price,
                "high_52w": high_52w,
                "drawdown_score": drawdown_score,
                "index_regime_score": index_regime_score,
                "cash_availability_score": cash_score,
                "conviction_score": conviction_score,
                "momentum_exhaustion": momentum_exhaustion,
                "breadth_deterioration": breadth_deterioration,
                "doi": doi_value,
                "action": action,
                "size_hint_dollars": size_hint,
            }
        )

    cash_deficit_warning = has_deploy_signal and cash_pct < 0.05
    cash_deficit_penalty = 0.0
    if cash_deficit_warning:
        cash_deficit_penalty = 0.25 * _clip((0.05 - cash_pct) / 0.05, 0.0, 1.0)

    portfolio_doi = _clip(weighted_doi_sum - cash_deficit_penalty, -1.0, 1.0)

    return {
        "as_of": date.today().isoformat(),
        "weights": asdict(weights),
        "portfolio_doi": portfolio_doi,
        "cash_deficit_warning": cash_deficit_warning,
        "cash_pct": cash_pct,
        "tickers": ticker_payload,
        "indices": index_payload,
    }
