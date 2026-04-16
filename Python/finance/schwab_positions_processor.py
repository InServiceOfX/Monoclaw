#!/usr/bin/env python3
"""Build and maintain Schwab Positions master CSV.

Positions are point-in-time snapshots — no deduplication needed. Each file
represents a distinct date, so all rows from all files are kept. The output
adds a SnapshotDate column derived from the Schwab metadata header line.

Usage:
  python Python/finance/schwab_positions_processor.py rebuild \
    --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/positions

  # After downloading a new snapshot, just rebuild (fast, idempotent):
  python Python/finance/schwab_positions_processor.py rebuild \
    --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/positions
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

MASTER_NAME = "master-positions.csv"


def _parse_snapshot_date(meta_line: str) -> str:
    """Extract date from Schwab header like: 'Positions for account ... as of ..., 2026/04/16'"""
    m = re.search(r"(\d{4})[/\-](\d{2})[/\-](\d{2})", meta_line)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # fallback: try MM/DD/YYYY
    m2 = re.search(r"(\d{2})/(\d{2})/(\d{4})", meta_line)
    if m2:
        return f"{m2.group(3)}-{m2.group(1)}-{m2.group(2)}"
    return ""


def _read_schwab_positions(path: Path) -> tuple[str, list[str], list[list[str]]]:
    """Return (snapshot_date, header, rows). Skips empty and trailing lines."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        meta = next(r, None) or []
        meta_text = meta[0] if meta else ""
        snapshot_date = _parse_snapshot_date(meta_text)
        if not snapshot_date:
            m = re.search(r"(\d{4})-(\d{2})-(\d{2})", path.stem)
            if m:
                snapshot_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        # Skip blank lines between metadata and column headers
        header = None
        for row in r:
            if row and any(c.strip() for c in row):
                header = row
                break
        if not header:
            return snapshot_date, [], []
        rows: list[list[str]] = []
        for row in r:
            if not row or all(not c.strip() for c in row):
                continue
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            rows.append(row[: len(header)])
    return snapshot_date, [c.strip() for c in header], rows


def rebuild(base_dir: Path) -> None:
    snapshot_files = sorted(
        p for p in base_dir.glob("*.csv") if "master" not in p.name.lower()
    )

    master_header: list[str] = []
    all_rows: list[list[str]] = []

    for p in snapshot_files:
        snapshot_date, header, rows = _read_schwab_positions(p)
        if not header:
            print(f"  skipped (no header): {p.name}")
            continue

        if not master_header:
            master_header = ["SnapshotDate"] + header
        elif "SnapshotDate" not in master_header:
            master_header = ["SnapshotDate"] + master_header

        for row in rows:
            all_rows.append([snapshot_date] + row)

        print(f"  {p.name}: date={snapshot_date}, rows={len(rows)}")

    # sort by snapshot date then symbol
    date_idx = 0
    sym_idx = master_header.index("Symbol") if "Symbol" in master_header else 1
    all_rows.sort(key=lambda r: (r[date_idx], r[sym_idx]))

    master_path = base_dir / MASTER_NAME
    master_path.parent.mkdir(parents=True, exist_ok=True)
    with master_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(master_header)
        w.writerows(all_rows)

    print(f"Rebuilt positions master: snapshots={len(snapshot_files)}, total_rows={len(all_rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Schwab Positions master CSV manager")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_rebuild = sub.add_parser("rebuild", help="rebuild master from all snapshot CSVs")
    p_rebuild.add_argument("--dir", required=True, type=Path)
    args = parser.parse_args()
    rebuild(args.dir.expanduser())


if __name__ == "__main__":
    main()
