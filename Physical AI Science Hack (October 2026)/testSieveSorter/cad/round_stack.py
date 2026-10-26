"""Round layered gate stack: full layers of the same size, gates in each floor.

    load here
       |
    [ layer 1: X gates ]   keeps anything bigger than X
       |  everything smaller than X falls through
    [ layer 2: Y gates ]   keeps X..Y
       |  everything smaller than Y falls through
    [ collector        ]   catches the rest (Z)

Gravity pulls anything that fits down through the gates; shaking keeps lifting and
turning grains so each one meets many gates. Each layer lifts off carrying its class.

Gate styles:
    square  sorts by width (a grain passes if its two smaller dimensions fit)
    slot    sorts by thickness: shaken grains tip edge-first into a floor slot, the way
            grain graders sort barley. This is what splits long-grain rice from quinoa.

Every gate widens downward by RELIEF_DEG, so a grain that gets in falls free instead of
wedging. Prints flat, right side up, no supports.

Run from this folder:  <venv python> round_stack.py      (all parts)
"""
import json
import math
import sys
import cadquery as cq
from cadkit import export_all

OD = 85.0            # outer diameter; fits across a 24-well plate's 85.47 mm width
H = 20.27            # layer height, same as a 24-well plate
WALL = 2.5
FIT = 0.6            # total nesting clearance
LIP_H, LIP_WALL = 3.0, 1.6   # lip under each layer that drops into the layer below
FLOOR_T = 2.0
RELIEF_DEG = 8.0
WEB = 1.0            # plastic between gates at their wide (bottom) side
EDGE = 1.5           # solid ring between the gates and the lip

# name: (style, gate width, slot length). Measure 10 grains of each with calipers first.
LAYERS = {
    "layer_x_square_5p0": ("square", 5.0, None),   # pasta stays; rice and quinoa pass
    "layer_y_square_2p3": ("square", 2.3, None),   # short-grain rice stays; quinoa passes
    "layer_y_slot_1p4": ("slot", 1.4, 10.0),       # long-grain rice (~1.7 thick) stays; quinoa (~1.0) passes
}

R_IN = OD / 2 - WALL
LIP_R_OUT = R_IN - FIT / 2
LIP_R_IN = LIP_R_OUT - LIP_WALL


def cup(floor_z, floor=True):
    """Round wall from floor_z to H, optional floor on top of floor_z, lip below it."""
    body = cq.Workplane("XY").workplane(offset=floor_z).circle(OD / 2).circle(R_IN).extrude(H - floor_z)
    if floor:
        body = body.union(cq.Workplane("XY").workplane(offset=floor_z).circle(R_IN + 0.1).extrude(FLOOR_T))
    return body


def gate_centres(style, width, length):
    grow = 2 * FLOOR_T * math.tan(math.radians(RELIEF_DEG))
    r_max = LIP_R_IN - EDGE
    if style == "square":
        s = width + grow
        px = py = s + WEB
        half_x = half_y = s / 2
    else:
        px, py = width + grow + WEB, length + grow + 1.5 * WEB
        half_x, half_y = (width + grow) / 2, (length + grow) / 2
    pts = []
    nx, ny = int(r_max / px) + 1, int(r_max / py) + 2
    for i in range(-nx, nx + 1):
        off = py / 2 if (style == "slot" and i % 2) else 0.0
        for j in range(-ny, ny + 1):
            x, y = i * px, j * py + off
            corners = [(x + sx * half_x, y + sy * half_y) for sx in (-1, 1) for sy in (-1, 1)]
            if all(math.hypot(cx, cy) <= r_max for cx, cy in corners):
                pts.append((x, y))
    area = width * width if style == "square" else width * length - (4 - math.pi) * (width / 2) ** 2
    open_frac = len(pts) * area / (math.pi * r_max ** 2)
    return pts, open_frac


def layer(name):
    style, width, length = LAYERS[name]
    body = cup(LIP_H).union(cq.Workplane("XY").circle(LIP_R_OUT).circle(LIP_R_IN).extrude(LIP_H + 0.5))
    pts, open_frac = gate_centres(style, width, length)
    wp = cq.Workplane("XY").workplane(offset=LIP_H + FLOOR_T + 0.01).pushPoints(pts)
    wp = wp.rect(width, width) if style == "square" else wp.slot2D(length, width, 90)
    body = body.cut(wp.extrude(-(FLOOR_T + 0.2), taper=-RELIEF_DEG))
    info = {"style": style, "gate_mm": width, "gates": len(pts), "open_area_pct": round(100 * open_frac, 1),
            "gate_bottom_mm": round(width + 2 * FLOOR_T * math.tan(math.radians(RELIEF_DEG)), 2),
            "headroom_mm": round(H - LIP_H - FLOOR_T, 2)}
    if length:
        info["slot_length_mm"] = length
    return body, info


def collector():
    return cup(0.0), {"volume_ml": round(math.pi * R_IN ** 2 * (H - FLOOR_T) / 1000)}


def lid():
    plate = cq.Workplane("XY").workplane(offset=LIP_H).circle(OD / 2).extrude(FLOOR_T)
    return plate.union(cq.Workplane("XY").circle(LIP_R_OUT).circle(LIP_R_IN).extrude(LIP_H + 0.5)), {}


def stack_section():
    """out/round_stack_section.png: lid, X layer, slot layer and collector, cut in half. Preview only."""
    parts = [collector()[0], layer("layer_y_slot_1p4")[0], layer("layer_x_square_5p0")[0], lid()[0]]
    stack = None
    for k, p in enumerate(parts):
        p = p.translate((0, 0, k * (H - LIP_H)))   # each part's lip drops into the rim below
        stack = p if stack is None else stack.union(p)
    # remove the half nearest the camera so the cut face shows
    return stack.cut(cq.Workplane("XY").box(200, 100, 200, centered=(True, False, False)).translate((0, -100, -50))), {"preview_only": True}


PARTS = {**{n: (lambda n=n: layer(n)) for n in LAYERS}, "round_collector": collector, "round_lid": lid,
         "round_stack_section": stack_section}


if __name__ == "__main__":
    for n in sys.argv[1:] or list(PARTS):
        part, info = PARTS[n]()
        print(n, json.dumps(export_all(part, n, info)))
