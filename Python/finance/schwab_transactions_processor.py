#!/usr/bin/env python3
"""Build and maintain Schwab Transactions master CSV.

Usage:
  python Python/finance/schwab_transactions_processor.py rebuild \
    --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/transactions

  python Python/finance/schwab_transactions_processor.py append \
    --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/transactions \
    --csv /path/to/Joint_Tenant_XXX231_Transactions_*.csv
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

MASTER_NAME = "Joint_Tenant_Transactions_MASTER.csv"


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        header = next(r, None)
        if not header:
            return [], []
        rows: list[list[str]] = []
        for row in r:
            if not row or all(not c.strip() for c in row):
                continue
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            rows.append(row[: len(header)])
        return header, rows


def read_master(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.exists():
        return [], []
    return read_csv(path)


def parse_date(s: str) -> datetime:
    s = (s or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return datetime.min


def merge(
    existing_header: list[str],
    existing_rows: list[list[str]],
    new_header: list[str],
    new_rows: list[list[str]],
    key_cols: list[str],
) -> tuple[list[str], list[list[str]]]:
    header = existing_header or new_header
    idx = {c: i for i, c in enumerate(header)}

    def normalize(src_header: list[str], row: list[str]) -> list[str]:
        src_idx = {c: i for i, c in enumerate(src_header)}
        out = [""] * len(header)
        for c, j in idx.items():
            i = src_idx.get(c)
            if i is not None and i < len(row):
                out[j] = row[i]
        return out

    all_rows = [normalize(existing_header or header, r) for r in existing_rows]
    all_rows.extend(normalize(new_header, r) for r in new_rows)

    key_idx = [idx[c] for c in key_cols if c in idx]
    seen = set()
    out = []
    for r in all_rows:
        k = tuple(r[i].strip() for i in key_idx) if key_idx else tuple(r)
        if k in seen:
            continue
        seen.add(k)
        out.append(r)

    date_idx = idx.get("Date")
    action_idx = idx.get("Action", 0)
    symbol_idx = idx.get("Symbol", 0)
    if date_idx is not None:
        out.sort(key=lambda r: (parse_date(r[date_idx]), r[action_idx].strip(), r[symbol_idx].strip()))

    return list(header), out


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def rebuild(base_dir: Path) -> None:
    files = sorted(p for p in base_dir.glob("*.csv") if "MASTER" not in p.name)
    h: list[str] = []
    r: list[list[str]] = []

    for p in files:
        nh, nr = read_csv(p)
        if not nh:
            continue
        if "source_file" not in nh:
            nh = nh + ["source_file"]
            nr = [row + [p.name] for row in nr]
        h, r = merge(
            h,
            r,
            nh,
            nr,
            ["Date", "Action", "Symbol", "Description", "Quantity", "Price", "Amount"],
        )

    write_csv(base_dir / MASTER_NAME, h, r)
    print(f"Rebuilt transactions master: rows={len(r)}")


def append(base_dir: Path, csv_file: Path) -> None:
    master = base_dir / MASTER_NAME
    eh, er = read_master(master)
    nh, nr = read_csv(csv_file)
    if not nh:
        raise SystemExit(f"No header found in {csv_file}")
    if "source_file" not in nh:
        nh = nh + ["source_file"]
        nr = [row + [csv_file.name] for row in nr]

    oh, orows = merge(
        eh,
        er,
        nh,
        nr,
        ["Date", "Action", "Symbol", "Description", "Quantity", "Price", "Amount"],
    )
    write_csv(master, oh, orows)
    print(f"Appended transactions master: rows={len(orows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Schwab Transactions master CSV manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rebuild = sub.add_parser("rebuild")
    p_rebuild.add_argument("--dir", required=True, type=Path)

    p_append = sub.add_parser("append")
    p_append.add_argument("--dir", required=True, type=Path)
    p_append.add_argument("--csv", required=True, type=Path)

    args = parser.parse_args()
    if args.cmd == "rebuild":
        rebuild(args.dir.expanduser())
    else:
        append(args.dir.expanduser(), args.csv.expanduser())


if __name__ == "__main__":
    main()
