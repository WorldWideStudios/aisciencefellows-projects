"""Synthetic 'insects on a white tray' images with known ground truth, so the
pipeline and notebook run before any real photos are in."""
from __future__ import annotations

import cv2
import numpy as np


def make_sample(n=25, px_per_mm=40.0, size=(900, 1200), seed=0,
                length_range=(0.4, 6.0), aspect_range=(2.0, 4.0)):
    rng = np.random.default_rng(seed)
    h, w = size
    img = np.full((h, w, 3), 235, np.uint8)
    img = (img + rng.normal(0, 4, img.shape)).clip(0, 255).astype(np.uint8)
    truth, placed = [], []
    for _ in range(n * 20):
        if len(truth) >= n:
            break
        L = rng.uniform(*length_range)
        W = L / rng.uniform(*aspect_range)
        cx, cy = rng.uniform(60, w - 60), rng.uniform(60, h - 60)
        r = L * px_per_mm / 2 + 8
        if any(np.hypot(cx - x, cy - y) < r + rr for x, y, rr in placed):
            continue
        ang = rng.uniform(0, 180)
        axes = (max(1, int(L * px_per_mm / 2)), max(1, int(W * px_per_mm / 2)))
        cv2.ellipse(img, (int(cx), int(cy)), axes, ang, 0, 360,
                    tuple(int(c) for c in rng.integers(20, 90, 3)), -1, cv2.LINE_AA)
        placed.append((cx, cy, r))
        truth.append({"cx": cx, "cy": cy, "length_mm": L, "width_mm": W})
    return img, truth
