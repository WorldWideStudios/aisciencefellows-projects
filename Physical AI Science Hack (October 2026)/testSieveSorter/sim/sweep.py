"""Parameter sweeps over sorter.run() in parallel worker processes, with a standalone HTML report.

Run from sim\\ with the venv python:
    python sweep.py dtcheck [--quick]          dt 0.5 ms vs 0.25 ms, contact params fixed; penetration vs clearance
    python sweep.py compare [--quick] [--with-plinko]
                                               current mesh inserts vs future printed inserts (+ plinko), on
                                               BioKEA's firmware stroke at 50 and 5 mm/s, 5 seeds x 3 contact
                                               parameter sets, 30 s runs
    python sweep.py stroke [--quick]           firmware constant-speed stroke vs sine (and sawtooth), same amplitude
    python sweep.py vertical [--quick] [--design inserts:5mm,2mm --mix pasta=15,rice=40,quinoa=40]
                                               demo tray (inserts:5mm, pasta + rice): stroke along the flow axis (0 deg),
                                               a 45 deg throw and straight up (90 deg) at equal peak acceleration
                                               (sine, 2 g and 4 g), 3 contact parameter sets
    python sweep.py <preset> --report-only     rebuild summary.csv and report.html from runs.jsonl

Writes out\\sweeps\\<preset>\\runs.jsonl (one sorter.run() results dict per run, plus a "sweep" key with
the run's block, group, variant, seed and the sweep settings), summary.csv (per block, group and metric:
mean, sd, and the split into seed and parameter-set variation) and report.html (one file, works offline).

Metrics per run, from results["particles"] and results["timeseries"]:
    recovery:<kind>        fraction of the kind whose final zone is its ideal zone
    t50:<kind>, t90:<kind> seconds from the start of the shake until 50% / 90% of the kind sits in its
                           ideal zone (empty if never reached)
    upstream:<kind>        particles still in a zone above their ideal zone at the end (not through yet)
    moved                  particles that changed zone during the shake (0 = the stroke moved nothing)
    contamination:<zone>   fraction of a zone's final contents whose ideal zone is another zone
    jams:between, jams:lost, jam rate:runs with a jam, penetration (tray and particle contacts)
"""
import argparse
import copy
import csv
import dataclasses
import html
import json
import math
import os
import time
import traceback
from collections import Counter
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "sweeps"
CALIBRATION_JSON = HERE / "out" / "calibration" / "calibration.json"
WORKERS = max(1, (os.cpu_count() or 6) - 2)   # PERF.md: 22 on the 24-core laptop matches 24 and leaves 2 free

PRESETS = {"dtcheck": (3, 10.0), "compare": (5, 30.0), "stroke": (3, 20.0), "vertical": (6, 10.0)}   # (seeds, duration_s)
QUICK_SEEDS, QUICK_DURATION_S = 2, 2.0
DT_PAIR = [5e-4, 2.5e-4]
DT_CONTACT = {"timeconst": 0.002}             # held fixed for both timesteps; MuJoCo needs timeconst >= 2 dt

# BioKEA firmware (BugSorter src/main.cpp): constant speed, hard reversals, 2 cm stroke, 5 mm/s default,
# 50 mm/s cap. ramp_s (reversal sharpness) is a guess until the slow-motion video measures it.
FIRMWARE = {"profile": "constant_speed", "amp_mm": 10.0, "speed_mm_s": 50.0, "ramp_s": 0.01}
COMPARE_DESIGNS = [("current mesh", "inserts:mesh5,mesh2"), ("future printed", "inserts:5mm,2mm")]
COMPARE_STROKES = [("firmware stroke at 50 mm/s (cap)", FIRMWARE),
                   ("firmware stroke at 5 mm/s (default)", {**FIRMWARE, "speed_mm_s": 5.0})]
COMPARE_FALLBACK = [("pool 1.4 mm tunnel", "pool:w5p0,t1p4"), ("pool 1.3 mm tunnel", "pool:w5p0,t1p3")]
PLINKO = ("plinko", "plinko")
FRICTIONS = [0.3, 0.4, 0.5]                   # used when there is no calibration.json yet
STROKE_DESIGNS = ["inserts:5mm,2mm"]          # first one that builds; else the RunConfig default
STROKE_PROFILES = [                           # same amplitude and cycle rate (speed_mm_s / (4 amp) = 1.25 Hz)
    ("firmware constant speed 50 mm/s", FIRMWARE),
    ("sine, same amplitude and rate", {"profile": "sine", "amp_mm": 10.0, "speed_mm_s": 50.0}),
    ("sawtooth, same amplitude and rate", {**FIRMWARE, "profile": "sawtooth", "forward_fraction": 0.7}),
]
# The demo rig (Forum's photos): one 5 mm printed insert on a handheld DeWalt tool, pasta + rice, shaken up and
# down. The tool is not modelled, only the stroke; frequency and accelerations are assumptions (sim/VERTICAL.md).
VERTICAL_DESIGN = "inserts:5mm"
VERTICAL_MIX = {"pasta": 15, "rice": 40}
VERTICAL_FREQ_HZ = 20.0
VERTICAL_PEAK_G = [2.0, 4.0]                  # peak acceleration / g; amp_mm = peak * g / (2 pi f)^2
VERTICAL_ANGLES = [(0, "along the flow axis"), (45, "45 deg throw"), (90, "straight up")]
CLEARANCE_MM = 0.3                            # quinoa (1.1 mm thick) in the 1.4 mm tunnel
PEN_MARGINAL = 0.5                            # tray penetration above this fraction of the clearance is marginal
SPECIAL_ZONES = ("between", "lost")

# family: (chart title, unit, axis range or None for auto, number format). Order = report order.
FAMILIES = {
    "recovery": ("Recovery: fraction of each kind that ends in its ideal zone", "fraction", (0, 1), "{:.2f}"),
    "t50": ("Throughput: seconds from the start of the shake until 50% of each kind is in its ideal zone",
            "s", None, "{:.1f}"),
    "t90": ("Throughput: seconds until 90% of each kind is in its ideal zone", "s", None, "{:.1f}"),
    "upstream": ("Still on a screen or zone above their ideal zone at the end (particles per run)",
                 "particles", None, "{:.1f}"),
    "moved": ("Particles that changed zone during the shake (0 means the stroke moved nothing)",
              "particles", None, "{:.1f}"),
    "class recovery": ("Recovery by target class: fraction of the particles whose ideal zone is this zone "
                       "that end there", "fraction", (0, 1), "{:.2f}"),
    "contamination": ("Contamination: fraction of each zone's final contents that belongs in another zone",
                      "fraction", (0, 1), "{:.2f}"),
    "jams": ("Jams and losses at the end (particles per run)", "particles", None, "{:.1f}"),
    "jam rate": ("Jam frequency: fraction of runs ending with a particle stuck between zones", "fraction",
                 (0, 1), "{:.2f}"),
    "penetration": ("Largest contact overlap per run; the gate clearance applies to particle vs tray", "mm",
                    None, "{:.3f}"),
    "speed": ("Sim speed: simulated seconds per wall-clock second", "x realtime", None, "{:.2f}"),
    "count": ("Final count per kind and zone", "particles", None, "{:.1f}"),
}
LEAD_FAMILIES = ["recovery", "t50", "t90", "upstream", "moved"]
ZERO_HIDDEN = {"t50", "t90", "upstream", "jams"}   # charts skip items that are 0 in every run (e.g. retained pasta)
CHECK_FAMILIES = ["class recovery", "contamination", "jams", "jam rate", "penetration", "speed"]
TRAY_PEN = "penetration:particle vs tray"


# ---------------------------------------------------------------- running

def run_one(job):
    """Worker: one sorter.run(), tagged with job["tags"]; a failure comes back as an error record."""
    import sorter
    t0 = time.time()
    try:
        res = sorter.run(sorter.RunConfig(**job["cfg"]))
    except Exception:
        res = {"config": job["cfg"], "error": traceback.format_exc(), "wall_s": round(time.time() - t0, 2)}
    res["sweep"] = job["tags"]
    return res


def jsonable(o):
    return o.tolist() if hasattr(o, "tolist") else str(o)


def run_in_child(job, job_dir, i):
    """One job in its own python process. multiprocessing pools lose their semaphore handles in this
    Windows setup (WinError 6), so each run is a plain child process that writes its result to a file."""
    path = job_dir / f"job{i:04d}.json"
    path.write_text(json.dumps(job, default=jsonable), encoding="utf-8")
    out = path.with_suffix(".out.json")
    out.unlink(missing_ok=True)
    p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--job", str(path)],
                       cwd=HERE, capture_output=True, text=True)
    if p.returncode or not out.exists():
        return {"config": job["cfg"], "sweep": job["tags"], "error": (p.stderr or "no result written")[-3000:]}
    return json.loads(out.read_text(encoding="utf-8"))


def run_jobs(jobs, jsonl_path, workers=WORKERS):
    """Run jobs in parallel; each result is appended to jsonl_path as it finishes. Returns them in job order."""
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    job_dir = jsonl_path.parent / "jobs"
    job_dir.mkdir(exist_ok=True)
    results = [None] * len(jobs)
    t0 = time.time()
    n_workers = max(1, min(workers, len(jobs)))
    print(f"{len(jobs)} runs on {n_workers} workers -> {jsonl_path}", flush=True)
    with open(jsonl_path, "w", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=n_workers) as ex:
        futures = {ex.submit(run_in_child, j, job_dir, i): i for i, j in enumerate(jobs)}
        for done, fut in enumerate(as_completed(futures), 1):
            i = futures[fut]
            try:
                res = fut.result()
            except Exception:                       # e.g. a worker process died
                res = {"config": jobs[i]["cfg"], "sweep": jobs[i]["tags"], "error": traceback.format_exc()}
            results[i] = res
            f.write(json.dumps(res, default=jsonable) + "\n")
            f.flush()
            tg = res["sweep"]
            what = "ERROR " + res["error"].strip().splitlines()[-1] if "error" in res else \
                "recovery " + " ".join(f"{k} {v:.2f}" for k, v in res.get("recovery", {}).items()) +                 (f" UNSTABLE ({len(res['unstable_resets'])} resets)" if res.get("unstable_resets") else "")
            label = " | ".join(str(x) for x in (tg.get("block"), tg["group"], tg.get("variant")) if x)
            print(f"[{done}/{len(jobs)} {time.time() - t0:5.0f} s] {label} | seed {tg['seed']}: {what}", flush=True)
    return results


def load_runs(jsonl_path):
    runs = [json.loads(line) for line in open(jsonl_path, encoding="utf-8") if line.strip()]
    return sorted(runs, key=lambda r: r["sweep"].get("index", 0))


def make_cfg(base, **over):
    """A full RunConfig dict: base with overrides. contact is merged key by key; stroke is replaced whole."""
    cfg = copy.deepcopy(base)
    for k, v in over.items():
        cfg[k] = {**cfg[k], **v} if k == "contact" else copy.deepcopy(v)
    cfg["record_fps"], cfg["out_dir"] = 0, None
    return cfg


def try_build(spec):
    """None if designs.build(spec) works, else the error message."""
    try:
        import designs
        designs.build(spec)
        return None
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def param_sets():
    """[(label, contact overrides)], and where they came from."""
    if CALIBRATION_JSON.exists():
        cal = json.loads(CALIBRATION_JSON.read_text(encoding="utf-8"))
        return [(p["label"], p["contact"]) for p in cal["param_sets"]], \
            f"calibration.json ({cal.get('status', 'status unknown')})"
    return [(f"mu {f:.1f}", {"friction": f}) for f in FRICTIONS], \
        "default friction 0.3 / 0.4 / 0.5 (no calibration.json yet)"


def compare_plan(with_plinko, notes):
    """(designs [(role, spec)], strokes [(label, stroke or None)])."""
    errors = {spec: try_build(spec) for _, spec in COMPARE_DESIGNS}
    if any(errors.values()):
        notes.append("Fell back to the pool designs on their default stroke, because designs.build failed: " +
                     "; ".join(f"{s}: {e}" for s, e in errors.items() if e))
        return list(COMPARE_FALLBACK), [(None, None)]
    chosen = list(COMPARE_DESIGNS)
    if with_plinko:
        err = try_build(PLINKO[1])
        if err:
            notes.append(f"plinko left out: {err}")
        else:
            chosen.append(PLINKO)
    notes.append("Every design gets the identical stroke within a block, so a difference is the inserts.")
    return chosen, list(COMPARE_STROKES)


def build_jobs(preset, quick, with_plinko, base_over=None, seeds=None, duration=None):
    import sorter
    base = make_cfg(dataclasses.asdict(sorter.RunConfig()), **(base_over or {}))
    n_seeds, dur = (QUICK_SEEDS, QUICK_DURATION_S) if quick else PRESETS[preset]
    n_seeds, dur = seeds or n_seeds, duration or dur
    meta = {"preset": preset, "quick": quick, "duration_s": dur, "seeds": n_seeds, "workers": WORKERS,
            "base": {k: base[k] for k in ("design", "mix", "stroke", "dt", "contact", "settle_s")},
            "notes": [], "param_source": None, "param_sets": {}}
    plan = []                                    # (block, group, variant, overrides)
    if preset == "dtcheck":
        for dt in DT_PAIR:
            plan.append((None, f"dt {dt * 1e3:.2f} ms", None, {"dt": dt, "contact": DT_CONTACT}))
        meta["notes"].append(f"Contact params held fixed for both timesteps: {({**base['contact'], **DT_CONTACT})}.")
    elif preset == "compare":
        sets, meta["param_source"] = param_sets()
        meta["param_sets"] = dict(sets)
        chosen, strokes = compare_plan(with_plinko, meta["notes"])
        for block, stroke in strokes:
            for role, spec in chosen:
                for label, contact in sets:
                    over = {"design": spec, "contact": contact, **({"stroke": stroke} if stroke else {})}
                    plan.append((block, f"{role}: {spec}", label, over))
    elif preset == "vertical":
        sets, meta["param_source"] = param_sets()
        meta["param_sets"] = dict(sets)
        mix = (base_over or {}).get("mix") or VERTICAL_MIX
        design = (base_over or {}).get("design") or VERTICAL_DESIGN
        meta["notes"].append(f"Design {design}, mix {mix}. Sine at {VERTICAL_FREQ_HZ:g} Hz; within a block every "
                             "direction has the same peak acceleration, so a difference is the direction.")
        for peak in VERTICAL_PEAK_G:
            amp = peak * 9810.0 / (2 * math.pi * VERTICAL_FREQ_HZ) ** 2
            block = f"peak acceleration {peak:g} g ({amp:.2f} mm amplitude at {VERTICAL_FREQ_HZ:g} Hz)"
            for ang, name in VERTICAL_ANGLES:
                stroke = {"profile": "sine", "amp_mm": round(amp, 4), "freq_hz": VERTICAL_FREQ_HZ, "angle_deg": ang}
                for label, contact in sets:
                    plan.append((block, f"{ang} deg: {name}", label,
                                 {"design": design, "mix": mix, "stroke": stroke, "contact": contact}))
    elif preset == "stroke":
        spec = next((s for s in STROKE_DESIGNS if try_build(s) is None), base["design"])
        meta["notes"].append(f"Design {spec}. Every profile has a 10 mm amplitude and the same cycle rate "
                             f"(1.25 Hz, the firmware's 50 mm/s over a 2 cm stroke).")
        for label, stroke in STROKE_PROFILES:
            plan.append((None, label, None, {"design": spec, "stroke": stroke}))
    jobs = []
    for block, group, variant, over in plan:
        for seed in range(n_seeds):
            tags = {"preset": preset, "block": block, "group": group, "variant": variant, "seed": seed,
                    "index": len(jobs), "meta": meta}
            jobs.append({"cfg": make_cfg(base, duration_s=dur, seed=seed, **over), "tags": tags})
    meta["workers"] = max(1, min(WORKERS, len(jobs)))
    return jobs, meta


# ---------------------------------------------------------------- metrics

def frac(k, n):
    return k / n if n else None


def shake_start(res):
    """Timeseries times shifted so 0 is the start of the shake, and the index of the first shake sample."""
    t = np.asarray((res.get("timeseries") or {}).get("t", []), float) - res["config"].get("settle_s", 0.0)
    return t, int(np.searchsorted(t, -1e-9)) if len(t) else 0


def throughput(res):
    """t50/t90 per kind: seconds after the settle until 50% / 90% of the kind is in its ideal zone.

    The timeseries counts kinds per zone, not individual particles, so a zone's count is capped at
    the number of that kind whose ideal zone it is."""
    ts = res.get("timeseries") or {}
    t, _ = shake_start(res)
    n_kind = Counter(p["kind"] for p in res["particles"])
    n_ideal = Counter((p["kind"], p["ideal_zone"]) for p in res["particles"])
    out = {}
    for kind in res["kinds"]:
        in_ideal = np.zeros(len(t))
        for (k, z), n in n_ideal.items():
            if k == kind and len(t):
                in_ideal += np.minimum(np.asarray(ts["counts"][kind][z], float), n)
        for q in (50, 90):
            hit = np.flatnonzero(in_ideal >= q / 100 * n_kind[kind] - 1e-9) if n_kind[kind] else []
            out[f"t{q}:{kind}"] = round(max(0.0, float(t[hit[0]])), 3) if len(hit) else None
    return out


def moved(res):
    """Particles that changed zone between the start of the shake and the end (net, per kind and zone)."""
    ts = res.get("timeseries") or {}
    t, i0 = shake_start(res)
    if not len(t):
        return None
    return int(sum(max(0, zs[-1] - zs[min(i0, len(zs) - 1)]) for c in ts["counts"].values() for zs in c.values()))


def run_metrics(res, zone_label=None):
    """Flat {"family:item": value or None} for one results dict, in report order. zone_label renames zones
    in the per-zone items, so designs with differently named zones line up by flow position."""
    parts, kinds = res["particles"], res["kinds"]
    lab = lambda z: (zone_label or {}).get(z, z)
    zones = [z for z in res["zones"] if z not in SPECIAL_ZONES]
    order = {z: i for i, z in enumerate(zones)}
    m = {}
    for kind in kinds:
        ps = [p for p in parts if p["kind"] == kind]
        m[f"recovery:{kind}"] = frac(sum(p["final_zone"] == p["ideal_zone"] for p in ps), len(ps))
    m.update(throughput(res))
    for kind in kinds:
        m[f"upstream:{kind}"] = sum(1 for p in parts if p["kind"] == kind and p["final_zone"] in order
                                    and order[p["final_zone"]] < order.get(p["ideal_zone"], -1))
    m["moved:particles that changed zone"] = moved(res)
    for z in zones:
        ps = [p for p in parts if p["ideal_zone"] == z]
        if ps:
            m[f"class recovery:{lab(z)}"] = frac(sum(p["final_zone"] == z for p in ps), len(ps))
    for z in zones:
        ps = [p for p in parts if p["final_zone"] == z]
        m[f"contamination:{lab(z)}"] = frac(sum(p["ideal_zone"] != z for p in ps), len(ps))
    between = sum(p["final_zone"] == "between" for p in parts)
    m["jams:between"] = between
    m["jams:lost"] = sum(p["final_zone"] == "lost" for p in parts)
    m["jam rate:runs with a jam"] = 1.0 if between else 0.0
    m[TRAY_PEN] = res.get("max_penetration_mm")
    m["penetration:particle vs particle"] = res.get("max_penetration_particles_mm")
    m["speed:sim s per wall s"] = frac(res.get("sim_s", 0), res.get("wall_s", 0))
    for kind in kinds:
        for z in res["zones"]:
            m[f"count:{kind} in {lab(z)}"] = res["counts"][kind][z]
    return m


def stats(by_variant):
    """Mean/sd over every run, plus seed sd (within a parameter set) and parameter sd (between set means)."""
    def summ(vs):
        a = np.array([v for v in vs if v is not None], float)
        return {"n": len(a), "N": len(vs), "mean": float(a.mean()) if len(a) else None,
                "sd": float(a.std(ddof=1)) if len(a) > 1 else None,
                "min": float(a.min()) if len(a) else None, "max": float(a.max()) if len(a) else None}
    out = summ([v for vs in by_variant.values() for v in vs])
    out["variants"] = {k: summ(vs) for k, vs in by_variant.items()}
    out["sd_seed"] = out["sd_param"] = None
    if len(by_variant) > 1:
        within = [np.var([v for v in vs if v is not None], ddof=1) for vs in by_variant.values()
                  if sum(v is not None for v in vs) > 1]
        means = [s["mean"] for s in out["variants"].values() if s["mean"] is not None]
        out["sd_seed"] = float(np.sqrt(np.mean(within))) if within else None
        out["sd_param"] = float(np.std(means, ddof=1)) if len(means) > 1 else None
    return out


def zone_labels(runs):
    """Per-run {zone name: label}: zones at the same flow position share a label across designs,
    e.g. "zone 1 (on_mesh5 | on_5mm)"; a position with one name keeps it."""
    names = {}
    for r in runs:
        if "error" not in r:
            for i, z in enumerate(z for z in r["zones"] if z not in SPECIAL_ZONES):
                names.setdefault(i, {}).setdefault(z, None)
    pos = {i: next(iter(ns)) if len(ns) == 1 else f"zone {i + 1} ({' | '.join(ns)})" for i, ns in names.items()}
    return lambda res: {z: pos[i] for i, z in enumerate(z for z in res["zones"] if z not in SPECIAL_ZONES)}


def aggregate(runs):
    """{group: {metric: stats}}, groups and metrics in first-seen order; failed runs are skipped."""
    vals = {}
    label = zone_labels(runs)
    for r in runs:
        if "error" in r:
            continue
        g = vals.setdefault(r["sweep"]["group"], {})
        for k, v in run_metrics(r, label(r)).items():
            g.setdefault(k, {}).setdefault(r["sweep"].get("variant") or "all", []).append(v)
    return {g: {k: stats(bv) for k, bv in ms.items()} for g, ms in vals.items()}


def by_block(runs):
    blocks = {}
    for r in runs:
        blocks.setdefault(r["sweep"].get("block"), []).append(r)
    return blocks


def items_of(agg, family):
    seen = {}
    for ms in agg.values():
        for k in ms:
            fam, _, item = k.partition(":")
            if fam == family:
                seen.setdefault(item, None)
    return list(seen)


def write_summary(path, runs):
    cols = ["n", "N", "mean", "sd", "sd_seed", "sd_param", "min", "max"]
    rnd = lambda v: "" if v is None else round(v, 5)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["block", "group", "variant", "metric", "n_with_value", "n_runs", "mean", "sd", "sd_seed",
                    "sd_param", "min", "max"])
        for block, rs in by_block(runs).items():
            for g, ms in aggregate(rs).items():
                for metric, st in ms.items():
                    w.writerow([block or "", g, "all", metric] + [rnd(st.get(c)) for c in cols])
                    if len(st["variants"]) > 1:
                        for v, vs in st["variants"].items():
                            w.writerow([block or "", g, v, metric] + [rnd(vs.get(c)) for c in cols])


# ---------------------------------------------------------------- report (inline SVG, no scripts)

CSS = """
:root{--surface:#fcfcfb;--page:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;
--axis:#c3c2b7;--border:rgba(11,11,11,.10);--s0:#2a78d6;--s1:#eb6834;--s2:#1baf7a;--s3:#898781;
--good:#0ca30c;--warn:#a06c00;--bad:#d03b3b}
@media (prefers-color-scheme:dark){:root{--surface:#1a1a19;--page:#0d0d0d;--ink:#f0efec;--ink2:#c3c2b7;
--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);--s0:#3987e5;--s1:#d95926;--s2:#199e70;
--warn:#fab219;--bad:#e66767}}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 20px 60px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:34px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--grid)}
h3{font-size:14px;margin:18px 0 6px}p{margin:6px 0}.lede{color:var(--ink2);margin:0 0 14px}
ul{margin:6px 0;padding-left:20px}li{margin:2px 0}
table{border-collapse:collapse;font-variant-numeric:tabular-nums;background:var(--surface);margin:6px 0 14px;
border:1px solid var(--border)}
th,td{padding:4px 10px;border-bottom:1px solid var(--grid);text-align:right;vertical-align:top}
th:first-child,td:first-child{text-align:left}th{font-weight:600;color:var(--ink2);font-size:12px}
td.l{text-align:left}.pm{color:var(--ink2)}.split{color:var(--muted);font-size:11px}
.ok{color:var(--good);font-weight:600}.warn{color:var(--warn);font-weight:600}.bad{color:var(--bad);font-weight:600}
.banner{border:1px solid var(--bad);border-left-width:4px;padding:8px 12px;margin:10px 0;background:var(--surface)}
.flagrow td{background:rgba(208,59,59,.08)}
figure{margin:10px 0 18px;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:10px 4px 2px}
figcaption{font-weight:600;margin:0 10px 2px}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;margin:8px 0;color:var(--ink2);font-size:13px}
.legend span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;
background:var(--c)}
svg{display:block;max-width:100%;height:auto}
svg text{font:12px system-ui,-apple-system,"Segoe UI",sans-serif;fill:var(--ink2)}
svg .head{font-weight:600;fill:var(--ink)}svg .lab{fill:var(--ink)}svg .tick{fill:var(--muted);font-size:11px}
svg .val{font-variant-numeric:tabular-nums}svg .grid{stroke:var(--grid)}svg .base{stroke:var(--axis)}
svg .ref{stroke:var(--bad);stroke-width:1.5;stroke-dasharray:5 3}svg .reftext{fill:var(--bad);font-size:11px}
svg .bar{stroke-width:2;stroke-linecap:round;fill:none}svg .dot{stroke:var(--surface);stroke-width:2}
.s0{stroke:var(--s0);fill:var(--s0)}.s1{stroke:var(--s1);fill:var(--s1)}.s2{stroke:var(--s2);fill:var(--s2)}
.s3{stroke:var(--s3);fill:var(--s3)}
pre{white-space:pre-wrap;font-size:11px;color:var(--ink2);background:var(--surface);padding:8px;border:1px solid var(--border)}
code{font-size:12px}
"""


def esc(s):
    return html.escape(str(s))


def fmt(v, f="{:.2f}"):
    return "n/a" if v is None or (isinstance(v, float) and math.isnan(v)) else f.format(v)


def nice_step(span, n=5):
    raw = max(span, 1e-9) / n
    mag = 10 ** math.floor(math.log10(raw))
    return next(m * mag for m in (1, 2, 2.5, 5, 10) if raw <= m * mag * 1.0001)


def dot_plot(rows, unit, rng=None, ref=None, ref_label="", f="{:.2f}"):
    """Horizontal dot plot as inline SVG: one line per row, mean as a dot, +/- sd as a bar.

    rows: {"head": text} starts a category; data rows are {"group", "sub", "cls", "mean", "sd", "strong",
    "note", "tip", "marks"}. "group" is drawn on the row (direct label); strong rows get their value
    printed; "marks" [(label, value)] are drawn as small hollow circles under the bar (parameter-set means)."""
    W, LEFT, RIGHT, TOP, ROW, HEAD = 940, 300, 150, 26, 24, 22
    ends = [r["mean"] + (r.get("sd") or 0) for r in rows if r.get("mean") is not None]
    ends += [v for r in rows for _, v in r.get("marks", []) if v is not None]
    lo, hi = rng if rng else (0.0, max(ends + [ref or 0.0]) or 1.0)
    if not rng:
        hi = math.ceil(hi * 1.02 / nice_step(hi)) * nice_step(hi)
    sx = lambda v: LEFT + (min(max(v, lo), hi) - lo) / (hi - lo) * (W - LEFT - RIGHT)
    body, y = [], TOP
    for r in rows:
        if "head" in r:
            y += HEAD
            body.append(f'<text class="head" x="10" y="{y - 7}">{esc(r["head"])}</text>')
            continue
        y += ROW
        cy = y - ROW / 2 - (3 if r.get("marks") else 0)
        if r.get("group"):
            body.append(f'<text class="lab" x="22" y="{cy + 4}">{esc(r["group"])}</text>')
        if r.get("sub"):
            body.append(f'<text x="{LEFT - 10}" y="{cy + 4}" text-anchor="end">{esc(r["sub"])}</text>')
        if r.get("mean") is None:
            body.append(f'<text class="tick" x="{LEFT + 4}" y="{cy + 4}">no value{esc(r.get("note", ""))}</text>')
            continue
        m, sd = r["mean"], r.get("sd") or 0.0
        x, x0, x1 = sx(m), sx(m - sd), sx(m + sd)
        cls, rad, op = f's{min(r.get("cls", 0), 3)}', (5 if r.get("strong") else 3.6), (1 if r.get("strong") else 0.55)
        tip = r.get("tip") or f"{fmt(m, f)} +/- {fmt(sd, f)}"
        bar = (f'<line class="bar {cls}" x1="{x0:.1f}" y1="{cy}" x2="{x1:.1f}" y2="{cy}" opacity="{op}"/>'
               f'<line class="bar {cls}" x1="{x0:.1f}" y1="{cy - 3}" x2="{x0:.1f}" y2="{cy + 3}" opacity="{op}"/>'
               f'<line class="bar {cls}" x1="{x1:.1f}" y1="{cy - 3}" x2="{x1:.1f}" y2="{cy + 3}" opacity="{op}"/>'
               if sd > 0 else "")
        marks = "".join(f'<circle class="{cls}" cx="{sx(v):.1f}" cy="{cy + 8}" r="2.6" fill="none" '
                        f'stroke-width="1.5"><title>{esc(lab)}: {fmt(v, f)}</title></circle>'
                        for lab, v in r.get("marks", []) if v is not None)
        body.append(f'<g><title>{esc(tip)}</title><rect x="{LEFT}" y="{y - ROW}" width="{W - LEFT - RIGHT}" '
                    f'height="{ROW}" fill="transparent"/>{bar}<circle class="dot {cls}" cx="{x:.1f}" cy="{cy}" '
                    f'r="{rad}" fill-opacity="{op}"/>{marks}</g>')
        if r.get("strong"):
            pm = f" &#177; {fmt(sd, f)}" if r.get("sd") is not None else ""
            body.append(f'<text class="val" x="{W - RIGHT + 12}" y="{cy + 4}">{fmt(m, f)}{pm}'
                        f'{esc(r.get("note", ""))}</text>')
    step = nice_step(hi - lo)
    grid = []
    for k in range(int(round((hi - lo) / step)) + 1):
        v = lo + k * step
        grid.append(f'<line class="{"base" if k == 0 else "grid"}" x1="{sx(v):.1f}" y1="{TOP}" x2="{sx(v):.1f}" '
                    f'y2="{y + 4}"/><text class="tick" x="{sx(v):.1f}" y="{y + 18}" text-anchor="middle">'
                    f'{v:g}</text>')
    grid.append(f'<text class="tick" x="{W - RIGHT}" y="{y + 32}" text-anchor="end">{esc(unit)}</text>')
    if ref is not None:
        grid.append(f'<line class="ref" x1="{sx(ref):.1f}" y1="{TOP - 8}" x2="{sx(ref):.1f}" y2="{y + 4}"/>'
                    f'<text class="reftext" x="{sx(ref) + 4:.1f}" y="{TOP - 10}">{esc(ref_label)}</text>')
    h = y + 40
    return (f'<svg viewBox="0 0 {W} {h}" width="{W}" height="{h}" role="img">'
            + "".join(grid) + "".join(body) + "</svg>")


def legend(groups):
    return '<div class="legend">' + "".join(
        f'<span style="--c:var(--s{min(i, 3)})">{esc(g)}</span>' for i, g in enumerate(groups)) + "</div>"


def family_rows(agg, family, f, colour):
    """Dot-plot rows for one metric family: per item a heading, then one line per group with the pooled
    mean +/- sd, and each parameter set's mean as a small mark. Items that are 0 in every run are left out.
    Returns (rows, names of the left-out items)."""
    rows, zero, empty = [], [], []
    for item in items_of(agg, family):
        sts = {g: ms[f"{family}:{item}"] for g, ms in agg.items() if f"{family}:{item}" in ms}
        if not any(st["n"] for st in sts.values()):
            empty.append(item)
            continue
        if family in ZERO_HIDDEN and all(st["n"] and st["min"] == 0 and st["max"] == 0 for st in sts.values()):
            zero.append(item)
            continue
        rows.append({"head": item})
        for g, st in sts.items():
            note = f"  ({st['n']}/{st['N']} runs)" if st["n"] < st["N"] else ""
            marks = [(v, vs["mean"]) for v, vs in st["variants"].items()] if len(st["variants"]) > 1 else []
            tip = f"{g}: {fmt(st['mean'], f)} +/- {fmt(st['sd'], f)} over {st['n']} runs{note}" + "".join(
                f"; {v} {fmt(m, f)}" for v, m in marks)
            rows.append({"group": g, "cls": colour[g], "mean": st["mean"], "sd": st["sd"], "strong": True,
                         "note": note, "tip": tip, "marks": marks})
    return rows, zero, empty


def stat_cell(st, f):
    if st is None or st["mean"] is None:
        return '<span class="split">no value</span>' + (f'<div class="split">0/{st["N"]} runs</div>' if st else "")
    s = f'{fmt(st["mean"], f)} <span class="pm">&#177; {fmt(st["sd"], f)}</span>'
    if st.get("sd_seed") is not None or st.get("sd_param") is not None:
        s += f'<div class="split">seed sd {fmt(st["sd_seed"], f)} | param sd {fmt(st["sd_param"], f)}</div>'
    if st["n"] < st["N"]:
        s += f'<div class="split">reached in {st["n"]}/{st["N"]} runs</div>'
    return s


def metric_table(agg, families):
    groups = list(agg)
    head = "<tr><th>Metric</th>" + "".join(f"<th>{esc(g)}</th>" for g in groups)
    head += f"<th>{esc(groups[1])} minus {esc(groups[0])}</th>" if len(groups) == 2 else ""
    rows = []
    for fam in families:
        f = FAMILIES[fam][3]
        for item in items_of(agg, fam):
            sts = [agg[g].get(f"{fam}:{item}") for g in groups]
            cells = "".join(f"<td>{stat_cell(st, f)}</td>" for st in sts)
            if len(groups) == 2:
                a, b = (st["mean"] if st else None for st in sts)
                cells += f"<td>{fmt(b - a, '{:+' + f[2:]) if a is not None and b is not None else 'n/a'}</td>"
            rows.append(f"<tr><td>{esc(fam)}: {esc(item)}</td>{cells}</tr>")
    return f"<table>{head}</tr>{''.join(rows)}</table>"


def still_banner(agg):
    """Say plainly when a group's stroke moved nothing (no particle changed zone)."""
    sts = {g: ms.get("moved:particles that changed zone") for g, ms in agg.items()}
    still = [g for g, st in sts.items() if st and st["n"] and st["max"] == 0]
    out = []
    if still:
        n = sum(sts[g]["n"] for g in still)
        who = "every design" if len(still) == len(sts) else ", ".join(still)
        out.append(f'<p class="banner"><span class="bad">&#10007; Nothing moved.</span> In all {n} runs of '
                   f'<b>{esc(who)}</b>, no particle changed zone during the shake: at this stroke the dry grains '
                   f'stay where they were dropped. Kinds that should pass a screen show no recovery and no '
                   f'throughput here; kinds that should stay on top score 1 only because nothing moved.</p>')
    for g, st in sts.items():
        if g in still:
            continue
        if st and st["n"] and st["mean"] < 1:
            out.append(f'<p class="banner"><span class="warn">Almost nothing moved.</span> <b>{esc(g)}</b>: '
                       f'{st["mean"]:.1f} particles per run changed zone on average.</p>')
    return "".join(out)


def pen_status(v):
    if v is None:
        return '<span class="split">no value</span>'
    if v >= CLEARANCE_MM:
        return f'<span class="bad">&#10007; FAIL</span> {v:.3f} mm is at or above the {CLEARANCE_MM} mm clearance'
    if v >= PEN_MARGINAL * CLEARANCE_MM:
        return f'<span class="warn">MARGINAL</span> {v:.3f} mm is over {PEN_MARGINAL:.0%} of the clearance'
    return f'<span class="ok">&#10003; OK</span> {v:.3f} mm is under {PEN_MARGINAL:.0%} of the clearance'


def penetration_table(runs):
    rows = []
    for block, rs in by_block(runs).items():
        for g, ms in aggregate(rs).items():
            st, pp = ms.get(TRAY_PEN), ms.get("penetration:particle vs particle")
            rows.append(f'<tr><td>{esc(" | ".join(x for x in (block, g) if x))}</td>'
                        f'<td class="l">{pen_status(st["max"] if st else None)}</td>'
                        f'<td>{fmt(pp["max"] if pp else None, "{:.3f}")}</td></tr>')
    return ("<table><tr><th>Group</th><th>Largest particle-vs-tray overlap in any run</th>"
            f"<th>Largest particle-vs-particle overlap, mm</th></tr>{''.join(rows)}</table>")


def dt_section(agg):
    """dtcheck: final counts per kind and zone side by side for the two timesteps."""
    groups = list(agg)
    if len(groups) != 2:
        return "<p>dt check needs exactly two timestep groups.</p>"
    a, b = (agg[g] for g in groups)
    rows, flagged, total = [], 0, 0
    for item in items_of(agg, "count"):
        sa, sb = a.get(f"count:{item}"), b.get(f"count:{item}")
        if not sa or not sb or (not sa["mean"] and not sb["mean"]):
            continue
        total += 1
        diff = sb["mean"] - sa["mean"]
        noise = 2 * math.sqrt(((sa["sd"] or 0) ** 2 + (sb["sd"] or 0) ** 2) / 2)
        flag = abs(diff) > max(noise, 1.0)
        flagged += flag
        rows.append(f'<tr{" class=flagrow" if flag else ""}><td>{esc(item)}</td><td>{stat_cell(sa, "{:.1f}")}</td>'
                    f'<td>{stat_cell(sb, "{:.1f}")}</td><td>{diff:+.1f}</td>'
                    f'<td class="l">{"&#10007; beyond seed noise" if flag else "&#10003; within"}</td></tr>')
    verdict = (f'<p class="ok">&#10003; All {total} kind/zone counts agree between the two timesteps within seed '
               f'noise (2 sd, at least 1 particle).</p>' if not flagged else
               f'<p class="bad">&#10007; {flagged} of {total} kind/zone counts differ by more than seed noise '
               f'(2 sd, at least 1 particle). Results depend on dt: use the smaller dt or stiffer contacts '
               f'before trusting a comparison.</p>')
    table = (f"<table><tr><th>Kind in zone</th><th>{esc(groups[0])}</th><th>{esc(groups[1])}</th>"
             f"<th>Difference</th><th>Verdict</th></tr>{''.join(rows)}</table>")
    return verdict + table


def design_info_table(runs):
    first = {}
    for r in runs:
        if "error" not in r:
            first.setdefault(r["design"], r)
    rows = "".join(f'<tr><td><code>{esc(d)}</code></td><td class="l">'
                   + "<br>".join(f"{esc(k)}: {esc(json.dumps(v, default=str)[:160])}"
                                 for k, v in (r.get("design_info") or {}).items()) + "</td></tr>"
                   for d, r in first.items())
    return f"<table><tr><th>Design</th><th>design_info</th></tr>{rows}</table>"


def html_page(title, body):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style></head>'
            f'<body><main>{body}</main></body></html>')


def figure(fam, agg, colour):
    title, unit, rng, f = FAMILIES[fam]
    rows, zero, empty = family_rows(agg, fam, f, colour)
    zero_note = "".join(f'<p class="split" style="margin:0 10px 6px">{label}: {esc(", ".join(items))}.</p>'
                        for label, items in (("Always 0, not drawn", zero),
                                             ("No value in any run (never reached), not drawn", empty)) if items)
    if not rows:
        return f"<figure><figcaption>{esc(title)}</figcaption>{zero_note}</figure>" if zero_note else ""
    marks = any(r.get("marks") for r in rows)
    how = ('<p class="split" style="margin:0 10px">Dot and bar: mean &#177; sd over all runs. Small hollow '
           'circles: the mean of each parameter set (hover for names).</p>' if marks else "")
    ref = CLEARANCE_MM if fam == "penetration" else None
    svg = dot_plot(rows, unit, rng, ref, f"{CLEARANCE_MM} mm gate clearance", f)
    return f"<figure><figcaption>{esc(title)}</figcaption>{how}{zero_note}{svg}</figure>"


def report(runs, meta):
    ok = [r for r in runs if "error" not in r]
    failed = [r for r in runs if "error" in r]
    groups = list(dict.fromkeys(r["sweep"]["group"] for r in runs))
    colour = {g: i for i, g in enumerate(groups)}
    blocks = by_block(runs)
    variants = list(dict.fromkeys(r["sweep"]["variant"] for r in runs if r["sweep"].get("variant")))
    wall = sum(r.get("wall_s") or 0 for r in runs)
    shape = (f"{len(blocks)} strokes x " if len(blocks) > 1 else "") + f"{len(groups)} groups" + \
        (f" x {len(variants)} parameter sets" if variants else "") + \
        f" x {meta['seeds']} seeds, {meta['duration_s']:g} s each"
    b = meta["base"]
    out = [f"<h1>Sweep: {esc(meta['preset'])}{' (quick)' if meta['quick'] else ''}</h1>",
           f'<p class="lede">{esc(shape)}. {len(ok)} runs ok, {len(failed)} failed, '
           f'{wall / 60:.1f} min of sim stepping (model building not counted) on {meta["workers"]} workers. Generated '
           f'{datetime.now():%Y-%m-%d %H:%M} by sweep.py.</p><ul>',
           "".join(f"<li>{esc(n)}</li>" for n in meta["notes"]),
           f"<li>Mix {esc(b['mix'])}; dt {b['dt']} s and contact {esc(b['contact'])} unless the group says "
           f"otherwise; {b['settle_s']} s settle before the shake.</li>"]
    if meta.get("param_source"):
        out.append(f"<li>Parameter sets from {esc(meta['param_source'])}: " +
                   "; ".join(f"<b>{esc(k)}</b> {esc(v)}" for k, v in meta["param_sets"].items()) + "</li>")
    strokes = dict.fromkeys(json.dumps(r["config"]["stroke"]) for r in ok)
    out.append("<li>Strokes: " + "; ".join(f"<code>{esc(s)}</code>" for s in strokes) + "</li></ul>")
    if not ok:
        out.append('<p class="bad">No run finished; see the failures below.</p>')
    else:
        out.append(legend(groups))
        if meta["preset"] == "dtcheck":
            agg = aggregate(ok)
            out += ["<h2>Timestep check: final counts at both timesteps</h2>", dt_section(agg),
                    "<h3>Penetration vs gate clearance</h3>", penetration_table(ok), figure("penetration", agg, colour)]
        for block, rs in blocks.items():
            agg = aggregate(rs)
            if not agg:
                continue
            at = f": {block}" if block else ""
            out += [f"<h2>Throughput and recovery{esc(at)}</h2>", still_banner(agg),
                    "<p>Mean &#177; sd over all runs in a group. Where a group has several parameter sets, the "
                    "small line under each value splits the sd into seed variation (within a set) and parameter "
                    "variation (between set means).</p>", metric_table(agg, LEAD_FAMILIES)]
            out += [figure(fam, agg, colour) for fam in LEAD_FAMILIES]
            out += [f"<h2>Contamination, jams and checks{esc(at)}</h2>", metric_table(agg, CHECK_FAMILIES)]
            out += [figure(fam, agg, colour) for fam in ("contamination", "jams")]
        if meta["preset"] != "dtcheck":
            out += ["<h2>Penetration vs gate clearance</h2>", penetration_table(ok)]
        out += ["<h2>Designs</h2>", design_info_table(ok)]
    if failed:
        out.append(f"<h2>Failed runs ({len(failed)})</h2>")
        for r in failed:
            tg = r["sweep"]
            label = " | ".join(str(x) for x in (tg.get("block"), tg["group"], tg.get("variant")) if x)
            out.append(f"<h3>{esc(label)} seed {tg['seed']}</h3>"
                       f"<pre>{esc(chr(10).join(r['error'].strip().splitlines()[-6:]))}</pre>")
    out.append("<h2>How to read this</h2><ul>"
               "<li><b>Recovery</b>: fraction of a kind whose final zone is its ideal zone (the zone it would "
               "reach if every opening cut perfectly, from its dimensions).</li>"
               "<li><b>t50 / t90</b>: seconds from the start of the shake until 50% / 90% of all particles of a "
               "kind sit in their ideal zone, from the 10 Hz zone counts. No value when never reached; the table "
               "says in how many runs it was reached. Kinds whose ideal zone is where they are dropped read 0.</li>"
               "<li><b>Upstream</b>: particles still in a zone above their ideal zone at the end, so not through "
               "their screen yet. <b>Moved</b>: particles that changed zone during the shake.</li>"
               "<li><b>Contamination</b>: fraction of a zone's final contents whose ideal zone is another zone. "
               "<b>Between</b> means stuck outside every zone box (in a gate or screen); <b>lost</b> means out "
               "of the tray.</li>"
               f"<li><b>Penetration</b>: deepest contact overlap seen in a run. Particle-vs-tray overlap should "
               f"stay well under the {CLEARANCE_MM} mm clearance between quinoa and the 1.4 mm tunnel, or the "
               f"sim can squeeze grains through openings they would not pass.</li></ul>")
    return html_page(f"Sweep {meta['preset']}", "".join(out))


def write_outputs(out_dir, runs, meta):
    write_summary(out_dir / "summary.csv", runs)
    (out_dir / "report.html").write_text(report(runs, meta), encoding="utf-8")
    print(f"wrote {out_dir / 'summary.csv'}\nwrote {out_dir / 'report.html'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preset", choices=list(PRESETS))
    ap.add_argument("--quick", action="store_true", help=f"{QUICK_SEEDS} seeds, {QUICK_DURATION_S:g} s runs")
    ap.add_argument("--with-plinko", action="store_true", help="compare: add plinko as a third design")
    ap.add_argument("--report-only", action="store_true", help="rebuild summary.csv and report.html from runs.jsonl")
    ap.add_argument("--mix", help="particle mix, e.g. rice=30,quinoa=30,insect_elongate=10")
    ap.add_argument("--design", help="design spec (vertical: instead of the demo tray, e.g. inserts:5mm,2mm)")
    ap.add_argument("--spray", choices=["default", "bench"], help="jets on: each design's placeholders, or bench/jets.csv")
    ap.add_argument("--dt", type=float, help="timestep, s")
    ap.add_argument("--timeconst", type=float, help="contact time constant, s (>= 2 dt)")
    ap.add_argument("--seeds", type=int, help="seeds per setting (overrides the preset)")
    ap.add_argument("--duration", type=float, help="shake seconds per run (overrides the preset)")
    ap.add_argument("--name", help="output folder under out\\sweeps (default: the preset)")
    ap.add_argument("--workers", type=int, default=WORKERS, help=f"parallel runs (default {WORKERS})")
    args = ap.parse_args()
    import sorter
    base_over = {}
    if args.mix:
        base_over["mix"] = sorter.parse_kv(args.mix)
    if args.design:
        base_over["design"] = args.design
    if args.spray:
        base_over["spray"] = {"jets": args.spray}
    if args.dt:
        base_over["dt"] = args.dt
    if args.timeconst:
        base_over["contact"] = {"timeconst": args.timeconst}
    out_dir = OUT / (args.name or args.preset)
    jsonl = out_dir / "runs.jsonl"
    if args.report_only:
        runs = load_runs(jsonl)
        meta = runs[0]["sweep"]["meta"]
    else:
        jobs, meta = build_jobs(args.preset, args.quick, args.with_plinko, base_over, args.seeds, args.duration)
        for n in meta["notes"]:
            print("note:", n)
        meta["workers"] = max(1, min(args.workers, len(jobs)))
        runs = run_jobs(jobs, jsonl, args.workers)
    write_outputs(out_dir, runs, meta)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--job":        # child process started by run_in_child
        job_path = Path(sys.argv[2])
        job_path.with_suffix(".out.json").write_text(
            json.dumps(run_one(json.loads(job_path.read_text(encoding="utf-8"))), default=jsonable), encoding="utf-8")
    else:
        main()
