"""Synthetic YOLO-segmentation dataset of bug analogs, with known mm sizes.

Shapes mimic the Track A kit: rice (ellipses, several colours), chia (small dark
ovals), ditalini (rings), lasagna shards (irregular polygons), and insect-like
bodies (segmented body + legs/antennae lines). Backgrounds: white printed tray,
woven/hex mesh texture, clear petri dish on a light stage. Each body is labelled
as a polygon from its own mask, and its true length/width are kept in a
sidecar JSON so sizing accuracy can be benchmarked.

This bootstraps the detector and validates the pipeline. Fine-tune on real
AmScope / BugPicker images (bugpicker_bridge.export_yolo) before trusting it.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np

CLASSES = ["specimen"]


def _background(rng, h, w):
    kind = rng.choice(["tray", "mesh", "petri"])
    base = int(rng.integers(205, 245))
    img = np.full((h, w, 3), base, np.uint8)
    img = (img + rng.normal(0, 3, img.shape)).clip(0, 255).astype(np.uint8)
    tint = rng.integers(-8, 8, 3)
    img = (img.astype(int) + tint).clip(0, 255).astype(np.uint8)
    if kind == "mesh":
        pitch = int(rng.integers(18, 40))
        col = int(base - rng.integers(25, 60))
        for x in range(0, w, pitch):
            cv2.line(img, (x, 0), (x, h), (col,) * 3, 1)
        for y in range(0, h, pitch):
            cv2.line(img, (0, y), (w, y), (col,) * 3, 1)
    elif kind == "petri":
        c = (w // 2 + int(rng.integers(-40, 40)), h // 2 + int(rng.integers(-40, 40)))
        r = int(min(h, w) * rng.uniform(0.42, 0.6))
        cv2.circle(img, c, r, (base - 30,) * 3, 3, cv2.LINE_AA)
        cv2.circle(img, c, r - 6, (min(255, base + 8),) * 3, 2, cv2.LINE_AA)
    # soft illumination gradient
    gy = np.linspace(-1, 1, h)[:, None]
    img = (img.astype(float) * (1 + 0.06 * gy)[..., None]).clip(0, 255).astype(np.uint8)
    return img, kind


def _draw(rng, mask, img, kind, cx, cy, L, W, ang, ppm):
    col = {
        "rice": [(225, 230, 235), (150, 185, 205), (40, 30, 80), (60, 45, 120)],
        "chia": [(40, 40, 45), (70, 70, 75), (180, 185, 190)],
        "pasta": [(60, 190, 230), (80, 200, 235)],
        "insect": [(20, 25, 30), (30, 50, 70), (40, 60, 40)],
    }
    c = tuple(int(v) for v in col[kind][rng.integers(len(col[kind]))])
    axes = (max(1, int(L * ppm / 2)), max(1, int(W * ppm / 2)))
    m = np.zeros_like(mask)
    if kind in ("rice", "chia"):
        cv2.ellipse(m, (cx, cy), axes, ang, 0, 360, 255, -1, cv2.LINE_AA)
    elif kind == "pasta":
        if rng.random() < 0.5:  # ditalini ring seen end-on
            r = axes[1]
            cv2.circle(m, (cx, cy), r, 255, -1)
            cv2.circle(m, (cx, cy), max(1, int(r * 0.45)), 0, -1)   # hole: background shows through
            L = W = 2 * r / ppm
        else:  # shard
            n = int(rng.integers(4, 7))
            pts = []
            for k in range(n):
                t = 2 * math.pi * k / n + rng.uniform(-0.3, 0.3)
                rr = rng.uniform(0.6, 1.0)
                pts.append((cx + rr * axes[0] * math.cos(t + math.radians(ang)),
                            cy + rr * axes[1] * math.sin(t + math.radians(ang))))
            cv2.fillPoly(m, [np.int32(pts)], 255)
    else:  # insect: 3 body segments + legs + antennae
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        for off, sx, sy in [(-0.32, 0.36, 1.0), (0.05, 0.22, 0.8), (0.33, 0.14, 0.65)]:
            px, py = cx + off * L * ppm * ux, cy + off * L * ppm * uy
            cv2.ellipse(m, (int(px), int(py)), (max(1, int(sx * L * ppm)), max(1, int(sy * W * ppm / 2))),
                        ang, 0, 360, 255, -1, cv2.LINE_AA)
        th = max(1, int(0.08 * W * ppm))
        for k in (-1, 0, 1):
            bx, by = cx + k * 0.12 * L * ppm * ux, cy + k * 0.12 * L * ppm * uy
            for s in (-1, 1):
                ex = bx + s * (-uy) * 0.9 * W * ppm + k * 0.1 * L * ppm * ux
                ey = by + s * ux * 0.9 * W * ppm + k * 0.1 * L * ppm * uy
                cv2.line(m, (int(bx), int(by)), (int(ex), int(ey)), 255, th, cv2.LINE_AA)
        hx, hy = cx + 0.45 * L * ppm * ux, cy + 0.45 * L * ppm * uy
        for s in (-1, 1):
            cv2.line(m, (int(hx), int(hy)),
                     (int(hx + 0.25 * L * ppm * ux + s * 0.3 * W * ppm * -uy),
                      int(hy + 0.25 * L * ppm * uy + s * 0.3 * W * ppm * ux)), 255, th, cv2.LINE_AA)
    img[m > 127] = c
    shade = cv2.GaussianBlur(m, (0, 0), 1.2)
    img[:] = np.where(shade[..., None] > 20, (img * 0.97).astype(np.uint8), img)
    mask |= m
    return m, L, W


def make_image(rng, ppm=None, size=(640, 640), n_range=(6, 22)):
    """ppm=None: random scale per image (6-40 px/mm) so 1-30 mm bodies all occur
    and still fit the frame; small-scale images carry the big bodies."""
    h, w = size
    if ppm is None:
        ppm = float(np.exp(rng.uniform(np.log(6), np.log(40))))
    img, bg = _background(rng, h, w)
    occupied = np.zeros((h, w), np.uint8)
    objs = []
    max_len = 0.45 * min(h, w) / ppm                      # keep bodies inside the frame
    spec = {"rice": ((5, 8), (1.4, 2.3)), "chia": ((1.6, 2.3), (1.0, 1.4)),
            "pasta": ((4, 9), (3, 6)), "insect": ((1.0, 30.0), (0.25, 10.0))}
    kinds = list(spec)
    for _ in range(int(rng.integers(*n_range)) * 4):
        if len(objs) >= n_range[1]:
            break
        k = kinds[rng.integers(len(kinds))]
        lo, hi = spec[k][0][0], min(spec[k][0][1], max_len)
        if hi <= lo:
            continue
        L = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))   # log-uniform: 1 mm as common as 10 mm
        W = min(L, rng.uniform(*spec[k][1])) if k != "insect" else L * rng.uniform(0.2, 0.5)
        if W * ppm < 3:                                         # below what the camera resolves
            continue
        r = int(L * ppm / 2) + 6
        cx, cy = int(rng.integers(r, w - r)), int(rng.integers(r, h - r))
        if occupied[max(0, cy - r):cy + r, max(0, cx - r):cx + r].any():
            continue
        m, _L2, _W2 = _draw(rng, np.zeros((h, w), np.uint8), img, k, cx, cy, L, W,
                          float(rng.uniform(0, 180)), ppm)
        cv2.circle(occupied, (cx, cy), r, 255, -1)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        cnt = max(cnts, key=cv2.contourArea)
        (_, _), (rw, rh), _ = cv2.minAreaRect(cnt)
        objs.append({"kind": k, "cx": cx, "cy": cy, "ppm": ppm,
                     "length_mm": max(rw, rh) / ppm, "width_mm": min(rw, rh) / ppm,
                     "poly": (cnt.reshape(-1, 2) / [w, h]).round(5).tolist()})
    img = cv2.GaussianBlur(img, (3, 3), 0)
    return img, objs, bg


def build_dataset(out_dir, n_train=300, n_val=60, ppm=None, size=640, seed=0):
    out = Path(out_dir)
    rng = np.random.default_rng(seed)
    for split, n in (("train", n_train), ("val", n_val)):
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
        truth = []
        for i in range(n):
            img, objs, bg = make_image(rng, ppm, (size, size))
            im_ppm = objs[0]["ppm"] if objs else (ppm or 0)
            name = f"{split}_{i:05d}"
            cv2.imwrite(str(out / "images" / split / f"{name}.jpg"), img,
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
            lines = ["0 " + " ".join(f"{x:.5f} {y:.5f}" for x, y in o["poly"]) for o in objs]
            (out / "labels" / split / f"{name}.txt").write_text("\n".join(lines) + "\n")
            truth.append({"image": f"images/{split}/{name}.jpg", "background": bg,
                          "px_per_mm": im_ppm,
                          "objects": [{k: v for k, v in o.items() if k not in ("poly", "ppm")} for o in objs]})
        (out / f"truth_{split}.json").write_text(json.dumps(truth))
    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\ntrain: images/train\nval: images/val\nnames:\n  0: specimen\n")
    return out
