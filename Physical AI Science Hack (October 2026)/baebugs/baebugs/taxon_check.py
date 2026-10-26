"""Does the food trigger plant detection? BioCLIP (Tree of Life) taxon check.

BioCLIP names kingdom -> species from a photo. For the triage decision matrix it
adds a biological branch: Insecta = candidate specimen (novel/known by size),
Plantae = out-group plant material (grain, seed, litter), anything else / low
confidence = unknown. This module classifies crops and reports the lineage.

  python -m baebugs.taxon_check --dish-photo docs/analog_test/01_dishes_ruler.jpg \
      --object-report <analog_test/report.json> --object-photo docs/analog_test/03_mixed_dish_ruler.jpg \
      --controls <dir of museum insect photos> --out <dir>
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2

# photo 01, dishes top -> bottom (docs/analog_test/README.md)
DISH_CONTENTS = ["mixed: wild rice, red rice, ditalini, white rice, pasta shard", "chia", "couscous",
                 "ditalini", "white rice", "red rice (2 grains)", "brown + red rice"]
EXPECT = {"chia": "Plantae (Lamiaceae, Salvia)", "white rice": "Plantae (Poaceae, Oryza)",
          "red rice (2 grains)": "Plantae (Poaceae, Oryza)", "brown + red rice": "Plantae (Poaceae, Oryza)",
          "couscous": "processed wheat: unknown", "ditalini": "processed wheat: unknown"}


def classify(paths, rank="family", k=3):
    from bioclip import Rank, TreeOfLifeClassifier
    clf = TreeOfLifeClassifier()
    r = {"kingdom": Rank.KINGDOM, "class": Rank.CLASS, "order": Rank.ORDER,
         "family": Rank.FAMILY, "genus": Rank.GENUS, "species": Rank.SPECIES}[rank]
    preds = clf.predict([str(p) for p in paths], r, k=k)
    out = {}
    for p in preds:
        out.setdefault(Path(p["file_name"]).name, []).append(
            {kk: p.get(kk) for kk in ("kingdom", "phylum", "class", "order", "family", "genus", "species", "score")})
    return out


def dish_crops(photo, out_dir):
    from .analog_test import find_dishes
    img = cv2.imread(str(photo))
    dishes = sorted(find_dishes(img), key=lambda t: t[1])
    paths = []
    for i, (x, y, r) in enumerate(dishes):
        x0, y0, x1, y1 = int(max(0, x - r)), int(max(0, y - r)), int(x + r), int(y + r)
        p = Path(out_dir) / f"dish_{i + 1}.jpg"
        cv2.imwrite(str(p), img[y0:y1, x0:x1]); paths.append(p)
    return paths


def object_crops(photo, report_json, out_dir, max_n=40):
    img = cv2.imread(str(photo))
    rep = next(r for r in json.loads(Path(report_json).read_text()) if r["image"] == Path(photo).name)
    ppm = rep["scale"]["median_period"] if rep.get("scale") else 10.0
    paths = []
    objs = sorted([o for o in rep["objects"] if o.get("length_mm")], key=lambda o: -o["length_mm"])[:max_n]
    for i, o in enumerate(objs):
        half = int(max(40, o["length_mm"] * ppm * 0.9))
        x0, y0 = max(0, o["cx"] - half), max(0, o["cy"] - half)
        crop = img[y0:o["cy"] + half, x0:o["cx"] + half]
        if crop.size == 0:
            continue
        p = Path(out_dir) / f"obj_{i:02d}_{o['length_mm']:.1f}x{o['width_mm']:.1f}mm.jpg"
        cv2.imwrite(str(p), crop); paths.append(p)
    return paths


def kingdom_vote(preds):
    """Score-weighted kingdom / class over the top-k lineages."""
    tally = {}
    for p in preds:
        key = (p.get("kingdom"), p.get("class"))
        tally[key] = tally.get(key, 0) + float(p.get("score") or 0)
    (kg, cl), s = max(tally.items(), key=lambda kv: kv[1])
    return kg, cl, round(s, 3)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-taxon-check")
    ap.add_argument("--dish-photo"); ap.add_argument("--object-photo"); ap.add_argument("--object-report")
    ap.add_argument("--controls", help="dir of museum insect photos (should come back Insecta)")
    ap.add_argument("--n-controls", type=int, default=20)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); (out / "crops").mkdir(parents=True, exist_ok=True)
    groups = {}
    if a.dish_photo:
        groups["dish"] = dish_crops(a.dish_photo, out / "crops")
    if a.object_photo and a.object_report:
        groups["object"] = object_crops(a.object_photo, a.object_report, out / "crops")
    if a.controls:
        groups["control_insect"] = sorted(Path(a.controls).glob("*.jpg"))[:a.n_controls]
    allp = [p for v in groups.values() for p in v]
    preds = classify(allp, "family", k=3)
    rows = []
    for g, ps in groups.items():
        for i, p in enumerate(ps):
            pr = preds.get(Path(p).name, [])
            if not pr:
                continue
            kg, cl, s = kingdom_vote(pr)
            top = pr[0]
            label = DISH_CONTENTS[i] if g == "dish" and i < len(DISH_CONTENTS) else ("museum insect" if g == "control_insect" else Path(p).stem)
            rows.append({"group": g, "item": label, "kingdom": kg, "class": cl, "kingdom_score": s,
                         "top_family": top.get("family"), "top_genus": top.get("genus"),
                         "top_score": round(float(top.get("score") or 0), 3),
                         "expected": EXPECT.get(label, "Insecta" if g == "control_insect" else "")})
    (out / "taxon_check.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(f"{r['group']:14s} {r['item'][:38]:38s} -> {r['kingdom']}/{r['class']} ({r['kingdom_score']}) "
              f"top {r['top_family']} {r['top_genus']} {r['top_score']} | expected {r['expected']}")


if __name__ == "__main__":
    main()
