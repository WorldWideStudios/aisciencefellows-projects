#!/usr/bin/env python3
"""
Evaluate candidate ROIs by SPECTRAL quality on the calm window, not whole-clip RR.

For each ROI: build the flow signal over the calm window, bandpass it for the
trace, and compute an FFT power spectrum (Welch-style periodogram) of the
detrended raw signal. A real breathing ROI shows a sharp peak in 0.15-0.25 Hz;
a couch ROI shows broadband noise. The in-band peak-to-median ratio (a crude
SNR) lets the cleaner spectrum pick the box.
"""
import numpy as np
from scipy.signal import detrend, periodogram
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import extract

PATH = "../JLG_Sleep_1.mov"
CALM = (52.0, 85.0)                      # seconds
BAND = (extract.BAND_LOW_HZ, extract.BAND_HIGH_HZ)   # 0.1 .. 0.5 Hz
ROIS = [
    ("default",  (384, 216, 512, 288)),
    ("chest B",  (470, 455, 260, 150)),
]


def band_spectrum(sig, fps):
    """Periodogram of the detrended signal; return (f, Pxx) and in-band stats."""
    sig = detrend(sig)                                  # kill DC + linear drift
    f, pxx = periodogram(sig, fs=fps, window="hann")
    in_band = (f >= BAND[0]) & (f <= BAND[1])
    fb, pb = f[in_band], pxx[in_band]
    k = int(np.argmax(pb))
    peak_f, peak_p = fb[k], pb[k]
    snr = peak_p / np.median(pb)                         # peak vs typical in-band power
    return f, pxx, fb, pb, peak_f, peak_p, snr


def main():
    frames, fps, (w, h) = extract.load_frames(PATH)
    i0, i1 = int(CALM[0] * fps), int(CALM[1] * fps)
    window = frames[i0:i1]
    print(f"calm window {CALM[0]:.0f}-{CALM[1]:.0f}s -> frames {i0}..{i1} ({len(window)} frames)")

    fig, axes = plt.subplots(len(ROIS), 2, figsize=(13, 7))
    results = []
    for row, (name, roi) in enumerate(ROIS):
        roi = extract.resolve_roi(roi, w, h)
        raw = extract.build_signal(window, roi, "flow")
        filt = extract.bandpass(raw, fps)
        f, pxx, fb, pb, peak_f, peak_p, snr = band_spectrum(raw, fps)
        results.append((name, roi, peak_f, snr))
        print(f"  {name:8s} ROI={roi}  peak={peak_f:.3f} Hz "
              f"({peak_f*60:.1f} bpm)  in-band SNR={snr:.1f}")

        t = np.arange(len(filt)) / fps + CALM[0]
        ax = axes[row, 0]
        ax.plot(t, filt, lw=1.0, color="tab:blue")
        ax.set_title(f"{name} {roi}  -  bandpassed {BAND[0]}-{BAND[1]} Hz")
        ax.set_ylabel("amplitude")
        if row == len(ROIS) - 1:
            ax.set_xlabel("time (s)")

        ax = axes[row, 1]
        ax.semilogy(f, pxx, lw=0.8, color="0.6")
        ax.axvspan(BAND[0], BAND[1], color="tab:orange", alpha=0.12)
        ax.axvspan(0.15, 0.25, color="tab:green", alpha=0.18)   # expected breathing
        ax.plot(peak_f, peak_p, "rx", ms=10)
        ax.set_xlim(0, 1.0)
        ax.set_title(f"FFT  -  peak {peak_f:.3f} Hz ({peak_f*60:.1f} bpm), SNR={snr:.1f}")
        ax.set_ylabel("power")
        if row == len(ROIS) - 1:
            ax.set_xlabel("frequency (Hz)")

    fig.tight_layout()
    out = "out/roi_eval_calm.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)

    winner = max(results, key=lambda r: r[3])
    print(f"\nWINNER (cleanest in-band spectrum): {winner[0]} {winner[1]}  "
          f"peak {winner[2]:.3f} Hz, SNR {winner[3]:.1f}")
    print(f"figure -> {out}")


if __name__ == "__main__":
    main()
