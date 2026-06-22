#!/usr/bin/env python3
"""
make_pointed_nose.py — fix starship_v2.stl's broken nose.

starship_v2.stl has a detailed body/flaps/engines but its nose is modeled as an
inverted open funnel (wide opening at the +Y nose end, tapering to a point going
down). Once the vehicle is stood upright that looks like an upward-facing nozzle.

This keeps the body, engines, and flaps and replaces the funnel with a proper
pointed cone, writing starship_v2_pointednose.stl.

Geometry (STL frame, Y-up, before create_stage's +90deg X rotation):
  Y -4..4   engines + lower body      Y 6..18  aft flaps (radius ~8.5)
  Y 18..36  clean body cylinder (R~4.5)   Y 36..50  funnel (removed) + fwd flaps

Classification per facet:
  - flap   : max vertex radius > FLAP_R           -> keep (fwd + aft flaps)
  - body   : max vertex Y <= Y_CUT+0.5            -> keep (body, engines)
  - funnel : above the cut and within body radius -> drop
Then graft a cone: base ring (Y_CUT, R_BODY) -> apex (0, Y_TIP, 0), plus a base
cap so it isn't see-through.

Usage:  python make_pointed_nose.py [in.stl] [out.stl]   (pure stdlib)
"""
import re, math, sys, statistics

src = sys.argv[1] if len(sys.argv) > 1 else "starship_v2.stl"
dst = sys.argv[2] if len(sys.argv) > 2 else "starship_v2_pointednose.stl"

Y_CUT, FLAP_R, Y_TIP, SEG = 36.0, 5.5, 52.0, 48


def rad(v):
    return math.hypot(v[0], v[2])


def normal(f):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = f
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / L, ny / L, nz / L


facets, cur = [], []
for line in open(src):
    m = re.match(r'\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)', line)
    if m:
        cur.append((float(m[1]), float(m[2]), float(m[3])))
        if len(cur) == 3:
            facets.append(cur); cur = []

wall = [rad(v) for f in facets for v in f if 28 <= v[1] <= Y_CUT and 3.0 <= rad(v) <= FLAP_R]
R_BODY = round(statistics.median(wall), 3)

kept, removed = [], 0
for f in facets:
    if max(rad(v) for v in f) > FLAP_R or max(v[1] for v in f) <= Y_CUT + 0.5:
        kept.append(f)
    else:
        removed += 1

ring = [(R_BODY * math.cos(2 * math.pi * i / SEG), Y_CUT, R_BODY * math.sin(2 * math.pi * i / SEG))
        for i in range(SEG)]
apex, cap_c = (0.0, Y_TIP, 0.0), (0.0, Y_CUT, 0.0)
nose = []
for i in range(SEG):
    a, b = ring[i], ring[(i + 1) % SEG]
    nose.append([a, b, apex])    # cone lateral face
    nose.append([b, a, cap_c])   # base cap (so the cone isn't see-through)

out = kept + nose
with open(dst, "w") as o:
    o.write("solid starship_v2_pointednose\n")
    for f in out:
        n = normal(f)
        o.write(f" facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n  outer loop\n")
        for v in f:
            o.write(f"   vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}\n")
        o.write("  endloop\n endfacet\n")
    o.write("endsolid starship_v2_pointednose\n")

print(f"R_BODY={R_BODY}  kept={len(kept)} removed_funnel={removed} added_nose={len(nose)} total={len(out)}")
print(f"wrote {dst}")
