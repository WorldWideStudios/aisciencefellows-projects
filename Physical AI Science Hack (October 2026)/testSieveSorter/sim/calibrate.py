"""Fit contact parameters to bench counts, then predict the held-out bench configuration.

Run from sim\\ with the venv python:
    python calibrate.py bench\\bench_counts.csv [--clear bench\\clear_times.csv] [--quick]
    python calibrate.py --zones "inserts:5mm,2mm"     print the zone names to write on the bench sheets

bench_counts.csv (see BENCH.md): run_id, split (fit|holdout), design, stroke_profile, amp_mm, freq_hz,
duration_s, kind, zone, count, and optionally speed_mm_s, ramp_s, stroke_csv (relative to the CSV's folder).
Rows sharing a run_id are one bench run; runs with the same split and settings are repeats of one
configuration. The sim drops in the mean bench total of each kind.

1. Fit: every friction x dampratio point on the grid, SEEDS seeds each, on every fit configuration;
   score = RMS difference between simulated and observed zone fractions per kind (all kinds, zones, configs).
   The best point must keep particle-vs-tray overlap under the gate clearance.
2. Uncertainty: grid points within (bench repeat noise or sim seed noise) of the best score are plausible;
   their friction range (at least one grid step either side) gives the low / best / high parameter sets
   that sweep.py compare uses.
3. Holdout: the best point predicts the holdout configuration(s), HOLDOUT_SEEDS seeds; predicted vs observed
   counts with spread. "validated" needs holdout rows, with settings that differ from every fit
   configuration, and holdout RMS error <= HOLDOUT_TOL.
4. --clear: the best point predicts how many of each kind are still on each screen at the bench's timed
   checkpoints (clear_times.csv), as a throughput check.

Writes out\\calibration\\calibration.json (read by sweep.py compare), calibration.html, and the runs as
fit_runs.jsonl / holdout_runs.jsonl / clear_runs.jsonl. --quick (smoke test) writes to out\\calibration\\quick\\.
"""
import argparse
import csv
import dataclasses
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

import sweep
from sweep import esc, fmt

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "calibration"
FRICTIONS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
DAMPRATIOS = [1.0, 0.5, 0.25]                 # bounce: 1 = no rebound, lower = bouncier
TIMECONST = 0.002                             # held: at 0.005 grains sank 0.57 mm, past the 0.3 mm gate clearance
SEEDS, HOLDOUT_SEEDS = 3, 5
HOLDOUT_TOL = 0.10                            # max holdout RMS zone-fraction error to call the fit validated
QUICK = {"frictions": [0.3, 0.5], "dampratios": [1.0], "seeds": 1, "holdout_seeds": 2, "max_duration_s": 2.0}
REQUIRED = ["run_id", "split", "design", "stroke_profile", "amp_mm", "freq_hz", "duration_s", "kind", "zone", "count"]
CLEAR_REQUIRED = ["run_id", "design", "stroke_profile", "amp_mm", "freq_hz", "kind", "n_loaded", "zone", "t_s",
                  "n_remaining"]
STROKE_KEYS = ["amp_mm", "freq_hz", "speed_mm_s", "ramp_s"]


# ---------------------------------------------------------------- bench sheets

def read_rows(path, required):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]
    missing = [c for c in required if not rows or c not in rows[0]]
    rows = [r for r in rows if any(r.values()) and not r.get(required[0], "").startswith("#")]
    if missing or not rows:
        raise SystemExit(f"{path}: missing columns {missing}" if missing and rows else
                         f"{path}: no data rows yet (rows starting with # are examples and are skipped)")
    return rows


def stroke_of(r, base_dir):
    s = {"profile": r["stroke_profile"] or "sine"}
    s.update({k: float(r[k]) for k in STROKE_KEYS if r.get(k)})
    if s["profile"] == "csv":
        p = Path(r.get("stroke_csv") or "missing.csv")
        p = p if p.is_absolute() else base_dir / p
        if not p.exists():
            raise SystemExit(f"run {r['run_id']}: stroke_csv {p} not found")
        s["csv"] = str(p.resolve())
    return s


def read_bench(path):
    """Bench configurations: [{"id", "split", "design", "stroke", "duration_s", "runs": [{kind: {zone: n}}], "mix"}]."""
    configs, run_of = {}, {}
    for r in read_rows(path, REQUIRED):
        split = r["split"].lower()
        if split not in ("fit", "holdout"):
            raise SystemExit(f"run {r['run_id']}: split must be fit or holdout, not {r['split']!r}")
        settings = (r["design"], json.dumps(stroke_of(r, path.parent), sort_keys=True), float(r["duration_s"]))
        key = (split, *settings)
        if run_of.setdefault(r["run_id"], key) != key:
            raise SystemExit(f"run {r['run_id']}: its rows disagree on split, design, stroke or duration")
        c = configs.setdefault(key, {"split": split, "design": settings[0], "stroke": json.loads(settings[1]),
                                     "duration_s": settings[2], "settings": settings, "runs": {}})
        counts = c["runs"].setdefault(r["run_id"], {}).setdefault(r["kind"], {})
        counts[r["zone"]] = counts.get(r["zone"], 0) + int(float(r["count"] or 0))
    out = []
    for i, c in enumerate(configs.values(), 1):
        c["run_ids"], c["runs"] = list(c["runs"]), list(c["runs"].values())
        kinds = list(dict.fromkeys(k for run in c["runs"] for k in run))
        c["mix"] = {k: int(round(np.mean([sum(run.get(k, {}).values()) for run in c["runs"]]))) for k in kinds}
        c["id"] = f"{c['split']} {i}"
        c["label"] = f"{c['id']}: {c['design']}, {stroke_label(c['stroke'])}, {c['duration_s']:g} s, " \
                     f"{len(c['runs'])} repeat{'s' if len(c['runs']) > 1 else ''}"
        out.append(c)
    return out


def read_clear(path):
    """Timed checkpoints: [{"id", "design", "stroke", "mix", "points": {(kind, zone, t_s): [n_remaining...]}}]."""
    configs = {}
    rows = read_rows(path, CLEAR_REQUIRED)
    loaded = defaultdict(dict)
    for r in rows:
        loaded[r["run_id"]][r["kind"]] = int(float(r["n_loaded"]))
    for r in rows:
        stroke = stroke_of(r, path.parent)
        key = (r["design"], json.dumps(stroke, sort_keys=True), json.dumps(loaded[r["run_id"]], sort_keys=True))
        c = configs.setdefault(key, {"design": r["design"], "stroke": stroke, "mix": loaded[r["run_id"]],
                                     "points": defaultdict(list)})
        c["points"][(r["kind"], r["zone"], float(r["t_s"]))].append(int(float(r["n_remaining"])))
    out = list(configs.values())
    for i, c in enumerate(out, 1):
        c["id"] = f"clear {i}"
        c["duration_s"] = max(t for _, _, t in c["points"]) + 2.0
        c["label"] = f"{c['id']}: {c['design']}, {stroke_label(c['stroke'])}, mix {c['mix']}"
    return out


def stroke_label(s):
    return s["profile"] + "".join(f" {k}={v:g}" for k, v in s.items() if k in STROKE_KEYS) + \
        (f" {Path(s['csv']).name}" if "csv" in s else "")


def check_zones(designs_and_zones):
    """Stop early if a bench zone name is not a zone the sim uses for that design."""
    try:
        import designs
    except Exception as e:
        print(f"note: cannot import designs ({e}); zone names are checked after the first runs")
        return
    for design, zones in designs_and_zones.items():
        try:
            names = [z["name"] for z in designs.build(design).zones] + list(sweep.SPECIAL_ZONES)
        except Exception as e:
            raise SystemExit(f"design {design!r} does not build: {e}")
        bad = sorted(set(zones) - set(names))
        if bad:
            raise SystemExit(f"zones {bad} are not zones of {design}; use {names}")


def zones_for(design):
    import designs
    return [z["name"] for z in designs.build(design).zones] + list(sweep.SPECIAL_ZONES)


# ---------------------------------------------------------------- scoring

def zone_stats(counts_list, kind, zones):
    """Mean and sd over repeats of a kind's count and fraction in each zone. counts_list: [{kind: {zone: n}}]."""
    c = np.array([[cl.get(kind, {}).get(z, 0) for z in zones] for cl in counts_list], float)
    tot = c.sum(axis=1, keepdims=True)
    f = np.divide(c, tot, out=np.zeros_like(c), where=tot > 0)
    sd = lambda a: a.std(axis=0, ddof=1) if len(a) > 1 else np.zeros(a.shape[1])
    return {"count": c.mean(0), "count_sd": sd(c), "frac": f.mean(0), "frac_sd": sd(f)}


def compare_config(cfg, sims):
    """Observed vs simulated zone stats per kind for one configuration: [(kind, zones, obs, sim)]."""
    zones = sims[0]["zones"]
    bad = sorted({z for run in cfg["runs"] for c in run.values() for z in c} - set(zones))
    if bad:
        raise SystemExit(f"{cfg['label']}: bench zones {bad} are not sim zones {zones}")
    return [(k, zones, zone_stats(cfg["runs"], k, zones), zone_stats([s["counts"] for s in sims], k, zones))
            for k in cfg["mix"]]


def score(cfgs, sims_by_cfg):
    """RMS fraction error over all kinds, zones and configs; per-seed RMS spread; noise levels."""
    diffs, per_seed, obs_sd, sim_sd = [], defaultdict(list), [], []
    for c in cfgs:
        sims = sims_by_cfg[c["id"]]
        for kind, zones, o, s in compare_config(c, sims):
            diffs += list(s["frac"] - o["frac"])
            obs_sd += list(o["frac_sd"]) if len(c["runs"]) > 1 else []
            sim_sd += list(s["frac_sd"]) if len(sims) > 1 else []
            for r in sims:
                per_seed[r["sweep"]["seed"]] += list(zone_stats([r["counts"]], kind, zones)["frac"] - o["frac"])
    rms = lambda a: float(np.sqrt(np.mean(np.square(a)))) if len(a) else None
    seed_rms = [rms(v) for v in per_seed.values()]
    return {"rmse": rms(diffs), "rmse_seed_sd": float(np.std(seed_rms, ddof=1)) if len(seed_rms) > 1 else None,
            "bench_noise": rms(obs_sd), "sim_noise": rms(sim_sd)}


def contact(mu, dr):
    return {"friction": mu, "timeconst": TIMECONST, "dampratio": dr}


def grid_label(mu, dr):
    return f"mu {mu:.2f}, dampratio {dr:g}"


def sim_jobs(base, cfgs, points, seeds, block, max_duration):
    jobs = []
    for label, cont in points:
        for c in cfgs:
            for seed in range(seeds):
                dur = min(c["duration_s"], max_duration)
                cfg = sweep.make_cfg(base, design=c["design"], mix=c["mix"], stroke=c["stroke"], duration_s=dur,
                                     seed=seed, contact=cont)
                jobs.append({"cfg": cfg, "tags": {"preset": "calibrate", "block": block, "group": label,
                                                  "variant": c["id"], "seed": seed, "index": len(jobs)}})
    return jobs


def by_point_and_config(results):
    out = defaultdict(lambda: defaultdict(list))
    failed = []
    for r in results:
        if "error" in r:
            failed.append(r)
        else:
            out[r["sweep"]["group"]][r["sweep"]["variant"]].append(r)
    return out, failed


def count_at(res, kind, zone, t_s):
    ts = res["timeseries"]
    t = np.asarray(ts["t"]) - res["config"]["settle_s"]
    return ts["counts"][kind][zone][int(np.argmin(np.abs(t - t_s)))]


def clear_time(res, kind, zone):
    """Seconds after the shake starts until no particle of the kind is left in the zone (None if never)."""
    ts = res["timeseries"]
    t = np.asarray(ts["t"]) - res["config"]["settle_s"]
    c = np.asarray(ts["counts"][kind][zone])
    hit = np.flatnonzero((t >= 0) & (c == 0))
    return float(t[hit[0]]) if len(hit) else None


def mean_sd(vals):
    a = np.array([v for v in vals if v is not None], float)
    return (float(a.mean()) if len(a) else None, float(a.std(ddof=1)) if len(a) > 1 else 0.0, len(a))


# ---------------------------------------------------------------- report

def counts_rows(cfg, sims):
    """Table rows and dot-plot rows of observed vs predicted counts for one configuration."""
    trs, plot = [], []
    for kind, zones, o, s in compare_config(cfg, sims):
        for i, z in enumerate(zones):
            if o["count"][i] == 0 and s["count"][i] == 0:
                continue
            diff = s["count"][i] - o["count"][i]
            within = abs(diff) <= 2 * math.hypot(o["count_sd"][i], s["count_sd"][i]) + 0.5
            trs.append(f"<tr><td>{esc(kind)}</td><td class='l'>{esc(z)}</td>"
                       f"<td>{o['count'][i]:.1f} <span class='pm'>&#177; {o['count_sd'][i]:.1f}</span></td>"
                       f"<td>{s['count'][i]:.1f} <span class='pm'>&#177; {s['count_sd'][i]:.1f}</span></td>"
                       f"<td>{diff:+.1f}</td><td class='l'>{'&#10003; within 2 sd' if within else '&#10007; outside'}"
                       f"</td></tr>")
            plot += [{"head": f"{kind} in {z}"},
                     {"group": "observed (bench)", "cls": 0, "mean": o["count"][i], "sd": o["count_sd"][i],
                      "strong": True, "tip": f"observed {o['count'][i]:.1f} +/- {o['count_sd'][i]:.1f}"},
                     {"group": "predicted (sim)", "cls": 1, "mean": s["count"][i], "sd": s["count_sd"][i],
                      "strong": True, "tip": f"predicted {s['count'][i]:.1f} +/- {s['count_sd'][i]:.1f}"}]
    table = ("<table><tr><th>Kind</th><th>Zone</th><th>Observed mean &#177; sd</th><th>Predicted mean &#177; sd</th>"
             f"<th>Predicted minus observed</th><th>Agreement</th></tr>{''.join(trs)}</table>")
    return table, plot


def report_html(cal, fit_cfgs, hold_cfgs, clear_cfgs, best_sims, hold_sims, clear_sims, grid, failed):
    status_cls = "ok" if cal["validated"] else "bad"
    glyph = "&#10003;" if cal["validated"] else "&#10007;"
    out = [f"<h1>Calibration{' (quick smoke test)' if cal['quick'] else ''}</h1>",
           f'<p class="lede">{esc(cal["bench_csv"])}, generated {esc(cal["created"])} by calibrate.py. '
           f'{len(fit_cfgs)} fit configuration(s), {len(hold_cfgs)} holdout, {len(clear_cfgs)} timed '
           f'clear-out check(s).</p>',
           f'<p class="banner"><span class="{status_cls}">{glyph} {esc(cal["status"])}</span></p>',
           "<ul>" + "".join(f"<li>{esc(c['label'])} ({c['split']})</li>" for c in fit_cfgs + hold_cfgs) + "</ul>",
           "<h2>Fit</h2>",
           f"<p>Best: <b>{esc(grid_label(cal['best']['friction'], cal['best']['dampratio']))}</b> "
           f"(timeconst {TIMECONST} s), RMS zone-fraction error {fmt(cal['best_rmse'], '{:.3f}')}. "
           f"Plausible friction {cal['uncertainty']['friction'][0]:.2f} to {cal['uncertainty']['friction'][1]:.2f}: "
           f"grid points within {fmt(cal['margin'], '{:.3f}')} of the best score (the larger of bench repeat noise "
           f"{fmt(cal['bench_noise'], '{:.3f}')} and sim seed noise {fmt(cal['sim_noise'], '{:.3f}')}).</p>",
           "<p>Parameter sets written for sweep.py compare: " +
           "; ".join(f"<b>{esc(p['label'])}</b> {esc(p['contact'])}" for p in cal["param_sets"]) + "</p>"]
    rows = []
    for dr in sorted({g["dampratio"] for g in grid}, reverse=True):
        rows.append({"head": f"dampratio {dr:g}" + (" (no rebound)" if dr >= 1 else " (bouncier)")})
        for g in (g for g in grid if g["dampratio"] == dr):
            pen = g["max_penetration_mm"]
            flag = pen is not None and pen >= sweep.CLEARANCE_MM
            rows.append({"group": f"mu {g['friction']:.2f}" + ("  overlap FAIL" if flag else ""),
                         "cls": 1 if g["best"] else 0, "mean": g["rmse"], "sd": g["rmse_seed_sd"], "strong": True,
                         "note": "  best" if g["best"] else "",
                         "tip": f"{grid_label(g['friction'], dr)}: RMS error {fmt(g['rmse'], '{:.3f}')}, "
                                f"max tray overlap {fmt(pen, '{:.3f}')} mm"})
    out.append("<figure><figcaption>Fit error per grid point: RMS difference in zone fractions, mean over seeds "
               "&#177; seed spread (orange = best)</figcaption>" +
               sweep.dot_plot(rows, "RMS zone-fraction error", f="{:.3f}") + "</figure>")
    for c in fit_cfgs:
        table, _ = counts_rows(c, best_sims[c["id"]])
        out += [f"<h3>At the best point: {esc(c['label'])}</h3>", table]
    out.append("<h2>Holdout prediction</h2>")
    if not hold_cfgs:
        out.append('<p class="bad">&#10007; No holdout rows. The fit above is not validated: it only shows the sim '
                   'can be tuned to match the runs it was tuned on.</p>')
    for c in hold_cfgs:
        if not hold_sims.get(c["id"]):
            out.append(f'<p class="bad">&#10007; {esc(c["label"])}: every holdout simulation failed.</p>')
            continue
        table, plot = counts_rows(c, hold_sims[c["id"]])
        out += [f"<h3>{esc(c['label'])}</h3>",
                f"<p>Predicted with the best fit point, {len(hold_sims[c['id']])} seeds; observed over "
                f"{len(c['runs'])} bench repeats. RMS zone-fraction error {fmt(cal['holdout']['rmse'], '{:.3f}')}.</p>",
                sweep.legend(["observed (bench)", "predicted (sim)"]),
                "<figure><figcaption>Predicted vs observed count per kind and zone, mean &#177; sd</figcaption>" +
                sweep.dot_plot(plot, "particles", f="{:.1f}") + "</figure>", table]
    if clear_cfgs:
        out.append("<h2>Throughput check: still on the screen at the bench checkpoints</h2>")
        for c in clear_cfgs:
            trs, plot = [], []
            for (kind, zone, t_s), obs in c["points"].items():
                sims = clear_sims.get(c["id"], [])
                pm, psd, _ = mean_sd([count_at(r, kind, zone, t_s) for r in sims])
                om, osd, _ = mean_sd(obs)
                ct = mean_sd([clear_time(r, kind, zone) for r in sims]) if om == 0 else None
                ct_txt = "" if ct is None else (f"sim clears at {fmt(ct[0], '{:.1f}')} &#177; {fmt(ct[1], '{:.1f}')} s "
                                                f"({ct[2]}/{len(sims)} runs)")
                trs.append(f"<tr><td>{esc(kind)}</td><td class='l'>{esc(zone)}</td><td>{t_s:g}</td>"
                           f"<td>{om:.1f} <span class='pm'>&#177; {osd:.1f}</span></td>"
                           f"<td>{fmt(pm, '{:.1f}')} <span class='pm'>&#177; {psd:.1f}</span></td>"
                           f"<td class='l'>{ct_txt}</td></tr>")
                plot += [{"head": f"{kind} on {zone} at {t_s:g} s"},
                         {"group": "observed (bench)", "cls": 0, "mean": om, "sd": osd, "strong": True},
                         {"group": "predicted (sim)", "cls": 1, "mean": pm, "sd": psd, "strong": True}]
            out += [f"<h3>{esc(c['label'])}</h3>", sweep.legend(["observed (bench)", "predicted (sim)"]),
                    "<figure><figcaption>Particles of each kind still in the zone at each checkpoint</figcaption>" +
                    sweep.dot_plot(plot, "particles still in the zone", f="{:.1f}") + "</figure>",
                    "<table><tr><th>Kind</th><th>Zone</th><th>t, s</th><th>Observed still there</th>"
                    f"<th>Predicted still there</th><th>Clear time</th></tr>{''.join(trs)}</table>"]
    if failed:
        out.append(f"<h2>Failed runs ({len(failed)})</h2>" + "".join(
            f"<pre>{esc(r['sweep']['group'])} | {esc(r['sweep']['variant'])} | seed {r['sweep']['seed']}\n"
            f"{esc(chr(10).join(r['error'].strip().splitlines()[-4:]))}</pre>" for r in failed))
    return sweep.html_page("Calibration", "".join(out))


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bench_csv", nargs="?", type=Path)
    ap.add_argument("--clear", type=Path, help="clear_times.csv: timed checkpoints for the throughput check")
    ap.add_argument("--quick", action="store_true", help="tiny grid, 2 s runs; writes to out/calibration/quick")
    ap.add_argument("--zones", metavar="DESIGN", help="print the sim zone names for a design and exit")
    args = ap.parse_args()
    if args.zones:
        print(", ".join(zones_for(args.zones)))
        return
    if not args.bench_csv:
        ap.error("give a bench_counts.csv, or --zones DESIGN")

    q = QUICK if args.quick else {"frictions": FRICTIONS, "dampratios": DAMPRATIOS, "seeds": SEEDS,
                                  "holdout_seeds": HOLDOUT_SEEDS, "max_duration_s": math.inf}
    out_dir = OUT / "quick" if args.quick else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    cfgs = read_bench(args.bench_csv)
    fit_cfgs = [c for c in cfgs if c["split"] == "fit"]
    hold_cfgs = [c for c in cfgs if c["split"] == "holdout"]
    clear_cfgs = read_clear(args.clear) if args.clear else []
    if not fit_cfgs:
        raise SystemExit("no fit rows: mark the runs to tune on with split=fit")
    zones_used = defaultdict(set)
    for c in cfgs:
        for run in c["runs"]:
            zones_used[c["design"]].update(z for k in run.values() for z in k)
    for c in clear_cfgs:
        zones_used[c["design"]].update(z for _, z, _ in c["points"])
    check_zones(zones_used)
    for c in cfgs:
        print(c["label"], "mix", c["mix"])

    import sorter
    base = dataclasses.asdict(sorter.RunConfig())
    points = [(grid_label(mu, dr), contact(mu, dr)) for dr in q["dampratios"] for mu in q["frictions"]]
    fit_res = sweep.run_jobs(sim_jobs(base, fit_cfgs, points, q["seeds"], "fit", q["max_duration_s"]),
                             out_dir / "fit_runs.jsonl")
    fit_by, failed = by_point_and_config(fit_res)
    grid = []
    for (label, cont) in points:
        sims = fit_by.get(label, {})
        if any(len(sims.get(c["id"], [])) == 0 for c in fit_cfgs):
            continue
        sc = score(fit_cfgs, sims)
        pens = [r.get("max_penetration_mm") for v in sims.values() for r in v]
        grid.append({"label": label, "friction": cont["friction"], "dampratio": cont["dampratio"], **sc,
                     "max_penetration_mm": max((p for p in pens if p is not None), default=None), "best": False})
    if not grid:
        raise SystemExit("every fit run failed; see fit_runs.jsonl")
    ok_pen = [g for g in grid if g["max_penetration_mm"] is None or g["max_penetration_mm"] < sweep.CLEARANCE_MM]
    best = min(ok_pen or grid, key=lambda g: g["rmse"])
    best["best"] = True
    margin = max(best["bench_noise"] or 0.0, best["sim_noise"] or 0.0)
    plaus = [g["friction"] for g in grid if g["dampratio"] == best["dampratio"] and g["rmse"] <= best["rmse"] + margin]
    fr = sorted(q["frictions"])
    k = fr.index(best["friction"])
    lo, hi = min(plaus + [fr[max(k - 1, 0)]]), max(plaus + [fr[min(k + 1, len(fr) - 1)]])
    sets = [(f"mu {lo:.2f} (low)", lo), (f"mu {best['friction']:.2f} (best)", best["friction"]),
            (f"mu {hi:.2f} (high)", hi)]
    param_sets = [{"label": lab, "contact": contact(mu, best["dampratio"])}
                  for i, (lab, mu) in enumerate(sets) if mu not in [s[1] for s in sets[:i]]]

    best_point = [(best["label"], contact(best["friction"], best["dampratio"]))]
    hold_by, clear_by = {}, {}
    if hold_cfgs:
        hold_res = sweep.run_jobs(sim_jobs(base, hold_cfgs, best_point, q["holdout_seeds"], "holdout",
                                           q["max_duration_s"]), out_dir / "holdout_runs.jsonl")
        by, f2 = by_point_and_config(hold_res)
        hold_by, failed = by[best["label"]], failed + f2
    if clear_cfgs:
        clear_res = sweep.run_jobs(sim_jobs(base, clear_cfgs, best_point, q["holdout_seeds"], "clear",
                                            q["max_duration_s"]), out_dir / "clear_runs.jsonl")
        by, f3 = by_point_and_config(clear_res)
        clear_by, failed = by[best["label"]], failed + f3

    fit_settings = {c["settings"] for c in fit_cfgs}
    repeats_fit = [c["id"] for c in hold_cfgs if c["settings"] in fit_settings]
    hold_ok = [c for c in hold_cfgs if hold_by.get(c["id"])]
    hold_score = score(hold_ok, hold_by) if hold_ok else {"rmse": None}
    if args.quick:
        validated, status = False, "Quick smoke test: tiny grid and 2 s runs, not a calibration. Not validated."
    elif not hold_cfgs:
        validated, status = False, "Fit only: NOT validated. There are no holdout rows to predict."
    elif repeats_fit:
        validated, status = False, (f"NOT validated: holdout {', '.join(repeats_fit)} uses the same settings as a "
                                    f"fit configuration, so it is a repeat, not a held-out prediction.")
    elif len(hold_ok) < len(hold_cfgs):
        validated, status = False, "NOT validated: some holdout simulations failed."
    elif hold_score["rmse"] <= HOLDOUT_TOL:
        validated, status = True, (f"Validated on the holdout: RMS zone-fraction error {hold_score['rmse']:.3f} "
                                   f"<= {HOLDOUT_TOL} on settings the fit never saw.")
    else:
        validated, status = False, (f"NOT validated: holdout RMS zone-fraction error {hold_score['rmse']:.3f} "
                                    f"> {HOLDOUT_TOL}. The fit does not carry over to the held-out settings.")

    cal = {"created": f"{datetime.now():%Y-%m-%d %H:%M}", "bench_csv": str(args.bench_csv.resolve()),
           "quick": args.quick, "validated": validated, "status": status,
           "best": contact(best["friction"], best["dampratio"]), "best_rmse": best["rmse"],
           "uncertainty": {"friction": [lo, hi]}, "margin": margin, "bench_noise": best["bench_noise"],
           "sim_noise": best["sim_noise"], "param_sets": param_sets,
           "grid": [{k: g[k] for k in ("friction", "dampratio", "rmse", "rmse_seed_sd", "max_penetration_mm")}
                    for g in grid],
           "fit_configs": [c["label"] for c in fit_cfgs], "holdout_configs": [c["label"] for c in hold_cfgs],
           "holdout": {"rmse": hold_score["rmse"], "tolerance": HOLDOUT_TOL, "seeds": q["holdout_seeds"]},
           "seeds": q["seeds"], "timeconst": TIMECONST}
    (out_dir / "calibration.json").write_text(json.dumps(cal, indent=1), encoding="utf-8")
    html_text = report_html(cal, fit_cfgs, hold_cfgs, clear_cfgs, fit_by[best["label"]], hold_by, clear_by, grid,
                            failed)
    (out_dir / "calibration.html").write_text(html_text, encoding="utf-8")
    print(status)
    print(f"wrote {out_dir / 'calibration.json'}\nwrote {out_dir / 'calibration.html'}")


if __name__ == "__main__":
    main()
