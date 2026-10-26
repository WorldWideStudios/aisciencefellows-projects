"""Novel-insect test with food analogs that are in NO insect database.

Expectation: none of the analogs should come out KNOWN. A confident detection
outside the database's size/shape range is NOVEL (VIP); something the insect
teacher doesn't recognise is UNKNOWN. Anything marked KNOWN is a miss the
human-review lane would let through.

Per photo:
  1. scale  - ruler px/mm; for tilted photos a LOCAL scale: the mm-tick period is
              measured in short windows along the ruler and fitted against position,
              so each object gets the px/mm at its own height (perspective).
  2. objects- analogs found with YOLOE prompted for grains/seeds/pasta (reference list).
  3. system - the production path: trained student (YOLO) + zero-shot 'insect'
              teacher (YOLOE) -> consensus -> triage vs the database reference.
  4. join   - every analog object gets the system's verdict (known/unknown/novel/missed)
              and a real mm size, which replaces the estimates table.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


def _ac_period(prof, lo=2.0, hi=40.0):
    prof = prof - np.convolve(prof, np.ones(41) / 41, mode="same")
    n = len(prof)
    f = np.fft.rfft(prof, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    ac = ac / (ac[0] + 1e-9)
    a, b = int(lo), min(int(hi) + 2, n - 2)
    seg = ac[a:b]
    if seg.size < 3:
        return None, 0.0
    pk = [i for i in range(1, len(seg) - 1) if seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1] and seg[i] > 0.5 * seg.max()]
    if not pk:
        return None, 0.0
    i = pk[0]
    p, q, r = seg[i - 1], seg[i], seg[i + 1]
    return a + i + 0.5 * (p - r) / (p - 2 * q + r + 1e-9), float(q)


def local_ruler_scale(img, win=260, step=130):
    """Find the ruler's tick edges (vertical or horizontal), measure the tick
    period in sliding windows along each, keep the FINER edge (mm, not 1/16 in),
    and fit period = a + b*position. Returns (ppm_at(pos) callable, axis, diag)."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    best = None
    for axis, reg in (("y", g.T), ("x", g)):   # axis = image axis the ruler runs along
        energy = np.abs(np.diff(reg, axis=1)).mean(axis=1)
        order = np.argsort(energy)[::-1]
        bands = []
        for c in order:
            if all(abs(c - b) > 12 for b in bands):
                bands.append(int(c))
            if len(bands) >= 4:
                break
        for c in bands:
            pos, per, q = [], [], []
            for s in range(0, reg.shape[1] - win, step):
                prof = reg[max(0, c - 2):c + 3, s:s + win].mean(axis=0)
                p, conf = _ac_period(prof)
                if p and conf > 0.3:
                    pos.append(s + win / 2); per.append(p); q.append(conf)
            if len(per) < 4:
                continue
            pos, per = np.array(pos), np.array(per)
            b, a = np.polyfit(pos, per, 1)
            resid = np.abs(per - (a + b * pos))
            keep = resid < max(0.6, 2.5 * np.median(resid))
            if keep.sum() >= 4:
                b, a = np.polyfit(pos[keep], per[keep], 1)
            fit_err = float(np.median(np.abs(per[keep] - (a + b * pos[keep]))) / np.median(per[keep]))
            cand = {"axis": axis, "band": c, "a": float(a), "b": float(b), "n": int(keep.sum()),
                    "median_period": float(np.median(per[keep])), "fit_rel_err": round(fit_err, 4),
                    "mean_conf": round(float(np.mean(q)), 3)}
            # prefer many consistent windows, then the finer period (mm over 1/16 inch)
            score = (cand["n"] >= 6, -fit_err > -0.08, -cand["median_period"])
            if best is None or score > best[0]:
                best = (score, cand)
    if best is None:
        return None, None, {}
    c = best[1]
    return (lambda pos: c["a"] + c["b"] * pos), c["axis"], c


def find_dishes(img, min_r_frac=0.05, max_r_frac=0.35):
    """Petri dishes as circles (Hough on a downscaled grey image)."""
    h, w = img.shape[:2]
    s = 800 / max(h, w)
    g = cv2.medianBlur(cv2.cvtColor(cv2.resize(img, None, fx=s, fy=s), cv2.COLOR_BGR2GRAY), 5)
    c = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT, dp=1.2, minDist=int(min_r_frac * 800 * 2.2),
                         param1=120, param2=45, minRadius=int(min_r_frac * 800), maxRadius=int(max_r_frac * 800))
    if c is None:
        return []
    out = []
    for x, y, r in c[0]:
        out.append((x / s, y / s, r / s))
    # real dishes share one size: keep circles near the most common radius
    rs = np.array([t[2] for t in out])
    best_n, best_r = 0, None
    for r0 in rs:
        n = int((np.abs(rs - r0) < 0.15 * r0).sum())
        if n > best_n or (n == best_n and best_r is not None and r0 < best_r):
            best_n, best_r = n, r0
    out = [t for t in out if abs(t[2] - best_r) < 0.25 * best_r]
    # drop circles mostly inside a bigger one (inner rim of the same dish)
    out.sort(key=lambda t: -t[2])
    keep = []
    for x, y, r in out:
        if all(np.hypot(x - X, y - Y) > 0.6 * R for X, Y, R in keep):
            keep.append((x, y, r))
    return keep


def dish_objects(img, ppm_at=None, axis="y", dev=32, sat_dev=40, min_area_px=12, ref_ppm=10.0):
    """Model-free reference list: inside each dish (inner 88% of its radius, away
    from the rim), pixels that differ from the dish's own background colour
    (darker, lighter or more/less saturated) are objects."""
    from .measure import _from_contour
    dishes = find_dishes(img)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.int32)
    h, w = img.shape[:2]
    polys, objs, dish_of = [], [], []
    for di, (x, y, r) in enumerate(dishes):
        m = np.zeros((h, w), np.uint8)
        cv2.circle(m, (int(x), int(y)), int(r * 0.88), 1, -1)
        inner = m.astype(bool)
        if inner.sum() < 100:
            continue
        bgL = np.median(lab[..., 0][inner]); bga = np.median(lab[..., 1][inner]); bgb = np.median(lab[..., 2][inner])
        d = np.sqrt((lab[..., 0] - bgL) ** 2 + 2 * (lab[..., 1] - bga) ** 2 + 2 * (lab[..., 2] - bgb) ** 2)
        fg = ((d > dev) & inner).astype(np.uint8) * 255
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cnts:
            if cv2.contourArea(c) < min_area_px:
                continue
            M = cv2.moments(c); cy = M["m01"] / (M["m00"] + 1e-9); cx = M["m10"] / (M["m00"] + 1e-9)
            ppm = ppm_at(cy if axis == "y" else cx) if ppm_at else ref_ppm
            polys.append(c.reshape(-1, 2)); objs.append(_from_contour(c, ppm, "dish_classical")); dish_of.append(di)
    return dishes, polys, objs, dish_of


def fastsam_objects(img, dishes, ppm_at=None, axis="y", ref_ppm=10.0, weights="FastSAM-s.pt",
                    imgsz=1536, min_area_mm2=0.3, max_area_mm2=400):
    """Reference list from FastSAM (segment-anything, no notion of 'insect' or
    'food'): every mask whose centre lies inside a dish's inner 88% and whose
    area is object-sized; measured with the local ruler scale."""
    from ultralytics import FastSAM

    from .measure import _from_contour
    res = FastSAM(weights).predict(img, imgsz=imgsz, retina_masks=True, conf=0.25, iou=0.7, verbose=False)[0]
    if res.masks is None:
        return [], [], []
    polys, objs, dish_of = [], [], []
    for xy in res.masks.xy:
        if len(xy) < 3:
            continue
        c = np.asarray(xy, np.float32).reshape(-1, 1, 2)
        M = cv2.moments(c); cx = M["m10"] / (M["m00"] + 1e-9); cy = M["m01"] / (M["m00"] + 1e-9)
        di = next((i for i, (x, y, r) in enumerate(dishes) if np.hypot(cx - x, cy - y) < 0.88 * r), None)
        if di is None:
            continue
        ppm = ppm_at(cy if axis == "y" else cx) if ppm_at else ref_ppm
        o = _from_contour(c, ppm, "fastsam")
        if not (min_area_mm2 <= o.area_mm2 <= max_area_mm2):
            continue
        x, y, r = dishes[di]
        if np.hypot(cx - x, cy - y) + 0.5 * o.length_mm * ppm > 0.92 * r:
            continue                                  # touches the rim
        polys.append(c.reshape(-1, 2)); objs.append(o); dish_of.append(di)
    return polys, objs, dish_of


def robust_dish_stats(objs, dish_of, n_dishes):
    """Per dish: median length/width over 'typical singletons' (area within the
    25-75th percentile band, which drops clumps of touching grains and rim fragments)."""
    out = []
    for di in range(n_dishes):
        o = [x for x, k in zip(objs, dish_of) if k == di]
        if not o:
            out.append({"dish": di, "n": 0}); continue
        a = np.array([x.area_mm2 for x in o])
        lo, hi = np.percentile(a, 25), np.percentile(a, 75)
        core = [x for x in o if lo <= x.area_mm2 <= hi] or o
        out.append({"dish": di, "n": len(o), "n_core": len(core),
                    "length_mm": round(float(np.median([x.length_mm for x in core])), 2),
                    "width_mm": round(float(np.median([x.width_mm for x in core])), 2),
                    "width_p25_p75": [round(float(np.percentile([x.width_mm for x in core], q)), 2) for q in (25, 75)]})
    return out


def tiled(fn, img, tile=640, overlap=0.25):
    """Run a detector on overlapping native-resolution tiles (small objects stay
    big enough to see); de-duplicate across tiles by centroid distance."""
    h, w = img.shape[:2]
    step = int(tile * (1 - overlap))
    found = []
    for y0 in list(range(0, max(1, h - tile), step)) + [max(0, h - tile)]:
        for x0 in list(range(0, max(1, w - tile), step)) + [max(0, w - tile)]:
            for m in fn(img[y0:y0 + tile, x0:x0 + tile]):
                m.cx += x0; m.cy += y0
                found.append(m)
    found.sort(key=lambda m: -m.conf)
    keep = []
    for m in found:
        r = 0.5 * min(max(m.width_mm, 0.3), 3.0)
        if all(np.hypot(m.cx - k.cx, m.cy - k.cy) > max(6, r * 10) for k in keep):
            keep.append(m)
    return keep


def run(image_paths, student_weights, ref_truths, out_dir, analog_prompts=("rice grain", "seed", "pasta"),
        insect_prompts=("insect",)):
    from .measure import YoloMeasurer, consensus
    from .specimen_photo import segment_yoloe
    from .triage import reference_from_truth, triage
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    ref_L, ref_W = reference_from_truth(*ref_truths)
    student = YoloMeasurer(str(student_weights), conf=0.15)
    report = []
    for p in image_paths:
        img = cv2.imread(str(p))
        name = Path(p).name
        ppm_at, axis, diag = local_ruler_scale(img)
        has_scale = ppm_at is not None and diag.get("fit_rel_err", 1) < 0.03 and diag.get("n", 0) >= 6  # serrated dish rims fit ~6%, rulers <2%
        ref_ppm = float(np.median([ppm_at(v) for v in np.linspace(0, img.shape[0 if axis == "y" else 1], 9)])) if has_scale else 10.0
        # reference list: model-free dish segmentation (independent of both models)
        dishes = find_dishes(img)
        try:
            polys, objs, dish_of = fastsam_objects(img, dishes, ppm_at if has_scale else None, axis or "y", ref_ppm)
        except Exception as e:  # noqa: BLE001 - FastSAM unavailable: colour threshold
            print("FastSAM failed, using colour threshold:", e)
            dishes, polys, objs, dish_of = dish_objects(img, ppm_at if has_scale else None, axis or "y", ref_ppm=ref_ppm)
        if not objs:   # no dishes found: fall back to YOLOE prompted for food
            polys, objs = segment_yoloe(img, ref_ppm, prompts=analog_prompts, conf=0.15,
                                        min_area_mm2=0.2, length_range=(0.3, 60))
            dish_of = [-1] * len(objs)
        # production path, tiled at native resolution
        a = tiled(lambda t, r=ref_ppm: student(t, r), img)
        b = tiled(lambda t, r=ref_ppm: segment_yoloe(t, r, prompts=insect_prompts, length_range=(0.3, 60))[1], img)
        ms = consensus(a, b, ref_ppm, match_mm=2.0) if (a or b) else []
        verdicts = triage(ms, ref_L, ref_W, image=name)
        rows, vis = [], img.copy()
        for poly, o in zip(polys, objs):
            # dish objects are already measured at the local scale
            L, W = o.length_mm, o.width_mm
            near = [v for v in verdicts if np.hypot(v.cx - o.cx, v.cy - o.cy) < max(2.0 * ref_ppm, 0.5 * o.length_mm * ref_ppm)]
            v = min(near, key=lambda v: np.hypot(v.cx - o.cx, v.cy - o.cy)) if near else None
            status = v.status if v else "missed"
            rows.append({"image": name, "cx": round(o.cx), "cy": round(o.cy),
                         "length_mm": round(L, 2) if has_scale else None,
                         "width_mm": round(W, 2) if has_scale else None,
                         "scale": "local ruler" if has_scale else "none",
                         "system_status": status, "priority": v.priority if v else "none",
                         "reasons": v.reasons if v else ["not detected by the production path"],
                         "teacher_conf": round(o.conf, 3)})
            col = {"known": (0, 160, 0), "unknown": (0, 165, 255), "novel": (0, 0, 230), "missed": (160, 160, 160)}[status]
            cv2.polylines(vis, [poly.astype(np.int32)], True, col, 2)
            if has_scale:
                cv2.putText(vis, f"{status} {L:.1f}x{W:.1f}", (int(o.cx) + 4, int(o.cy) - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        cv2.imwrite(str(out / f"annotated_{name}"), vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
        for (x, y, r) in dishes:
            cv2.circle(vis, (int(x), int(y)), int(r), (255, 0, 0), 2)
        report.append({"image": name, "scale": diag if has_scale else None, "objects": rows,
                       "dishes": [{"x": round(x), "y": round(y), "r": round(r)} for x, y, r in dishes],
                       "dish_stats": robust_dish_stats(objs, dish_of, len(dishes)) if has_scale else None,
                       "system_detections": len(ms),
                       "system_by_status": {st: sum(v.status == st for v in verdicts) for st in ("known", "unknown", "novel")},
                       "summary": {s: sum(r["system_status"] == s for r in rows) for s in ("known", "unknown", "novel", "missed")}})
    (out / "report.json").write_text(json.dumps(report, indent=1))
    return report


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-analog-test")
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--ref", nargs="+", required=True, help="truth JSONs that define the database reference")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rep = run(a.images, a.weights, a.ref, a.out)
    for r in rep:
        print(r["image"], "scale:", "local ruler" if r["scale"] else "none", r["summary"])


if __name__ == "__main__":
    main()
