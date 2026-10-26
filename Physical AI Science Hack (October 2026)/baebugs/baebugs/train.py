"""Train / fine-tune the YOLO sizer locally (Apple MPS, CUDA or CPU) and
benchmark sizing against ground truth.

  baebugs-train synth   --root /Volumes/magicLABbox/baebugs            # build synthetic set
  baebugs-train fit     --data <dir>/data.yaml --epochs 40               # train
  baebugs-train bench   --weights best.pt --truth <dir>/truth_val.json   # mm accuracy
  baebugs-train export-bugpicker --scan <scan_dir> --out <yolo_dir>      # real-data path
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np

DEFAULT_ROOT = os.environ.get("BAEBUGS_ROOT", "/Volumes/magicLABbox/baebugs")


def device():
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return 0
    except Exception:  # noqa: BLE001,S110 - best-effort, nothing to record
        pass
    return "cpu"


def fit(data, model="yolo11n-seg.pt", epochs=40, imgsz=640, batch=16, project=None,
        name="baebugs-seg", ledger=None, **kw):
    """Train; with a GitLedger, every epoch is a Merkle break point that is
    committed and pushed (metrics + sha256 of last/best weights)."""
    from ultralytics import YOLO
    project = project or str(Path(DEFAULT_ROOT) / "runs")
    m = YOLO(model)
    if ledger is not None:
        from .git_ledger import yolo_epoch_callback
        m.add_callback("on_fit_epoch_end", yolo_epoch_callback(ledger))
        ledger.append("fit_start", {"data": str(data), "model": str(model), "epochs": epochs,
                                    "imgsz": imgsz, "batch": batch, "device": str(device())},
                      files={"init_weights": model} if Path(str(model)).exists() else None)
    m.train(data=str(data), epochs=epochs, imgsz=imgsz, batch=batch, device=device(),
            project=project, name=name, exist_ok=True, plots=True, verbose=False,
            mosaic=0.5, degrees=180, flipud=0.5, fliplr=0.5, **kw)
    best = Path(project) / name / "weights" / "best.pt"
    if ledger is not None:
        ledger.append("fit_end", {"best": str(best)}, files={"best.pt": best})
    return best


def bench(weights, truth_json, max_images=None, match_mm=1.0):
    """Median relative length/width error and recall for YOLO, classical, and
    their consensus, against synthetic ground truth."""
    from .measure import YoloMeasurer, classical_measure, consensus
    truth = json.loads(Path(truth_json).read_text())[:max_images]
    root = Path(truth_json).parent
    yolo = YoloMeasurer(str(weights), conf=0.25) if weights else None
    stats = {k: {"L": [], "W": [], "found": 0} for k in ("yolo", "classical", "consensus")}
    n_true = 0
    for rec in truth:
        img = cv2.imread(str(root / rec["image"]))
        ppm = rec["px_per_mm"]
        sets = {"classical": classical_measure(img, ppm)}
        if yolo:
            sets["yolo"] = yolo(img, ppm)
            sets["consensus"] = [m for m in consensus(list(sets["yolo"]), list(sets["classical"]), ppm)
                                 if m.flag is None]
        for t in rec["objects"]:
            n_true += 1
            for k, ms in sets.items():
                if not ms:
                    continue
                d = [np.hypot(m.cx - t["cx"], m.cy - t["cy"]) for m in ms]
                i = int(np.argmin(d))
                if d[i] < match_mm * ppm:
                    stats[k]["found"] += 1
                    stats[k]["L"].append(abs(ms[i].length_mm / t["length_mm"] - 1))
                    stats[k]["W"].append(abs(ms[i].width_mm / t["width_mm"] - 1))
    out = {}
    for k, s in stats.items():
        if s["found"]:
            out[k] = {"recall": round(s["found"] / n_true, 3),
                      "median_len_err": round(float(np.median(s["L"])), 4),
                      "median_wid_err": round(float(np.median(s["W"])), 4),
                      "p90_wid_err": round(float(np.percentile(s["W"], 90)), 4)}
    out["n_true"] = n_true
    return out


def pseudo_label(images_dir, weights, out_dir, conf=0.5, val_every=6, max_images=None,
                 px_per_mm=40.0, imgsz=640):
    """Semi-supervised step for real photos without outlines (e.g. pulled GBIF
    specimen images): keep only YOLO masks that the classical sizer independently
    agrees with (consensus, no flag) and write them as YOLO-seg labels. Two
    methods that fail differently must agree before a label is trusted.
    px_per_mm only matters for the agreement tolerance; real scale isn't needed."""
    import shutil

    from ultralytics import YOLO

    from .measure import _from_contour, classical_measure, consensus
    out = Path(out_dir)
    model = YOLO(str(weights))
    paths = sorted(Path(images_dir).glob("*.jpg"))[:max_images]
    kept = total = 0
    for i, p in enumerate(paths):
        img = cv2.imread(str(p))
        if img is None:
            continue
        h, w = img.shape[:2]
        res = model.predict(img, conf=conf, imgsz=imgsz, verbose=False, device=device())[0]
        if res.masks is None:
            continue
        polys = [np.asarray(xy, np.float32) for xy in res.masks.xy if len(xy) >= 3]
        ys = [_from_contour(pp.reshape(-1, 1, 2), px_per_mm, "yolo") for pp in polys]
        agreed = consensus(list(ys), classical_measure(img, px_per_mm), px_per_mm)
        ok = {(round(m.cx), round(m.cy)) for m in agreed if m.flag is None and m.source == "consensus"}
        lines = []
        for pp, m in zip(polys, ys):
            total += 1
            if any(abs(m.cx - x) < 0.5 * px_per_mm and abs(m.cy - y) < 0.5 * px_per_mm for x, y in ok):
                kept += 1
                lines.append("0 " + " ".join(f"{x / w:.5f} {y / h:.5f}" for x, y in pp))
        if not lines:
            continue
        split = "val" if i % val_every == val_every - 1 else "train"
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
        shutil.copy(p, out / "images" / split / p.name)
        (out / "labels" / split / f"{p.stem}.txt").write_text("\n".join(lines) + "\n")
    (out / "data.yaml").write_text(f"path: {out.resolve()}\ntrain: images/train\nval: images/val\n"
                                   "names:\n  0: specimen\n")
    return {"images": len(paths), "masks": total, "kept": kept, "data": str(out / "data.yaml")}


def pseudo_label_specimens(image_dirs, out_dir, min_ruler_conf=0.4, max_objects=6,
                           length_range=(1.0, 30.0), val_every=6, max_images=None,
                           preview_n=12, teacher="yoloe"):
    """Teacher for museum specimen photos (grey stage + ruler): real px/mm from
    the ruler, specimens segmented on the stage only (labels/barcodes/ruler
    excluded). Writes YOLO-seg labels AND truth_real.json with sizes in mm
    (teacher-derived 'silver' truth for benchmarking on real photos)."""
    import shutil

    from .specimen_photo import preview, ruler_px_per_mm, segment, segment_yoloe
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    paths = [p for d in image_dirs for p in sorted(Path(d).glob("*.jpg"))][:max_images]
    stats = {"images": len(paths), "no_ruler": 0, "rejected": 0, "kept_images": 0, "objects": 0}
    truth, previews = {"train": [], "val": []}, []
    for i, p in enumerate(paths):
        img = cv2.imread(str(p))
        if img is None:
            continue
        ppm, conf = ruler_px_per_mm(img)
        if not ppm or conf < min_ruler_conf:
            stats["no_ruler"] += 1; continue
        polys, ms = (segment_yoloe(img, ppm, length_range=length_range) if teacher == "yoloe"
                     else segment(img, ppm))
        keep = [(pp, m) for pp, m in zip(polys, ms) if length_range[0] <= m.length_mm <= length_range[1]]
        if not keep or len(keep) > max_objects:
            stats["rejected"] += 1; continue
        h, w = img.shape[:2]
        split = "val" if i % val_every == val_every - 1 else "train"
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
        shutil.copy(p, out / "images" / split / p.name)
        (out / "labels" / split / f"{p.stem}.txt").write_text("\n".join(
            "0 " + " ".join(f"{x / w:.5f} {y / h:.5f}" for x, y in pp) for pp, _ in keep) + "\n")
        truth[split].append({"image": f"images/{split}/{p.name}", "px_per_mm": ppm, "ruler_conf": conf,
                             "objects": [{"cx": m.cx, "cy": m.cy, "length_mm": m.length_mm,
                                          "width_mm": m.width_mm} for _, m in keep]})
        stats["kept_images"] += 1; stats["objects"] += len(keep)
        if len(previews) < preview_n:
            previews.append(preview(img, [pp for pp, _ in keep], [m for _, m in keep], ppm, conf))
    for split, rows in truth.items():
        (out / f"truth_real_{split}.json").write_text(json.dumps(rows))
    (out / "data.yaml").write_text(f"path: {out.resolve()}\ntrain: images/train\nval: images/val\n"
                                   "names:\n  0: specimen\n")
    if previews:
        tiles = [cv2.resize(v, (480, int(480 * v.shape[0] / v.shape[1]))) for v in previews]
        hmax = max(t.shape[0] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255,) * 3) for t in tiles]
        while len(tiles) % 3: tiles.append(np.full_like(tiles[0], 255))
        cv2.imwrite(str(out / "preview.jpg"), np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]))
    widths = [o["width_mm"] for t in truth["train"] + truth["val"] for o in t["objects"]]
    if widths:
        stats["width_mm_p10_p50_p90"] = [round(float(np.percentile(widths, q)), 2) for q in (10, 50, 90)]
    return stats


def mix(data_yamls, out_yaml):
    """Combine several YOLO datasets (e.g. synthetic + pseudo-labelled real) into
    one data.yaml so fine-tuning keeps what earlier data taught (no forgetting)."""
    import yaml
    tr, va = [], []
    for y in data_yamls:
        d = yaml.safe_load(Path(y).read_text())
        base = Path(d.get("path", Path(y).parent))
        tr.append(str(base / d["train"])); va.append(str(base / d["val"]))
    Path(out_yaml).parent.mkdir(parents=True, exist_ok=True)
    Path(out_yaml).write_text(yaml.safe_dump({"train": tr, "val": va, "names": {0: "specimen"}}))
    return out_yaml


def main(argv=None):
    ap = argparse.ArgumentParser("baebugs-train")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("synth"); s.add_argument("--root", default=DEFAULT_ROOT)
    s.add_argument("--n-train", type=int, default=300); s.add_argument("--n-val", type=int, default=60)
    f = sub.add_parser("fit"); f.add_argument("--data", required=True)
    f.add_argument("--model", default="yolo11n-seg.pt"); f.add_argument("--epochs", type=int, default=40)
    f.add_argument("--batch", type=int, default=16)
    b = sub.add_parser("bench"); b.add_argument("--weights"); b.add_argument("--truth", required=True)
    b.add_argument("--max-images", type=int)
    e = sub.add_parser("export-bugpicker"); e.add_argument("--scan", required=True)
    e.add_argument("--out", required=True)
    mx = sub.add_parser("mix"); mx.add_argument("--data", nargs="+", required=True)
    mx.add_argument("--out", required=True)
    f.add_argument("--project"); f.add_argument("--name", default="baebugs-seg")
    f.add_argument("--imgsz", type=int, default=640)
    ps = sub.add_parser("pseudo-specimens"); ps.add_argument("--images", nargs="+", required=True)
    ps.add_argument("--out", required=True); ps.add_argument("--max-images", type=int)
    ps.add_argument("--teacher", default="yoloe", choices=["yoloe", "classical"])
    pl = sub.add_parser("pseudo-label"); pl.add_argument("--images", required=True)
    pl.add_argument("--weights", required=True); pl.add_argument("--out", required=True)
    pl.add_argument("--conf", type=float, default=0.5); pl.add_argument("--max-images", type=int)
    a = ap.parse_args(argv)
    if a.cmd == "pseudo-specimens":
        print(json.dumps(pseudo_label_specimens(a.images, a.out, max_images=a.max_images, teacher=a.teacher), indent=2)); return
    if a.cmd == "mix":
        print(mix(a.data, a.out)); return
    if a.cmd == "pseudo-label":
        print(json.dumps(pseudo_label(a.images, a.weights, a.out, a.conf, max_images=a.max_images), indent=2))
        return
    if a.cmd == "synth":
        from .synth_seg import build_dataset
        print(build_dataset(Path(a.root) / "datasets" / "synth_seg", a.n_train, a.n_val))
    elif a.cmd == "fit":
        print(fit(a.data, a.model, a.epochs, imgsz=a.imgsz, batch=a.batch, project=a.project, name=a.name))
    elif a.cmd == "bench":
        print(json.dumps(bench(a.weights, a.truth, a.max_images), indent=2))
    else:
        from .bugpicker_bridge import export_yolo
        print(export_yolo(a.scan, a.out))


if __name__ == "__main__":
    main()
