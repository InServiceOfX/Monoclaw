#!/usr/bin/env python3
"""Run Monte Carlo, DOI, and earnings analysis on current Schwab portfolio.

Outputs structured JSON to stdout and optionally to a file. Designed to be
run by an LLM agent that synthesizes the results into actionable recommendations.

Usage:
    cd ~/.openclaw/workspace/repos/Monoclaw/Python/finance && uv run python schwab_portfolio_outlook.py

    # Save to file:
    cd ~/.openclaw/workspace/repos/Monoclaw/Python/finance && uv run python schwab_portfolio_outlook.py --out /tmp/outlook.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.monte_carlo import Holding, run_monte_carlo
from api.doi import DOIInputs, compute_doi
from api.earnings_impact import analyze_earnings_impact

POS_DIR = Path("~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/positions").expanduser()
SKIP_SYMBOLS = {"", "Account Total", "Cash & Cash Investments", "Positions Total", "Symbol"}
TOP_N_EARNINGS = 40


def parse_positions() -> tuple[list[dict], float]:
    snapshots = sorted(
        (p for p in POS_DIR.glob("*.csv") if "master" not in p.name.lower()),
        key=lambda p: p.stem,
        reverse=True,
    )
    if not snapshots:
        print("ERROR: No position snapshots found", file=sys.stderr)
        sys.exit(1)

    pos_file = snapshots[0]
    print(f"Using: {pos_file.name}", file=sys.stderr)

    holdings = []
    cash_value = 0.0

    with open(pos_file) as f:
        lines = f.readlines()

    reader = csv.reader(lines[2:])
    for r in reader:
        if len(r) < 8:
            continue
        sym = r[0].strip()
        if sym in SKIP_SYMBOLS:
            if sym == "Cash & Cash Investments":
                try:
                    cash_value = float(r[7].replace("$", "").replace(",", "").strip())
                except ValueError:
                    pass
            continue

        mktval_str = r[7].replace("$", "").replace(",", "").strip()
        price_str = r[3].replace("$", "").replace(",", "").strip()
        desc = r[1].strip() if len(r) > 1 else ""
        costbasis_str = r[10].replace("$", "").replace(",", "").strip() if len(r) > 10 else ""
        gainpct_str = r[12].replace("%", "").strip() if len(r) > 12 else "0"
        pct_str = r[16].replace("%", "").strip() if len(r) > 16 else ""
        atype = r[17].strip() if len(r) > 17 else ""

        try:
            mv = float(mktval_str)
        except ValueError:
            continue
        if mv <= 0:
            continue

        try:
            price = float(price_str)
        except ValueError:
            price = None
        try:
            gp = float(gainpct_str)
        except ValueError:
            gp = None
        try:
            pct = float(pct_str)
        except ValueError:
            pct = None

        holdings.append({
            "symbol": sym,
            "description": desc,
            "market_value": mv,
            "current_price": price,
            "cost_basis": costbasis_str,
            "gain_pct": gp,
            "pct_of_account": pct,
            "asset_type": atype,
        })

    return holdings, cash_value


def run_all(holdings: list[dict], cash_value: float) -> dict:
    equity_mv = sum(h["market_value"] for h in holdings)
    total_acct = equity_mv + cash_value
    today = date.today().isoformat()

    result: dict = {
        "as_of": today,
        "account": {
            "equity_market_value": round(equity_mv, 2),
            "cash": round(cash_value, 2),
            "total": round(total_acct, 2),
            "cash_pct": round(cash_value / total_acct * 100, 1) if total_acct > 0 else 0,
            "num_positions": len(holdings),
        },
    }

    # --- Monte Carlo (6-month with 3-month midpoint) ---
    print("Running Monte Carlo (6-month, 5000 sims)...", file=sys.stderr)
    t0 = time.time()
    mc_holdings = [Holding(h["symbol"], h["description"], h["market_value"]) for h in holdings]
    mc = run_monte_carlo(mc_holdings, days=126, simulations=5000, period="2y", seed=42)
    elapsed_mc = time.time() - t0
    print(f"  Done in {elapsed_mc:.0f}s", file=sys.stderr)

    mc_summary: dict = {"error": mc.get("error")}
    if not mc.get("error") and mc.get("portfolio"):
        p = mc["portfolio"]
        bands = p.get("bands", [])
        day63 = bands[62] if len(bands) > 62 else {}

        mc_summary = {
            "initial_equity": p.get("initial_value"),
            "three_month": {
                "bear_5th": day63.get("p05"),
                "median": day63.get("p50"),
                "bull_95th": day63.get("p95"),
                "total_acct_median": round((day63.get("p50") or 0) + cash_value, 2),
                "total_acct_bull": round((day63.get("p95") or 0) + cash_value, 2),
            },
            "six_month": {
                "bear_5th": p.get("p05"),
                "p25": p.get("p25"),
                "median": p.get("p50"),
                "p75": p.get("p75"),
                "bull_95th": p.get("p95"),
                "total_acct_median": round((p.get("p50") or 0) + cash_value, 2),
                "total_acct_bull": round((p.get("p95") or 0) + cash_value, 2),
                "prob_gain_pct": p.get("probability_gain_pct"),
                "prob_loss_pct": p.get("probability_loss_pct"),
                "var_5": p.get("var_5"),
                "cvar_5": p.get("cvar_5"),
            },
            "enhancements": {
                "student_t_df": mc.get("enhancements", {}).get("student_t_df"),
                "iv_weight": mc.get("enhancements", {}).get("iv_weight"),
            },
            "history_rows": mc.get("history_rows"),
            "history_range": f"{mc.get('history_start')} to {mc.get('history_end')}",
            "elapsed_seconds": round(elapsed_mc, 1),
        }

        # Top/bottom positions by risk/reward
        details = mc.get("position_details", [])
        mc_summary["top_positions"] = [
            {
                "symbol": d["symbol"],
                "market_value": d.get("market_value"),
                "expected_return_pct": d.get("expected_return_pct"),
                "annual_vol_pct": d.get("annual_vol_pct"),
                "sharpe_like": d.get("sharpe_like"),
                "risk_reward_score": d.get("risk_reward_score"),
            }
            for d in details[:15]
        ]

    result["monte_carlo"] = mc_summary

    # --- DOI ---
    print("Running DOI...", file=sys.stderr)
    t0 = time.time()
    doi_inputs = DOIInputs(
        holdings=[{
            "symbol": h["symbol"],
            "market_value": h["market_value"],
            "current_price": h.get("current_price"),
            "pct_of_account": h.get("pct_of_account"),
        } for h in holdings],
        cash_value=cash_value,
        total_account_value=total_acct,
    )
    doi = compute_doi(doi_inputs)
    elapsed_doi = time.time() - t0
    print(f"  Done in {elapsed_doi:.0f}s", file=sys.stderr)

    deploy = [t for t in doi.get("tickers", []) if t["action"] == "deploy"]
    trim = [t for t in doi.get("tickers", []) if t["action"] == "trim"]
    hold = [t for t in doi.get("tickers", []) if t["action"] == "hold"]

    result["doi"] = {
        "portfolio_doi": doi.get("portfolio_doi"),
        "cash_deficit_warning": doi.get("cash_deficit_warning"),
        "indices": doi.get("indices"),
        "signal_counts": {"deploy": len(deploy), "hold": len(hold), "trim": len(trim)},
        "deploy_tickers": sorted(
            [{"symbol": t["symbol"], "doi": t.get("doi"), "conviction": t.get("conviction_score")}
             for t in deploy],
            key=lambda x: x.get("doi") or -999, reverse=True,
        )[:10],
        "trim_tickers": sorted(
            [{"symbol": t["symbol"], "doi": t.get("doi")} for t in trim],
            key=lambda x: x.get("doi") or 999,
        )[:10],
        "elapsed_seconds": round(elapsed_doi, 1),
    }

    # --- Earnings Impact (top holdings only) ---
    print(f"Running earnings impact (top {TOP_N_EARNINGS} holdings)...", file=sys.stderr)
    t0 = time.time()
    top_holdings = sorted(holdings, key=lambda h: h["market_value"], reverse=True)[:TOP_N_EARNINGS]
    top_syms = [h["symbol"] for h in top_holdings]
    descs = {h["symbol"]: h["description"] for h in top_holdings}
    atypes = {h["symbol"]: h.get("asset_type", "") for h in top_holdings}
    earnings = analyze_earnings_impact(top_syms, descriptions=descs, asset_types=atypes)
    elapsed_earn = time.time() - t0
    print(f"  Done in {elapsed_earn:.0f}s", file=sys.stderr)

    result["earnings"] = {
        "upcoming_alerts": earnings.get("upcoming_alerts", []),
        "classifications": [
            {
                "symbol": p["symbol"],
                "signal": p.get("classification", {}).get("signal"),
                "reason": p.get("classification", {}).get("reason"),
                "next_earnings_date": p.get("next_earnings_date"),
                "days_until_earnings": p.get("days_until_earnings"),
                "beat_rate_pct": p.get("stats", {}).get("beat_rate_pct"),
            }
            for p in earnings.get("positions", [])
            if p.get("status") == "ok"
        ],
        "elapsed_seconds": round(elapsed_earn, 1),
    }

    # --- Winners / Losers summary ---
    winners = sorted(
        [h for h in holdings if (h.get("gain_pct") or 0) > 10],
        key=lambda h: h.get("gain_pct") or 0, reverse=True,
    )[:15]
    losers = sorted(
        [h for h in holdings if (h.get("gain_pct") or 0) < -10],
        key=lambda h: h.get("gain_pct") or 0,
    )[:15]
    result["winners"] = [
        {"symbol": h["symbol"], "market_value": h["market_value"], "gain_pct": h.get("gain_pct")}
        for h in winners
    ]
    result["losers"] = [
        {"symbol": h["symbol"], "market_value": h["market_value"], "gain_pct": h.get("gain_pct")}
        for h in losers
    ]

    return result


def main():
    parser = argparse.ArgumentParser(description="Schwab portfolio outlook analysis")
    parser.add_argument("--out", type=Path, help="Write JSON output to file")
    args = parser.parse_args()

    holdings, cash_value = parse_positions()
    result = run_all(holdings, cash_value)

    output = json.dumps(result, indent=2, default=str)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output)
        print(f"\nOutput written to {args.out}", file=sys.stderr)

    print(output)


if __name__ == "__main__":
    main()
