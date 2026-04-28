#!/usr/bin/env bash
# Run after downloading fresh Schwab CSVs.
# Updates master-balances.csv, then re-runs rec matcher + performance scorer.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_DIR/.venv/bin/python"
SCRIPTS="$REPO_DIR/Python/finance/scripts"
SCHWAB_BASE="${SCHWAB_BASE_DIR:-$HOME/.openclaw/workspace/Data/Private/finance/schwab-brokerage}"
BAL_DIR="$SCHWAB_BASE/balances"

echo "=== daily_finance_update.sh — $(date '+%Y-%m-%d %H:%M') ==="

# 1. Rebuild master-balances.csv from all balance snapshots
echo ""
echo "--- Rebuilding master-balances.csv ---"
"$VENV" -m Python.finance.schwab_balances_processor rebuild \
  --dir "$BAL_DIR" 2>&1 || echo "(balances rebuild failed — continuing)"

# 2. Match recommendations to transactions
echo ""
echo "--- Matching recommendations to transactions ---"
"$VENV" "$SCRIPTS/match_recommendations.py"

# 3. Compute forward returns (only fills in prices that are now available)
echo ""
echo "--- Computing forward-return performance ---"
"$VENV" "$SCRIPTS/compute_performance.py"

echo ""
echo "=== Done. Refresh the Recs tab in the dashboard. ==="
