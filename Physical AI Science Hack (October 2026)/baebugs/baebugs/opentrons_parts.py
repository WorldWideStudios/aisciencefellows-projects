"""Opentrons-deck versions of the BioKEA modules: printed parts on the SBS/ANSI footprint
(127.76 x 85.48 mm) plus custom labware definitions, so the Flex gripper can move them and the
Heater-Shaker can agitate or incubate them.

  ot_sieve_adapter   SBS plate with a socket for the 50 mm mini sieve stack (vortex kit rings);
                     sits on the Heater-Shaker universal flat adapter -> BugSorter/BugDisperser on deck
  ot_mini_trommel    SBS base with 4 collection wells, bearing towers, N20 gear-motor pocket and a
                     36 mm drum (1.5 / 3 / 5 mm zones) -> BugSorter as a deck module (motor driven
                     by an external controller, e.g. ESP32; the protocol pauses for it)
  ot_handoff_plate   SBS carrier with a top grip handle (external arm), a 20 mm flat suction pad
                     (BugPicker vacuum), an AprilTag pocket and a ring socket -> moves between
                     the deck, an external arm and a suction picker
Materials: PLA/PETG for fit checks; PA12 powder (Fuse 1+) or tough resin for wet use (resin parts
need full post-cure and a solvent check before contact with lysis buffer).
Geometry concepts, not tested on a Flex: verify gripper grip height, skirt fit in the deck slot
and Heater-Shaker latch clearance before running hardware.
"""
from __future__ import annotations

import json
from pathlib import Path

from manifold3d import Manifold

from .print_parts import P as PP
from .print_parts import box, cyl, radial_holes, to_trimesh, tube, union

SBS = (127.76, 85.48)
O = {"skirt_engage": 8.0, "flat_adapter_h": 12.0, "skirt_h": 8.0, "plate_t": 4.0, "drum_od": 36.0, "drum_len": 90.0, "zones": [1.5, 3.0, 5.0], "axle_d": 3.0,
     "n20": (12.2, 10.2, 24.0), "axis_z": 37.0, "well_depth": 14.0, "tag": 14.0, "pad_d": 20.0, "grip_h": 8.0}


def sbs_plate(h, wall=1.6, skirt=None):
    """Outer SBS footprint with a hollow skirt (prints flat, saves material). The skirt clears the
    Heater-Shaker universal flat adapter (111 x 75 x 12 mm): the part rests on it with the skirt
    engaged `skirt` mm, so its stacking offset on that adapter is 12 - skirt."""
    x, y = SBS
    skirt = O["skirt_engage"] if skirt is None else skirt
    hollow = box(x - 2 * wall, y - 2 * wall, skirt + 0.01).translate([wall, wall, -0.01])
    return box(x, y, h) - hollow


def sieve_adapter():
    x, y = SBS; h = O["skirt_h"] + O["plate_t"] + 6
    base = sbs_plate(h)
    socket = cyl(6.2, PP["mini_od"] / 2 + PP["fit"], seg=96).translate([x / 2, y / 2, h - 6])
    drains = [cyl(h + 2, 1.5, seg=16).translate([x / 2 + dx, y / 2 + dy, -1]) for dx in (-15, 0, 15) for dy in (-15, 0, 15)]
    return base - union([socket] + drains)


def mini_trommel_base():
    x, y = SBS; wd = O["well_depth"]; h = wd + 2
    base = box(x, y, h)
    L, z0 = O["drum_len"], 18.0
    wells = []
    edges = [z0, z0 + L / 3, z0 + 2 * L / 3, z0 + L, x - 4]
    for i in range(4):                      # 3 zone wells + oversize well at the open end
        wells.append(box(edges[i + 1] - edges[i] - 2, y - 30, wd).translate([edges[i] + 1, 15, h - wd]))
    towers = []
    for xt in (z0 - 8, z0 + L + 2):
        tw = box(6, 16, O["axis_z"] + 6).translate([xt, y / 2 - 8, 0])
        bore = cyl(10, O["axle_d"] / 2 + 0.25, seg=24).rotate([0, 90, 0]).translate([xt - 2, y / 2, O["axis_z"]])
        towers.append(tw - bore)
    n20 = O["n20"]
    motor_block = box(n20[2] + 4, n20[0] + 6, O["axis_z"] + n20[1] / 2 + 3).translate([2, y / 2 - (n20[0] + 6) / 2, 0])
    pocket = box(n20[2] + 0.4, n20[0], n20[1]).translate([3, y / 2 - n20[0] / 2, O["axis_z"] - n20[1] / 2])
    shaft = cyl(10, 2.0, seg=24).rotate([0, 90, 0]).translate([n20[2], y / 2, O["axis_z"]])
    return union([base, motor_block - pocket - shaft] + towers) - union(wells)


def mini_trommel_drum():
    od, w, L = O["drum_od"], 1.6, O["drum_len"]
    body = tube(L, od / 2, od / 2 - w, seg=72)
    holes = []
    for i, d in enumerate(O["zones"]):
        holes += radial_holes(od, w, i * L / 3 + 2, (i + 1) * L / 3 - 2, d, 1.0, seg=12)
    drum = body - union(holes)
    hub_in = union([cyl(3, od / 2, seg=72), tube(8, 3.5, O["axle_d"] / 2 + 0.15).translate([0, 0, -8])])
    feed = [cyl(5, 4.5, seg=24).translate([dx, dy, -1]) for dx, dy in ((9, 0), (-4.5, 7.8), (-4.5, -7.8))]
    hub_in = hub_in - union(feed)
    spokes_out = [box(od / 2 - 1, 2.4, 2).translate([0, -1.2, 0]).rotate([0, 0, a]) for a in (90, 210, 330)]
    hub_out = union([tube(2, od / 2, od / 2 - 2.5, seg=72), tube(8, 3.5, O["axle_d"] / 2 + 0.15)] + spokes_out).translate([0, 0, L - 2])
    return union([drum, hub_in, hub_out])


def handoff_plate():
    x, y = SBS; h = O["skirt_h"] + O["plate_t"]
    base = sbs_plate(h)
    g = PP["jaw_gap"]
    handle = box(g, 16, 22).translate([x / 2 - g / 2, y - 22, h])
    vee = [Manifold.cube([3, 3, 30], True).rotate([0, 0, 45]).translate([x / 2 + sx * g / 2, y - 14, h + 11]) for sx in (-1, 1)]
    pad = cyl(1.2, O["pad_d"] / 2, seg=48).translate([22, y / 2, h])
    tag = box(O["tag"] + 0.4, O["tag"] + 0.4, 0.8).translate([x - 24, 8, h - 0.79])
    socket = cyl(3.2, PP["mini_od"] / 2 + PP["fit"], seg=96).translate([x / 2, y / 2 - 6, h - 3])   # 3 mm recess, 1 mm floor
    return union([base, handle, pad]) - union(vee + [tag, socket])


def parts():
    return {"ot_sieve_adapter": sieve_adapter(), "ot_mini_trommel_base": mini_trommel_base(),
            "ot_mini_trommel_drum": mini_trommel_drum(), "ot_handoff_plate": handoff_plate()}


# ------------------------------------------------------------------ Opentrons labware definitions
def _labware(load_name, display, z, wells, grip_h, category="other"):
    x, y = SBS
    return {
        "ordering": [[k] for k in wells], "brand": {"brand": "baebugs", "brandId": [load_name]},
        "metadata": {"displayName": display, "displayCategory": category, "displayVolumeUnits": "mL", "tags": ["baebugs", "BioKEA"]},
        "dimensions": {"xDimension": x, "yDimension": y, "zDimension": z},
        "wells": wells, "groups": [{"metadata": {"wellBottomShape": "flat"}, "wells": list(wells)}],
        "parameters": {"format": "irregular", "quirks": [], "isTiprack": False, "isMagneticModuleCompatible": False,
                       "loadName": load_name},
        "namespace": "custom_beta", "version": 1, "schemaVersion": 2,
        "cornerOffsetFromSlot": {"x": 0, "y": 0, "z": 0},
        "gripperOffsets": {}, "gripForce": 15, "gripHeightFromLabwareBottom": grip_h,
        "stackingOffsetWithLabware": {"opentrons_universal_flat_adapter":
                                      {"x": 0, "y": 0, "z": O["flat_adapter_h"] - O["skirt_engage"]}},
    }


def labware_defs():
    x, y = SBS
    sa_z = O["skirt_h"] + O["plate_t"] + 6
    ring_depth = PP["mini_h"] + 6
    sieve = _labware("baebugs_sieve_adapter_50mm", "baebugs mini sieve stack adapter (50 mm)", sa_z + PP["mini_h"] * 3,
                     {"A1": {"depth": ring_depth, "totalLiquidVolume": 25000, "shape": "circular", "diameter": PP["mini_od"] - 4,
                             "x": x / 2, "y": y / 2, "z": sa_z + PP["mini_h"] * 3 - ring_depth}}, grip_h=O["grip_h"])
    L, z0, _h = O["drum_len"], 18.0, O["well_depth"] + 2
    edges = [z0, z0 + L / 3, z0 + 2 * L / 3, z0 + L, x - 4]
    tw = {}
    for i, name in enumerate(["A1", "A2", "A3", "A4"]):
        wx = edges[i + 1] - edges[i] - 2
        tw[name] = {"depth": O["well_depth"], "totalLiquidVolume": int(wx * (y - 30) * O["well_depth"]), "shape": "rectangular",
                    "xDimension": round(wx, 2), "yDimension": round(y - 30, 2), "x": round(edges[i] + 1 + wx / 2, 2), "y": y / 2, "z": 2}
    trommel = _labware("baebugs_mini_trommel_4bin", "baebugs mini trommel (1.5/3/5 mm + oversize bins)",
                       O["axis_z"] + O["drum_od"] / 2 + 2, tw, grip_h=O["grip_h"])
    hz = O["skirt_h"] + O["plate_t"]
    handoff = _labware("baebugs_handoff_plate", "baebugs hand-off carrier (arm / suction / gripper)", hz + 22,
                       {"A1": {"depth": 3, "totalLiquidVolume": 5000, "shape": "circular", "diameter": PP["mini_od"],
                               "x": x / 2, "y": y / 2 - 6, "z": hz - 3}}, grip_h=O["grip_h"] / 2 + 2)
    return {d["parameters"]["loadName"]: d for d in (sieve, trommel, handoff)}


def export(out_dir="opentrons"):
    import hashlib
    out = Path(out_dir); (out / "stl").mkdir(parents=True, exist_ok=True); (out / "labware").mkdir(exist_ok=True)
    rows = []
    for name, m in parts().items():
        t = to_trimesh(m); f = out / "stl" / f"{name}.stl"; t.export(f); bb = t.bounds
        rows.append({"part": name, "stl": f"stl/{name}.stl", "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                     "watertight": bool(t.is_watertight), "bbox_mm": [round(float(v), 2) for v in bb[1] - bb[0]],
                     "volume_cm3": round(t.volume / 1000, 2)})
        print(name, rows[-1]["bbox_mm"], rows[-1]["volume_cm3"], "cm3", "watertight" if t.is_watertight else "NOT WATERTIGHT")
    for ln, d in labware_defs().items():
        (out / "labware" / f"{ln}.json").write_text(json.dumps(d, indent=1))
    (out / "parts.json").write_text(json.dumps({"params": O, "sbs_mm": SBS, "parts": rows}, indent=1))
    return rows


if __name__ == "__main__":
    export()
