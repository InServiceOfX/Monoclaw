"""
One-time helper: enable omni.isaac.ros2_bridge in the default Isaac Sim extension config.
Run this INSIDE the container if the extension isn't auto-loading:

    /isaac-sim/python.sh scripts/enable_ros2_bridge.py

Not needed if start_isaac.sh's --enable flag works (it usually does in 4.5+).
Kept here for debugging / manual runs.
"""

import carb
import omni.kit.app

manager = omni.kit.app.get_app().get_extension_manager()
if not manager.is_extension_enabled("omni.isaac.ros2_bridge"):
    manager.set_extension_enabled_immediate("omni.isaac.ros2_bridge", True)
    print("omni.isaac.ros2_bridge enabled.")
else:
    print("omni.isaac.ros2_bridge already enabled.")
