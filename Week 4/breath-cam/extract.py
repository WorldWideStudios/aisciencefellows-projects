#!/usr/bin/env python3
"""
Breathing-signal extraction pipeline for phone video.

Usage:
    python3 extract.py <video_path> [--method flow|intensity] [--fps N] [--roi x,y,w,h]

Designed so the real protocol clip can be swapped in later with no code changes:
just point the CLI at the new path. Tune the ROI default below if needed.
"""

# ---------------------------------------------------------------------------
# EDIT ME: default ROI as a fraction of the (upright) frame.
# Centered box covering the middle of the frame. Replace with an absolute pixel
# box via --roi x,y,w,h at runtime, or edit these fractions for a new default.
# (fx, fy) = top-left corner as fraction of (width, height); (fw, fh) = size.
# ---------------------------------------------------------------------------
DEFAULT_ROI_FRAC = (0.30, 0.30, 0.40, 0.40)  # centered 40% x 40% box

# Bandpass for human breathing: 0.1 Hz (6 bpm) .. 0.5 Hz (30 bpm).
BAND_LOW_HZ = 0.1
BAND_HIGH_HZ = 0.5

import argparse
import os
import sys

import cv2
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
import matplotlib

matplotlib.use("Agg")  # headless: write figure to disk, never open a window
import matplotlib.pyplot as plt

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


# ---------------------------------------------------------------------------
# 1. Loader
# ---------------------------------------------------------------------------
def _rotation_from_metadata(path):
    """
    Return the clockwise display rotation (0/90/180/270) phone players apply.

    Portrait phone clips are usually stored landscape with a rotation tag in
    the container. Whether OpenCV auto-applies that tag depends on the build
    (CAP_PROP_ORIENTATION_AUTO is ON by default on FFmpeg builds, OFF/absent on
    others), so load_frames disables auto-rotation and applies this value once
    itself -- the single, portable rotation step.
    """
    cap = cv2.VideoCapture(path)
    rot = 0.0
    try:
        # CAP_PROP_ORIENTATION_META exists on OpenCV builds with the FFmpeg
        # backend; guard it so older builds don't blow up.
        prop = getattr(cv2, "CAP_PROP_ORIENTATION_META", None)
        if prop is not None:
            rot = cap.get(prop)
    finally:
        cap.release()
    if rot is None or rot != rot:  # None or NaN
        return 0
    return int(round(rot)) % 360


def _apply_rotation(frame, rotation):
    """Rotate a decoded frame so it comes out upright."""
    if rotation == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rotation == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    if rotation == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame


def load_frames(path, fps_override=None):
    """
    Read a video with OpenCV and return (frames, fps, (w, h)).

    Handles phone-video gotchas:
      - HEVC (HardEVC/H.265) vs H.264: OpenCV's FFmpeg backend decodes both;
        we just open with the default backend and let FFmpeg pick the decoder.
      - Portrait rotation metadata: frames are rotated upright here.
      - Grayscale: every returned frame is single-channel uint8.

    Prints frame count, fps, and resolution for sanity-checking before anything
    downstream is trusted.
    """
    if not os.path.exists(path):
        sys.exit(f"ERROR: video not found: {path}")

    rotation = _rotation_from_metadata(path)

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        sys.exit(
            f"ERROR: OpenCV could not open {path}. "
            "If this is HEVC, your OpenCV build may lack an H.265 decoder; "
            "re-encode with: ffmpeg -i in.mov -c:v libx264 out.mp4"
        )

    # Disable OpenCV's built-in orientation handling so our _apply_rotation is
    # the ONLY rotation applied. Without this, builds that auto-rotate (this one
    # does) would rotate twice: a 180 tag nets to 0 and frames come out
    # upside-down; a 90 tag nets to 180. getattr-guarded for older builds.
    auto_prop = getattr(cv2, "CAP_PROP_ORIENTATION_AUTO", None)
    if auto_prop is not None:
        cap.set(auto_prop, 0)

    meta_fps = cap.get(cv2.CAP_PROP_FPS)

    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = _apply_rotation(frame, rotation)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frames.append(gray)
    cap.release()

    if not frames:
        sys.exit(f"ERROR: decoded 0 frames from {path}. File may be corrupt or unreadable.")

    # fps: CLI override wins; else metadata; else fall back to 30 with a warning.
    if fps_override is not None:
        fps = float(fps_override)
        fps_source = "CLI --fps override"
    elif meta_fps and meta_fps > 0 and meta_fps == meta_fps:  # >0 and not NaN
        fps = float(meta_fps)
        fps_source = "container metadata"
    else:
        fps = 30.0
        fps_source = "FALLBACK default (metadata missing/invalid)"

    h, w = frames[0].shape[:2]
    print("---- loader ----")
    print(f"  path:        {path}")
    print(f"  frames:      {len(frames)}")
    print(f"  fps:         {fps:.3f}  ({fps_source}; metadata said {meta_fps})")
    print(f"  resolution:  {w}x{h}  (upright; rotation metadata applied: {rotation} deg)")
    print("----------------")
    return frames, fps, (w, h)


# ---------------------------------------------------------------------------
# ROI handling
# ---------------------------------------------------------------------------
def resolve_roi(roi_arg, width, height):
    """Return an absolute (x, y, w, h) ROI, clamped to frame bounds."""
    if roi_arg is not None:
        x, y, w, h = roi_arg
    else:
        fx, fy, fw, fh = DEFAULT_ROI_FRAC
        x, y, w, h = (
            int(fx * width),
            int(fy * height),
            int(fw * width),
            int(fh * height),
        )
    # Clamp so we never index outside the frame.
    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    w = max(1, min(w, width - x))
    h = max(1, min(h, height - y))
    return (x, y, w, h)


def _crop(frame, roi):
    x, y, w, h = roi
    return frame[y : y + h, x : x + w]


# ---------------------------------------------------------------------------
# 2. Reducers (same signature, selected by --method)
# ---------------------------------------------------------------------------
def reduce_flow(prev_gray, gray, roi):
    """
    Primary estimator: mean magnitude of the VERTICAL optical-flow component
    inside the ROI (Farneback dense flow). One scalar per frame.

    Breathing is dominated by vertical chest/abdomen motion, so we use the
    vertical flow component (flow[..., 1]) rather than total magnitude.
    """
    prev_roi = _crop(prev_gray, roi)
    cur_roi = _crop(gray, roi)
    flow = cv2.calcOpticalFlowFarneback(
        prev_roi, cur_roi,
        None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
    )
    vertical = flow[..., 1]
    return float(np.mean(np.abs(vertical)))


def reduce_intensity(prev_gray, gray, roi):
    """
    Secondary/diagnostic estimator: mean pixel intensity inside the ROI.
    (prev_gray is unused; kept for a uniform reducer signature.)
    """
    return float(np.mean(_crop(gray, roi)))


REDUCERS = {"flow": reduce_flow, "intensity": reduce_intensity}


def build_signal(frames, roi, method):
    """Apply the chosen reducer across the frame sequence -> 1-D signal."""
    reducer = REDUCERS[method]
    values = []
    prev = frames[0]
    for i, gray in enumerate(frames):
        if method == "flow" and i == 0:
            # No previous frame for the first flow value; seed with 0 so the
            # signal length matches the frame count.
            values.append(0.0)
        else:
            values.append(reducer(prev, gray, roi))
        prev = gray
    return np.asarray(values, dtype=np.float64)


# ---------------------------------------------------------------------------
# 3. Bandpass
# ---------------------------------------------------------------------------
def bandpass(signal, fps):
    """Zero-phase Butterworth bandpass, BAND_LOW_HZ..BAND_HIGH_HZ."""
    nyq = 0.5 * fps
    low = BAND_LOW_HZ / nyq
    high = BAND_HIGH_HZ / nyq
    # Guard against degenerate normalized frequencies (very low fps / short clips).
    low = max(low, 1e-4)
    high = min(high, 0.999)
    if not (0 < low < high < 1):
        print(f"WARNING: band edges out of range for fps={fps}; skipping bandpass.")
        return signal - np.mean(signal)
    b, a = butter(2, [low, high], btype="band")
    # filtfilt needs the signal longer than the padding length.
    padlen = 3 * max(len(a), len(b))
    if len(signal) <= padlen:
        print(
            f"WARNING: signal too short ({len(signal)} samples) for zero-phase "
            f"filtering; returning mean-removed raw signal."
        )
        return signal - np.mean(signal)
    return filtfilt(b, a, signal)


# ---------------------------------------------------------------------------
# 4. Rate estimation
# ---------------------------------------------------------------------------
def estimate_rr(filtered, fps):
    """
    Peak-pick the bandpassed signal and report breaths per minute.

    Returns (rr_bpm, peak_indices).
    """
    # Minimum spacing between breaths = period of the fastest allowed rate.
    min_distance = max(1, int(fps / BAND_HIGH_HZ))
    peaks, _ = find_peaks(filtered, distance=min_distance)
    duration_s = len(filtered) / fps
    if len(peaks) < 2 or duration_s <= 0:
        return 0.0, peaks
    rr_bpm = len(peaks) / duration_s * 60.0
    return rr_bpm, peaks


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
def save_figure(raw, filtered, peaks, fps, method, roi, rr_bpm, out_path):
    t = np.arange(len(raw)) / fps
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    ax1.plot(t, raw, lw=0.9, color="tab:gray")
    ax1.set_title(f"Raw per-frame trace  (method={method}, ROI={roi})")
    ax1.set_ylabel("reducer output")

    ax2.plot(t, filtered, lw=1.1, color="tab:blue", label="bandpassed")
    if len(peaks):
        ax2.plot(t[peaks], filtered[peaks], "rx", ms=9, label="peaks")
    ax2.set_title(f"Bandpassed {BAND_LOW_HZ}-{BAND_HIGH_HZ} Hz   ->   RR = {rr_bpm:.1f} bpm")
    ax2.set_xlabel("time (s)")
    ax2.set_ylabel("amplitude")
    ax2.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_roi(s):
    try:
        parts = [int(p) for p in s.split(",")]
        if len(parts) != 4:
            raise ValueError
        return tuple(parts)
    except ValueError:
        raise argparse.ArgumentTypeError("--roi must be 'x,y,w,h' integers, e.g. 100,200,300,300")


def main():
    parser = argparse.ArgumentParser(description="Breathing-signal extraction from phone video.")
    parser.add_argument("video_path", help="path to the input clip")
    parser.add_argument("--method", choices=["flow", "intensity"], default="flow",
                        help="reducer: flow (primary) or intensity (diagnostic). default flow")
    parser.add_argument("--fps", type=float, default=None,
                        help="override fps if container metadata is wrong/missing")
    parser.add_argument("--roi", type=parse_roi, default=None,
                        help="ROI as x,y,w,h in pixels; default is a centered box")
    args = parser.parse_args()

    frames, fps, (w, h) = load_frames(args.video_path, fps_override=args.fps)
    roi = resolve_roi(args.roi, w, h)
    print(f"ROI used: {roi}  (x, y, w, h)")
    print(f"Method:   {args.method}")

    raw = build_signal(frames, roi, args.method)
    filtered = bandpass(raw, fps)
    rr_bpm, peaks = estimate_rr(filtered, fps)

    os.makedirs(OUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.video_path))[0]
    out_path = os.path.join(OUT_DIR, f"{base}_{args.method}.png")
    save_figure(raw, filtered, peaks, fps, args.method, roi, rr_bpm, out_path)

    print("---- result ----")
    print(f"  estimated RR: {rr_bpm:.1f} breaths/min")
    print(f"  peaks found:  {len(peaks)}")
    print(f"  ROI used:     {roi}")
    print(f"  figure:       {out_path}")
    print("----------------")


if __name__ == "__main__":
    main()
