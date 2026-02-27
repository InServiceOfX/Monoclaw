#!/usr/bin/env python3
"""Build and maintain Schwab Realized Gain/Loss master CSVs.

Usage:
  # Rebuild masters from all historical files in directory
  python Python/finance/schwab_rgl_processor.py rebuild \
    --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/realized-gain-loss

  # Incrementally merge one newly downloaded pair
  python Python/finance/schwab_rgl_processor.py append \
    --summary /path/to/Joint_Tenant_GainLoss_Realized_*.csv \
    --details /path/to/Joint_Tenant_GainLoss_Realized_Details_*.csv \
    --dir ~/.openclaw/workspace/Data/Private/finance/schwab-brokerage/realized-gain-loss
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

SUMMARY_MASTER = "Joint_Tenant_GainLoss_Realized_Summary_MASTER.csv"
DETAILS_MASTER = "Joint_Tenant_GainLoss_Realized_Details_MASTER.csv"


def _read_schwab_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    # Schwab exports have a metadata line first, header line second.
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        _meta = next(r, None)
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


def _read_master_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        header = next(r, None)
        if not header:
            return [], []
        return header, [row for row in r if row]


def _date_value(s: str) -> datetime:
    s = (s or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return datetime.min


def _merge_rows(
    existing_header: list[str],
    existing_rows: list[list[str]],
    new_header: list[str],
    new_rows: list[list[str]],
    key_columns: list[str],
) -> tuple[list[str], list[list[str]]]:
    if not existing_header:
        header = list(new_header)
    else:
        header = list(existing_header)

    # normalize to the target header
    index = {c: i for i, c in enumerate(header)}

    def normalize(src_header: list[str], row: list[str]) -> list[str]:
        out = [""] * len(header)
        src_idx = {c: i for i, c in enumerate(src_header)}
        for c, j in index.items():
            i = src_idx.get(c)
            if i is not None and i < len(row):
                out[j] = row[i]
        return out

    all_rows = [normalize(existing_header or header, r) for r in existing_rows]
    all_rows.extend(normalize(new_header, r) for r in new_rows)

    key_idx = [index[c] for c in key_columns if c in index]
    seen = set()
    deduped: list[list[str]] = []
    for r in all_rows:
        key = tuple(r[i].strip() for i in key_idx) if key_idx else tuple(r)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    date_col = "Transaction Closed Date" if "Transaction Closed Date" in index else "Closed Date"
    date_idx = index.get(date_col)
    sym_idx = index.get("Symbol", 0)
    if date_idx is not None:
        deduped.sort(key=lambda r: (_date_value(r[date_idx]), r[sym_idx].strip()))

    return header, deduped


def _write_master(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def rebuild(base_dir: Path) -> None:
    summary_files = sorted(
        p for p in base_dir.glob("*.csv") if "Details" not in p.name and "MASTER" not in p.name
    )
    details_files = sorted(
        p for p in base_dir.glob("*.csv") if "Details" in p.name and "MASTER" not in p.name
    )

    sum_h: list[str] = []
    sum_r: list[list[str]] = []
    for p in summary_files:
        h, r = _read_schwab_csv(p)
        if h:
            if "source_file" not in h:
                h = h + ["source_file"]
                r = [row + [p.name] for row in r]
            sum_h, sum_r = _merge_rows(sum_h, sum_r, h, r, ["Symbol", "Closed Date", "Quantity", "Gain/Loss"])

    det_h: list[str] = []
    det_r: list[list[str]] = []
    for p in details_files:
        h, r = _read_schwab_csv(p)
        if h:
            if "source_file" not in h:
                h = h + ["source_file"]
                r = [row + [p.name] for row in r]
            det_h, det_r = _merge_rows(
                det_h,
                det_r,
                h,
                r,
                [
                    "Symbol",
                    "Closed Date",
                    "Opened Date",
                    "Quantity",
                    "Proceeds",
                    "Cost Basis (CB)",
                    "Transaction Closed Date",
                ],
            )

    _write_master(base_dir / SUMMARY_MASTER, sum_h, sum_r)
    _write_master(base_dir / DETAILS_MASTER, det_h, det_r)
    print(f"Rebuilt masters: summary={len(sum_r)} rows, details={len(det_r)} rows")


def append(base_dir: Path, summary_file: Path, details_file: Path) -> None:
    sum_master = base_dir / SUMMARY_MASTER
    det_master = base_dir / DETAILS_MASTER

    existing_sum_h, existing_sum_r = _read_master_csv(sum_master)
    existing_det_h, existing_det_r = _read_master_csv(det_master)

    sum_h, sum_r = _read_schwab_csv(summary_file)
    det_h, det_r = _read_schwab_csv(details_file)

    if "source_file" not in sum_h:
        sum_h = sum_h + ["source_file"]
        sum_r = [row + [summary_file.name] for row in sum_r]
    if "source_file" not in det_h:
        det_h = det_h + ["source_file"]
        det_r = [row + [details_file.name] for row in det_r]

    out_sum_h, out_sum_r = _merge_rows(
        existing_sum_h,
        existing_sum_r,
        sum_h,
        sum_r,
        ["Symbol", "Closed Date", "Quantity", "Gain/Loss"],
    )
    out_det_h, out_det_r = _merge_rows(
        existing_det_h,
        existing_det_r,
        det_h,
        det_r,
        [
            "Symbol",
            "Closed Date",
            "Opened Date",
            "Quantity",
            "Proceeds",
            "Cost Basis (CB)",
            "Transaction Closed Date",
        ],
    )

    _write_master(sum_master, out_sum_h, out_sum_r)
    _write_master(det_master, out_det_h, out_det_r)
    print(f"Appended masters: summary={len(out_sum_r)} rows, details={len(out_det_r)} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description="Schwab RGL master CSV manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rebuild = sub.add_parser("rebuild", help="rebuild master files from all historical CSVs")
    p_rebuild.add_argument("--dir", required=True, type=Path, help="realized-gain-loss directory")

    p_append = sub.add_parser("append", help="append one new summary+details pair into masters")
    p_append.add_argument("--dir", required=True, type=Path, help="realized-gain-loss directory")
    p_append.add_argument("--summary", required=True, type=Path)
    p_append.add_argument("--details", required=True, type=Path)

    args = parser.parse_args()
    if args.cmd == "rebuild":
        rebuild(args.dir.expanduser())
    else:
        append(args.dir.expanduser(), args.summary.expanduser(), args.details.expanduser())


if __name__ == "__main__":
    main()
