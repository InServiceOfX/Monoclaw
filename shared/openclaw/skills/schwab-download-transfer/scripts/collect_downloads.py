#!/usr/bin/env python3
"""Move newly downloaded Schwab export files into their canonical private directories.

This script does not fetch data from Schwab. It organizes files that were already
exported into a local Downloads directory by a browser session.
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Rule:
    category: str
    patterns: tuple[str, ...]
    destination: str


RULES: tuple[Rule, ...] = (
    Rule("positions", ("*Positions*.csv",), "positions"),
    Rule(
        "realized-gain-loss-summary",
        ("*GainLoss_Realized_*.csv",),
        "realized-gain-loss",
    ),
    Rule(
        "realized-gain-loss-details",
        ("*GainLoss_Realized_Details*.csv",),
        "realized-gain-loss",
    ),
    Rule("transactions-csv", ("*Transactions*.csv",), "transactions"),
    Rule("transactions-json", ("*Transactions*.json",), "transactions"),
)


def iter_matches(downloads_dir: Path) -> Iterable[tuple[Rule, Path]]:
    for rule in RULES:
        for pattern in rule.patterns:
            for path in sorted(downloads_dir.glob(pattern)):
                if path.is_file():
                    yield rule, path


def ensure_unique_destination(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    for i in range(2, 1000):
        candidate = parent / f"{stem}__dup{i}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"unable to allocate unique destination for {dest}")


def collect(downloads_dir: Path, base_dir: Path, dry_run: bool = False) -> int:
    moved = 0
    seen: set[Path] = set()
    for rule, src in iter_matches(downloads_dir):
        if src in seen:
            continue
        seen.add(src)
        dest_dir = base_dir / rule.destination
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = ensure_unique_destination(dest_dir / src.name)
        print(f"[{rule.category}] {src} -> {dest}")
        if not dry_run:
            shutil.move(str(src), str(dest))
        moved += 1
    return moved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--downloads", required=True, type=Path, help="Downloads directory to scan")
    parser.add_argument("--base-dir", required=True, type=Path, help="Base Schwab brokerage directory")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without moving files")
    args = parser.parse_args()

    downloads_dir = args.downloads.expanduser()
    base_dir = args.base_dir.expanduser()

    if not downloads_dir.exists():
        raise SystemExit(f"downloads directory not found: {downloads_dir}")

    moved = collect(downloads_dir, base_dir, dry_run=args.dry_run)
    print(f"moved_files={moved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
