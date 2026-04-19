"""Monte Carlo analytics for local portfolio and watchlist symbols.

This module intentionally contains no account-specific paths or hardcoded
holdings. Callers pass current holdings derived from local Schwab CSVs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Holding:
    symbol: str
    description: str
    market_value: float
    asset_type: str = ""


def _clean_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace("/", "-")


def _finite_or_none(value):
    try:
        import math

        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _percentile(values, pct: float):
    import numpy as np

    return _finite_or_none(np.percentile(values, pct))


def _download_close(symbols: list[str], period: str):
    import pandas as pd
    import yfinance as yf

    data = yf.download(
        symbols,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if data is None or data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            close = data["Close"]
        elif "Adj Close" in data.columns.get_level_values(0):
            close = data["Adj Close"]
        else:
            close = data.xs(data.columns.get_level_values(0)[0], axis=1, level=0)
    else:
        close = data.get("Close") if "Close" in data else data.get("Adj Close")
        if close is None:
            return pd.DataFrame()
        if not hasattr(close, "to_frame"):
            return pd.DataFrame()
        close = close.to_frame(symbols[0])

    if not isinstance(close, pd.DataFrame):
        close = close.to_frame(symbols[0])

    close = close.rename(columns={c: _clean_symbol(str(c)) for c in close.columns})
    close = close.dropna(axis=1, how="all").ffill().dropna(how="all")
    return close


def _metrics(final_values, initial_value: float):
    import numpy as np

    losses = final_values[final_values < initial_value]
    p05 = _percentile(final_values, 5)
    cvar_5 = _finite_or_none(losses.mean()) if len(losses) else p05
    return {
        "initial_value": _finite_or_none(initial_value),
        "expected_final": _finite_or_none(final_values.mean()),
        "p05": p05,
        "p25": _percentile(final_values, 25),
        "p50": _percentile(final_values, 50),
        "p75": _percentile(final_values, 75),
        "p95": _percentile(final_values, 95),
        "expected_return_pct": _finite_or_none((final_values.mean() / initial_value - 1) * 100) if initial_value else None,
        "probability_gain_pct": _finite_or_none((final_values > initial_value).mean() * 100),
        "probability_loss_pct": _finite_or_none((final_values < initial_value).mean() * 100),
        "var_5": _finite_or_none(initial_value - p05) if p05 is not None else None,
        "cvar_5": _finite_or_none(initial_value - cvar_5) if cvar_5 is not None else None,
        "sample_count": int(np.asarray(final_values).shape[0]),
    }


def run_monte_carlo(
    holdings: Iterable[Holding],
    candidate_symbols: Iterable[str] = (),
    *,
    days: int = 90,
    simulations: int = 3000,
    period: str = "1y",
    seed: int = 42,
) -> dict:
    """Run a correlated Monte Carlo portfolio simulation and standalone candidates.

    Returns JSON-serializable dicts. Historical return estimates use public Yahoo
    price history through yfinance.
    """
    import numpy as np

    clean_holdings: list[Holding] = []
    for h in holdings:
        sym = _clean_symbol(h.symbol)
        if not sym or h.market_value <= 0:
            continue
        clean_holdings.append(Holding(sym, h.description, float(h.market_value), h.asset_type))

    candidate_list = []
    seen_candidates = set()
    for sym in candidate_symbols:
        cleaned = _clean_symbol(sym)
        if cleaned and cleaned not in seen_candidates:
            seen_candidates.add(cleaned)
            candidate_list.append(cleaned)

    portfolio_symbols = [h.symbol for h in clean_holdings]
    all_symbols = sorted(set(portfolio_symbols + candidate_list))
    if not all_symbols:
        return {"error": "No symbols to simulate", "portfolio": None, "candidates": []}

    close = _download_close(all_symbols, period)
    if close.empty:
        return {"error": "No historical prices returned", "portfolio": None, "candidates": []}

    returns = np.log(close / close.shift(1)).replace([np.inf, -np.inf], np.nan).dropna(how="all")
    available = [s for s in all_symbols if s in returns.columns and returns[s].dropna().shape[0] >= 50]
    missing = [s for s in all_symbols if s not in available]
    if not available:
        return {
            "error": "Not enough historical return data",
            "portfolio": None,
            "candidates": [],
            "missing_symbols": missing,
        }

    returns = returns[available].dropna(how="any")
    if returns.shape[0] < 50:
        return {
            "error": "Not enough overlapping historical return data",
            "portfolio": None,
            "candidates": [],
            "missing_symbols": missing,
        }

    days = max(5, min(int(days), 252))
    simulations = max(500, min(int(simulations), 20000))
    rng = np.random.default_rng(seed)

    mean_daily = returns.mean().to_numpy(dtype=float)
    cov_daily = returns.cov().to_numpy(dtype=float)
    cov_daily = cov_daily + np.eye(cov_daily.shape[0]) * 1e-10

    try:
        draws = rng.multivariate_normal(mean_daily, cov_daily, size=(simulations, days), check_valid="ignore")
    except Exception:
        diag = np.diag(np.diag(cov_daily))
        draws = rng.multivariate_normal(mean_daily, diag, size=(simulations, days), check_valid="ignore")

    cumulative = np.exp(np.cumsum(draws, axis=1))
    symbol_index = {sym: i for i, sym in enumerate(available)}

    portfolio = None
    used_holdings = [h for h in clean_holdings if h.symbol in symbol_index]
    if used_holdings:
        values = np.array([h.market_value for h in used_holdings], dtype=float)
        indices = [symbol_index[h.symbol] for h in used_holdings]
        portfolio_paths = np.tensordot(cumulative[:, :, indices], values, axes=([2], [0]))
        initial_value = float(values.sum())
        final_values = portfolio_paths[:, -1]
        bands = []
        for day in range(days):
            day_values = portfolio_paths[:, day]
            bands.append({
                "day": day + 1,
                "p05": _percentile(day_values, 5),
                "p50": _percentile(day_values, 50),
                "p95": _percentile(day_values, 95),
            })

        portfolio = {
            **_metrics(final_values, initial_value),
            "days": days,
            "period": period,
            "symbols_used": [h.symbol for h in used_holdings],
            "symbols_missing": [h.symbol for h in clean_holdings if h.symbol not in symbol_index],
            "bands": bands,
            "note": "Monte Carlo uses historical log returns and correlation from Yahoo prices. It is risk context, not a price forecast.",
        }

    candidates = []
    annual_mean = returns.mean() * 252
    annual_vol = returns.std() * np.sqrt(252)
    for sym in candidate_list:
        if sym not in symbol_index:
            candidates.append({"symbol": sym, "status": "missing_history"})
            continue
        idx = symbol_index[sym]
        price = close[sym].dropna().iloc[-1] if sym in close else None
        simulated_prices = float(price) * cumulative[:, -1, idx] if price is not None else cumulative[:, -1, idx]
        metric = _metrics(simulated_prices, float(price) if price is not None else 1.0)
        downside = (float(price) - (metric["p05"] or float(price))) if price is not None else None
        upside = ((metric["p50"] or float(price)) - float(price)) if price is not None else None
        score = _finite_or_none(upside / downside) if downside and downside > 0 and upside is not None else None
        candidates.append({
            "symbol": sym,
            "status": "ok",
            "last_price": _finite_or_none(price),
            "annual_return_pct": _finite_or_none(annual_mean[sym] * 100),
            "annual_vol_pct": _finite_or_none(annual_vol[sym] * 100),
            "sharpe_like": _finite_or_none(annual_mean[sym] / annual_vol[sym]) if annual_vol[sym] else None,
            "risk_reward_score": score,
            **metric,
        })

    candidates.sort(key=lambda c: (c.get("status") == "ok", c.get("risk_reward_score") or -999), reverse=True)

    return {
        "portfolio": portfolio,
        "candidates": candidates,
        "missing_symbols": missing,
        "history_rows": int(returns.shape[0]),
        "history_start": str(returns.index[0])[:10],
        "history_end": str(returns.index[-1])[:10],
    }
