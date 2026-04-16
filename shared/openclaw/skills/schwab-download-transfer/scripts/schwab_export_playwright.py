#!/usr/bin/env python3
"""Playwright helper for authenticated Schwab exports.

This is an operator-assisted automation skeleton:
- it expects a logged-in browser context or a manual login step
- selectors may need maintenance when Schwab changes its UI
- it focuses on repeatable page navigation and export clicking
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path


def require_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Playwright is required. Install with: python3 -m pip install playwright && python3 -m playwright install chromium"
        ) from exc
    return sync_playwright


POSITIONS_URL = "https://client.schwab.com/app/accounts/positions/#/"
RGL_URL = "https://client.schwab.com/app/accounts/RGL/#/RGL"
TRANSACTIONS_URL = "https://client.schwab.com/app/accounts/history/#/"


def launch_context(sync_playwright, user_data_dir: Path, headed: bool):
    pw = sync_playwright().start()
    browser = pw.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=not headed,
        accept_downloads=True,
    )
    return pw, browser


def maybe_wait_for_login(page, timeout_seconds: int) -> None:
    print("Waiting for authenticated Schwab session. Log in manually if needed...")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        url = page.url
        if "client.schwab.com/app/accounts" in url:
            return
        time.sleep(1)
    print("Login wait expired; continuing anyway.")


def best_effort_click(page, selectors: list[str]) -> bool:
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=3000)
            return True
        except Exception:
            continue
    return False


def export_positions(page) -> None:
    page.goto(POSITIONS_URL, wait_until="domcontentloaded")
    best_effort_click(page, ["text=Export", "button:has-text('Export')"])
    best_effort_click(page, ["role=button[name='Export']", "button:has-text('Export')"])


def set_date_via_js(page, from_date: str, to_date: str) -> None:
    page.evaluate(
        """
        ([fromDate, toDate]) => {
          const fromEl = document.getElementById('fromdaterange-datepicker-input');
          const toEl = document.getElementById('todaterange-datepicker-input');
          if (fromEl) { fromEl.value = fromDate; fromEl.dispatchEvent(new Event('input', { bubbles: true })); fromEl.dispatchEvent(new Event('change', { bubbles: true })); }
          if (toEl) { toEl.value = toDate; toEl.dispatchEvent(new Event('input', { bubbles: true })); toEl.dispatchEvent(new Event('change', { bubbles: true })); }
        }
        """,
        [from_date, to_date],
    )


def export_rgl(page, from_date: str, to_date: str) -> None:
    page.goto(RGL_URL, wait_until="domcontentloaded")
    set_date_via_js(page, from_date, to_date)
    best_effort_click(page, ["text=Export", "button:has-text('Export')"])
    page.evaluate("""() => { const el = document.getElementById('summary-card-radio'); if (el) el.click(); }""")
    best_effort_click(page, ["role=button[name='Export']", "button:has-text('Export')"])
    time.sleep(1)
    best_effort_click(page, ["text=Export", "button:has-text('Export')"])
    page.evaluate("""() => { const el = document.getElementById('details-card-radio'); if (el) el.click(); }""")
    best_effort_click(page, ["role=button[name='Export']", "button:has-text('Export')"])


def export_transactions(page, from_date: str | None, to_date: str | None) -> None:
    page.goto(TRANSACTIONS_URL, wait_until="domcontentloaded")
    if from_date and to_date:
        set_date_via_js(page, from_date, to_date)
    best_effort_click(page, ["text=Export", "button:has-text('Export')"])
    best_effort_click(page, ["label:has-text('CSV')", "text=CSV"])
    best_effort_click(page, ["role=button[name='Export']", "button:has-text('Export')"])
    time.sleep(1)
    best_effort_click(page, ["text=Export", "button:has-text('Export')"])
    best_effort_click(page, ["label:has-text('JSON')", "text=JSON"])
    best_effort_click(page, ["role=button[name='Export']", "button:has-text('Export')"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=["positions", "rgl", "transactions"])
    parser.add_argument("--user-data-dir", type=Path, required=True, help="Persistent browser profile dir")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--login-timeout", type=int, default=120)
    parser.add_argument("--from-date", help="Date like 03/01/2026")
    parser.add_argument("--to-date", help="Date like 03/20/2026")
    args = parser.parse_args()

    sync_playwright = require_playwright()
    pw, browser = launch_context(sync_playwright, args.user_data_dir.expanduser(), args.headed)
    try:
        page = browser.new_page()
        page.goto("https://client.schwab.com/", wait_until="domcontentloaded")
        maybe_wait_for_login(page, args.login_timeout)

        if args.task == "positions":
            export_positions(page)
        elif args.task == "rgl":
            if not (args.from_date and args.to_date):
                raise SystemExit("rgl requires --from-date and --to-date")
            export_rgl(page, args.from_date, args.to_date)
        else:
            export_transactions(page, args.from_date, args.to_date)

        print(f"completed_task={args.task}")
        return 0
    finally:
        browser.close()
        pw.stop()


if __name__ == "__main__":
    raise SystemExit(main())
