"""Sorter designs for the sim, in the tray frame (see common.Design). Units mm.

    pool:<gate1>,<gate2>   the pool sorter with two gate strips from cad/sieve_system.py STRIPS,
                           e.g. pool:w5p0,t1p4 (the pool_gate_ prefix is optional)
    inserts:<a>,<b>,...    BioKEA's holder box with sieve inserts (designs_holder.py)
    plinko                 plinko layers in the holder box (designs_holder.py)
    gated:<slope>,<strips> the gated container tower, one strip per level (designs_gated.py),
                           e.g. gated:2,w5p0,t1p4

Geometry is computed from the CAD parameters, so the sim follows the CAD when it changes.
The pool's rounded corners and the gate grooves a strip fills are left out; the empty cover
grooves, where a grain can park, are kept.

Run from sim\\ to print a summary:  <venv python> designs.py pool:w5p0,t1p4
"""
import json
import sys
import types
from pathlib import Path

import numpy as np


class ParamsOnly(types.ModuleType):
    """Stands in for cadquery and cadkit while the CAD modules load. The sim reads their parameters
    and never builds a solid, and loading the real kernel costs seconds per worker process."""
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return None


for _name in ("cadquery", "cadkit"):
    sys.modules.setdefault(_name, ParamsOnly(_name))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cad"))
import sieve_system as cad  # noqa: E402
from common import Design, ellipse_fits  # noqa: E402

LID_H = 60.0                                   # invisible walls and lid above the wall tops
FLOOR_RGBA = [0.72, 0.78, 0.86, 1.0]
WALL_RGBA = [0.60, 0.68, 0.78, 0.25]
GATE_RGBA = [0.20, 0.35, 0.75, 1.0]
LID_RGBA = [0.0, 0.0, 0.0, 0.0]
JET_PLACEHOLDER = {"flow_ml_s": 5.0, "nozzle_d_mm": 1.0, "half_angle_deg": 20.0, "range_mm": 150.0}


def box(x0, x1, y0, y1, z0, z1, rgba, role):
    (x0, x1), (y0, y1), (z0, z1) = sorted((x0, x1)), sorted((y0, y1)), sorted((z0, z1))
    return {"type": "box", "size": [(x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2],
            "pos": [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], "quat": [1.0, 0.0, 0.0, 0.0],
            "rgba": rgba, "role": role}


def fits(dims, gap, open_h):
    """A particle passes a gap x open_h opening if its cross-section fits at some tilt."""
    return ellipse_fits(dims["width"], dims["thickness"], gap, open_h)


def strip(name, x0, floor):
    """Geoms of a strip standing on `floor`, downstream face at x0; and its opening (gap, height)."""
    kind, size = cad.STRIPS[name]
    top, x1, hy = floor + cad.strip_size(kind)[1], x0 + cad.STRIP_T, cad.IN_W / 2
    if kind == "dam":
        return [box(x0, x1, -hy, hy, floor, top, GATE_RGBA, "gate")], None
    gap, open_h = (size, cad.OPEN_H) if kind == "w" else (cad.TUNNEL_W, size)
    n = int((cad.IN_W - cad.TOOTH) / (gap + cad.TOOTH))
    span = n * gap + (n - 1) * cad.TOOTH
    geoms = [box(x0, x1, -hy, -span / 2, floor, top, GATE_RGBA, "gate"),
             box(x0, x1, span / 2, hy, floor, top, GATE_RGBA, "gate"),
             box(x0, x1, -span / 2, span / 2, floor + open_h, top, GATE_RGBA, "gate")]
    for i in range(n - 1):
        y = -span / 2 + (i + 1) * gap + i * cad.TOOTH
        geoms.append(box(x0, x1, y, y + cad.TOOTH, floor, floor + open_h, GATE_RGBA, "gate"))
    return geoms, (gap, open_h)


def pool(args):
    names = [a if a.startswith("pool_gate_") else f"pool_gate_{a}" for a in args] or ["pool_gate_w5p0", "pool_gate_t1p4"]
    if len(names) != len(cad.POOL_ZONES):
        raise ValueError(f"pool takes {len(cad.POOL_ZONES)} gates, got {names}")
    edges, floors = cad.pool_slots(cad.POOL_ZONES, cad.IN_L)
    L, W, H, hx, hy = cad.L, cad.W, cad.H, cad.IN_L / 2, cad.IN_W / 2
    groove_w = cad.STRIP_T + cad.SLOT_FIT

    geoms = [box(-L / 2, L / 2, -W / 2, W / 2, 0, cad.FLOOR_T, FLOOR_RGBA, "floor")]
    for k, e in enumerate(edges):   # terrace upstream of each drop edge
        geoms.append(box(e, hx if k == 0 else edges[k - 1], -hy, hy, cad.FLOOR_T, floors[k], FLOOR_RGBA, "floor"))
    geoms.append(box(hx, L / 2, -W / 2, W / 2, 0, H, WALL_RGBA, "wall"))
    covers = [(e + groove_w + cad.LAND, e + 2 * groove_w + cad.LAND, floors[k]) for k, e in enumerate(edges)]
    for s in (-1, 1):   # side walls; the empty cover grooves are notches GROOVE_D deep
        geoms.append(box(-L / 2, L / 2, s * (hy + cad.GROOVE_D), s * W / 2, 0, H, WALL_RGBA, "wall"))
        x = -L / 2
        for c0, c1, z in sorted(covers):
            geoms.append(box(x, c0, s * hy, s * (hy + cad.GROOVE_D), 0, H, WALL_RGBA, "wall"))
            geoms.append(box(c0, c1, s * hy, s * (hy + cad.GROOVE_D), 0, z, WALL_RGBA, "wall"))
            x = c1
        geoms.append(box(x, L / 2, s * hy, s * (hy + cad.GROOVE_D), 0, H, WALL_RGBA, "wall"))

    gate_x = [e + cad.SLOT_FIT / 2 for e in edges]
    openings = []
    for name, x0, z in zip(names, gate_x, floors):
        g, opening = strip(name, x0, z)
        geoms += g
        openings.append(opening)
    dam_x0 = -hx + cad.DAM_INSET + cad.SLOT_FIT / 2
    geoms += strip("pool_dam", dam_x0, cad.FLOOR_T)[0]

    top = H + LID_H
    geoms += [box(hx, L / 2, -W / 2, W / 2, H, top, LID_RGBA, "lid"),
              box(-L / 2, -hx, -W / 2, W / 2, cad.FLOOR_T, top, LID_RGBA, "lid"),
              box(-L / 2, L / 2, hy, W / 2, H, top, LID_RGBA, "lid"),
              box(-L / 2, L / 2, -W / 2, -hy, H, top, LID_RGBA, "lid"),
              box(-L / 2, L / 2, -W / 2, W / 2, top, top + 2, LID_RGBA, "lid")]

    zone_names = ["load", "middle", "end"] if len(names) == 2 else [f"zone{k}" for k in range(len(names) + 1)]
    highs = [hx, *gate_x]                                           # zone k runs from gate k's upstream face
    lows = [*[x + cad.STRIP_T for x in gate_x], dam_x0 + cad.STRIP_T]  # down to the next gate's downstream face
    zones = [{"name": n, "box": [lo, hi, -hy, hy, 0.0, top]} for n, lo, hi in zip(zone_names, lows, highs)]

    def ideal_zone(dims):
        for k, (gap, open_h) in enumerate(openings):
            if not fits(dims, gap, open_h):
                return zone_names[k]
        return zone_names[-1]

    jets = [{"pos_lab": [x + cad.STRIP_T + 8.0, 0.0, H + 40.0], "dir": list(np.array([-0.4, 0.0, -1.0]) / np.hypot(0.4, 1.0)),
             **JET_PLACEHOLDER} for x in gate_x]
    return Design(
        name="pool:" + ",".join(n.removeprefix("pool_gate_") for n in names),
        geoms=geoms, zones=zones,
        spawn=[lows[0] + 2.0, hx - 2.0, -hy + 2.0, hy - 2.0, floors[0] + 1.0, top - 5.0],
        ideal_zone=ideal_zone, stroke_axis=[-1.0, 0.0, 0.0], jets_default=jets,
        info={"gates": names, "openings_gap_x_height_mm": openings, "zone_floors_mm": floors,
              "drop_edges_x_mm": [round(e, 2) for e in edges], "stroke_axis": "-X is the flow direction",
              "jets": "placeholder: one per gate, 40 mm above the wall top, until the bench measures the nozzles"})


def build(spec):
    kind, _, arg = spec.partition(":")
    args = [a.strip() for a in arg.split(",") if a.strip()]
    if kind == "pool":
        return pool(args)
    if kind in ("inserts", "plinko"):
        import designs_holder
        return getattr(designs_holder, f"build_{kind}")(args)
    if kind == "gated":
        import designs_gated
        return designs_gated.build(args)
    if kind == "breaker":
        import designs_breaker
        return designs_breaker.build(args)
    raise ValueError(f"unknown design {spec!r}: use pool:<g1>,<g2>, inserts:<a>,<b>, plinko, gated:<slope>,<strips> "
                     f"or breaker:<key>=<value>,...")


if __name__ == "__main__":
    d = build(sys.argv[1] if len(sys.argv) > 1 else "pool:w5p0,t1p4")
    print(d.name, f"{len(d.geoms)} geoms")
    print(json.dumps({"zones": d.zones, "spawn": d.spawn, "info": d.info}, indent=1, default=str))
