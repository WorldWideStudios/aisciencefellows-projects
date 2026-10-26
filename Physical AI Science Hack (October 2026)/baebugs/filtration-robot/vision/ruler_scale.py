"""Measure pixels per mm from the millimetre ticks of a ruler in a photo.

Give a strip that crosses the mm ticks and avoids anything else that repeats (e.g. the dish's
serrated rim). The tick spacing is found by autocorrelation, then refined with a straight-line
fit through every tick, so a few scratches or glare spots don't throw it off.

Usage: python ruler_scale.py IMAGE --strip X0 X1 Y0 Y1 [--strip ...] --along vertical|horizontal
"""
import argparse

import cv2
import numpy as np

MAX_RMS_PX = 1.0  # a strip whose ticks stray further than this from a straight line is unreliable


def tick_profile(gray, x0, x1, y0, y1, along):
    """Darkness along the ruler, averaged across the strip, with slow lighting changes removed."""
    strip = gray[y0:y1, x0:x1].astype(float)
    profile = -(strip.mean(axis=1) if along == "vertical" else strip.mean(axis=0))
    return profile - np.convolve(profile, np.ones(25) / 25, mode="same")


def tick_spacing(profile, min_px=4, max_px=40):
    """Approximate tick spacing in px: the first strong autocorrelation peak.

    Taking the strongest peak can land on 2x the spacing (long/short ticks alternate), so take the
    shortest lag whose peak is at least half as strong as the strongest.
    """
    p = profile - profile.mean()
    ac = np.correlate(p, p, mode="full")[len(p) - 1:]
    lags = np.arange(min_px, min(max_px, len(ac) - 1))
    peaks = [lag for lag in lags if ac[lag] >= ac[lag - 1] and ac[lag] >= ac[lag + 1]]
    strongest = max(ac[lag] for lag in peaks)
    return int(next(lag for lag in peaks if ac[lag] >= 0.5 * strongest))


def tick_fit(profile, spacing):
    """(px per tick, rms residual px, tick count) from a line fit through the detected ticks."""
    half = max(2, int(spacing * 0.3))
    ticks = [i for i in range(half, len(profile) - half)
             if profile[i] == profile[i - half:i + half + 1].max() and profile[i] > 0]
    index = np.round((np.array(ticks) - ticks[0]) / spacing)
    slope, offset = np.polyfit(index, ticks, 1)
    residual = np.sqrt(np.mean((np.array(ticks) - (slope * index + offset)) ** 2))
    return slope, residual, len(ticks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--strip", type=int, nargs=4, action="append", required=True, metavar=("X0", "X1", "Y0", "Y1"))
    ap.add_argument("--along", choices=["vertical", "horizontal"], required=True, help="direction the ruler runs")
    args = ap.parse_args()

    gray = cv2.cvtColor(cv2.imread(args.image), cv2.COLOR_BGR2GRAY)
    good = []
    for x0, x1, y0, y1 in args.strip:
        profile = tick_profile(gray, x0, x1, y0, y1, args.along)
        spacing = tick_spacing(profile)
        px_per_mm, residual, count = tick_fit(profile, spacing)
        clean = residual <= MAX_RMS_PX
        if clean:
            good.append(px_per_mm)
        print(f"strip x{x0}-{x1} y{y0}-{y1}: {count} ticks, {px_per_mm:.3f} px/mm "
              f"(fit rms {residual:.2f} px{'' if clean else ', ignored: ticks do not line up'})")
    if not good:
        raise SystemExit("no strip gave clean ticks; try a strip away from glare, scratches and the dish rim")
    print(f"px per mm: {np.mean(good):.2f}")


if __name__ == "__main__":
    main()
