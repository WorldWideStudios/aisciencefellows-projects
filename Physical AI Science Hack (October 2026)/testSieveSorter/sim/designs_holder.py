"""BioKEA's holder box designs for the sorter sim, in the tray frame (see common.Design). Units mm.

    inserts:<a>,<b>,...   a tower of holder boxes (cad/frame_holder.py), one insert per box,
                          coarse to fine in the order given, on a catch pan. Inserts:
                            5mm, 2mm        printed square-hole screens (cad/sieve_insert.py INSERTS)
                            h<hole>b<bar>[_across]  a custom printed screen, sizes as modelled with p for the
                                          point: h2p15b1p15_across = 2.15 mm holes, 1.15 mm bars, ribs across
                                          (see insert_spec); any number of boxes, coarse to fine (sim/LAYERS.md)
                            mesh5, mesh2    today's inserts: woven mesh glued over the same frame (MESHES)
                          e.g. inserts:mesh5,mesh2 (current) vs inserts:5mm,2mm (future); mixing works.
                          pitch=<mm> spaces the boxes (bottom to bottom) instead of rim on rim, as on the
                          bench tower frame: inserts:5mm,2mm,pitch=65
                          5mm_across, 2mm_across  the ribs-across inserts for the seesaw (sieve_insert.py
                                          ACROSS): 45 deg border ramps, ridges along Y only
                          holder=seesaw   cad/seesaw_holder.py: boxes with no +X tab and no finger notches
                                          (pivot pins in the middle), over the deep catch pan with its lip:
                                          inserts:5mm_across,2mm_across,pitch=55,holder=seesaw
    plinko                the plinko layers (cad/plinko_layers.py LAYERS) stacked in one holder box

Tray frame: origin at the holder's centre in XY, z = 0 under the lowest part, x along the holder's
long side (the stroke). Sizes are read from the CAD modules; no CAD solids are built.

Stacking (the CAD doesn't define it; the user confirmed this setup): one insert per box, boxes
stacked straight up coarse to fine, each on the rim of the one below, bolted to the shaker by the
+X end tab and shaken along X while fixed jets spray from above. Under the bottom box is a catch
pan: the holder box with its open centre filled in. Only the holder's open bottom
(OPEN_L x OPEN_W) drains; the insert border over the 3 mm ledge never does.

Ideal zone (dims "width" >= "thickness"): a particle stays on the first layer whose opening it
can't pass, else it ends in the catch.
    square hole or mesh aperture s   passes if its width x thickness cross-section fits the s x s
                                     square at some tilt (common.ellipse_fits): a flat grain goes
                                     through corner to corner, so 2.0 x 1.7 mm rice passes a 2 mm hole
    rod gap g (a long slot)          passes if thickness <= g
    solid floor                      passes nothing

Run from sim\\ to print a summary:  <venv python> designs_holder.py [spec ...]
"""
import functools
import json
import math
import re
import sys
from pathlib import Path

from common import Design, ellipse_fits

CAD_DIR = Path(__file__).resolve().parent.parent / "cad"

# Glued woven mesh, today's inserts. Wires are capsules: X wires and Y wires in two layers one
# wire diameter apart, running across the whole insert (windows, ribs and border).
# side: "top" = glued on the frame's top face; "under" = on its underside (the insert then sits
# on the mesh). The bench photos (IMG20261024193841/-846) show both meshes on top of the frame:
# the coarse mesh's flat strands (about 1 mm wide) and the fine net's threads (about 0.3 mm)
# cross the ribs and are glued over the border. Apertures are the nominal names until measured:
# scaled by the CAD window size, the coarse mesh in the photo has a pitch of about 4 x 3.6 mm,
# so an aperture nearer 3 mm than 5.
MESHES = {
    "mesh5": {"aperture": 5.0, "wire_d": 1.0, "side": "top"},
    "mesh2": {"aperture": 2.0, "wire_d": 0.3, "side": "top"},
}
MESH_STATUS = "placeholder until measured (aperture nominal; wire size and side judged from the bench photos)"
CUSTOM_INSERT = re.compile(r"^h(\d+(?:p\d+)?)b(\d+(?:p\d+)?)(_across)?$")   # h<hole>b<bar>[_across], see insert_spec

LID_ABOVE = 80.0          # invisible lid this far above the top layer's surface
SPAWN_Z = (5.0, 45.0)     # spawn box heights above the top layer's surface
SPAWN_INSET = 12.0        # spawn box inset from the walls in XY
JET_Z = 60.0              # placeholder jets: height above the top layer's surface
JET = {"dir": (0.0, 0.0, -1.0), "flow_ml_s": 5.0, "nozzle_d_mm": 1.0, "half_angle_deg": 15.0, "range_mm": 150.0}
TUB_FLOOR, TUB_HALF = 110.0, 200.0   # spaced towers: invisible floor this far under the catch pan, +/- this wide
NOTCH_SEGMENTS = 4        # chords approximating the round bottom of each finger notch

HOLDER_RGBA = [0.93, 0.92, 0.88, 1.0]
INSERT_RGBA = [0.80, 0.86, 0.95, 1.0]
SCREEN_RGBA = [0.35, 0.55, 0.85, 1.0]
WIRE_RGBA = [0.62, 0.64, 0.70, 1.0]
LAYER_RGBA = [0.86, 0.80, 0.68, 1.0]
ROD_RGBA = [0.90, 0.52, 0.22, 1.0]
LID_RGBA = [0.0, 0.0, 0.0, 0.0]
_S = math.sqrt(0.5)
CAPSULE_QUAT = {"x": [_S, 0.0, _S, 0.0], "y": [_S, -_S, 0.0, 0.0]}   # local z onto x or y


@functools.cache
def cad():
    """The CAD modules (imported on first use: they pull in CadQuery)."""
    sys.path.insert(0, str(CAD_DIR))
    import frame_holder
    import plinko_layers
    import sieve_insert
    return frame_holder, sieve_insert, plinko_layers


@functools.cache
def seesaw_cad():
    """cad/seesaw_holder.py (the seesaw holder and deep catch pan)."""
    cad()
    import seesaw_holder
    return seesaw_holder


def box(x0, x1, y0, y1, z0, z1, rgba, role):
    return {"type": "box", "size": [(x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2],
            "pos": [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], "quat": [1.0, 0.0, 0.0, 0.0],
            "rgba": rgba, "role": role}


def prism(section, axis, a0, a1, rgba, role):
    """Convex mesh: the (u, z) polygon `section` extruded along `axis` ("x" or "y") from a0 to a1;
    u is the other horizontal axis."""
    verts = [[a, u, z] if axis == "x" else [u, a, z] for a in (a0, a1) for u, z in section]
    return {"type": "mesh", "vertices": verts, "rgba": rgba, "role": role}


def capsule(axis, a0, a1, u, z, r, rgba, role):
    """A wire along `axis` from a0 to a1 (ends included), centred at u across and height z."""
    c = (a0 + a1) / 2
    return {"type": "capsule", "size": [r, (a1 - a0) / 2 - r], "pos": [c, u, z] if axis == "x" else [u, c, z],
            "quat": CAPSULE_QUAT[axis], "rgba": rgba, "role": role}


def lid(hx, hy, z0, z1, t, floor_z=0.0):
    """Invisible walls around the rectangle |x| <= hx, |y| <= hy from z0 to z1, a lid on top, and a
    plate under the holder footprint at z < 0, so a particle forced through the thin bottom floor
    by a soft-contact impact stays in the scene (as "between") instead of falling out."""
    fh = cad()[0]
    return [box(hx, hx + t, -hy - t, hy + t, z0, z1, LID_RGBA, "lid"),
            box(-hx - t, -hx, -hy - t, hy + t, z0, z1, LID_RGBA, "lid"),
            box(-hx, hx, hy, hy + t, z0, z1, LID_RGBA, "lid"),
            box(-hx, hx, -hy - t, -hy, z0, z1, LID_RGBA, "lid"),
            box(-hx - t, hx + t, -hy - t, hy + t, z1, z1 + t, LID_RGBA, "lid"),
            box(-fh.L / 2, fh.L / 2, -fh.W / 2, fh.W / 2, floor_z - t, floor_z, LID_RGBA, "lid")]


def holder(z0, solid_base=False, close_notches=False, seesaw=False):
    """frame_holder.py's box standing at z0: the ledge round the open centre (or a solid base for
    the catch pan), walls with the U finger notch in each long wall, and the +X mounting tab
    (its bolt hole left out). close_notches adds invisible lids over the notches. seesaw: the
    seesaw_holder.py box instead, with no tab and no notches (its pivot lugs stand outside the
    walls and are left out)."""
    fh = cad()[0]
    hx, hy, ix, iy = fh.L / 2, fh.W / 2, fh.L / 2 - fh.WALL, fh.W / 2 - fh.WALL
    ox, oy, zl, zt = fh.OPEN_L / 2, fh.OPEN_W / 2, z0 + fh.LEDGE_T, z0 + fh.H
    if seesaw:
        return [box(-hx, -ox, -hy, hy, z0, zl, HOLDER_RGBA, "frame"), box(ox, hx, -hy, hy, z0, zl, HOLDER_RGBA, "frame"),
                box(-ox, ox, -hy, -oy, z0, zl, HOLDER_RGBA, "frame"), box(-ox, ox, oy, hy, z0, zl, HOLDER_RGBA, "frame"),
                box(-hx, -ix, -hy, hy, zl, zt, HOLDER_RGBA, "wall"), box(ix, hx, -hy, hy, zl, zt, HOLDER_RGBA, "wall"),
                box(-ix, ix, -hy, -iy, zl, zt, HOLDER_RGBA, "wall"), box(-ix, ix, iy, hy, zl, zt, HOLDER_RGBA, "wall")]
    if solid_base:
        g = [box(-hx, hx, -hy, hy, z0, zl, HOLDER_RGBA, "floor")]
    else:
        g = [box(-hx, -ox, -hy, hy, z0, zl, HOLDER_RGBA, "frame"), box(ox, hx, -hy, hy, z0, zl, HOLDER_RGBA, "frame"),
             box(-ox, ox, -hy, -oy, z0, zl, HOLDER_RGBA, "frame"), box(-ox, ox, oy, hy, z0, zl, HOLDER_RGBA, "frame")]
    g += [box(-hx, -ix, -hy, hy, zl, zt, HOLDER_RGBA, "wall"), box(ix, hx, -hy, hy, zl, zt, HOLDER_RGBA, "wall")]
    r = fh.NOTCH_W / 2
    zc = zt - fh.NOTCH_D + r                     # centre of the notch's round bottom
    xs = [-r + 2 * r * k / NOTCH_SEGMENTS for k in range(NOTCH_SEGMENTS + 1)]
    arc = [zc - math.sqrt(max(r * r - x * x, 0.0)) for x in xs]
    for y0, y1 in ((-hy, -iy), (iy, hy)):
        g += [box(-ix, -r, y0, y1, zl, zt, HOLDER_RGBA, "wall"), box(r, ix, y0, y1, zl, zt, HOLDER_RGBA, "wall")]
        g += [prism([(xa, zl), (xb, zl), (xb, za_b), (xa, za_a)], "y", y0, y1, HOLDER_RGBA, "wall")
              for xa, xb, za_a, za_b in zip(xs, xs[1:], arc, arc[1:])]
        if close_notches:
            g.append(box(-r, r, y0, y1, zl, zt, LID_RGBA, "lid"))
    g.append(box(hx, hx + fh.TAB_L, -fh.TAB_T / 2, fh.TAB_T / 2, z0, zt, HOLDER_RGBA, "frame"))
    return g


def seesaw_pan():
    """seesaw_holder.py's catch pan with its rim at z = H, like a box standing at 0, reaching CATCH_DEPTH
    below 0: walls, the solid floor and the inward lip (a convex prism per side, 45 deg underside).
    Returns geoms and the floor top z."""
    fh, sh = cad()[0], seesaw_cad()
    hx, hy, ix, iy = fh.L / 2, fh.W / 2, fh.L / 2 - fh.WALL, fh.W / 2 - fh.WALL
    zb, zt = -sh.CATCH_DEPTH, fh.H
    zf = zb + sh.FLOOR_T
    g = [box(-hx, hx, -hy, hy, zb, zf, HOLDER_RGBA, "floor"),
         box(-hx, -ix, -hy, hy, zf, zt, HOLDER_RGBA, "wall"), box(ix, hx, -hy, hy, zf, zt, HOLDER_RGBA, "wall"),
         box(-ix, ix, -hy, -iy, zf, zt, HOLDER_RGBA, "wall"), box(-ix, ix, iy, hy, zf, zt, HOLDER_RGBA, "wall")]
    for axis, i_half, o_half, along in (("y", ix, fh.OPEN_L / 2, iy), ("x", iy, fh.OPEN_W / 2, ix)):
        d = i_half - o_half                         # 5 at the ends, 7 along the sides
        for sgn in (1, -1):
            sec = [(sgn * o_half, zt), (sgn * i_half, zt), (sgn * i_half, zt - sh.LIP_T - d), (sgn * o_half, zt - sh.LIP_T)]
            g.append(prism(sec, axis, -along, along, HOLDER_RGBA, "wall"))
    return g, zf


def solid_runs(w0, w1, centres, hole):
    """Solid intervals of [w0, w1] between holes of width `hole` at `centres`; each flagged per
    end for whether it borders a hole (and so tapers) or the window edge."""
    edges = [(w0, False)] + [e for c in centres for e in ((c - hole / 2, True), (c + hole / 2, True))] + [(w1, False)]
    return [(a, b, ah, bh) for (a, ah), (b, bh) in zip(edges[::2], edges[1::2])]


def insert_frame(z0):
    """sieve_insert.py's frame standing at z0: border, ribs and the two pull tabs."""
    si = cad()[1]
    hx, hy, ib_x, ib_y, z1 = si.L / 2, si.W / 2, si.L / 2 - si.BORDER, si.W / 2 - si.BORDER, z0 + si.FRAME_T
    g = [box(-hx, -ib_x, -hy, hy, z0, z1, INSERT_RGBA, "frame"), box(ib_x, hx, -hy, hy, z0, z1, INSERT_RGBA, "frame"),
         box(-ib_x, ib_x, -hy, -ib_y, z0, z1, INSERT_RGBA, "frame"), box(-ib_x, ib_x, ib_y, hy, z0, z1, INSERT_RGBA, "frame")]
    win = si.windows()
    for cx, _cy, wl, _ww in win[::si.ROWS][:-1]:                 # ribs between columns
        g.append(box(cx + wl / 2, cx + wl / 2 + si.RIB, -ib_y, ib_y, z0, z1, INSERT_RGBA, "frame"))
    for _cx, cy, _wl, ww in win[:si.ROWS - 1]:                   # ribs between rows
        g.append(box(-ib_x, ib_x, cy + ww / 2, cy + ww / 2 + si.RIB, z0, z1, INSERT_RGBA, "frame"))
    for y0, y1 in ((hy - si.TAB_T, hy), (-hy, -hy + si.TAB_T)):
        g.append(box(-si.TAB_W / 2, si.TAB_W / 2, y0, y1, z0, z1 + si.TAB_H, INSERT_RGBA, "frame"))
    return g


def insert_frame_across(z0, name):
    """sieve_insert.py's ribs-across frame standing at z0: the four 45 deg border ramps (solid from z0, so
    they cover the screen's border too), the ridges along Y (solid down to z0) and the two pull tabs."""
    si = cad()[1]
    st = si.ACROSS[name][2]
    hx, hy, (bx, by) = si.L / 2, si.W / 2, si.ACROSS_BORDER
    g = []
    for axis, half, b, along in (("y", hx, bx, hy), ("x", hy, by, hx)):
        e, top = half - b, z0 + st + b - si.RAMP_FLAT
        for sgn in (1, -1):
            sec = [(sgn * e, z0), (sgn * half, z0), (sgn * half, top), (sgn * (half - si.RAMP_FLAT), top), (sgn * e, z0 + st)]
            g.append(prism(sec, axis, -along, along, INSERT_RGBA, "frame"))
    rw, sy = si.RIDGE_W / 2, hy - by
    for cx, _cy, wl, _ww in si.across_windows()[:-1]:
        x = cx + wl / 2 + rw
        sec = [(x - rw, z0), (x + rw, z0), (x + rw, z0 + st), (x, z0 + st + rw), (x - rw, z0 + st)]
        g.append(prism(sec, "y", -sy, sy, INSERT_RGBA, "frame"))
    for y0, y1 in ((hy - si.TAB_T, hy), (-hy, -hy + si.TAB_T)):
        g.append(box(-si.TAB_W / 2, si.TAB_W / 2, y0, y1, z0, z0 + si.FRAME_T + si.TAB_H, INSERT_RGBA, "frame"))
    return g


def printed_screen(name, z0):
    """The square-hole screen at the bottom of every window, as tapered bars (convex prisms) that
    leave the exact hole size at the top surface and widen RELIEF_DEG downward, as the CAD cuts it.
    Bars along Y run through both window rows, bars along X through all three columns (the ribs
    cover the joins). Returns geoms, hole count, open area at the top surface."""
    si = cad()[1]
    across = name in getattr(si, "ACROSS", {})
    hole, bar, screen_t = (si.ACROSS if across else si.INSERTS)[name]
    pitch, z1, taper = hole + bar, z0 + screen_t, screen_t * math.tan(math.radians(si.RELIEF_DEG))
    win, rows = (si.across_windows(), 1) if across else (si.windows(), si.ROWS)
    g, n_holes = [], 0
    for cx, cy, wl, ww in win:
        n_holes += int((wl - bar) // pitch) * int((ww - bar) // pitch)

    def bars(axis, w0, w1, n, a0, a1):
        c0 = (w0 + w1) / 2 - (n - 1) * pitch / 2
        for a, b, ah, bh in solid_runs(w0, w1, [c0 + k * pitch for k in range(n)], hole):
            section = [(a + taper * ah, z0), (b - taper * bh, z0), (b, z1), (a, z1)]
            g.append(prism(section, axis, a0, a1, SCREEN_RGBA, "screen"))

    if across:
        ib_x, ib_y = si.L / 2 - si.ACROSS_BORDER[0], si.W / 2 - si.ACROSS_BORDER[1]
    else:
        ib_x, ib_y = si.L / 2 - si.BORDER, si.W / 2 - si.BORDER
    for cx, _cy, wl, _ww in win[::rows]:             # one per column: bars along Y
        bars("y", cx - wl / 2, cx + wl / 2, int((wl - bar) // pitch), -ib_y, ib_y)
    for _cx, cy, _wl, ww in win[:rows]:              # one per row: bars along X
        bars("x", cy - ww / 2, cy + ww / 2, int((ww - bar) // pitch), -ib_x, ib_x)
    return g, n_holes, n_holes * hole * hole


def mesh_wires(spec, z0):
    """Woven mesh as wires over the whole insert outline, X wires below, Y wires on top, starting
    at height z0. Apertures are centred on the insert. Returns geoms, wire centres along x and y."""
    si = cad()[1]
    a, d = spec["aperture"], spec["wire_d"]
    p, r = a + d, d / 2

    def centres(half):
        n = int((half - r) / p + 0.5)               # wires at (k + 1/2) p that fit inside +-half
        return [(k + 0.5) * p for k in range(-n, n)]

    ys, xs = centres(si.W / 2), centres(si.L / 2)
    g = [capsule("x", -si.L / 2, si.L / 2, y, z0 + r, r, WIRE_RGBA, "screen") for y in ys]
    g += [capsule("y", -si.W / 2, si.W / 2, x, z0 + 3 * r, r, WIRE_RGBA, "screen") for x in xs]
    return g, xs, ys


def open_len(w0, w1, wires, d):
    """Length of [w0, w1] not under any wire of diameter d."""
    return (w1 - w0) - sum(max(0.0, min(w1, c + d / 2) - max(w0, c - d / 2)) for c in wires)


def insert_spec(arg):
    """(zone suffix, kind, CAD/mesh name) for a spec argument such as 5mm, sieve_insert_5mm or mesh5.
    A custom printed screen h<hole>b<bar> (optimize.py's naming, e.g. h2p15b1p15: 2.15 mm holes, 1.15 mm bars,
    sizes as modelled, so nominal - 0.15 for the hole) is added to sieve_insert.INSERTS, or with _across to
    sieve_insert.ACROSS (ribs-across frame), on first use; screen 1.6 mm thick for holes of 3 mm and up, else 1.4."""
    si = cad()[1]
    short = arg.removeprefix("sieve_insert_")
    m = CUSTOM_INSERT.match(short)
    if m and f"sieve_insert_{short}" not in si.INSERTS and f"sieve_insert_{short}" not in getattr(si, "ACROSS", {}):
        hole, bar = (float(v.replace("p", ".")) for v in m.group(1, 2))
        (si.ACROSS if m.group(3) else si.INSERTS)[f"sieve_insert_{short}"] = (hole, bar, 1.6 if hole >= 3 else 1.4)
    if f"sieve_insert_{short}" in si.INSERTS:
        return short, "printed", f"sieve_insert_{short}"
    if f"sieve_insert_{short}" in getattr(si, "ACROSS", {}):
        return short, "across", f"sieve_insert_{short}"
    if arg in MESHES:
        return arg, "mesh", arg
    raise ValueError(f"unknown insert {arg!r}: use one of {[n.removeprefix('sieve_insert_') for n in si.INSERTS]}"
                     f" or {list(MESHES)}")


def insert(arg, z_seat, drain_area):
    """Geoms of one insert seated on a ledge top at z_seat, and its layer record."""
    si = cad()[1]
    short, kind, name = insert_spec(arg)
    win_area = sum(wl * ww for _, _, wl, ww in (si.across_windows() if kind == "across" else si.windows()))
    if kind in ("printed", "across"):
        z0 = z_seat
        screen, n_holes, open_area = printed_screen(name, z0)
        s, bar, screen_t = (si.ACROSS if kind == "across" else si.INSERTS)[name]
        surface, opening = (z0, z0 + screen_t), f"{s:g} mm square holes ({n_holes}), bars {bar:g} mm"
        extra = {"holes": n_holes}
    else:
        spec = MESHES[name]
        s, d = spec["aperture"], spec["wire_d"]
        z0 = z_seat + (2 * d if spec["side"] == "under" else 0.0)
        z_mesh = z0 + si.FRAME_T if spec["side"] == "top" else z_seat
        screen, xs, ys = mesh_wires(spec, z_mesh)
        open_area = sum(open_len(cx - wl / 2, cx + wl / 2, xs, d) * open_len(cy - ww / 2, cy + ww / 2, ys, d)
                        for cx, cy, wl, ww in si.windows())
        surface, opening = (z_mesh, z_mesh + 2 * d), f"{s:g} mm woven mesh, {d:g} mm wire, glued {spec['side']}"
        extra = {"mesh": {**spec, "status": MESH_STATUS}, "wires": len(screen)}
    geoms = (insert_frame_across(z0, name) if kind == "across" else insert_frame(z0)) + screen
    layer = {"zone": f"on_{short}", "insert": name, "opening": opening, "rule": "square", "opening_mm": s,
             "insert_bottom_z_mm": round(z0, 3), "surface_z_mm": [round(v, 3) for v in surface],
             "open_area_mm2": round(open_area, 1), "open_pct_of_drainable": round(100 * open_area / drain_area, 1),
             "open_pct_of_windows": round(100 * open_area / win_area, 1), "geoms": len(geoms), **extra}
    return geoms, layer


def ideal_zone(dims, layers, last):
    """First layer whose opening the particle can't pass (rules in the module docstring), else `last`.
    layers: ((zone, rule, opening_mm), ...) top to bottom; rule "square", "slot" or "solid"."""
    w, t = dims["width"], dims["thickness"]
    for zone, rule, s in layers:
        if rule == "solid" or t > s or (rule == "square" and not ellipse_fits(w, t, s, s)):
            return zone
    return last


def jets(top, half_x):
    """Placeholder until the bench measures the nozzles: two jets straight down on the centre line."""
    return [{"pos_lab": (x, 0.0, top + JET_Z), **JET} for x in (-half_x / 2, half_x / 2)]


def geom_count(geoms):
    out = {"total": len(geoms)}
    for key in ("role", "type"):
        for g in geoms:
            out[f"{key}:{g[key]}"] = out.get(f"{key}:{g[key]}", 0) + 1
    return out


def build_inserts(args):
    """inserts:<a>,<b>,...[,pitch=<mm>]  top to bottom, one insert per holder box, on a catch pan. pitch is box
    bottom to box bottom (default the box height: rim on rim). A larger pitch leaves open air between the
    boxes, as on BioKEA's tower frame, where each box hangs from a rod through its +X tab; a grain that
    bounces out through a gap falls to an invisible tub floor and counts as lost."""
    opts = dict(a.split("=", 1) for a in args if "=" in a)
    args = [a for a in args if "=" not in a]
    if set(opts) - {"pitch", "holder"}:
        raise ValueError(f"unknown inserts option(s) {sorted(set(opts) - {'pitch', 'holder'})}: use pitch=<mm>, "
                         "holder=seesaw")
    if opts.get("holder", "frame") not in ("frame", "seesaw"):
        raise ValueError(f"holder={opts['holder']}: use holder=seesaw (or leave it out for frame_holder.py's box)")
    seesaw = opts.get("holder") == "seesaw"
    if not args:
        raise ValueError("inserts needs insert names, e.g. inserts:5mm,2mm or inserts:mesh5,mesh2")
    fh = cad()[0]
    H, ix, iy = fh.H, fh.L / 2 - fh.WALL, fh.W / 2 - fh.WALL
    pitch = float(opts.get("pitch", H))
    if pitch < H:
        raise ValueError(f"pitch {pitch:g} mm is less than the box height ({H:g} mm)")
    drain_area = fh.OPEN_L * fh.OPEN_W
    if seesaw:
        geoms, catch_floor = seesaw_pan()
    else:
        geoms, catch_floor = holder(0.0, solid_base=True, close_notches=True), fh.LEDGE_T
    layers = []
    for k, arg in enumerate(reversed(args)):          # bottom box first
        z0 = (k + 1) * pitch
        g, layer = insert(arg, z0 + fh.LEDGE_T, drain_area)
        geoms += holder(z0, close_notches=True, seesaw=seesaw) + g
        layer["holder_z_mm"] = [z0, z0 + H]
        layers.insert(0, layer)
    names = [layer["zone"] for layer in layers]
    for k, layer in enumerate(layers):                # repeated inserts get numbered zones
        if names.count(layer["zone"]) > 1:
            layer["zone"] += f"_{k + 1}"
    top = layers[0]["surface_z_mm"][1]
    z_lid = top + LID_ABOVE
    geoms += lid(ix, iy, len(args) * pitch + H, z_lid, fh.WALL, catch_floor - fh.LEDGE_T)
    if pitch > H:
        geoms.append(box(-TUB_HALF, TUB_HALF, -TUB_HALF, TUB_HALF, -TUB_FLOOR - fh.WALL, -TUB_FLOOR, LID_RGBA, "lid"))
    spaced = "" if pitch == H else f", {pitch - H:g} mm of open air between boxes (pitch {pitch:g} mm)"

    zones, z_above = [], z_lid
    for layer in layers:
        zones.append({"name": layer["zone"], "box": [-ix, ix, -iy, iy, layer["surface_z_mm"][1], z_above]})
        z_above = layer["surface_z_mm"][0]
    zones.append({"name": "catch", "box": [-ix, ix, -iy, iy, catch_floor, z_above]})
    rules = tuple((layer["zone"], layer["rule"], layer["opening_mm"]) for layer in layers)
    return Design(
        name="inserts:" + ",".join(args) + ("" if pitch == H else f",pitch={pitch:g}") + (",holder=seesaw" if seesaw else ""),
        geoms=geoms, zones=zones,
        spawn=[-ix + SPAWN_INSET, ix - SPAWN_INSET, -iy + SPAWN_INSET, iy - SPAWN_INSET, top + SPAWN_Z[0], top + SPAWN_Z[1]],
        ideal_zone=functools.partial(ideal_zone, layers=rules, last="catch"),
        jets_default=jets(top, ix),
        info={"stacking": "tower of holder boxes (confirmed by the user), one insert per box, top to bottom in spec "
                          "order, " + (f"each box hanging {pitch:g} mm above the one below{spaced}" if spaced else
                                       "each box on the rim of the one below") +
                          ("; seesaw holders (cad/seesaw_holder.py: no tab, no notches, pivot pins in the middle) over "
                           "its deep catch pan (rim and pivot as on a box, floor CATCH_DEPTH lower, inward lip)" if seesaw else
                           "; catch pan under the bottom box = the holder with its open centre filled solid. Finger "
                           "notches closed by invisible lids."), "pitch_mm": pitch, "holder": "seesaw" if seesaw else "frame",
              "open_area_note": "printed: holes x hole^2 at the top surface; mesh: wire-free area inside the six "
                                "windows (the frame blocks the rest)",
              "layers": layers, "catch_z_mm": [catch_floor, z_above], "top_surface_z_mm": top, "lid_z_mm": z_lid,
              "drainable_area_mm2": drain_area, "drainable_note": f"only the {fh.OPEN_L:g} x {fh.OPEN_W:g} open bottom "
                                                                  "drains; the windows lie entirely over it",
              "geom_count": geom_count(geoms),
              "jets": "placeholder: two jets 60 mm above the top surface, straight down, until the bench measures them"})


def build_plinko(args):
    """plinko: the layers of cad/plinko_layers.py in one holder box (no arguments)."""
    if args:
        raise ValueError(f"plinko takes no arguments, got {args}")
    fh, _, pl = cad()
    hx, hy, ox, oy = pl.IN_L / 2, pl.IN_W / 2, pl.OUT_L / 2, pl.OUT_W / 2
    bottoms = pl.bottoms()
    taper = math.tan(math.radians(pl.RELIEF_DEG))
    geoms = holder(0.0)          # the layer walls cover the finger notches from inside
    layers = []
    for idx, (name, floor, gap, b_top, h, wall_h, tab_x) in enumerate(pl.LAYERS):
        zb, g = bottoms[name], []
        g += [box(-ox, -hx, -oy, oy, zb, zb + wall_h, LAYER_RGBA, "wall"), box(hx, ox, -oy, oy, zb, zb + wall_h, LAYER_RGBA, "wall"),
              box(-hx, hx, -oy, -hy, zb, zb + wall_h, LAYER_RGBA, "wall"), box(-hx, hx, hy, oy, zb, zb + wall_h, LAYER_RGBA, "wall")]
        for y0, y1 in ((hy - pl.TAB_T, hy), (-hy, -hy + pl.TAB_T)):      # pull tabs up to TAB_TOP
            g.append(box(tab_x - pl.TAB_W / 2, tab_x + pl.TAB_W / 2, y0, y1, zb, pl.TAB_TOP, LAYER_RGBA, "frame"))
        record = {"zone": name, "floor": floor, "bottom_z_mm": zb, "wall_top_z_mm": zb + wall_h, "surface_z_mm": [zb, zb + h]}
        if floor == "rods":
            # mirrors plinko_layers.rods(): first and last gaps exact, leftover closed by a filler,
            # rods run 0.5 into the walls, a rib along X at y = 0
            b_bot, pitch, ry = b_top - 2 * h * taper, gap + b_top, hy + 0.5
            xs, x = [], -hx + gap + b_top / 2
            while x + b_top / 2 + gap <= hx + 1e-6:
                xs.append(x)
                x += pitch
            g += [prism([(x - b_bot / 2, zb), (x + b_bot / 2, zb), (x + b_top / 2, zb + h), (x - b_top / 2, zb + h)],
                        "y", -ry, ry, ROD_RGBA, "gate") for x in xs]
            end = xs[-1] + b_top / 2 + gap
            if end < hx:
                g.append(box(end, hx + 0.5, -ry, ry, zb, zb + h, ROD_RGBA, "frame"))
            g.append(box(-hx - 0.5, hx + 0.5, -pl.RIB_W / 2, pl.RIB_W / 2, zb, zb + h, ROD_RGBA, "frame"))
            # bars tying the rod ends cut by each lower layer's tab slot (sizes as in plinko_layers.layer());
            # the slots themselves are left out: the lower tab fills them to within SLOT_FIT
            y_in = hy - pl.TAB_T - 2 * pl.SLOT_FIT
            for *_rest, lower_tab_x in pl.LAYERS[idx + 1:]:
                x0 = lower_tab_x - pl.TAB_W / 2 - 3
                g += [box(x0, x0 + pl.TAB_W + 6, y_in - 2.0, y_in, zb, zb + h, ROD_RGBA, "frame"),
                      box(x0, x0 + pl.TAB_W + 6, -y_in, -y_in + 2.0, zb, zb + h, ROD_RGBA, "frame")]
            record.update({"rule": "slot", "opening_mm": gap, "rods": len(xs), "pitch_mm": round(pitch, 3),
                           "rod_width_top_bottom_mm": [b_top, round(b_bot, 3)], "gap_bottom_mm": round(gap + b_top - b_bot, 3),
                           "open_area_mm2_less_rib": round(gap * (len(xs) + 1) * (pl.IN_W - pl.RIB_W), 1),
                           "open_pct_of_floor": round(100 * gap * (len(xs) + 1) / pl.IN_L, 1)})
        else:
            g.append(box(-hx - 0.5, hx + 0.5, -hy - 0.5, hy + 0.5, zb, zb + h, LAYER_RGBA, "floor"))
            record.update({"rule": "solid", "opening_mm": 0.0})
        record["geoms"] = len(g)
        geoms += g
        layers.append(record)
    top = layers[0]["surface_z_mm"][1]
    z_lid = top + LID_ABOVE
    geoms += lid(hx, hy, layers[0]["wall_top_z_mm"], z_lid, fh.WALL)

    zones, z_above = [], z_lid
    for layer in layers:
        zones.append({"name": layer["zone"], "box": [-hx, hx, -hy, hy, layer["surface_z_mm"][1], z_above]})
        z_above = layer["bottom_z_mm"]
    rules = tuple((layer["zone"], layer["rule"], layer["opening_mm"]) for layer in layers)
    return Design(
        name="plinko", geoms=geoms, zones=zones,
        spawn=[-hx + SPAWN_INSET, hx - SPAWN_INSET, -hy + SPAWN_INSET, hy - SPAWN_INSET, top + SPAWN_Z[0], top + SPAWN_Z[1]],
        ideal_zone=functools.partial(ideal_zone, layers=rules[:-1], last=rules[-1][0]),
        jets_default=jets(top, hx),
        info={"stacking": "plinko_layers.bottoms(): the catch layer on the holder ledge, each layer on the wall top of "
                          "the one below; the top layer stands above the holder rim",
              "layers": layers, "top_surface_z_mm": top, "lid_z_mm": z_lid, "geom_count": geom_count(geoms),
              "jets": "placeholder: two jets 60 mm above the top surface, straight down, until the bench measures them"})


if __name__ == "__main__":
    for spec in sys.argv[1:] or ["inserts:5mm,2mm", "inserts:mesh5,mesh2", "plinko"]:
        kind, _, arg = spec.partition(":")
        d = (build_plinko if kind == "plinko" else build_inserts)([a for a in arg.split(",") if a])
        print(d.name, json.dumps(d.info["geom_count"]))
        print("  spawn", [round(v, 2) for v in d.spawn])
        for z in d.zones:
            print("  zone", z["name"], [round(v, 2) for v in z["box"]])
        for layer in d.info["layers"]:
            print("  layer", json.dumps(layer))
