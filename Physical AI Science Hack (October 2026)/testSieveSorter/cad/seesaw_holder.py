"""Seesaw holder box and catch pan: frame_holder.py's box re-made for a tray that tips about a pivot across
its middle (docs/SYSTEM.md section 3), with neighbours tipping opposite ways.

    seesaw_holder      the holder box with no +X mounting tab and a pivot lug on each long wall
    seesaw_catch_pan   the bottom level: a solid floor, CATCH_DEPTH deeper than a box, and an inward lip

Changes from frame_holder.py (same 140 x 104 x 25 body, same pocket, ledge and open bottom, so every
insert, plinko layer, gated container and the breaker layer drops in unchanged):
- No +X tab. A middle pivot doesn't need it, and the tab ends decide how close the levels can hang
  (seesaw_tower.py): with it gone, levels hang about half as far apart at +/-10 deg, so specimens drop
  about half as far between levels (the clump session found those drops give the largest impact force).
- A pivot lug on the middle of each long wall: a D-shaped plate LUG_W wide standing LUG_T out from the
  wall, from the bed up to a half-round top, with a blind PIN_D hole along Y at PIVOT_Z (mid-height, the
  pivot the sim assumes). A 6 mm rod or shoulder bolt from each post of the rig goes in; the two holes
  are coaxial. The lug prints from the bed, so nothing overhangs but the small hole's top.
- No finger notches: the lugs sit where they were. Lift the box off its pins to swap inserts, or reach
  the pull tabs from above (levels hang 50 mm or more apart).

The catch pan keeps a box's top 25 mm (the same rim, and the pivot the same 12.5 mm under it) and reaches
CATCH_DEPTH further down, where nothing hangs below it, so it doesn't change the pitch. Its rim has an
inward lip, LIP_T thick with a 45 deg underside (prints without supports), leaving exactly the 122 x 82
open bottom of the box above: everything falling from above still lands in the pan, and grains that
bounce at the ends hit the lip instead of leaving (the 11:20 renders lost grains over the ends).

Prints with the flat bottom on the bed, no supports.

Run from this folder:  <venv python> seesaw_holder.py [seesaw_holder seesaw_catch_pan]
"""
import json
import sys
import cadquery as cq
from cadkit import export_all
import frame_holder as box

PIVOT_Z = box.H / 2               # pivot height above the box bottom (the sim's assumption)
PIN_D = 6.2                       # blind hole for a 6 mm rod or shoulder bolt
PIN_DEPTH = 8.0                   # from the lug face: through the lug and half the wall
LUG_W, LUG_T = 16.0, 6.0          # lug width along X, how far it stands out from the long wall
CATCH_DEPTH = 20.0                # the catch pan reaches this much further down than a box
LIP_T = 2.0                       # the pan's inward lip: flat top thickness, then a 45 deg underside
FLOOR_T = 3.0                     # the pan's solid floor


def cyl_y(r, y0, length, z):
    """A cylinder along Y from y0, `length` long (negative: toward -Y), centred on x = 0 at height z."""
    d = 1 if length > 0 else -1
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, abs(length), cq.Vector(0, y0, z), cq.Vector(0, d, 0)))


def walls(h):
    """A ring of the box's outer walls, h tall."""
    return (cq.Workplane("XY").box(box.L, box.W, h, centered=(True, True, False))
            .cut(cq.Workplane("XY").box(box.L - 2 * box.WALL, box.W - 2 * box.WALL, h, centered=(True, True, False))))


def body():
    """frame_holder's box with the +X tab cut off at the end wall and the finger notches filled."""
    b = box.frame().intersect(cq.Workplane("XY").box(box.L, box.W, box.H, centered=(True, True, False)))
    return b.union(walls(box.H).intersect(cq.Workplane("XY").box(box.NOTCH_W + 2, box.W, box.H,
                                                                 centered=(True, True, False))))


def with_lugs(part, pivot_z):
    """Add a pivot lug to each long wall at x = 0 and drill the blind pin holes, centred pivot_z up."""
    r = LUG_W / 2
    for sy in (1, -1):
        y_wall, y_face = sy * box.W / 2, sy * (box.W / 2 + LUG_T)
        plate = cq.Workplane("XY").box(LUG_W, LUG_T, pivot_z, centered=(True, False, False))
        plate = plate.translate((0, box.W / 2 if sy > 0 else -box.W / 2 - LUG_T, 0))
        part = part.union(plate).union(cyl_y(r, y_wall, sy * LUG_T, pivot_z))
        part = part.cut(cyl_y(PIN_D / 2, y_face, -sy * PIN_DEPTH, pivot_z))
    return part


def holder():
    part = with_lugs(body(), PIVOT_Z)
    return part, {"pivot_mm": [0.0, 0.0, PIVOT_Z], "pin_hole_mm": {"d": PIN_D, "depth_from_lug_face": PIN_DEPTH},
                  "lug_mm": {"w": LUG_W, "out_from_wall": LUG_T}, "tab": False, "finger_notches": False,
                  "overall_y_mm": box.W + 2 * LUG_T, "same_as_frame_holder": "body, pocket, ledge, open bottom"}


def catch_pan():
    """A box's top 25 mm on a CATCH_DEPTH skirt, a solid floor, the inward lip at the rim."""
    h = box.H + CATCH_DEPTH
    part = walls(h).union(cq.Workplane("XY").box(box.L - 1, box.W - 1, FLOOR_T, centered=(True, True, False)))
    # the lip: a slab LIP_T thick plus a 45 deg chamfer under it, cut back to the box above's open bottom
    ix, iy = box.L - 2 * box.WALL, box.W - 2 * box.WALL
    lip_x, lip_y = (ix - box.OPEN_L) / 2, (iy - box.OPEN_W) / 2     # 5 at the ends, 7 along the sides
    d = max(lip_x, lip_y)
    lip = cq.Workplane("XY").box(ix + 0.2, iy + 0.2, LIP_T + d, centered=(True, True, False)).translate((0, 0, h - LIP_T - d))
    opening = (cq.Workplane("XY").workplane(offset=h - LIP_T).rect(box.OPEN_L, box.OPEN_W).extrude(LIP_T + 1)
               .union(cq.Workplane("XY").workplane(offset=h - LIP_T).rect(box.OPEN_L, box.OPEN_W)
                      .workplane(offset=-(d + 0.5)).rect(box.OPEN_L + 2 * d + 1, box.OPEN_W + 2 * d + 1).loft()))
    part = part.union(lip.cut(opening))
    part = with_lugs(part, CATCH_DEPTH + PIVOT_Z)
    return part, {"pivot_mm": [0.0, 0.0, CATCH_DEPTH + PIVOT_Z], "height_mm": h, "catch_depth_below_box_mm": CATCH_DEPTH,
                  "floor_t_mm": FLOOR_T, "floor_top_below_rim_mm": h - FLOOR_T,
                  "lip_mm": {"t": LIP_T, "underside_deg": 45, "in_at_ends": lip_x, "in_at_sides": lip_y,
                             "opening": [box.OPEN_L, box.OPEN_W]},
                  "note": "rim and pivot sit as on a box (pivot 12.5 under the rim), so it hangs at the same pitch"}


PARTS = {"seesaw_holder": holder, "seesaw_catch_pan": catch_pan}


if __name__ == "__main__":
    for n in sys.argv[1:] or list(PARTS):
        part, info = PARTS[n]()
        print(n, json.dumps(export_all(part, n, info)))
