#!/usr/bin/env python3
"""
Match recommendations against actual Schwab transactions.

Reads recommendations.jsonl and the transactions master CSV,
produces a match report showing which recs were followed, ignored, etc.

Usage:
    python3 scripts/match_recommendations.py [--days-window 7] [--output report.json]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional


REC_FILE = os.path.expanduser(
    "~/.openclaw/workspace/Data/Private/finance/recommendations/recommendations.jsonl"
)
TXN_FILE = os.path.expanduser(
    "~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/transactions/Joint_Tenant_Transactions_MASTER.csv"
)
REPORT_DIR = os.path.expanduser(
    "~/.openclaw/workspace/Data/Private/finance/recommendations/reports"
)


def parse_txn_date(date_str: str) -> datetime | None:
    """Parse Schwab transaction date formats."""
    # Handle 'MM/DD/YYYY' and 'MM/DD/YYYY as of MM/DD/YYYY'
    date_str = date_str.split(" as of ")[0].strip()
    try:
        return datetime.strptime(date_str, "%m/%d/%Y")
    except ValueError:
        return None


def load_recommendations() -> list[dict]:
    """Load all recommendations from JSONL."""
    recs = []
    if not os.path.exists(REC_FILE):
        return recs
    with open(REC_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def load_transactions() -> list[dict]:
    """Load buy/sell transactions from master CSV."""
    txns = []
    if not os.path.exists(TXN_FILE):
        print(f"Warning: {TXN_FILE} not found")
        return txns
    with open(TXN_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Action") in ("Buy", "Sell"):
                parsed_date = parse_txn_date(row.get("Date", ""))
                if parsed_date:
                    txns.append(
                        {
                            "date": parsed_date,
                            "action": row["Action"],
                            "symbol": row.get("Symbol", ""),
                            "quantity": row.get("Quantity", ""),
                            "price": row.get("Price", ""),
                            "amount": row.get("Amount", ""),
                        }
                    )
    return txns


def directions_agree(rec_action: str, txn_action: str) -> bool:
    """Check if rec direction matches trade direction."""
    buy_actions = {"buy", "add"}
    sell_actions = {"sell", "trim"}
    if rec_action in buy_actions and txn_action == "Buy":
        return True
    if rec_action in sell_actions and txn_action == "Sell":
        return True
    return False


def directions_conflict(rec_action: str, txn_action: str) -> bool:
    """Check if rec direction conflicts with trade direction."""
    buy_actions = {"buy", "add"}
    sell_actions = {"sell", "trim"}
    if rec_action in buy_actions and txn_action == "Sell":
        return True
    if rec_action in sell_actions and txn_action == "Buy":
        return True
    return False


def match_recs_to_txns(
    recs: list[dict], txns: list[dict], days_window: int = 7
) -> dict:
    """
    Match each recommendation to transactions.

    Returns a dict with:
      - matches: list of matched rec->trade pairs
      - unmatched_recs: recs with no matching trades
      - discretionary_trades: trades with no matching rec
      - summary stats
    """
    # Index transactions by (symbol, date)
    txn_by_symbol = defaultdict(list)
    for t in txns:
        txn_by_symbol[t["symbol"]].append(t)

    matches = []
    unmatched_recs = []
    matched_txn_indices = set()

    for rec in recs:
        sym = rec["symbol"]
        rec_ts = datetime.fromisoformat(rec["timestamp"])
        rec_date = rec_ts.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        rec_action = rec["action"]

        symbol_txns = txn_by_symbol.get(sym, [])

        best_match = None
        best_quality = None
        best_idx = None

        for i, t in enumerate(symbol_txns):
            txn_key = (sym, t["date"].isoformat(), t["price"], id(t))
            if txn_key in matched_txn_indices:
                continue

            delta_days = (t["date"] - rec_date).days

            if delta_days < 0 or delta_days > days_window:
                continue

            if directions_agree(rec_action, t["action"]):
                if delta_days == 0:
                    quality = "same_day"
                elif delta_days <= 3:
                    quality = "within_3_days"
                else:
                    quality = "within_7_days"

                # Prefer closest match
                if best_match is None or delta_days < (best_match["date"] - rec_date).days:
                    best_match = t
                    best_quality = quality
                    best_idx = txn_key
            elif directions_conflict(rec_action, t["action"]) and delta_days <= 3:
                if best_match is None:
                    best_match = t
                    best_quality = "contrary"
                    best_idx = txn_key

        if best_match:
            matched_txn_indices.add(best_idx)

            attribution = {
                "same_day": "followed",
                "within_3_days": "partially_followed",
                "within_7_days": "partially_followed",
                "contrary": "contrary",
            }[best_quality]

            matches.append(
                {
                    "recommendation_id": rec["id"],
                    "symbol": sym,
                    "rec_action": rec_action,
                    "rec_conviction": rec.get("conviction"),
                    "rec_timestamp": rec["timestamp"],
                    "rec_rr": rec.get("metrics", {}).get("risk_reward_score"),
                    "matched_trade": {
                        "date": best_match["date"].strftime("%Y-%m-%d"),
                        "action": best_match["action"],
                        "quantity": best_match["quantity"],
                        "price": best_match["price"],
                        "amount": best_match["amount"],
                    },
                    "attribution": attribution,
                    "match_quality": best_quality,
                }
            )
        else:
            unmatched_recs.append(
                {
                    "recommendation_id": rec["id"],
                    "symbol": sym,
                    "rec_action": rec_action,
                    "rec_conviction": rec.get("conviction"),
                    "rec_timestamp": rec["timestamp"],
                    "rec_rr": rec.get("metrics", {}).get("risk_reward_score"),
                    "attribution": "ignored",
                }
            )

    # Find discretionary trades (no matching rec)
    # Only look at trades in the date range of recommendations
    if recs:
        first_rec = min(
            datetime.fromisoformat(r["timestamp"]).replace(tzinfo=None) for r in recs
        )
        last_rec = max(
            datetime.fromisoformat(r["timestamp"]).replace(tzinfo=None) for r in recs
        )

        discretionary = []
        for t in txns:
            if t["date"] < first_rec.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) or t["date"] > last_rec + timedelta(days=7):
                continue

            txn_key = (t["symbol"], t["date"].isoformat(), t["price"], id(t))
            if txn_key not in matched_txn_indices:
                discretionary.append(
                    {
                        "symbol": t["symbol"],
                        "date": t["date"].strftime("%Y-%m-%d"),
                        "action": t["action"],
                        "quantity": t["quantity"],
                        "price": t["price"],
                        "amount": t["amount"],
                        "attribution": "discretionary",
                    }
                )
    else:
        discretionary = []

    # Summary stats
    total_recs = len(recs)
    followed = sum(1 for m in matches if m["attribution"] == "followed")
    partial = sum(1 for m in matches if m["attribution"] == "partially_followed")
    contrary = sum(1 for m in matches if m["attribution"] == "contrary")
    ignored = len(unmatched_recs)

    summary = {
        "total_recommendations": total_recs,
        "followed": followed,
        "partially_followed": partial,
        "contrary": contrary,
        "ignored": ignored,
        "discretionary_trades": len(discretionary),
        "follow_rate_pct": round(
            (followed + partial) / total_recs * 100, 1
        )
        if total_recs > 0
        else 0,
    }

    return {
        "summary": summary,
        "matches": matches,
        "unmatched_recs": unmatched_recs,
        "discretionary_trades": discretionary[:50],  # Cap output size
    }


def main():
    parser = argparse.ArgumentParser(
        description="Match recommendations to transactions"
    )
    parser.add_argument("--days-window", type=int, default=7)
    parser.add_argument("--output", help="Output file (default: stdout)")
    args = parser.parse_args()

    recs = load_recommendations()
    if not recs:
        print("No recommendations found in", REC_FILE)
        return

    txns = load_transactions()
    print(f"Loaded {len(recs)} recommendations, {len(txns)} buy/sell transactions")

    result = match_recs_to_txns(recs, txns, days_window=args.days_window)

    print(f"\n=== Match Summary ===")
    s = result["summary"]
    print(f"Total recs:            {s['total_recommendations']}")
    print(f"Followed (same day):   {s['followed']}")
    print(f"Partially followed:    {s['partially_followed']}")
    print(f"Contrary:              {s['contrary']}")
    print(f"Ignored:               {s['ignored']}")
    print(f"Discretionary trades:  {s['discretionary_trades']}")
    print(f"Follow rate:           {s['follow_rate_pct']}%")

    if args.output:
        output_path = args.output
    else:
        os.makedirs(REPORT_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        output_path = os.path.join(REPORT_DIR, f"match_{today}.json")

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nFull report: {output_path}")


if __name__ == "__main__":
    main()
