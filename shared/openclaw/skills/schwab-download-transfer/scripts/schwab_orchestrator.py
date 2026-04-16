#!/usr/bin/env python3
"""Orchestrate Schwab export, file collection, log updates, and master CSV maintenance.

This script is intentionally operator-friendly rather than fully autonomous.
It glues together the other helpers in this skill plus Monoclaw's existing
finance processors.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Paths:
    base_dir: Path
    downloads_dir: Path
    skill_dir: Path
    repo_root: Path

    @property
    def positions_dir(self) -> Path:
        return self.base_dir / "positions"

    @property
    def rgl_dir(self) -> Path:
        return self.base_dir / "realized-gain-loss"

    @property
    def transactions_dir(self) -> Path:
        return self.base_dir / "transactions"

    @property
    def rgl_log(self) -> Path:
        return self.rgl_dir / "download-log.json"

    @property
    def transactions_log(self) -> Path:
        return self.transactions_dir / "download-log.json"

    @property
    def export_script(self) -> Path:
        return self.skill_dir / "schwab_export_playwright.py"

    @property
    def collect_script(self) -> Path:
        return self.skill_dir / "collect_downloads.py"

    @property
    def update_log_script(self) -> Path:
        return self.skill_dir / "update_download_log.py"

    @property
    def tx_processor(self) -> Path:
        return self.repo_root / "Python/finance/schwab_transactions_processor.py"

    @property
    def rgl_processor(self) -> Path:
        return self.repo_root / "Python/finance/schwab_rgl_processor.py"


@dataclass(frozen=True)
class RangePlan:
    date_from_iso: str
    date_to_iso: str

    @property
    def from_ui(self) -> str:
        return _iso_to_ui(self.date_from_iso)

    @property
    def to_ui(self) -> str:
        return _iso_to_ui(self.date_to_iso)


def _run(cmd: list[str], dry_run: bool = False) -> None:
    printable = " ".join(_shell_quote(c) for c in cmd)
    print(f"$ {printable}")
    if not dry_run:
        subprocess.run(cmd, check=True)


def _shell_quote(s: str) -> str:
    if not s or any(ch in s for ch in " '\t\n\"\\$()[]{}*?&;|<>!"):
        return repr(s)
    return s


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object in {path}")
    return data


def _today_iso() -> str:
    return date.today().isoformat()


def _iso_to_ui(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%m/%d/%Y")


def _next_day_iso(value: str) -> str:
    return (date.fromisoformat(value) + timedelta(days=1)).isoformat()


def _plan_from_log(log_path: Path, fallback_from: str | None = None) -> RangePlan | None:
    data = _load_json(log_path)
    start = data.get("next_download_start") or fallback_from
    if not start:
        return None
    end = _today_iso()
    if date.fromisoformat(start) > date.fromisoformat(end):
        return None
    return RangePlan(date_from_iso=start, date_to_iso=end)


def _latest_matching(directory: Path, pattern: str) -> Path | None:
    files = [p for p in directory.glob(pattern) if p.is_file() and "MASTER" not in p.name]
    if not files:
        return None
    files.sort(key=lambda p: (p.stat().st_mtime, p.name))
    return files[-1]


def _latest_since(directory: Path, pattern: str, started_at: float) -> Path | None:
    files = [p for p in directory.glob(pattern) if p.is_file() and p.stat().st_mtime >= started_at - 1]
    if not files:
        return None
    files.sort(key=lambda p: (p.stat().st_mtime, p.name))
    return files[-1]


def _latest_many_since(directory: Path, pattern: str, started_at: float) -> list[Path]:
    files = [p for p in directory.glob(pattern) if p.is_file() and p.stat().st_mtime >= started_at - 1]
    files.sort(key=lambda p: (p.stat().st_mtime, p.name))
    return files


def _ensure_dirs(paths: Paths) -> None:
    for d in (paths.positions_dir, paths.rgl_dir, paths.transactions_dir):
        d.mkdir(parents=True, exist_ok=True)


def do_positions(paths: Paths, args: argparse.Namespace) -> None:
    started_at = datetime.now().timestamp()
    _run(
        [
            sys.executable,
            str(paths.export_script),
            "positions",
            "--user-data-dir",
            str(args.user_data_dir),
            *( ["--headed"] if args.headed else [] ),
            "--login-timeout",
            str(args.login_timeout),
        ],
        dry_run=args.dry_run,
    )
    _run(
        [
            sys.executable,
            str(paths.collect_script),
            "--downloads",
            str(paths.downloads_dir),
            "--base-dir",
            str(paths.base_dir),
            *( ["--dry-run"] if args.dry_run else [] ),
        ],
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        latest = _latest_since(paths.positions_dir, "*Positions*.csv", started_at)
        print(f"positions_file={latest if latest else '<not found>'}")


def do_rgl(paths: Paths, args: argparse.Namespace) -> None:
    plan = _plan_from_log(paths.rgl_log, fallback_from=args.first_rgl_from)
    if not plan:
        raise SystemExit("No RGL range available. Provide --first-rgl-from or create a log with next_download_start.")
    print(f"rgl_range={plan.date_from_iso}..{plan.date_to_iso}")
    started_at = datetime.now().timestamp()
    _run(
        [
            sys.executable,
            str(paths.export_script),
            "rgl",
            "--user-data-dir",
            str(args.user_data_dir),
            *( ["--headed"] if args.headed else [] ),
            "--login-timeout",
            str(args.login_timeout),
            "--from-date",
            plan.from_ui,
            "--to-date",
            plan.to_ui,
        ],
        dry_run=args.dry_run,
    )
    _run(
        [
            sys.executable,
            str(paths.collect_script),
            "--downloads",
            str(paths.downloads_dir),
            "--base-dir",
            str(paths.base_dir),
            *( ["--dry-run"] if args.dry_run else [] ),
        ],
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return

    summary = _latest_since(paths.rgl_dir, "*GainLoss_Realized_*.csv", started_at)
    details = _latest_since(paths.rgl_dir, "*GainLoss_Realized_Details*.csv", started_at)
    print(f"rgl_summary={summary if summary else '<not found>'}")
    print(f"rgl_details={details if details else '<not found>'}")
    if not summary or not details:
        raise SystemExit("Expected new RGL summary and details files after export")
    if not args.last_closed_date:
        raise SystemExit("RGL requires --last-closed-date so next_download_start can be computed safely")

    _run(
        [
            sys.executable,
            str(paths.update_log_script),
            "--log",
            str(paths.rgl_log),
            "--kind",
            "realized-gain-loss",
            "--from",
            plan.date_from_iso,
            "--to",
            plan.date_to_iso,
            "--last-closed-date",
            args.last_closed_date,
            "--file",
            str(summary),
            "--file",
            str(details),
        ]
    )
    if args.update_masters:
        _run(
            [
                sys.executable,
                str(paths.rgl_processor),
                "append",
                "--dir",
                str(paths.rgl_dir),
                "--summary",
                str(summary),
                "--details",
                str(details),
            ]
        )


def do_transactions(paths: Paths, args: argparse.Namespace) -> None:
    plan = _plan_from_log(paths.transactions_log, fallback_from=args.first_transactions_from)
    if not plan:
        print("transactions_range=<full-history/manual>")
    else:
        print(f"transactions_range={plan.date_from_iso}..{plan.date_to_iso}")
    started_at = datetime.now().timestamp()
    cmd = [
        sys.executable,
        str(paths.export_script),
        "transactions",
        "--user-data-dir",
        str(args.user_data_dir),
        *( ["--headed"] if args.headed else [] ),
        "--login-timeout",
        str(args.login_timeout),
    ]
    if plan:
        cmd += ["--from-date", plan.from_ui, "--to-date", plan.to_ui]
    _run(cmd, dry_run=args.dry_run)
    _run(
        [
            sys.executable,
            str(paths.collect_script),
            "--downloads",
            str(paths.downloads_dir),
            "--base-dir",
            str(paths.base_dir),
            *( ["--dry-run"] if args.dry_run else [] ),
        ],
        dry_run=args.dry_run,
    )
    if args.dry_run or not plan:
        return

    csv_file = _latest_since(paths.transactions_dir, "*Transactions*.csv", started_at)
    json_file = _latest_since(paths.transactions_dir, "*Transactions*.json", started_at)
    print(f"transactions_csv={csv_file if csv_file else '<not found>'}")
    print(f"transactions_json={json_file if json_file else '<not found>'}")
    if not csv_file or not json_file:
        raise SystemExit("Expected new transactions CSV and JSON files after export")

    _run(
        [
            sys.executable,
            str(paths.update_log_script),
            "--log",
            str(paths.transactions_log),
            "--kind",
            "transactions",
            "--from",
            plan.date_from_iso,
            "--to",
            plan.date_to_iso,
            "--file",
            str(csv_file),
            "--file",
            str(json_file),
        ]
    )
    if args.update_masters:
        _run(
            [
                sys.executable,
                str(paths.tx_processor),
                "append",
                "--dir",
                str(paths.transactions_dir),
                "--csv",
                str(csv_file),
            ]
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=["positions", "rgl", "transactions", "all"])
    parser.add_argument("--base-dir", type=Path, required=True, help="Schwab brokerage base directory")
    parser.add_argument("--downloads-dir", type=Path, default=Path("~/Downloads"), help="Browser downloads directory")
    parser.add_argument("--user-data-dir", type=Path, required=True, help="Persistent browser profile for Playwright")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--login-timeout", type=int, default=120)
    parser.add_argument("--first-rgl-from", help="Bootstrap ISO date for first RGL incremental run")
    parser.add_argument("--first-transactions-from", help="Bootstrap ISO date for first transactions incremental run")
    parser.add_argument("--last-closed-date", help="Required for RGL log updates after a successful export")
    parser.add_argument("--update-masters", action="store_true", help="Append new files into Monoclaw master CSVs")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without running browser export or changing logs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_dir = Path(__file__).resolve().parent
    repo_root = skill_dir.parents[4]
    paths = Paths(
        base_dir=args.base_dir.expanduser(),
        downloads_dir=args.downloads_dir.expanduser(),
        skill_dir=skill_dir,
        repo_root=repo_root,
    )
    _ensure_dirs(paths)

    if args.task in ("positions", "all"):
        do_positions(paths, args)
    if args.task in ("rgl", "all"):
        do_rgl(paths, args)
    if args.task in ("transactions", "all"):
        do_transactions(paths, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
