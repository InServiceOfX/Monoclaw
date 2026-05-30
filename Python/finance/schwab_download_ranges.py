#!/usr/bin/env python3
"""Print the next custom date ranges for Schwab data downloads.

Usage:
    cd ~/.openclaw/workspace/repos/Monoclaw/Python/finance && uv run python schwab_download_ranges.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

BASE = Path("~/.openclaw/workspace/Data/Private/finance/schwab-brokerage").expanduser()
TODAY = date.today().strftime("%m/%d/%Y")
TODAY_ISO = date.today().isoformat()


def read_log(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception as e:
        print(f"  ⚠ Could not read {path}: {e}", file=sys.stderr)
        return None


def fmt_date(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%m/%d/%Y")
    except Exception:
        return iso


def main():
    print(f"Schwab Download Ranges ({TODAY_ISO}):")
    print()

    # Transactions
    tx_log = read_log(BASE / "transactions" / "download-log.json")
    if tx_log:
        start = tx_log.get("next_download_start", "?")
        print(f"  Transactions:      {fmt_date(start)}  →  {TODAY}")
    else:
        print("  Transactions:      (no download-log.json found)")

    # Realized Gain/Loss
    rgl_log = read_log(BASE / "realized-gain-loss" / "download-log.json")
    if rgl_log:
        start = rgl_log.get("next_download_start", "?")
        print(f"  Realized Gain/Loss: {fmt_date(start)}  →  {TODAY}")
    else:
        print("  Realized Gain/Loss: (no download-log.json found)")

    print()
    print("Download order: Positions → Balances → RGL (Summary+Details) → Transactions (CSV+JSON)")


if __name__ == "__main__":
    main()
