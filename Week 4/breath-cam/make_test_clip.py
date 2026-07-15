#!/usr/bin/env python3
"""
Generate a throwaway synthetic 'breathing' clip to shake out the loader and
pipeline before real footage exists. NOT part of the pipeline.

Writes a portrait-ish H.264 mp4 where a soft blob drifts vertically at a known
breathing rate, so estimate_rr has something real to find.
"""
import sys
import cv2
import numpy as np

OUT = sys.argv[1] if len(sys.argv) > 1 else "junk_clip.mp4"
W, H = 240, 320          # portrait
FPS = 30.0
DURATION_S = 20
RR_BPM = 15.0            # ground-truth breathing rate
N = int(FPS * DURATION_S)

freq = RR_BPM / 60.0     # Hz
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
vw = cv2.VideoWriter(OUT, fourcc, FPS, (W, H))

rng = np.random.default_rng(0)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
for i in range(N):
    t = i / FPS
    cy = H / 2 + 18.0 * np.sin(2 * np.pi * freq * t)   # vertical chest motion
    cx = W / 2
    blob = 200 * np.exp(-(((xx - cx) ** 2) / (2 * 40 ** 2) +
                          ((yy - cy) ** 2) / (2 * 55 ** 2)))
    frame = np.clip(blob + 25 + rng.normal(0, 4, (H, W)), 0, 255).astype(np.uint8)
    vw.write(cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR))
vw.release()
print(f"wrote {OUT}: {W}x{H}, {FPS} fps, {DURATION_S}s, ground-truth RR={RR_BPM} bpm")
