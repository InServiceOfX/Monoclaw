"""Local Schwab portfolio API — binds to 127.0.0.1:8765 only."""
from __future__ import annotations

import json
import os
import csv
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .price_fetcher import get_prices
from .schwab_parser import parse_positions_csv, parse_rgl_csv, parse_transactions_csv
from .monte_carlo import Holding, run_monte_carlo
from .doi import DOIInputs, DOIWeights, compute_doi
from . import price_history

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


def _parse_single_balance_file(path: Path) -> Optional[dict]:
    """Parse one Schwab balance key-value CSV into a normalised row dict."""
    try:
        content = path.read_text(encoding="utf-8-sig")
    except Exception:
        return None
    lines = content.splitlines()
    if not lines:
        return None

    # Header: "Balances for account XXXX as of MM/DD/YYYY HH:MM AM/PM ET"
    header = lines[0].strip().strip('"')
    snapshot_date = ""
    snapshot_time = ""
    m = re.search(r"as of (\d{1,2}/\d{1,2}/\d{4}) (\d{1,2}:\d{2} [AP]M)", header, re.IGNORECASE)
    if m:
        snapshot_date = m.group(1)
        snapshot_time = m.group(2)

    # State-tracked key-value extraction (handles repeated keys in subsections)
    section = ""
    kv: dict[str, str] = {}
    for line in lines[1:]:
        line = line.strip()
        if not line:
            section = ""
            continue
        try:
            parts = next(csv.reader([line]))
        except StopIteration:
            continue
        key = parts[0].strip().strip('"') if parts else ""
        val = parts[1].strip().strip('"') if len(parts) > 1 else ""
        if not key:
            continue
        if not val:
            section = key
            continue
        # Disambiguate repeated "Cash & Cash Investments" by subsection
        full_key = key
        if section == "To Trade" and key == "Cash & Cash Investments":
            full_key = "Available to Trade (Cash)"
        elif section == "To Withdraw" and key == "Cash & Cash Investments":
            full_key = "Available to Withdraw"
        if full_key not in kv:
            kv[full_key] = val

    iso = _date_iso(snapshot_date)
    return {
        "SnapshotDate": snapshot_date,
        "SnapshotTime": snapshot_time,
        "Account Value": kv.get("Account Value", ""),
        "Day Change": kv.get("Day Change", ""),
        "Day Change %": kv.get("Day Change %", ""),
        "Cash & Cash Investments": kv.get("Cash & Cash Investments", ""),
        "Market Value (Securities)": kv.get("Market Value", ""),
        "Available to Trade (Cash)": kv.get("Available to Trade (Cash)", ""),
        "Settled Funds": kv.get("Settled Funds", ""),
        "Available to Withdraw": kv.get("Available to Withdraw", ""),
        "snapshot_date_iso": iso,
        "account_value": _parse_money(kv.get("Account Value", "")),
        "day_change": _parse_money(kv.get("Day Change", "")),
        "day_change_pct": _parse_money(kv.get("Day Change %", "")),
        "cash": _parse_money(kv.get("Cash & Cash Investments", "")),
        "securities_value": _parse_money(kv.get("Market Value", "")),
        "available_to_trade": _parse_money(kv.get("Available to Trade (Cash)", "")),
        "settled_funds": _parse_money(kv.get("Settled Funds", "")),
        "available_to_withdraw": _parse_money(kv.get("Available to Withdraw", "")),
    }


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


def _portfolio_cash_totals() -> tuple[float, float]:
    bal_data = balances()
    latest = bal_data.get("latest") if isinstance(bal_data, dict) else None
    if latest:
        cash_value = _parse_float(latest.get("Available to Trade (Cash)", "")) or latest.get("available_to_trade")
        total_account_value = _parse_float(latest.get("Account Value", "")) or latest.get("account_value")
        if cash_value is not None and total_account_value:
            return float(cash_value), float(total_account_value)

    snapshot_date, rows = _current_positions_from_csv()
    del snapshot_date
    positions = [r for r in rows if _is_security_position(r)]
    total_mv = sum(_position_market_value(r) for r in positions)
    cash_rows = [r for r in rows if not _is_security_position(r)]
    cash = sum(_position_market_value(r) for r in cash_rows if _position_market_value(r) > 0)
    return cash, total_mv + cash


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
    bal_dir = BASE_DIR / "balances"
    master = bal_dir / "master-balances.csv"
    rows: list[dict] = []

    if master.exists():
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
    elif bal_dir.exists():
        # No master — read individual Schwab balance CSV files directly
        for p in sorted(bal_dir.glob("*.csv")) + sorted(bal_dir.glob("*.CSV")):
            if "master" in p.name.lower():
                continue
            row = _parse_single_balance_file(p)
            if row and row.get("account_value") is not None:
                rows.append(row)

    # Deduplicate by snapshot_date_iso, keeping latest file per date
    seen: dict[str, dict] = {}
    for r in rows:
        key = r.get("snapshot_date_iso") or r.get("SnapshotDate") or ""
        seen[key] = r
    rows = sorted(seen.values(), key=lambda r: r.get("snapshot_date_iso") or "")
    return {"count": len(rows), "rows": rows, "latest": rows[-1] if rows else None}


@app.get("/transactions/actions")
def transaction_actions():
    """Return all unique Action values seen in the transactions data."""
    tx_dir = BASE_DIR / "transactions"
    master = tx_dir / "Joint_Tenant_Transactions_MASTER.csv"
    if master.exists():
        _, rows = parse_transactions_csv(str(master))
    else:
        rows = []
        for p in sorted(tx_dir.glob("*.csv")):
            if "MASTER" in p.name:
                continue
            _, r = parse_transactions_csv(str(p))
            rows.extend(r)
    actions = sorted({r.get("Action", "").strip() for r in rows if r.get("Action", "").strip()})
    return {"actions": actions}


@app.get("/doi/snapshot")
def doi_snapshot():
    pos = positions_current()
    positions = pos.get("positions", [])
    holdings = [
        {
            "symbol": p.get("symbol", ""),
            "description": p.get("description", ""),
            "market_value": p.get("market_value"),
            "current_price": p.get("current_price"),
            "pct_of_account": p.get("pct_of_account"),
            "asset_type": p.get("asset_type", ""),
        }
        for p in positions
        if p.get("symbol") and p.get("symbol") != "Positions Total" and p.get("qty") is not None
    ]
    cash_value, total_account_value = _portfolio_cash_totals()
    inputs = DOIInputs(
        holdings=holdings,
        cash_value=cash_value,
        total_account_value=total_account_value,
    )
    return compute_doi(inputs, DOIWeights())


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


# ---------------------------------------------------------------------------
# Recommendations report
# ---------------------------------------------------------------------------

REC_FILE = Path("~/.openclaw/workspace/Data/Private/finance/recommendations/recommendations.jsonl").expanduser()
REC_REPORTS_DIR = Path("~/.openclaw/workspace/Data/Private/finance/recommendations/reports").expanduser()


def _latest_report(prefix: str) -> Optional[dict]:
    """Load the most recent report file matching reports/{prefix}_*.json."""
    if not REC_REPORTS_DIR.exists():
        return None
    files = sorted(REC_REPORTS_DIR.glob(f"{prefix}_*.json"))
    if not files:
        return None
    with open(files[-1]) as f:
        return json.load(f)


@app.get("/recommendations/report")
def recommendations_report(days: int = Query(default=90, ge=1, le=3650)):
    """
    Returns recommendations with match attribution and forward-return performance.
    Joins recommendations.jsonl + latest match_*.json + latest performance_*.json.
    """
    if not REC_FILE.exists():
        return {"recommendations": [], "summary": {}, "generated_at": datetime.now().isoformat()}

    cutoff = datetime.now() - timedelta(days=days)

    recs: list[dict] = []
    with open(REC_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                ts = datetime.fromisoformat(rec["timestamp"])
                if ts.replace(tzinfo=None) >= cutoff:
                    recs.append(rec)
            except Exception:
                continue

    # Build lookup tables from latest reports
    match_report = _latest_report("match")
    perf_report = _latest_report("performance")

    attribution_by_id: dict[str, str] = {}
    matched_trade_by_id: dict[str, dict] = {}
    if match_report:
        for m in match_report.get("matches", []):
            rid = m.get("recommendation_id")
            if rid:
                attribution_by_id[rid] = m.get("attribution", "unknown")
                matched_trade_by_id[rid] = m.get("matched_trade", {})
        for u in match_report.get("unmatched_recs", []):
            rid = u.get("recommendation_id")
            if rid:
                attribution_by_id[rid] = "ignored"

    perf_by_id: dict[str, dict] = {}
    if perf_report:
        for p in perf_report.get("results", []):
            rid = p.get("recommendation_id")
            if rid:
                perf_by_id[rid] = p

    # Combine
    combined = []
    for rec in recs:
        rid = rec["id"]
        perf = perf_by_id.get(rid, {})
        combined.append({
            "id": rid,
            "symbol": rec["symbol"],
            "action": rec["action"],
            "conviction": rec.get("conviction"),
            "timestamp": rec["timestamp"],
            "risk_reward_score": rec.get("metrics", {}).get("risk_reward_score"),
            "expected_return": rec.get("metrics", {}).get("expected_return"),
            "prob_gain": rec.get("metrics", {}).get("prob_gain"),
            "attribution": attribution_by_id.get(rid, "unknown"),
            "matched_trade": matched_trade_by_id.get(rid),
            "forward_returns": perf.get("forward_returns"),
            "spy_alpha": perf.get("spy_alpha"),
        })

    # Summary stats
    by_attribution: dict[str, int] = {}
    by_conviction: dict[str, int] = {}
    for r in combined:
        attr = r["attribution"]
        by_attribution[attr] = by_attribution.get(attr, 0) + 1
        conv = r["conviction"] or "unknown"
        by_conviction[conv] = by_conviction.get(conv, 0) + 1

    total = len(combined)
    followed = by_attribution.get("followed", 0)
    partial = by_attribution.get("partially_followed", 0)

    summary = {
        "total": total,
        "days_lookback": days,
        "by_attribution": by_attribution,
        "by_conviction": by_conviction,
        "follow_rate_pct": round((followed + partial) / total * 100, 1) if total > 0 else 0,
        "match_report_date": match_report.get("generated_at") if match_report else None,
        "perf_report_date": perf_report.get("generated_at") if perf_report else None,
    }

    return {
        "recommendations": combined,
        "summary": summary,
        "generated_at": datetime.now().isoformat(),
    }


# ── Transaction Grading (Phase 4 + Per-Symbol) ────────────────────────────────────────────

from .price_history import calculate_sell_quality

_SELL_SCORE_CACHE_TTL = 15 * 60
_SELL_SCORE_CACHE: dict[tuple[str, str], tuple[float, dict]] = {}
_GRADING_MAX_CANDIDATES = 1000
_GRADING_MATURE_DAYS = 35


def _load_transaction_rows() -> list[dict]:
    tx_dir = BASE_DIR / "transactions"
    preferred = [
        tx_dir / "Joint_Tenant_Transactions_MASTER.csv",
        tx_dir / "master-transactions.csv",
    ]
    for master in preferred:
        if master.exists():
            _, rows = parse_transactions_csv(str(master))
            return rows

    rows: list[dict] = []
    for p in sorted(tx_dir.glob("*.csv")):
        if "MASTER" in p.name or p.name.startswith("master-"):
            continue
        _, parsed = parse_transactions_csv(str(p))
        rows.extend(parsed)
    return rows


def _sell_rows(symbol: Optional[str] = None) -> list[dict]:
    rows = []
    for row in _load_transaction_rows():
        if row.get("Action", "").strip().lower() != "sell":
            continue
        sym = row.get("Symbol", "").strip()
        if not sym:
            continue
        if symbol and sym.upper() != symbol.upper():
            continue
        rows.append(row)
    rows.sort(key=lambda r: _parse_schwab_date(r.get("Date", "")) or date.min, reverse=True)
    return rows


def _cached_sell_quality(sym: str, sell_date: str) -> dict:
    key = (sym.upper(), sell_date)
    now = time.time()
    cached = _SELL_SCORE_CACHE.get(key)
    if cached and now - cached[0] < _SELL_SCORE_CACHE_TTL:
        return cached[1]

    score = calculate_sell_quality(sym, sell_date, realized_gain_pct=None)
    _SELL_SCORE_CACHE[key] = (now, score)
    return score


def _is_provisional_sell(row: dict, mature_days: int = _GRADING_MATURE_DAYS) -> bool:
    sell_date = _parse_schwab_date(row.get("Date", ""))
    if sell_date is None:
        return True
    return sell_date > date.today() - timedelta(days=mature_days)


def _graded_sells(
    symbol: Optional[str] = None,
    limit: Optional[int] = None,
    max_candidates: int = _GRADING_MAX_CANDIDATES,
    include_provisional: bool = False,
) -> tuple[list[dict], int, int]:
    candidates = _sell_rows(symbol)
    graded = []
    provisional_skipped = 0
    mature_scanned = 0
    for row in candidates:
        if not include_provisional and _is_provisional_sell(row):
            provisional_skipped += 1
            continue
        mature_scanned += 1
        if mature_scanned > max_candidates:
            break

        sym = row.get("Symbol", "").strip()
        sell_date = row.get("Date", "")
        try:
            score = _cached_sell_quality(sym, sell_date)
        except Exception:
            continue
        if score.get("quality_score") is None:
            continue

        graded.append({
            "date": sell_date,
            "symbol": sym,
            "action": "Sell",
            "quality_score": score["quality_score"],
            "mfe_pct": score["mfe_pct"],
            "max_drawdown_pct": score["max_drawdown_pct"],
            "near_local_peak": score["is_near_local_peak"],
            "provisional": score.get("is_provisional", False),
        })
        if limit is not None and len(graded) >= limit:
            break
    return graded, len(candidates), provisional_skipped


@app.get("/transactions/grading")
def transaction_grading(
    symbol: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    include_provisional: bool = Query(False),
):
    """Return graded sell transactions with timing quality scores (Phase 3)."""
    try:
        graded, total_sells, provisional_skipped = _graded_sells(
            symbol=symbol,
            limit=limit,
            include_provisional=include_provisional,
        )
    except Exception as e:
        return {"error": str(e)}

    return {
        "graded_sells": graded,
        "count": len(graded),
        "total_sells": total_sells,
        "candidates_scanned": min(total_sells, _GRADING_MAX_CANDIDATES),
        "provisional_skipped": provisional_skipped,
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/grading/summary")
def grading_summary():
    """Aggregate Trader Score and key statistics (Phase 4)."""
    try:
        graded, total_sells, provisional_skipped = _graded_sells(max_candidates=300)
    except Exception as e:
        return {"error": str(e)}

    scores = [s["quality_score"] for s in graded]
    peak_sells = sum(1 for s in graded if s.get("near_local_peak"))
    if not scores:
        return {
            "trader_score": None,
            "avg_quality_score": None,
            "total_sells_scored": 0,
            "total_sells": total_sells,
            "candidates_scanned": min(total_sells, 300),
            "provisional_skipped": provisional_skipped,
            "sells_near_local_peak": 0,
            "pct_near_peak": 0,
            "error": "No scored sells found",
            "generated_at": datetime.now().isoformat(),
        }

    import statistics
    median_score = statistics.median(scores)
    avg_score = statistics.mean(scores)

    return {
        "trader_score": round(median_score, 1),
        "avg_quality_score": round(avg_score, 1),
        "total_sells_scored": len(scores),
        "total_sells": total_sells,
        "candidates_scanned": min(total_sells, 300),
        "provisional_skipped": provisional_skipped,
        "sells_near_local_peak": peak_sells,
        "pct_near_peak": round(peak_sells / len(scores) * 100, 1) if scores else 0,
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/grading/top-bottom")
def grading_top_bottom(limit: int = Query(5, ge=3, le=20)):
    """Return best and worst timed sells (Phase 4 enhancement)."""
    scored_sells, total_sells, provisional_skipped = _graded_sells(limit=None, max_candidates=300)

    if not scored_sells:
        return {
            "best_sells": [],
            "worst_sells": [],
            "total_sells": total_sells,
            "candidates_scanned": min(total_sells, 300),
            "provisional_skipped": provisional_skipped,
            "error": "No scored sells",
            "generated_at": datetime.now().isoformat(),
        }

    # Sort by quality score
    scored_sells.sort(key=lambda x: x["quality_score"], reverse=True)

    best = scored_sells[:limit]
    worst = scored_sells[-limit:][::-1]  # worst first

    # Flag "sold too early" = high MFE after sell
    for s in best + worst:
        s["sold_too_early"] = (s.get("mfe_pct") or 0) > 15

    return {
        "best_sells": best,
        "worst_sells": worst,
        "total_sells": total_sells,
        "candidates_scanned": min(total_sells, 300),
        "provisional_skipped": provisional_skipped,
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/grading/by-symbol")
def grading_by_symbol():
    """Per-symbol timing quality summary."""
    from collections import defaultdict
    symbol_data: dict[str, list] = defaultdict(list)

    try:
        scored_sells, total_sells, provisional_skipped = _graded_sells(limit=None, max_candidates=300)
    except Exception as e:
        return {"error": str(e)}

    for sell in scored_sells:
        symbol_data[sell["symbol"]].append(sell)

    results = []
    for sym, scores in symbol_data.items():
        if len(scores) < 2:
            continue  # need at least 2 sells for meaningful stats
        avg_score = sum(s["quality_score"] for s in scores) / len(scores)
        near_peak = sum(1 for s in scores if s.get("near_local_peak")) / len(scores)
        avg_mfe = sum((s.get("mfe_pct") or 0) for s in scores) / len(scores)

        edge = "Strong" if avg_score > 15 else "Weak" if avg_score < -5 else "Neutral"

        results.append({
            "symbol": sym,
            "sells": len(scores),
            "avg_quality_score": round(avg_score, 1),
            "pct_near_peak": round(near_peak * 100, 1),
            "avg_mfe_after_sell": round(avg_mfe, 1),
            "edge": edge,
        })

    results.sort(key=lambda x: x["avg_quality_score"], reverse=True)
    return {
        "by_symbol": results,
        "symbols_analyzed": len(results),
        "total_sells": total_sells,
        "candidates_scanned": min(total_sells, 300),
        "provisional_skipped": provisional_skipped,
        "generated_at": datetime.now().isoformat(),
    }
