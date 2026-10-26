"""Objects in an image as nested geometry levels, Merkle-hashed, with the
cross-model break point.

For each model's outline of an object:
  L1 aabb      axis-aligned bounding box
  L2 obb       minimum-area rotated rectangle (length x width live here)
  L3 hull      convex hull
  L4 poly_2pct polygon simplified at 2% of the perimeter
  L5 poly_05pct polygon simplified at 0.5%
  L6 contour   full outline
Each node: coordinates in mm (rounded 0.01), area, length/width, and checks
(boxes and hull contain the contour; hull inside both boxes; simplified polygons
within their epsilon of the contour (Hausdorff) since Douglas-Peucker output is not nested). node hash = H(level, geometry, checks, child hash):
the tree root is the object's geometry hash at full detail.

Across models, each level is compared pairwise (IoU and length difference);
the BREAK POINT is the first level where agreement falls below policy. Models
can agree on where the object is (L1) and still disagree on what it looks like (L6).

  python -m baebugs.image_levels spotcheck --images a.jpg b.png --ppm 41.5 10 --out spot/
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Polygon
from shapely.validation import make_valid

LEVELS = ["L1_aabb", "L2_obb", "L3_hull", "L4_poly_2pct", "L5_poly_05pct", "L6_contour"]
POLICY = {"iou_min": 0.80, "length_rel": 0.10}
COLORS = {"L1_aabb": (255, 200, 0), "L2_obb": (0, 200, 255), "L3_hull": (0, 255, 0),
          "L4_poly_2pct": (255, 0, 255), "L5_poly_05pct": (0, 128, 255), "L6_contour": (0, 0, 255)}


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _poly(pts):
    p = Polygon(pts)
    return p if p.is_valid else make_valid(p).buffer(0)


def level_geoms(contour):
    c = contour.reshape(-1, 2).astype(np.float32)
    x, y, w, h = cv2.boundingRect(c)
    obb = cv2.boxPoints(cv2.minAreaRect(c))
    hull = cv2.convexHull(c).reshape(-1, 2)
    per = cv2.arcLength(c.reshape(-1, 1, 2), True)
    p2 = cv2.approxPolyDP(c.reshape(-1, 1, 2), 0.02 * per, True).reshape(-1, 2)
    p05 = cv2.approxPolyDP(c.reshape(-1, 1, 2), 0.005 * per, True).reshape(-1, 2)
    return {"L1_aabb": np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], np.float32),
            "L2_obb": obb, "L3_hull": hull, "L4_poly_2pct": p2, "L5_poly_05pct": p05, "L6_contour": c}


def tree(contour, ppm, model):
    """Merkle tree from coarse to fine. Claims per level (exact geometry facts):
      L1 aabb, L2 obb, L3 hull : contain the full contour (1 px)
      L3 hull                  : inside L1 and inside L2 (1 px); area <= both
      L4 / L5 simplified       : Hausdorff distance to the contour <= the simplification
                                 epsilon (+1 px). Douglas-Peucker polygons are NOT nested
                                 (they cut corners), so containment is the wrong claim there;
                                 the tolerance is the claim's variance policy.
      L6 contour               : valid polygon, area <= hull."""
    g = level_geoms(contour)
    c = g["L6_contour"]
    per = cv2.arcLength(c.reshape(-1, 1, 2), True)
    eps = {"L4_poly_2pct": 0.02 * per, "L5_poly_05pct": 0.005 * per}
    polys = {k: _poly(v) if len(v) >= 3 else None for k, v in g.items()}
    C = polys["L6_contour"]
    nodes, child = [], None
    for i in range(len(LEVELS) - 1, -1, -1):              # fine -> coarse so parents cover children
        lv = LEVELS[i]
        P = polys[lv]
        (_cx, _cy), (rw, rh), _ = cv2.minAreaRect(g[lv].reshape(-1, 1, 2).astype(np.float32))
        geom = [[round(float(x) / ppm, 2), round(float(y) / ppm, 2)] for x, y in g[lv]]
        checks = {"valid_polygon": P is not None and P.area > 0}
        if P is not None and C is not None:
            if lv in ("L1_aabb", "L2_obb", "L3_hull"):
                checks["contains_contour_1px"] = bool(P.buffer(1.0).contains(C))
            if lv == "L3_hull":
                for par in ("L1_aabb", "L2_obb"):
                    checks[f"inside_{par}_1px"] = bool(polys[par].buffer(1.0).contains(P))
                    checks[f"area_le_{par}"] = bool(P.area <= polys[par].area + 1.0)
            if lv in eps:
                checks["hausdorff_le_eps"] = bool(P.hausdorff_distance(C) <= eps[lv] + 1.0)
            if lv == "L6_contour":
                checks["area_le_hull"] = bool(P.area <= polys["L3_hull"].area + 1.0)
        body = {"model": model, "level": lv, "geometry_mm": geom,
                "area_mm2": round(P.area / ppm ** 2, 3) if P is not None else None,
                "length_mm": round(max(rw, rh) / ppm, 3), "width_mm": round(min(rw, rh) / ppm, 3),
                "policy_px": round(eps.get(lv, 1.0), 2), "checks": checks, "child": child}
        node = {**body, "hash": H(body)}
        nodes.insert(0, node); child = node["hash"]
    return nodes, polys


def compare(polys_by_model, nodes_by_model, policy=POLICY):
    """Pairwise agreement per level; break point = first level failing policy."""
    ms = sorted(polys_by_model)
    per_level = {}
    for lv in LEVELS:
        pairs = []
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                a, b = polys_by_model[ms[i]].get(lv), polys_by_model[ms[j]].get(lv)
                if a is None or b is None:
                    continue
                inter = a.intersection(b).area; uni = a.union(b).area
                la = next(n["length_mm"] for n in nodes_by_model[ms[i]] if n["level"] == lv)
                lb = next(n["length_mm"] for n in nodes_by_model[ms[j]] if n["level"] == lv)
                pairs.append({"a": ms[i], "b": ms[j], "iou": round(inter / uni, 3) if uni else 0.0,
                              "length_rel": round(abs(la - lb) / max(la, lb, 1e-9), 3)})
        ok = all(p["iou"] >= policy["iou_min"] and p["length_rel"] <= policy["length_rel"] for p in pairs) if pairs else None
        per_level[lv] = {"pairs": pairs, "agree": ok,
                         "min_iou": min((p["iou"] for p in pairs), default=None)}
    bp = next((lv for lv in LEVELS if per_level[lv]["agree"] is False), None)
    return {"policy": policy, "per_level": per_level, "break_point": bp}


# ------------------------------------------------------------ model masks

def _largest(contours):
    return max(contours, key=cv2.contourArea) if contours else None


def mask_classical(img, ppm):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    h, w = img.shape[:2]
    cs = [c for c in cs if cv2.boundingRect(c)[0] > 2 and cv2.boundingRect(c)[1] > 2 and
          sum(cv2.boundingRect(c)[::2]) < w - 2 and sum(cv2.boundingRect(c)[1::2]) < h - 2]
    return _largest(cs)


_U = {}


def mask_ultra(img, kind, weights):
    from ultralytics import YOLO, YOLOE, FastSAM
    key = (kind, weights)
    if key not in _U:
        if kind == "yoloe":
            m = YOLOE(weights); m.set_classes(["insect"], m.get_text_pe(["insect"]))
        elif kind == "fastsam":
            m = FastSAM(weights)
        else:
            m = YOLO(weights)
        _U[key] = m
    r = _U[key].predict(img, conf=0.15, verbose=False, retina_masks=True)[0]
    if r.masks is None:
        return None
    h, w = img.shape[:2]
    cs = [np.asarray(p, np.float32).reshape(-1, 1, 2) for p in r.masks.xy if len(p) >= 3]
    if kind == "fastsam":                                   # drop background-sized segments
        cs = [c for c in cs if cv2.contourArea(c) < 0.5 * h * w]
    return _largest(cs)


def mask_macos_vision(img):
    """Apple Vision foreground instance mask (macOS 14+), via pyobjc."""
    import Vision
    from Foundation import NSData
    ok, buf = cv2.imencode(".png", img)
    data = NSData.dataWithBytes_length_(buf.tobytes(), len(buf))
    handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(data, None)
    req = Vision.VNGenerateForegroundInstanceMaskRequest.alloc().init()
    ok, _err = handler.performRequests_error_([req], None)
    res = req.results()
    if not ok or not res:
        return None
    obs = res[0]
    pb, _err = obs.generateScaledMaskForImageForInstances_fromRequestHandler_error_(obs.allInstances(), handler, None)
    import Quartz
    Quartz.CVPixelBufferLockBaseAddress(pb, 0)
    w, h = Quartz.CVPixelBufferGetWidth(pb), Quartz.CVPixelBufferGetHeight(pb)
    bpr = Quartz.CVPixelBufferGetBytesPerRow(pb)
    base = Quartz.CVPixelBufferGetBaseAddress(pb)
    arr = np.frombuffer(base.as_buffer(bpr * h), dtype=np.float32 if bpr >= w * 4 else np.uint8)
    Quartz.CVPixelBufferUnlockBaseAddress(pb, 0)
    m = (arr.reshape(h, bpr // arr.itemsize)[:, :w] > 0.5).astype(np.uint8) * 255
    m = cv2.resize(m, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return _largest(cs)


MODELS = {
    "classical": lambda img, ppm, W: mask_classical(img, ppm),
    "yolo_r3": lambda img, ppm, W: mask_ultra(img, "yolo", W["yolo_r3"]),
    "yoloe": lambda img, ppm, W: mask_ultra(img, "yoloe", W["yoloe"]),
    "fastsam": lambda img, ppm, W: mask_ultra(img, "fastsam", W["fastsam"]),
    "macos_vision": lambda img, ppm, W: mask_macos_vision(img),
}


def crop_to(img, contour, pad_mm, ppm):
    x, y, w, h = cv2.boundingRect(contour.reshape(-1, 1, 2).astype(np.int32))
    p = int(pad_mm * ppm)
    return max(0, x - p), max(0, y - p), min(img.shape[1], x + w + p), min(img.shape[0], y + h + p)


def spotcheck(items, weights, out_dir, models=tuple(MODELS)):
    """items: [{"image": path, "ppm": float, "label": str}]. Writes per-image sheet PNG + JSON."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    report = []
    for it in items:
        img = cv2.imread(str(it["image"]))
        if img is None:
            continue
        nodes_by, polys_by, errs = {}, {}, {}
        for m in models:
            try:
                c = MODELS[m](img, it["ppm"], weights)
            except Exception as e:  # noqa: BLE001 - model unavailable on this machine
                errs[m] = str(e)[:120]; continue
            if c is None or cv2.contourArea(c.reshape(-1, 1, 2).astype(np.float32)) < 4:
                errs[m] = "no object"; continue
            nodes_by[m], polys_by[m] = tree(c, it["ppm"], m)
        cmp = compare(polys_by, nodes_by)
        # sheet: one panel per model, all six levels drawn
        ref = next(iter(nodes_by), None)
        panels = []
        for m in models:
            p = img.copy()
            if m in nodes_by:
                g = level_geoms(np.array([[[x * it["ppm"], y * it["ppm"]]] for x, y in nodes_by[m][-1]["geometry_mm"]], np.float32))
                for lv in LEVELS:
                    cv2.polylines(p, [g[lv].reshape(-1, 1, 2).astype(np.int32)], True, COLORS[lv],
                                  max(1, round(min(img.shape[:2]) / 400)))
                n2 = nodes_by[m][1]
                txt = f"{m}: L {n2['length_mm']:.2f} W {n2['width_mm']:.2f} mm"
            else:
                txt = f"{m}: {errs.get(m, 'n/a')[:40]}"
            if ref:
                x0, y0, x1, y1 = crop_to(img, np.array([[x * it["ppm"], y * it["ppm"]] for x, y in nodes_by[ref][0]["geometry_mm"]],
                                                       np.float32), 3.0, it["ppm"])
                p = p[y0:y1, x0:x1]
            p = cv2.resize(p, (360, int(360 * p.shape[0] / max(1, p.shape[1]))))
            p = cv2.copyMakeBorder(p, 26, 4, 4, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            cv2.putText(p, txt[:46], (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
            panels.append(p)
        hmax = max(q.shape[0] for q in panels)
        panels = [cv2.copyMakeBorder(q, 0, hmax - q.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for q in panels]
        sheet = np.hstack(panels)
        bp = cmp["break_point"]
        bar = np.full((30, sheet.shape[1], 3), 255, np.uint8)
        legend = f"{it.get('label', '')} | {it['ppm']:.1f} px/mm | break point: {bp or 'none (all levels agree)'} | " + \
                 " ".join(f"{lv[:2]} {cmp['per_level'][lv]['min_iou']}" for lv in LEVELS)
        cv2.putText(bar, legend[:170], (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        stem = Path(it["image"]).stem
        cv2.imwrite(str(out / f"{stem}_levels.png"), np.vstack([bar, sheet]))
        rec = {"image": str(it["image"]), "label": it.get("label"), "ppm": it["ppm"], "errors": errs,
               "roots": {m: n[0]["hash"] for m, n in nodes_by.items()},
               "L2": {m: {"length_mm": n[1]["length_mm"], "width_mm": n[1]["width_mm"]} for m, n in nodes_by.items()},
               "failed_checks": {m: [f"{x['level']}:{k}" for x in n for k, v in x["checks"].items() if not v] for m, n in nodes_by.items()},
               "compare": cmp, "truth": it.get("truth")}
        report.append(rec)
        (out / f"{stem}_levels.json").write_text(json.dumps({**rec, "nodes": nodes_by}, indent=1))
    (out / "spotcheck.json").write_text(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True, help="json list of {image, ppm, label, truth}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--yolo", default="/Volumes/magicBLACKbox/baebugs/runs/r3_real/weights/best.pt")
    ap.add_argument("--yoloe", default="/Volumes/magicLABbox/baebugs/weights/yoloe-11s-seg.pt")
    ap.add_argument("--fastsam", default="/Volumes/magicLABbox/baebugs/weights/FastSAM-s.pt")
    a = ap.parse_args()
    W = {"yolo_r3": a.yolo, "yoloe": a.yoloe, "fastsam": a.fastsam}
    for r in spotcheck(json.loads(Path(a.items).read_text()), W, a.out):
        print(Path(r["image"]).name, r["label"], "| break:", r["compare"]["break_point"], "| L2:",
              {m: (v["length_mm"], v["width_mm"]) for m, v in r["L2"].items()}, "| errors:", r["errors"])
