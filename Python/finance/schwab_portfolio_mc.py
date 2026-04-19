#!/usr/bin/env python3
"""CLI wrapper for the Schwab portfolio Monte Carlo analytics module.

The implementation lives in `api/monte_carlo.py` so the dashboard and CLI use
the same logic. This wrapper reads the latest local Schwab positions snapshot
at runtime and never hardcodes account holdings.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from api.main import _current_positions_from_csv, _is_security_position, _position_market_value
from api.monte_carlo import Holding, run_monte_carlo


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local portfolio Monte Carlo analysis")
    parser.add_argument("--symbols", default="", help="Comma-separated watchlist symbols")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--simulations", type=int, default=3000)
    parser.add_argument("--period", default="1y")
    parser.add_argument("--max-positions", type=int, default=25)
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    snapshot_date, rows = _current_positions_from_csv()
    positions = sorted(
        [r for r in rows if _is_security_position(r)],
        key=_position_market_value,
        reverse=True,
    )[: args.max_positions]
    holdings = [
        Holding(
            symbol=r.get("Symbol", ""),
            description=r.get("Description", ""),
            market_value=_position_market_value(r),
            asset_type=r.get("Asset Type", r.get("Security Type", "")),
        )
        for r in positions
    ]
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    result = {
        "snapshot_date": snapshot_date,
        "base_dir": os.environ.get("SCHWAB_BASE_DIR", "~/.openclaw/workspace/Data/Private/finance/schwab-brokerage"),
        **run_monte_carlo(
            holdings,
            symbols,
            days=args.days,
            simulations=args.simulations,
            period=args.period,
        ),
    }

    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
