"""Tiered concentric gate sorter ("wedding cake") that sits in the 24-well-plate collector.

The physics it relies on:
- Push. Each tier's floor is a shallow cone, high in the middle. At SLOPE_DEG = 10 nothing
  moves while the plate is still (rice on PLA needs about 22 degrees to slide). Once the
  shaker reaches roughly 0.2-0.3 g, grains flow downhill to the rim. A flat floor gives them
  no reason to go anywhere, which is why the flat ring version didn't work.
- Gate shape. Shaking lays grains flat, so each gate is a low tunnel at floor level: its
  height is the thickness cut and its width is the width cut. Tall narrow slits only pass
  grains standing on edge, which shaken grains almost never do.
- One-way. Whatever passes a tunnel falls DROP mm onto the bigger tier below, or into the
  collector, and can't climb back.
- Unloading. Each tier lifts off carrying its own size class.

Stack, top to bottom:
    tier_coarse   40 mm cone, tunnels 5.0 wide x 4.0 high: tube pasta stays
    tier_fine     66 mm cone, tunnels 4.0 wide x 1.4 high: long-grain rice (~1.7 thick) stays,
                  quinoa (~1.0 thick) passes
    collector     the plate-sized collector from sieve_system.py: quinoa ends up here

Prints flat on each tier's base, no supports. The only bridges are the tunnel ceilings
(4-5 mm). Print at 0.2 mm layers so 1.4 mm is exactly 7 layers.

Run from this folder:  <venv python> tiered_sorter.py   (all parts plus a section preview)
"""
import json
import math
import sys
import cadquery as cq
from cadkit import export_all
from sieve_system import FLOOR_T, IN_L, IN_W, collector

SLOPE_DEG = 10.0     # cone angle of each tier floor
LANDING = 3.0        # flat ring inside the rim where grains meet the tunnels
RIM_T = 2.0          # rim wall thickness (= tunnel length)
RIM_H = 10.0         # rim wall height above the landing
DROP = 8.0           # landing height above whatever the tier stands on
POST = 2.0           # wall left between two tunnels
TUNNEL_RELIEF_DEG = 8.0   # tunnels widen outward so near-size grains don't wedge
PEG_D, PEG_H, PEG_FIT = 8.0, 4.0, 0.6   # centres the coarse tier on the fine tier
TAB_W, TAB_H, TAB_FIT = 8.0, 3.0, 0.3   # feet that centre the fine tier in the collector

# rim inner radius, tunnel width, tunnel height. Measure 10 grains of each with calipers
# and set the heights between the thickness of what should pass and what should stay.
TIERS = {
    "tier_coarse": (20.0, 5.0, 4.0),
    "tier_fine": (33.0, 4.0, 1.4),
}
COARSE_R_OUT = TIERS["tier_coarse"][0] + RIM_T


def tier(name):
    r_in, w, h = TIERS[name]
    r_out, r_land = r_in + RIM_T, r_in - LANDING
    bottom = name == "tier_fine"
    plateau_r = COARSE_R_OUT + 0.5 if bottom else 2.0   # fine: the coarse tier stands here; coarse: no sharp apex
    top_z = DROP + (r_land - plateau_r) * math.tan(math.radians(SLOPE_DEG))
    profile = [(0, 0), (r_out, 0), (r_out, DROP), (r_land, DROP), (plateau_r, top_z), (0, top_z)]
    body = cq.Workplane("XZ").polyline(profile).close().revolve(360, (0, 0, 0), (0, 1, 0))
    body = body.union(cq.Workplane("XY").workplane(offset=DROP - 0.1)
                      .circle(r_out).circle(r_in).extrude(RIM_H + 0.1))
    circ = 2 * math.pi * r_in
    count = int(circ / (w + POST))
    widen = (RIM_T + 0.4) * math.tan(math.radians(TUNNEL_RELIEF_DEG))
    pts = [(r_in - 0.2, -w / 2), (r_out + 0.2, -w / 2 - widen), (r_out + 0.2, w / 2 + widen), (r_in - 0.2, w / 2)]
    cutter = None
    for j in range(count):
        c = (cq.Workplane("XY").workplane(offset=DROP).polyline(pts).close().extrude(h)
             .rotate((0, 0, 0), (0, 0, 1), 360 * j / count))
        cutter = c if cutter is None else cutter.union(c)
    body = body.cut(cutter)
    if bottom:
        body = body.union(cq.Workplane("XY").workplane(offset=top_z - 0.1).circle(PEG_D / 2).extrude(PEG_H + 0.1))
        for ax, reach in (((1, 0), IN_L / 2), ((-1, 0), IN_L / 2), ((0, 1), IN_W / 2), ((0, -1), IN_W / 2)):
            length = reach - TAB_FIT / 2 - (r_out - 1)
            cx, cy = ax[0] * (r_out - 1 + length / 2), ax[1] * (r_out - 1 + length / 2)
            size = (length, TAB_W) if ax[0] else (TAB_W, length)
            body = body.union(cq.Workplane("XY").center(cx, cy).rect(*size).extrude(TAB_H))
    else:
        body = body.cut(cq.Workplane("XY").workplane(offset=-0.01).circle((PEG_D + PEG_FIT) / 2).extrude(PEG_H + 0.5))
    return body, {"rim_inner_diameter_mm": 2 * r_in, "tunnel_w_mm": w, "tunnel_h_mm": h,
                  "tunnels": count, "post_mm": round(circ / count - w, 2), "slope_deg": SLOPE_DEG,
                  "drop_mm": DROP, "top_z_mm": round(top_z, 2)}


def section_preview():
    """out/tiered_section.png: the stack in the collector, cut in half. Preview only, not a print."""
    fine, fine_info = tier("tier_fine")
    coarse, _ = tier("tier_coarse")
    stack = (collector()[0]
             .union(fine.translate((0, 0, FLOOR_T)))
             .union(coarse.translate((0, 0, FLOOR_T + fine_info["top_z_mm"]))))
    half = stack.cut(cq.Workplane("XY").box(200, 100, 100, centered=(True, False, False)).translate((0, 0, -10)))
    return half, {"preview_only": True}


PARTS = {**{n: (lambda n=n: tier(n)) for n in TIERS}, "tiered_section": section_preview}


if __name__ == "__main__":
    for n in sys.argv[1:] or list(PARTS):
        part, info = PARTS[n]()
        print(n, json.dumps(export_all(part, n, info)))
