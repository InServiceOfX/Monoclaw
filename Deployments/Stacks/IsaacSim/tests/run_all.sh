#!/usr/bin/env bash
# Run PhysX validation tests via docker compose run.
#
# Each test creates its own SimulationApp — it must be the main process of a
# fresh container, NOT exec'd into an already-running Isaac Sim container.
# docker compose run starts a throwaway container, runs the test, exits.
#
# Must be run from Stacks/IsaacSim/ (where docker-compose.yml lives):
#   cd Stacks/IsaacSim
#   ./tests/run_all.sh                          # all T1-T8
#   ./tests/run_all.sh test_t1_free_fall.py     # single test
#
# Single-test one-liner (from anywhere):
#   docker compose -f /path/to/Stacks/IsaacSim/docker-compose.yml \
#     run --rm --entrypoint /isaac-sim/python.sh isaac \
#     /isaac-sim/tests/test_t1_free_fall.py
#
# Each test exits 0=PASS, 1=FAIL, 2=ERROR.

set -euo pipefail

PYTHON="/isaac-sim/python.sh"
TEST_DIR="/isaac-sim/tests"

# Confirm docker-compose.yml is reachable (must run from Stacks/IsaacSim/)
if [ ! -f "docker-compose.yml" ]; then
    echo "ERROR: docker-compose.yml not found in $(pwd)"
    echo "Run this script from Stacks/IsaacSim/:"
    echo "  cd $(dirname "$0")/.."
    echo "  ./tests/run_all.sh"
    exit 1
fi

if [ $# -gt 0 ]; then
    TESTS=("$@")
else
    TESTS=(
        test_t1_free_fall.py
        test_t2_harmonic.py
        test_t3_lin_momentum.py
        test_t4_ang_momentum.py
        test_t5_symtop.py
        test_t6_instability.py
        test_t7_polhode.py
        test_t8_quat_drift.py
    )
fi

PASS=0
FAIL=0
ERRORS=()

for test in "${TESTS[@]}"; do
    name="${test%.py}"
    echo ""
    echo "══════════════════════════════════════════════════"
    echo "  Running: $name"
    echo "══════════════════════════════════════════════════"
    # Capture output while still streaming it to the terminal.
    # Isaac Sim's python.sh can exit 0 even on unhandled Python exceptions, so we
    # also require the explicit "PASS" sentinel in stdout to guard against false
    # positives (e.g. ModuleNotFoundError at import time swallowed by python.sh).
    TMPOUT=$(mktemp)
    set +e
    docker compose run --rm --entrypoint "$PYTHON" isaac "$TEST_DIR/$test" 2>&1 | tee "$TMPOUT"
    CODE=${PIPESTATUS[0]}
    set -e
    if [ "$CODE" -eq 0 ] && grep -q " PASS" "$TMPOUT"; then
        PASS=$((PASS+1))
    else
        FAIL=$((FAIL+1))
        if [ "$CODE" -eq 0 ]; then
            ERRORS+=("$name (exit 0 but no PASS sentinel — likely import error)")
        else
            ERRORS+=("$name (exit $CODE)")
        fi
    fi
    rm -f "$TMPOUT"
done

echo ""
echo "══════════════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
if [ ${#ERRORS[@]} -gt 0 ]; then
    for e in "${ERRORS[@]}"; do
        echo "    FAIL: $e"
    done
fi
echo "══════════════════════════════════════════════════"

[ "$FAIL" -eq 0 ]
