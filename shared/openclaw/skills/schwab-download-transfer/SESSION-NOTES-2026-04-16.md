# Session Notes: Schwab Automation — 2026-04-16

## What we tried

### Playwright automation (partially working)
- Installed Playwright + Chromium into Monoclaw's `.venv` via `uv pip install playwright` + `uv run playwright install chromium`
- The Playwright-controlled Chromium browser opens, but **Schwab blocks or breaks login** in the Playwright Chromium profile
  - Ernest could log in to Schwab fine in normal Chrome and Safari
  - In the Playwright Chromium window, login consistently failed or got stuck on auth gateway pages (`sws-gateway-nr.schwab.com`)
  - Likely cause: Schwab detects Playwright's Chromium as a bot (different browser fingerprint, no extensions, clean profile)
- When we pre-authenticated and let the script run, **navigation and export clicking actually worked** (the script successfully found the right pages and clicked the right buttons)
- The real blocker was auth, not the automation logic itself

### Peekaboo / macOS UI automation (permissions blocker)
- Peekaboo is installed (`/opt/homebrew/bin/peekaboo` v3.0.0-beta3)
- It requires **Screen Recording** and **Accessibility** macOS permissions
- These permissions must be granted to the **parent process** that runs Peekaboo
- On Ernest's setup, OpenClaw runs via `openclaw-gateway` (a Node.js daemon launched by launchd, PID parented by launchd directly)
- Granting permissions to **Cursor** (which hosts the OpenClaw dashboard) did not propagate to `openclaw-gateway`
- **Unresolved:** Need to figure out how to grant Screen Recording + Accessibility to `openclaw-gateway` or the specific Node binary it uses
- Possible approaches:
  1. Add `/opt/homebrew/bin/node` to TCC (may be too broad)
  2. Find the exact binary path for `openclaw-gateway` and add that
  3. Run Peekaboo through a wrapper/helper that already has permissions
  4. Use `tccutil` or manual TCC DB edits (requires SIP consideration)

### What actually worked: manual browser + agent file management
- Ernest logged into Schwab in Chrome manually
- Grimlock (OpenClaw agent) guided him through the exact click sequence
- Ernest downloaded all 5 files (Positions, Transactions CSV+JSON, RGL Summary+Details)
- Grimlock moved files to the correct private directories and updated download logs
- This is the reliable fallback until automation is unblocked

## Changes made to scripts in this session

### `schwab_export_playwright.py`
- Added `is_authenticated_page()` with multiple URL and DOM checks (not just URL matching)
- Added `wait_for_any()` helper for reliable element visibility waiting
- Added `trigger_download()` that uses Playwright's `expect_download()` instead of hoping files appear in ~/Downloads
- Hardened `export_positions()`: handles the OK/Export dialog, waits for radio options
- Hardened `export_transactions()`: explicit page load waits, better error messages, aria-label selectors
- Hardened `export_rgl()`: same wait patterns
- Added logging throughout (`clicked=`, `visible=`, `positions_page_url=`, etc.)

### `collect_downloads.py`
- Added `--modified-after` flag (Unix timestamp)
- Collector now only moves files modified after the run started
- This prevents stale files in ~/Downloads from being incorrectly collected

### `schwab_orchestrator.py`
- All three task functions (positions, rgl, transactions) now pass `--modified-after` timestamp to the collector
- Prevents stale-file pollution across all export types

## Data state after this session

- **Positions:** New snapshot `Joint Tenant-Positions-2026-04-16-151421.csv` in `positions/`
- **Transactions:** `next_download_start = 2026-04-16` (covers through 04/15)
- **RGL:** `next_download_start = 2026-04-16`, `last_closed_date = 2026-04-15`
- **Both download-log.json files were repaired** (had broken JSON from prior sessions — duplicate array brackets)

## Recommendations for next agent

1. **Don't fight Playwright auth with Schwab.** It's a losing battle unless someone figures out how to make Playwright's Chromium look identical to real Chrome (extensions, user agent, etc.). Consider using `--channel chrome` to use the system Chrome installation instead of Playwright's bundled Chromium.
2. **Peekaboo is the better path** if permissions can be solved. It drives the real browser, so Schwab can't distinguish it from a human.
3. **The manual flow works** and is fast (~2 minutes for all 5 exports). Don't over-engineer if Ernest is OK doing it weekly.
4. **The Monoclaw `.venv`** has Playwright installed. Use `uv run python` from the repo root to run the scripts.
5. **Download logs are fragile.** The `update_download_log.py` script should validate JSON after writing. See Task 5c in PLANS-schwab-portfolio.md.
