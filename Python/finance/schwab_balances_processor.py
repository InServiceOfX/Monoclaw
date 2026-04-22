#!/usr/bin/env python3
"""Build and maintain Schwab Balances master CSV.

Each individual Schwab balance CSV is a key-value snapshot file (not columnar).
This processor parses them all into a single columnar master CSV so the
portfolio API can query balance history efficiently.

Usage
-----
Rebuild from scratch (processes every *.csv / *.CSV in the balances dir):

  python Python/finance/schwab_balances_processor.py rebuild \\
    --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/balances

Append one new file downloaded from Schwab:

  python Python/finance/schwab_balances_processor.py append \\
    --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/balances \\
    --csv ~/Downloads/XXXX8231_Balances_20260430-183000.CSV

The master file is written to:
  <dir>/master-balances.csv

Master CSV columns
------------------
SnapshotDate        MM/DD/YYYY  from file header  ("as of MM/DD/YYYY HH:MM AM/PM ET")
SnapshotTime        HH:MM AM/PM from file header
Account Value       raw string  e.g. "$299,625.78"
Day Change          raw string  e.g. "-$1,727.77"
Day Change %        raw string  e.g. "-0.57%"
Cash & Cash Investments  raw string  first occurrence = top-level summary
Market Value (Securities) raw string  first "Market Value" line = securities only
Available to Trade (Cash) raw string  from "To Trade > Cash & Cash Investments"
Settled Funds       raw string  from "To Trade > Settled Funds"
Available to Withdraw raw string  from "To Withdraw > Cash & Cash Investments"
source_file         filename of the originating CSV

Deduplication
-------------
Key = SnapshotDate (date only).  If multiple files share the same date the one
with the lexicographically latest filename (which encodes the timestamp) wins.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

MASTER_NAME = "master-balances.csv"

COLUMNS = [
    "SnapshotDate",
    "SnapshotTime",
    "Account Value",
    "Day Change",
    "Day Change %",
    "Cash & Cash Investments",
    "Market Value (Securities)",
    "Available to Trade (Cash)",
    "Settled Funds",
    "Available to Withdraw",
    "source_file",
]

# ── parser ────────────────────────────────────────────────────────────────────

def parse_balance_file(path: Path) -> dict[str, str] | None:
    """Parse one Schwab balance key-value CSV into a normalised dict.

    Returns None if the file cannot be parsed or has no account value.
    """
    try:
        content = path.read_text(encoding="utf-8-sig")
    except Exception as exc:
        print(f"  WARN: cannot read {path.name}: {exc}")
        return None

    lines = content.splitlines()
    if not lines:
        return None

    # Header line: "Balances for account XXXX as of MM/DD/YYYY HH:MM AM/PM ET"
    header_text = lines[0].strip().strip('"')
    snapshot_date = ""
    snapshot_time = ""
    m = re.search(r"as of (\d{1,2}/\d{1,2}/\d{4}) (\d{1,2}:\d{2} [AP]M)", header_text, re.IGNORECASE)
    if m:
        snapshot_date = m.group(1)
        snapshot_time = m.group(2)

    # State-tracked key-value parse — handles repeated keys in subsections
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
            section = key          # section header (no value)
            continue
        # Disambiguate "Cash & Cash Investments" by subsection
        full_key = key
        if section == "To Trade" and key == "Cash & Cash Investments":
            full_key = "Available to Trade (Cash)"
        elif section == "To Withdraw" and key == "Cash & Cash Investments":
            full_key = "Available to Withdraw"
        if full_key not in kv:     # first occurrence wins for top-level keys
            kv[full_key] = val

    if not kv.get("Account Value"):
        print(f"  WARN: no Account Value found in {path.name}, skipping")
        return None

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
        "source_file": path.name,
    }


# ── I/O helpers ───────────────────────────────────────────────────────────────

def read_master(master: Path) -> list[dict[str, str]]:
    if not master.exists():
        return []
    rows: list[dict[str, str]] = []
    with master.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(dict(row))
    return rows


def write_master(master: Path, rows: list[dict[str, str]]) -> None:
    master.parent.mkdir(parents=True, exist_ok=True)
    with master.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _date_sort_key(row: dict[str, str]) -> str:
    """Convert MM/DD/YYYY → YYYY-MM-DD for chronological sorting."""
    d = row.get("SnapshotDate", "")
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d)
    if m:
        return f"{m.group(3)}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"
    return d


def merge_rows(existing: list[dict[str, str]], new: list[dict[str, str]]) -> list[dict[str, str]]:
    """Merge two lists of rows, deduplicating by SnapshotDate.

    When two rows share the same date, the one with the lexicographically
    larger source_file wins (filename encodes the download timestamp).
    """
    by_date: dict[str, dict[str, str]] = {}
    for row in existing + new:
        date_key = row.get("SnapshotDate", "")
        current = by_date.get(date_key)
        if current is None or row.get("source_file", "") >= current.get("source_file", ""):
            by_date[date_key] = row
    return sorted(by_date.values(), key=_date_sort_key)


# ── commands ──────────────────────────────────────────────────────────────────

def rebuild(bal_dir: Path) -> None:
    """Parse every individual balance CSV in bal_dir and write a fresh master."""
    files = sorted(
        p for p in list(bal_dir.glob("*.csv")) + list(bal_dir.glob("*.CSV"))
        if "master" not in p.name.lower()
    )
    if not files:
        print(f"No balance CSV files found in {bal_dir}")
        return

    rows: list[dict[str, str]] = []
    for p in files:
        print(f"  Parsing {p.name}…")
        row = parse_balance_file(p)
        if row:
            rows.append(row)

    merged = merge_rows([], rows)
    master = bal_dir / MASTER_NAME
    write_master(master, merged)
    print(f"Wrote {master} — {len(merged)} snapshots")


def append(bal_dir: Path, csv_file: Path) -> None:
    """Parse one new balance CSV and merge it into the existing master."""
    master = bal_dir / MASTER_NAME
    existing = read_master(master)
    print(f"  Parsing {csv_file.name}…")
    row = parse_balance_file(csv_file)
    if not row:
        raise SystemExit(f"Could not parse {csv_file}")
    merged = merge_rows(existing, [row])
    write_master(master, merged)
    print(f"Updated {master} — {len(merged)} snapshots")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Schwab Balances master CSV manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rebuild = sub.add_parser("rebuild", help="Rebuild master from all individual files")
    p_rebuild.add_argument("--dir", required=True, type=Path, help="Path to balances/ directory")

    p_append = sub.add_parser("append", help="Append one new balance CSV to the master")
    p_append.add_argument("--dir", required=True, type=Path, help="Path to balances/ directory")
    p_append.add_argument("--csv", required=True, type=Path, help="Path to the new balance CSV file")

    args = parser.parse_args()
    if args.cmd == "rebuild":
        rebuild(args.dir.expanduser())
    else:
        append(args.dir.expanduser(), args.csv.expanduser())


if __name__ == "__main__":
    main()
