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

LOGIN_URL_HINTS = (
    "client.schwab.com/Login/SignOn",
    "client.schwab.com/secure/login",
    "schwab.com/login",
)


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


def is_authenticated_page(page) -> bool:
    url = page.url or ""
    if "client.schwab.com/app/accounts" in url:
        return True
    if any(hint in url for hint in LOGIN_URL_HINTS):
        return False
    checks = [
        "text=Accounts",
        "text=Positions",
        "text=History",
        "text=Transactions",
        "text=Move Money",
        "[data-testid='accounts-menu']",
        "button:has-text('Export')",
    ]
    for selector in checks:
        try:
            if page.locator(selector).first.is_visible(timeout=500):
                return True
        except Exception:
            continue
    return False


def maybe_wait_for_login(page, timeout_seconds: int) -> None:
    print("Waiting for authenticated Schwab session. Log in manually if needed...")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_authenticated_page(page):
            print(f"authenticated_url={page.url}")
            return
        time.sleep(1)
    print(f"Login wait expired at url={page.url}; continuing anyway.")


def best_effort_click(page, selectors: list[str], timeout: int = 3000) -> bool:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            locator.click(timeout=timeout)
            print(f"clicked={selector}")
            return True
        except Exception:
            continue
    return False


def wait_for_any(page, selectors: list[str], timeout_ms: int = 15000) -> bool:
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        for selector in selectors:
            try:
                if page.locator(selector).first.is_visible(timeout=300):
                    print(f"visible={selector}")
                    return True
            except Exception:
                continue
        time.sleep(0.5)
    return False


def trigger_download(page, selectors: list[str], wait_timeout_ms: int = 20000):
    with page.expect_download(timeout=wait_timeout_ms) as download_info:
        if not best_effort_click(page, selectors, timeout=8000):
            raise SystemExit(f"Unable to click download trigger from url={page.url}")
    download = download_info.value
    suggested = download.suggested_filename
    print(f"downloaded={suggested}")
    return download


def export_positions(page) -> None:
    page.goto(POSITIONS_URL, wait_until="domcontentloaded")
    wait_for_any(
        page,
        [
            "text=Positions",
            "text=Export",
            "button:has-text('Export')",
            "[aria-label='Export']",
        ],
        timeout_ms=20000,
    )
    print(f"positions_page_url={page.url}")
    opened = best_effort_click(
        page,
        ["text=Export", "button:has-text('Export')", "[aria-label='Export']", "a:has-text('Export')"],
        timeout=8000,
    )
    if not opened:
        raise SystemExit(f"Unable to open positions export dialog at url={page.url}")
    dialog_ready = wait_for_any(
        page,
        [
            "role=button[name='OK']",
            "button:has-text('OK')",
            "role=button[name='Ok']",
            "button:has-text('Ok')",
            "role=button[name='Export']",
            "button:has-text('Export')",
            "text=CSV",
            "input[type=radio]",
        ],
        timeout_ms=10000,
    )
    if not dialog_ready:
        raise SystemExit(f"Positions export dialog did not appear at url={page.url}")
    if not best_effort_click(page, ["label:has-text('CSV')", "text=CSV"]):
        print("warning=unable_to_select_positions_csv_explicitly")
    trigger_download(
        page,
        [
            "role=button[name='OK']",
            "button:has-text('OK')",
            "role=button[name='Ok']",
            "button:has-text('Ok')",
            "role=button[name='Export']",
            "button:has-text('Export')",
        ],
    )


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
    wait_for_any(page, ["text=Realized Gain", "text=Export", "button:has-text('Export')"], timeout_ms=20000)
    set_date_via_js(page, from_date, to_date)
    if not best_effort_click(page, ["text=Export", "button:has-text('Export')"], timeout=8000):
        raise SystemExit(f"Unable to open RGL export dialog at url={page.url}")
    page.evaluate("""() => { const el = document.getElementById('summary-card-radio'); if (el) el.click(); }""")
    trigger_download(page, ["role=button[name='Export']", "button:has-text('Export')"])
    time.sleep(1)
    if not best_effort_click(page, ["text=Export", "button:has-text('Export')"], timeout=8000):
        raise SystemExit("Unable to reopen RGL export dialog for details")
    page.evaluate("""() => { const el = document.getElementById('details-card-radio'); if (el) el.click(); }""")
    trigger_download(page, ["role=button[name='Export']", "button:has-text('Export')"])


def export_transactions(page, from_date: str | None, to_date: str | None) -> None:
    page.goto(TRANSACTIONS_URL, wait_until="domcontentloaded")
    wait_for_any(
        page,
        [
            "text=Transactions",
            "text=History",
            "text=Export",
            "button:has-text('Export')",
        ],
        timeout_ms=20000,
    )
    print(f"transactions_page_url={page.url}")
    if from_date and to_date:
        set_date_via_js(page, from_date, to_date)
        print(f"set_transaction_dates={from_date}..{to_date}")
        time.sleep(1)
    export_opened = best_effort_click(
        page,
        [
            "text=Export",
            "button:has-text('Export')",
            "a:has-text('Export')",
            "[aria-label='Export']",
        ],
        timeout=8000,
    )
    if not export_opened:
        raise SystemExit(f"Unable to open transactions export dialog at url={page.url}")
    print(f"export_dialog_attempt_url={page.url}")
    radio_ready = wait_for_any(page, ["label:has-text('CSV')", "text=CSV", "input[type=radio]"], timeout_ms=10000)
    if not radio_ready:
        raise SystemExit(f"Transactions export dialog did not appear after clicking Export at url={page.url}")
    if not best_effort_click(page, ["label:has-text('CSV')", "text=CSV"]):
        print("warning=unable_to_select_csv_explicitly")
    trigger_download(page, ["role=button[name='Export']", "button:has-text('Export')"])
    time.sleep(2)
    if not best_effort_click(page, ["text=Export", "button:has-text('Export')", "a:has-text('Export')", "[aria-label='Export']"], timeout=8000):
        raise SystemExit("Unable to reopen transactions export dialog for JSON")
    radio_ready = wait_for_any(page, ["label:has-text('JSON')", "text=JSON", "input[type=radio]"], timeout_ms=10000)
    if not radio_ready:
        raise SystemExit(f"Transactions export dialog did not appear for JSON at url={page.url}")
    if not best_effort_click(page, ["label:has-text('JSON')", "text=JSON"]):
        print("warning=unable_to_select_json_explicitly")
    trigger_download(page, ["role=button[name='Export']", "button:has-text('Export')"])
    time.sleep(3)


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
