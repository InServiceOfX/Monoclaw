#!/usr/bin/env python3
"""Update Schwab download-log.json files after a successful export and file move."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

KINDS = {"transactions", "realized-gain-loss"}


def load_log(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"history": []}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SystemExit("log must be a JSON object")
    data.setdefault("history", [])
    return data


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def next_day_iso(value: str) -> str:
    return (parse_iso_date(value) + timedelta(days=1)).isoformat()


def append_history(data: dict[str, Any], files: list[Path], date_from: str, date_to: str, kind: str) -> None:
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    for path in files:
        data["history"].append(
            {
                "filename": path.name,
                "format": path.suffix.lstrip(".").lower(),
                "kind": kind,
                "downloaded_at": stamp,
                "date_range": {"from": date_from, "to": date_to},
            }
        )


def update_state(data: dict[str, Any], kind: str, date_to: str, last_closed_date: str | None) -> None:
    if kind == "transactions":
        data["last_data_point"] = date_to
        data["next_download_start"] = next_day_iso(date_to)
    else:
        if not last_closed_date:
            raise SystemExit("--last-closed-date is required for realized-gain-loss")
        data["last_closed_date"] = last_closed_date
        data["next_download_start"] = next_day_iso(last_closed_date)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path, help="Path to download-log.json")
    parser.add_argument("--kind", required=True, choices=sorted(KINDS))
    parser.add_argument("--from", dest="date_from", required=True, help="Covered range start (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", required=True, help="Covered range end (YYYY-MM-DD)")
    parser.add_argument("--file", dest="files", action="append", required=True, help="Downloaded file path; repeat for each file")
    parser.add_argument("--last-closed-date", help="Final closed date in RGL details (YYYY-MM-DD)")
    args = parser.parse_args()

    parse_iso_date(args.date_from)
    parse_iso_date(args.date_to)
    if args.last_closed_date:
        parse_iso_date(args.last_closed_date)

    log_path = args.log.expanduser()
    data = load_log(log_path)
    files = [Path(f).expanduser() for f in args.files]

    append_history(data, files, args.date_from, args.date_to, args.kind)
    data["date_range"] = {"from": args.date_from, "to": args.date_to}
    update_state(data, args.kind, args.date_to, args.last_closed_date)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"updated_log={log_path}")
    print(f"next_download_start={data.get('next_download_start')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
