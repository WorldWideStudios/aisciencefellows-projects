"""Trommel sized to BioKEA trays, all parts on ONE build plate (single print run).

Trays (measured from the pinned BioKEA/BugPicker designs, by size only; nothing copied):
  tray.stl        103.0 x 140.0 x 12.5 mm
  screentray.stl  113.6 x 149.7 x 10.0 mm
One drum zone per tray: trays sit side by side under the drum, short side along the axis, so the zone pitch
is the widest tray's short side plus a gap, and only a centred band of each zone is perforated so fines land
inside the narrower tray too. The drum bottom clears the tallest tray.

  python -m baebugs.trommel_plate --printer x1c --out print/packages/trommel_biokea_x1c
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import trimesh

from . import print_parts as pp

TRAYS = {"tray": (103.0, 140.0, 12.5), "screentray": (113.6, 149.7, 10.0)}
PRINTERS = {"x1c": {"name": "Bambu Lab X1 Carbon", "bed": (256.0, 256.0, 256.0)},
            "h2s": {"name": "Bambu Lab H2S", "bed": (340.0, 320.0, 340.0)}}


def params(gap=6.0, margin=9.0, clearance=12.0, drum_od=76.0):
    short = max(t[0] for t in TRAYS.values()); narrow = min(t[0] for t in TRAYS.values())
    tall = max(t[2] for t in TRAYS.values())
    zone = round(short + gap, 1)                       # zone pitch = tray pitch
    return {"drum_od": drum_od, "zone_len": zone, "hole_band": round(narrow - 2 * margin, 1),
            "axis_h": round(drum_od / 2 + tall + clearance, 1)}


def build(printer="x1c", out="print/packages/trommel_biokea_x1c", spacing=6.0):
    q = params()
    saved = dict(pp.P)
    pp.P.update(q)
    try:
        return _build(q, printer, out, spacing)
    finally:
        pp.P.clear(); pp.P.update(saved)


def _build(q, printer, out, spacing):
    L = q["zone_len"]
    parts = {f"trommel_zone_{d:g}mm": pp.drum_zone(d) for d in pp.P["zone_holes"]}
    parts.update({"trommel_cap_inlet": pp.drum_cap("inlet").mirror([0, 0, 1]),
                  "trommel_cap_outlet": pp.drum_cap("outlet").mirror([0, 0, 1]),
                  "trommel_stand_inlet": pp.stand(math.tan(math.radians(pp.P["incline_deg"])) * (3 * L + 20)),
                  "trommel_stand_outlet": pp.stand(0.0), "trommel_crank_hand": pp.crank(False).rotate([0, 0, 90])})
    meshes = {}
    for k, m in parts.items():
        t = pp.to_trimesh(m); t.apply_translation(-t.bounds[0]); meshes[k] = t
    bx, by, bz = PRINTERS[printer]["bed"]
    rows = [["trommel_zone_2mm", "trommel_zone_4mm", "trommel_zone_7mm"],
            ["trommel_cap_inlet", "trommel_cap_outlet", "trommel_crank_hand"],
            ["trommel_stand_inlet", "trommel_stand_outlet"]]
    placed, y = {}, spacing
    for row in rows:
        x, h = spacing, 0.0
        for k in row:
            t = meshes[k].copy(); t.apply_translation([x, y, 0]); placed[k] = t
            x += t.extents[0] + spacing; h = max(h, t.extents[1])
        y += h + spacing
    plate = trimesh.util.concatenate(list(placed.values()))
    lo, hi = plate.bounds
    edge = 5.0                                         # keep clear of the bed edge
    fits = bool(lo[0] >= edge and lo[1] >= edge and hi[0] <= bx - edge and hi[1] <= by - edge and hi[2] <= bz)
    boxes = [t.bounds for t in placed.values()]
    overlap = any(not (a[1][0] <= b[0][0] or b[1][0] <= a[0][0] or a[1][1] <= b[0][1] or b[1][1] <= a[0][1])
                  for i, a in enumerate(boxes) for b in boxes[i + 1:])
    out = Path(out); (out / "stl").mkdir(parents=True, exist_ok=True)
    files = []
    for k, t in meshes.items():
        f = out / "stl" / f"{k}.stl"; t.export(f)
        files.append({"file": f"stl/{f.name}", "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                      "size_mm": [round(float(v), 1) for v in t.extents], "watertight": bool(t.is_watertight)})
    pf = out / f"trommel_plate_{printer}.stl"; plate.export(pf)
    sc = trimesh.Scene(); [sc.add_geometry(t, node_name=k) for k, t in placed.items()]
    p3 = out / f"trommel_plate_{printer}.3mf"; p3.write_bytes(trimesh.exchange.threemf.export_3MF(sc))
    rod = round(3 * L + 2 * 9 + 2 * 30 + 14 + 20)
    info = {"printer": PRINTERS[printer]["name"], "bed_mm": [bx, by, bz], "plate_extent_mm": [round(float(v), 1) for v in hi],
            "fits_bed": fits, "parts_overlap": overlap, "trays_mm": TRAYS, "params": q, "rod_mm": rod,
            "drum_bottom_above_bench_mm": round(q["axis_h"] - q["drum_od"] / 2, 1),
            "plate_stl_sha256": hashlib.sha256(pf.read_bytes()).hexdigest(), "files": files}
    from .explore import merkle_root
    info["merkle_root"] = merkle_root(sorted(f["sha256"] for f in files))
    (out / "manifest.json").write_text(json.dumps(info, indent=1))
    # top-down plate preview
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    fig, ax = plt.subplots(figsize=(6, 6)); ax.add_patch(plt.Rectangle((0, 0), bx, by, fill=False, lw=2))
    for k, t in placed.items():
        ax.add_collection(PolyCollection(
            t.vertices[t.faces][:, :, :2][::7], facecolor="#6aa", edgecolor="none", alpha=.35))
        c = t.bounds.mean(0); ax.text(c[0], c[1], k.replace("trommel_", ""), ha="center", va="center", fontsize=7)
    ax.set_xlim(-5, bx + 5); ax.set_ylim(-5, by + 5); ax.set_aspect("equal"); ax.set_title(f"{PRINTERS[printer]['name']} plate {bx:g} x {by:g} mm")
    fig.savefig(out / "plate_preview.png", dpi=120, bbox_inches="tight"); plt.close(fig)
    return info


def build_split(out="print/packages/trommel_biokea_split", spacing=8.0):
    """After FDM attempt 1: perforated drum zones go to the Fuse 1+ (PA12 powder needs no supports, holes stay clean);
    caps, stands and crank stay on one X1C plate. Same geometry and tray fit as the one-plate package."""
    import tempfile
    src = Path(tempfile.mkdtemp())
    info = build("x1c", src)
    out = Path(out); (out / "fuse1_zones").mkdir(parents=True, exist_ok=True); (out / "x1c_rest").mkdir(parents=True, exist_ok=True)
    meshes = {f.stem: trimesh.load(f) for f in sorted((src / "stl").glob("*.stl"))}
    zones = [k for k in meshes if "zone" in k]; rest = [k for k in meshes if k not in zones]
    files = []

    def place(keys, bed, sub, name, gap=spacing):
        x = y = gap; row_h = 0.0; placed = []
        for k in keys:
            t = meshes[k].copy(); t.apply_translation(-t.bounds[0])
            if x + t.extents[0] > bed[0] - gap:
                x = gap; y += row_h + gap; row_h = 0.0
            t.apply_translation([x, y, 0]); placed.append(t); x += t.extents[0] + gap; row_h = max(row_h, t.extents[1])
            f = out / sub / f"{k}.stl"; meshes[k].export(f)
            files.append({"file": f"{sub}/{f.name}", "sha256": hashlib.sha256(f.read_bytes()).hexdigest()})
        plate = trimesh.util.concatenate(placed); hi = plate.bounds[1]
        plate.export(out / sub / name)
        return {"extent_mm": [round(float(v), 1) for v in hi], "fits": bool(hi[0] <= bed[0] and hi[1] <= bed[1] and hi[2] <= bed[2])}

    fuse = place(zones, (165.0, 165.0, 300.0), "fuse1_zones", "fuse1_zones_build.stl", gap=4.0)   # powder bed: 4 mm gaps
    x1c = place(rest, (256.0 - 5, 256.0 - 5, 256.0), "x1c_rest", "x1c_rest_plate.stl")
    from .explore import merkle_root
    m = {"params": info["params"], "trays_mm": TRAYS, "fuse1_build": fuse, "x1c_plate": x1c, "rod_mm": info["rod_mm"],
         "files": files, "merkle_root": merkle_root(sorted(f["sha256"] for f in files)),
         "why": "FDM attempt 1 (blue, photo fdm_trommel_attempt1): caps/crank/feet printed, perforated zones failed"}
    (out / "manifest.json").write_text(json.dumps(m, indent=1))
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--printer", default="x1c"); ap.add_argument("--out", default="print/packages/trommel_biokea_x1c")
    a = ap.parse_args()
    i = build(a.printer, a.out)
    print(json.dumps({k: i[k] for k in ("fits_bed", "parts_overlap", "plate_extent_mm", "params", "rod_mm", "drum_bottom_above_bench_mm", "merkle_root")}, indent=1))
    print([(f["file"], f["size_mm"], f["watertight"]) for f in i["files"]])
