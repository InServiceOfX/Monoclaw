#!/bin/bash
# Diagnose CycloneDDS discovery between isaac-sim and rosa-ros2 containers.
# Run from the host AFTER Isaac Sim is fully booted.
#
# Usage: ./scripts/diagnose_dds.sh

set -e
echo "=== DDS Discovery Diagnostic ==="
echo ""

# ── 1. Host-side UDP socket check ─────────────────────────────────────────────
echo "1. DDS participant ports on host:"
ss -ulnp 2>/dev/null | grep -E '740[0-9]' || echo "   (no DDS ports found — bridge may not be running)"
echo ""

# ── 2. Topics from inside rosa-ros2 ───────────────────────────────────────────
echo "2. ros2 topic list from rosa-ros2 (30s wait):"
docker exec rosa-ros2 bash -ic "
  ros2 daemon stop 2>/dev/null || true
  ros2 daemon start 2>/dev/null || true
  timeout 30 ros2 topic list 2>&1
" 2>&1 | grep -v 'job control\|terminal' || true
echo ""

# ── 3. Topic count ────────────────────────────────────────────────────────────
TOPIC_COUNT=$(docker exec rosa-ros2 bash -ic "ros2 topic list 2>/dev/null | wc -l" 2>/dev/null | tr -d '[:space:]' || echo 0)
echo "3. Topic count visible from rosa-ros2: $TOPIC_COUNT"
if [ "$TOPIC_COUNT" -gt 2 ]; then
    echo "   ✅ DDS discovery is working! (>2 topics means Isaac topics are visible)"
else
    echo "   ⚠️  Only base topics visible — /clock may not be publishing yet"
    echo "      or DDS discovery is failing"
fi
echo ""

# ── 4. CycloneDDS interface check ─────────────────────────────────────────────
echo "4. Network interfaces on host:"
cat /proc/net/if_inet6 | awk '{print "   ", $NF}' | sort -u 2>/dev/null || true
echo ""

# ── 5. Probe from inside isaac-sim using its own rclpy ────────────────────────
echo "5. Topics from inside isaac-sim (15s probe):"
docker exec isaac-sim bash -c "
  export LD_LIBRARY_PATH=/isaac-sim/exts/isaacsim.ros2.bridge/humble/lib:\$LD_LIBRARY_PATH
  export PYTHONPATH=/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy:\$PYTHONPATH
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  export ROS_DOMAIN_ID=0
  /isaac-sim/kit/python/bin/python3 -c \"
import sys, time
sys.path.insert(0, '/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy')
import rclpy
rclpy.init()
node = rclpy.create_node('diag_probe')
time.sleep(10)  # wait for DDS discovery
topics = node.get_topic_names_and_types()
print('Topics seen from isaac internal rclpy:', [t for t,_ in topics])
node.destroy_node()
rclpy.shutdown()
\" 2>&1
" 2>&1 | grep -v '^\[' || true
echo ""

# ── 6. Try echo on /clock ──────────────────────────────────────────────────────
echo "6. Attempting to echo /clock from rosa-ros2 (5s):"
docker exec rosa-ros2 bash -ic "timeout 5 ros2 topic echo /clock --once 2>&1" 2>&1 | grep -v 'job control\|terminal' || true
echo ""

echo "=== Diagnostic complete ==="
echo ""
echo "If /clock is not visible from rosa-ros2 but isaac-sim sees it internally:"
echo "  → CycloneDDS interface mismatch"
echo "  → Add CYCLONEDDS_URI to both containers pointing to cyclonedds.xml"
echo ""
echo "If /clock is visible from isaac-sim's internal rclpy but NOT from rosa-ros2:"
echo "  → Same CycloneDDS interface mismatch, but between containers"
echo ""
echo "If /clock is NOT visible from isaac-sim's own probe either:"
echo "  → The OmniGraph clock publisher may not have initialized yet"
echo "  → Check: docker logs isaac-sim | grep 'rosa.*clock\|OmniGraph'"
