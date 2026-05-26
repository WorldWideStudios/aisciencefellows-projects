#!/usr/bin/env python3
from __future__ import annotations
"""
cryovision.py — Identify labels in a 10x10 cryogenic freezer box using Claude vision.

Usage:
    python cryovision.py --image box.jpg
    python cryovision.py --image box.jpg --output results.json
    python cryovision.py --image box.jpg --output results.csv
    python cryovision.py --image box.jpg --fast   # row strips, no thinking
    python cryovision.py --image box.jpg --debug  # save preprocessed image + grid overlay
"""

import argparse
import base64
import csv
import io
import json
import os
import sys
from pathlib import Path

import anthropic
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROWS = list("ABCDEFGHIJ")
COLS = [str(n) for n in range(1, 11)]

CELL_SIZE = 160   # px — each cell is resized to this before compositing
CELL_GAP  = 4     # px — gap between cells in composite
LABEL_H   = 22    # px — height of column-number label bar

SYSTEM_PROMPT = """You are a laboratory assistant specializing in cryogenic sample storage.
You have excellent attention to detail and can read small, partially obscured, and handwritten
text on tube caps and labels."""


# ─── OpenCV preprocessing ────────────────────────────────────────────────────

def order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def correct_perspective(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = img.shape[:2]
    img_area = h * w

    best_quad, best_score = None, 0.0
    # Only consider quads that are 15–92% of the image (rules out full-frame noise
    # and tiny shapes, while not assuming the box fills the whole image)
    min_area = img_area * 0.15
    max_area = img_area * 0.92

    # Try several blur levels so faint edges on light-coloured boxes are caught
    for blur_k in ((5, 5), (9, 9), (13, 13)):
        edges = cv2.Canny(cv2.GaussianBlur(gray, blur_k, 0), 30, 120)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if not (min_area < area < max_area):
                continue
            peri = cv2.arcLength(c, True)
            # Try a few approximation epsilons — looser eps catches boxes whose
            # corners aren't perfectly sharp
            for eps in (0.01, 0.02, 0.04):
                approx = cv2.approxPolyDP(c, eps * peri, True)
                if len(approx) != 4:
                    continue
                pts = order_points(approx.reshape(4, 2).astype(np.float32))
                sides = [np.linalg.norm(pts[(i + 1) % 4] - pts[i]) for i in range(4)]
                # Cryoboxes are square; prefer larger AND more square quads
                squareness = min(sides) / max(sides) if max(sides) > 0 else 0
                score = area * squareness
                if score > best_score:
                    best_quad, best_score = approx, score

    if best_quad is None:
        return img

    pts = order_points(best_quad.reshape(4, 2).astype(np.float32))
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    return cv2.warpPerspective(img, cv2.getPerspectiveTransform(pts, dst), (w, h))


def enhance_contrast(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return cv2.cvtColor(cv2.merge([clahe.apply(l), a, b]), cv2.COLOR_LAB2BGR)


def sharpen(img: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(img, (0, 0), 3)
    return cv2.addWeighted(img, 1.5, blur, -0.5, 0)


def preprocess_cv(image_path: Path) -> np.ndarray:
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Error: could not read image: {image_path}", file=sys.stderr)
        sys.exit(1)
    img = correct_perspective(img)
    img = enhance_contrast(img)
    img = sharpen(img)
    return img


# ─── Grid detection ───────────────────────────────────────────────────────────

def equal_split(size: int) -> list[int]:
    return [int(size * i / 10) for i in range(11)]


def centers_to_boundaries(centers: np.ndarray, size: int) -> list[int]:
    """Convert 10 cell centres to 11 boundary lines."""
    centers = np.sort(centers)
    # Outer boundaries use the actual gap to the nearest neighbour,
    # not the median — so the first and last cells aren't undersized.
    first_gap = (centers[1] - centers[0]) if len(centers) > 1 else size / 10
    last_gap  = (centers[-1] - centers[-2]) if len(centers) > 1 else size / 10
    boundaries = [int(centers[0] - first_gap / 2)]
    for i in range(len(centers) - 1):
        boundaries.append(int((centers[i] + centers[i + 1]) / 2))
    boundaries.append(int(centers[-1] + last_gap / 2))
    return [max(0, min(size, b)) for b in boundaries]


def find_natural_clusters(coords: np.ndarray, gap_ratio: float = 3.0) -> np.ndarray:
    """
    Find natural 1-D clusters by splitting wherever the gap between consecutive
    sorted values is significantly larger than the typical within-cluster spread.
    Returns cluster medians — however many there actually are.
    """
    coords = np.sort(coords)
    if len(coords) < 2:
        return coords
    gaps = np.diff(coords)
    threshold = gap_ratio * np.median(gaps)
    split_pts = np.where(gaps > threshold)[0]
    clusters = np.split(coords, split_pts + 1)
    return np.array([float(np.median(c)) for c in clusters])


def find_clusters_adaptive(coords: np.ndarray, target_n: int = 10) -> np.ndarray:
    """
    Produce exactly target_n cluster centres from 1-D coordinates.

    Strategy:
    1. Try gap-ratio clustering from loose → tight; if any ratio gives exactly
       target_n clusters, use that result.
    2. If no ratio hits exactly target_n, fall back to percentile binning:
       sort all coords, split into target_n equal-count bins, return median of each.
       This guarantees exactly target_n centres regardless of distribution.
    """
    best_clusters, best_diff = None, float("inf")
    for ratio in (7.0, 6.0, 5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0):
        clusters = find_natural_clusters(coords, gap_ratio=ratio)
        diff = abs(len(clusters) - target_n)
        if diff < best_diff:
            best_diff, best_clusters = diff, clusters
        if diff == 0:
            return best_clusters  # exact match — done

    if len(best_clusters) > target_n:
        # Too many clusters (e.g. 12 cols instead of 10): percentile binning merges them.
        # Safe here because detections are spread across the full axis.
        sorted_coords = np.sort(coords)
        bins = np.array_split(sorted_coords, target_n)
        return np.array([float(np.median(b)) for b in bins if len(b) > 0])
    else:
        # Too few clusters (e.g. 8 rows instead of 10): return what we found.
        # build_full_centers will interpolate/extrapolate the missing positions.
        # Percentile binning would be wrong here — it packs bins into the dense region
        # and squishes sparse rows (e.g. bottom rows with fewer detections) together.
        return best_clusters


def build_full_centers(detected: np.ndarray, n: int, image_size: int) -> np.ndarray:
    """
    Given k detected cluster centres, produce n centres that correctly handle
    skip-gaps (empty rows/cols between occupied ones).

    1. Estimates base spacing from tight adjacent-cluster gaps (ignores large
       skip-gaps so they don't inflate the estimate).
    2. Assigns each detected cluster a grid-slot index by rounding diff/base,
       so a gap of ~3× base gets slot index +3 (two empty rows in between).
    3. Fills missing slots by linear interpolation between known slots, or
       linear extrapolation before/after the detected range.
    """
    detected = np.sort(detected)
    k = len(detected)
    if k >= n:
        return detected[:n]
    if k == 1:
        return detected[0] + (image_size / n) * np.arange(n)

    diffs = np.diff(detected)
    # Base spacing: median of the smaller diffs, ignoring large skip-gaps
    med = float(np.median(diffs))
    small = diffs[diffs < 2.0 * med]
    base = float(np.median(small)) if len(small) else med

    # Assign each detected centre a slot index
    slots: list[int] = [0]
    for d in diffs:
        slots.append(slots[-1] + max(1, round(float(d) / base)))

    slot_map = {s: float(p) for s, p in zip(slots, detected.tolist())}

    def interp(target: int) -> float:
        lo = [s for s in slots if s <= target]
        hi = [s for s in slots if s >= target]
        if lo and hi:
            s0, s1 = lo[-1], hi[0]
            if s0 == s1:
                return slot_map[s0]
            t = (target - s0) / (s1 - s0)
            return slot_map[s0] + t * (slot_map[s1] - slot_map[s0])
        if lo:                          # extrapolate forward
            s0 = lo[-1]
            step = base if len(lo) < 2 else (slot_map[lo[-1]] - slot_map[lo[-2]]) / (lo[-1] - lo[-2])
            return slot_map[s0] + (target - s0) * step
        # extrapolate backward
        s1 = hi[0]
        step = base if len(hi) < 2 else (slot_map[hi[1]] - slot_map[hi[0]]) / (hi[1] - hi[0])
        return slot_map[s1] - (s1 - target) * step

    return np.array([interp(i) for i in range(n)])


def detect_tubes_rfdetr(img: np.ndarray) -> np.ndarray | None:
    """
    Detect tube caps using the trained RF-DETR model via Roboflow inference.
    Returns a circles-format array (1, N, 3) with columns (cx, cy, r),
    or None if RF-DETR is unavailable, unconfigured, or finds nothing.
    """
    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        return None
    try:
        from inference import get_model  # pip install inference
    except ImportError:
        print("  RF-DETR: inference package not installed — pip install inference",
              file=sys.stderr)
        return None

    model_id = os.environ.get("ROBOFLOW_MODEL_ID", "cryovvision/1")
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    try:
        model  = get_model(model_id, api_key=api_key)
        result = model.infer(pil_img, confidence=0.15)
    except Exception as exc:
        print(f"  RF-DETR inference error: {exc}", file=sys.stderr)
        return None

    preds = result[0].predictions if result else []
    if not preds:
        print("  RF-DETR: no tubes detected", file=sys.stderr)
        return None

    print(f"  RF-DETR: {len(preds)} tubes detected", file=sys.stderr)
    circles = np.array([[
        [p.x, p.y, max(p.width, p.height) / 2] for p in preds
    ]], dtype=np.float32)
    return circles


def detect_tubes_hough(img: np.ndarray) -> np.ndarray | None:
    """
    Detect tube caps using HoughCircles. Returns circles array or None.
    """
    gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    short   = min(img.shape[:2])
    min_r    = int(short / 22)
    max_r    = int(short / 13)
    min_dist = int(short / 10)

    circles = None
    for param2 in (50, 40, 30, 22):
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=1,
            minDist=min_dist, param1=80, param2=param2,
            minRadius=min_r, maxRadius=max_r,
        )
        n = 0 if circles is None else len(circles[0])
        print(f"  HoughCircles: param2={param2} → {n} circles", file=sys.stderr)
        if circles is not None and n >= 20:
            break
    return circles


def fit_grid(circles: np.ndarray, h: int, w: int) -> tuple[list[int], list[int]]:
    """
    Fit a 10×10 grid to detected circle centres.
    Filters edge circles, clusters remaining centres, extrapolates to 10 cols/rows.
    """
    short  = min(h, w)
    margin = short * 0.04
    mask = (
        (circles[0, :, 0] > margin) & (circles[0, :, 0] < w - margin) &
        (circles[0, :, 1] > margin) & (circles[0, :, 1] < h - margin)
    )
    kept = circles[0][mask]
    if len(kept) < 4:
        return equal_split(h), equal_split(w)

    cx, cy = kept[:, 0], kept[:, 1]
    col_natural = find_natural_clusters(cx)
    row_natural = find_natural_clusters(cy)
    print(f"  Grid fit: {len(kept)} circles → "
          f"{len(col_natural)} col clusters, {len(row_natural)} row clusters",
          file=sys.stderr)

    col_centers = build_full_centers(col_natural, 10, w)
    row_centers = build_full_centers(row_natural, 10, h)
    return centers_to_boundaries(row_centers, h), centers_to_boundaries(col_centers, w)


def detect_grid(img: np.ndarray) -> tuple[list[int], list[int], object]:
    """
    Detect tube positions and fit a 10×10 grid.
    Uses RF-DETR if ROBOFLOW_API_KEY is set, otherwise falls back to HoughCircles.
    Returns (y_lines, x_lines, circles_or_None).
    """
    h, w = img.shape[:2]

    # Try RF-DETR first (trained model, handles all cap types)
    rf_circles = detect_tubes_rfdetr(img)
    rf_count = len(rf_circles[0]) if rf_circles is not None else 0

    # Always also run HoughCircles — used for grid geometry when RF-DETR is sparse
    hough_circles = detect_tubes_hough(img)
    hough_count = len(hough_circles[0]) if hough_circles is not None else 0

    # Grid source: RF-DETR when it has good coverage (>=40), else HoughCircles.
    # HoughCircles finds more tubes in sparse boxes (including white caps RF-DETR misses),
    # giving better spatial coverage for grid extrapolation.
    # Presence map: always RF-DETR when available — more precise, no rim false-positives.
    MIN_RFDETR_FOR_GRID = 40
    if rf_count >= MIN_RFDETR_FOR_GRID:
        grid_circles = rf_circles
        print(f"  RF-DETR: {rf_count} detections — using RF-DETR for grid", file=sys.stderr)
    elif hough_count >= 20:
        grid_circles = hough_circles
        src = "HoughCircles" if rf_count < 4 else f"HoughCircles (RF-DETR sparse: {rf_count})"
        print(f"  Using {src} for grid geometry", file=sys.stderr)
    elif rf_count >= 4:
        grid_circles = rf_circles
        print(f"  RF-DETR: {rf_count} detections (HoughCircles insufficient) — using RF-DETR for grid",
              file=sys.stderr)
    else:
        grid_circles = None
        print("  No usable detections for grid", file=sys.stderr)

    presence_circles = rf_circles if rf_count >= 4 else hough_circles

    if grid_circles is not None and len(grid_circles[0]) >= 4:
        cx = grid_circles[0, :, 0]
        cy = grid_circles[0, :, 1]
        col_natural = find_clusters_adaptive(cx, 10)
        row_natural = find_clusters_adaptive(cy, 10)
        print(f"  Grid fit: {len(grid_circles[0])} points → "
              f"{len(col_natural)} col clusters, {len(row_natural)} row clusters",
              file=sys.stderr)
        col_centers = build_full_centers(col_natural, 10, w)
        row_centers = build_full_centers(row_natural, 10, h)
        x_lines = centers_to_boundaries(col_centers, w)
        y_lines = centers_to_boundaries(row_centers, h)
        # Return both: presence_circles for analysis, grid_circles for debug overlay
        return y_lines, x_lines, presence_circles, grid_circles

    print("  Not enough detections — using equal division", file=sys.stderr)
    return equal_split(h), equal_split(w), None, None


# ─── Cell cropping & compositing ─────────────────────────────────────────────

def assign_circles_to_grid(
    circles: np.ndarray, img_w: int, img_h: int
) -> dict[tuple[int, int], tuple[float, float, float]]:
    """
    Assign each detected circle to a (row_i, col_j) grid position (0-indexed).
    Uses cluster centres to map positions — no boundary lines needed.
    Returns {(row_i, col_j): (cx, cy, r)}.
    """
    pts = circles[0]
    cx_all, cy_all = pts[:, 0], pts[:, 1]

    row_natural = find_clusters_adaptive(cy_all, 10)
    col_natural = find_clusters_adaptive(cx_all, 10)
    row_centers = build_full_centers(row_natural, 10, img_h)
    col_centers = build_full_centers(col_natural, 10, img_w)

    assignments: dict[tuple[int, int], tuple[float, float, float]] = {}
    for cx, cy, r in pts:
        row_i = int(np.argmin(np.abs(row_centers - cy)))
        col_j = int(np.argmin(np.abs(col_centers - cx)))
        key = (row_i, col_j)
        if key not in assignments:
            assignments[key] = (cx, cy, r)
        else:
            # Keep whichever detection is closer to the cluster centre
            ocx, ocy, _ = assignments[key]
            new_d = (cx - col_centers[col_j]) ** 2 + (cy - row_centers[row_i]) ** 2
            old_d = (ocx - col_centers[col_j]) ** 2 + (ocy - row_centers[row_i]) ** 2
            if new_d < old_d:
                assignments[key] = (cx, cy, r)

    return assignments


def crop_circle_composite(
    pil_img: Image.Image,
    row_cells: list[tuple[int, float, float, float]],
    row_label: str,
) -> Image.Image:
    """
    Make a row composite by cropping a square centred on each detected circle.
    row_cells: list of (col_j, cx, cy, r) sorted by col_j.
    Column numbers are printed above each crop so Claude can orient itself.
    """
    n = len(row_cells)
    half = max(int(np.median([r for _, _, _, r in row_cells]) * 1.5), CELL_SIZE // 2)

    total_w = CELL_SIZE * n + CELL_GAP * (n - 1)
    total_h = CELL_SIZE + LABEL_H
    composite = Image.new("RGB", (total_w, total_h), (50, 50, 50))
    draw = ImageDraw.Draw(composite)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        font = ImageFont.load_default()

    for idx, (col_j, cx, cy, r) in enumerate(row_cells):
        x_off = idx * (CELL_SIZE + CELL_GAP)
        draw.text((x_off + CELL_SIZE // 2, 3), str(col_j + 1),
                  fill=(220, 220, 220), font=font, anchor="mt")
        x1 = max(0, int(cx) - half)
        y1 = max(0, int(cy) - half)
        x2 = min(pil_img.width, int(cx) + half)
        y2 = min(pil_img.height, int(cy) + half)
        crop = pil_img.crop((x1, y1, x2, y2)).resize((CELL_SIZE, CELL_SIZE), Image.LANCZOS)
        composite.paste(crop, (x_off, LABEL_H))

    return composite


def crop_cells(pil_img: Image.Image,
               y_lines: list[int],
               x_lines: list[int]) -> list[list[Image.Image]]:
    """Return a 10×10 list of cropped cell images (used for --fast mode)."""
    cells = []
    for i in range(10):
        row_cells = []
        for j in range(10):
            cell = pil_img.crop((x_lines[j], y_lines[i], x_lines[j+1], y_lines[i+1]))
            row_cells.append(cell)
        cells.append(row_cells)
    return cells


def make_row_composite(cells: list[Image.Image], row_label: str) -> Image.Image:
    """
    Tile 10 cell crops into one labelled composite image.
    Column numbers (1-10) are printed above each cell so Claude can orient itself.
    """
    total_w = CELL_SIZE * 10 + CELL_GAP * 9
    total_h = CELL_SIZE + LABEL_H
    composite = Image.new("RGB", (total_w, total_h), (50, 50, 50))
    draw = ImageDraw.Draw(composite)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        font = ImageFont.load_default()

    for j, cell in enumerate(cells):
        x_off = j * (CELL_SIZE + CELL_GAP)

        # Column label
        col_label = str(j + 1)
        draw.text((x_off + CELL_SIZE // 2, 3), col_label,
                  fill=(220, 220, 220), font=font, anchor="mt")

        # Cell image
        resized = cell.resize((CELL_SIZE, CELL_SIZE), Image.LANCZOS)
        composite.paste(resized, (x_off, LABEL_H))

    return composite


def save_debug(cv_img: np.ndarray,
               assignments: dict[tuple[int, int], tuple[float, float, float]],
               out_path: Path) -> None:
    """
    Save preprocessed image with each detected tube circled and labeled
    with its assigned grid position (e.g. A3, G7).
    """
    debug = cv_img.copy()
    h, w = debug.shape[:2]
    font_scale = max(w, h) / 3000
    for (row_i, col_j), (cx, cy, r) in assignments.items():
        cx, cy, r = int(round(cx)), int(round(cy)), int(round(r))
        cv2.circle(debug, (cx, cy), r, (255, 255, 0), 2)
        label = f"{ROWS[row_i]}{col_j + 1}"
        cv2.putText(debug, label, (cx - r // 2, cy - r - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 0), 1,
                    cv2.LINE_AA)
    cv2.imwrite(str(out_path), debug)
    print(f"  Debug image saved: {out_path}", file=sys.stderr)


# ─── Image encoding ───────────────────────────────────────────────────────────

def encode_pil(img: Image.Image) -> tuple[str, str]:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return base64.standard_b64encode(buf.getvalue()).decode(), "image/jpeg"


# ─── Claude analysis ──────────────────────────────────────────────────────────

def parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.splitlines() if not l.startswith("```")).strip()
    return json.loads(raw)


def make_cell_prompt(row: str) -> str:
    positions = [f"{row}{c}" for c in COLS]
    return f"""This image shows row {row} of a 10×10 cryogenic freezer storage box.
It contains 10 individual tube crops arranged left to right, labeled 1–10 at the top.
Each crop is a single tube cap viewed from above.

The positions are: {", ".join(positions)} (left to right).

For each crop, answer ONE question first: is there a physical tube here?

A TUBE is present when you see a circular or oval cap surface (plastic or coloured cap, possibly with handwritten text or markings on it).

A slot is EMPTY when you see cardboard walls forming a square compartment, an open hole, or just the beige/cream box material — no circular cap visible. Return null.

If a tube IS present:
- Return any readable text, ID code, or gene name written on the cap
- If no text is readable, return the cap color (e.g. "white cap", "red cap")

Empty slots are very common. Do not describe cardboard, box walls, shadows, or empty compartments — just return null.

Respond with ONLY valid JSON, no prose, no markdown:
{{
  "{positions[0]}": "...",
  ...
  "{positions[-1]}": "..."
}}

Include all 10 positions."""


def make_circle_prompt(row: str, col_indices: list[int]) -> str:
    """Prompt for circle-based crops: only occupied positions are shown."""
    positions = [f"{row}{j + 1}" for j in col_indices]
    col_nums = ", ".join(str(j + 1) for j in col_indices)
    return f"""This image shows {len(positions)} tube cap(s) from row {row} of a cryogenic freezer box.
The crops are arranged left to right. Column numbers are labeled above each crop: {col_nums}.
Each crop is centered directly on a detected tube cap.

Positions shown: {", ".join(positions)}.

For each tube cap, return the text, ID code, or label written on it.
If no text is readable, return the cap color (e.g. "white cap", "green cap").

These are all confirmed occupied — do not return null.

Respond with ONLY valid JSON:
{{
  "{positions[0]}": "...",
  ...
  "{positions[-1]}": "..."
}}"""


def make_row_strip_prompt(row: str) -> str:
    positions = [f"{row}{c}" for c in COLS]
    return f"""This image is row {row} of a 10×10 cryogenic freezer storage box —
a horizontal strip with 10 tubes from left to right: {", ".join(positions)}.

For each slot: if a physical tube is present return its label text or cap color; if the slot is empty (cardboard walls, open hole) return null. Do NOT describe empty cardboard.
Respond with ONLY valid JSON covering all 10 positions."""


def call_claude(
    client: anthropic.Anthropic,
    img: Image.Image,
    prompt: str,
    use_thinking: bool,
    row: str,
) -> dict[str, str | None]:
    image_data, media_type = encode_pil(img)
    kwargs: dict = dict(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": media_type, "data": image_data}},
            {"type": "text", "text": prompt},
        ]}],
    )
    if use_thinking:
        kwargs["thinking"] = {"type": "adaptive"}

    response = client.messages.create(**kwargs)
    raw = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return parse_json(raw)
    except json.JSONDecodeError as exc:
        print(f"  Warning: could not parse row {row}: {exc}", file=sys.stderr)
        return {f"{row}{c}": None for c in COLS}


# ─── Main pipelines ───────────────────────────────────────────────────────────

def build_presence_map(circles: np.ndarray | None,
                        y_lines: list[int],
                        x_lines: list[int]) -> list[list[bool]]:
    """
    Return a 10×10 boolean grid: True where a detected circle centre falls
    inside the cell, False for confirmed-empty cells.
    If no circle data is available every cell is assumed occupied.
    """
    if circles is None:
        return [[True] * 10 for _ in range(10)]
    presence = [[False] * 10 for _ in range(10)]
    for cx, cy, _ in circles[0]:
        for i in range(10):
            if not (y_lines[i] <= cy < y_lines[i + 1]):
                continue
            for j in range(10):
                if x_lines[j] <= cx < x_lines[j + 1]:
                    presence[i][j] = True
    return presence


def analyze_box_cells(image_path: Path, debug: bool) -> dict[str, str | None]:
    """
    Full pipeline:
      1. OpenCV preprocessing
      2. Detect tube circles (RF-DETR → HoughCircles fallback)
      3. Assign each circle to a (row, col) grid position directly from
         circle centres — no boundary lines needed
      4. Crop a square centred on each detected tube; composite by row
      5. Send each occupied row to Claude; empty cells stay null
    """
    print("Preprocessing image…", file=sys.stderr)
    cv_img = preprocess_cv(image_path)
    h, w = cv_img.shape[:2]
    pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

    # Detect circles
    print("Detecting tubes…", file=sys.stderr)
    rf_circles  = detect_tubes_rfdetr(cv_img)
    rf_count    = len(rf_circles[0]) if rf_circles is not None else 0
    hough_circles = detect_tubes_hough(cv_img)
    hough_count = len(hough_circles[0]) if hough_circles is not None else 0

    # Prefer RF-DETR (precise); fall back to HoughCircles
    circles = rf_circles if rf_count >= 4 else hough_circles

    client = anthropic.Anthropic()
    grid: dict[str, str | None] = {f"{r}{c}": None for r in ROWS for c in COLS}

    if circles is None or len(circles[0]) == 0:
        print("  No tube detections — all positions null", file=sys.stderr)
        return grid

    # Assign each circle to a grid position
    assignments = assign_circles_to_grid(circles, w, h)
    print(f"  {len(assignments)}/100 positions occupied", file=sys.stderr)

    if debug:
        save_debug(cv_img, assignments,
                   image_path.parent / f"{image_path.stem}_debug.jpg")

    # Group by row index
    by_row: dict[int, list[tuple[int, float, float, float]]] = {}
    for (row_i, col_j), (cx, cy, r) in assignments.items():
        by_row.setdefault(row_i, []).append((col_j, cx, cy, r))

    print("Analyzing rows (circle crops, thinking enabled)…", file=sys.stderr)
    for i, row in enumerate(ROWS):
        if i not in by_row:
            print(f"  Row {row}: no circles — skipping", file=sys.stderr)
            continue
        row_cells = sorted(by_row[i], key=lambda x: x[0])  # sort by col_j
        col_indices = [c[0] for c in row_cells]
        print(f"  Row {row} ({i+1}/10) — cols {[j+1 for j in col_indices]}…",
              file=sys.stderr)
        composite = crop_circle_composite(pil_img, row_cells, row)
        result = call_claude(client, composite,
                             make_circle_prompt(row, col_indices),
                             use_thinking=True, row=row)
        for col_j, _, _, _ in row_cells:
            pos = f"{row}{col_j + 1}"
            grid[pos] = result.get(pos)

    return grid


def analyze_box_fast(image_path: Path) -> dict[str, str | None]:
    """Fast mode: row strips, no thinking."""
    print("Preprocessing image…", file=sys.stderr)
    cv_img = preprocess_cv(image_path)
    pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
    w, h = pil_img.size
    row_h = h // 10

    client = anthropic.Anthropic()
    grid: dict[str, str | None] = {}

    print("Analyzing rows (strip mode, no thinking)…", file=sys.stderr)
    for i, row in enumerate(ROWS):
        print(f"  Row {row} ({i+1}/10)…", file=sys.stderr)
        y1 = i * row_h
        y2 = (i + 1) * row_h if i < 9 else h
        strip = pil_img.crop((0, y1, w, y2))
        grid.update(call_claude(client, strip, make_row_strip_prompt(row),
                                use_thinking=False, row=row))

    for r in ROWS:
        for c in COLS:
            grid.setdefault(f"{r}{c}", None)
    return grid


# ─── Display ──────────────────────────────────────────────────────────────────

def print_grid(grid: dict[str, str | None]) -> None:
    max_label = max((len(str(v)) for v in grid.values() if v is not None), default=4)
    cell_width = max(max_label, 4)

    header = "   " + "  ".join(str(c).center(cell_width) for c in COLS)
    print()
    print(header)
    print("-" * len(header))
    for row in ROWS:
        cells = []
        for col in COLS:
            label = grid.get(f"{row}{col}")
            cells.append("·" * cell_width if label is None
                         else str(label).center(cell_width)[:cell_width])
        print(f"{row}  " + "  ".join(cells))
    print()
    filled = sum(1 for v in grid.values() if v is not None)
    print(f"Filled: {filled}/100   Empty/unread: {100 - filled}/100")
    print()


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Identify labels in a 10×10 cryogenic freezer box using Claude vision.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python cryovision.py --image box.jpg\n"
            "  python cryovision.py --image box.jpg --output results.csv\n"
            "  python cryovision.py --image box.jpg --fast\n"
            "  python cryovision.py --image box.jpg --debug"
        ),
    )
    parser.add_argument("--image", required=True, metavar="FILE",
                        help="Path to the freezer box image (JPEG, PNG, GIF, WebP)")
    parser.add_argument("--output", metavar="FILE",
                        help="Save results to .json or .csv (default: print to stdout)")
    parser.add_argument("--fast", action="store_true",
                        help="Row-strip mode, no thinking — faster and cheaper")
    parser.add_argument("--debug", action="store_true",
                        help="Save a debug image showing the detected grid overlay")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: file not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    if args.fast:
        print("Mode: fast (row strips, no thinking)", file=sys.stderr)
        grid = analyze_box_fast(image_path)
    else:
        print("Mode: accurate (cell crops + grid detection + thinking)", file=sys.stderr)
        grid = analyze_box_cells(image_path, debug=args.debug)

    if args.output:
        out = Path(args.output)
        if out.suffix.lower() == ".csv":
            with out.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["position", "row", "column", "label"])
                for r in ROWS:
                    for c in COLS:
                        pos = f"{r}{c}"
                        writer.writerow([pos, r, c, grid.get(pos) or ""])
            print(f"CSV written to: {out}", file=sys.stderr)
        else:
            out.write_text(json.dumps(grid, indent=2, sort_keys=True))
            print(f"JSON written to: {out}", file=sys.stderr)
    else:
        print("\n=== JSON Output ===")
        print(json.dumps(grid, indent=2, sort_keys=True))

    print("\n=== Grid View ===")
    print_grid(grid)


if __name__ == "__main__":
    main()
