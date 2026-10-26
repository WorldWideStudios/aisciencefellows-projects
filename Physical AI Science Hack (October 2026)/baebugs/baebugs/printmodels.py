"""TOY insect models for SLS printing (Formlabs Fuse 1+ 30W): parametric stand-ins, not replicas.

Sizes come from the ruler-measured museum specimens (GBIF/UCSB etc., pulled and
measured by baebugs): for each family, length = mean + k*SD for k in -2..+2,
clamped to 1-30 mm. A novel set comes from specimens OUTSIDE California
(Oregon/Arizona/Nevada pulls): families absent from the California data and
specimens more than 2 SD from their California family. A fill-in set covers
1-3 mm, where the database has no specimens.

Body = head + thorax + abdomen ellipsoids along X (length), width along Y.
Legs, antennae and wings are added only where the Fuse can print them:
pins/legs >= 0.8 mm diameter, plates >= 0.8 mm thick (Formlabs Fuse 1 design
spec: 0.8 mm pins, 0.6 mm vertical walls in Nylon 12). Database widths include
spread wings/legs, so BODY width uses a per-body-plan aspect ratio instead.

Output: one watertight STL per model + manifest.csv (+ breakaway trees that keep
small parts from getting lost in the powder).
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import trimesh

PIN = 0.8      # mm, min pin / leg / antenna diameter
PLATE = 0.8    # mm, min wing thickness (vertical walls 0.6 mm; keep margin)

# body plan: body width / length, height / width, head, thorax, abdomen fractions
PLANS = {
    "beetle_dome":  {"aspect": 0.75, "h": 0.65, "seg": (0.15, 0.25, 0.60), "legs": True, "wings": None},
    "beetle_long":  {"aspect": 0.40, "h": 0.55, "seg": (0.15, 0.25, 0.60), "legs": True, "wings": None},
    "ant":          {"aspect": 0.25, "h": 0.90, "seg": (0.25, 0.35, 0.40), "legs": True, "wings": None},
    "bee":          {"aspect": 0.42, "h": 0.90, "seg": (0.18, 0.32, 0.50), "legs": True, "wings": "folded"},
    "wasp":         {"aspect": 0.30, "h": 0.90, "seg": (0.18, 0.30, 0.52), "legs": True, "wings": "folded"},
    "fly":          {"aspect": 0.40, "h": 0.85, "seg": (0.20, 0.35, 0.45), "legs": True, "wings": "spread"},
    "bug":          {"aspect": 0.42, "h": 0.45, "seg": (0.12, 0.30, 0.58), "legs": True, "wings": None},
    "strider":      {"aspect": 0.15, "h": 0.80, "seg": (0.15, 0.35, 0.50), "legs": True, "wings": None},
    "moth":         {"aspect": 0.25, "h": 0.90, "seg": (0.15, 0.35, 0.50), "legs": False, "wings": "spread"},
    "cicada":       {"aspect": 0.38, "h": 0.75, "seg": (0.15, 0.35, 0.50), "legs": True, "wings": "folded"},
    "damselfly":    {"aspect": 0.08, "h": 1.00, "seg": (0.08, 0.17, 0.75), "legs": False, "wings": "folded"},
    "thrips":       {"aspect": 0.25, "h": 0.70, "seg": (0.15, 0.25, 0.60), "legs": False, "wings": None},
    "aphid":        {"aspect": 0.55, "h": 0.75, "seg": (0.15, 0.20, 0.65), "legs": False, "wings": None},
}

# California families (n, length mean, SD) from the ruler-measured specimens -> body plan
CA_FAMILIES = [
    ("Coleoptera", "Coccinellidae", 54, 6.3, 1.3, "beetle_dome"),
    ("Hymenoptera", "Formicidae", 26, 6.9, 2.2, "ant"),
    ("Hymenoptera", "Melittidae", 23, 7.7, 1.9, "bee"),
    ("Hymenoptera", "Andrenidae", 158, 9.8, 1.9, "bee"),
    ("Hymenoptera", "Halictidae", 308, 9.9, 3.5, "bee"),
    ("Diptera", "Syrphidae", 94, 10.7, 2.8, "fly"),
    ("Coleoptera", "Meloidae", 15, 11.4, 2.6, "beetle_long"),
    ("Hemiptera", "Largidae", 51, 13.0, 2.7, "bug"),
    ("Hymenoptera", "Vespidae", 34, 13.2, 2.5, "wasp"),
    ("Hymenoptera", "Apidae", 361, 13.5, 3.6, "bee"),
    ("Diptera", "Bombyliidae", 326, 15.0, 3.2, "fly"),
    ("Hemiptera", "Gerridae", 44, 21.3, 5.1, "strider"),
    ("Lepidoptera", "Hesperiidae", 30, 24.4, 4.0, "moth"),
    ("Hemiptera", "Cicadidae", 18, 25.5, 3.3, "cicada"),
]

# outside California (Oregon / Arizona / Nevada pulls)
NOVEL = [
    ("Odonata", "Coenagrionidae", "AZ, NV", "family absent from CA data", [22.9, 26.4, 29.9], "damselfly"),
    ("Lepidoptera", "Elachistidae", "OR", "family absent from CA data", [6.7, 8.4, 10.1], "moth"),
    ("Hymenoptera", "Apidae (Xylocopa tabaniformis orpifex)", "OR", "z = +4.4 vs CA Apidae", [29.1], "bee"),
    ("Hymenoptera", "Apidae (Bombus mixtus)", "OR", "z = +4.1 vs CA Apidae", [28.2], "bee"),
    ("Hymenoptera", "Andrenidae (Andrena prunorum)", "OR", "z = +5.6 vs CA Andrenidae", [20.1], "bee"),
    ("Hymenoptera", "Colletidae (Ptiloglossa arizonensis)", "AZ", "z = +4.2 vs CA Colletidae", [16.2], "bee"),
    ("Coleoptera", "Meloidae (Epicauta fortis)", "AZ", "z = -3.5 vs CA Meloidae", [2.1], "beetle_long"),
    ("Hymenoptera", "Andrenidae (Perdita sp.)", "AZ", "z = -3.3 vs CA Andrenidae", [3.6], "bee"),
]

# 1-3 mm: below the database's smallest specimen (2.8 mm) -> fill-in sizes, not measured
FILL_IN = [("Thysanoptera", "thrips-like", [1.0, 1.5, 2.0], "thrips"),
           ("Hemiptera", "aphid-like", [1.5, 2.0, 2.5, 3.0], "aphid"),
           ("Coleoptera", "small beetle", [1.0, 1.5, 2.0, 2.5, 3.0], "beetle_dome")]


# Every model here is a TOY: a parametric stand-in (ellipsoids + 0.8 mm rods +
# 0.8 mm plates) sized from database statistics. Not an anatomical replica and
# not a validated size standard; use for handling, sieve and vision tests only.
REPRESENTATION = "toy"
TOY_SHAPE = "parametric toy: ellipsoid body segments, rod legs/antennae, flat plate wings"
# sizes that disagree with typical published body lengths: museum-photo envelope
# probably included wings / legs / labels (or a mis-scaled ruler). Flagged, not corrected.
SIZE_SUSPECT = {
    "Hesperiidae": "family mean likely wingspan, not body length",
    "Gerridae": "family mean likely includes legs",
    "Halictidae": "family mean runs large for sweat bees",
    "Bombyliidae": "family mean runs large; likely includes wings",
    "Apidae (Xylocopa tabaniformis orpifex)": "29.1 mm larger than typical for this carpenter bee",
    "Apidae (Bombus mixtus)": "28.2 mm far larger than typical for this bumble bee",
    "Andrenidae (Andrena prunorum)": "20.1 mm far larger than typical for this mining bee",
    "Meloidae (Epicauta fortis)": "2.1 mm far smaller than typical for a blister beetle",
}


DB_MIN_MM = 2.8   # smallest ruler-measured specimen in the pulled database


def toy_fields(family, size_source, length_mm):
    """Toy labels + training role. Edge negatives look like insects but must NOT
    be triaged as known database insects: suspect sizes (wrong size for the named
    taxon) and anything below the database minimum."""
    if size_source.startswith("fill-in"):
        flag = "fill-in size, not measured"
    else:
        flag = "suspect: " + SIZE_SUSPECT[family] if family in SIZE_SUSPECT else "database-derived, unverified"
    role = ("edge_negative:family_stats_suspect" if flag.startswith("suspect") and family in {f: 1 for _, f, *_ in CA_FAMILIES} else
            "edge_negative:size_suspect" if flag.startswith("suspect") else
            "edge_negative:below_database" if length_mm < DB_MIN_MM else "positive")
    return {"representation": REPRESENTATION, "shape_fidelity": TOY_SHAPE, "size_flag": flag, "training_role": role}


def _ellipsoid(center, rx, ry, rz, sub=3):
    m = trimesh.creation.icosphere(subdivisions=sub, radius=1.0)
    m.apply_scale([rx, ry, rz])
    m.apply_translation(center)
    return m


def _rod(a, b, d):
    a, b = np.asarray(a, float), np.asarray(b, float)
    v = b - a
    L = float(np.linalg.norm(v))
    m = trimesh.creation.cylinder(radius=d / 2, height=L, sections=12)
    T = trimesh.geometry.align_vectors([0, 0, 1], v / L)
    m.apply_transform(T)
    m.apply_translation((a + b) / 2)
    caps = [trimesh.creation.icosphere(subdivisions=1, radius=d / 2).apply_translation(p) for p in (a, b)]
    return [m] + caps


def insect_parts(length_mm, plan_name):
    """The insect as named primitives, in build order. Each entry:
    {"part": "leg_2R", "tagma": "thorax", "kind": "rod", "spec": {...}, "meshes": [...]}.
    Specs are the exact build parameters, so a part can be hashed and rebuilt
    deterministically (baebugs.insect_kg)."""
    p = PLANS[plan_name]
    L = float(length_mm)
    W = max(L * p["aspect"], 0.7)            # body width
    H = max(W * p["h"], 0.6)
    fh, ft, fa = p["seg"]
    xs = [-L / 2 + fh * L / 2, -L / 2 + fh * L + ft * L / 2, L / 2 - fa * L / 2]
    prims, feats = [], []

    def ell(part, tagma, c, r):
        prims.append({"part": part, "tagma": tagma, "kind": "ellipsoid", "seg": part,
                      "spec": {"center": list(c), "radii": list(r)}, "meshes": [_ellipsoid(c, *r)]})

    def rod(part, tagma, seg, a, b, d):
        prims.append({"part": part, "tagma": tagma, "kind": "rod", "seg": seg,
                      "spec": {"a": list(a), "b": list(b), "d": d}, "meshes": _rod(a, b, d)})

    def box(part, tagma, ext, c):
        m = trimesh.creation.box(extents=ext); m.apply_translation(c)
        prims.append({"part": part, "tagma": tagma, "kind": "plate", "seg": part,
                      "spec": {"center": list(c), "extents": list(ext)}, "meshes": [m]})

    ell("head_body", "head", [xs[0], 0, 0], (fh * L / 2 * 1.15, W * 0.30 + 0.15, H * 0.40 + 0.1))
    ell("thorax_body", "thorax", [xs[1], 0, 0], (ft * L / 2 * 1.10, W * 0.45, H * 0.48))
    ell("abdomen_body", "abdomen", [xs[2], 0, 0], (fa * L / 2 * 1.05, W * 0.50, H * 0.50))
    leg_d = max(PIN, 0.09 * W)
    if p["legs"] and L >= 6.0 and leg_d <= 0.45 * W + 0.4:
        span = W * (2.6 if plan_name == "strider" else 0.75)   # total leg spread ~1.5x body width
        for i, dx in enumerate((-0.30, 0.0, 0.30)):
            x0 = xs[1] + dx * ft * L
            for s in (-1, 1):
                side = "L" if s < 0 else "R"
                knee = [x0 + dx * L * 0.25, s * span * 0.55, -H * 0.10]
                foot = [x0 + dx * L * 0.55 + (0.15 * L if i == 2 else 0), s * span, -H * 0.45]
                rod(f"leg_{i + 1}{side}", "thorax", "femur", [x0, s * W * 0.25, -H * 0.1], knee, leg_d)
                rod(f"leg_{i + 1}{side}", "thorax", "tibia", knee, foot, leg_d)
        feats.append(f"6 legs Ø{leg_d:.2f}")
    if L >= 12.0 and plan_name not in ("damselfly",):
        a0 = [-L / 2 + 0.1 * fh * L, 0, H * 0.15]
        for s in (-1, 1):
            rod(f"antenna_{'L' if s < 0 else 'R'}", "head", "antenna", a0, [-L / 2 - 0.25 * L, s * W * 0.6, H * 0.45], PIN)
        feats.append(f"antennae Ø{PIN}")
    if p["wings"] and L >= 8.0:
        t = PLATE
        if p["wings"] == "spread":
            wl, ww = 0.55 * L, (0.95 if plan_name == "moth" else 0.6) * L
            for s in (-1, 1):
                box(f"wing_{'L' if s < 0 else 'R'}", "thorax", [wl, ww, t], [xs[1] + 0.05 * L, s * (ww / 2 + W * 0.2), H * 0.30])
            feats.append(f"spread wings {t} mm")
        else:
            wl, ww = 0.75 * L, max(W * 0.55, 1.2)
            for s in (-1, 1):
                box(f"wing_{'L' if s < 0 else 'R'}", "thorax", [wl, ww, t], [xs[1] + 0.30 * L, s * ww * 0.35, H * 0.52])
            feats.append(f"folded wings {t} mm")
    dims = {"L": L, "W": W, "H": H, "xs": xs}
    return prims, feats, dims


def build_insect(length_mm, plan_name):
    """Watertight mesh of a length_mm insect with the given body plan, honouring
    Fuse minimums. Returns (mesh, info)."""
    prims, feats, d = insect_parts(length_mm, plan_name)
    L, W, H = d["L"], d["W"], d["H"]
    parts = [m for pr in prims for m in pr["meshes"]]
    mesh = trimesh.boolean.union(parts, engine="manifold")
    if not mesh.is_watertight:                      # repair pass (rare): fill holes, fix winding
        trimesh.repair.fill_holes(mesh); trimesh.repair.fix_normals(mesh)
    ext = mesh.bounding_box.extents
    info = {"plan": plan_name, "length_mm": round(L, 2), "body_width_mm": round(W, 2), "height_mm": round(H, 2),
            "bbox_mm": [round(float(e), 2) for e in ext], "features": "; ".join(feats) or "body only",
            "watertight": bool(mesh.is_watertight), "volume_mm3": round(float(mesh.volume), 2)}
    return mesh, info


def tray_for(width_mm):
    from .sieve import classify, load_yaml
    kit = load_yaml("insects.yaml")
    cls = classify(width_mm, kit["classes"])
    return next((c["sieve"] for c in kit["classes"] if c["name"] == cls), "out of range")


def breakaway_tree(meshes, spacing=5.0, rail_d=1.6, sprue_d=0.8):
    """Lay parts out on a rail with thin sprues (break off after printing) so
    small parts are not lost in the powder; 5 mm spacing per Formlabs guidance."""
    placed, x = [], 0.0
    for m in meshes:
        m = m.copy()
        b = m.bounds
        m.apply_translation([x - b[0][0], -b[0][1] + 3.0, -b[0][2]])
        cx = float((m.bounds[0][0] + m.bounds[1][0]) / 2)
        placed.append(m)
        placed += _rod([cx, 0, rail_d / 2], [cx, 3.0 + 0.3, max(0.5, float(m.bounds[1][2]) * 0.3)], sprue_d)
        x = float(m.bounds[1][0]) + spacing
    rail = trimesh.creation.box(extents=[x, rail_d, rail_d]); rail.apply_translation([x / 2 - spacing / 2, 0, rail_d / 2])
    tree = trimesh.boolean.union(placed + [rail], engine="manifold")
    return tree


def generate(out_dir):
    out = Path(out_dir)
    for sub in ("california", "novel_outside_ca", "fill_in_1-3mm", "trees"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    rows = []

    def emit(group, order, family, label, L, plan, source, note=""):
        L = float(min(30.0, max(1.0, L)))
        mesh, info = build_insect(L, plan)
        safe = "".join(c if c.isalnum() else "_" for c in family)[:40].strip("_")
        name = f"{safe}_{label}_{L:.1f}mm.stl".replace("__", "_")
        path = out / group / name
        mesh.export(path)
        rows.append({"group": group, "file": f"{group}/{name}", "order": order, "family": family, "level": label,
                     **info, "kit_tray": tray_for(info["body_width_mm"]), "size_source": source, "note": note,
                     **toy_fields(family, source, L)})
        return mesh

    for order, fam, n, mu, sd, plan in CA_FAMILIES:
        for k in (-2, -1, 0, 1, 2):
            L = mu + k * sd
            if L < 1.0 or L > 30.0:
                continue
            emit("california", order, fam, f"mean{'+' if k >= 0 else ''}{k}SD" if k else "mean", L, plan,
                 f"CA museum specimens n={n}: L {mu}±{sd} mm")
    for order, fam, states, why, Ls, plan in NOVEL:
        for L in Ls:
            emit("novel_outside_ca", order, fam, "novel", L, plan, f"outside CA ({states})", why)
    small = []
    for order, fam, Ls, plan in FILL_IN:
        for L in Ls:
            small.append(emit("fill_in_1-3mm", order, fam, "fill", L, plan,
                              "fill-in: below database minimum (2.8 mm); not measured"))
    # trees: all 1-3 mm parts, and all parts < 6 mm from the other groups
    if small:
        breakaway_tree(small).export(out / "trees" / "tree_fill_in_1-3mm.stl")
    tiny_other = [trimesh.load(out / r["file"]) for r in rows if r["group"] != "fill_in_1-3mm" and r["length_mm"] < 6]
    if tiny_other:
        breakaway_tree(tiny_other).export(out / "trees" / "tree_under_6mm.stl")
    with (out / "manifest.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    return rows


if __name__ == "__main__":
    import sys
    rows = generate(sys.argv[1] if len(sys.argv) > 1 else "print/fuse1")
    print(len(rows), "models;", sum(r["watertight"] for r in rows), "watertight")
