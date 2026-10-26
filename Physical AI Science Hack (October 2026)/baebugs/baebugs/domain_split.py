"""DAISY-BB-002 (amendment 1; identity rule widened by amendment 2 / 002a): split pseudo_specimens_r3_real by source collection.

Each r3 photo is traced to the GBIF collection it was copied from: its filename must exist in
<source>/images and the sha256 must match (byte identity), otherwise it is dropped as
unresolved. Labels and ruler truth are carried over unchanged (same teacher as r3).
  r3_ca          photos from gbif_ca_2 / gbif_specimen_images, original train/val split kept
  holdout_<st>   photos from gbif_<st>; all go to val (evaluation only)
Files are hardlinked when on the same volume. A report with per-set counts is written.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .retention import sha

DATASETS = "/Volumes/magicBLACKbox/baebugs/datasets"
SOURCES = {"ca": ["{D}/gbif_ca_2", "/Volumes/magicLABbox/baebugs/datasets/gbif_specimen_images"],
           "az": ["{D}/gbif_az"], "nv": ["{D}/gbif_nv"], "or": ["{D}/gbif_or"]}


def _img_dir(src):
    p = Path(src)
    return p / "images" if (p / "images").is_dir() else p


def _link(a, b):
    b.parent.mkdir(parents=True, exist_ok=True)
    if b.exists():
        b.unlink()
    try:
        os.link(a, b)
    except OSError:
        shutil.copy2(a, b)


def _pixel_diff(a, b):
    import cv2
    import numpy as np
    x, y = cv2.imread(str(a)), cv2.imread(str(b))
    if x is None or y is None or x.shape != y.shape:
        return None
    return float(np.abs(x.astype(np.int16) - y.astype(np.int16)).mean())


def source_of(img, srcs, max_diff=4.0):
    """(state, rule, diff): rule 'bytes' (sha identical) or 'media_id_pixels' (amendment 2: same media id,
    same dimensions, mean abs pixel diff <= max_diff); (None, reason, None) if unresolved/ambiguous."""
    h = sha(img)
    cands = [(st, _img_dir(d) / img.name) for st, dirs in srcs.items() for d in dirs if (_img_dir(d) / img.name).exists()]
    for st, c in cands:
        if sha(c) == h:
            return st, "bytes", 0.0
    states = {st for st, _ in cands}
    if len(states) != 1:
        return None, ("ambiguous_states" if states else "no_media_id_match"), None
    st, c = cands[0]
    d = _pixel_diff(img, c)
    if d is not None and d <= max_diff:
        return st, "media_id_pixels", round(d, 3)
    return None, "pixels_differ" if d is not None else "shape_differs", d


def build(datasets=DATASETS):
    D = Path(datasets); r3 = D / "pseudo_specimens_r3_real"
    srcs = {st: [s.format(D=D) for s in v] for st, v in SOURCES.items()}
    outs = {"ca": D / "r3_ca", **{st: D / f"holdout_{st}" for st in ("az", "nv", "or")}}
    for o in outs.values():
        if o.exists():
            shutil.rmtree(o)
    truth = {sp: json.loads((r3 / f"truth_real_{sp}.json").read_text()) for sp in ("train", "val")}
    tby = {sp: {Path(t["image"]).name: t for t in truth[sp]} for sp in truth}
    new_truth = {k: {"train": [], "val": []} for k in outs}
    rep = {k: {"train": 0, "val": 0} for k in outs}; rep["unresolved"] = []
    for sp in ("train", "val"):
        for img in sorted((r3 / "images" / sp).glob("*.jpg")):
            st, rule, diff = source_of(img, srcs)
            rep.setdefault("rules", {}).setdefault(rule, 0); rep["rules"][rule] += 1
            if st is None:
                rep["unresolved"].append(f"{sp}/{img.name}:{rule}"); continue
            if rule != "bytes":
                rep.setdefault("pixel_matches", []).append({"photo": img.name, "state": st, "mean_abs_diff": diff})
            dsp = sp if st == "ca" else "val"
            o = outs[st]
            _link(img, o / "images" / dsp / img.name)
            lab = r3 / "labels" / sp / f"{img.stem}.txt"
            if lab.exists():
                _link(lab, o / "labels" / dsp / lab.name)
            if img.name in tby[sp]:
                t = dict(tby[sp][img.name]); t["image"] = f"images/{dsp}/{img.name}"
                new_truth[st][dsp].append(t)
            rep[st][dsp] += 1
    for st, o in outs.items():
        o.mkdir(parents=True, exist_ok=True)
        (o / "images" / "train").mkdir(parents=True, exist_ok=True)
        for sp in ("train", "val"):
            (o / f"truth_real_{sp}.json").write_text(json.dumps(new_truth[st][sp]))
        (o / "data.yaml").write_text(f"path: {o}\ntrain: images/train\nval: images/val\nnames:\n  0: specimen\n")
        (o / "SPLIT_REPORT.json").write_text(json.dumps({"set": o.name, "source_state": st, **rep[st],
                                                          "from": "pseudo_specimens_r3_real"}, indent=1))
    rep["n_unresolved"] = len(rep["unresolved"]); rep["unresolved"] = rep["unresolved"][:20]
    pm = rep.get("pixel_matches", [])
    rep["pixel_match_summary"] = {"n": len(pm), "max_mean_abs_diff": max((x["mean_abs_diff"] for x in pm), default=None)}
    (D / "domain_split_pixel_matches.json").write_text(json.dumps(pm, indent=1))
    rep.pop("pixel_matches", None)
    (D / "domain_split_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "unresolved"}))
    return rep


if __name__ == "__main__":
    build()
