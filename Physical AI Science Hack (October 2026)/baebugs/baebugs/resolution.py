"""Different megapixels: how sizing holds up as the camera gets worse/better.

Cameras on the bench differ (AmScope MD300A ~3 MP, BugPicker top camera,
phones ~12 MP, cheap USB scopes ~0.3 MP). `at_megapixels` resamples an image to
a target pixel count (area-preserving, aspect kept) and rescales px/mm, so the
same specimen can be measured at every resolution. `sweep` benchmarks a model
across MP levels; `leave_one_resolution_out` reports how each level does
relative to the others (which resolutions are the weak link). `build_multires`
writes resampled copies of a dataset for multi-resolution training.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import cv2
import numpy as np

MP_LEVELS = (0.3, 1.0, 3.0, 5.0, 12.0)


def at_megapixels(img, mp, px_per_mm=None):
    h, w = img.shape[:2]
    s = float(np.sqrt(mp * 1e6 / (h * w)))
    nh, nw = max(8, round(h * s)), max(8, round(w * s))
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
    out = cv2.resize(img, (nw, nh), interpolation=interp)
    return out, (px_per_mm * nw / w if px_per_mm else None), nw / w


def _scaled_truth(truth_json, mp, out_dir):
    """Resample every image in a truth file to `mp` megapixels; returns a new truth file."""
    src = Path(truth_json)
    root = src.parent
    out = Path(out_dir); (out / "images").mkdir(parents=True, exist_ok=True)
    recs = []
    for rec in json.loads(src.read_text()):
        img = cv2.imread(str(root / rec["image"]))
        if img is None:
            continue
        im2, ppm2, s = at_megapixels(img, mp, rec["px_per_mm"])
        name = Path(rec["image"]).name
        cv2.imwrite(str(out / "images" / name), im2, [cv2.IMWRITE_JPEG_QUALITY, 92])
        recs.append({**rec, "image": f"images/{name}", "px_per_mm": ppm2,
                     "objects": [{**o, "cx": o["cx"] * s, "cy": o["cy"] * s} for o in rec["objects"]]})
    tj = out / "truth.json"
    tj.write_text(json.dumps(recs))
    return tj


def sweep(weights, truth_json, work_dir, levels=MP_LEVELS, max_images=None):
    from .train import bench
    src = Path(truth_json)
    if max_images:
        sub = Path(work_dir) / "_subset.json"
        sub.parent.mkdir(parents=True, exist_ok=True)
        recs = json.loads(src.read_text())[:max_images]
        sub.write_text(json.dumps([{**r, "image": str((src.parent / r["image"]).resolve())} for r in recs]))
        src = sub
    res = {}
    for mp in levels:
        tj = _scaled_truth(src, mp, Path(work_dir) / f"mp_{mp:g}")
        res[f"{mp:g}MP"] = bench(weights, tj)
    return res


def leave_one_resolution_out(sweep_result, metric=("yolo", "median_wid_err")):
    """For each MP level: its error vs the mean of the OTHER levels (positive =
    worse than the rest). Identifies the resolution the model generalises worst to."""
    vals = {k: v.get(metric[0], {}).get(metric[1]) for k, v in sweep_result.items()}
    vals = {k: v for k, v in vals.items() if v is not None}
    out = {}
    for k, v in vals.items():
        others = [x for kk, x in vals.items() if kk != k]
        if others:
            out[k] = {"value": v, "others_mean": round(float(np.mean(others)), 4),
                      "delta": round(float(v - np.mean(others)), 4)}
    return out


def build_multires(data_yaml, out_dir, levels=(0.3, 1.0, 3.0)):
    """Resampled copies of a YOLO-seg dataset (labels are normalised, so they
    carry over unchanged). Returns data.yaml paths, one per level."""
    import yaml
    d = yaml.safe_load(Path(data_yaml).read_text())
    base = Path(d.get("path", Path(data_yaml).parent))
    outs = []
    for mp in levels:
        o = Path(out_dir) / f"mp_{mp:g}"
        for split in ("train", "val"):
            simg = base / d[split]
            (o / "images" / split).mkdir(parents=True, exist_ok=True)
            (o / "labels" / split).mkdir(parents=True, exist_ok=True)
            for p in sorted(Path(simg).glob("*.jpg")):
                img = cv2.imread(str(p))
                if img is None:
                    continue
                cv2.imwrite(str(o / "images" / split / p.name), at_megapixels(img, mp)[0],
                            [cv2.IMWRITE_JPEG_QUALITY, 90])
                lab = base / "labels" / split / f"{p.stem}.txt"
                if lab.exists():
                    shutil.copy(lab, o / "labels" / split / lab.name)
        (o / "data.yaml").write_text(f"path: {o.resolve()}\ntrain: images/train\nval: images/val\n"
                                     "names:\n  0: specimen\n")
        outs.append(o / "data.yaml")
    return outs
