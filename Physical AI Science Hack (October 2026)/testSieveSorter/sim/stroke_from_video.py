"""Measure the tray stroke from a video: track one tray feature, scale px to mm, write a stroke CSV.

ffmpeg pipes grayscale frames of a crop; a template patch of the feature (a pull tab, an edge, a dot)
is found in each frame by normalized cross-correlation with a sub-pixel peak. The principal axis of
the track is the stroke axis; motion across it is reported as bounce. Times are frame index / fps
(divided by --slowdown for a slow-motion clip that plays back at normal speed).

Steps, from sim\\ (numpy, matplotlib and ffmpeg; runs on Windows, no MuJoCo):
    python stroke_from_video.py VIDEO --probe
        ffprobe info, plus out/stroke/<clip>/probe.png: the first frame with a 50 px grid to read
        coordinates off
    python stroke_from_video.py VIDEO --roi x,y,w,h --feature x,y,w,h --ref x1,y1,x2,y2 \\
        [--ref-mm 131.4] [--start s] [--duration s] [--slowdown k] --out bench/stroke_forum.csv
        roi: search area (full-frame px). feature: template box, inside roi, on a part that moves
        with the tray. ref: two points a known distance apart; 131.4 mm is an insert's length
        (cad/WORKING_DIMENSIONS.md). Writes the CSV and out/stroke/<clip>/ (track.csv, stroke.png,
        overlay_*.png, metrics.json)
    python stroke_from_video.py --selftest
        renders a synthetic clip with a known stroke and checks it is recovered

The CSV holds whole cycles only, starting and ending at a rising crossing of the mid-stroke position,
because sorter.py loops it. Header first, then # comments (np.loadtxt's skiprows counts comments).

ramp_s is reported as a bracket. A reversal is timed from the last sample at >= 90% of the stroke
speed to the first sample at >= 90% the other way; with a box-smoothed velocity (sorter.py's model)
that is 0.9 ramp_s. Velocities come from central differences, which widen the transition by up to
two frame intervals, so ramp_s lies between (measured - 2 dt) / 0.9 and measured / 0.9. At 30 fps
anything under about 70 ms is an upper bound only.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
INSERT_MM = 131.4
FIRMWARE = {"amp_mm": 10.0, "speed_mm_s": 5.0}     # BugSorter src/main.cpp default: 2 cm stroke at 5 mm/s
HI = 0.9                                            # reversal timing threshold, fraction of stroke speed


# ---------------------------------------------------------------- video io

def probe(video):
    """fps, size, duration and codec of the first video stream, plus the container's creation info."""
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,codec_name,duration:"
                        "stream_tags=rotate:stream_side_data=rotation:format=duration:format_tags=creation_time,com.apple.quicktime.model,"
                        "com.android.manufacturer,com.android.model,make,model",
                        "-of", "json", str(video)], capture_output=True, text=True, check=True)
    info = json.loads(p.stdout)
    s, fmt = info["streams"][0], info.get("format", {})

    def rate(r):
        n, _, d = r.partition("/")
        return float(n) / float(d or 1) if float(d or 1) else 0.0

    tags = fmt.get("tags", {})
    rot = s.get("tags", {}).get("rotate") or next((d["rotation"] for d in s.get("side_data_list", [])
                                                   if "rotation" in d), 0)
    w, h = (s["height"], s["width"]) if abs(int(float(rot))) % 180 == 90 else (s["width"], s["height"])
    return {"file": Path(video).name, "width": w, "height": h, "codec": s.get("codec_name"),
            "fps": rate(s["avg_frame_rate"]) or rate(s["r_frame_rate"]), "r_frame_rate": s["r_frame_rate"],
            "avg_frame_rate": s["avg_frame_rate"], "frames": int(s.get("nb_frames") or 0),
            "duration_s": float(s.get("duration") or fmt.get("duration") or 0),
            "rotation_deg": int(float(rot)),                 # width and height above are as displayed
            "camera": " ".join(v for k, v in tags.items() if k != "creation_time") or None,
            "created": tags.get("creation_time")}


def frames(video, crop, start=0.0, duration=None):
    """Yield grayscale uint8 frames (h, w) of crop = (x, y, w, h), in full-frame px after rotation."""
    x, y, w, h = crop
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start}", "-i", str(video)]
    if duration:
        cmd += ["-t", f"{duration}"]
    cmd += ["-vf", f"crop={w}:{h}:{x}:{y},format=gray", "-fps_mode", "passthrough",
            "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = w * h
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w)
    p.wait()


def frame_rgb(video, t):
    """One full RGB frame at time t, as displayed (ffmpeg applies the phone's rotation)."""
    s = probe(video)
    w, h = s["width"], s["height"]
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", str(video), "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(h, w, 3).copy()


# ---------------------------------------------------------------- tracking

def ncc(img, tmpl):
    """Normalized cross-correlation of tmpl over every valid position of img, via FFT and integral images."""
    img = img.astype(np.float64)
    th, tw = tmpl.shape
    H, W = img.shape
    t = tmpl - tmpl.mean()
    tn = np.sqrt((t ** 2).sum()) or 1.0
    fh, fw = H + th - 1, W + tw - 1
    corr = np.fft.irfft2(np.fft.rfft2(img, (fh, fw)) * np.conj(np.fft.rfft2(t, (fh, fw))), (fh, fw))[:H - th + 1, :W - tw + 1]
    ii = np.pad(img, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    ii2 = np.pad(img ** 2, ((1, 0), (1, 0))).cumsum(0).cumsum(1)

    def box(a):
        return a[th:, tw:] - a[:-th, tw:] - a[th:, :-tw] + a[:-th, :-tw]

    var = box(ii2) - box(ii) ** 2 / (th * tw)
    return corr / (np.sqrt(np.maximum(var, 1e-9)) * tn)


def subpixel(c, i, j):
    """Parabolic peak refinement around (i, j)."""
    def off(a, b, d):
        den = a - 2 * b + d
        return 0.5 * (a - d) / den if den else 0.0
    di = off(c[i - 1, j], c[i, j], c[i + 1, j]) if 0 < i < c.shape[0] - 1 else 0.0
    dj = off(c[i, j - 1], c[i, j], c[i, j + 1]) if 0 < j < c.shape[1] - 1 else 0.0
    return i + di, j + dj


def track(video, roi, feature, start=0.0, duration=None, max_step=None):
    """(n, 2) feature centre in full-frame px per frame, and the NCC peak score per frame."""
    rx, ry, rw, rh = roi
    fx, fy, fw, fh = feature
    if not (rx <= fx and ry <= fy and fx + fw <= rx + rw and fy + fh <= ry + rh):
        raise ValueError("--feature must lie inside --roi")
    max_step = max_step or max(fw, fh) / 2
    tmpl, prev, out, score = None, None, [], []
    for f in frames(video, roi, start, duration):
        if tmpl is None:
            tmpl = f[fy - ry:fy - ry + fh, fx - rx:fx - rx + fw].astype(np.float64)
            prev = (fy - ry, fx - rx)
        c = ncc(f, tmpl)
        ii, jj = np.mgrid[:c.shape[0], :c.shape[1]]
        far = (ii - prev[0]) ** 2 + (jj - prev[1]) ** 2 > max_step ** 2  # stay near the last hit: a mesh repeats
        c = np.where(far, -1.0, c)
        i, j = np.unravel_index(np.argmax(c), c.shape)
        score.append(float(c[i, j]))
        prev = subpixel(c, i, j)
        out.append((rx + prev[1] + fw / 2, ry + prev[0] + fh / 2))
    if not out:
        raise RuntimeError(f"no frames read from {video}")
    return np.array(out), np.array(score)


# ---------------------------------------------------------------- analysis

def principal_axis(xy):
    """Unit vector of the largest motion (sign: toward +x, or +y if vertical) and the perpendicular."""
    c = xy - xy.mean(0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    a = vt[0]
    if abs(a[0]) >= abs(a[1]) and a[0] < 0 or abs(a[0]) < abs(a[1]) and a[1] < 0:
        a = -a
    return a, np.array([-a[1], a[0]])


def smooth(x, n):
    if n <= 1:
        return x
    k = np.ones(n) / n
    return np.convolve(np.pad(x, (n // 2, n - 1 - n // 2), mode="edge"), k, mode="valid")


def dominant_period(t, s):
    """Period from the FFT peak of the detrended signal, refined parabolically."""
    dt = np.median(np.diff(t))
    x = s - np.polyval(np.polyfit(t, s, 1), t)
    n = 1 << int(np.ceil(np.log2(len(x) * 8)))
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)), n))
    f = np.fft.rfftfreq(n, dt)
    k = int(np.argmax(spec[1:]) + 1)
    if 1 <= k < len(spec) - 1:
        a, b, c = spec[k - 1:k + 2]
        k = k + 0.5 * (a - c) / (a - 2 * b + c)
    return 1.0 / (k * f[1])


def rising_crossings(t, s):
    """Times where s crosses 0 going up, linearly interpolated."""
    i = np.flatnonzero((s[:-1] < 0) & (s[1:] >= 0))
    return t[i] - s[i] * (t[i + 1] - t[i]) / (s[i + 1] - s[i])


def analyze(t, s, perp):
    """Stroke metrics from displacement s along the axis and perp across it (mm, s)."""
    dt = float(np.median(np.diff(t)))
    sm = smooth(s, 3)
    mid = (np.percentile(sm, 99) + np.percentile(sm, 1)) / 2
    s0 = s - mid
    period = dominant_period(t, s0)
    cyc = max(1, int(round(period / dt)))
    peaks = [np.ptp(s0[i:i + cyc]) for i in range(0, len(s0) - cyc + 1, cyc)] or [np.ptp(s0)]
    v = np.gradient(s, t)
    av = np.abs(v)
    speed = float(np.median(av[av > 0.6 * np.percentile(av, 95)]))
    hi = HI * speed
    ramps = []
    rev = np.flatnonzero(np.sign(smooth(v, 3)[:-1]) != np.sign(smooth(v, 3)[1:]))
    for r in rev:
        before = np.flatnonzero(av[:r + 1] >= hi)
        after = np.flatnonzero(av[r + 1:] >= hi)
        if len(before) and len(after) and np.sign(v[before[-1]]) != np.sign(v[r + 1 + after[0]]):
            ramps.append(t[r + 1 + after[0]] - t[before[-1]])
    ramps = sorted(set(round(x, 6) for x in ramps))
    meas = float(np.median(ramps)) if ramps else None
    pc = perp - np.median(perp)
    out = {"fps": round(1 / dt, 3), "frames": len(t), "duration_s": round(float(t[-1] - t[0]), 4),
           "amplitude_mm": round(float(np.median(peaks)) / 2, 3), "stroke_mm": round(float(np.median(peaks)), 3),
           "speed_mm_s": round(speed, 3), "period_s": round(float(period), 4),
           "cycles": round(float((t[-1] - t[0]) / period), 2), "reversals_timed": len(ramps),
           "reversal_90_90_s": round(meas, 4) if meas is not None else None,
           "ramp_s_upper": round(meas / HI, 4) if meas is not None else None,
           "ramp_s_lower": round(max(0.0, meas - 2 * dt) / HI, 4) if meas is not None else None,
           "ramp_resolved": bool(meas is not None and meas > 4 * dt),
           "bounce_p2p_mm": round(float(np.percentile(pc, 99) - np.percentile(pc, 1)), 3),
           "bounce_rms_mm": round(float(np.sqrt(np.mean(pc ** 2))), 3), "mid_mm": float(mid)}
    if meas is not None and not out["ramp_resolved"]:
        out["ramp_note"] = (f"reversal takes {meas / dt:.1f} frame intervals: not resolved at {1 / dt:.0f} fps, "
                            f"ramp_s <= {meas / HI:.3f} s only")
    return out


def whole_cycles(t, s0):
    """Rows (t, x) from the first to the last rising crossing of s0, t starting at 0, x = 0 at both ends."""
    tc = rising_crossings(t, s0)
    if len(tc) < 2:
        raise RuntimeError("fewer than one full cycle in the clip: use a longer --duration")
    keep = (t > tc[0]) & (t < tc[-1])
    tt = np.concatenate([[tc[0]], t[keep], [tc[-1]]]) - tc[0]
    xx = np.concatenate([[0.0], s0[keep], [0.0]])
    return tt, xx, len(tc) - 1


def model_stroke(t, amp, speed, ramp_s):
    """sorter.py's constant_speed profile (copied, sorter imports mujoco): square velocity, box-smoothed."""
    dt = np.median(np.diff(t))
    f = speed / (4 * amp)
    v = np.where((t * f) % 1.0 < 0.5, 1.0, -1.0)
    v = smooth(v, max(1, round(ramp_s / dt)))
    x = np.cumsum(v) * dt
    x -= (x.max() + x.min()) / 2
    return x * amp / max(x.max(), 1e-9)


# ---------------------------------------------------------------- outputs

def write_csv(path, tt, xx, meta, m):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["t_s,x_mm",
             f"# measured by stroke_from_video.py from {meta['file']} ({meta['width']}x{meta['height']}, "
             f"{meta['fps']:.3f} fps, slowdown {meta['slowdown']:g})",
             f"# {m['whole_cycles']} whole cycles, rising mid-stroke crossing to rising crossing; looped by sorter.py",
             f"# stroke {m['stroke_mm']} mm (amp_mm {m['amplitude_mm']}), speed {m['speed_mm_s']} mm/s, "
             f"period {m['period_s']} s",
             f"# ramp_s between {m['ramp_s_lower']} and {m['ramp_s_upper']} s"
             + ("" if m["ramp_resolved"] else " (not resolved at this frame rate; upper bound)"),
             f"# axis {m['axis']}, {m['axis_deg_from_image_x']} deg from image x; bounce p2p {m['bounce_p2p_mm']} mm",
             f"# scale {m['mm_per_px']:.5f} mm/px from {meta['scale_from']}"]
    lines += [f"{a:.5f},{b:.4f}" for a, b in zip(tt, xx)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plots(out, video, t, s0, perp, xy, m, meta, roi, feature, start):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    ax[0].plot(t, s0, ".-", ms=3, lw=0.8, label="measured")
    tm = np.arange(0, t[-1], 1e-3)
    ax[0].plot(tm, model_stroke(tm, m["amplitude_mm"], m["speed_mm_s"], m["ramp_s_upper"] or 0.01), lw=0.8,
               alpha=0.8, label=f"model: constant_speed at measured amp/speed, ramp_s {m['ramp_s_upper']}")
    ax[0].plot(tm, model_stroke(tm, FIRMWARE["amp_mm"], FIRMWARE["speed_mm_s"], 0.01), "--", lw=0.8,
               label="firmware default: 2 cm stroke at 5 mm/s")
    ax[0].set_ylabel("along stroke, mm")
    ax[0].legend(fontsize=8, loc="upper right")
    ax[1].plot(t, np.gradient(s0, t), ".-", ms=3, lw=0.8)
    ax[1].axhline(m["speed_mm_s"], color="gray", lw=0.5)
    ax[1].axhline(-m["speed_mm_s"], color="gray", lw=0.5)
    ax[1].set_ylabel("velocity, mm/s")
    ax[2].plot(t, perp - np.median(perp), ".-", ms=3, lw=0.8)
    ax[2].set_ylabel("across stroke (bounce), mm")
    ax[2].set_xlabel(f"time, s ({meta['fps']:.1f} fps, slowdown {meta['slowdown']:g})")
    fig.suptitle(f"{meta['file']}: stroke {m['stroke_mm']} mm, {m['speed_mm_s']} mm/s, period {m['period_s']} s, "
                 f"{m['axis']}", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "stroke.png", dpi=120)
    plt.close(fig)
    # overlays: the tracked point at the two stroke ends and mid-stroke
    picks = [int(np.argmin(s0)), int(np.argmin(np.abs(s0))), int(np.argmax(s0))]
    rx, ry, rw, rh = roi
    for name, i in zip(("min", "mid", "max"), picks):
        img = frame_rgb(video, start + i / meta["fps_video"])
        fig, a = plt.subplots(figsize=(8, 8 * img.shape[0] / img.shape[1]))
        a.imshow(img)
        a.add_patch(plt.Rectangle((rx, ry), rw, rh, fill=False, ec="yellow", lw=1))
        a.plot(*xy[i], "+", color="red", ms=25, mew=1.5)
        a.plot(*xy[0], "x", color="cyan", ms=10, mew=1)
        a.set_title(f"frame {i}, t={t[i]:.3f} s, x={s0[i]:+.2f} mm (red: tracked, cyan: frame 0)", fontsize=9)
        a.axis("off")
        fig.tight_layout()
        fig.savefig(out / f"overlay_{name}.png", dpi=110)
        plt.close(fig)


def measure(video, roi, feature, ref=None, ref_mm=INSERT_MM, mm_per_px=None, start=0.0, duration=None,
            slowdown=1.0, csv=None, plot_dir=None, max_step=None):
    meta = probe(video)
    meta["fps_video"], meta["slowdown"] = meta["fps"], slowdown
    if mm_per_px is None:
        if ref is None:
            raise ValueError("give --ref x1,y1,x2,y2 (with --ref-mm) or --mm-per-px")
        mm_per_px = ref_mm / float(np.hypot(ref[2] - ref[0], ref[3] - ref[1]))
        meta["scale_from"] = f"{ref_mm} mm between px {ref[:2]} and {ref[2:]}"
    else:
        meta["scale_from"] = "--mm-per-px"
    xy, score = track(video, roi, feature, start, duration, max_step)
    t = np.arange(len(xy)) / meta["fps"] / slowdown
    meta["fps"] = meta["fps"] * slowdown                     # real-time sample rate
    a, n = principal_axis(xy)
    s = (xy - xy[0]) @ a * mm_per_px
    perp = (xy - xy[0]) @ n * mm_per_px
    m = analyze(t, s, perp)
    s0 = s - m.pop("mid_mm")
    tt, xx, k = whole_cycles(t, s0)
    deg = float(np.degrees(np.arctan2(a[1], a[0])))
    m.update(whole_cycles=k, mm_per_px=mm_per_px, axis_deg_from_image_x=round(deg, 1),
             axis="horizontal in the image" if abs(np.cos(np.radians(deg))) >= np.cos(np.radians(30))
             else "vertical in the image" if abs(np.sin(np.radians(deg))) >= np.cos(np.radians(30)) else "diagonal",
             ncc_min=round(float(score.min()), 3), ncc_median=round(float(np.median(score)), 3))
    if m["ncc_min"] < 0.6:
        m["tracking_note"] = "NCC fell below 0.6 on some frames: check the overlays for lost tracking"
    if csv:
        write_csv(Path(csv), tt, xx, meta, m)
    if plot_dir:
        out = Path(plot_dir)
        out.mkdir(parents=True, exist_ok=True)
        np.savetxt(out / "track.csv", np.column_stack([t, xy, s0, perp, score]), delimiter=",", fmt="%.5f",
                   header="t_s,x_px,y_px,along_mm,across_mm,ncc", comments="")
        (out / "metrics.json").write_text(json.dumps({"video": meta, "metrics": m, "roi": roi, "feature": feature,
                                                      "start_s": start, "duration_s": duration}, indent=1))
        plots(out, video, t, s0, perp, xy, m, meta, roi, feature, start)
    return m, meta


def probe_image(video, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    img = frame_rgb(video, 0.0)
    h, w = img.shape[:2]
    fig, a = plt.subplots(figsize=(12, 12 * h / w))
    a.imshow(img)
    a.set_xticks(range(0, w, 100))
    a.set_yticks(range(0, h, 100))
    a.set_xticks(range(0, w, 50), minor=True)
    a.set_yticks(range(0, h, 50), minor=True)
    a.grid(which="both", color="yellow", lw=0.3, alpha=0.6)
    a.tick_params(labelsize=6)
    fig.tight_layout()
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "probe.png", dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- self test

def selftest():
    """Render a textured tray moving with a known trapezoid stroke and check the measurement."""
    fps, amp_px, speed_px, ramp_s, dur = 120, 60.0, 240.0, 0.05, 4.0
    mm_per_px = 0.25                                         # so amp 15 mm, speed 60 mm/s
    period = 4 * amp_px / speed_px
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        n = int(dur * fps)
        t = np.arange(n) / fps
        tf = np.arange(-period, dur + period, 1e-4)           # a cycle of lead-in and -out: the end half-strokes
        x = np.interp(t, tf, model_stroke(tf, amp_px, speed_px, ramp_s))   # have no reversal and run long
        v = np.gradient(x, t)
        want = {"amplitude_mm": np.ptp(x) / 2 * mm_per_px, "period_s": period,   # truth from the rendered signal
                "speed_mm_s": float(np.median(np.abs(v)[np.abs(v) > 0.9 * speed_px])) * mm_per_px}
        bounce = 0.8 * np.sin(2 * np.pi * t / period * 2)     # small vertical bounce, 0.8 px
        rng = np.random.default_rng(0)
        tray = (rng.random((120, 200)) * 80 + 60).astype(np.uint8)
        tray[40:80, 80:120] = 245                              # bright pull tab
        clip = td / "synthetic.mkv"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "480x320",
                              "-r", str(fps), "-i", "-", "-c:v", "ffv1", str(clip)], stdin=subprocess.PIPE)
        for xi, bi in zip(x, bounce):
            f = np.full((320, 480), 30, np.uint8)
            # sub-pixel motion by blending two integer shifts
            x0, fx = int(np.floor(xi)), xi - np.floor(xi)
            y0, fy = int(np.floor(bi)), bi - np.floor(bi)
            acc = np.zeros((320, 480))
            for dx, wx in ((0, 1 - fx), (1, fx)):
                for dy, wy in ((0, 1 - fy), (1, fy)):
                    c = np.full((320, 480), 30.0)
                    c[100 + y0 + dy:220 + y0 + dy, 140 + x0 + dx:340 + x0 + dx] = tray
                    acc += wx * wy * c
            f[:] = np.clip(acc + rng.normal(0, 2, acc.shape), 0, 255).astype(np.uint8)
            p.stdin.write(f.tobytes())
        p.stdin.close()
        p.wait()
        m, _ = measure(clip, roi=(40, 60, 400, 220), feature=(210, 130, 60, 60), mm_per_px=mm_per_px,
                       csv=td / "s.csv", plot_dir=td / "plots")
        rows = np.loadtxt(td / "s.csv", delimiter=",", skiprows=1)
    ok = True
    for k, v in want.items():
        err = abs(m[k] - v) / v
        ok &= err < 0.01
        print(f"{k:14s} want {v:8.3f}  got {m[k]:8.3f}  ({err:.1%})")
    inside = m["ramp_s_lower"] - 1e-9 <= ramp_s <= m["ramp_s_upper"] + 1e-9
    ok &= inside
    print(f"ramp_s         want {ramp_s:8.3f}  bracket [{m['ramp_s_lower']}, {m['ramp_s_upper']}]  "
          f"{'contains it' if inside else 'MISSES IT'}")
    want_bounce = 1.6 * mm_per_px                             # 0.8 px amplitude
    ok &= m["axis"] == "horizontal in the image" and abs(m["bounce_p2p_mm"] - want_bounce) < 0.5 * want_bounce
    print(f"axis {m['axis']}, bounce p2p {m['bounce_p2p_mm']} mm (rendered {want_bounce:.2f} mm)")
    ok &= abs(rows[0, 1]) < 1e-9 and abs(rows[-1, 1]) < 1e-9 and m["whole_cycles"] >= 3
    print(f"csv: {len(rows)} rows, {m['whole_cycles']} whole cycles, ends at x = 0: "
          f"{abs(rows[0, 1]) < 1e-9 and abs(rows[-1, 1]) < 1e-9}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


def ints(s):
    return tuple(int(round(float(v))) for v in s.split(","))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?")
    ap.add_argument("--probe", action="store_true", help="print ffprobe info and write a gridded first frame")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--roi", type=ints, help="search area x,y,w,h in full-frame px")
    ap.add_argument("--feature", type=ints, help="template box x,y,w,h inside the roi")
    ap.add_argument("--ref", type=lambda s: tuple(map(float, s.split(","))), help="x1,y1,x2,y2: two px points --ref-mm apart")
    ap.add_argument("--ref-mm", type=float, default=INSERT_MM, help=f"default {INSERT_MM} (an insert's length)")
    ap.add_argument("--mm-per-px", type=float)
    ap.add_argument("--start", type=float, default=0.0, help="clip time to start at, s")
    ap.add_argument("--duration", type=float, help="clip seconds to use")
    ap.add_argument("--slowdown", type=float, default=1.0, help="slow-motion factor baked into playback (e.g. 8 for 240 fps played at 30)")
    ap.add_argument("--max-step", type=float, help="px the feature may move between frames (default half the template)")
    ap.add_argument("--out", help="stroke CSV to write, e.g. bench/stroke_forum.csv")
    ap.add_argument("--plots", help="folder for track.csv, stroke.png, overlays (default out/stroke/<clip>)")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if not args.video:
        ap.error("video required")
    plot_dir = Path(args.plots) if args.plots else HERE / "out" / "stroke" / Path(args.video).stem
    if args.probe:
        print(json.dumps(probe(args.video), indent=1))
        probe_image(args.video, plot_dir)
        print(f"wrote {plot_dir / 'probe.png'}")
        return
    if not (args.roi and args.feature):
        ap.error("--roi and --feature are required (run --probe first to read coordinates)")
    m, meta = measure(args.video, args.roi, args.feature, args.ref, args.ref_mm, args.mm_per_px, args.start,
                      args.duration, args.slowdown, args.out, plot_dir, args.max_step)
    print(json.dumps(m, indent=1))
    print(f"wrote {args.out or '(no csv)'} and {plot_dir}")


if __name__ == "__main__":
    main()
