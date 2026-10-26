"""Sieve inserts for BioKEA's holder box: the flat 2x3-window frames with pull tabs from
the bench photos (Downloads\\IMG20261024193841.jpg, IMG20261024193846.jpg), with the mesh
printed in as square holes instead of glued on.

    sieve_insert_5mm   5.0 mm square holes (the coarse mesh in the photos)
    sieve_insert_2mm   2.0 mm square holes (the insert marked "2 mm")

Read from the photos: the insert's proportions match the holder pocket, a border about
10 mm wide, ribs about 3 mm making six windows (about 35 x 36 mm), and two upright pull
tabs in the middle of the long edges. These are the working dimensions as of 2026-10-24
(see WORKING_DIMENSIONS.md); the outside size follows the frame_holder.py pocket.

The square-hole screen sits at the bottom of each window, on the print bed, so it prints
cleanly with no bridging. The border and ribs stand FRAME_T - SCREEN_T above it. Holes
widen downward by RELIEF_DEG so a grain that gets in falls free instead of wedging.
Prints flat, right side up, no supports.

Run from this folder:  <venv python> sieve_insert.py
"""
import json
import sys
import cadquery as cq
from cadkit import export_all
import frame_holder as box

FIT = 0.6                         # total clearance in the holder pocket
L = box.L - 2 * box.WALL - FIT    # 131.4 with the working frame_holder values
W = box.W - 2 * box.WALL - FIT    # 95.4
FRAME_T = 3.0                     # border and rib height
BORDER = 10.0
RIB = 3.0
COLS, ROWS = 3, 2
TAB_W, TAB_T, TAB_H = 20.0, 6.0, 18.0   # pull tab: along the edge, thickness, height above the frame
RELIEF_DEG = 8.0
LABEL_H, LABEL_D = 4.0, 0.6

# name: (hole size, bar width between holes, screen thickness)
INSERTS = {
    "sieve_insert_5mm": (5.0, 1.2, 1.6),
    "sieve_insert_2mm": (2.0, 1.0, 1.4),
}


def windows():
    """Centre and size of each of the COLS x ROWS windows."""
    win_l = (L - 2 * BORDER - (COLS - 1) * RIB) / COLS
    win_w = (W - 2 * BORDER - (ROWS - 1) * RIB) / ROWS
    out = []
    for i in range(COLS):
        for j in range(ROWS):
            out.append((-L / 2 + BORDER + win_l / 2 + i * (win_l + RIB),
                        -W / 2 + BORDER + win_w / 2 + j * (win_w + RIB), win_l, win_w))
    return out


def insert(name):
    hole, bar, screen_t = INSERTS[name]
    body = cq.Workplane("XY").box(L, W, FRAME_T, centered=(True, True, False))
    pitch = hole + bar
    holes = []
    for cx, cy, wl, ww in windows():
        body = body.cut(cq.Workplane("XY").box(wl, ww, FRAME_T, centered=(True, True, False))
                        .translate((cx, cy, screen_t)))
        nx, ny = int((wl - bar) // pitch), int((ww - bar) // pitch)   # whole holes that fit with a bar at each edge
        x0, y0 = cx - (nx - 1) * pitch / 2, cy - (ny - 1) * pitch / 2
        holes += [(x0 + i * pitch, y0 + j * pitch) for i in range(nx) for j in range(ny)]
    cutter = (cq.Workplane("XY").workplane(offset=screen_t + 0.01).pushPoints(holes)
              .rect(hole, hole).extrude(-(screen_t + 0.2), taper=-RELIEF_DEG))
    body = body.cut(cutter)
    for sy in (1, -1):
        tab = cq.Workplane("XY").box(TAB_W, TAB_T, FRAME_T + TAB_H, centered=(True, False, False))
        body = body.union(tab.translate((0, W / 2 - TAB_T if sy > 0 else -W / 2, 0)))
    label = cq.Workplane("XY").workplane(offset=FRAME_T + TAB_H + 0.01).center(0, W / 2 - TAB_T / 2) \
        .text(f"{hole:g}", LABEL_H, -(LABEL_D + 0.01), combine=False)
    body = body.cut(label)
    open_pct = 100 * len(holes) * hole * hole / sum(wl * ww for _, _, wl, ww in windows())
    return body, {"hole_mm": hole, "bar_mm": bar, "screen_t_mm": screen_t, "holes": len(holes),
                  "open_area_of_windows_pct": round(open_pct, 1), "outside_mm": [round(L, 2), round(W, 2), FRAME_T],
                  "window_mm": [round(windows()[0][2], 1), round(windows()[0][3], 1)]}


# Ribs-across inserts for the seesaw (docs/SYSTEM.md section 3: the ends tip, so grains slide along X). The
# 11:20 renders left quinoa and chia sitting on the flat-topped border and riding the rib along X like a
# rail. These have no flat top a grain can rest on and nothing solid running along X:
# - the screen reaches the edge of the holder's open bottom (borders ACROSS_BORDER: 5 at the ends, 7
#   along the sides, just the ledge), so every hole drains;
# - the border is a 45 deg ramp down to the screen (steeper than the ~22 deg a grain needs to slide),
#   ending in a RAMP_FLAT mm flat at the outer edge, against the holder wall;
# - ACROSS_COLS - 1 ribs, all along Y (across the slide), as 45 deg ridges RIDGE_W wide at the screen.
# Kept out of INSERTS on purpose: the sim's designs_holder.py builds INSERTS with the flat 3 x 2 frame.
ACROSS = {"sieve_insert_5mm_across": INSERTS["sieve_insert_5mm"], "sieve_insert_2mm_across": INSERTS["sieve_insert_2mm"]}
ACROSS_BORDER = ((L - box.OPEN_L) / 2 + 0.3, (W - box.OPEN_W) / 2 + 0.3)   # 5.0, 7.0: the ledge under the edge
ACROSS_COLS = 3
RIDGE_W = 3.0
RAMP_FLAT = 0.6


def across_windows():
    """The ACROSS_COLS windows, one row, ridges RIDGE_W wide between them."""
    bx, by = ACROSS_BORDER
    wl, ww = (L - 2 * bx - (ACROSS_COLS - 1) * RIDGE_W) / ACROSS_COLS, W - 2 * by
    return [(-L / 2 + bx + wl / 2 + i * (wl + RIDGE_W), 0.0, wl, ww) for i in range(ACROSS_COLS)]


def insert_across(name):
    hole, bar, screen_t = ACROSS[name]
    bx, by = ACROSS_BORDER
    sx, sy = L - 2 * bx, W - 2 * by                       # the screen, at the bottom
    body = cq.Workplane("XY").box(L, W, screen_t, centered=(True, True, False))
    pitch, holes = hole + bar, []
    for cx, cy, wl, ww in across_windows():
        nx, ny = int((wl - bar) // pitch), int((ww - bar) // pitch)
        x0, y0 = cx - (nx - 1) * pitch / 2, cy - (ny - 1) * pitch / 2
        holes += [(x0 + i * pitch, y0 + j * pitch) for i in range(nx) for j in range(ny)]
    body = body.cut(cq.Workplane("XY").workplane(offset=screen_t + 0.01).pushPoints(holes)
                    .rect(hole, hole).extrude(-(screen_t + 0.2), taper=-RELIEF_DEG))
    # border ramps: a ring standing on the screen, cut by a pocket widening 45 deg upward from the screen's edge
    ring_h = max(bx, by) - RAMP_FLAT
    ring = (cq.Workplane("XY").box(L, W, ring_h, centered=(True, True, False)).translate((0, 0, screen_t))
            .cut(cq.Workplane("XY").workplane(offset=screen_t - 0.01).rect(sx, sy)
                 .workplane(offset=ring_h + 0.02).rect(sx + 2 * (ring_h + 0.02), sy + 2 * (ring_h + 0.02)).loft()))
    ring = ring.intersect(cq.Workplane("XY").box(L, W, screen_t + bx - RAMP_FLAT, centered=(True, True, False))
                          .union(cq.Workplane("XY").box(sx + 2, W, screen_t + ring_h, centered=(True, True, False))))
    body = body.union(ring)
    ridge_h = RIDGE_W / 2
    for cx, _cy, wl, _ww in across_windows()[:-1]:
        x = cx + wl / 2 + RIDGE_W / 2
        ridge = (cq.Workplane("XZ").polyline([(x - RIDGE_W / 2, screen_t - 0.01), (x + RIDGE_W / 2, screen_t - 0.01),
                                              (x, screen_t + ridge_h)]).close().extrude(sy / 2 + 1, both=True))
        body = body.union(ridge)
    for sgn in (1, -1):
        tab = cq.Workplane("XY").box(TAB_W, TAB_T, FRAME_T + TAB_H, centered=(True, False, False))
        body = body.union(tab.translate((0, W / 2 - TAB_T if sgn > 0 else -W / 2, 0)))
    label = cq.Workplane("XY").workplane(offset=FRAME_T + TAB_H + 0.01).center(0, W / 2 - TAB_T / 2) \
        .text(f"{hole:g}X", LABEL_H, -(LABEL_D + 0.01), combine=False)
    body = body.cut(label)
    open_pct = 100 * len(holes) * hole * hole / (box.OPEN_L * box.OPEN_W)
    return body, {"hole_mm": hole, "bar_mm": bar, "screen_t_mm": screen_t, "holes": len(holes),
                  "open_pct_of_box_bottom": round(open_pct, 1), "outside_mm": [round(L, 2), round(W, 2)],
                  "screen_mm": [round(sx, 2), round(sy, 2)], "border_ramp": {"ends_mm": round(bx, 2), "sides_mm": round(by, 2),
                                                                           "deg": 45, "outer_flat_mm": RAMP_FLAT},
                  "ridges_along_y": {"count": ACROSS_COLS - 1, "w_mm": RIDGE_W, "h_mm": ridge_h, "deg": 45,
                                     "x_mm": [round(c + w / 2 + RIDGE_W / 2, 2) for c, _, w, _ in across_windows()[:-1]]},
                  "window_mm": [round(across_windows()[0][2], 2), round(across_windows()[0][3], 2)],
                  "label": f"{hole:g}X on the +Y tab", "solid_along_x": "none above the screen but the tabs"}


PARTS = {**{n: (lambda n=n: insert(n)) for n in INSERTS}, **{n: (lambda n=n: insert_across(n)) for n in ACROSS}}


if __name__ == "__main__":
    for n in sys.argv[1:] or list(PARTS):
        part, info = PARTS[n]()
        print(n, json.dumps(export_all(part, n, info)))
