"""Gated container: drop-in replacement for the mesh sieve inserts in the BugSorter tower,
same footprint as the current inserts (WORKING_DIMENSIONS.md), shaken longways (X).

    top view, one container (gate end at +X)

    +--------------------------------------------------+---+----+
    |                                                  | G | dr |
    |   solid floor, sloping 2 deg down toward +X      | A | op |   <- box's open bottom
    |   big items stay here                            | T |    |      under the drop slot
    |                                                  | E | sl |
    |                       [tabs]                     |   | ot |
    +--------------------------------------------------+---+----+

- Shaking walks grains (and the spray water) down the floor to the gate strip. Anything that
  fits through the gate drops through the drop slot to the next level; it can't come back.
- Whatever is too big stays in the container. Lift it out by the tabs and put it in the pool.
- Gates are swappable strips that slide into rails. They print flat, so the gap width or
  tunnel height is in the printer's accurate XY plane. Width gates (w) cut by the narrower
  side of a flat-lying grain; tunnel gates (t) cut by its thickness, which is what splits
  long-grain rice (~1.7 mm) from quinoa (~1.0 mm).
- In the tower, flip the container 180 degrees on every other level, so what drops from
  the level above lands on the solid end of the next container, not straight into its slot.

Prints flat, right side up, no supports.

Run from this folder:  <venv python> gated_container.py
"""
import json
import math
import sys
import cadquery as cq
from cadkit import export_all
import frame_holder as box
import sieve_insert as ins

L, W = ins.L, ins.W                # 131.4 x 95.4: same footprint as the current inserts
LW = 2.0                           # container wall
IN_L, IN_W = L - 2 * LW, W - 2 * LW
WALL_H = 16.0
FLOOR_T = 2.0
FLOOR_SLOPE_DEG = 2.0              # floor falls toward the gate end
OPEN_X = box.OPEN_L / 2            # 61: edge of the box's open bottom
OPEN_Y = box.OPEN_W / 2 - 1.0      # 40: keep the drop slot 1 mm inside the open bottom
STRIP_T = 2.0
SLOT_FIT = 0.3                     # rail gap minus strip thickness
END_FIT = 0.4                      # inside width minus strip length
GATE_X = OPEN_X - 8.0              # strip centre; the drop slot runs from its face to OPEN_X
WEDGE_DEG = 30.0                   # mid-slot containers: the fill beyond a short slot slopes back into it
RAIL_P, RAIL_T = 1.5, 2.0          # rail: how far it sticks out from the wall, its thickness
TAB_W, TAB_T = ins.TAB_W, ins.TAB_T                  # pull tabs, centred on the long walls
TAB_TOP = box.H - box.LEDGE_T - 1.0                 # 21: 1 mm under the rim, like the inserts' tabs. Higher
                                                    # tabs hit the ledge of the box above in the tower; the
                                                    # box's finger notches sit over them for gripping

# gate strips: (kind, size). w = width gaps GATE_H tall; t = tunnels TUNNEL_W wide, size tall
GATE_H, TUNNEL_W, TOOTH = 8.0, 8.0, 2.0
STRIP_H = WALL_H - FLOOR_T + 4.0   # stands 4 mm above the walls to pull out
STRIPS = {
    "gate_w5p0": ("w", 5.0), "gate_w3p0": ("w", 3.0), "gate_w2p0": ("w", 2.0),
    "gate_t1p2": ("t", 1.2), "gate_t1p4": ("t", 1.4), "gate_t1p6": ("t", 1.6),
}


def container(gate_x=None, slot=None):
    """gate_x: strip centre (default GATE_X). slot: drop slot length from the strip's downstream face (default:
    out to OPEN_X, then a 45 deg ramp to the end wall). A shorter slot makes the mid-slot container (optimizer
    proposal, sim/designs_gated.py gx= / slot=): a WEDGE_DEG wedge fills the rest of the container, sloping back
    into the slot from a 0.4 mm lip and capped 2 mm under the wall top."""
    gate_x = GATE_X if gate_x is None else gate_x
    x_lo, x_strip = -IN_L / 2 - 0.5, gate_x + STRIP_T / 2
    x_se = OPEN_X if slot is None else x_strip + slot
    if x_se > OPEN_X + 1e-6:
        raise ValueError(f"gate at x {gate_x:g} with slot {slot:g}: the slot must end over the box's open bottom")
    if abs(gate_x) - (STRIP_T / 2 + SLOT_FIT / 2 + RAIL_T) < TAB_W / 2:
        raise ValueError(f"gate at x {gate_x:g}: the strip rails would hit the pull tabs")
    rise = (gate_x - STRIP_T / 2 - x_lo) * math.tan(math.radians(FLOOR_SLOPE_DEG))
    floor = (cq.Workplane("XZ").polyline([(x_lo, 0), (x_strip, 0), (x_strip, FLOOR_T),
                                          (gate_x - STRIP_T / 2, FLOOR_T), (x_lo, FLOOR_T + rise)])
             .close().extrude(IN_W / 2 + 0.5, both=True))
    walls = (cq.Workplane("XY").box(L, W, WALL_H, centered=(True, True, False)).edges("|Z").fillet(1.5)
             .cut(cq.Workplane("XY").box(IN_L, IN_W, WALL_H, centered=(True, True, False))))
    body = walls.union(floor)
    # drop zone beside the slot (over the box ledge) and the ramp or wedge at the end all shed into the slot
    for sy in (1, -1):
        body = body.union(cq.Workplane("XY").box(x_se + 0.5 - x_strip, IN_W / 2 + 0.5 - OPEN_Y, FLOOR_T, centered=False)
                          .translate((x_strip, OPEN_Y if sy > 0 else -IN_W / 2 - 0.5, 0)))
    x_end, lip = IN_L / 2 + 0.5, 0.4               # a 0.4 mm lip instead of a knife edge
    if x_se >= OPEN_X - 1e-6:                      # 45 deg ramp
        end = [(OPEN_X, 0), (x_end, 0), (x_end, x_end - OPEN_X + lip), (OPEN_X, lip)]
        end_info = "45 deg ramp"
    else:                                          # mid-slot wedge
        top = min(lip + (x_end - x_se) * math.tan(math.radians(WEDGE_DEG)), WALL_H - 2.0)
        x_knee = x_se + (top - lip) / math.tan(math.radians(WEDGE_DEG))
        end = [(x_se, 0), (x_end, 0), (x_end, top), (x_knee, top), (x_se, lip)]
        end_info = f"{WEDGE_DEG:g} deg wedge from x {x_se:.1f}, {top:.1f} mm tall"
    body = body.union(cq.Workplane("XZ").polyline(end).close().extrude(IN_W / 2 + 0.5, both=True))
    # rails that hold the gate strip
    for side in (-1, 1):
        rx = gate_x + side * (STRIP_T / 2 + SLOT_FIT / 2 + RAIL_T / 2)
        for sy in (1, -1):
            body = body.union(cq.Workplane("XY").box(RAIL_T, RAIL_P + 0.5, WALL_H, centered=(True, False, False))
                              .translate((rx, IN_W / 2 - RAIL_P if sy > 0 else -IN_W / 2 - 0.5, 0)))
    for sy in (1, -1):
        body = body.union(cq.Workplane("XY").box(TAB_W, TAB_T, TAB_TOP, centered=(True, False, False))
                          .translate((0, W / 2 - TAB_T if sy > 0 else -W / 2, 0)))
    return body, {"outside_mm": [round(L, 2), round(W, 2), WALL_H], "floor_rise_mm": round(rise, 2),
                  "drop_slot_mm": [round(x_se - x_strip, 2), 2 * OPEN_Y], "gate_x_mm": gate_x, "beyond_slot": end_info,
                  "gate_end": "+X; flip 180 deg on alternate tower levels"}


def strip(name):
    """Printed flat: X = along the gate line, Y = height (gates open from the y = 0 edge)."""
    kind, size = STRIPS[name]
    length = IN_W - END_FIT
    body = cq.Workplane("XY").box(length, STRIP_H, STRIP_T, centered=(True, False, False))
    opening_w, opening_h = (size, GATE_H) if kind == "w" else (TUNNEL_W, size)
    pitch = opening_w + TOOTH
    n = int((2 * OPEN_Y - TOOTH) // pitch)     # whole openings that fit inside the drop slot's span
    x0 = -(n - 1) * pitch / 2
    cutter = (cq.Workplane("XY").pushPoints([(x0 + i * pitch, opening_h / 2 - 0.01) for i in range(n)])
              .rect(opening_w, opening_h + 0.02).extrude(STRIP_T + 1).translate((0, 0, -0.5)))
    body = body.cut(cutter)
    label = (cq.Workplane("XY").workplane(offset=STRIP_T + 0.01).center(0, STRIP_H - 4.0)
             .text(f"{kind.upper()}{size:g}", 4.0, -0.61, combine=False))
    return body.cut(label), {"kind": "width gaps" if kind == "w" else "tunnels", "size_mm": size,
                             "openings": n, "opening_mm": [opening_w, opening_h],
                             "strip_mm": [round(length, 2), STRIP_H, STRIP_T]}


def seated(gate, gate_x=None, slot=None):
    """The container with the strip standing in its rails, in the container's frame."""
    gate_x = GATE_X if gate_x is None else gate_x
    s = (strip(gate)[0].rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 0, 1), 90)
         .translate((gate_x - STRIP_T / 2, 0, FLOOR_T)))
    return container(gate_x, slot)[0].union(s)


def half(stack):
    """Cut away y < 0 so the preview shows the inside."""
    return stack.cut(cq.Workplane("XY").box(300, 100, 400, centered=(True, False, False)).translate((0, -100, -50)))


def preview(gate="gate_w5p0"):
    """out/gated_preview.png: holder box + container + one seated strip, cut in half. Preview only."""
    stack = box.frame().union(seated(gate).translate((0, 0, box.LEDGE_T)))
    return half(stack), {"preview_only": True, "gate": gate}


def tower(gates=("gate_w5p0", "gate_t1p4"), gate_xs=None, slots=None, flip=True):
    """out/gated_tower.png: the tower cut in half, one holder box per gate (top first) stacked rim on rim, the
    container flipped 180 deg on every other level (unless flip is False), over a catch pan (a holder with its
    open centre filled). gate_xs and slots: per level, as container() takes them. Preview only."""
    pan = box.frame().union(cq.Workplane("XY").box(box.OPEN_L + 1, box.OPEN_W + 1, box.LEDGE_T,
                                                   centered=(True, True, False)))
    stack = pan
    for i, gate in enumerate(gates):
        z = (len(gates) - i) * box.H
        level = seated(gate, gate_xs[i] if gate_xs else None, slots[i] if slots else None).translate((0, 0, box.LEDGE_T))
        if flip and i % 2:
            level = level.rotate((0, 0, 0), (0, 0, 1), 180)
        stack = stack.union(box.frame().translate((0, 0, z))).union(level.translate((0, 0, z)))
    return half(stack), {"preview_only": True, "levels_top_first": list(gates),
                         "stacking": "holder boxes rim on rim, " + ("containers flipped on alternate levels"
                                                                    if flip else "containers not flipped")
                                     + ", catch pan under"}


PARTS = {"gated_container": container, **{n: (lambda n=n: strip(n)) for n in STRIPS}, "gated_preview": preview,
         "gated_tower": tower}


if __name__ == "__main__":
    for n in sys.argv[1:] or list(PARTS):
        part, info = PARTS[n]()
        print(n, json.dumps(export_all(part, n, info)))
