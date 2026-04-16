"""Schwab CSV parsing utilities."""
from __future__ import annotations

import csv
import re
from pathlib import Path


def _strip_currency(val: str) -> str:
    """Remove $, %, commas from a value string."""
    return val.replace("$", "").replace("%", "").replace(",", "").strip()


def _read_raw(path: Path, skip_meta: bool) -> tuple[list[str], list[dict]]:
    """Read a Schwab CSV. If skip_meta=True, skip line 0 (metadata) and any
    following blank lines before the header row."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        if skip_meta:
            next(reader, None)  # metadata line
            # skip blank separator lines
            header = None
            for row in reader:
                if row and any(c.strip() for c in row):
                    header = [c.strip() for c in row]
                    break
        else:
            header = [c.strip() for c in (next(reader, None) or [])]

        if not header:
            return [], []

        rows = []
        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            d = {header[i]: row[i].strip() for i in range(len(header))}
            # Skip Schwab summary/aggregate rows that are not real positions
            sym = d.get("Symbol", "").strip().lower()
            if sym in ("total", "positions total"):
                continue
            rows.append(d)
    return header, rows


def parse_positions_csv(path: str) -> tuple[str, list[str], list[dict]]:
    """Parse a positions snapshot CSV.
    Returns (snapshot_date, header, rows).
    snapshot_date is YYYY-MM-DD extracted from the metadata line or filename.
    """
    p = Path(path).expanduser()
    with p.open("r", encoding="utf-8-sig") as f:
        meta_line = f.readline()

    snapshot_date = ""
    m = re.search(r"(\d{4})[/\-](\d{2})[/\-](\d{2})", meta_line)
    if m:
        snapshot_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if not snapshot_date:
        m2 = re.search(r"(\d{2})/(\d{2})/(\d{4})", meta_line)
        if m2:
            snapshot_date = f"{m2.group(3)}-{m2.group(1)}-{m2.group(2)}"
    if not snapshot_date:
        m3 = re.search(r"(\d{4})-(\d{2})-(\d{2})", p.stem)
        if m3:
            snapshot_date = f"{m3.group(1)}-{m3.group(2)}-{m3.group(3)}"

    header, rows = _read_raw(p, skip_meta=True)
    return snapshot_date, header, rows


def parse_transactions_csv(path: str) -> tuple[list[str], list[dict]]:
    """Parse a transactions CSV (no metadata line)."""
    return _read_raw(Path(path).expanduser(), skip_meta=False)


def parse_rgl_csv(path: str) -> tuple[list[str], list[dict]]:
    """Parse an RGL summary or details CSV.

    Original Schwab downloads have a free-text metadata line before the header.
    MASTER CSVs start directly with the header row. Auto-detect by checking
    whether the first cell is "Symbol".
    """
    p = Path(path).expanduser()
    with p.open("r", encoding="utf-8-sig") as f:
        first_cell = f.readline().strip().strip('"').split(",")[0].strip().strip('"')
    skip_meta = first_cell.lower() != "symbol"
    return _read_raw(p, skip_meta=skip_meta)
