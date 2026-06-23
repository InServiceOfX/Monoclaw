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
#     run --rm -T --entrypoint /isaac-sim/python.sh isaac \
#     /isaac-sim/tests/test_t1_free_fall.py
#
# Each test exits 0=PASS, 1=FAIL, 2=ERROR but the container often does NOT
# exit cleanly after os._exit(): NVIDIA RTX background threads keep running
# indefinitely.  run_all.sh therefore reads the PASS/FAIL sentinel from stdout
# rather than relying on the container exit code, and kills the container the
# moment that sentinel is found.

set -euo pipefail

PYTHON="/isaac-sim/python.sh"
TEST_DIR="/isaac-sim/tests"
# Max wall-clock seconds to wait for the PASS/FAIL/ERROR sentinel.
# Isaac Sim startup ≈ 17 s; longest test (T4) runs ≈ 33 s of physics.
# 300 s gives >8× headroom for slow shader-cache builds on first run.
SENTINEL_TIMEOUT=${SENTINEL_TIMEOUT:-300}

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

    TMPOUT=$(mktemp)

    # -T: no pseudo-TTY.  docker-compose.yml has tty:true which, without -T,
    # forces TTY allocation even when stdout is a pipe.  After os._exit() the
    # Python process dies but NVIDIA RTX threads inside the container keep the
    # cgroup alive; docker compose run never returns naturally.  Running in the
    # background lets us kill the container the instant the sentinel appears
    # rather than waiting for those threads to drain.
    set +e
    docker compose run --rm -T --entrypoint "$PYTHON" isaac "$TEST_DIR/$test" \
        2>&1 | tee "$TMPOUT" &
    PIPE_PID=$!
    set -e

    # Poll stdout for the PASS / FAIL / ERROR sentinel emitted by the test.
    ELAPSED=0
    RESULT="timeout"
    while [ "$ELAPSED" -lt "$SENTINEL_TIMEOUT" ]; do
        sleep 1
        ELAPSED=$((ELAPSED + 1))
        if grep -qE "T[0-9]+ (PASS|FAIL|ERROR)" "$TMPOUT" 2>/dev/null; then
            if grep -qE "T[0-9]+ PASS" "$TMPOUT"; then
                RESULT="pass"
            else
                RESULT="fail"
            fi
            break
        fi
    done

    # Kill the container immediately — don't wait for RTX threads to drain.
    docker compose down --remove-orphans --timeout 2 >/dev/null 2>&1 || true
    # Let tee flush remaining buffered output before we print the result line.
    wait "$PIPE_PID" 2>/dev/null || true

    case "$RESULT" in
        pass)
            PASS=$((PASS + 1))
            ;;
        fail)
            echo "  RESULT: $name — FAIL (see output above)"
            FAIL=$((FAIL + 1))
            ERRORS+=("$name (FAIL/ERROR in output)")
            ;;
        timeout)
            echo "  RESULT: $name — TIMEOUT (no sentinel in ${SENTINEL_TIMEOUT}s — startup hang?)"
            FAIL=$((FAIL + 1))
            ERRORS+=("$name (no PASS/FAIL/ERROR sentinel in ${SENTINEL_TIMEOUT}s)")
            ;;
    esac

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
