#!/usr/bin/env python3
"""Build site/lab/parts.json (+ copy STLs into site/lab/stl/) from the repo's printable-part manifests.

Run from anywhere:  python3 site/lab/build_parts.py
Positions in the layout are ILLUSTRATIVE (mm, z up, part centred in x/y, sitting on z=0).
"""
import json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from baebugs.labbox import MODULES  # noqa: E402

OUT = Path(__file__).resolve().parent
SOURCES = {"print/parts": "bench", "opentrons": "flex"}
MISC = "bench_misc"  # parts that no labbox module lists

G = 130
BENCH = {
    # trommel assembly, exploded along x
    "trommel_stand_inlet": (-1.5 * G - 70, 0, 0), "trommel_cap_inlet": (-1.5 * G, 0, 0),
    "trommel_zone_2mm": (-0.5 * G, 0, 0), "trommel_zone_4mm": (0.5 * G, 0, 0), "trommel_zone_7mm": (1.5 * G, 0, 0),
    "trommel_cap_outlet": (2.5 * G, 0, 0), "trommel_stand_outlet": (2.5 * G + 90, 0, 0),
    "trommel_crank_hand": (-1.5 * G - 70, 90, 0), "trommel_crank_arm": (2.5 * G + 90, 90, 0),
    # bins below
    "trommel_bin": (-0.5 * G, -150, 0), "trommel_bin_oversize": (0.5 * G, -150, 0),
    # vortex kit
    "vortex_puck_76": (-1.5 * G, -300, 0), "vortex_mini_sieve_1.5mm": (-0.5 * G, -300, 0),
    "vortex_mini_sieve_3mm": (0.5 * G, -300, 0), "vortex_mini_sieve_5mm": (1.5 * G, -300, 0),
    "vortex_mini_pan": (2.5 * G, -300, 0), "vortex_mini_lid": (3.5 * G, -300, 0),
    # centrifuge strainers + arm grip handle
    "centrifuge_tube_strainer_1.5mm": (-0.5 * G, -430, 0), "centrifuge_tube_strainer_3mm": (0.5 * G, -430, 0),
    "arm_grip_handle": (1.5 * G, -430, 0),
    # hand-off carrier (shared bench/flex module)
    "ot_handoff_plate": (3.2 * G, -150, 0),
}
# Flex deck grid, ~150 x 105 mm pitch; slots used by opentrons/protocols/baebugs_flex_line.py
PX, PY = 150.0, 105.0
COLS = {"1": 0, "2": 1, "3": 2}
ROWS = {"D": 3, "C": 2, "B": 1, "A": 0}
SLOTS = {r + c: {"x": COLS[c] * PX, "y": ROWS[r] * PY} for r in "DCBA" for c in "123"}
FLEX_SLOT = {"ot_mini_trommel_base": "D2", "ot_mini_trommel_drum": "D2", "ot_sieve_adapter": "C2", "ot_handoff_plate": "B2"}


def main():
    (OUT / "stl").mkdir(exist_ok=True)
    owners = {}
    for mname, m in MODULES.items():
        for p in m["part_names"]:
            owners.setdefault(p, []).append(mname)
    parts = []
    for src, plat in SOURCES.items():
        man = json.loads((ROOT / src / "parts.json").read_text())
        for p in man["parts"]:
            n = p["part"]
            mods = owners.get(n) or [MISC]
            mm = [MODULES[x] for x in mods if x in MODULES]
            shutil.copyfile(ROOT / src / p["stl"], OUT / "stl" / f"{n}.stl")
            e = {"name": n, "modules": mods, "platform": plat, "stl": f"lab/stl/{n}.stl", "bbox_mm": p["bbox_mm"],
                 "sha256": p["sha256"], "status": mm[0]["status"] if mm else "CONCEPT",
                 "materials": sorted({t for m in mm for t in m["materials"]}),
                 "stages": sorted({s for m in mm for s in m["stages"]}),
                 "triangles": p.get("triangles"), "watertight": p.get("watertight")}
            if plat == "bench":
                e["pos"] = list(BENCH[n])
            else:
                s = SLOTS[FLEX_SLOT[n]]
                e["pos"] = [s["x"], s["y"], 45.1 if n == "ot_mini_trommel_drum" else 0]  # drum rests on the base
                e["slot"] = FLEX_SLOT[n]
            parts.append(e)
    # the hand-off carrier serves both platforms: add a bench-line view of the same part
    for p in list(parts):
        if p["name"] == "ot_handoff_plate":
            q = dict(p, platform="bench", pos=list(BENCH["ot_handoff_plate"]), view_copy=True)
            q.pop("slot", None)
            parts.append(q)
    mods = {k: {"biokea": m["biokea"], "stages": m["stages"], "platform": m["platform"], "status": m["status"],
                "materials": m["materials"], "n_parts": len(m["part_names"])}
            for k, m in MODULES.items() if m["part_names"]}
    mods[MISC] = {"biokea": None, "stages": [], "platform": ["bench"], "status": "CONCEPT", "materials": [], "n_parts": 1}
    out = {"note": "Geometry concepts, not tested on hardware. Layout positions are illustrative.",
           "sbs_mm": [127.76, 85.48], "slot_pitch_mm": [PX, PY], "slots": SLOTS, "modules": mods, "parts": parts}
    (OUT / "parts.json").write_text(json.dumps(out, indent=1))
    print(len(parts), "part entries,", len(mods), "modules")


if __name__ == "__main__":
    main()
