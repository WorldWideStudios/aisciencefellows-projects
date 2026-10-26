"""Insect sizing from a USB-camera image with two independent models.

Model A: YOLO (ultralytics) detection/segmentation.
Model B: classical morphometrics (threshold + contours) with no learned weights.
`consensus()` pairs their detections and flags disagreements, so a size the arm
acts on has been measured twice by methods that fail differently.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np


@dataclass
class Measurement:
    cx: float              # centroid, px
    cy: float
    length_mm: float       # long axis of min-area rectangle
    width_mm: float        # short axis -> governs passage through square mesh
    area_mm2: float
    source: str            # "yolo" | "classical" | "consensus"
    conf: float = 1.0
    label: str = "insect"
    flag: str | None = None

    def to_dict(self):
        return asdict(self)


# ---------- calibration ----------

def px_per_mm_from_aruco(image: np.ndarray, marker_mm: float,
                         dictionary=cv2.aruco.DICT_4X4_50) -> float | None:
    """Scale from a printed ArUco marker of known side length in the field of view."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(dictionary))
    corners, ids, _ = det.detectMarkers(gray)
    if ids is None or len(corners) == 0:
        return None
    c = corners[0].reshape(4, 2)
    side_px = np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)])
    return float(side_px / marker_mm)


# ---------- shared geometry ----------

def _from_contour(cnt, px_per_mm, source, conf=1.0, label="insect") -> Measurement:
    (cx, cy), (w, h), _ = cv2.minAreaRect(cnt)
    long_px, short_px = max(w, h), min(w, h)
    area_px = cv2.contourArea(cnt)
    return Measurement(cx, cy, long_px / px_per_mm, short_px / px_per_mm,
                       area_px / px_per_mm ** 2, source, conf, label)


# ---------- Model B: classical ----------

def classical_measure(image: np.ndarray, px_per_mm: float,
                      min_area_mm2: float = 0.01, dark_on_light: bool = True,
                      roi_mask: np.ndarray | None = None) -> list[Measurement]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    flag = cv2.THRESH_BINARY_INV if dark_on_light else cv2.THRESH_BINARY
    _, bw = cv2.threshold(gray, 0, 255, flag + cv2.THRESH_OTSU)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    if roi_mask is not None:
        bw = cv2.bitwise_and(bw, roi_mask)
    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    min_px = min_area_mm2 * px_per_mm ** 2
    return [_from_contour(c, px_per_mm, "classical") for c in cnts
            if cv2.contourArea(c) >= min_px]


# ---------- Model A: YOLO ----------

class YoloMeasurer:
    """Wraps an ultralytics model. Segmentation weights give the best widths;
    box-only weights fall back to classical segmentation inside each box."""

    def __init__(self, weights: str = "yolo11n-seg.pt", conf: float = 0.25):
        from ultralytics import YOLO  # optional dependency
        self.model = YOLO(weights)
        self.conf = conf

    def __call__(self, image: np.ndarray, px_per_mm: float) -> list[Measurement]:
        res = self.model.predict(image, conf=self.conf, verbose=False)[0]
        names = res.names
        out: list[Measurement] = []
        if res.masks is not None:
            for poly, cls, cf in zip(res.masks.xy, res.boxes.cls, res.boxes.conf):
                cnt = np.asarray(poly, dtype=np.float32).reshape(-1, 1, 2)
                if len(cnt) >= 3:
                    out.append(_from_contour(cnt, px_per_mm, "yolo", float(cf),
                                             names[int(cls)]))
            return out
        for (x1, y1, x2, y2), cls, cf in zip(res.boxes.xyxy.cpu().numpy(),
                                             res.boxes.cls, res.boxes.conf):
            x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
            crop = image[y1:y2, x1:x2]
            sub = classical_measure(crop, px_per_mm)
            if sub:
                m = max(sub, key=lambda s: s.area_mm2)
                m.cx += x1; m.cy += y1
                m.source, m.conf, m.label = "yolo", float(cf), names[int(cls)]
                out.append(m)
        return out


# ---------- consensus ----------

def consensus(a: list[Measurement], b: list[Measurement], px_per_mm: float,
              match_mm: float = 1.0, rel_tol: float = 0.20) -> list[Measurement]:
    """Pair detections by centroid distance. Agreeing pairs are averaged;
    disagreements and unmatched detections are kept but flagged for review."""
    out, used = [], set()
    for ma in a:
        best, bd = None, match_mm * px_per_mm
        for j, mb in enumerate(b):
            d = np.hypot(ma.cx - mb.cx, ma.cy - mb.cy)
            if j not in used and d < bd:
                best, bd = j, d
        if best is None:
            ma.flag = f"only_{ma.source}"
            out.append(ma)
            continue
        used.add(best)
        mb = b[best]
        rel = abs(ma.width_mm - mb.width_mm) / max(ma.width_mm, mb.width_mm, 1e-9)
        m = Measurement((ma.cx + mb.cx) / 2, (ma.cy + mb.cy) / 2,
                        (ma.length_mm + mb.length_mm) / 2,
                        (ma.width_mm + mb.width_mm) / 2,
                        (ma.area_mm2 + mb.area_mm2) / 2,
                        "consensus", min(ma.conf, mb.conf), ma.label)
        if rel > rel_tol:
            m.flag = f"width_disagree_{rel:.0%}"
        out.append(m)
    for j, mb in enumerate(b):
        if j not in used:
            mb.flag = f"only_{mb.source}"
            out.append(mb)
    return out


def annotate(image: np.ndarray, ms: list[Measurement]) -> np.ndarray:
    vis = image.copy() if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    for m in ms:
        col = (0, 180, 0) if m.flag is None else (0, 0, 230)
        cv2.circle(vis, (int(m.cx), int(m.cy)), 4, col, -1)
        cv2.putText(vis, f"{m.length_mm:.2f}x{m.width_mm:.2f}mm",
                    (int(m.cx) + 6, int(m.cy) - 6), cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, col, 1, cv2.LINE_AA)
    return vis
