"""Teacher for museum specimen photos (UCSB-style layout: grey stage, white
paper labels with DataMatrix codes, cm/mm ruler along the top).

* ruler_px_per_mm: true scale from the ruler's mm ticks (FFT of the tick band),
  so pseudo-labels carry real millimetres, not a guessed px/mm.
* stage_mask: the grey, low-saturation stage; white paper labels, barcodes and
  the ruler are outside it, so they can never become 'specimens'.
* segment: specimens = pixels on the stage that differ from the stage colour
  (darker, lighter or coloured), with pins removed by opening.

Used by train.pseudo_label_specimens to make YOLO-seg labels and a real-mm
size table from photos that come without outlines.
"""
from __future__ import annotations

import cv2
import numpy as np

from .measure import _from_contour


def ruler_px_per_mm(img, search_frac=0.35, min_ppm=2.0, max_ppm=80.0):
    """Return (px_per_mm, confidence) from the ruler's mm ticks.
    Autocorrelation of the tick-band profile: the FIRST strong peak is the
    1 mm period (harmonics of thin ticks don't fool it the way an FFT peak
    can). Confidence = that peak's normalised autocorrelation (0-1)."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = g.shape
    best = (None, 0.0)
    for region in (g[: int(h * search_frac)], g[int(h * (1 - search_frac)):],
                   g[:, : int(w * search_frac)].T, g[:, int(w * (1 - search_frac)):].T):
        if region.shape[0] < 5 or region.shape[1] < 4 * max_ppm:
            continue
        dx = np.abs(np.diff(region, axis=1)).mean(axis=1)
        k = max(5, region.shape[0] // 40)
        sm = np.convolve(dx, np.ones(k) / k, mode="same")
        r0 = int(np.argmax(sm))
        prof = region[max(0, r0 - k // 2): r0 + k // 2 + 1].mean(axis=0)
        win = int(4 * max_ppm) | 1
        prof = prof - np.convolve(prof, np.ones(win) / win, mode="same")
        n = len(prof)
        f = np.fft.rfft(prof, 2 * n)
        ac = np.fft.irfft(f * np.conj(f))[:n]
        ac = ac / (ac[0] + 1e-9)
        lo, hi = int(min_ppm), min(int(max_ppm) + 2, n - 2)
        seg = ac[lo:hi]
        if seg.size < 3:
            continue
        thr = 0.5 * seg.max()
        peaks = [i for i in range(1, len(seg) - 1)
                 if seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1] and seg[i] > thr]
        if not peaks:
            continue
        i = peaks[0]
        a_, b_, c_ = seg[i - 1], seg[i], seg[i + 1]
        lag = lo + i + 0.5 * (a_ - c_) / (a_ - 2 * b_ + c_ + 1e-9)
        # a tick ruler repeats: autocorrelation must stay high at 2x..5x the period
        reps = [ac[max(0, round(m * lag) - 2): round(m * lag) + 3].max()
                for m in range(2, 6) if round(m * lag) + 3 < n]
        regular = len(reps) >= 3 and min(reps) > 0.35
        score = float(b_) if regular else 0.0
        if score > best[1]:
            best = (float(lag), score)
    return best


def stage_mask(img, sat_max=45, v_lo=110, v_hi=222):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s, v = hsv[..., 1], hsv[..., 2]
    grey = ((s < sat_max) & (v > v_lo) & (v < v_hi)).astype(np.uint8) * 255
    k = max(3, min(img.shape[:2]) // 100)
    grey = cv2.morphologyEx(grey, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(grey)
    if n <= 1:
        return np.zeros_like(grey)
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    m = (lab == i).astype(np.uint8) * 255
    # fill holes (the specimen itself sits inside the stage)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(m)
    cv2.drawContours(filled, cnts, -1, 255, -1)
    return filled


def segment(img, px_per_mm, min_area_mm2=0.3, pin_mm=0.35, dev=28, sat_min=55,
            exclude_bright=True):
    """Specimen contours on the stage (polygons in px) + Measurements in mm."""
    st = stage_mask(img)
    if not st.any():
        return [], []
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    inner = cv2.erode(st, np.ones((15, 15), np.uint8))
    bg = np.median(g[inner > 0]) if (inner > 0).any() else np.median(g)
    fg = ((np.abs(g.astype(int) - bg) > dev) | (hsv[..., 1] > sat_min)).astype(np.uint8) * 255
    fg &= inner
    if exclude_bright:   # silver pins / glare; turn off for pale objects (white rice)
        fg[(hsv[..., 2] > 225) & (hsv[..., 1] < 35)] = 0
    # paper labels: only LARGE bright regions (a pin is bright but thin), filled so
    # barcodes/text printed on them are excluded too, plus a small margin
    bright = ((hsv[..., 2] > 228) & (hsv[..., 1] < 35)).astype(np.uint8) * 255
    bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, np.ones((max(3, int(px_per_mm // 4) | 1),) * 2, np.uint8))
    cnts_p, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    paper = np.zeros_like(bright)
    for cp in cnts_p:
        if cv2.contourArea(cp) > (5 * px_per_mm) ** 2:
            cv2.drawContours(paper, [cp], -1, 255, -1)
    paper = cv2.dilate(paper, np.ones((9, 9), np.uint8))
    fg[paper > 0] = 0
    kp = max(3, int(pin_mm * px_per_mm) | 1)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kp, kp)))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kp * 2 + 1,) * 2))
    cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_px = min_area_mm2 * px_per_mm ** 2
    polys, ms = [], []
    for c in cnts:
        if cv2.contourArea(c) < min_px:
            continue
        eps = 0.002 * cv2.arcLength(c, True)
        c = cv2.approxPolyDP(c, eps, True)
        if len(c) < 3:
            continue
        m = _from_contour(c, px_per_mm, "stage_classical")
        if m.length_mm / max(m.width_mm, 1e-6) > 12:   # ruler edges, pins, seams
            continue
        polys.append(c.reshape(-1, 2))
        ms.append(m)
    return polys, ms


def preview(img, polys, ms, ppm, conf):
    vis = img.copy()
    t = max(2, img.shape[1] // 400)
    for p, m in zip(polys, ms):
        cv2.polylines(vis, [p.astype(np.int32)], True, (0, 0, 255), t)
        cv2.putText(vis, f"{m.length_mm:.1f}x{m.width_mm:.1f}mm", (int(m.cx), int(m.cy)),
                    cv2.FONT_HERSHEY_SIMPLEX, t * 0.5, (0, 0, 255), t)
    cv2.putText(vis, f"{ppm:.1f}px/mm conf {conf:.0f}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX,
                t * 0.6, (255, 0, 0), t)
    return vis


_YOLOE = {}


def segment_yoloe(img, px_per_mm, prompts=("insect",), weights="yoloe-11s-seg.pt", conf=0.25,
                  min_area_mm2=0.3, length_range=(1.0, 30.0)):
    """Zero-shot teacher: open-vocabulary YOLOE segmentation prompted with text
    ('insect'), then the same exclusions as `segment` (paper labels, image
    border) and the 1-30 mm size window. Runs locally (ultralytics)."""
    from ultralytics import YOLOE
    key = (weights, tuple(prompts))
    if key not in _YOLOE:
        m = YOLOE(weights)
        m.set_classes(list(prompts), m.get_text_pe(list(prompts)))
        _YOLOE[key] = m
    res = _YOLOE[key].predict(img, conf=conf, verbose=False, retina_masks=True)[0]
    if res.masks is None:
        return [], []
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    paper = ((hsv[..., 2] > 228) & (hsv[..., 1] < 35)).astype(np.uint8)
    h, w = img.shape[:2]
    polys, ms = [], []
    for xy, cf in zip(res.masks.xy, res.boxes.conf.cpu().numpy()):
        if len(xy) < 3:
            continue
        c = np.asarray(xy, np.float32).reshape(-1, 1, 2)
        x, y, bw, bh = cv2.boundingRect(c.astype(np.int32))
        if x <= 2 or y <= 2 or x + bw >= w - 2 or y + bh >= h - 2:
            continue                                   # clipped by the frame
        mask = np.zeros((h, w), np.uint8)
        cv2.fillPoly(mask, [c.astype(np.int32)], 1)
        if (paper[mask > 0].mean() if mask.any() else 1) > 0.5:
            continue                                   # mostly on a label
        if cv2.contourArea(c) < min_area_mm2 * px_per_mm ** 2:
            continue
        m = _from_contour(c, px_per_mm, "yoloe", float(cf))
        if not (length_range[0] <= m.length_mm <= length_range[1]):
            continue
        polys.append(c.reshape(-1, 2)); ms.append(m)
    return polys, ms
