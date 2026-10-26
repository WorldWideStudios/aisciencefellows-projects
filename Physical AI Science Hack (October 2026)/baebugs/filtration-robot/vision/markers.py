"""ArUco markers that tell the wrist camera which filter it is looking at.

Each filter carries a printed 4x4 ArUco marker (OpenCV's DICT_4X4_50). filters.json maps each filter's
letter to its marker id ("markers") and the letter to the filter id ("codes"). A marker needs its white
margin (one cell wide, included on the sheet) to be found, so cut along the dotted line, not closer.

Usage:
  python markers.py sheet [--out filter_markers.pdf] [--sizes 15 20 25]   # print at 100% / actual size
  python markers.py read IMAGE [--out annotated.png]                      # which filters are in a photo
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
FILTERS = HERE / "filters.json"
DICTIONARY = cv2.aruco.DICT_4X4_50
CELLS = 6  # 4x4 bits plus a one-cell black border
DPI = 600
PAGE_MM = (215.9, 279.4)  # US Letter
MARGIN_MM = 12
GAP_MM = 6


def px(mm):
    return round(mm / 25.4 * DPI)


def dotted_square(draw, x, y, side):
    """Cut line: a dotted square, so it doesn't look like part of the marker."""
    dash, width = px(1), max(1, px(0.15))
    for i in range(0, side, 2 * dash):
        end = min(i + dash, side)
        draw.line([x + i, y, x + end, y], fill=0, width=width)
        draw.line([x + i, y + side, x + end, y + side], fill=0, width=width)
        draw.line([x, y + i, x, y + end], fill=0, width=width)
        draw.line([x + side, y + i, x + side, y + end], fill=0, width=width)


def sheet(out, sizes):
    """Write a printable page with every filter's marker at each size (mm, black square's side)."""
    data = json.loads(FILTERS.read_text())
    dictionary = cv2.aruco.getPredefinedDictionary(DICTIONARY)
    page = Image.new("1", (px(PAGE_MM[0]), px(PAGE_MM[1])), 1)
    draw = ImageDraw.Draw(page)
    font, small = ImageFont.load_default(px(4)), ImageFont.load_default(px(3))
    left, right = px(MARGIN_MM), px(PAGE_MM[0] - MARGIN_MM)
    y = px(MARGIN_MM)
    draw.text((left, y), "Filter markers (ArUco 4x4_50). Print at 100% / actual size, no 'fit to page'.", font=font, fill=0)
    y += px(7)
    draw.text((left, y), "This bar must measure 50 mm:", font=small, fill=0)
    draw.rectangle([left + px(55), y, left + px(105), y + px(2.5)], fill=0)
    y += px(9)
    for size in sizes:
        side = px(size * (CELLS + 2) / CELLS)  # marker plus a one-cell white margin all round
        x = left
        draw.text((left, y), f"{size} mm markers", font=font, fill=0)
        y += px(7)
        for letter, marker_id in data["markers"].items():
            if x + side > right:
                x, y = left, y + side + px(5 + GAP_MM)
            filter_id = data["codes"].get(letter)
            draw.text((x, y), f"{letter} ({filter_id})" if filter_id else letter, font=small, fill=0)
            top = y + px(4.5)
            marker = cv2.aruco.generateImageMarker(dictionary, marker_id, px(size))
            page.paste(Image.fromarray(marker).convert("1"), (x + (side - px(size)) // 2, top + (side - px(size)) // 2))
            dotted_square(draw, x, top, side)
            x += side + px(GAP_MM)
        y += side + px(4.5 + GAP_MM + 4)
    if y > px(PAGE_MM[1] - MARGIN_MM):
        raise SystemExit("too many sizes for one page; pass fewer --sizes")
    page.save(out, resolution=DPI)
    print(f"wrote {out}")


def detect(img):
    """[(marker id, 4x2 corners in px)] for every filter marker found in a BGR image."""
    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICTIONARY), cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    return [] if ids is None else [(int(i), c.reshape(4, 2)) for i, c in zip(ids.ravel(), corners)]


def read(image, out=None):
    data = json.loads(FILTERS.read_text())
    letters = {marker_id: letter for letter, marker_id in data["markers"].items()}
    img = cv2.imread(str(image))
    found = detect(img)
    for marker_id, corners in found:
        letter = letters.get(marker_id, "?")
        side = np.linalg.norm(corners - np.roll(corners, 1, 0), axis=1).mean()
        cx, cy = corners.mean(0)
        print(f"marker {marker_id}: letter {letter}, filter {data['codes'].get(letter, '-')}, "
              f"centre ({cx:.0f}, {cy:.0f}) px, side {side:.0f} px")
    if not found:
        print("no markers found")
    if out:
        if found:
            cv2.aruco.drawDetectedMarkers(img, [c.reshape(1, 4, 2) for _, c in found], np.array([[m] for m, _ in found]))
        cv2.imwrite(str(out), img)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("--out", default=str(HERE / "filter_markers.pdf"))
    s.add_argument("--sizes", type=float, nargs="+", default=[15, 20, 25], help="black square's side, mm")
    r = sub.add_parser("read")
    r.add_argument("image")
    r.add_argument("--out", help="save the photo with found markers outlined")
    args = p.parse_args()
    if args.cmd == "sheet":
        sheet(args.out, args.sizes)
    else:
        read(args.image, args.out)


if __name__ == "__main__":
    main()
