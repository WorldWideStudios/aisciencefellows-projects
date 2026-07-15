#!/usr/bin/env python3
"""
ROI preview helper -- SINGLE rotation path.

Imports extract.load_frames and operates on the EXACT frames the trace reduces
(same load -> rotate -> grayscale path). It never re-reads or re-rotates the
video itself, so the saved crop and boxed full-frame are guaranteed to match
the orientation of the array the flow reducer sees, pixel-for-pixel.

Usage:
    python3 roi_preview.py <video_path> [x,y,w,h]   # ROI defaults to extract's default
"""
import os
import sys
import cv2

import extract


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python3 roi_preview.py <video_path> [x,y,w,h]")
    path = sys.argv[1]

    # Exact same load+rotate+grayscale path the trace uses.
    frames, fps, (w, h) = extract.load_frames(path)

    roi_arg = extract.parse_roi(sys.argv[2]) if len(sys.argv) > 2 else None
    roi = extract.resolve_roi(roi_arg, w, h)
    x, y, rw, rh = roi

    idx = len(frames) // 2          # mid-clip representative frame
    gray = frames[idx]              # the upright, grayscale array that gets reduced

    base = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(extract.OUT_DIR, exist_ok=True)

    # 1. Literal crop the reducer slices: frame[y:y+h, x:x+w]. No drawing.
    crop = gray[y:y + rh, x:x + rw]
    crop_path = os.path.join(extract.OUT_DIR, f"{base}_roi_crop.png")
    cv2.imwrite(crop_path, crop)

    # 2. Full upright frame with the ROI box drawn. Derived from the SAME gray
    #    array (gray->BGR only so the box can be red), so orientation is identical.
    vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(vis, (x, y), (x + rw, y + rh), (0, 0, 255), 3)
    cv2.putText(vis, f"ROI {roi}", (x, max(20, y - 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    box_path = os.path.join(extract.OUT_DIR, f"{base}_roi_boxed.png")
    cv2.imwrite(box_path, vis)

    print(f"frame {idx}/{len(frames)}  ROI={roi}  crop={crop.shape}")
    print(f"  crop  -> {crop_path}")
    print(f"  boxed -> {box_path}")


if __name__ == "__main__":
    main()
