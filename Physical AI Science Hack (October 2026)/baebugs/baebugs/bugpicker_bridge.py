"""Speak BioKEA BugPicker's file protocol (github.com/biokea/BugPicker).

BugPicker coordinates through files, not sockets: a scan dir holds
`manifest.jsonl` (one record per frame) and `objects.jsonl` (one per detection).
Its manifest already carries `tray_size_class` and `sorting_tray_slot` - the
exact hand-off from BugSorter (step 1) to BugPicker (step 3). baebugs fills
those from the sieve plan, and can also import BugPicker's own detections as a
measurement source next to YOLO and classical morphometrics.
"""
from __future__ import annotations

import json
from pathlib import Path

from .measure import Measurement

COORDINATE_TRANSFORM_VERSION = "image_y_inverted_v2"  # matches BugPicker


def _write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def manifest_record(file_name, frame_index, px_per_mm, image_shape,
                    tray_size_class, sorting_tray_slot=1, camera="Top",
                    x_mm=None, y_mm=None, **extra):
    h, w = image_shape[:2]
    rec = {"file_name": str(file_name), "frame_index": frame_index, "camera": camera,
           "image_width_px": int(w), "image_height_px": int(h),
           "units_per_pixel_x_mm": 1.0 / px_per_mm,
           "units_per_pixel_y_mm": 1.0 / px_per_mm,
           "sorting_tray_slot": sorting_tray_slot, "collection_event_slot": 1,
           "plate_slot": 1, "recovery_slot": 1, "tray_size_class": tray_size_class}
    if x_mm is not None:
        rec.update(x_mm=x_mm, y_mm=y_mm)
    rec.update(extra)
    return rec


def object_records(ms: list[Measurement], frame: dict, start_index=0):
    upp = frame["units_per_pixel_x_mm"]
    out = []
    for i, m in enumerate(ms):
        long_px, short_px = m.length_mm / upp, m.width_mm / upp
        out.append({
            "object_index": start_index + i, "frame_index": frame["frame_index"],
            "camera": frame.get("camera", "Top"), "source_file": frame["file_name"],
            "centroid_x_px": m.cx, "centroid_y_px": m.cy,
            "rect_long_side_px": long_px, "rect_short_side_px": short_px,
            "aspect_ratio": short_px / max(long_px, 1e-9),
            "image_width_px": frame.get("image_width_px"),
            "image_height_px": frame.get("image_height_px"),
            "units_per_pixel_x_mm": upp,
            "units_per_pixel_y_mm": frame["units_per_pixel_y_mm"],
            "tray_size_class": frame["tray_size_class"],
            "sorting_tray_slot": frame["sorting_tray_slot"],
            "detector": "baebugs", "detection_method": m.source,
            "is_duplicate": False, "score": m.conf,
            "coordinate_transform_version": COORDINATE_TRANSFORM_VERSION,
            # baebugs extras (BugPicker ignores unknown keys)
            "length_mm": m.length_mm, "width_mm": m.width_mm,
            "area_mm2": m.area_mm2, "flag": m.flag,
        })
    return out


def write_scan(scan_dir, frames: list[dict], objects: list[dict]):
    scan_dir = Path(scan_dir)
    _write_jsonl(scan_dir / "manifest.jsonl", frames)
    _write_jsonl(scan_dir / "objects.jsonl", objects)
    return scan_dir


def export_yolo(scan_dir, out_dir, class_of=lambda r: 0, class_names=("insect",),
                val_every=5):
    """Fast training path: turn a BugPicker scan (frames + objects.jsonl) into a
    YOLO detection dataset, so YOLO can be fine-tuned on real tray images in
    minutes (e.g. `yolo train data=out_dir/data.yaml model=yolo11n.pt epochs=30`).
    `class_of` maps an object record to a class id (e.g. by tray_size_class or
    an Essig family from the specimen-context FCO)."""
    import shutil
    scan_dir, out_dir = Path(scan_dir), Path(out_dir)
    rows = [json.loads(l) for l in (scan_dir / "objects.jsonl").read_text().splitlines() if l.strip()]
    by_frame: dict[str, list] = {}
    for r in rows:
        if not r.get("is_duplicate"):
            by_frame.setdefault(r["source_file"], []).append(r)
    for i, (frame, objs) in enumerate(sorted(by_frame.items())):
        split = "val" if i % val_every == val_every - 1 else "train"
        (out_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_dir / "labels" / split).mkdir(parents=True, exist_ok=True)
        src = scan_dir / frame
        stem = Path(frame).stem
        if src.exists():
            shutil.copy(src, out_dir / "images" / split / src.name)
        lines = []
        for r in objs:
            W, H = r.get("image_width_px"), r.get("image_height_px")
            if not W or not H:
                continue
            if "bbox_x_px" in r:
                x, y, w, h = r["bbox_x_px"], r["bbox_y_px"], r["bbox_width_px"], r["bbox_height_px"]
                cx, cy = x + w / 2, y + h / 2
            else:  # baebugs records: axis-aligned box from rect sides (orientation unknown)
                s = max(r["rect_long_side_px"], r["rect_short_side_px"])
                cx, cy, w, h = r["centroid_x_px"], r["centroid_y_px"], s, s
            lines.append(f"{class_of(r)} {cx / W:.6f} {cy / H:.6f} {w / W:.6f} {h / H:.6f}")
        (out_dir / "labels" / split / f"{stem}.txt").write_text("\n".join(lines) + "\n")
    (out_dir / "data.yaml").write_text(
        f"path: {out_dir.resolve()}\ntrain: images/train\nval: images/val\n"
        f"names: {json.dumps(dict(enumerate(class_names)))}\n")
    return out_dir


def read_bugpicker_objects(path) -> list[Measurement]:
    """Import a BugPicker objects.jsonl as Measurements (skips duplicates)."""
    out = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("is_duplicate"):
            continue
        ux = r.get("units_per_pixel_x_mm") or 1.0
        out.append(Measurement(
            r.get("centroid_x_px", 0.0), r.get("centroid_y_px", 0.0),
            r.get("rect_long_side_px", 0.0) * ux, r.get("rect_short_side_px", 0.0) * ux,
            r.get("rect_area_px", r.get("bbox_area_px", 0.0)) * ux * ux,
            "bugpicker", float(r.get("score", 1.0)) if r.get("score") else 1.0))
    return out
