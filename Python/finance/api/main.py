"""Local Schwab portfolio API — binds to 127.0.0.1:8765 only."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .price_fetcher import get_prices
from .schwab_parser import parse_positions_csv, parse_rgl_csv, parse_transactions_csv

BASE_DIR = Path(os.environ.get("SCHWAB_BASE_DIR", "~/.openclaw/workspace/Data/Private/finance/schwab-brokerage")).expanduser()

app = FastAPI(title="Schwab Portfolio API", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
    v = val.replace("$", "").replace("%", "").replace(",", "").strip()
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _filter_by_date(rows: list[dict], date_col: str, from_date: Optional[str], to_date: Optional[str]) -> list[dict]:
    if not from_date and not to_date:
        return rows
    out = []
    for r in rows:
        d = r.get(date_col, "")
        if from_date and d < from_date:
            continue
        if to_date and d > to_date:
            continue
        out.append(r)
    return out


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

    return {"count": len(rows), "rows": rows}


@app.get("/portfolio/history")
def portfolio_history():
    """All position snapshots over time."""
    snapshots = []
    for p in _all_positions_files():
        snapshot_date, _, rows = parse_positions_csv(str(p))
        total_mv = sum(_parse_float(r.get("Mkt Val (Market Value)", r.get("Mkt Val", ""))) or 0 for r in rows)
        total_cb = sum(_parse_float(r.get("Cost Basis", "")) or 0 for r in rows)
        snapshots.append({
            "date": snapshot_date,
            "total_market_value": total_mv,
            "total_cost_basis": total_cb,
            "unrealized_gl": total_mv - total_cb,
            "position_count": len(rows),
            "positions": [
                {
                    "symbol": r.get("Symbol", ""),
                    "qty": _parse_float(r.get("Qty (Quantity)", r.get("Qty", ""))),
                    "market_value": _parse_float(r.get("Mkt Val (Market Value)", r.get("Mkt Val", ""))),
                    "cost_basis": _parse_float(r.get("Cost Basis", "")),
                }
                for r in rows
            ],
        })
    return {"snapshots": snapshots}
