"""Local Schwab portfolio API — binds to 127.0.0.1:8765 only."""
from __future__ import annotations

import os
import csv
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .price_fetcher import get_prices
from .schwab_parser import parse_positions_csv, parse_rgl_csv, parse_transactions_csv
from .monte_carlo import Holding, run_monte_carlo

BASE_DIR = Path(os.environ.get("SCHWAB_BASE_DIR", "~/.openclaw/workspace/Data/Private/finance/schwab-brokerage")).expanduser()
_EARNINGS_CACHE: dict[str, tuple[float, dict]] = {}
_EARNINGS_CACHE_TTL = 6 * 60 * 60

app = FastAPI(title="Schwab Portfolio API", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _latest_positions_file() -> Optional[Path]:
    pos_dir = BASE_DIR / "positions"
    snapshots = sorted(
        (p for p in pos_dir.glob("*.csv") if "master" not in p.name.lower()),
        key=lambda p: p.stem,
        reverse=True,
    )
    return snapshots[0] if snapshots else None


def _all_positions_files() -> list[Path]:
    pos_dir = BASE_DIR / "positions"
    return sorted(p for p in pos_dir.glob("*.csv") if "master" not in p.name.lower())


def _all_rgl_files(kind: str) -> list[Path]:
    """kind='summary' or 'details'"""
    rgl_dir = BASE_DIR / "realized-gain-loss"
    if kind == "details":
        return sorted(p for p in rgl_dir.glob("*.csv") if "Details" in p.name and "MASTER" not in p.name)
    return sorted(p for p in rgl_dir.glob("*.csv") if "Details" not in p.name and "MASTER" not in p.name and p.stem[0] != "d")


def _parse_float(val: str) -> Optional[float]:
    if val is None:
        return None
    v = val.replace("$", "").replace("%", "").replace(",", "").strip()
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _parse_schwab_date(val: str) -> Optional[date]:
    """Parse Schwab dates and date-range input into a date.

    Handles values such as MM/DD/YYYY, MM/DD/YY, YYYY-MM-DD, and
    transaction strings like "04/06/2026 as of 04/02/2026". The first date
    is the trade/closed date and is the one users expect filters to apply to.
    """
    s = (val or "").strip()
    if not s:
        return None
    first = s.split(" as of ", 1)[0].strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(first, fmt).date()
        except ValueError:
            pass
    return None


def _date_iso(val: str) -> Optional[str]:
    parsed = _parse_schwab_date(val)
    return parsed.isoformat() if parsed else None


def _filter_by_date(rows: list[dict], date_col: str, from_date: Optional[str], to_date: Optional[str]) -> list[dict]:
    if not from_date and not to_date:
        return rows
    start = _parse_schwab_date(from_date or "")
    end = _parse_schwab_date(to_date or "")
    out = []
    for r in rows:
        d = _parse_schwab_date(r.get(date_col, ""))
        if d is None:
            continue
        if start and d < start:
            continue
        if end and d > end:
            continue
        out.append(r)
    return out


def _annotate_iso_date(rows: list[dict], source_col: str, target_col: str) -> list[dict]:
    for r in rows:
        r[target_col] = _date_iso(r.get(source_col, ""))
    return rows


def _parse_money(val: str) -> Optional[float]:
    return _parse_float(val)


def _current_positions_from_csv() -> tuple[str, list[dict]]:
    path = _latest_positions_file()
    if not path:
        return "", []
    snapshot_date, _, rows = parse_positions_csv(str(path))
    return snapshot_date, rows


def _position_market_value(row: dict) -> float:
    return _parse_float(row.get("Mkt Val (Market Value)", row.get("Mkt Val", ""))) or 0.0


def _is_security_position(row: dict) -> bool:
    sym = row.get("Symbol", "").strip()
    qty = _parse_float(row.get("Qty (Quantity)", row.get("Qty", "")))
    return bool(sym) and sym != "Positions Total" and qty is not None


def _yahoo_symbol(sym: str) -> str:
    return sym.strip().replace("/", "-")


# ── endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "base_dir": str(BASE_DIR)}


@app.get("/positions/current")
def positions_current():
    path = _latest_positions_file()
    if not path:
        return {"error": "no positions file found", "positions": []}

    snapshot_date, _, rows = parse_positions_csv(str(path))

    symbols = [r.get("Symbol", "").strip() for r in rows]
    prices = get_prices(symbols)

    result = []
    for r in rows:
        sym = r.get("Symbol", "").strip()
        qty = _parse_float(r.get("Qty (Quantity)", r.get("Qty", "")))
        cost_per_share = _parse_float(r.get("Cost/Share", ""))
        cost_basis = _parse_float(r.get("Cost Basis", ""))
        pinfo = prices.get(sym, {})
        current_price = pinfo.get("current_price")
        market_value = (qty * current_price) if (qty is not None and current_price is not None) else _parse_float(r.get("Mkt Val (Market Value)", r.get("Mkt Val", "")))
        unreal_gl = (market_value - cost_basis) if (market_value is not None and cost_basis is not None) else None
        unreal_gl_pct = (unreal_gl / cost_basis * 100) if (unreal_gl is not None and cost_basis) else None

        result.append({
            "symbol": sym,
            "description": r.get("Description", ""),
            "qty": qty,
            "cost_basis_per_share": cost_per_share,
            "cost_basis_total": cost_basis,
            "current_price": current_price,
            "market_value": market_value,
            "unrealized_gl_dollars": unreal_gl,
            "unrealized_gl_pct": unreal_gl_pct,
            "day_change_dollars": pinfo.get("day_change"),
            "day_change_pct": pinfo.get("day_change_pct"),
            "pct_of_account": _parse_float(r.get("% of Acct (% of Account)", r.get("% of Acct", ""))),
            "asset_type": r.get("Asset Type", r.get("Security Type", "")),
            "price_stale": pinfo.get("stale", True),
        })

    return {"snapshot_date": snapshot_date, "positions": result}


@app.get("/portfolio/summary")
def portfolio_summary():
    pos = positions_current()
    positions = pos.get("positions", [])
    total_mv = sum(p["market_value"] for p in positions if p["market_value"] is not None)
    total_cb = sum(p["cost_basis_total"] for p in positions if p["cost_basis_total"] is not None)
    # Compute unrealized G/L only for positions where BOTH market value AND cost basis
    # are known — this excludes cash (cost_basis=None) which has zero unrealized gain.
    total_gl = sum(
        p["market_value"] - p["cost_basis_total"]
        for p in positions
        if p["market_value"] is not None and p["cost_basis_total"] is not None
    )
    total_gl_pct = (total_gl / total_cb * 100) if total_cb else None
    total_day = sum((p["day_change_dollars"] or 0) * (p["qty"] or 0) for p in positions)
    return {
        "total_market_value": total_mv,
        "total_cost_basis": total_cb,
        "total_unrealized_gl_dollars": total_gl,
        "total_unrealized_gl_pct": total_gl_pct,
        "total_day_change": total_day,
        "position_count": len(positions),
        "as_of": pos.get("snapshot_date"),
    }


@app.get("/transactions")
def transactions(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
):
    tx_dir = BASE_DIR / "transactions"
    master = tx_dir / "Joint_Tenant_Transactions_MASTER.csv"
    if master.exists():
        _, rows = parse_transactions_csv(str(master))
    else:
        all_rows: list[dict] = []
        for p in sorted(tx_dir.glob("*.csv")):
            if "MASTER" in p.name:
                continue
            _, r = parse_transactions_csv(str(p))
            all_rows.extend(r)
        rows = all_rows

    if from_date or to_date:
        rows = _filter_by_date(rows, "Date", from_date, to_date)
    _annotate_iso_date(rows, "Date", "date_iso")
    if symbol:
        rows = [r for r in rows if symbol.upper() in r.get("Symbol", "").upper()]
    if action:
        rows = [r for r in rows if action.lower() in r.get("Action", "").lower()]

    return {"count": len(rows), "transactions": rows}


@app.get("/rgl/summary")
def rgl_summary(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
):
    rgl_dir = BASE_DIR / "realized-gain-loss"
    master = rgl_dir / "Joint_Tenant_GainLoss_Realized_Summary_MASTER.csv"
    if master.exists():
        _, rows = parse_rgl_csv(str(master))
    else:
        rows = []
        for p in _all_rgl_files("summary"):
            _, r = parse_rgl_csv(str(p))
            rows.extend(r)

    if from_date or to_date:
        rows = _filter_by_date(rows, "Closed Date", from_date, to_date)
    _annotate_iso_date(rows, "Closed Date", "closed_date_iso")

    return {"count": len(rows), "rows": rows}


@app.get("/rgl/details")
def rgl_details(
    symbol: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
):
    rgl_dir = BASE_DIR / "realized-gain-loss"
    master = rgl_dir / "Joint_Tenant_GainLoss_Realized_Details_MASTER.csv"
    if master.exists():
        _, rows = parse_rgl_csv(str(master))
    else:
        rows = []
        for p in _all_rgl_files("details"):
            _, r = parse_rgl_csv(str(p))
            rows.extend(r)

    if symbol:
        rows = [r for r in rows if symbol.upper() == r.get("Symbol", "").upper()]
    if from_date or to_date:
        rows = _filter_by_date(rows, "Closed Date", from_date, to_date)
    _annotate_iso_date(rows, "Closed Date", "closed_date_iso")
    _annotate_iso_date(rows, "Opened Date", "opened_date_iso")

    return {"count": len(rows), "rows": rows}


@app.get("/balances")
def balances():
    master = BASE_DIR / "balances" / "master-balances.csv"
    if not master.exists():
        return {"count": 0, "rows": [], "latest": None}

    rows: list[dict] = []
    with master.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            snapshot_iso = _date_iso(r.get("SnapshotDate", ""))
            rows.append({
                **r,
                "snapshot_date_iso": snapshot_iso,
                "account_value": _parse_money(r.get("Account Value", "")),
                "day_change": _parse_money(r.get("Day Change", "")),
                "day_change_pct": _parse_money(r.get("Day Change %", "")),
                "cash": _parse_money(r.get("Cash & Cash Investments", "")),
                "securities_value": _parse_money(r.get("Market Value (Securities)", "")),
                "available_to_trade": _parse_money(r.get("Available to Trade (Cash)", "")),
                "settled_funds": _parse_money(r.get("Settled Funds", "")),
                "available_to_withdraw": _parse_money(r.get("Available to Withdraw", "")),
            })

    rows.sort(key=lambda r: r.get("snapshot_date_iso") or "")
    return {"count": len(rows), "rows": rows, "latest": rows[-1] if rows else None}


@app.get("/portfolio/context")
def portfolio_context():
    """Local-only portfolio context and risk flags from Schwab CSV data.

    This is deterministic analytics, not model-generated financial advice.
    It avoids sending private holdings to any external AI service.
    """
    snapshot_date, rows = _current_positions_from_csv()
    positions = [r for r in rows if _is_security_position(r)]
    total_mv = sum(_position_market_value(r) for r in positions)
    cash_rows = [r for r in rows if not _is_security_position(r)]
    cash = sum(_position_market_value(r) for r in cash_rows if _position_market_value(r) > 0)

    ranked = sorted(positions, key=_position_market_value, reverse=True)
    top = []
    for r in ranked[:10]:
        mv = _position_market_value(r)
        cb = _parse_float(r.get("Cost Basis", ""))
        gl = (mv - cb) if cb is not None else _parse_float(r.get("Gain $ (Gain/Loss $)", r.get("Gain $", "")))
        top.append({
            "symbol": r.get("Symbol", "").strip(),
            "description": r.get("Description", ""),
            "market_value": mv,
            "weight_pct": (mv / total_mv * 100) if total_mv else None,
            "unrealized_gl": gl,
            "unrealized_gl_pct": _parse_float(r.get("Gain % (Gain/Loss %)", r.get("Gain %", ""))),
            "rating": r.get("Ratings", ""),
            "asset_type": r.get("Asset Type", r.get("Security Type", "")),
        })

    ytd_realized = 0.0
    st_ytd = 0.0
    lt_ytd = 0.0
    wash_sale_count = 0
    rgl_master = BASE_DIR / "realized-gain-loss" / "Joint_Tenant_GainLoss_Realized_Summary_MASTER.csv"
    if rgl_master.exists():
        _, rgl_rows = parse_rgl_csv(str(rgl_master))
        current_year = datetime.now().year
        for r in rgl_rows:
            closed = _parse_schwab_date(r.get("Closed Date", ""))
            if not closed or closed.year != current_year:
                continue
            ytd_realized += _parse_float(r.get("Total Gain/Loss ($)", "")) or 0.0
            st_ytd += _parse_float(r.get("Short Term (ST) Gain/Loss ($)", r.get("ST Gain/Loss ($)", ""))) or 0.0
            lt_ytd += _parse_float(r.get("Long Term (LT) Gain/Loss ($)", r.get("LT Gain/Loss ($)", ""))) or 0.0
            if (r.get("Wash Sale?", "") or "").strip().lower() == "yes":
                wash_sale_count += 1

    top_weight = top[0]["weight_pct"] if top else None
    top5_weight = sum((p["weight_pct"] or 0) for p in top[:5])
    cash_pct = (cash / (total_mv + cash) * 100) if (total_mv + cash) else None
    flags: list[dict] = []
    if top_weight and top_weight >= 15:
        flags.append({"severity": "medium", "label": "Single-name concentration", "detail": f"Largest holding is {top_weight:.1f}% of securities value."})
    if top5_weight >= 50:
        flags.append({"severity": "medium", "label": "Top-five concentration", "detail": f"Top five holdings are {top5_weight:.1f}% of securities value."})
    if cash_pct and cash_pct >= 20:
        flags.append({"severity": "info", "label": "High cash allocation", "detail": f"Cash is {cash_pct:.1f}% of account value from current snapshot rows."})
    if wash_sale_count:
        flags.append({"severity": "high", "label": "Wash-sale review", "detail": f"{wash_sale_count} current-year realized G/L summary rows are marked wash sale."})
    if st_ytd:
        flags.append({"severity": "info", "label": "Short-term tax exposure", "detail": "Current-year realized G/L includes short-term activity."})

    return {
        "snapshot_date": snapshot_date,
        "total_securities_value": total_mv,
        "cash_value": cash,
        "cash_pct": cash_pct,
        "top_holdings": top,
        "realized_ytd": {
            "total": ytd_realized,
            "short_term": st_ytd,
            "long_term": lt_ytd,
            "wash_sale_rows": wash_sale_count,
        },
        "flags": flags,
        "note": "Local deterministic context only. Not investment advice.",
    }


@app.get("/portfolio/earnings")
def portfolio_earnings(limit: int = Query(20, ge=1, le=50)):
    """Upcoming/recent earnings for top current stock positions via yfinance."""
    try:
        import pandas as pd
        import yfinance as yf
    except ImportError:
        return {"events": [], "error": "yfinance/pandas not installed"}

    snapshot_date, rows = _current_positions_from_csv()
    positions = [r for r in rows if _is_security_position(r)]
    ranked = sorted(positions, key=_position_market_value, reverse=True)[:limit]
    now = time.time()
    today = datetime.now().date()
    events = []

    for r in ranked:
        sym = r.get("Symbol", "").strip()
        asset_type = r.get("Asset Type", r.get("Security Type", ""))
        if not sym:
            continue
        cached = _EARNINGS_CACHE.get(sym)
        if cached and (now - cached[0]) < _EARNINGS_CACHE_TTL:
            events.append(cached[1])
            continue

        event = {
            "symbol": sym,
            "description": r.get("Description", ""),
            "asset_type": asset_type,
            "market_value": _position_market_value(r),
            "weight_pct": _parse_float(r.get("% of Acct (% of Account)", r.get("% of Acct", ""))),
            "next_earnings_date": None,
            "previous_earnings_date": None,
            "eps_estimate": None,
            "reported_eps": None,
            "surprise_pct": None,
            "status": "unavailable",
        }

        if "ETF" in asset_type.upper() or "FUND" in asset_type.upper():
            event["status"] = "not_applicable"
            _EARNINGS_CACHE[sym] = (now, event)
            events.append(event)
            continue

        try:
            df = yf.Ticker(_yahoo_symbol(sym)).get_earnings_dates(limit=12)
            if df is None or df.empty:
                _EARNINGS_CACHE[sym] = (now, event)
                events.append(event)
                continue
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index, errors="coerce")
            df = df.sort_index()
            future = df[df.index.date >= today]
            past = df[df.index.date < today]
            row = None
            if not future.empty:
                row = future.iloc[0]
                event["next_earnings_date"] = future.index[0].date().isoformat()
                event["status"] = "upcoming"
            if not past.empty:
                prev = past.iloc[-1]
                event["previous_earnings_date"] = past.index[-1].date().isoformat()
                if row is None:
                    row = prev
                    event["status"] = "historical"
                event["reported_eps"] = None if pd.isna(prev.get("Reported EPS")) else float(prev.get("Reported EPS"))
                event["surprise_pct"] = None if pd.isna(prev.get("Surprise(%)")) else float(prev.get("Surprise(%)"))
            if row is not None:
                est = row.get("EPS Estimate")
                event["eps_estimate"] = None if pd.isna(est) else float(est)
        except Exception as e:
            event["status"] = "error"
            event["error"] = str(e)

        if event["status"] != "error":
            _EARNINGS_CACHE[sym] = (now, event)
        events.append(event)

    return {
        "snapshot_date": snapshot_date,
        "events": events,
        "note": "Earnings data comes from yfinance/Yahoo and may be delayed or missing, especially for ETFs/funds.",
    }


@app.get("/portfolio/earnings-impact")
def portfolio_earnings_impact(
    max_positions: int = Query(25, ge=1, le=75),
):
    """Analyze historical post-earnings price impact for portfolio positions."""
    from .earnings_impact import analyze_earnings_impact

    snapshot_date, rows = _current_positions_from_csv()
    positions = sorted(
        [r for r in rows if _is_security_position(r)],
        key=_position_market_value,
        reverse=True,
    )[:max_positions]

    symbols = []
    descriptions = {}
    asset_types = {}
    for r in positions:
        sym = (r.get("Symbol") or "").strip().upper()
        if sym:
            symbols.append(sym)
            descriptions[sym] = r.get("Description", "")
            asset_types[sym] = r.get("Asset Type", "")

    try:
        result = analyze_earnings_impact(symbols, descriptions, asset_types)
        return {"snapshot_date": snapshot_date, **result}
    except Exception as e:
        return {"snapshot_date": snapshot_date, "error": str(e), "positions": [], "upcoming_alerts": []}


@app.get("/portfolio/monte-carlo")
def portfolio_monte_carlo(
    symbols: str = Query("", description="Comma-separated optional watchlist symbols"),
    days: int = Query(90, ge=5, le=252),
    simulations: int = Query(3000, ge=500, le=20000),
    period: str = Query("1y", description="Yahoo history period, e.g. 6mo, 1y, 2y, 5y"),
    max_positions: int = Query(25, ge=1, le=75),
):
    """Monte Carlo risk bands for current positions plus optional watchlist symbols."""
    snapshot_date, rows = _current_positions_from_csv()
    positions = sorted(
        [r for r in rows if _is_security_position(r)],
        key=_position_market_value,
        reverse=True,
    )[:max_positions]
    holdings = [
        Holding(
            symbol=r.get("Symbol", ""),
            description=r.get("Description", ""),
            market_value=_position_market_value(r),
            asset_type=r.get("Asset Type", r.get("Security Type", "")),
        )
        for r in positions
    ]
    candidates = [s.strip() for s in symbols.split(",") if s.strip()]
    try:
        result = run_monte_carlo(
            holdings,
            candidates,
            days=days,
            simulations=simulations,
            period=period,
        )
    except Exception as e:
        return {
            "snapshot_date": snapshot_date,
            "error": str(e),
            "portfolio": None,
            "candidates": [],
        }

    return {
        "snapshot_date": snapshot_date,
        "portfolio_position_count": len(holdings),
        "watchlist": candidates,
        **result,
    }


@app.get("/portfolio/history")
def portfolio_history():
    """All downloaded position snapshots over time."""
    snapshots = []
    for p in _all_positions_files():
        snapshot_date, _, rows = parse_positions_csv(str(p))
        # Exclude summary rows (no cost basis = cash, no symbol = total)
        sec_rows = [r for r in rows if _parse_float(r.get("Cost Basis", "")) is not None]
        cash_rows = [r for r in rows if _parse_float(r.get("Cost Basis", "")) is None
                     and r.get("Symbol", "") not in ("", "Positions Total")]
        total_mv = (
            sum(_parse_float(r.get("Mkt Val (Market Value)", "")) or 0 for r in sec_rows)
            + sum(_parse_float(r.get("Mkt Val (Market Value)", "")) or 0 for r in cash_rows)
        )
        total_cb = sum(_parse_float(r.get("Cost Basis", "")) or 0 for r in sec_rows)
        unrealized_gl = sum(
            (_parse_float(r.get("Mkt Val (Market Value)", "")) or 0) - (_parse_float(r.get("Cost Basis", "")) or 0)
            for r in sec_rows
        )
        snapshots.append({
            "date": snapshot_date,
            "total_market_value": total_mv,
            "total_cost_basis": total_cb,
            "unrealized_gl": unrealized_gl,
            "position_count": len(sec_rows),
        })
    return {"snapshots": snapshots}


@app.get("/portfolio/timeseries")
def portfolio_timeseries(period: str = Query("1y", description="1m 3m 6m 1y 2y")):
    """
    Estimated daily portfolio value using current holdings × Yahoo Finance historical prices.

    NOTE: This uses your CURRENT position quantities applied to historical prices.
    It is NOT a reconstruction of your actual historical portfolio — positions
    you have sold are excluded, and positions you bought recently may be included
    from before you owned them. Think of it as 'how have my current holdings
    performed over time', not 'what was my account worth on date X'.
    """
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed", "series": []}

    path = _latest_positions_file()
    if not path:
        return {"error": "no positions file", "series": []}

    _, _, rows = parse_positions_csv(str(path))

    # Build (yahoo_symbol, qty) pairs for securities with known qty
    holdings: list[tuple[str, float]] = []
    cash_value = 0.0
    for r in rows:
        sym = r.get("Symbol", "").strip()
        qty = _parse_float(r.get("Qty (Quantity)", r.get("Qty", "")))
        if not sym or sym == "Positions Total":
            continue
        if qty is None:
            # Cash row — treat as fixed value
            mv = _parse_float(r.get("Mkt Val (Market Value)", ""))
            if mv:
                cash_value += mv
            continue
        yahoo_sym = sym.replace("/", "-")
        holdings.append((yahoo_sym, qty))

    if not holdings:
        return {"series": []}

    period_map = {"1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y", "2y": "2y"}
    yf_period = period_map.get(period, "1y")

    syms = [s for s, _ in holdings]
    qty_map = {s: q for s, q in holdings}

    try:
        data = yf.download(syms, period=yf_period, auto_adjust=True, progress=False)
        if data.empty:
            return {"series": [], "note": "No price data returned"}
        close = data["Close"] if "Close" in data.columns else data
        # If single symbol, wrap in DataFrame
        if hasattr(close, "squeeze") and len(syms) == 1:
            close = close.to_frame(syms[0])
    except Exception as e:
        return {"error": str(e), "series": []}

    series = []
    for date, price_row in close.iterrows():
        daily_mv = cash_value
        for sym in syms:
            price = price_row.get(sym) if hasattr(price_row, "get") else getattr(price_row, sym, None)
            if price is not None and not (isinstance(price, float) and price != price):  # NaN check
                daily_mv += qty_map[sym] * float(price)
        series.append({
            "date": str(date)[:10],
            "value": round(daily_mv, 2),
        })

    # Also fetch SPY for benchmark
    benchmark = []
    try:
        spy = yf.download("SPY", period=yf_period, auto_adjust=True, progress=False)
        if not spy.empty:
            spy_close = spy["Close"]
            first_val = float(spy_close.iloc[0])
            first_portfolio = series[0]["value"] if series else 1.0
            for date, price in spy_close.items():
                # Normalize SPY to same starting portfolio value
                benchmark.append({
                    "date": str(date)[:10],
                    "value": round(float(price) / first_val * first_portfolio, 2),
                })
    except Exception:
        pass

    return {
        "series": series,
        "benchmark_spy": benchmark,
        "note": "Current holdings × historical prices. Not actual historical portfolio value.",
        "period": period,
    }
