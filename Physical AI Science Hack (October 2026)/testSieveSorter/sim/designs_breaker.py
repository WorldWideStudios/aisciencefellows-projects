"""The breaker layer on top of a seesaw tower, for the sorter sim (cad/breaker_layer.py, docs/sessions/clump-breakup.md).
Units mm, tray frame as in designs_holder.py.

    breaker:open=<mm>,bar=<mm>,pin_d=<mm>,pin_h=<mm>,pitch=<mm>,tip=<round|flat>[,under=<a>+<b>...][,tower=<mm>]

The first six keys are cad/breaker_layer.py's, with its defaults and rounding (openings and bars on 0.1 mm, pin
heights on 0.2 mm layers), so a sim winner prints as is (info["breaker"]["cad_spec"]). Two keys are the sim's own:
    under   the sieve inserts below the breaker, top to bottom, joined by + (default 5mm+2mm: the demo rig)
    tower   box bottom to box bottom, mm (default 85: clear of the neighbours at +/-15 deg with the +X tab)

The tower is designs_holder.build_inserts(under, pitch=tower) with one more holder box on top. That box holds the
breaker: a GRID_T thick square grid (`open` openings between `bar` bars, centred, a rim round them on the holder's
ledge) with round pins `pin_d` across standing `pin_h` above the grid on every k-th node, k = round(pitch / step).
A round tip is a capsule (a hemisphere on a cylinder: the CAD's 0.05 mm short fillet left out), a flat one a
cylinder. Each level is its own box, so rocking.py's seesaw rocks the breaker as the top level. The zone on the
breaker is "on_breaker"; a particle stays there if it can't pass an `open` square hole (leaves, twigs).

Run from sim\\ to print a summary:  <venv python> designs_breaker.py ["breaker:open=8,pin_h=12" ...]
"""
import functools
import json
import sys

import designs  # noqa: F401  (stubs cadquery and cadkit before the CAD modules load)
import designs_holder as dh
from common import Design

BREAKER_RGBA = [0.92, 0.70, 0.30, 1.0]
PIN_RGBA = [0.85, 0.45, 0.20, 1.0]
SIM_KEYS = {"under": "5mm+2mm", "tower": 85.0}


@functools.cache
def cad():
    dh.cad()                     # puts cad/ on sys.path
    import breaker_layer
    return breaker_layer


def parse(args):
    """Spec arguments -> (CAD parameters as breaker_layer.spec() rounds them, sim options)."""
    bl = cad()
    sim = dict(SIM_KEYS)
    cad_kv = []
    for a in args:
        k, _, v = a.partition("=")
        if k in sim:
            sim[k] = v if k == "under" else float(v)
        else:
            cad_kv.append(a)
    p = bl.spec(",".join(cad_kv))
    under = [u for u in str(sim["under"]).split("+") if u]
    if not under:
        raise ValueError("breaker: under= needs at least one insert below, e.g. under=5mm+2mm")
    return p, {"under": under, "tower": float(sim["tower"])}


def cad_spec(p):
    return "breaker:" + ",".join(f"{k}={p[k]}" if k == "tip" else f"{k}={p[k]:g}" for k in cad().DEFAULT)


def breaker_geoms(p, z_seat):
    """The breaker seated on a ledge at z_seat: grid bars and rim (boxes), pins, pull tabs. Returns geoms and the layer
    facts (grid top, pin top, hole centres, pins)."""
    bl = cad()
    L, W, t = bl.L, bl.W, bl.GRID_T
    z1 = z_seat + t
    g, ((ox, bx), (oy, by)) = bl.grid(p)
    o = p["open"]
    xa, xb, ya, yb = ox[0] - o / 2, ox[-1] + o / 2, oy[0] - o / 2, oy[-1] + o / 2
    geoms = [dh.box(-L / 2, xa, -W / 2, W / 2, z_seat, z1, BREAKER_RGBA, "frame"),       # rim
             dh.box(xb, L / 2, -W / 2, W / 2, z_seat, z1, BREAKER_RGBA, "frame"),
             dh.box(xa, xb, -W / 2, ya, z_seat, z1, BREAKER_RGBA, "frame"),
             dh.box(xa, xb, yb, W / 2, z_seat, z1, BREAKER_RGBA, "frame")]
    b = p["bar"]
    geoms += [dh.box(x - b / 2, x + b / 2, ya, yb, z_seat, z1, BREAKER_RGBA, "screen") for x in bx]
    geoms += [dh.box(xa, xb, y - b / 2, y + b / 2, z_seat, z1, BREAKER_RGBA, "screen") for y in by]
    k = max(1, round(p["pitch"] / g))
    pins = [(x, y) for x in bl.every_kth(bx, k) for y in bl.every_kth(by, k)]
    r, h = p["pin_d"] / 2, p["pin_h"]
    for x, y in pins:
        if p["tip"] == "round" and h > r:
            half = (h - r) / 2                                   # cylinder part; the bottom cap sinks into the grid
            geoms.append({"type": "capsule", "size": [r, half], "pos": [x, y, z1 + half], "quat": [1.0, 0.0, 0.0, 0.0],
                          "rgba": PIN_RGBA, "role": "gate"})
        else:
            geoms.append({"type": "cylinder", "size": [r, h / 2], "pos": [x, y, z1 + h / 2], "quat": [1.0, 0.0, 0.0, 0.0],
                          "rgba": PIN_RGBA, "role": "gate"})
    for y0, y1 in ((W / 2 - bl.TAB_T, W / 2), (-W / 2, -W / 2 + bl.TAB_T)):
        geoms.append(dh.box(-bl.TAB_W / 2, bl.TAB_W / 2, y0, y1, z_seat, z_seat + bl.TAB_TOP, BREAKER_RGBA, "frame"))
    facts = {"grid_top_z_mm": round(z1, 3), "pin_top_z_mm": round(z1 + h, 3), "grid_step_mm": round(g, 3),
             "openings": [len(ox), len(oy)], "pins": len(pins), "pin_every_nodes": k, "pin_pitch_mm": round(k * g, 3),
             "hole_centres_mm": [[round(x, 3), round(y, 3)] for x in ox for y in oy],
             "open_area_mm2": round(len(ox) * len(oy) * o * o, 1)}
    return geoms, facts


def build(args):
    p, sim = parse(args)
    fh = dh.cad()[0]
    H, ix, iy = fh.H, fh.L / 2 - fh.WALL, fh.W / 2 - fh.WALL
    tower = dh.build_inserts(sim["under"] + [f"pitch={sim['tower']:g}"])
    n = len(sim["under"])
    top_box = n * sim["tower"] + H                       # top of the highest sieve box
    # drop the invisible walls and lid above the old top box (keep the notch covers, the plate under the
    # footprint and the tub floor), then add the breaker box and new walls above it
    geoms = [g for g in tower.geoms
             if not (g["role"] == "lid" and g["pos"][2] - g["size"][2] >= top_box - 1e-6)]
    z0 = (n + 1) * sim["tower"]
    z_seat = z0 + fh.LEDGE_T
    bg, facts = breaker_geoms(p, z_seat)
    geoms += dh.holder(z0, close_notches=True) + bg
    top = facts["grid_top_z_mm"]
    z_lid = facts["pin_top_z_mm"] + dh.LID_ABOVE
    geoms += dh.lid(ix, iy, z0 + H, z_lid, fh.WALL)[:-1]   # the plate under the footprint is there already

    zones = [{"name": "on_breaker", "box": [-ix, ix, -iy, iy, top, z_lid]}]
    zones += [dict(z, box=list(z["box"])) for z in tower.zones]
    zones[1]["box"][5] = z_seat
    layer = {"zone": "on_breaker", "insert": cad().name(p), "rule": "square", "opening_mm": p["open"],
             "opening": f"breaker: {p['open']:g} mm square grid, bars {p['bar']:g} mm, {facts['pins']} pins "
                        f"{p['pin_d']:g} mm x {p['pin_h']:g} mm ({p['tip']} tips) every {facts['pin_pitch_mm']:g} mm",
             "holder_z_mm": [z0, z0 + H], "surface_z_mm": [round(z_seat, 3), top], **facts}
    layers = [layer] + tower.info["layers"]
    rules = tuple((L["zone"], L["rule"], L["opening_mm"]) for L in layers)
    sx0, sx1, sy0, sy1 = tower.spawn[:4]
    spawn = [sx0, sx1, sy0, sy1, facts["pin_top_z_mm"] + dh.SPAWN_Z[0], facts["pin_top_z_mm"] + dh.SPAWN_Z[1]]
    name = ("breaker:" + ",".join(f"{k}={p[k]}" if k == "tip" else f"{k}={p[k]:g}" for k in cad().DEFAULT)
            + f",under={'+'.join(sim['under'])},tower={sim['tower']:g}")
    info = {**tower.info, "stacking": f"a breaker box on top of {tower.name}: " + tower.info["stacking"],
            "layers": layers, "top_surface_z_mm": top, "lid_z_mm": z_lid, "geom_count": dh.geom_count(geoms),
            "breaker": {"params": p, "cad_spec": cad_spec(p), "cad_file": "cad/breaker_layer.py", **{k: v for k, v in facts.items()
                                                                                                  if k != "hole_centres_mm"}}}
    return Design(name=name, geoms=geoms, zones=zones, spawn=spawn,
                  ideal_zone=functools.partial(dh.ideal_zone, layers=rules, last="catch"),
                  jets_default=dh.jets(facts["pin_top_z_mm"], ix), info=info)


if __name__ == "__main__":
    for spec in sys.argv[1:] or ["breaker:"]:
        d = build([a for a in spec.partition(":")[2].split(",") if a])
        print(d.name, json.dumps(d.info["geom_count"]))
        print("  breaker", json.dumps(d.info["breaker"]))
        print("  spawn", [round(v, 2) for v in d.spawn])
        for z in d.zones:
            print("  zone", z["name"], [round(v, 2) for v in z["box"]])
        for L in d.info["layers"]:
            print("  layer", L["zone"], L["holder_z_mm"], L["surface_z_mm"])
