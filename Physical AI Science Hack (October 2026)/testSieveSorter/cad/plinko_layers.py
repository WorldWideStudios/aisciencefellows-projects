"""Plinko layers: removable gate layers that stack inside the frame holder box
(frame_holder.py), in place of the glued-mesh inserts.

    side view, one box (load on top, shake along X)

    |  layer 1: rods 5.0 mm apart       -> pasta stays here      (tabs at x = 0)
    |  layer 2: rods 1.4 mm apart       -> rice stays here       (tabs at x = -35)
    |  layer 3: catch tray, solid floor -> quinoa ends up here   (tabs at x = +35)
    |___ box ledge ___________________________________________

Each layer is a tray with walls, so whatever it holds stays on it when you lift it out.
Unload top-down: lift layer 1 (pasta), then layer 2 (rice), then layer 3 (quinoa). Each
layer can go straight into the water pool, like the current mesh filters.

Each layer's pull tabs rise above the box rim and pass through close-fitting slots in the
layers above (0.3 mm clearance), so nothing can fall through around them.

Rods run across the box (along Y), perpendicular to the shake, so grains hop across them
and tip into the gaps. The gap is measured at the top; rods narrow downward by RELIEF_DEG
so a grain that gets in falls free. Gaps between rods sort a flat-lying grain by its
thickness once it tips in: that's what splits long-grain rice (~1.7 mm) from quinoa (~1.0 mm).

Sizes follow frame_holder.py (its WALL and LEDGE_T are guesses; change them there).
Prints flat, right side up, no supports.

Run from this folder:  <venv python> plinko_layers.py
"""
import json
import math
import sys
import cadquery as cq
from cadkit import export_all
import frame_holder as box

FIT = 0.6                 # total clearance between a layer and the box pocket
LW = 2.0                  # layer wall thickness
OUT_L = box.L - 2 * box.WALL - FIT
OUT_W = box.W - 2 * box.WALL - FIT
IN_L, IN_W = OUT_L - 2 * LW, OUT_W - 2 * LW
RELIEF_DEG = 8.0
TAB_W, TAB_T = 14.0, 3.0
TAB_TOP = box.H + 6.0     # tabs stand 6 mm above the box rim
SLOT_FIT = 0.3            # clearance around a lower layer's tab where it passes an upper layer
RIB_W = 2.0               # rib under the rods along X, for stiffness
FLOOR_T = 2.0

# Top to bottom: name, floor ("rods" or "solid"), gap, rod top width, rod height, wall height, tab x
LAYERS = [
    ("layer_1_rods_5p0", "rods", 5.0, 2.4, 3.0, 12.0, 0.0),
    ("layer_2_rods_1p4", "rods", 1.4, 2.0, 2.5, 8.0, -35.0),
    ("layer_3_catch", "solid", None, None, FLOOR_T, 6.0, 35.0),
]


def bottoms():
    """Height of each layer's underside in box coordinates: the bottom layer sits on the
    ledge, every other layer sits on the wall top of the layer below."""
    z, out = box.LEDGE_T, {}
    for name, *_rest, wall_h, _tab_x in reversed(LAYERS):
        out[name] = z
        z += wall_h
    return out


def rods(gap, b_top, h):
    b_bot = b_top - 2 * h * math.tan(math.radians(RELIEF_DEG))
    pitch = gap + b_top
    xs, x = [], -IN_L / 2 + gap + b_top / 2
    while x + b_top / 2 + gap <= IN_L / 2 + 1e-6:
        xs.append(x)
        x += pitch
    grate = None
    for x in xs:
        bar = (cq.Workplane("XZ").polyline([(x - b_bot / 2, 0), (x + b_bot / 2, 0), (x + b_top / 2, h),
                                            (x - b_top / 2, h)]).close().extrude(IN_W / 2 + 0.5, both=True))
        grate = bar if grate is None else grate.union(bar)
    end = xs[-1] + b_top / 2 + gap   # close any leftover so the last gap is exactly `gap`
    if end < IN_L / 2:
        grate = grate.union(cq.Workplane("XY").box(IN_L / 2 + 0.5 - end, IN_W + 1, h, centered=False)
                            .translate((end, -IN_W / 2 - 0.5, 0)))
    rib = cq.Workplane("XY").box(IN_L + 1, RIB_W, h, centered=(True, True, False))
    return grate.union(rib), xs, pitch


def span_to_rods(x0, x1, xs):
    """[x0, x1] widened out to the nearest rod centre lines. A block whose end face lands exactly on a rod's top
    edge touches the rod along a line, which leaves the exported mesh open; through a rod's middle it doesn't."""
    left, right = [x for x in xs if x <= x0], [x for x in xs if x >= x1]
    return max(left) if left else -IN_L / 2 - 0.5, min(right) if right else IN_L / 2 + 0.5


def tab_block(x, z0, z1, extra=0.0):
    """Both tabs (or tab slots, with extra clearance) at x, against the inside of the long walls."""
    w, t = TAB_W + 2 * extra, TAB_T + extra
    y = IN_W / 2 - TAB_T - extra
    blocks = None
    for sy in (1, -1):
        b = cq.Workplane("XY").box(w, t + extra, z1 - z0, centered=False).translate(
            (x - w / 2, y if sy > 0 else -y - t - extra, z0))
        blocks = b if blocks is None else blocks.union(b)
    return blocks


def layer(name):
    idx = [n for n, *_ in LAYERS].index(name)
    _, floor, gap, b_top, h, wall_h, tab_x = LAYERS[idx]
    z_bottom = bottoms()[name]
    body = (cq.Workplane("XY").box(OUT_L, OUT_W, wall_h, centered=(True, True, False)).edges("|Z").fillet(1.5)
            .cut(cq.Workplane("XY").box(IN_L, IN_W, wall_h, centered=(True, True, False))))
    info = {"z_in_box_mm": round(z_bottom, 2), "outside_mm": [round(OUT_L, 2), round(OUT_W, 2), wall_h],
            "tab_x_mm": tab_x}
    if floor == "rods":
        grate, xs, pitch = rods(gap, b_top, h)
        body = body.union(grate)
        # a foot under each tab at rod height, so the tab's side faces stand on solid instead of on a rod edge
        x0, x1 = span_to_rods(tab_x - TAB_W / 2, tab_x + TAB_W / 2, xs)
        for sy in (1, -1):
            body = body.union(cq.Workplane("XY").box(x1 - x0, TAB_T + 0.5, h, centered=False)
                              .translate((x0, IN_W / 2 - TAB_T if sy > 0 else -IN_W / 2 - 0.5, 0)))
        info.update({"gap_mm": gap, "rods": len(xs), "pitch_mm": round(pitch, 2),
                     "open_area_pct": round(100 * gap / pitch, 1)})
    else:
        body = body.union(cq.Workplane("XY").box(IN_L + 1, IN_W + 1, FLOOR_T, centered=(True, True, False)))
    body = body.union(tab_block(tab_x, 0, TAB_TOP - z_bottom))
    for _, lower_floor, _g, _b, lower_h, _w, lower_tab_x in LAYERS[idx + 1:]:
        # slot for a lower layer's tab, plus a bar that ties the cut rod ends back together
        body = body.cut(tab_block(lower_tab_x, -1, wall_h + 1, extra=SLOT_FIT))
        if floor == "rods":
            x0, x1 = span_to_rods(lower_tab_x - TAB_W / 2 - 3, lower_tab_x + TAB_W / 2 + 3, xs)
            for sy in (1, -1):
                y_in = IN_W / 2 - TAB_T - 2 * SLOT_FIT
                bar = cq.Workplane("XY").box(x1 - x0, 2.0, h, centered=False).translate(
                    (x0, y_in - 2.0 if sy > 0 else -y_in, 0))
                body = body.union(bar)
    return body, info


def section():
    """out/plinko_section.png: box plus all layers, cut in half. Preview only, not a print."""
    z = bottoms()
    stack = box.frame()
    for name, *_ in LAYERS:
        stack = stack.union(layer(name)[0].translate((0, 0, z[name])))
    return stack.cut(cq.Workplane("XY").box(300, 100, 200, centered=(True, False, False))
                     .translate((0, -100, -50))), {"preview_only": True}


PARTS = {**{n: (lambda n=n: layer(n)) for n, *_ in LAYERS}, "plinko_section": section}


if __name__ == "__main__":
    for n in sys.argv[1:] or list(PARTS):
        part, info = PARTS[n]()
        print(n, json.dumps(export_all(part, n, info)))
