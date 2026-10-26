"""DAISY-BB-004 data: specimen crops labelled with GBIF taxonomy, one classification view per run.

Crops come from the YOLOE pseudo-label polygons of r3_ca (train/val) and holdout_az/nv/or (test). Each
crop inherits its source photo's GBIF order/family/scientificName, licence and rights holder (matched by
media id = file stem). Splits follow the source photo, so one photo's crops never span splits.

Output (under datasets/taxon_crops):
  crops/<split>/<mediaid>_<k>.jpg        the crop files (one store)
  crops.jsonl                            one record per crop: path, sha256, split, labels, licence, source
  views/<RUN>/<train|val|test>/<class>/  hardlinks into crops/ for yolo-cls (ORDER, FAMILY_<order>)
  report.json                            counts, pooled classes, leakage gate, Merkle root
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path

D = Path("/Volumes/magicBLACKbox/baebugs/datasets")
MANIFESTS = [D / "gbif_ca_2/manifest.jsonl", D / "gbif_az/manifest.jsonl", D / "gbif_nv/manifest.jsonl",
             D / "gbif_or/manifest.jsonl", Path("/Volumes/magicLABbox/baebugs/datasets/gbif_specimen_images/manifest.jsonl")]
SOURCES = [("r3_ca", "train", "train"), ("r3_ca", "val", "val"),
           ("holdout_az", "val", "test"), ("holdout_nv", "val", "test"), ("holdout_or", "val", "test")]
MIN_TRAIN = 20
PAD = 0.08


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def taxonomy():
    t = {}
    for m in MANIFESTS:
        if not m.exists():
            continue
        for line in m.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                stem = Path(r.get("file") or "").stem or str(r.get("gbifID"))
                t[stem] = {k: r.get(k) for k in ("order", "family", "scientificName", "license", "rightsHolder",
                                                  "institutionCode", "catalogNumber", "gbifID")}
    return t


def build(datasets=D, out=None):
    import cv2
    out = Path(out or Path(datasets) / "taxon_crops")
    tax = taxonomy()
    recs, missing = [], Counter()
    (out / "crops").mkdir(parents=True, exist_ok=True)
    for ds, sp, split in SOURCES:
        base = Path(datasets) / ds
        for img_p in sorted((base / "images" / sp).glob("*.jpg")):
            lab = base / "labels" / sp / f"{img_p.stem}.txt"
            t = tax.get(img_p.stem)
            if not lab.exists() or not t or not t.get("order"):
                missing["no_taxonomy" if not t or not t.get("order") else "no_label"] += 1; continue
            img = cv2.imread(str(img_p))
            if img is None:
                missing["undecodable"] += 1; continue
            h, w = img.shape[:2]
            for k, line in enumerate(l for l in lab.read_text().splitlines() if l.strip()):
                v = [float(x) for x in line.split()[1:]]
                xs, ys = v[0::2], v[1::2]
                x0, x1, y0, y1 = min(xs) * w, max(xs) * w, min(ys) * h, max(ys) * h
                px, py = (x1 - x0) * PAD, (y1 - y0) * PAD
                x0, y0 = max(0, int(x0 - px)), max(0, int(y0 - py)); x1, y1 = min(w, int(x1 + px)), min(h, int(y1 + py))
                if x1 - x0 < 8 or y1 - y0 < 8:
                    missing["tiny"] += 1; continue
                rel = f"crops/{split}/{img_p.stem}_{k}.jpg"
                (out / rel).parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out / rel), img[y0:y1, x0:x1], [cv2.IMWRITE_JPEG_QUALITY, 95])
                recs.append({"path": rel, "sha256": sha(out / rel), "split": split, "media_id": img_p.stem,
                             "source": f"{ds}/images/{sp}/{img_p.name}", "box_px": [x0, y0, x1, y1], **t})
    # leakage gate: a media id in exactly one split
    by = {}
    for r in recs:
        by.setdefault(r["media_id"], set()).add(r["split"])
    leak = sorted(m for m, s in by.items() if len(s) > 1)
    # views
    import shutil
    if (out / "views").exists():
        shutil.rmtree(out / "views")
    runs = {}

    def view(run, key, subset):
        train_counts = Counter(r[key] for r in subset if r["split"] == "train")
        keep = {c for c, n in train_counts.items() if n >= MIN_TRAIN}
        pooled = sorted({r[key] for r in subset} - keep)
        for r in subset:
            cls = r[key] if r[key] in keep else "other"
            dst = out / "views" / run / r["split"] / cls.replace(" ", "_") / Path(r["path"]).name
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(out / r["path"], dst)
            except OSError:
                shutil.copy2(out / r["path"], dst)
        runs[run] = {"key": key, "classes": sorted(keep) + (["other"] if pooled else []), "pooled": pooled,
                     "counts": {s: dict(Counter((r[key] if r[key] in keep else "other") for r in subset if r["split"] == s))
                                for s in ("train", "val", "test")}}
    view("ORDER", "order", recs)
    top = [o for o, _ in Counter(r["order"] for r in recs if r["split"] == "train").most_common(2)]
    for o in top:
        view(f"FAMILY_{o}", "family", [r for r in recs if r["order"] == o and r.get("family")])
    from .explore import merkle_root
    leaves = sorted(hashlib.sha256(f"{r['path']}\0{r['sha256']}".encode()).hexdigest() for r in recs)
    (out / "crops.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    rep = {"crops": len(recs), "by_split": dict(Counter(r["split"] for r in recs)), "skipped": dict(missing),
           "leakage_media_ids": len(leak), "leak_examples": leak[:5], "runs": runs, "merkle_root": merkle_root(leaves),
           "licences": dict(Counter(r.get("license") for r in recs)), "min_train_per_class": MIN_TRAIN}
    (out / "report.json").write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    r = build()
    print(json.dumps({k: v for k, v in r.items() if k != "runs"}, indent=1))
    for k, v in r["runs"].items():
        print(k, v["classes"], v["counts"])
