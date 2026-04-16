#!/usr/bin/env python3
"""Inspect a Schwab download-log.json and summarize the next download state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

KINDS = {"auto", "transactions", "realized-gain-loss"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def infer_kind(data: dict[str, Any], explicit: str) -> str:
    if explicit != "auto":
        return explicit
    if "last_closed_date" in data:
        return "realized-gain-loss"
    return "transactions"


def entries_count(data: dict[str, Any]) -> int:
    for key in ("history", "downloads", "entries"):
        value = data.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


def print_field(label: str, value: Any) -> None:
    print(f"{label}: {value if value not in (None, '') else '<missing>'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_path", type=Path, help="Path to download-log.json")
    parser.add_argument(
        "--kind",
        default="auto",
        choices=sorted(KINDS),
        help="Interpretation mode for the log",
    )
    args = parser.parse_args()

    if not args.log_path.exists():
        print(f"error: file not found: {args.log_path}", file=sys.stderr)
        return 2

    try:
        data = load_json(args.log_path)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.log_path}: {exc}", file=sys.stderr)
        return 3

    if not isinstance(data, dict):
        print("error: expected top-level JSON object", file=sys.stderr)
        return 4

    kind = infer_kind(data, args.kind)

    print_field("log", args.log_path)
    print_field("kind", kind)
    print_field("entries", entries_count(data))

    if kind == "realized-gain-loss":
        print_field("last_closed_date", data.get("last_closed_date"))
    else:
        print_field("last_data_point", data.get("last_data_point"))

    print_field("next_download_start", data.get("next_download_start"))

    date_range = data.get("date_range")
    if isinstance(date_range, dict):
        print_field("last_range.from", date_range.get("from"))
        print_field("last_range.to", date_range.get("to"))

    latest = None
    for key in ("history", "downloads", "entries"):
        value = data.get(key)
        if isinstance(value, list) and value:
            latest = value[-1]
            break

    if isinstance(latest, dict):
        print_field("latest.filename", latest.get("filename"))
        print_field("latest.format", latest.get("format"))
        if isinstance(latest.get("date_range"), dict):
            print_field("latest.date_range.from", latest["date_range"].get("from"))
            print_field("latest.date_range.to", latest["date_range"].get("to"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
