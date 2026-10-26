"""First-pass object sizing for a petri dish photo.

Finds the dish, separates objects from the background by colour difference,
and measures each object's length and width (the short side is what decides
whether it fits through a filter's holes).

Usage: python dish_sizer.py IMAGE [--px-per-mm 13.9] [--out annotated.png] [--json objects.json]
  Without --px-per-mm the scale comes from calibration.json (the mounted webcam).
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

CALIBRATION = Path(__file__).with_name("calibration.json")


RIM_RADIUS_MM = (28, 34)  # outer rim of the 63 mm dish (with or without lid), where its edge is strongest
RIM_MIN_VISIBLE = 0.8  # the dish may run off the photo's edge, but most of its rim must be in view


def _edges(gray):
    """Horizontal and vertical brightness gradients."""
    return cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1)


def _ring_scores(edges, cxs, cys, r, n=180):
    """How strongly a circle of radius r around each centre (cxs, cys: 1-D arrays) follows an edge.

    Only the gradient across the circle counts (pointing at the centre or away from it), so edges
    the circle merely cuts through, like reflections or objects inside the dish, add little. The score
    is the median along the circle, not the mean, so a circle must follow an edge all the way round:
    borrowing a stretch of a very strong straight edge (a ruler) doesn't help. Points off the photo
    are skipped; a circle with too little of its rim in view scores 0.
    """
    gx, gy = edges
    h, w = gx.shape
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    cos, sin = np.cos(t), np.sin(t)
    xs = np.rint(cxs[:, None] + r * cos).astype(int)
    ys = np.rint(cys[:, None] + r * sin).astype(int)
    inside = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
    xs, ys = np.clip(xs, 0, w - 1), np.clip(ys, 0, h - 1)
    across = np.where(inside, np.abs(gx[ys, xs] * cos + gy[ys, xs] * sin), np.nan)
    visible = inside.mean(axis=1)
    return np.where(visible >= RIM_MIN_VISIBLE, np.nan_to_num(np.nanmedian(across, axis=1)), 0)


def fit_rim(img, px_per_mm, scale=4):
    """Return (cx, cy, r) of the dish rim: the dish-sized circle with the strongest edge all the way round.

    Tries every centre where most of the rim is in the photo on a 1/4-size edge map, then refines
    at full size. A straight edge such as a ruler lines up with only a small part of any circle, so
    it can't win, and a faint rim on white paper still beats the background.
    """
    gray = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0).astype(np.float32)
    small = _edges(cv2.resize(gray, None, fx=1 / scale, fy=1 / scale, interpolation=cv2.INTER_AREA))
    h, w = small[0].shape
    best = None
    for r_mm in np.arange(RIM_RADIUS_MM[0], RIM_RADIUS_MM[1] + 0.01, 0.5):
        r = r_mm * px_per_mm / scale
        m = int(0.6 * r)  # centres this close to the border can still have 80% of the rim in view
        ys, xs = np.mgrid[m:int(h - m):2, m:int(w - m):2]
        if not xs.size:
            continue
        xs, ys = xs.ravel().astype(float), ys.ravel().astype(float)
        scores = _ring_scores(small, xs, ys, r)
        i = int(scores.argmax())
        if best is None or scores[i] > best[0]:
            best = (scores[i], xs[i] * scale, ys[i] * scale, r * scale)
    if best is None:
        return None

    full = _edges(gray)
    _, cx0, cy0, r0 = best
    ys, xs = np.mgrid[cy0 - 2 * scale:cy0 + 2 * scale + 1, cx0 - 2 * scale:cx0 + 2 * scale + 1]
    xs, ys = xs.ravel().astype(float), ys.ravel().astype(float)
    refined = max(
        (scores[i], xs[i], ys[i], r)
        for r in np.arange(r0 - px_per_mm, r0 + px_per_mm + 0.01, 0.1 * px_per_mm)
        for scores in [_ring_scores(full, xs, ys, r, n=360)]
        for i in [int(scores.argmax())]
    )
    _, cx, cy, r = refined
    return int(round(cx)), int(round(cy)), int(round(r))


def colour_distance(diff, shadow_weight):
    """CIELAB distance with darkening down-weighted: shadows make the background darker but keep its colour.

    Getting lighter is not down-weighted, so pale objects (pasta, rice) still stand out.
    """
    diff = diff.copy()
    darker = diff[..., 0] < 0
    diff[..., 0][darker] *= shadow_weight
    return np.linalg.norm(diff, axis=-1)


def fit_background(lab, mask, threshold, shadow_weight, iterations=4):
    """Background colour over the dish as a smooth quadratic surface per CIELAB channel.

    Models gradual lighting changes across the dish. Each pass refits without the pixels that stood
    out from the previous fit (objects, shadows), so even big objects don't drag the background.
    """
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    step = max(1, len(xs) // 40000)
    ys, xs = ys[::step], xs[::step]

    def terms(x, y):
        x, y = (x - w / 2) / w, (y - h / 2) / h
        return np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], axis=-1)

    a, samples = terms(xs.astype(float), ys.astype(float)), lab[ys, xs]
    keep = np.ones(len(xs), bool)
    for _ in range(iterations):
        coef, *_ = np.linalg.lstsq(a[keep], samples[keep], rcond=None)
        keep = colour_distance(samples - a @ coef, shadow_weight) < threshold
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    return (terms(xx, yy) @ coef).astype(np.float32)


def segment(img, mask, threshold, shadow_weight):
    """Mark pixels whose colour differs from the background by more than `threshold` (CIELAB units)."""
    lab = cv2.cvtColor(cv2.GaussianBlur(img, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
    distance = colour_distance(lab - fit_background(lab, mask, threshold, shadow_weight), shadow_weight)
    objects = ((distance > threshold) & (mask > 0)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    objects = cv2.morphologyEx(objects, cv2.MORPH_OPEN, kernel)
    objects = cv2.morphologyEx(objects, cv2.MORPH_CLOSE, kernel, iterations=2)
    return objects, distance


def measure(objects, px_per_mm, min_area_mm2):
    contours, _ = cv2.findContours(objects, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    results = []
    for c in contours:
        area_mm2 = cv2.contourArea(c) / px_per_mm**2
        if area_mm2 < min_area_mm2:
            continue
        (cx, cy), (a, b), angle = cv2.minAreaRect(c)
        results.append({
            "center_px": [round(cx), round(cy)],
            "length_mm": round(max(a, b) / px_per_mm, 1),
            "width_mm": round(min(a, b) / px_per_mm, 1),
            "area_mm2": round(area_mm2, 1),
            "box_px": cv2.boxPoints(((cx, cy), (a, b), angle)).round().astype(int).tolist(),
            "contour": c,
            "rect": ((cx, cy), (a, b), angle),
        })
    results.sort(key=lambda o: -o["area_mm2"])
    for i, o in enumerate(results, start=1):
        o["id"] = i
    return results


def annotate(img, dish, inner_r, results):
    out = img.copy()
    if dish:
        cv2.circle(out, dish[:2], inner_r, (255, 200, 0), 1)
    for o in results:
        cv2.drawContours(out, [o["contour"]], -1, (0, 255, 0), 2)
        box = cv2.boxPoints(o["rect"]).astype(int)
        cv2.drawContours(out, [box], -1, (255, 0, 255), 1)
        x, y = o["center_px"]
        label = f"#{o['id']} {o['length_mm']}x{o['width_mm']}mm"
        cv2.putText(out, label, (x + 12, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(out, label, (x + 12, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--px-per-mm", type=float,
                    help="scale of this photo. Omit it for the mounted webcam: the scale and that setup's "
                         "threshold, floor size and dish centre then come from calibration.json")
    ap.add_argument("--threshold", type=float, help="colour difference from background (CIELAB), default 20")
    ap.add_argument("--floor-mm", type=float, help="diameter of the dish floor to analyse, mm, default 48 (wall starts at ~48 mm)")
    ap.add_argument("--dish-center", type=int, nargs=2, metavar=("X", "Y"), help="dish centre in px, skipping detection")
    ap.add_argument("--shadow-weight", type=float, default=0.5, help="weight of darkening vs colour change (shadows only darken)")
    ap.add_argument("--min-area", type=float, default=0.5, help="ignore blobs smaller than this, mm^2")
    ap.add_argument("--out", default="annotated.png")
    ap.add_argument("--json")
    args = ap.parse_args()

    # Without --px-per-mm the photo is from the calibrated webcam, so use its whole setup;
    # anything given on the command line still wins.
    setup = {}
    if args.px_per_mm is None:
        if not CALIBRATION.exists():
            raise SystemExit("no --px-per-mm given and no calibration.json; measure the scale with ruler_scale.py")
        setup = json.loads(CALIBRATION.read_text())
        args.px_per_mm = setup["px_per_mm"]
        print(f"scale: {args.px_per_mm} px/mm from {CALIBRATION.name}")
    if args.threshold is None:
        args.threshold = setup.get("threshold", 20)
    if args.floor_mm is None:
        args.floor_mm = setup.get("floor_mm", 48)
    if args.dish_center is None:
        args.dish_center = setup.get("dish_center_px")

    img = cv2.imread(args.image)
    if img is None:
        raise SystemExit(f"cannot read {args.image}")
    dish = (*args.dish_center, 0) if args.dish_center else fit_rim(img, args.px_per_mm)
    mask = np.zeros(img.shape[:2], np.uint8)
    if dish:
        inner_r = int(args.floor_mm / 2 * args.px_per_mm)
        cv2.circle(mask, dish[:2], inner_r, 255, -1)
        print(f"dish: center {dish[:2]}, analysing {args.floor_mm:g} mm across")
    else:
        inner_r = 0
        mask[:] = 255
        print("dish not found; analysing the whole image")

    objects, _ = segment(img, mask, args.threshold, args.shadow_weight)
    results = measure(objects, args.px_per_mm, args.min_area)
    cv2.imwrite(args.out, annotate(img, dish, inner_r, results))

    print(f"{len(results)} objects")
    for o in results:
        print(f"  #{o['id']}: {o['length_mm']} x {o['width_mm']} mm, area {o['area_mm2']} mm2, at {o['center_px']}")
    if args.json:
        with open(args.json, "w") as f:
            json.dump([{k: v for k, v in o.items() if k not in ("contour", "rect")} for o in results], f, indent=2)


if __name__ == "__main__":
    main()
