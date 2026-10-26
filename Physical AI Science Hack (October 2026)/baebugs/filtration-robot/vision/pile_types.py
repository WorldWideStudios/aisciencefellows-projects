"""Recognise which object types are in a dish, and roughly how much of each, even when they pile up.

Instead of measuring each piece, the dish floor is cut into small squares (~2.5 mm) and each square is
classified by colour and texture. Training needs no hand labels: every object square in a single-type
photo is that type (see training.json). The share of squares per type is the rough estimate the first
filter choice needs; each type's size comes from a reference table.

Usage:
  python pile_types.py train                    # trains from training.json, saves models/pile_types.yml
  python pile_types.py predict IMAGE [--out overlay.png] [--json estimate.json]
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from dish_sizer import CALIBRATION, fit_rim, segment

HERE = Path(__file__).parent
TRAINING = HERE / "training.json"
MODEL = HERE / "models" / "pile_types.yml"
PATCH_MM = 2.5
BACKGROUND = "background"
LABEL_THRESHOLD = 15  # stricter than sizing, so faint reflections aren't learned as objects
COLORS = [(40, 40, 40), (200, 0, 200), (0, 230, 255), (0, 128, 255), (255, 220, 0), (0, 200, 0),
          (255, 60, 0), (0, 0, 220), (128, 128, 128), (90, 60, 30)]  # BGR, one per class in training.json order


def setup():
    cal = json.loads(CALIBRATION.read_text())
    return cal["px_per_mm"], cal.get("floor_mm", 48)


def floor_patches(img, px_per_mm, floor_mm, rim=None):
    """Yield (x, y, size) for every square fully inside the dish floor, on a half-square grid."""
    size = int(PATCH_MM * px_per_mm)
    cx, cy, _ = rim or fit_rim(img, px_per_mm)
    r = floor_mm / 2 * px_per_mm - size
    for y in range(int(cy - r), int(cy + r), size // 2):
        for x in range(int(cx - r), int(cx + r), size // 2):
            if (x + size / 2 - cx) ** 2 + (y + size / 2 - cy) ** 2 < r * r:
                yield x, y, size


def features(lab, hsv, grad, x, y, size):
    """Colour and texture of one square: Lab mean/spread, dark and light tails, saturation, edge density."""
    p = lab[y:y + size, x:x + size].reshape(-1, 3)
    s = hsv[y:y + size, x:x + size, 1].ravel()
    g = grad[y:y + size, x:x + size]
    return np.concatenate([p.mean(0), p.std(0), np.percentile(p[:, 0], [10, 90]), [s.mean(), s.std(), g.mean(), g.std()]])


def prepare(img):
    blur = cv2.GaussianBlur(img, (3, 3), 0)
    lab = cv2.cvtColor(blur, cv2.COLOR_BGR2LAB).astype(np.float32)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV).astype(np.float32)
    gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY).astype(np.float32)
    grad = cv2.magnitude(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))
    return lab, hsv, grad


def labelled_patches(entry, px_per_mm, floor_mm):
    """(features, label) for the squares of one training photo whose label is clear."""
    img = cv2.imread(str(HERE / entry["file"]))
    lab, hsv, grad = prepare(img)
    rim = fit_rim(img, px_per_mm)
    if not entry["packed"]:
        mask = np.zeros(img.shape[:2], np.uint8)
        cv2.circle(mask, rim[:2], int(floor_mm / 2 * px_per_mm), 255, -1)
        objects, _ = segment(img, mask, entry.get("label_threshold", LABEL_THRESHOLD), 0.5)
    rows = []
    for x, y, size in floor_patches(img, px_per_mm, floor_mm, rim):
        if entry["packed"]:
            label = entry["type"]
        else:
            fill = (objects[y:y + size, x:x + size] > 0).mean()
            label = entry["type"] if fill > 0.6 else BACKGROUND if fill < 0.02 else None
        if label:
            rows.append((features(lab, hsv, grad, x, y, size), label))
    return rows


def balance(X, y, rng, per_class=400):
    """Equal squares per class: sample down the big classes, repeat the small ones."""
    keep = np.concatenate([rng.choice(np.flatnonzero(y == c), per_class, replace=(y == c).sum() < per_class)
                           for c in np.unique(y)])
    return X[keep], y[keep]


def fit(X, y):
    model = cv2.ml.RTrees_create()
    model.setMaxDepth(12)
    model.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER, 150, 0))
    model.train(X.astype(np.float32), cv2.ml.ROW_SAMPLE, y.astype(np.int32))
    return model


def report(classes, truth, pred):
    for i, name in enumerate(classes):
        n = (truth == i).sum()
        if n:
            wrong = {classes[j]: int(((truth == i) & (pred == j)).sum()) for j in range(len(classes)) if j != i}
            mistakes = ", ".join(f"{k} {v}" for k, v in sorted(wrong.items(), key=lambda kv: -kv[1]) if v)[:80]
            print(f"  {name:20s} {((pred == i) & (truth == i)).sum() / n:5.0%} of {n:4d} squares right  {mistakes}")


def train():
    px_per_mm, floor_mm = setup()
    photos = json.loads(TRAINING.read_text())["photos"]
    classes = [BACKGROUND] + list(dict.fromkeys(p["type"] for p in photos))
    per_photo = []
    for entry in photos:
        rows = labelled_patches(entry, px_per_mm, floor_mm)
        per_photo.append((np.array([r[0] for r in rows]), np.array([classes.index(r[1]) for r in rows])))
    rng = np.random.default_rng(0)

    # honest check: each photo is tested by a model that never saw it, trained on all the other photos
    # (only for types with another photo to learn from)
    photos_per_type = {t: sum(p["type"] == t for p in photos) for t in classes[1:]}
    truth, pred = [], []
    for i, entry in enumerate(photos):
        if photos_per_type[entry["type"]] < 2:
            continue
        X = np.concatenate([x for j, (x, _) in enumerate(per_photo) if j != i])
        y = np.concatenate([y for j, (_, y) in enumerate(per_photo) if j != i])
        model = fit(*balance(X, y, rng))
        truth.append(per_photo[i][1])
        pred.append(model.predict(per_photo[i][0].astype(np.float32))[1].ravel().astype(int))
    print("check (each photo judged by a model trained without it):")
    report(classes, np.concatenate(truth), np.concatenate(pred))
    unchecked = [t for t, n in photos_per_type.items() if n < 2]
    if unchecked:
        print("  not checked, only one photo:", ", ".join(unchecked))

    X = np.concatenate([x for x, _ in per_photo])
    y = np.concatenate([y for _, y in per_photo])
    model = fit(*balance(X, y, rng))
    MODEL.parent.mkdir(exist_ok=True)
    model.save(str(MODEL))
    MODEL.with_suffix(".json").write_text(json.dumps({"classes": classes, "patch_mm": PATCH_MM}, indent=2))
    print(f"trained on {len(y)} squares from {len(photos)} photos, saved {MODEL.relative_to(HERE)}")


def predict(image, out, json_out=None):
    px_per_mm, floor_mm = setup()
    classes = json.loads(MODEL.with_suffix(".json").read_text())["classes"]
    model = cv2.ml.RTrees_load(str(MODEL))
    img = cv2.imread(image)
    lab, hsv, grad = prepare(img)
    patches = list(floor_patches(img, px_per_mm, floor_mm))
    X = np.array([features(lab, hsv, grad, *p) for p in patches], np.float32)
    pred = model.predict(X)[1].ravel().astype(int)

    counts = np.bincount(pred, minlength=len(classes))
    objects = counts[1:].sum()
    print(f"{len(patches)} squares, {objects} with objects")
    shares = {classes[i]: counts[i] / objects for i in range(1, len(classes)) if objects}
    for name, share in sorted(shares.items(), key=lambda kv: -kv[1]):
        print(f"  {name:20s} {share:5.0%}")

    overlay = img.copy()
    for (x, y, size), c in zip(patches, pred):
        if c:
            q = size // 4  # paint the centre half of each square so neighbours don't overlap
            cv2.rectangle(overlay, (x + q, y + q), (x + size - q, y + size - q), COLORS[c % len(COLORS)], -1)
    out_img = cv2.addWeighted(overlay, 0.55, img, 0.45, 0)
    for row, name in enumerate(classes[1:], start=1):
        text = f"{name} {shares.get(name, 0):.0%}"
        cv2.rectangle(out_img, (10, 10 + row * 28), (30, 30 + row * 28), COLORS[row % len(COLORS)], -1)
        cv2.putText(out_img, text, (38, 27 + row * 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3)
        cv2.putText(out_img, text, (38, 27 + row * 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1)
    cv2.imwrite(out, out_img)
    if json_out:
        Path(json_out).write_text(json.dumps({"image": image, "squares": int(objects),
                                              "shares": {k: round(v, 3) for k, v in shares.items()}}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("train")
    p = sub.add_parser("predict")
    p.add_argument("image")
    p.add_argument("--out", default="pile_types.png")
    p.add_argument("--json", help="write the estimate (share of each type) here, for filter_plan.py --estimate")
    args = ap.parse_args()
    train() if args.cmd == "train" else predict(args.image, args.out, args.json)


if __name__ == "__main__":
    main()
