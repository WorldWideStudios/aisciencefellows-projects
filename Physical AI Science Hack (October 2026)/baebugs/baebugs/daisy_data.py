"""DAISY custody for every dataset we pulled or derived: verify, then stage.

For each registered dataset (raw pulls, transforms, synthetic, checks, context):
  1. pointer manifest: one leaf per file {path, sha256, bytes, role}, sorted by
     path; dataset root = merkle_root(leaf hashes). Source files are never
     modified (no-clobber); manifests are written beside, under daisy/.
  2. checks by kind
       raw_images  every manifest row present, file sha256 == manifest sha256,
                   image header decodes, licence present, unlisted files flagged
       yolo_seg    image/label pairing, label syntax (class, even coords >= 6,
                   all in [0,1], polygon area > 0), image header decodes,
                   duplicate bytes across splits (leakage)
       tabular     PII screen (person / email / phone columns, email + phone
                   patterns in cells)
       json        parses
  3. lineage (transforms): every derived item's id (gbifID stem) exists in its
     declared source; split consistency across source and derivative
     (no derived val item whose source sits in a training split, and vice versa)
  4. global leakage: no gbifID in a training split of one dataset and a val
     split of another.
Status per dataset: VERIFIED | FAILED (with reasons) | REJECTED (kept as a
negative record, never staged for training). Each dataset is a ledger break point.

  python -m baebugs.daisy_data verify --out /Volumes/magicBLACKbox/baebugs/daisy --ledger
  python -m baebugs.daisy_data transform-dataone ...   (PII-stripped public CSV)
  python -m baebugs.daisy_data toys --out .../daisy/toy_renders
  python -m baebugs.daisy_data stage --out .../daisy --kaggle-user biobitworks
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path

from .explore import merkle_root

B = "/Volumes/magicBLACKbox/baebugs/datasets"
R = "/Volumes/magicLABbox/baebugs/datasets"
IMG = {".jpg", ".jpeg", ".png"}

# name -> spec. roles: source | train | eval | negative | context
REGISTRY = {
    "gbif_ca_2":               {"path": f"{B}/gbif_ca_2", "kind": "raw_images", "role": "source"},
    "gbif_az":                 {"path": f"{B}/gbif_az", "kind": "raw_images", "role": "source"},
    "gbif_nv":                 {"path": f"{B}/gbif_nv", "kind": "raw_images", "role": "source"},
    "gbif_or":                 {"path": f"{B}/gbif_or", "kind": "raw_images", "role": "source"},
    "gbif_specimen_images":    {"path": f"{R}/gbif_specimen_images", "kind": "raw_images", "role": "source"},
    "pseudo_specimens_r3_real": {"path": f"{B}/pseudo_specimens_r3_real", "kind": "yolo_seg", "role": "train",
                                 "derived_from": ["gbif_ca_2", "gbif_az", "gbif_nv", "gbif_or", "gbif_specimen_images"],
                                 "transform": "YOLOE-11s-seg teacher pseudo-labels on ruler-scaled museum photos (train.pseudo_label_specimens)"},
    "multires_mp_0.3":         {"path": f"{B}/multires_r4_multires/mp_0.3", "kind": "yolo_seg", "role": "train",
                                "derived_from": ["pseudo_specimens_r3_real"], "transform": "resample to 0.3 MP (resolution.py)"},
    "multires_mp_1":           {"path": f"{B}/multires_r4_multires/mp_1", "kind": "yolo_seg", "role": "train",
                                "derived_from": ["pseudo_specimens_r3_real"], "transform": "resample to 1 MP"},
    "multires_mp_3":           {"path": f"{B}/multires_r4_multires/mp_3", "kind": "yolo_seg", "role": "train",
                                "derived_from": ["pseudo_specimens_r3_real"], "transform": "resample to 3 MP"},
    "synth_1_30_r2":           {"path": f"{B}/synth_1_30_r2", "kind": "yolo_seg", "role": "train", "synthetic": True,
                                "transform": "synth_seg.py 1-30 mm, ppm 6-40"},
    "synth_1_30_r3_real":      {"path": f"{B}/synth_1_30_r3_real", "kind": "yolo_seg", "role": "train", "synthetic": True,
                                "transform": "synth_seg.py 1-30 mm, ppm 6-40"},
    "synth_seg":               {"path": f"{R}/synth_seg", "kind": "yolo_seg", "role": "train", "synthetic": True,
                                "transform": "synth_seg.py r1"},
    "teacher_check":           {"path": f"{B}/_teacher_check", "kind": "yolo_seg", "role": "eval",
                                "derived_from": ["gbif_ca_2", "gbif_az", "gbif_nv", "gbif_or", "gbif_specimen_images"]},
    "teacher_check2":          {"path": f"{B}/_teacher_check2", "kind": "yolo_seg", "role": "eval",
                                "derived_from": ["gbif_ca_2", "gbif_az", "gbif_nv", "gbif_or", "gbif_specimen_images"]},
    "rejected_pseudo_v1":      {"path": f"{B}/_rejected_pseudo_v1", "kind": "yolo_seg", "role": "negative",
                                "note": "v1 pseudo-labels marked barcodes/labels as insects; kept as a negative record"},
    "dataone_cib_raw":         {"path": f"{B}/dataone_cib", "kind": "tabular", "role": "source",
                                "note": "raw DataONE soil survey; contains observer PII -> never staged"},
    "essig":                   {"path": f"{R}/essig", "kind": "json", "role": "context"},
    "r3_ca":                   {"path": f"{B}/r3_ca", "kind": "yolo_seg", "role": "train",
                                "derived_from": ["gbif_ca_2", "gbif_specimen_images"],
                                "transform": "subset of pseudo_specimens_r3_real whose photo is byte-identical to a gbif_ca_2 / "
                                             "gbif_specimen_images photo; r3 labels, ruler truth and split kept (domain_split.py)"},
    "holdout_az":              {"path": f"{B}/holdout_az", "kind": "yolo_seg", "role": "domain_holdout",
                                "derived_from": ["gbif_az"],
                                "transform": "subset of pseudo_specimens_r3_real whose photo is byte-identical to a gbif_az photo; "
                                             "r3 labels + ruler truth, all photos in val (domain_split.py, 002 amendment 1)"},
    "holdout_nv":              {"path": f"{B}/holdout_nv", "kind": "yolo_seg", "role": "domain_holdout",
                                "derived_from": ["gbif_nv"],
                                "transform": "subset of pseudo_specimens_r3_real whose photo is byte-identical to a gbif_nv photo; "
                                             "r3 labels + ruler truth, all photos in val (domain_split.py, 002 amendment 1)"},
    "holdout_or":              {"path": f"{B}/holdout_or", "kind": "yolo_seg", "role": "domain_holdout",
                                "derived_from": ["gbif_or"],
                                "transform": "subset of pseudo_specimens_r3_real whose photo is byte-identical to a gbif_or photo; "
                                             "r3 labels + ruler truth, all photos in val (domain_split.py, 002 amendment 1)"},
}
PII_COLS = re.compile(r"observer|email|phone|recorded_?by|creator|editor|owner|author|surveyor|contact|user_?name", re.IGNORECASE)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")
FREE_TEXT_DROP = ("survey_comments", "location_notes", "habitat_notes")


def sha256_file(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def _leaf(rec):
    return hashlib.sha256(json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def pointer_manifest(root, role, skip=(".cache",)):
    root = Path(root)
    leaves = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix not in skip and not p.name.startswith("._") and p.name != ".DS_Store":
            leaves.append({"path": str(p.relative_to(root)), "sha256": sha256_file(p), "bytes": p.stat().st_size, "role": role})
    return leaves, (merkle_root([_leaf(l) for l in leaves]) if leaves else None)


def _img_ok(p):
    try:
        from PIL import Image
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            return im.size
    except Exception:  # noqa: BLE001 - fallback; the failure is recorded or degrades
        return None


def _poly_area(xy):
    x, y = xy[0::2], xy[1::2]
    return 0.5 * abs(sum(x[i] * y[(i + 1) % len(x)] - x[(i + 1) % len(x)] * y[i] for i in range(len(x))))


def check_raw(path, sha_by_path):
    root = Path(path)
    rows = [json.loads(l) for l in (root / "manifest.jsonl").read_text().splitlines() if l.strip()]
    bad_sha, missing, undecodable, lic = [], [], [], {}
    listed = set()
    for r in rows:
        rel = f"images/{r['file']}"
        listed.add(rel)
        if rel not in sha_by_path:
            missing.append(r["file"]); continue
        if r.get("sha256") and r["sha256"] != sha_by_path[rel]:
            bad_sha.append(r["file"])
        if _img_ok(root / rel) is None:
            undecodable.append(r["file"])
        l = (r.get("license") or "MISSING").rstrip("/").split("/")[-2:] if r.get("license") else ["MISSING"]
        lic["/".join(l)] = lic.get("/".join(l), 0) + 1
    unlisted = sorted(p for p in sha_by_path if p.startswith("images/") and p not in listed)
    ids = {"all": {Path(r["file"]).stem for r in rows if f"images/{r['file']}" in sha_by_path}}
    checks = {"manifest_rows": len(rows), "missing_files": len(missing), "sha_mismatch": len(bad_sha),
              "undecodable": len(undecodable), "unlisted_files": len(unlisted), "licences": lic,
              "licence_missing": lic.get("MISSING", 0)}
    fails = [k for k in ("missing_files", "sha_mismatch", "undecodable", "licence_missing") if checks[k]]
    return checks, fails, ids, {"examples": {"sha_mismatch": bad_sha[:5], "undecodable": undecodable[:5],
                                             "unlisted": unlisted[:5], "missing": missing[:5]}}


def check_yolo(path, sha_by_path):
    root = Path(path)
    splits = sorted({p.split("/")[1] for p in sha_by_path if p.startswith("images/") and p.count("/") >= 2})
    checks, ids, ex = {"splits": {}}, {}, {}
    bad_lines, unpaired, undecodable, empty = 0, 0, 0, 0
    by_sha = {}
    for sp in splits:
        imgs = sorted(p for p in sha_by_path if p.startswith(f"images/{sp}/") and Path(p).suffix.lower() in IMG)
        ids[sp] = set()
        n_obj = 0
        for rel in imgs:
            stem = Path(rel).stem
            ids[sp].add(stem)
            by_sha.setdefault(sha_by_path[rel], set()).add(sp)
            lab = root / "labels" / sp / f"{stem}.txt"
            if not lab.exists():
                unpaired += 1; ex.setdefault("unpaired", []).append(rel); continue
            if _img_ok(root / rel) is None:
                undecodable += 1; ex.setdefault("undecodable", []).append(rel)
            txt = lab.read_text().strip()
            if not txt:
                empty += 1; continue
            for line in txt.splitlines():
                parts = line.split()
                try:
                    c = int(parts[0]); xy = [float(v) for v in parts[1:]]
                    ok = c >= 0 and len(xy) >= 6 and len(xy) % 2 == 0 and all(0.0 <= v <= 1.0 for v in xy) and _poly_area(xy) > 0
                except Exception:  # noqa: BLE001 - fallback; the failure is recorded or degrades
                    ok = False
                if ok:
                    n_obj += 1
                else:
                    bad_lines += 1; ex.setdefault("bad_label", []).append(f"{lab.name}: {line[:60]}")
        labels = [p for p in sha_by_path if p.startswith(f"labels/{sp}/")]
        orphan = len({Path(p).stem for p in labels} - ids[sp])
        checks["splits"][sp] = {"images": len(imgs), "labels": len(labels), "objects": n_obj, "orphan_labels": orphan}
    cross = sum(1 for s in by_sha.values() if len(s) > 1)
    checks.update({"bad_label_lines": bad_lines, "unpaired_images": unpaired, "undecodable": undecodable,
                   "empty_labels": empty, "identical_bytes_across_splits": cross})
    fails = [k for k in ("bad_label_lines", "unpaired_images", "undecodable", "identical_bytes_across_splits") if checks[k]]
    if not splits:
        fails.append("no_splits")
    return checks, fails, ids, {"examples": {k: v[:5] for k, v in ex.items()}}


def check_tabular(path, sha_by_path):
    hits = {}
    for rel in sha_by_path:
        if not rel.endswith(".csv"):
            continue
        with open(Path(path) / rel, newline="", encoding="utf-8-sig", errors="replace") as f:
            rd = csv.DictReader(f)
            cols = rd.fieldnames or []
            pcols = [c for c in cols if PII_COLS.search(c)]
            em = ph = 0
            for row in rd:
                for v in row.values():
                    if isinstance(v, str):
                        em += bool(EMAIL.search(v)); ph += bool(PHONE.search(v))
            hits[rel] = {"pii_columns": pcols, "email_cells": em, "phone_cells": ph, "columns": len(cols)}
    pii = any(h["pii_columns"] or h["email_cells"] or h["phone_cells"] for h in hits.values())
    return {"files": hits, "pii_found": pii}, (["pii_present"] if pii else []), {}, {}


def check_json(path, sha_by_path):
    bad, rows = [], 0
    for rel in sha_by_path:
        try:
            if rel.endswith(".json"):
                json.loads((Path(path) / rel).read_text())
            elif rel.endswith(".jsonl"):
                for line in (Path(path) / rel).read_text().splitlines():
                    if line.strip():
                        json.loads(line); rows += 1
        except Exception:  # noqa: BLE001 - fallback; the failure is recorded or degrades
            bad.append(rel)
    return {"json_files": sum(r.endswith((".json", ".jsonl")) for r in sha_by_path), "jsonl_rows": rows,
            "unparseable": len(bad)}, \
        (["unparseable_json"] if bad else []), {}, {}


CHECKERS = {"raw_images": check_raw, "yolo_seg": check_yolo, "tabular": check_tabular, "json": check_json}


def verify_one(name, spec, out_dir):
    t = time.time()
    leaves, root = pointer_manifest(spec["path"], spec["role"])
    sha_by_path = {l["path"]: l["sha256"] for l in leaves}
    checks, fails, ids, extra = CHECKERS[spec["kind"]](spec["path"], sha_by_path)
    mdir = Path(out_dir) / "manifests"; mdir.mkdir(parents=True, exist_ok=True)
    (mdir / f"{name}.jsonl").write_text("".join(json.dumps(l, sort_keys=True) + "\n" for l in leaves))
    rec = {"dataset": name, "path": spec["path"], "kind": spec["kind"], "role": spec["role"],
           "files": len(leaves), "bytes": sum(l["bytes"] for l in leaves), "merkle_root": root,
           "checks": checks, "fails": fails, "derived_from": spec.get("derived_from"), "transform": spec.get("transform"),
           "synthetic": spec.get("synthetic", False), "note": spec.get("note"), **extra,
           "seconds": round(time.time() - t, 1)}
    return rec, ids


def lineage(results, ids):
    """Derived ids must exist in a declared source; derived splits must not
    cross source splits; global gbifID train/val leakage across datasets."""
    for name, rec in results.items():
        src = rec.get("derived_from")
        if not src:
            continue
        pool, src_split = set(), {}
        for s in src:
            for sp, st in ids.get(s, {}).items():
                pool |= st
                for x in st:
                    src_split.setdefault(x, set()).add(sp)
        mine = ids.get(name, {})
        all_mine = set().union(*mine.values()) if mine else set()
        orphan = sorted(all_mine - pool)
        crossed = []
        for sp, st in mine.items():
            for x in st:
                ss = src_split.get(x, set()) - {"all"}
                if ss and sp not in ss:
                    crossed.append(f"{x}:{sp}<-{'/'.join(sorted(ss))}")
        rec["lineage"] = {"derived_items": len(all_mine), "found_in_source": len(all_mine) - len(orphan),
                          "orphans": len(orphan), "orphan_examples": orphan[:5],
                          "split_crossings": len(crossed), "crossing_examples": crossed[:5]}
        if orphan:
            rec["fails"].append("lineage_orphans")
        if crossed:
            rec["fails"].append("lineage_split_crossing")
    # global: an id in train anywhere and in val anywhere (non-synthetic, non-negative)
    tr, va = {}, {}
    for name, rec in results.items():
        if rec["role"] in ("negative",) or rec.get("synthetic") or rec["kind"] != "yolo_seg":
            continue
        for sp, st in ids.get(name, {}).items():
            for x in st:
                (tr if sp == "train" else va).setdefault(x, set()).add(name)
    leak = sorted(set(tr) & set(va))
    return {"train_ids": len(tr), "val_ids": len(va), "train_val_overlap": len(leak),
            "overlap_examples": [f"{x}: train in {sorted(tr[x])}, val in {sorted(va[x])}" for x in leak[:8]]}


def verify(out_dir, names=None, ledger=None):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    results, ids = {}, {}
    prev = json.loads((out / "datasets.json").read_text())["datasets"] if names and (out / "datasets.json").exists() else {}
    for name, spec in REGISTRY.items():
        if names and name not in names:
            continue
        if not Path(spec["path"]).exists():
            results[name] = {"dataset": name, "path": spec["path"], "role": spec["role"], "kind": spec["kind"],
                             "fails": ["path_missing"], "status": "FAILED"}
            continue
        rec, i = verify_one(name, spec, out)
        results[name], ids[name] = rec, i
        print(f"[verify] {name}: {rec['files']} files, root {str(rec['merkle_root'])[:12]}, fails {rec['fails']} ({rec['seconds']}s)", flush=True)
    glob = lineage(results, ids) if not names else json.loads((out / "datasets.json").read_text())["global_leakage"]
    for name, rec in results.items():
        rec["status"] = ("REJECTED" if rec["role"] == "negative" else
                         "QUARANTINED_PII" if "pii_present" in rec.get("fails", []) else
                         "FAILED" if rec.get("fails") else "VERIFIED")
    results = {**prev, **results}                       # partial re-verify merges into the existing summary
    summary = {"schema": "baebugs.daisy.datasets.v1", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "datasets": results, "global_leakage": glob,
               "root": merkle_root(sorted(r["merkle_root"] for r in results.values() if r.get("merkle_root")))}
    (out / "datasets.json").write_text(json.dumps(summary, indent=1, default=list))
    if ledger is not None:
        for name, rec in results.items():
            ledger.append(f"dataset_{name}", {k: rec.get(k) for k in ("status", "merkle_root", "files", "bytes", "fails",
                                                                          "derived_from", "lineage")})
        ledger.append("datasets_root", {"root": summary["root"], "global_leakage": glob,
                                        "status": {n: r["status"] for n, r in results.items()}})
    return summary


# ------------------------------------------------------------- transforms

def transform_dataone(raw_dir, out_dir):
    """Public derivative of the DataONE soil survey: drop person/contact and
    free-text columns, then re-screen. Writes CSV + transform record."""
    raw = Path(raw_dir); out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    src = next(raw.glob("*.csv"))
    with open(src, newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f); cols = rd.fieldnames; rows = list(rd)
    drop = [c for c in cols if PII_COLS.search(c) or c in FREE_TEXT_DROP]
    keep = [c for c in cols if c not in drop]
    dst = out / "soil_sampling_survey_public_noPII.csv"
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keep); w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in keep})
    shutil.copy2(raw / "eml_latest.xml", out / "eml_latest.xml") if (raw / "eml_latest.xml").exists() else None
    rec = {"transform": "drop PII + free-text columns", "source_sha256": sha256_file(src), "source": src.name,
           "dropped_columns": drop, "kept_columns": len(keep), "rows": len(rows), "output_sha256": sha256_file(dst)}
    (out / "TRANSFORM.json").write_text(json.dumps(rec, indent=1))
    return rec


def toy_renders(out_dir, kg="print/fuse1/kg", ppms=(10, 20)):
    """Eval set with exact ground truth: every toy rendered top-down at known
    px/mm; label = silhouette polygon (YOLO-seg), truth = envelope, area, insect hash."""
    import cv2
    import numpy as np
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    from .insect_kg import insect_tree
    from .model_compare import render
    index = json.loads((Path(kg) / "index.json").read_text())
    out = Path(out_dir)
    truth = []
    for ppm in ppms:
        for sub in ("images", "labels"):
            (out / sub / f"ppm{ppm}").mkdir(parents=True, exist_ok=True)
        for x in index:
            img = render(x["length_mm"], x["plan"], ppm)
            _, root = insect_tree(x["length_mm"], x["plan"])
            m = root["_mesh"]; v = m.vertices; lo, hi = v.min(0), v.max(0); margin = 4.0
            tri = v[m.faces[m.face_normals[:, 2] > 1e-9]][:, :, :2]
            sil = unary_union([Polygon(t) for t in tri if Polygon(t).area > 1e-12])
            geoms = list(getattr(sil, "geoms", [sil]))
            H, W = img.shape[:2]
            lines = []
            for g in geoms:
                ext = np.asarray(g.exterior.coords)
                px = np.stack([(ext[:, 0] - lo[0] + margin) * ppm / W, (hi[1] - ext[:, 1] + margin) * ppm / H], 1)
                px = np.clip(px, 0, 1)
                if len(px) >= 3:
                    lines.append("0 " + " ".join(f"{a:.5f} {b:.5f}" for a, b in px))
            stem = x["name"]
            cv2.imwrite(str(out / "images" / f"ppm{ppm}" / f"{stem}.png"), img)
            (out / "labels" / f"ppm{ppm}" / f"{stem}.txt").write_text("\n".join(lines) + "\n")
            o = x["observation"]
            truth.append({"image": f"images/ppm{ppm}/{stem}.png", "px_per_mm": ppm, "insect_hash": x["insect_hash"],
                          "plan": x["plan"], "length_mm": x["length_mm"], "training_role": x.get("training_role"),
                          "envelope_mm": o["envelope_mm"], "top_area_mm2": o["top_area_mm2"],
                          "representation": "toy"})
    (out / "truth.json").write_text(json.dumps(truth, indent=1))
    (out / "data.yaml").write_text("path: .\nval: images/ppm10\ntest: images/ppm20\nnames:\n  0: specimen\n")
    return len(truth)


# ---------------------------------------------------------------- staging

BUNDLES = {
    "baebugs-daisy-train": ["pseudo_specimens_r3_real", "multires_mp_0.3", "multires_mp_1", "multires_mp_3",
                            "synth_1_30_r2", "synth_1_30_r3_real", "synth_seg"],
    "baebugs-daisy-eval": ["teacher_check", "teacher_check2", "toy_renders"],
    "baebugs-daisy-context": ["dataone_cib_public", "essig", "gbif_manifests"],
    "baebugs-daisy-toykg": ["toy_kg"],
    "baebugs-daisy-holdout": ["r3_ca", "holdout_az", "holdout_nv", "holdout_or"],
}


def stage(out_dir, user, summary=None, only=None):
    """Hardlink (same volume) or copy VERIFIED datasets into Kaggle bundles; each
    bundle carries datasets.json + every member's pointer manifest."""
    out = Path(out_dir)
    summary = summary or json.loads((out / "datasets.json").read_text())
    ds = summary["datasets"]
    staged = {}
    for bundle, members in BUNDLES.items():
        if only and bundle not in only:
            continue
        bdir = out / "kaggle" / bundle
        if bdir.exists():
            shutil.rmtree(bdir)
        bdir.mkdir(parents=True)
        included = []
        for name in members:
            rec = ds.get(name)
            if rec is None or rec["status"] != "VERIFIED":
                print(f"[stage] skip {name}: {rec and rec['status']}"); continue
            src = Path(rec["path"]); dst = bdir / name
            for l in (json.loads(x) for x in (out / "manifests" / f"{name}.jsonl").read_text().splitlines()):
                d = dst / l["path"]; d.parent.mkdir(parents=True, exist_ok=True)
                try:
                    os.link(src / l["path"], d)
                except OSError:
                    shutil.copy2(src / l["path"], d)
            shutil.copy2(out / "manifests" / f"{name}.jsonl", dst / "DAISY_POINTERS.jsonl")
            included.append(name)
        (bdir / "DAISY_DATASETS.json").write_text(json.dumps(
            {"bundle": bundle, "members": {n: {k: ds[n].get(k) for k in ("merkle_root", "files", "bytes", "status", "kind",
                                                                          "role", "derived_from", "transform", "lineage")}
                                           for n in included},
             "datasets_root": summary["root"], "representation_note": "toy_renders are TOY models, not replicas"}, indent=1))
        (bdir / "dataset-metadata.json").write_text(json.dumps(
            {"title": bundle, "id": f"{user}/{bundle}", "licenses": [{"name": "other"}],
             "subtitle": "baebugs DAISY-verified data (mixed source licences, see pointers)",
             "description": "Verified by baebugs.daisy_data: pointer manifests + Merkle roots per member. "
                            "Museum images: GBIF occurrence media under per-record licences (CC0 / CC BY / CC BY-NC, see "
                            "gbif manifests). PII removed from DataONE survey. Toy renders are parametric toys."}, indent=1))
        staged[bundle] = included
    return staged


def toy_kg_copy(out_dir, kg="print/fuse1/kg"):
    """The toy Merkle KG for AI evaluation on Kaggle: index, collection roots and
    every per-insect tree (no results). Verified tree-by-tree before copying."""
    from .insect_kg import verify_tree
    src, dst = Path(kg), Path(out_dir)
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "insects").mkdir(parents=True)
    bad = []
    for f in sorted((src / "insects").glob("*.json")):
        ok, where = verify_tree(json.loads(f.read_text())["nodes"])
        if not ok:
            bad.append((f.name, where))
        shutil.copy2(f, dst / "insects" / f.name)
    for name in ("index.json", "collection.json", "nodes.csv"):
        shutil.copy2(src / name, dst / name)
    if bad:
        raise SystemExit(f"toy KG trees fail verification: {bad[:5]}")
    return len(list((dst / "insects").glob("*.json")))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-daisy-data")
    ap.add_argument("cmd", choices=["verify", "transform-dataone", "toys", "gbif-manifests", "stage", "toy-kg"])
    ap.add_argument("--out", default="/Volumes/magicBLACKbox/baebugs/daisy")
    ap.add_argument("--only")
    ap.add_argument("--bundles", help="comma list: stage only these bundles")
    ap.add_argument("--kaggle-user", default="biobitworks")
    ap.add_argument("--ledger", action="store_true")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if a.cmd == "transform-dataone":
        print(transform_dataone(REGISTRY["dataone_cib_raw"]["path"], out / "derived" / "dataone_cib_public"))
    elif a.cmd == "toys":
        print(toy_renders(out / "derived" / "toy_renders"))
    elif a.cmd == "toy-kg":
        print(toy_kg_copy(out / "derived" / "toy_kg"))
    elif a.cmd == "gbif-manifests":
        d = out / "derived" / "gbif_manifests"; d.mkdir(parents=True, exist_ok=True)
        for n in ("gbif_ca_2", "gbif_az", "gbif_nv", "gbif_or", "gbif_specimen_images"):
            shutil.copy2(Path(REGISTRY[n]["path"]) / "manifest.jsonl", d / f"{n}.manifest.jsonl")
        print("copied")
    elif a.cmd == "verify":
        # derived outputs join the registry once they exist
        der = out / "derived"
        if (der / "dataone_cib_public").exists():
            REGISTRY["dataone_cib_public"] = {"path": str(der / "dataone_cib_public"), "kind": "tabular", "role": "context",
                                              "derived_from": None, "transform": "drop PII + free-text columns"}
        if (der / "toy_renders").exists():
            REGISTRY["toy_renders"] = {"path": str(der / "toy_renders"), "kind": "yolo_seg", "role": "eval",
                                       "synthetic": True, "transform": "insect_kg toys rendered top-down at 10/20 px/mm"}
        if (der / "toy_kg").exists():
            REGISTRY["toy_kg"] = {"path": str(der / "toy_kg"), "kind": "json", "role": "eval",
                                  "transform": "print/fuse1/kg copy (index, collection roots, per-insect Merkle trees)"}
        if (der / "gbif_manifests").exists():
            REGISTRY["gbif_manifests"] = {"path": str(der / "gbif_manifests"), "kind": "json", "role": "context"}
        led = None
        if a.ledger:
            from .git_ledger import GitLedger
            led = GitLedger("daisy_data", a.repo)
        s = verify(out, a.only.split(",") if a.only else None, led)
        print(json.dumps({n: (r["status"], r.get("fails")) for n, r in s["datasets"].items()}, indent=1))
        print("global leakage:", s["global_leakage"])
        print("datasets root:", s["root"])
    elif a.cmd == "stage":
        print(stage(out, a.kaggle_user, only=a.bundles.split(",") if a.bundles else None))


if __name__ == "__main__":
    main()
