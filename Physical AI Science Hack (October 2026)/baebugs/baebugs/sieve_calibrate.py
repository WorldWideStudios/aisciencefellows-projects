"""Measure a mesh's real aperture from a top-down image of it, so the planner
uses measured openings instead of nominal ones. Works for woven screen, printed
grids, hex wire and perforated round holes: each opening is a bright blob when
the mesh is backlit (or dark on a light background with dark_openings=True).

aperture = narrowest dimension of each opening (min-area-rect short side;
for round holes this is the diameter). Reports median and spread so a worn or
warped mesh shows up as a wide spread.
"""
from __future__ import annotations

import cv2
import numpy as np


def measure_aperture(image, px_per_mm, dark_openings=False, min_area_mm2=0.05,
                     max_area_mm2=400):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    flag = cv2.THRESH_BINARY_INV if dark_openings else cv2.THRESH_BINARY
    _, bw = cv2.threshold(gray, 0, 255, flag + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    lo, hi = min_area_mm2 * px_per_mm ** 2, max_area_mm2 * px_per_mm ** 2
    h, w = gray.shape
    sides = []
    for c in cnts:
        a = cv2.contourArea(c)
        x, y, cw, ch = cv2.boundingRect(c)
        if not (lo <= a <= hi) or x == 0 or y == 0 or x + cw >= w or y + ch >= h:
            continue  # skip clipped openings at the image edge
        (_, _), (rw, rh), _ = cv2.minAreaRect(c)
        sides.append(min(rw, rh) / px_per_mm)
    if not sides:
        return None
    s = np.array(sides)
    return {"aperture_mm": float(np.median(s)), "p10_mm": float(np.percentile(s, 10)),
            "p90_mm": float(np.percentile(s, 90)), "n_openings": int(s.size),
            "cv": float(s.std() / s.mean())}


def synthetic_mesh(aperture_mm=1.2, wire_mm=0.3, px_per_mm=30, size=(600, 800),
                   round_holes=False):
    """Backlit mesh image with known aperture, for tests/demo."""
    img = np.zeros(size, np.uint8)
    pitch = (aperture_mm + wire_mm) * px_per_mm
    for y in np.arange(pitch / 2, size[0], pitch):
        for x in np.arange(pitch / 2, size[1], pitch):
            if round_holes:
                cv2.circle(img, (int(x), int(y)), int(aperture_mm * px_per_mm / 2), 255, -1)
            else:
                h = aperture_mm * px_per_mm / 2
                cv2.rectangle(img, (int(x - h), int(y - h)), (int(x + h), int(y + h)), 255, -1)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
