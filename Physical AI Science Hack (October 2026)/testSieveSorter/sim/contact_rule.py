"""Pick the solver timestep and contact time constant for a run from its design's tightest gate clearance and its
stroke. Physics session, 2026-10-25. The measurements are in VERTICAL.md ("Contact rule") and come from instab.py.

Why. Contacts are soft: a grain pressed onto the tray sinks into it a little. Once that overlap reaches about half
of a gate's clearance (the margin by which a grain fits or misses the opening), the sim can let a grain through a
gate it shouldn't pass, which is why the optimizer flags such runs (PEN_FLAG = 0.5). A smaller contact time constant
cuts the overlap, but it needs a smaller timestep (timeconst >= 2 dt), at about 2x the wall time per halving.

What drives the overlap is the stroke's profile and direction, not its peak acceleration alone. The firmware's
constant-speed stroke never throws the grains: they slide and get knocked at each reversal, so pointing it up presses
*less* than running it along the tray. A sine above 1 g vertical throws them, and the landings press hardest.

Rule. Take the cheapest setting whose measured overlap for this stroke is at most FLAG x the clearance. The measured
overlap is looked up among the strokes of the same profile that were measured (MEASURED): at the gentlest measured
level whose peak acceleration and peak speed are both at least this stroke's (a lower frequency at the same
acceleration moves faster and lands harder), interpolated linearly in angle. A stroke between two measured levels gets
the harder one's overlap, so the rule errs on the safe side. Anything else is unmeasured, and pick() returns the
stiffest setting and says so.

The overlap is the worst design's median of the per-run maximum, read every step after the settle, on the surfaces
that bound an opening: the screen of inserts:5mm; the gates of pool:w5p0,t1p4 and the floor under them (its 1.4 mm
tunnel leaves quinoa 0.3 mm, and a grain sunk into the floor clears a lower ceiling); and the rods of plinko, which
grains hit after dropping from the layer above. It comes from instab.py on the grains76 and insects70 mixes x 3 seeds
per design, 2 s of shaking. Keep checking each run's own overlap and unstable_resets afterwards: the rule picks the
setting, it doesn't replace the flag.

Not covered yet: the stacked rig (inserts:5mm,2mm). Its 2 mm screen takes about twice the overlap of these designs
under the firmware stroke (verify.py's probe: 0.179 / 0.076 / 0.045 mm), so the rule picks one setting too soft for
it. Use 0.0625 / 0.125 ms there until the grid is rerun with it (opt/VERIFY.md).

    from contact_rule import pick
    dt, tc, why = pick(0.3, {"profile": "sine", "amp_mm": 1.24, "freq_hz": 20, "angle_deg": 90})
    cfg = sweep.make_cfg(base, dt=dt, contact={"timeconst": tc})

The clearance is the as-built margin in mm (optimize.py's clearance()); None means no gate is near size.

Run from sim\\ (WSL venv on this laptop):
    python contact_rule.py --clearance 0.3 --stroke sine:amp_mm=1.24,freq_hz=20,angle_deg=90
    python contact_rule.py --table                              the measured overlaps the rule reads
    python contact_rule.py --rebuild out/instab/rule2.jsonl out/instab/rule2_plinko.jsonl
                                                                recompute them from instab.py output
"""
import argparse
import collections
import json

import numpy as np

import sorter

FLAG = 0.5                       # optimize.py's PEN_FLAG: overlap >= FLAG x clearance is untrustworthy
OPENING_ROLES = {"inserts:5mm": ("screen",), "pool:w5p0,t1p4": ("gate", "floor"), "plinko": ("gate",)}
FW = "constant_speed:amp_mm=10,speed_mm_s=50,ramp_s=0.01"
TOL_G, TOL_V = 0.05, 1.05        # within 0.05 g and 5 % of a measured level's peak acceleration and speed
# (dt, timeconst) in s, cheapest first, with the wall time relative to the first (instab.py, rule2.jsonl)
SETTINGS = {(2.5e-4, 5e-4): 1.0, (1.25e-4, 2.5e-4): 1.9, (6.25e-5, 1.25e-4): 3.8}
# Overlap (mm) by setting and stroke, from
# python contact_rule.py --rebuild out/instab/rule2.jsonl out/instab/rule2_plinko.jsonl
MEASURED = {
    (2.5e-4, 5e-4): {
        FW: 0.092,
        f"{FW},angle_deg=45": 0.093,
        f"{FW},angle_deg=90": 0.023,
        "sine:amp_mm=1.242,freq_hz=20,angle_deg=90": 0.236,
        "sine:amp_mm=2.485,freq_hz=20,angle_deg=45": 0.39,
        "sine:amp_mm=2.485,freq_hz=20,angle_deg=90": 0.521,
        "sine:amp_mm=4.970,freq_hz=20,angle_deg=90": 0.661,
    },
    (1.25e-4, 2.5e-4): {
        FW: 0.047,
        f"{FW},angle_deg=45": 0.048,
        f"{FW},angle_deg=90": 0.02,
        "sine:amp_mm=1.242,freq_hz=20,angle_deg=90": 0.129,
        "sine:amp_mm=2.485,freq_hz=20,angle_deg=45": 0.345,
        "sine:amp_mm=2.485,freq_hz=20,angle_deg=90": 0.244,
        "sine:amp_mm=4.970,freq_hz=20,angle_deg=90": 0.612,
    },
    (6.25e-5, 1.25e-4): {
        FW: 0.023,
        f"{FW},angle_deg=45": 0.021,
        f"{FW},angle_deg=90": 0.005,
        "sine:amp_mm=1.242,freq_hz=20,angle_deg=90": 0.08,
        "sine:amp_mm=2.485,freq_hz=20,angle_deg=45": 0.144,
        "sine:amp_mm=2.485,freq_hz=20,angle_deg=90": 0.194,
        "sine:amp_mm=4.970,freq_hz=20,angle_deg=90": 0.242,
    },
}


def parse_stroke(spec):
    """sorter.py --stroke syntax ('sine:amp_mm=1.24,freq_hz=20,angle_deg=90') -> stroke dict."""
    profile, _, rest = spec.partition(":")
    return {"profile": profile, **sorter.parse_kv(rest)}


def intensity(stroke):
    """(peak acceleration along the stroke axis in g, peak speed in mm/s, angle above the tray in degrees). No design
    is needed: only the axis' vertical part matters here."""
    if stroke.get("axis") is not None:
        ax = np.asarray(stroke["axis"], float)
        angle = float(np.degrees(np.arcsin(min(1.0, abs(ax[2]) / np.linalg.norm(ax)))))
    else:
        angle = float(stroke.get("angle_deg", 0.0))
    if stroke.get("profile", "sine") == "none":
        return 0.0, 0.0, angle
    f = stroke.get("freq_hz", 10.0)
    if "speed_mm_s" in stroke:
        f = stroke["speed_mm_s"] / (4 * stroke.get("amp_mm", 3.0))
    dt = 1.25e-4
    _, v, a = sorter.stroke_profile(stroke, int(max(2.0, 2.0 / f) / dt), dt)
    return float(np.abs(a).max() / sorter.G), float(np.abs(v).max()), angle


def predicted(setting, stroke):
    """(overlap mm, note) for one setting, from MEASURED; (None, why) when the stroke wasn't measured."""
    profile = stroke.get("profile", "sine")
    if profile == "none":
        return 0.0, "no stroke"
    peak, speed, angle = intensity(stroke)
    levels = collections.defaultdict(list)
    for spec, pen in MEASURED.get(setting, {}).items():
        s = parse_stroke(spec)
        if s["profile"] == profile:
            p, v, a = intensity(s)
            levels[(round(p, 2), round(v))].append((a, pen))
    for p, v in sorted(levels):
        pts = sorted(levels[(p, v)])
        if p + TOL_G >= peak and v * TOL_V >= speed and pts[0][0] - 1e-6 <= angle <= pts[-1][0] + 1e-6:
            a, pen = zip(*pts)
            return (float(np.interp(angle, a, pen)),
                    f"measured at {p:.2f} g, {v:g} mm/s, {'/'.join(f'{x:g}' for x in a)} deg")
    return None, f"{profile} at {peak:.2f} g, {speed:.0f} mm/s, {angle:g} deg is unmeasured"


def pick(clearance_mm, stroke):
    """(dt, timeconst, why) for a run with this tightest gate clearance (mm, None if no gate is near size) and stroke
    (a sorter stroke dict). The cheapest setting that keeps the expected overlap under FLAG x the clearance; if none
    does, the stiffest, and why says so."""
    order = sorted(SETTINGS, key=SETTINGS.get)
    if clearance_mm is None:
        dt, tc = order[0]
        return dt, tc, "no gate near size: production contacts"
    limit = FLAG * clearance_mm
    for dt, tc in order:
        pen, note = predicted((dt, tc), stroke)
        if pen is not None and pen <= limit:
            return dt, tc, (f"clearance {clearance_mm:g} mm: expected overlap {pen:.3f} mm <= {limit:.3f} mm ({note}), "
                            f"{SETTINGS[(dt, tc)]:g}x production wall time")
    dt, tc = order[-1]
    pen, note = predicted((dt, tc), stroke)
    if pen is None:
        return dt, tc, (f"clearance {clearance_mm:g} mm: {note}, so the stiffest setting as a precaution; measure "
                        "this stroke with instab.py and add it to MEASURED")
    return dt, tc, (f"clearance {clearance_mm:g} mm: no setting keeps the expected overlap under {limit:.3f} mm "
                    f"(stiffest: {pen:.3f} mm, {note}); results near this gate are untrustworthy, so soften the "
                    "stroke or widen the gate")


def rebuild(paths):
    """MEASURED recomputed from instab.py output (records with max_pen_role): per setting and stroke, the worse
    design's median of the per-run maximum overlap on the design's OPENING_ROLES."""
    runs = collections.defaultdict(list)
    for path in paths:
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            roles = OPENING_ROLES.get(r.get("design"))
            if roles and r.get("max_pen_role") and not r.get("unstable"):
                v = max(r["max_pen_role"].get(x, 0.0) for x in roles)
                runs[((r["dt"], r["tc"]), r.get("stroke", FW), r["design"])].append(v)
    out = collections.defaultdict(dict)
    for (setting, stroke, _), v in runs.items():
        if setting in SETTINGS:
            out[setting][stroke] = round(max(out[setting].get(stroke, 0.0), float(np.median(v))), 3)
    order = lambda kv: (parse_stroke(kv[0])["profile"], *intensity(parse_stroke(kv[0])))
    return {k: dict(sorted(out[k].items(), key=order)) for k in SETTINGS if k in out}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clearance", type=float, help="tightest gate clearance, mm (omit: no gate near size)")
    ap.add_argument("--stroke", default=FW, help="sorter.py --stroke syntax (default: the firmware stroke)")
    ap.add_argument("--table", action="store_true", help="print the measured overlaps by setting and stroke")
    ap.add_argument("--rebuild", nargs="+", metavar="JSONL", help="recompute MEASURED from instab.py output")
    args = ap.parse_args()
    if args.rebuild:
        for setting, rows in rebuild(args.rebuild).items():
            print(f"    {setting}: {{")
            for s, v in rows.items():
                print(f"        {'FW' if s == FW else repr(s)}: {v},")
            print("    },")
        return
    if args.table:
        for (dt, tc), rows in MEASURED.items():
            print(f"dt {dt * 1e3:g} ms, timeconst {tc * 1e3:g} ms ({SETTINGS[(dt, tc)]:g}x wall time)")
            for s, pen in rows.items():
                p, v, a = intensity(parse_stroke(s))
                print(f"    {pen:.3f} mm  {p:4.2f} g, {v:3.0f} mm/s at {a:2g} deg  {s}")
        return
    dt, tc, why = pick(args.clearance, parse_stroke(args.stroke))
    print(f"--dt {dt:g} --timeconst {tc:g}    # {why}")


if __name__ == "__main__":
    main()
