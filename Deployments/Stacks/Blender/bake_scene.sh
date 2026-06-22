#!/usr/bin/env bash
# Bake the IsaacSim Starship USD into a self-contained starship.blend.
#
# Why: opening a .blend (`blender starship.blend`) is rock-solid, whereas
# importing a USD from a --python script at GUI startup is flaky (the import
# lands in a startup context the visible window doesn't show). Baking once
# sidesteps that and embeds materials + lighting + EEVEE engine.
#
# Re-run this whenever the IsaacSim USD (../IsaacSim/starship/starship.usd)
# changes — e.g. after editing create_stage.py and regenerating the stage.
#
# Usage:  ./bake_scene.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USD_DIR="$HERE/../IsaacSim/starship"
IMAGE="${IMAGE:-monoclaw/blender-starship:4.2.3}"

docker run --rm \
  -v "$USD_DIR:/work/starship:ro" \
  -v "$HERE:/work/out" \
  --entrypoint blender "$IMAGE" \
  -b --python-expr '
import bpy
bpy.ops.wm.usd_import(filepath="/work/starship/starship.usd")
# Drop default startup junk + the green collision capsule for a clean shot.
for name in ["Cube", "Light", "Camera", "Shape"]:
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)
bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
print("FINAL objects:", sorted(o.name for o in bpy.context.scene.objects))
bpy.ops.wm.save_as_mainfile(filepath="/work/out/starship.blend")
print("saved /work/out/starship.blend")
'
echo "Baked: $HERE/starship.blend"
