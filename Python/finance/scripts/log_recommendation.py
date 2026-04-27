#!/usr/bin/env python3
"""
Log a portfolio recommendation to recommendations.jsonl.

Usage:
    python3 scripts/log_recommendation.py \
        --symbol MU --action buy --conviction strong_buy \
        --model "anthropic/claude-opus-4-7" --method monte_carlo_backend \
        --rr 10.45 --sharpe 3.15 --pgain 92.1 --ann-ret 184.6 \
        --rationale "Highest R/R in portfolio" \
        [--mc-snapshot /path/to/snapshot.json]

Can also be imported and used as a library:
    from scripts.log_recommendation import log_rec
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional


REC_DIR = os.path.expanduser(
    "~/.openclaw/workspace/Data/Private/finance/recommendations"
)
REC_FILE = os.path.join(REC_DIR, "recommendations.jsonl")

VALID_ACTIONS = {"buy", "sell", "hold", "trim", "add"}
VALID_CONVICTIONS = {"strong_buy", "buy", "hold", "weak_hold", "trim", "sell"}


def log_rec(
    symbol: str,
    action: str,
    conviction: str,
    source_model: str = "unknown",
    method: str = "qualitative",
    risk_reward_score: float | None = None,
    annual_return_pct: float | None = None,
    sharpe_like: float | None = None,
    probability_gain_pct: float | None = None,
    expected_return_pct: float | None = None,
    p05_pct: float | None = None,
    p50_pct: float | None = None,
    p95_pct: float | None = None,
    var_5: float | None = None,
    garch_vol: float | None = None,
    implied_vol_annual: float | None = None,
    current_market_value: float | None = None,
    current_price: float | None = None,
    portfolio_weight_pct: float | None = None,
    suggested_action_size: str | None = None,
    suggested_price_target: float | None = None,
    rationale: str = "",
    mc_snapshot_file: str | None = None,
    mc_params: dict | None = None,
    agent: str = "openclaw-main",
) -> str:
    """Append a recommendation to the JSONL log. Returns the rec ID."""
    now = datetime.now().astimezone()
    ts = now.strftime("%Y%m%d_%H%M%S")
    rec_id = f"rec_{ts}_{symbol}"

    metrics = {}
    for k, v in [
        ("risk_reward_score", risk_reward_score),
        ("annual_return_pct", annual_return_pct),
        ("sharpe_like", sharpe_like),
        ("probability_gain_pct", probability_gain_pct),
        ("expected_return_pct", expected_return_pct),
        ("p05_pct", p05_pct),
        ("p50_pct", p50_pct),
        ("p95_pct", p95_pct),
        ("var_5", var_5),
        ("garch_vol", garch_vol),
        ("implied_vol_annual", implied_vol_annual),
    ]:
        if v is not None:
            metrics[k] = v

    position_context = {}
    for k, v in [
        ("current_market_value", current_market_value),
        ("current_price", current_price),
        ("portfolio_weight_pct", portfolio_weight_pct),
        ("suggested_action_size", suggested_action_size),
        ("suggested_price_target", suggested_price_target),
    ]:
        if v is not None:
            position_context[k] = v

    rec = {
        "id": rec_id,
        "timestamp": now.isoformat(),
        "symbol": symbol,
        "action": action,
        "conviction": conviction,
        "source": {
            "agent": agent,
            "model": source_model,
            "method": method,
        },
        "metrics": metrics,
        "position_context": position_context if position_context else None,
        "rationale": rationale,
        "mc_snapshot_file": mc_snapshot_file,
    }

    if mc_params:
        rec["source"]["mc_params"] = mc_params

    os.makedirs(os.path.dirname(REC_FILE), exist_ok=True)
    with open(REC_FILE, "a") as f:
        f.write(json.dumps(rec) + "\n")

    return rec_id


def log_batch_from_mc(
    mc_data: dict,
    recs: list[dict],
    source_model: str = "unknown",
    agent: str = "openclaw-main",
    mc_snapshot_file: str | None = None,
) -> list[str]:
    """
    Log a batch of recommendations from MC data.

    recs: list of dicts with keys: symbol, action, conviction, rationale
    mc_data: the full MC JSON (with position_details and enhancements)
    """
    pds = {p["symbol"]: p for p in mc_data.get("position_details", [])}
    enhs = mc_data.get("enhancements", {}).get("per_symbol", {})

    ids = []
    for r in recs:
        sym = r["symbol"]
        p = pds.get(sym, {})
        e = enhs.get(sym, {})

        rec_id = log_rec(
            symbol=sym,
            action=r["action"],
            conviction=r["conviction"],
            source_model=source_model,
            method="monte_carlo_backend",
            risk_reward_score=p.get("risk_reward_score"),
            annual_return_pct=p.get("annual_return_pct"),
            sharpe_like=p.get("sharpe_like"),
            probability_gain_pct=p.get("probability_gain_pct"),
            expected_return_pct=p.get("expected_return_pct"),
            p05_pct=(
                (p["p05"] / p["last_price"] - 1) * 100
                if p.get("p05") and p.get("last_price")
                else None
            ),
            p50_pct=(
                (p["p50"] / p["last_price"] - 1) * 100
                if p.get("p50") and p.get("last_price")
                else None
            ),
            p95_pct=(
                (p["p95"] / p["last_price"] - 1) * 100
                if p.get("p95") and p.get("last_price")
                else None
            ),
            var_5=p.get("var_5"),
            garch_vol=float(e.get("garch_vol", 0)) if e.get("garch_vol") else None,
            implied_vol_annual=(
                float(e.get("implied_vol_annual", 0))
                if e.get("implied_vol_annual")
                else None
            ),
            current_market_value=p.get("market_value"),
            current_price=p.get("last_price"),
            rationale=r.get("rationale", ""),
            mc_snapshot_file=mc_snapshot_file,
            agent=agent,
        )
        ids.append(rec_id)

    return ids


def main():
    parser = argparse.ArgumentParser(description="Log a portfolio recommendation")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--action", required=True, choices=VALID_ACTIONS)
    parser.add_argument("--conviction", required=True, choices=VALID_CONVICTIONS)
    parser.add_argument("--model", default="unknown")
    parser.add_argument("--method", default="qualitative")
    parser.add_argument("--agent", default="openclaw-main")
    parser.add_argument("--rr", type=float, help="Risk/Reward score")
    parser.add_argument("--sharpe", type=float)
    parser.add_argument("--pgain", type=float, help="P(Gain) percentage")
    parser.add_argument("--ann-ret", type=float, help="Annualized return %")
    parser.add_argument("--rationale", default="")
    parser.add_argument("--mc-snapshot", help="Path to MC snapshot JSON")
    args = parser.parse_args()

    rec_id = log_rec(
        symbol=args.symbol,
        action=args.action,
        conviction=args.conviction,
        source_model=args.model,
        method=args.method,
        risk_reward_score=args.rr,
        sharpe_like=args.sharpe,
        probability_gain_pct=args.pgain,
        annual_return_pct=args.ann_ret,
        rationale=args.rationale,
        mc_snapshot_file=args.mc_snapshot,
        agent=args.agent,
    )
    print(f"Logged: {rec_id}")


if __name__ == "__main__":
    main()
