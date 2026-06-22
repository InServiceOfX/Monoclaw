"""
create_stage.py — Generate the Starship USD stage for Isaac Sim.

Scene: Starship floating in Mars orbit / low-altitude proximity ops.
  - Starship spawns at 1000 m AGL, pointing nose-up (+Z)
  - Gravity: Mars (3.72 m/s²) — hover throttle ≈ 0.033
  - Ground: Martian regolith surface (rust-red, 10 km × 10 km)
  - Skybox: space black with a dim star-dome tint
  - Sun: harsh directional light at low angle (Mars orbit sun ~43% of Earth flux)
  - Starship mesh from starship_v2.stl (ogive nose, 4 flaps, 6 Raptors)

Run inside the Isaac Sim container:
  docker exec isaac-sim /isaac-sim/python.sh /isaac-sim/exts/starship/create_stage.py

Output: /isaac-sim/exts/starship/starship.usd

Stage hierarchy:
  /World/PhysicsScene        — Mars gravity (3.72 m/s²) + GPU dynamics
  /World/MarsSurface         — static collision slab + Martian texture
  /World/Starship            — RigidBody root at z=1000
    /Visual                  — UsdGeom.Mesh from starship_v2.stl
    /Collider                — UsdGeom.Capsule (cheap physics collision)
    /Camera                  — perspective sensor at nose cone
  /World/Lighting            — Mars sun + deep space dome

Coordinate system: Z-up  (robotics / ROS REP-103 convention)
  +X = East, +Y = North, +Z = Up. z=0 is the Martian surface; altitude = world-Z.
  The starship_v2.stl is authored long-axis-along-Y, so its points are rotated
  +90deg about X at load time (x, y, z) -> (x, -z, y) to stand nose-up along +Z.

Units: meters, kilograms, seconds
"""

import math
import os
import re
import sys

# ---------------------------------------------------------------------------
# Geometry constants — match starship_v2.stl exactly
# ---------------------------------------------------------------------------

# The STL was generated with Y=0 at engine plane, Y=50 at nose tip; _load_stl_mesh
# rotates it +90deg about X so the long axis stands along +Z (Z-up stage).
# Paths are env-overridable so this can also run standalone (usd-core, no Isaac)
# to regenerate the visual stage for re-baking the Blender scene.
# starship_v2_pointednose.stl = the detailed starship_v2 body/flaps/engines with
# its broken inverted-funnel nose cut off and a proper pointed cone grafted on
# (see make_pointed_nose.py). Alternatives via STARSHIP_STL env:
#   starship_simple.stl  — clean pointed nose, low detail
#   starship_v2.stl      — detailed body but inverted-funnel nose (broken)
STL_PATH    = os.environ.get("STARSHIP_STL", "/isaac-sim/exts/starship/starship_v2_pointednose.stl")
OUTPUT_PATH = os.environ.get("STARSHIP_USD_OUT", "/isaac-sim/exts/starship/starship.usd")

# ── Scene constants ────────────────────────────────────────────────────────
GRAVITY_BODY    = "mars"
GRAVITY_M_S2    = 3.72          # Mars surface gravity
SPAWN_ALTITUDE  = 1_000.0       # m — Starship starts here (free-float, no ground contact)

# Physics capsule — cheaper than mesh collision
CAPSULE_AXIAL_OFFSET = 25.0   # capsule centre along +Z relative to Starship origin
CAPSULE_RADIUS   = 4.5    # m
CAPSULE_HEIGHT   = 44.0   # m (cylinder section only, not counting hemispheres)
MASS_KG          = 830_000.0

# ── Isaac Sim Python path
sys.path.insert(0, "/isaac-sim/kit/python/bin")

try:
    from pxr import Gf, UsdGeom, UsdPhysics, UsdShade, Sdf, Usd
except ImportError:
    print("[starship] ERROR: pxr (USD) not found. Run inside Isaac Sim's Python,")
    print("  or in a venv with usd-core installed (uv pip install usd-core).")
    sys.exit(1)

# PhysxSchema is an Omniverse extension schema — present inside Isaac Sim, absent
# in a plain usd-core install. Guard it so this script can also regenerate the
# visual stage standalone (to re-bake the Blender scene) without Isaac running.
try:
    from pxr import PhysxSchema
except ImportError:
    PhysxSchema = None
    print("[starship] PhysxSchema unavailable — authoring base UsdPhysics only")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_stl_mesh(path: str) -> tuple[list, list]:
    """
    Parse an ASCII STL file and return (points, face_vertex_indices).
    Returns flat lists: points = [Gf.Vec3f, ...], indices = [0,1,2, 3,4,5, ...]
    """
    points = []
    with open(path) as f:
        for line in f:
            m = re.match(r'\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)', line)
            if m:
                points.append(Gf.Vec3f(float(m.group(1)),
                                       float(m.group(2)),
                                       float(m.group(3))))
    # Rotate +90deg about X so the STL's long axis (+Y, nose at Y=50) stands
    # along +Z for the Z-up stage:  (x, y, z) -> (x, -z, y).
    points = [Gf.Vec3f(p[0], -p[2], p[1]) for p in points]
    indices = list(range(len(points)))
    return points, indices


def _define_pbr_material(stage, prim_path: str,
                         diffuse_color: Gf.Vec3f,
                         metallic: float = 0.0,
                         roughness: float = 0.5) -> UsdShade.Material:
    """
    Create a UsdPreviewSurface PBR material and return it.
    Attach to geometry with (Apply the schema first so readers see it):
        UsdShade.MaterialBindingAPI.Apply(prim)
        UsdShade.MaterialBindingAPI(prim).Bind(mat)
    """
    mat = UsdShade.Material.Define(stage, prim_path)
    shader = UsdShade.Shader.Define(stage, prim_path + "/PBRShader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor",    Sdf.ValueTypeNames.Color3f).Set(diffuse_color)
    shader.CreateInput("metallic",        Sdf.ValueTypeNames.Float).Set(metallic)
    shader.CreateInput("roughness",       Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateInput("useSpecularWorkflow", Sdf.ValueTypeNames.Int).Set(0)
    mat.CreateSurfaceOutput().ConnectToSource(
        shader.ConnectableAPI(), "surface"
    )
    return mat


# ---------------------------------------------------------------------------
# Stage creation
# ---------------------------------------------------------------------------

print("[starship] Creating Starship USD stage...")

# CreateNew fails when called from within a running Isaac Sim session because
# the Sdf layer registry still holds starship.usd's identifier (it's the loaded
# stage). CreateInMemory() + Export() bypasses the registry check entirely.
stage = Usd.Stage.CreateInMemory()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)   # 1 USD unit = 1 metre

world = UsdGeom.Xform.Define(stage, "/World")
stage.SetDefaultPrim(world.GetPrim())

# ── Physics scene ──────────────────────────────────────────────────────────

physics_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
physics_scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))   # Z-up: gravity along -Z
physics_scene.CreateGravityMagnitudeAttr(GRAVITY_M_S2)   # Mars: 3.72 m/s²

if PhysxSchema is not None:
    physx_scene = PhysxSchema.PhysxSceneAPI.Apply(physics_scene.GetPrim())
    for _attr_fn in ("CreateGpuDynamicsEnabledAttr", "CreateEnableGPUDynamicsAttr"):
        _fn = getattr(physx_scene, _attr_fn, None)
        if _fn:
            _fn(True)
            break

# ── Martian surface — 10 km × 10 km rust-red regolith ────────────────────
# Flat ground in the X-Y plane (Z-up). Parent Xform at z=-0.5, local z=+0.5,
# so the surface sits exactly at world z=0. Starship spawns at z=SPAWN_ALTITUDE.

surface_xform = UsdGeom.Xform.Define(stage, "/World/MarsSurface")
surface_xform.AddTranslateOp().Set(Gf.Vec3d(0, 0, -0.5))

# Authored as a flat Mesh quad (not an analytic UsdGeom.Cube): Blender's USD
# importer drops material bindings on analytic prims (Cube/Capsule/Sphere) but
# keeps them on real Mesh prims.
surface_mesh = UsdGeom.Mesh.Define(stage, "/World/MarsSurface/Geom")
surface_mesh.CreatePointsAttr([
    Gf.Vec3f(-5_000.0, -5_000.0, 0.5),
    Gf.Vec3f( 5_000.0, -5_000.0, 0.5),
    Gf.Vec3f( 5_000.0,  5_000.0, 0.5),
    Gf.Vec3f(-5_000.0,  5_000.0, 0.5),
])
surface_mesh.CreateFaceVertexCountsAttr([4])
surface_mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
surface_mesh.CreateSubdivisionSchemeAttr("none")
# Rust-red / iron-oxide colour of Martian regolith
surface_mesh.CreateDisplayColorAttr([Gf.Vec3f(0.55, 0.22, 0.10)])
UsdPhysics.CollisionAPI.Apply(surface_mesh.GetPrim())

# Martian regolith PBR material — fine dusty surface, not shiny
mat_mars = _define_pbr_material(
    stage, "/World/Materials/MartianRegolith",
    diffuse_color=Gf.Vec3f(0.55, 0.22, 0.10),
    metallic=0.0, roughness=0.95
)
# Apply the MaterialBindingAPI schema before binding — without Apply() the
# binding relationship is authored but the schema isn't listed in apiSchemas,
# so downstream readers (Blender's USD importer) warn and drop the material,
# rendering the prim flat grey.
UsdShade.MaterialBindingAPI.Apply(surface_mesh.GetPrim())
UsdShade.MaterialBindingAPI(surface_mesh.GetPrim()).Bind(mat_mars)

# ── Starship rigid body root ───────────────────────────────────────────────
# Starship spawns at SPAWN_ALTITUDE (1000 m AGL) in free-float. After the mesh
# rotation the prim origin is at the engine plane (z=0 local) and the nose tip
# at z=50 local. Set Z = SPAWN_ALTITUDE so engine bells are at z=1000.

starship_xform = UsdGeom.Xform.Define(stage, "/World/Starship")
starship_xform.AddTranslateOp().Set(Gf.Vec3d(0, 0, SPAWN_ALTITUDE))

UsdPhysics.RigidBodyAPI.Apply(starship_xform.GetPrim())
if PhysxSchema is not None:
    PhysxSchema.PhysxRigidBodyAPI.Apply(starship_xform.GetPrim())

mass_api = UsdPhysics.MassAPI.Apply(starship_xform.GetPrim())
mass_api.CreateMassAttr(MASS_KG)

# Approximate moment of inertia for a thin rod: I = m*L²/12
# L ≈ 50 m, m = 130,000 kg  →  I ≈ 2.7e10 kg·m²
# (rough; PhysX will use this if set, otherwise it auto-computes from collider)
# mass_api.CreateDiagonalInertiaAttr(Gf.Vec3f(2.7e10, 1e9, 2.7e10))

stage.GetPrimAtPath("/World/Starship").SetCustomDataByKey(
    "ros2_topic_namespace", "starship"
)

# ── Visual mesh — loaded from starship_v2.stl ─────────────────────────────

if os.path.isfile(STL_PATH):
    print(f"[starship] Loading visual mesh from {STL_PATH} ...")
    points, indices = _load_stl_mesh(STL_PATH)
    n_tris = len(indices) // 3

    visual_mesh = UsdGeom.Mesh.Define(stage, "/World/Starship/Visual")
    visual_mesh.CreatePointsAttr(points)
    visual_mesh.CreateFaceVertexCountsAttr([3] * n_tris)
    visual_mesh.CreateFaceVertexIndicesAttr(indices)
    visual_mesh.CreateSubdivisionSchemeAttr("none")   # flat-shaded triangles
    # No CollisionAPI on this prim — collision is handled by the capsule below

    # ── Body material: stainless steel (silver-metallic) ─────────────────
    mat_starship = _define_pbr_material(
        stage, "/World/Materials/StarshipBody",
        diffuse_color=Gf.Vec3f(0.78, 0.78, 0.82),   # brushed stainless
        metallic=0.90, roughness=0.25
    )
    UsdShade.MaterialBindingAPI.Apply(visual_mesh.GetPrim())   # see MarsSurface note
    UsdShade.MaterialBindingAPI(visual_mesh.GetPrim()).Bind(mat_starship)
    print(f"[starship] Visual mesh: {len(points)} verts, {n_tris} triangles")
else:
    print(f"[starship] WARNING: {STL_PATH} not found — using capsule for visual too")
    fallback = UsdGeom.Capsule.Define(stage, "/World/Starship/Visual")
    fallback.CreateRadiusAttr(CAPSULE_RADIUS)
    fallback.CreateHeightAttr(CAPSULE_HEIGHT)
    fallback.CreateAxisAttr("Z")
    fallback.AddTranslateOp().Set(Gf.Vec3d(0, 0, CAPSULE_AXIAL_OFFSET))
    fallback.CreateDisplayColorAttr([Gf.Vec3f(0.8, 0.8, 0.85)])

# ── Collision capsule (lightweight, inside the visual mesh) ───────────────
# RigidBodyAPI is on the parent Xform; CollisionAPI goes on this capsule child.
# PhysX auto-computes inertia from the capsule geometry + mass.

collider_xform = UsdGeom.Xform.Define(stage, "/World/Starship/Collider")
collider_xform.AddTranslateOp().Set(Gf.Vec3d(0, 0, CAPSULE_AXIAL_OFFSET))

capsule = UsdGeom.Capsule.Define(stage, "/World/Starship/Collider/Shape")
capsule.CreateRadiusAttr(CAPSULE_RADIUS)
capsule.CreateHeightAttr(CAPSULE_HEIGHT)
capsule.CreateAxisAttr("Z")
capsule.CreateDisplayColorAttr([Gf.Vec3f(0.0, 1.0, 0.0)])  # green — hidden at runtime

UsdPhysics.CollisionAPI.Apply(capsule.GetPrim())

# PhysX collision hint (skipped when running standalone without Omniverse).
if PhysxSchema is not None:
    physx_collision = PhysxSchema.PhysxCollisionAPI.Apply(capsule.GetPrim())
# "capsule" approximation is exact for our capsule shape
# No further override needed — UsdGeom.Capsule already maps to a capsule shape.

# ── Camera at nose cone ───────────────────────────────────────────────────
# z=50 is the nose tip (after the +90deg mesh rotation). Camera at z=48, just
# below the tip. A default camera looks down its local -Z, i.e. toward the
# engines / ground — a downward nose-cam during descent.

camera_xform = UsdGeom.Xform.Define(stage, "/World/Starship/Camera")
camera_xform.AddTranslateOp().Set(Gf.Vec3d(0, 0, 48.0))

camera = UsdGeom.Camera.Define(stage, "/World/Starship/Camera/Sensor")
camera.CreateProjectionAttr(UsdGeom.Tokens.perspective)
camera.CreateFocalLengthAttr(24.0)
camera.CreateHorizontalApertureAttr(20.955)
camera.CreateVerticalApertureAttr(15.2908)
camera.CreateClippingRangeAttr(Gf.Vec2f(0.1, 10000.0))

# ── Scene lighting — dome + directional key light ─────────────────────────
# Isaac Sim needs at least one light for RTX rendering to look good.
# A distant directional light simulates the sun; a dome provides ambient fill.

lighting_xform = UsdGeom.Xform.Define(stage, "/World/Lighting")

# Mars sun — 43% of Earth intensity, slightly orange-tinted, low on horizon
try:
    from pxr import UsdLux
    sun = UsdLux.DistantLight.Define(stage, "/World/Lighting/MarsSun")
    sun.CreateIntensityAttr(3500.0)                    # brighter key so stainless reads on camera
    sun.CreateColorAttr(Gf.Vec3f(1.0, 0.92, 0.80))   # warm orange-white
    sun_xform = UsdGeom.Xformable(sun.GetPrim())
    # Z-up: a DistantLight emits along local -Z; tilt it so sunlight comes from
    # above at an angle (lights the standing hull's side + the ground).
    sun_xform.AddRotateXYZOp().Set(Gf.Vec3f(-45, 0, 30))

    # Deep space dome — dim ambient fill (raised from 50 so the steel hull and
    # Mars surface aren't crushed to black in EEVEE; still reads as space).
    dome = UsdLux.DomeLight.Define(stage, "/World/Lighting/DeepSpace")
    dome.CreateIntensityAttr(250.0)                    # ambient fill
    dome.CreateColorAttr(Gf.Vec3f(0.05, 0.05, 0.10)) # dark blue-tinted space
    print(f"[starship] Lighting: Mars sun + deep-space dome ({GRAVITY_BODY} scene)")
except Exception as exc:
    print(f"[starship] Lighting skipped (UsdLux unavailable): {exc}")

# ── Save ──────────────────────────────────────────────────────────────────

# Export to a temp path (not in the Sdf layer registry) then rename to
# atomically overwrite the real file. The registry keeps the old layer
# object alive, but the file on disk is updated for the next scene load.
_tmp = OUTPUT_PATH + ".tmp"
stage.Export(_tmp)
import shutil
shutil.move(_tmp, OUTPUT_PATH)
print(f"[starship] Stage written → {OUTPUT_PATH}")
print("[starship] Scene hierarchy:")
for prim in stage.Traverse():
    depth = len(prim.GetPath().pathString.split("/")) - 1
    print(f"{'  '*depth}{prim.GetPath()} ({prim.GetTypeName()})")
print()
print("[starship] To load in Isaac Sim:")
print("  curl -X POST http://localhost:8282/scene/load \\")
print(f"       -d '{{\"path\":\"{OUTPUT_PATH}\"}}'")
