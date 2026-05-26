"""
create_stage.py — Generate the Starship USD stage for Isaac Sim.

Run inside the Isaac Sim container:
  docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/exts/starship/create_stage.py

Output: /isaac-sim/exts/starship/starship.usd

The stage contains:
  - World/GroundPlane         — static collision plane at y=0
  - World/Starship            — rigid body capsule (simplified Starship geometry)
    └─ World/Starship/Camera  — perspective camera at nose cone for vision tools
    └─ World/Starship/Base    — cylinder mesh (launch pad anchor zone)
  - Physics scene with gravity = -9.81 m/s² (Earth)

Coordinate system: Y-up  (Isaac Sim default)
  +X = East, +Y = Up, +Z = South

Units: meters, kilograms, seconds

The Starship rigid body receives external forces/torques from
starship_controller.py (reads ROS commands → applies forces).
Physics state is read by starship_publisher.py (reads physics → publishes ROS topics).
"""

import os
import sys

# Add Isaac Sim Python path
sys.path.insert(0, "/isaac-sim/kit/python/bin")

try:
    from pxr import Gf, UsdGeom, UsdPhysics, UsdShade, Sdf, Usd, PhysxSchema
except ImportError:
    print("[starship] ERROR: pxr not found. Run this inside Isaac Sim's Python environment.")
    print("  docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/exts/starship/create_stage.py")
    sys.exit(1)

OUTPUT_PATH = "/isaac-sim/exts/starship/starship.usd"

# ── Stage setup ───────────────────────────────────────────────────────────────

print("[starship] Creating Starship USD stage...")

stage = Usd.Stage.CreateNew(OUTPUT_PATH)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)   # 1 USD unit = 1 meter

# ── Default prim ─────────────────────────────────────────────────────────────

world = UsdGeom.Xform.Define(stage, "/World")
stage.SetDefaultPrim(world.GetPrim())

# ── Physics scene ─────────────────────────────────────────────────────────────

physics_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
physics_scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, -1.0, 0.0))
physics_scene.CreateGravityMagnitudeAttr(9.81)   # m/s²

# Enable GPU dynamics for faster simulation
physx_scene = PhysxSchema.PhysxSceneAPI.Apply(physics_scene.GetPrim())
# Enable GPU dynamics if supported (attribute name varies across Isaac Sim versions)
for _attr_fn in ("CreateGpuDynamicsEnabledAttr", "CreateEnableGPUDynamicsAttr"):
    _fn = getattr(physx_scene, _attr_fn, None)
    if _fn:
        _fn(True)
        break

# ── Ground plane ──────────────────────────────────────────────────────────────

ground = UsdGeom.Mesh.Define(stage, "/World/GroundPlane/Plane")
ground.CreatePointsAttr([
    Gf.Vec3f(-500, 0, -500),
    Gf.Vec3f( 500, 0, -500),
    Gf.Vec3f( 500, 0,  500),
    Gf.Vec3f(-500, 0,  500),
])
ground.CreateFaceVertexCountsAttr([4])
ground.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
ground.CreateNormalsAttr([Gf.Vec3f(0, 1, 0)] * 4)

UsdPhysics.CollisionAPI.Apply(ground.GetPrim())
# Static body (no RigidBody API → immovable)

# ── Starship body — simplified capsule ────────────────────────────────────────
# Approximate as a tall capsule: radius ≈ 4.5 m, half-height ≈ 25 m
# Launch position: base at y = 0, tip at y ≈ 50 m

starship_xform = UsdGeom.Xform.Define(stage, "/World/Starship")
# Place so the base is at y = 0 (ground level)
starship_xform.AddTranslateOp().Set(Gf.Vec3d(0, 25, 0))   # center at 25 m AGL

capsule = UsdGeom.Capsule.Define(stage, "/World/Starship/Body")
capsule.CreateRadiusAttr(4.5)       # 9 m diameter
capsule.CreateHeightAttr(50.0)      # 50 m tall cylindrical section
capsule.CreateAxisAttr("Y")         # height along Y (up)
capsule.CreateDisplayColorAttr([Gf.Vec3f(0.8, 0.8, 0.85)])   # light gray

# Physics: rigid body
UsdPhysics.RigidBodyAPI.Apply(starship_xform.GetPrim())
UsdPhysics.CollisionAPI.Apply(capsule.GetPrim())

mass_api = UsdPhysics.MassAPI.Apply(starship_xform.GetPrim())
mass_api.CreateMassAttr(130000.0)   # 130 tonnes (simplified upper stage)

# ── Camera at nose cone ───────────────────────────────────────────────────────
# Position: tip of the capsule = +25 m in Y from the Starship center
# The camera looks forward (down the Z axis in the local frame).

camera_xform = UsdGeom.Xform.Define(stage, "/World/Starship/Camera")
camera_xform.AddTranslateOp().Set(Gf.Vec3d(0, 27, 0))  # just above nose cone
camera_xform.AddRotateXYZOp().Set(Gf.Vec3f(-90, 0, 0))  # look down/forward

camera = UsdGeom.Camera.Define(stage, "/World/Starship/Camera/Sensor")
camera.CreateProjectionAttr(UsdGeom.Tokens.perspective)
camera.CreateFocalLengthAttr(24.0)          # mm, ~85° HFOV
camera.CreateHorizontalApertureAttr(20.955) # mm (standard 35mm sensor)
camera.CreateVerticalApertureAttr(15.2908)  # mm (standard 35mm sensor)
camera.CreateClippingRangeAttr(Gf.Vec2f(0.1, 10000.0))

# ── Variants / annotations ────────────────────────────────────────────────────
# Mark the Starship prim with semantic labels so the vision pipeline can
# identify it in synthetic image data.

stage.GetPrimAtPath("/World/Starship").SetCustomDataByKey(
    "ros2_topic_namespace", "starship"
)

# ── Save ──────────────────────────────────────────────────────────────────────
stage.Save()
print(f"[starship] Stage saved to {OUTPUT_PATH}")
print("[starship] Contents:")
for prim in stage.Traverse():
    indent = "  " * len(prim.GetPath().pathString.split("/"))
    print(f"{indent}{prim.GetPath()} ({prim.GetTypeName()})")
