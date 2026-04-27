#!/usr/bin/env python3
"""
Compute performance metrics for recommendations.

For each recommendation in recommendations.jsonl:
  1. Determine the reference price (matched trade price, or rec's current_price)
  2. Fetch historical prices at rec_date + 1d, 7d, 30d, 90d
  3. Compute forward returns and SPY-relative alpha
  4. Aggregate by attribution bucket and conviction tier

Usage:
    python3 scripts/compute_performance.py [--output report.json] [--horizons 1,7,30,90]

Requires: yfinance (already installed in the finance venv)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

try:
    import yfinance as yf
except ImportError:
    print("yfinance is required. Run with: cd ~/.openclaw/workspace/repos/Monoclaw/Python/finance && uv run python3 scripts/compute_performance.py")
    sys.exit(1)


REC_DIR = os.path.expanduser(
    "~/.openclaw/workspace/Data/Private/finance/recommendations"
)
REC_FILE = os.path.join(REC_DIR, "recommendations.jsonl")
TXN_FILE = os.path.expanduser(
    "~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/transactions/Joint_Tenant_Transactions_MASTER.csv"
)
REPORT_DIR = os.path.join(REC_DIR, "reports")
PRICE_CACHE = os.path.join(REC_DIR, ".price_cache.json")

BENCHMARK = "SPY"


# ---------- Schwab → Yahoo symbol mapping ----------
SYMBOL_MAP = {
    "BRK/B": "BRK-B",
    "BRK/A": "BRK-A",
}


def yahoo_symbol(s: str) -> Optional[str]:
    s = s.strip()
    if s in SYMBOL_MAP:
        return SYMBOL_MAP[s]
    if not s or s == "--":
        return None
    return s


# ---------- Price lookups ----------
def _load_price_cache() -> dict:
    if os.path.exists(PRICE_CACHE):
        with open(PRICE_CACHE) as f:
            return json.load(f)
    return {}


def _save_price_cache(cache: dict) -> None:
    with open(PRICE_CACHE, "w") as f:
        json.dump(cache, f)


def fetch_prices(symbols: list[str], start: str, end: str, cache: dict) -> dict:
    """
    Fetch daily close prices for symbols between start and end (inclusive).
    Returns: {symbol: {date_str: close_price}}
    Uses on-disk cache to avoid re-fetching.
    """
    out = {}
    to_fetch = []

    for sym in symbols:
        ysym = yahoo_symbol(sym)
        if ysym is None:
            continue
        cache_key = f"{ysym}__{start}__{end}"
        if cache_key in cache:
            out[sym] = cache[cache_key]
        else:
            to_fetch.append((sym, ysym, cache_key))

    if to_fetch:
        # Batch fetch in chunks of 30 to be polite to Yahoo
        chunk_size = 30
        for i in range(0, len(to_fetch), chunk_size):
            chunk = to_fetch[i : i + chunk_size]
            ysyms = [y for _, y, _ in chunk]
            try:
                df = yf.download(
                    ysyms,
                    start=start,
                    end=end,
                    progress=False,
                    auto_adjust=True,
                    threads=True,
                )
                if df is None or df.empty:
                    continue

                # Single ticker case
                if len(ysyms) == 1:
                    if "Close" in df.columns:
                        prices = {
                            d.strftime("%Y-%m-%d"): float(p)
                            for d, p in df["Close"].dropna().items()
                        }
                    else:
                        prices = {}
                    sym, ysym, ck = chunk[0]
                    out[sym] = prices
                    cache[ck] = prices
                else:
                    # Multi-ticker case (multi-level columns)
                    for sym, ysym, ck in chunk:
                        try:
                            close_series = df["Close"][ysym].dropna()
                            prices = {
                                d.strftime("%Y-%m-%d"): float(p)
                                for d, p in close_series.items()
                            }
                        except (KeyError, TypeError):
                            prices = {}
                        out[sym] = prices
                        cache[ck] = prices
                time.sleep(0.5)  # polite delay between chunks
            except Exception as e:
                print(f"  Warning: fetch failed for chunk: {e}")
                for sym, _, ck in chunk:
                    out[sym] = {}
                    cache[ck] = {}

    return out


def find_price_on_or_after(prices: dict, target_date: datetime, max_offset_days: int = 5) -> Optional[tuple[str, float]]:
    """Find the first available close price on or after target_date."""
    for offset in range(max_offset_days + 1):
        d = (target_date + timedelta(days=offset)).strftime("%Y-%m-%d")
        if d in prices:
            return d, prices[d]
    return None


# ---------- Recommendation loading & matching ----------
def load_recommendations() -> list[dict]:
    if not os.path.exists(REC_FILE):
        return []
    recs = []
    with open(REC_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def parse_txn_date(date_str: str) -> Optional[datetime]:
    date_str = date_str.split(" as of ")[0].strip()
    try:
        return datetime.strptime(date_str, "%m/%d/%Y")
    except ValueError:
        return None


def load_transactions() -> list[dict]:
    if not os.path.exists(TXN_FILE):
        return []
    txns = []
    with open(TXN_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Action") in ("Buy", "Sell"):
                d = parse_txn_date(row.get("Date", ""))
                if d:
                    price_str = (row.get("Price", "") or "").replace("$", "").replace(",", "")
                    try:
                        price = float(price_str) if price_str else None
                    except ValueError:
                        price = None
                    txns.append(
                        {
                            "date": d,
                            "symbol": row.get("Symbol", ""),
                            "action": row["Action"],
                            "price": price,
                            "quantity": row.get("Quantity", ""),
                        }
                    )
    return txns


def directions_agree(rec_action: str, txn_action: str) -> bool:
    if rec_action in ("buy", "add") and txn_action == "Buy":
        return True
    if rec_action in ("sell", "trim") and txn_action == "Sell":
        return True
    return False


def find_matching_trade(rec: dict, txns: list[dict], days_window: int = 7) -> Optional[dict]:
    """Find the closest same-direction trade within days_window after rec date."""
    sym = rec["symbol"]
    rec_dt = datetime.fromisoformat(rec["timestamp"]).replace(tzinfo=None)
    rec_date = rec_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    rec_action = rec["action"]

    candidates = []
    for t in txns:
        if t["symbol"] != sym:
            continue
        delta = (t["date"] - rec_date).days
        if 0 <= delta <= days_window and directions_agree(rec_action, t["action"]):
            candidates.append((delta, t))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


# ---------- Performance computation ----------
def compute_rec_performance(
    rec: dict,
    matched_trade: Optional[dict],
    prices: dict,
    spy_prices: dict,
    horizons: list[int],
) -> dict:
    """
    For one recommendation, compute forward returns at each horizon.
    """
    rec_dt = datetime.fromisoformat(rec["timestamp"]).replace(tzinfo=None)
    rec_date = rec_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    # Reference price: prefer matched trade price, fall back to rec's current_price
    if matched_trade and matched_trade.get("price") is not None:
        ref_price = matched_trade["price"]
        ref_date = matched_trade["date"]
        price_source = "matched_trade"
    elif rec.get("position_context", {}) and rec["position_context"].get("current_price"):
        ref_price = rec["position_context"]["current_price"]
        ref_date = rec_date
        price_source = "rec_snapshot"
    else:
        # Try to look it up
        rec_date_str = rec_date.strftime("%Y-%m-%d")
        if rec_date_str in prices:
            ref_price = prices[rec_date_str]
            ref_date = rec_date
            price_source = "yahoo_lookup"
        else:
            return {
                "recommendation_id": rec["id"],
                "symbol": rec["symbol"],
                "error": "no_reference_price",
            }

    # SPY reference
    spy_ref = find_price_on_or_after(spy_prices, ref_date)
    if not spy_ref:
        spy_ref_price = None
    else:
        spy_ref_price = spy_ref[1]

    horizon_returns = {}
    for h in horizons:
        target = ref_date + timedelta(days=h)
        symbol_target = find_price_on_or_after(prices, target)
        spy_target = find_price_on_or_after(spy_prices, target)

        entry = {
            "horizon_days": h,
            "target_date": target.strftime("%Y-%m-%d"),
        }

        if symbol_target:
            actual_date, future_price = symbol_target
            ret_pct = (future_price - ref_price) / ref_price * 100
            entry["actual_date"] = actual_date
            entry["future_price"] = round(future_price, 4)
            entry["return_pct"] = round(ret_pct, 4)
        else:
            entry["future_price"] = None
            entry["return_pct"] = None

        if spy_target and spy_ref_price:
            spy_actual_date, spy_future = spy_target
            spy_ret = (spy_future - spy_ref_price) / spy_ref_price * 100
            entry["spy_return_pct"] = round(spy_ret, 4)
            if entry.get("return_pct") is not None:
                entry["alpha_pct"] = round(entry["return_pct"] - spy_ret, 4)

        horizon_returns[f"{h}d"] = entry

    return {
        "recommendation_id": rec["id"],
        "symbol": rec["symbol"],
        "rec_action": rec["action"],
        "rec_conviction": rec["conviction"],
        "rec_timestamp": rec["timestamp"],
        "rec_rr": rec.get("metrics", {}).get("risk_reward_score"),
        "rec_pgain": rec.get("metrics", {}).get("probability_gain_pct"),
        "matched_trade": matched_trade is not None,
        "reference_price": round(ref_price, 4),
        "reference_date": ref_date.strftime("%Y-%m-%d") if isinstance(ref_date, datetime) else ref_date,
        "price_source": price_source,
        "horizons": horizon_returns,
    }


# ---------- Aggregation ----------
def aggregate(performance_records: list[dict], horizons: list[int]) -> dict:
    """Aggregate stats by attribution and conviction."""
    by_action = defaultdict(list)
    by_conviction = defaultdict(list)
    by_matched = defaultdict(list)

    for p in performance_records:
        if "error" in p:
            continue
        for h in horizons:
            entry = p["horizons"].get(f"{h}d", {})
            if entry.get("return_pct") is None:
                continue

            ret = entry["return_pct"]
            alpha = entry.get("alpha_pct")
            buckets = [
                (by_action, p["rec_action"]),
                (by_conviction, p["rec_conviction"]),
                (by_matched, "matched" if p["matched_trade"] else "unmatched"),
            ]
            for bucket, key in buckets:
                bucket[(key, h)].append(
                    {
                        "symbol": p["symbol"],
                        "return_pct": ret,
                        "alpha_pct": alpha,
                        "rr": p.get("rec_rr"),
                    }
                )

    def _summarize(bucket: dict) -> dict:
        out = {}
        for (key, h), items in bucket.items():
            rets = [i["return_pct"] for i in items]
            alphas = [i["alpha_pct"] for i in items if i["alpha_pct"] is not None]
            wins = sum(1 for r in rets if r > 0)
            n = len(rets)
            out_key = f"{key}_{h}d"
            out[out_key] = {
                "n": n,
                "avg_return_pct": round(sum(rets) / n, 3) if n else None,
                "median_return_pct": round(sorted(rets)[n // 2], 3) if n else None,
                "win_rate_pct": round(wins / n * 100, 1) if n else None,
                "avg_alpha_pct": round(sum(alphas) / len(alphas), 3) if alphas else None,
            }
        return out

    return {
        "by_action": _summarize(by_action),
        "by_conviction": _summarize(by_conviction),
        "by_matched": _summarize(by_matched),
    }


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizons", default="1,7,30,90", help="Comma-separated days")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--no-cache", action="store_true", help="Skip price cache")
    args = parser.parse_args()

    horizons = [int(x.strip()) for x in args.horizons.split(",")]

    recs = load_recommendations()
    if not recs:
        print("No recommendations found.")
        return

    txns = load_transactions()
    print(f"Loaded {len(recs)} recs, {len(txns)} buy/sell transactions")

    # Determine date range to fetch
    rec_dates = [datetime.fromisoformat(r["timestamp"]).replace(tzinfo=None) for r in recs]
    earliest = min(rec_dates)
    latest = max(rec_dates) + timedelta(days=max(horizons) + 7)
    today = datetime.now()
    end_date = min(latest, today)

    start_str = (earliest - timedelta(days=2)).strftime("%Y-%m-%d")
    end_str = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Fetching prices from {start_str} to {end_str}")

    # Symbols to fetch
    symbols = sorted({r["symbol"] for r in recs})
    print(f"  {len(symbols)} unique symbols + SPY benchmark")

    cache = {} if args.no_cache else _load_price_cache()
    all_prices = fetch_prices(symbols + [BENCHMARK], start_str, end_str, cache)
    if not args.no_cache:
        _save_price_cache(cache)

    spy_prices = all_prices.get(BENCHMARK, {})
    if not spy_prices:
        print("  Warning: SPY prices not available — alpha will be skipped")

    # Compute performance for each rec
    print(f"\nComputing performance for {len(recs)} recommendations...")
    performance = []
    for rec in recs:
        sym = rec["symbol"]
        prices = all_prices.get(sym, {})
        matched = find_matching_trade(rec, txns)
        perf = compute_rec_performance(rec, matched, prices, spy_prices, horizons)
        performance.append(perf)

    # Aggregate
    aggregates = aggregate(performance, horizons)

    # Print summary
    print("\n=== Performance Summary ===")
    completed = [p for p in performance if "error" not in p]
    errored = [p for p in performance if "error" in p]
    print(f"Recommendations evaluated: {len(completed)}")
    print(f"Errors / no reference price: {len(errored)}")

    print("\nBy conviction (avg return %):")
    for h in horizons:
        print(f"\n  Horizon {h}d:")
        for key, stats in sorted(aggregates["by_conviction"].items()):
            if not key.endswith(f"_{h}d"):
                continue
            label = key.rsplit("_", 1)[0]
            print(
                f"    {label:<14} n={stats['n']:>3}  avg={stats.get('avg_return_pct')}%  "
                f"win={stats.get('win_rate_pct')}%  alpha={stats.get('avg_alpha_pct')}%"
            )

    # Top winners and losers (90d)
    winners = sorted(
        [p for p in completed if p["horizons"].get("90d", {}).get("return_pct") is not None],
        key=lambda x: -x["horizons"]["90d"]["return_pct"],
    )
    if winners:
        print(f"\nTop 5 winners (90d):")
        for p in winners[:5]:
            ret = p["horizons"]["90d"]["return_pct"]
            print(f"  {p['symbol']:<6} {p['rec_action']:<6} {ret:>+6.2f}%  R/R {p.get('rec_rr')}")
        print(f"\nTop 5 losers (90d):")
        for p in winners[-5:][::-1]:
            ret = p["horizons"]["90d"]["return_pct"]
            print(f"  {p['symbol']:<6} {p['rec_action']:<6} {ret:>+6.2f}%  R/R {p.get('rec_rr')}")

    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "n_recommendations": len(recs),
        "n_evaluated": len(completed),
        "horizons_days": horizons,
        "benchmark": BENCHMARK,
        "aggregates": aggregates,
        "details": performance,
    }

    if args.output:
        out_path = args.output
    else:
        os.makedirs(REPORT_DIR, exist_ok=True)
        today_str = datetime.now().strftime("%Y-%m-%d")
        out_path = os.path.join(REPORT_DIR, f"performance_{today_str}.json")

    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport: {out_path}")


if __name__ == "__main__":
    main()
