"""The gated container tower for the sim (cad/gated_container.py, the README's final design), in the tray
frame (see common.Design). Units mm.

    gated:<slope>,<strip>,<strip>,...[,key=value...]

    slope    floor slope in degrees (gated_container.FLOOR_SLOPE_DEG), e.g. 2
    strip    one gate strip per tower level, top level first. Either a STRIPS name (gate_w5p0 or w5p0) or a
             numeric token: w4.6 / w4p6 (width gaps), t1.3 / t1p3 (tunnels). A width gap may carry its own
             height: w4.6x5.0 (a "window" gate: the gap's height is capped at 5.0 instead of GATE_H)
    key=value  overrides of gated_container.py constants for every level:
             gh=GATE_H  tw=TUNNEL_W  tooth=TOOTH  slot=<drop slot length, sets GATE_X>
             rib=<h>x<pitch>x<steep>  a ratchet floor (PROPOSAL, not in the CAD yet): sawtooth ribs across the
             floor, h tall, one every pitch mm, each rising gently toward the gate and dropping on the gate
             side over steep x pitch, so a symmetric stroke walks grains toward the gate. They stop 3 mm short
             of the strip.
             gx=<x1>/<x2>/...  gate position (strip centre, mm along the container, gate end +X) per level instead
             of GATE_X (PROPOSAL, mid-slot tower): with slot=<length> the drop slot runs from the strip's downstream
             face for that length, and a 30 deg wedge (capped 2 mm under the wall top) fills the rest of the
             container beyond it, sloping back into the slot. The strip and its rails must clear the pull tabs
             (|x| >= 13.15).
             flip=0   don't flip alternate levels (with gx: what passes L1 lands just upstream of L2's gate)
             pitch=<mm>  box bottom to box bottom (default the box height: rim on rim). A larger pitch leaves a gap
             between levels, so each container lifts out on its own, and lets rocking.py's seesaw rock every level
             on its own pivot with neighbours in opposite phase (docs/SYSTEM.md section 3). Default unchanged.

    e.g. gated:2,w5p0,t1p4              today's CAD with two existing strips
         gated:2.6,w4.4x6,t1.5,tw=6,tooth=1.6,slot=9

The tower (designs_holder.py's stacking, confirmed by the user): one holder box per level, stacked rim on
rim, one gated container per box on the box's ledge, a catch pan (the holder with its open centre filled)
under the bottom box. The top level's gate is at +X; every other level is flipped 180 deg about Z
(gated_container.py docstring), so what drops through a slot lands on the solid, high end of the next level.
Load: the sample is poured onto the high (upstream) half of the top container.

Per container (gated_container.container(), mirrored in x on flipped levels):
    walls LW thick and WALL_H tall; a solid floor FLOOR_T thick at the gate that rises FLOOR_SLOPE_DEG away from it;
    the strip standing on the floor at GATE_X between two rails per side; the drop slot from the strip's
    downstream face to OPEN_X (|y| < OPEN_Y), with a FLOOR_T ledge beside it; a 45 deg ramp from OPEN_X to the
    end wall that sheds into the slot; the two pull tabs (they stand 4 mm into the container at mid-length).
Left out: the outside corner fillets and the strip's debossed label.
The pull tabs reach TAB_TOP above the container bottom, which is 3 mm above the holder rim, so in a rim-on-rim
stack they would hit the ledge of the box above. Here they are cut off at that ledge (see TAB_CLASH in info).

Zones, flow order: L1 .. Ln (a container's inside, upstream of its strip, up to the ledge of the box above), then
catch. A particle in a strip, in a drop slot, on the ledge beside a slot or on a ramp is "between".
Ideal zone: the first level whose openings the particle can't pass at any tilt (designs.fits), else catch.

Run from sim\\ to print a summary:  <venv python> designs_gated.py gated:2,w5p0,t1p4
"""
import json
import math
import re
import sys

import numpy as np

import designs  # noqa: F401  (stubs cadquery/cadkit and puts cad/ on the path)
import designs_holder as dh
from common import Design, ellipse_fits

import gated_container as gc  # noqa: E402

FLOOR_RGBA = [0.72, 0.78, 0.86, 1.0]
WALL_RGBA = [0.60, 0.68, 0.78, 0.35]
GATE_RGBA = [0.20, 0.35, 0.75, 1.0]
RAIL_RGBA = [0.45, 0.55, 0.70, 1.0]
TAB_RGBA = [0.80, 0.86, 0.95, 1.0]
LID_ABOVE = 60.0           # invisible lid this far above the top holder's rim
SPAWN_RUN = 50.0           # the sample is poured on this length of the top container's high end
SPAWN_INSET = 3.0
TOKEN = re.compile(r"^(?:gate_)?([wt])(\d+(?:[.p]\d+)?)(?:x(\d+(?:[.p]\d+)?))?$")
KEYS = {"gh": "GATE_H", "tw": "TUNNEL_W", "tooth": "TOOTH", "slot": "slot", "rib": "rib", "gx": "gx", "flip": "flip",
        "pitch": "pitch"}
WEDGE_DEG = 30.0           # mid-slot containers: slope of the fill beyond the slot, back toward it
RIB_CLEAR = 3.0            # ribs stop this far upstream of the strip
RIB_EMBED = 0.3            # ribs reach this far into the floor, so they fuse with it


def num(s):
    return float(s.replace("p", "."))


def parse(args):
    """(slope_deg, [(kind, size, height or None)], {constant: value})."""
    if not args:
        raise ValueError("gated needs a slope and at least one strip, e.g. gated:2,w5p0,t1p4")
    slope, strips, over = float(args[0]), [], {}
    for a in args[1:]:
        if "=" in a:
            k, _, v = a.partition("=")
            if k not in KEYS:
                raise ValueError(f"unknown gated key {k!r}: use {list(KEYS)}")
            over[KEYS[k]] = (tuple(num(x) for x in v.split("x")) if k == "rib" else
                             tuple(float(x) for x in v.split("/")) if k == "gx" or "/" in v else float(v))
            if k == "rib" and len(over["rib"]) != 3:
                raise ValueError(f"rib takes <h>x<pitch>x<steep>, got {v!r}")
            continue
        name = a if a.startswith("gate_") else f"gate_{a}"
        if name in gc.STRIPS:
            kind, size = gc.STRIPS[name]
            strips.append((kind, float(size), None))
            continue
        m = TOKEN.match(a)
        if not m:
            raise ValueError(f"bad gated strip {a!r}: use w<size>, t<size>, w<size>x<height> or a STRIPS name")
        kind, size, h = m.group(1), num(m.group(2)), m.group(3)
        if h and kind != "w":
            raise ValueError(f"only width gaps take a height: {a!r}")
        strips.append((kind, size, num(h) if h else None))
    if not strips:
        raise ValueError("gated needs at least one strip")
    if "gx" in over:
        if len(over["gx"]) != len(strips):
            raise ValueError(f"gx needs one position per level, got {over['gx']} for {len(strips)} strips")
        if "slot" not in over:
            raise ValueError("gx needs slot=<length>")
        if not isinstance(over["slot"], tuple):
            over["slot"] = (over["slot"],) * len(strips)
        for g, sl in zip(over["gx"], over["slot"]):
            clear = gc.STRIP_T / 2 + gc.SLOT_FIT / 2 + gc.RAIL_T
            if abs(g) - clear < gc.TAB_W / 2:
                raise ValueError(f"gate at x {g:g}: the strip and rails would hit the pull tabs (|x| < {gc.TAB_W / 2 + clear:g})")
            if g + gc.STRIP_T / 2 + sl > gc.OPEN_X + 1e-6 or g - gc.STRIP_T / 2 < -gc.OPEN_X:
                raise ValueError(f"gate at x {g:g} with slot {sl:g}: the slot must lie over the holder's open bottom")
    return slope, strips, over


def token(kind, size, h=None):
    return f"{kind}{size:g}".replace(".", "p") + (f"x{h:g}".replace(".", "p") if h else "")


def params(slope, over, level=0):
    """Container numbers for one level of this spec, from gated_container.py with the overrides applied."""
    p = {"slope": slope, "GATE_H": over.get("GATE_H", gc.GATE_H), "TUNNEL_W": over.get("TUNNEL_W", gc.TUNNEL_W),
         "TOOTH": over.get("TOOTH", gc.TOOTH)}
    if "gx" in over:
        gate_x = over["gx"][level]
        p["slot"] = over["slot"][level]
    else:
        gate_x = gc.OPEN_X - over["slot"] - gc.STRIP_T / 2 if "slot" in over else gc.GATE_X
        p["slot"] = gc.OPEN_X - (gate_x + gc.STRIP_T / 2)
    p["GATE_X"] = gate_x
    p["slot_end"] = gate_x + gc.STRIP_T / 2 + p["slot"]
    x_lo = -gc.IN_L / 2 - 0.5
    p["x_lo"] = x_lo
    p["rise"] = (gate_x - gc.STRIP_T / 2 - x_lo) * math.tan(math.radians(slope))
    p["rib"] = over.get("rib")
    return p


def opening(kind, size, h, p):
    """(width across, height) of one opening."""
    return (size, h or p["GATE_H"]) if kind == "w" else (p["TUNNEL_W"], size)


def openings_layout(ow, p):
    """Centres (y) of the openings in a strip: whole openings inside the drop slot's span, centred."""
    pitch = ow + p["TOOTH"]
    n = int((2 * gc.OPEN_Y - p["TOOTH"]) // pitch)
    return [-(n - 1) * pitch / 2 + i * pitch for i in range(n)]


class Level:
    """Geoms of one container, built in its own frame (gate at +X, z = 0 under the container), then placed."""

    def __init__(self, z0, flip):
        self.z0, self.s, self.geoms = z0, -1.0 if flip else 1.0, []

    def box(self, x0, x1, y0, y1, z0, z1, rgba, role):
        a, b = sorted((self.s * x0, self.s * x1))
        self.geoms.append(dh.box(a, b, *sorted((y0, y1)), self.z0 + z0, self.z0 + z1, rgba, role))

    def prism_x(self, section, y0, y1, rgba, role):
        """Convex prism: the (x, z) polygon `section` extruded along y."""
        verts = [[self.s * x, y, self.z0 + z] for y in (y0, y1) for x, z in section]
        self.geoms.append({"type": "mesh", "vertices": verts, "rgba": rgba, "role": role})


def container(lv, strip, p, tab_top):
    L, W, IN_L, IN_W, LW, FT = gc.L, gc.W, gc.IN_L, gc.IN_W, gc.LW, gc.FLOOR_T
    gx, x_lo, rise = p["GATE_X"], p["x_lo"], p["rise"]
    x_up, x_dn = gx - gc.STRIP_T / 2, gx + gc.STRIP_T / 2
    hy = IN_W / 2 + 0.5
    # walls
    lv.box(-L / 2, -IN_L / 2, -W / 2, W / 2, 0, gc.WALL_H, WALL_RGBA, "wall")
    lv.box(IN_L / 2, L / 2, -W / 2, W / 2, 0, gc.WALL_H, WALL_RGBA, "wall")
    for sy in (-1, 1):
        lv.box(-IN_L / 2, IN_L / 2, sy * IN_W / 2, sy * W / 2, 0, gc.WALL_H, WALL_RGBA, "wall")
    # floor: the slope up to the strip's upstream face, then flat under the strip (two convex pieces)
    lv.prism_x([(x_lo, 0), (x_up, 0), (x_up, FT), (x_lo, FT + rise)], -hy, hy, FLOOR_RGBA, "floor")
    lv.box(x_up, x_dn, -hy, hy, 0, FT, FLOOR_RGBA, "floor")
    # ratchet ribs (proposal) on the slope
    if p.get("rib"):
        h, pitch, steep = p["rib"]
        x_end = x_up - RIB_CLEAR
        tan = math.tan(math.radians(p["slope"]))
        z = lambda x: FT + (x_up - x) * tan
        x0 = -IN_L / 2
        while x0 + pitch <= x_end + 1e-9:
            x1, xa = x0 + pitch, x0 + pitch * (1 - steep)
            lv.prism_x([(x0, z(x0) - RIB_EMBED), (x1, z(x1) - RIB_EMBED), (x1, z(x1)), (xa, z(xa) + h), (x0, z(x0))],
                       -hy, hy, FLOOR_RGBA, "floor")
            x0 = x1
    # ledge beside the drop slot, over the holder's ledge
    x_se = p["slot_end"]
    for sy in (-1, 1):
        lv.box(x_dn, x_se + 0.5, sy * gc.OPEN_Y, sy * hy, 0, FT, FLOOR_RGBA, "floor")
    lip = 0.4
    if x_se >= gc.OPEN_X - 1e-6:
        # 45 deg ramp from the slot's far edge to the end wall, with a 0.4 mm lip
        run = IN_L / 2 + 0.5 - gc.OPEN_X
        lv.prism_x([(gc.OPEN_X, 0), (IN_L / 2 + 0.5, 0), (IN_L / 2 + 0.5, run + lip), (gc.OPEN_X, lip)],
                   -hy, hy, FLOOR_RGBA, "floor")
    else:
        # mid-slot: a wedge fills the container beyond the slot, sloping back into it
        x_end = IN_L / 2 + 0.5
        top = min(lip + (x_end - x_se) * math.tan(math.radians(WEDGE_DEG)), gc.WALL_H - 2.0)
        x_knee = x_se + (top - lip) / math.tan(math.radians(WEDGE_DEG))
        lv.prism_x([(x_se, 0), (x_end, 0), (x_end, top), (x_knee, top), (x_se, lip)], -hy, hy, FLOOR_RGBA, "floor")
    # rails, two per side
    for side in (-1, 1):
        rx = gx + side * (gc.STRIP_T / 2 + gc.SLOT_FIT / 2 + gc.RAIL_T / 2)
        for sy in (-1, 1):
            lv.box(rx - gc.RAIL_T / 2, rx + gc.RAIL_T / 2, sy * (IN_W / 2 - gc.RAIL_P), sy * hy, 0, gc.WALL_H,
                   RAIL_RGBA, "wall")
    # pull tabs
    for sy in (-1, 1):
        lv.box(-gc.TAB_W / 2, gc.TAB_W / 2, sy * (W / 2 - gc.TAB_T), sy * W / 2, 0, tab_top, TAB_RGBA, "frame")
    # the strip, standing on the flat floor between the rails
    kind, size, h = strip
    ow, oh = opening(kind, size, h, p)
    sl = (IN_W - gc.END_FIT) / 2
    top = FT + gc.STRIP_H
    ys = openings_layout(ow, p)
    lv.box(x_up, x_dn, -sl, sl, FT + oh, top, GATE_RGBA, "gate")
    edges = [-sl] + [e for y in ys for e in (y - ow / 2, y + ow / 2)] + [sl]
    for a, b in zip(edges[::2], edges[1::2]):
        if b - a > 1e-6:
            lv.box(x_up, x_dn, a, b, FT, FT + oh, GATE_RGBA, "gate")
    return {"kind": kind, "size_mm": size, "opening_mm": [round(ow, 3), round(oh, 3)], "openings": len(ys),
            "span_mm": round(len(ys) * ow + (len(ys) - 1) * p["TOOTH"], 3)}


def build(args):
    slope, strips, over = parse(args)
    ps = [params(slope, over, k) for k in range(len(strips))]
    p = ps[0]
    flip = over.get("flip", 1.0) != 0
    fh = dh.cad()[0]
    H, n = fh.H, len(strips)
    P = over.get("pitch", H)                         # box bottom to box bottom; H = rim on rim
    if P < H:
        raise ValueError(f"gated pitch={P:g} is less than the box height {H:g}")
    hx, hy = fh.L / 2 - fh.WALL, fh.W / 2 - fh.WALL
    geoms = dh.holder(0.0, solid_base=True, close_notches=True)
    tab_top = min(gc.TAB_TOP, P - fh.LEDGE_T)        # the ledge of the box above
    levels, zones, layers = [], [], []
    for k, strip in enumerate(strips):               # k = 0 is the top level
        z_h = (n - k) * P
        layers.append({"zone": f"L{k + 1}", "holder_z_mm": [z_h, z_h + H]})
        geoms += dh.holder(z_h, close_notches=True)
        lv = Level(z_h + fh.LEDGE_T, flip=flip and k % 2 == 1)
        info = container(lv, strip, ps[k], tab_top)
        geoms += lv.geoms
        z_c = z_h + fh.LEDGE_T
        x_up = ps[k]["GATE_X"] - gc.STRIP_T / 2
        a, b = sorted((lv.s * -gc.IN_L / 2, lv.s * x_up))
        levels.append({**info, "level": f"L{k + 1}", "gate_end": "+X" if lv.s > 0 else "-X",
                       "container_bottom_z_mm": z_c, "token": token(*strip), "gate_x_mm": round(ps[k]["GATE_X"], 3),
                       "slot_end_mm": round(ps[k]["slot_end"], 3), "floor_rise_mm": round(ps[k]["rise"], 3)})
        zones.append({"name": f"L{k + 1}", "box": [a, b, -gc.IN_W / 2, gc.IN_W / 2, z_c, z_h + H]})
    z_bottom = H + fh.LEDGE_T
    zones.append({"name": "catch", "box": [-hx, hx, -hy, hy, fh.LEDGE_T, z_bottom]})
    rim = n * P + H
    zones[0]["box"][5] = rim + LID_ABOVE
    geoms += dh.lid(hx, hy, rim, rim + LID_ABOVE, fh.WALL)

    open_ = [opening(*s, pk) for s, pk in zip(strips, ps)]

    def ideal_zone(dims):
        for k, (ow, oh) in enumerate(open_):
            if not ellipse_fits(dims["width"], dims["thickness"], ow, oh):
                return f"L{k + 1}"
        return "catch"

    z_top = P * n + fh.LEDGE_T
    x0 = -gc.IN_L / 2 + SPAWN_INSET
    x1 = min(x0 + SPAWN_RUN, p["GATE_X"] - gc.STRIP_T / 2 - 10.0)
    spawn = [x0, x1, -gc.IN_W / 2 + SPAWN_INSET + gc.TAB_T, gc.IN_W / 2 - SPAWN_INSET - gc.TAB_T,
             z_top + gc.FLOOR_T + p["rise"] + 1.0 + (p["rib"][0] if p["rib"] else 0.0), rim + LID_ABOVE - 5.0]
    jets = [{"pos_lab": [(1 if k % 2 == 0 or not flip else -1) * (ps[k]["GATE_X"] - 10.0), 0.0, rim + 40.0],
             "dir": list(np.array([0.0, 0.0, -1.0])), **designs.JET_PLACEHOLDER} for k in range(n)]
    name = f"gated:{slope:g}," + ",".join(token(*s) for s in strips)
    extra = []
    for key, const in (("gh", "GATE_H"), ("tw", "TUNNEL_W"), ("tooth", "TOOTH")):
        if const in over:
            extra.append(f"{key}={over[const]:g}")
    if "slot" in over:
        sl = over["slot"]
        extra.append("slot=" + ("/".join(f"{v:g}" for v in sl) if isinstance(sl, tuple) and len(set(sl)) > 1 else
                                f"{sl[0] if isinstance(sl, tuple) else sl:g}"))
    if over.get("rib"):
        extra.append("rib=" + "x".join(f"{v:g}" for v in over["rib"]))
    if "gx" in over:
        extra.append("gx=" + "/".join(f"{v:g}" for v in over["gx"]))
    if not flip:
        extra.append("flip=0")
    if P != H:
        extra.append(f"pitch={P:g}")
    name += "".join("," + e for e in extra)
    # a spaced tower describes its boxes the way designs_holder does, so rocking.py can seesaw each level
    spaced = {"layers": layers, "catch_z_mm": 0.0, "pitch_mm": P} if P > H else {}
    return Design(
        name=name, geoms=geoms, zones=zones, spawn=spawn, ideal_zone=ideal_zone, stroke_axis=[1.0, 0.0, 0.0],
        jets_default=jets,
        info={**spaced, "levels": levels, "floor_slope_deg": slope, "floor_rise_mm": round(p["rise"], 3),
              "gate_x_mm": round(p["GATE_X"], 3), "drop_slot_mm": [round(p["slot"], 3), 2 * gc.OPEN_Y],
              "GATE_H": p["GATE_H"], "TUNNEL_W": p["TUNNEL_W"], "TOOTH": p["TOOTH"],
              "ratchet_rib_h_pitch_steep": p["rib"],
              "TAB_CLASH": f"gated_container TAB_TOP {gc.TAB_TOP:g} mm is {gc.TAB_TOP - (H - fh.LEDGE_T):g} mm above "
                           f"the ledge of the box above in a rim-on-rim stack; tabs cut to {tab_top:g} mm here",
              "flipped_levels": flip,
              "stacking": "holder boxes rim on rim, one gated container per box, alternate levels flipped 180 deg, "
                          "catch pan under the bottom box; sample poured on the top container's high end",
              "jets": "placeholder: one per level, 40 mm above the top rim, straight down"})


if __name__ == "__main__":
    for spec in sys.argv[1:] or ["gated:2,w5p0,t1p4"]:
        d = designs.build(spec)
        print(d.name, f"{len(d.geoms)} geoms")
        print("  spawn", [round(v, 2) for v in d.spawn])
        for z in d.zones:
            print("  zone", z["name"], [round(v, 2) for v in z["box"]])
        print(json.dumps(d.info, indent=1, default=str))