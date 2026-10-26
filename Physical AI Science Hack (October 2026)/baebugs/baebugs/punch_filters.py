"""Novel filters from craft-store hole punches, plastic canvas and netting.

Each library entry is a hole SHAPE at a NOMINAL size (inch punches converted to
mm; canvas openings = pitch - nominal bar). Sizes are nominal until measured:
punch dies vary by brand, so measure one punched hole (calibrate-sieve) before
trusting a cut. A filter = shape x layout (square or hex grid) x web x plate.

Realisations
  punched  hand-punch the pattern into PET / acetate / craft-foam sheet
  bought   plastic canvas, tulle (use as sold)
  printed  Fuse 1+ Nylon 12 plate (holes >= 1.0 mm, web >= 0.8 mm)

  python -m baebugs.punch_filters --out print/filters
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

IN = 25.4
FUSE_MIN_HOLE = 1.0     # mm
FUSE_MIN_WEB = 0.8      # mm (0.6 vertical-wall rule + margin)


# ------------------------------------------------------------------ shapes

def circle(d):
    return Point(0, 0).buffer(d / 2, 64)


def square(s):
    return box(-s / 2, -s / 2, s / 2, s / 2)


def hexagon(across_flats):
    r = across_flats / 2 / math.cos(math.pi / 6)
    return Polygon([(r * math.cos(math.pi / 3 * i), r * math.sin(math.pi / 3 * i)) for i in range(6)])


def star(outer_d, inner_ratio=0.45, n=5):
    R, r = outer_d / 2, outer_d / 2 * inner_ratio
    pts = []
    for i in range(2 * n):
        a = math.pi / 2 + math.pi * i / n
        rr = R if i % 2 == 0 else r
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return Polygon(pts)


def heart(width):
    pts = [(16 * math.sin(t) ** 3, 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
           for t in [2 * math.pi * i / 120 for i in range(120)]]
    p = Polygon(pts)
    minx, _miny, maxx, _maxy = p.bounds
    p = affinity.scale(p, width / (maxx - minx), width / (maxx - minx), origin=(0, 0))
    c = p.centroid
    return affinity.translate(p, -c.x, -c.y)


def slot(w, length):
    return LineString([(-(length - w) / 2, 0), ((length - w) / 2, 0)]).buffer(w / 2, 32)


SHAPES = {"circle": circle, "square": square, "hexagon": hexagon, "star": star, "heart": heart, "slot": slot}

# ------------------------------------------------------------------ library
# (id, category, realisation, shape, params, note)
LIBRARY = [
    ("RND-1/16", "single hole punch", "punched", "circle", {"d": IN / 16}, "1/16 in round punch"),
    ("RND-1/8", "single hole punch", "punched", "circle", {"d": IN / 8}, "1/8 in round punch"),
    ("RND-3/16", "single hole punch", "punched", "circle", {"d": 3 * IN / 16}, "3/16 in round punch"),
    ("RND-1/4", "single hole punch", "punched", "circle", {"d": IN / 4}, "1/4 in round (standard office/craft)"),
    ("RND-3/8", "shape punch", "punched", "circle", {"d": 3 * IN / 8}, "3/8 in circle"),
    ("RND-1/2", "shape punch", "punched", "circle", {"d": IN / 2}, "1/2 in circle"),
    ("RND-5/8", "shape punch", "punched", "circle", {"d": 5 * IN / 8}, "5/8 in circle"),
    ("RND-1", "shape punch", "punched", "circle", {"d": IN}, "1 in circle"),
    ("SQ-1/4", "shape punch", "punched", "square", {"s": IN / 4}, "1/4 in square"),
    ("STAR-1/4", "shape punch", "punched", "star", {"outer_d": IN / 4}, "1/4 in star"),
    ("STAR-1/2", "shape punch", "punched", "star", {"outer_d": IN / 2}, "1/2 in star"),
    ("HEART-1/4", "shape punch", "punched", "heart", {"width": IN / 4}, "1/4 in heart"),
    ("HEART-1/2", "shape punch", "punched", "heart", {"width": IN / 2}, "1/2 in heart"),
    ("HEX-1/4", "shape punch", "punched", "hexagon", {"across_flats": IN / 4}, "1/4 in hexagon"),
    ("SLOT-1/8x1/2", "badge slot punch", "punched", "slot", {"w": IN / 8, "length": IN / 2}, "ID-badge slot"),
    ("SLOT-3/16x5/8", "badge slot punch", "punched", "slot", {"w": 3 * IN / 16, "length": 5 * IN / 8}, "wide slot"),
    ("CANVAS-7", "plastic canvas", "bought", "square", {"s": IN / 7 - 0.9}, "7-count, bar ~0.9 mm (nominal)"),
    ("CANVAS-10", "plastic canvas", "bought", "square", {"s": IN / 10 - 0.9}, "10-count, bar ~0.9 mm (nominal)"),
    ("CANVAS-14", "plastic canvas", "bought", "square", {"s": IN / 14 - 0.9}, "14-count, bar ~0.9 mm (nominal)"),
    ("TULLE", "netting", "bought", "hexagon", {"across_flats": 1.2}, "bridal tulle hex ~1.2 mm (nominal)"),
    # metal: preferred for dead specimens (rigid, thin, cleanable). Standard perforated-sheet and
    # woven-mesh openings, NOMINAL until measured.
    ("SS-PERF-1.6", "metal perforated sheet", "metal", "circle", {"d": 1.6}, "stainless perforated 1/16 in round"),
    ("SS-PERF-2.4", "metal perforated sheet", "metal", "circle", {"d": 2.4}, "stainless perforated 3/32 in round"),
    ("SS-PERF-3.2", "metal perforated sheet", "metal", "circle", {"d": 3.2}, "stainless perforated 1/8 in round"),
    ("SS-PERF-4.8", "metal perforated sheet", "metal", "circle", {"d": 4.8}, "stainless perforated 3/16 in round"),
    ("SS-PERF-6.4", "metal perforated sheet", "metal", "circle", {"d": 6.4}, "stainless perforated 1/4 in round"),
    ("SS-PERF-9.5", "metal perforated sheet", "metal", "circle", {"d": 9.5}, "stainless perforated 3/8 in round"),
    ("SS-SLOT-1.6x12.7", "metal slotted sheet", "metal", "slot", {"w": 1.6, "length": 12.7}, "slotted perforated 1/16 x 1/2 in"),
    ("SS-SLOT-3.2x19", "metal slotted sheet", "metal", "slot", {"w": 3.2, "length": 19.05}, "slotted perforated 1/8 x 3/4 in"),
    ("SS-SLOT-4.8x19", "metal slotted sheet", "metal", "slot", {"w": 4.8, "length": 19.05}, "slotted perforated 3/16 x 3/4 in"),
    ("SS-MESH-1.0", "woven wire mesh", "metal", "square", {"s": 1.0}, "woven stainless ~1.0 mm opening"),
    ("SS-MESH-2.0", "woven wire mesh", "metal", "square", {"s": 2.0}, "woven stainless ~2.0 mm opening"),
    ("SS-HEX-2.5AF", "laser-cut 316L insert (concept C)", "metal", "hexagon", {"across_flats": 2.5},
     "hexagonal 2.5 mm across flats; distinct orientation / open-area alternative (uncalibrated concept)"),
]

# how each realisation is made; punch dies also cut thin aluminium shim, so punched shapes have a metal route
MATERIALS = {
    "punched": ["aluminium shim <= 0.3 mm (punched)", "PET / acetate sheet (punched)"],
    "bought": ["as sold (nylon / polyester)"],
    "metal": ["stainless sheet or woven mesh (bought; laser-cut for custom shapes)"],
    "kit": ["BioKEA kit frame"],
    "printed": ["Fuse 1+ PA12 (prototype only)"],
}


def hole(entry):
    _, _, _, shape, params, _ = entry
    return SHAPES[shape](**params)


def hole_metrics(h):
    """Inscribed diameter (largest circle), max width (bbox diag of min rect),
    min caliper width (narrow side of min rotated rect)."""
    mrr = h.minimum_rotated_rectangle
    xs = list(mrr.exterior.coords)[:4]
    sides = sorted(math.dist(xs[i], xs[(i + 1) % 4]) for i in range(2))
    try:
        from shapely import maximum_inscribed_circle
        r = maximum_inscribed_circle(h).length
    except Exception:  # noqa: BLE001 - fallback; the failure is recorded or degrades
        from shapely.ops import polylabel
        c = polylabel(h, 0.01); r = h.exterior.distance(c)
    return {"area_mm2": round(h.area, 3), "inscribed_d_mm": round(2 * r, 3),
            "min_width_mm": round(sides[0], 3), "max_width_mm": round(sides[1], 3)}


def plate(entry, size_mm=50.0, border_mm=3.0, web_mm=1.0, grid="hex"):
    """Plate outline with the hole pattern (shapely). Returns (geometry, holes, open_area)."""
    h = hole(entry)
    minx, miny, maxx, maxy = h.bounds
    w, hgt = maxx - minx, maxy - miny
    px, py = w + web_mm, hgt + web_mm
    inner = box(border_mm, border_mm, size_mm - border_mm, size_mm - border_mm)
    holes = []
    j = 0
    y = border_mm + hgt / 2
    while y + hgt / 2 <= size_mm - border_mm + 1e-9:
        off = (px / 2 if (grid == "hex" and j % 2) else 0.0)
        x = border_mm + w / 2 + off
        while x + w / 2 <= size_mm - border_mm + 1e-9:
            holes.append(affinity.translate(h, x, y))
            x += px
        y += py * (0.866 if grid == "hex" else 1.0) if grid == "hex" and entry[3] in ("circle", "hexagon") else py
        j += 1
    union = unary_union(holes) if holes else None
    geom = box(0, 0, size_mm, size_mm).difference(union) if union else box(0, 0, size_mm, size_mm)
    open_area = (union.area / inner.area) if union else 0.0
    return geom, holes, round(open_area, 3)


def spec(entry, web_mm=1.0, size_mm=50.0, thickness_mm=1.6):
    fid, cat, real, shape, params, note = entry
    m = hole_metrics(hole(entry))
    s = {"id": fid, "category": cat, "realisation": real, "materials": MATERIALS.get(real, []), "shape": shape,
         "params_mm": {k: round(v, 3) for k, v in params.items()}, "note": note, "nominal": True, **m,
         "plate": {"size_mm": size_mm, "thickness_mm": thickness_mm, "web_mm": web_mm}}
    s["fuse_printable"] = m["min_width_mm"] >= FUSE_MIN_HOLE and web_mm >= FUSE_MIN_WEB
    s["hash"] = hashlib.sha256(json.dumps({k: s[k] for k in ("shape", "params_mm", "plate")}, sort_keys=True).encode()).hexdigest()
    return s


def plate_stl(entry, path, size_mm=50.0, thickness_mm=1.6, web_mm=1.0, grid="hex"):
    import trimesh
    geom, holes, oa = plate(entry, size_mm, web_mm=web_mm, grid=grid)
    polys = list(getattr(geom, "geoms", [geom]))
    meshes = [trimesh.creation.extrude_polygon(p, thickness_mm) for p in polys]
    m = trimesh.util.concatenate(meshes)
    m.export(path)
    return {"holes": len(holes), "open_area": oa, "watertight": bool(m.is_watertight)}


def build(out_dir, stl=True):
    out = Path(out_dir); (out / "stl").mkdir(parents=True, exist_ok=True)
    rows = []
    for e in LIBRARY:
        s = spec(e)
        grid = "square" if e[1] == "plastic canvas" else "hex"
        _, holes, oa = plate(e, grid=grid)
        s.update({"holes_on_50mm_plate": len(holes), "open_area": oa})
        if stl and s["fuse_printable"]:
            try:
                s["stl"] = f"stl/{s['id'].replace('/', '-')}.stl"
                s.update(plate_stl(e, out / s["stl"], grid=grid))
            except Exception as ex:  # noqa: BLE001 - missing triangulator etc.
                s["stl"] = None; s["stl_error"] = str(ex)[:120]
        rows.append(s)
    (out / "filters.json").write_text(json.dumps(rows, indent=1))
    return rows


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="print/filters")
    ap.add_argument("--no-stl", action="store_true")
    a = ap.parse_args()
    for r in build(a.out, not a.no_stl):
        print(f"{r['id']:14s} {r['shape']:8s} inscribed {r['inscribed_d_mm']:6.2f} min_w {r['min_width_mm']:6.2f} "
              f"max_w {r['max_width_mm']:6.2f} open {r['open_area']:.2f} holes {r['holes_on_50mm_plate']:4d} "
              f"printable {r['fuse_printable']} {r.get('stl') or ''} {r.get('stl_error','')}")
