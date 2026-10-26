"""Breaker layer: the top level of the stack, which teases a wet clump of insects apart before sorting
(docs/sessions/clump-breakup.md). A drop-in like sieve_insert.py: same 131.4 x 95.4 footprint, same
pull tabs, so it sits in a holder box on top of the stack.

    breaker:open=<mm>,bar=<mm>,pin_d=<mm>,pin_h=<mm>,pitch=<mm>,tip=<round|flat>
    (the same names as the optimizer's sim spec, so a sim winner prints as is)

Geometry, for the sim to mirror:
- Floor: a square grid GRID_T thick, square openings `open` wide between bars `bar` wide, so the grid
  steps g = open + bar. As many whole openings as fit inside a BORDER-wide rim are centred on the
  layer; what's left over goes to the rim, which rests on the holder's ledge. Every opening lies over
  the holder's open bottom, so all of them drain.
- Pins: round pins `pin_d` across stand on the grid nodes (where an inner bar along X crosses one
  along Y), on every k-th node in both directions, k = round(pitch / g) (at least 1), centred. The
  pins actually stand k * g apart; `pitch` is the target. They rise `pin_h` above the grid top; a round
  tip is a dome of radius pin_d / 2 inside that height (a fillet 0.05 mm short of the radius, so a
  0.1 mm flat on top). Each pin is built from the bed up, so a pin wider than the bars overhangs nothing.

Printable as asked: openings on 0.1 mm steps, pin heights on 0.2 mm layers (both rounded and reported),
pins point up, no supports. Flags: bars or pins under two 0.4 mm lines, pins taller than 8 diameters,
and pin tops above the box rim (then the breaker has to be the top level).

Run from this folder:  <venv python> breaker_layer.py ["open=8,bar=1.6,pin_d=2.5,pin_h=12,pitch=10,tip=round" ...]
"""
import json
import math
import sys
import cadquery as cq
from cadkit import OUT, export_all
import frame_holder as box
import sieve_insert as si

L, W = si.L, si.W                  # 131.4 x 95.4
GRID_T = 2.4                       # floor grid thickness (12 layers of 0.2)
BORDER = 6.0                       # rim round the grid; it rests on the holder's ledge
TAB_W, TAB_T, TAB_H = si.TAB_W, si.TAB_T, si.TAB_H
TAB_TOP = si.FRAME_T + si.TAB_H    # 21 above the layer's bottom, as on the inserts
LINES = 0.8                        # two 0.4 mm extrusion lines
DEFAULT = {"open": 8.0, "bar": 1.6, "pin_d": 2.5, "pin_h": 12.0, "pitch": 10.0, "tip": "round"}


def spec(s=""):
    """'breaker:open=8,bar=1.6,...' (or without the prefix) -> parameters, defaults filled in and rounded
    to what prints: openings and bars on 0.1 mm, pin heights on 0.2 mm layers."""
    p = dict(DEFAULT)
    for kv in filter(None, s.split(":", 1)[-1].split(",")):
        k, _, v = kv.partition("=")
        if k not in DEFAULT:
            raise ValueError(f"unknown breaker key {k!r}: use {list(DEFAULT)}")
        p[k] = v if k == "tip" else float(v)
    if p["tip"] not in ("round", "flat"):
        raise ValueError(f"tip must be round or flat, got {p['tip']!r}")
    for k in ("open", "bar", "pin_d", "pitch"):
        p[k] = round(p[k], 1)
    p["pin_h"] = round(p["pin_h"] / 0.2) * 0.2
    return p


def name(p):
    f = lambda v: f"{v:g}".replace(".", "p")
    return f"breaker_o{f(p['open'])}_b{f(p['bar'])}_d{f(p['pin_d'])}_h{f(p['pin_h'])}_p{f(p['pitch'])}_{p['tip']}"


def grid(p):
    """Opening centres along X and Y, and the inner bar centres (node lines) between them."""
    g = p["open"] + p["bar"]
    out = []
    for span in (L - 2 * BORDER, W - 2 * BORDER):
        n = int((span - p["bar"]) // g)                  # whole openings with a bar at each end
        centres = [(i - (n - 1) / 2) * g for i in range(n)]
        out.append((centres, [c + g / 2 for c in centres[:-1]]))
    return g, out


def every_kth(lines, k):
    """Every k-th node line, the leftover split between the two ends."""
    first = (len(lines) - 1) % k // 2
    return lines[first::k]


def layer(p):
    g, ((ox, bx), (oy, by)) = grid(p)
    body = cq.Workplane("XY").box(L, W, GRID_T, centered=(True, True, False))
    body = body.cut(cq.Workplane("XY").pushPoints([(x, y) for x in ox for y in oy])
                    .rect(p["open"], p["open"]).extrude(GRID_T + 1).translate((0, 0, -0.5)))
    k = max(1, round(p["pitch"] / g))
    pins = [(x, y) for x in every_kth(bx, k) for y in every_kth(by, k)]
    r, top = p["pin_d"] / 2, GRID_T + p["pin_h"]
    pin = cq.Workplane("XY").circle(r).extrude(top)
    if p["tip"] == "round":       # a fillet just short of the radius: a sphere on a cylinder leaves the mesh open
        pin = pin.faces(">Z").edges().fillet(r - 0.05)
    body = body.union(cq.Workplane("XY").pushPoints(pins).eachpoint(lambda loc: pin.val().moved(loc), combine=True))
    for sy in (1, -1):
        tab = cq.Workplane("XY").box(TAB_W, TAB_T, TAB_TOP, centered=(True, False, False))
        body = body.union(tab.translate((0, W / 2 - TAB_T if sy > 0 else -W / 2, 0)))
    label = (cq.Workplane("XY").workplane(offset=TAB_TOP + 0.01).center(0, W / 2 - TAB_T / 2)
             .text(f"B{p['open']:g}", si.LABEL_H, -(si.LABEL_D + 0.01), combine=False))
    body = body.cut(label)
    open_area = len(ox) * len(oy) * p["open"] ** 2
    pin_top_box = box.LEDGE_T + top                     # in the holder box's frame
    info = {"spec": "breaker:" + ",".join(f"{k}={p[k]:g}" if k != "tip" else f"tip={p[k]}" for k in DEFAULT),
            "grid_step_mm": round(g, 2), "openings": [len(ox), len(oy)], "open_area_mm2": round(open_area),
            "open_pct_of_box_bottom": round(100 * open_area / (box.OPEN_L * box.OPEN_W), 1),
            "pins": len(pins), "pin_every_nodes": k, "pin_pitch_mm": round(k * g, 2),
            "pin_top_in_box_mm": round(pin_top_box, 2), "outside_mm": [round(L, 2), round(W, 2), GRID_T]}
    flags = []
    if p["bar"] < LINES:
        flags.append(f"bars are {p['bar']:g} mm: under two 0.4 mm lines, fragile")
    if p["pin_d"] < LINES:
        flags.append(f"pins are {p['pin_d']:g} mm across: under two lines")
    if p["pin_h"] > 8 * p["pin_d"]:
        flags.append(f"pins are {p['pin_h'] / p['pin_d']:.1f} diameters tall: may wobble while printing or snap")
    if pin_top_box > box.H:
        flags.append(f"pin tops are {pin_top_box:g} mm up the box, above its {box.H:g} mm rim: top level only")
    info["printability_flags"] = flags
    return body, info


def half(stack):
    """Cut away y < 0 so the preview shows the inside."""
    return stack.cut(cq.Workplane("XY").box(300, 100, 400, centered=(True, False, False)).translate((0, -100, -50)))


def preview(p):
    """The layer seated in a holder box, cut in half. Preview only."""
    return half(box.frame().union(layer(p)[0].translate((0, 0, box.LEDGE_T)))), {"preview_only": True}


if __name__ == "__main__":
    specs = sys.argv[1:] or [""]
    built = []
    for s in specs:
        p = spec(s)
        n = name(p)
        part, info = layer(p)
        checks = export_all(part, n, info)
        print(n, json.dumps(checks))
        prev, prev_info = preview(p)
        export_all(prev, f"{n}_preview", prev_info)
        built.append({"name": n, "info": info,
                      "checks_ok": all(checks[c] for c in ("valid_solid", "single_solid", "watertight_mesh", "fits_bed"))})
    (OUT / "breaker_build.json").write_text(json.dumps(built, indent=1), encoding="utf-8")
