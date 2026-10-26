"""Second opinion on the optimizer's winners (physics session). Reruns the top designs from opt/winners.json and the
demo rig with fresh seeds, every friction set, the study's load and a heavy load, at the contacts a short probe
measures for each design (and one setting stiffer), then says whether the ranking holds. Writes opt/VERIFY.md; raw runs
go to out/verify/ (gitignored).

It uses optimize.py's own run (optimize.run_job, with its instability check) and score (imported, not edited), so a
difference from the leaderboard comes from the seeds, the load or the contacts, not from the scoring. One thing is
added: the overlap per tray role, read every step after the settle. optimize.py reads the gate overlap every 10th
step, which misses part of an impact's peak (VERTICAL.md, Contact rule), so a second flag uses the every-step gate
and screen overlap. The floor overlap is reported but not flagged: in the gated tower it is mostly the landing after
the drop to the next level, which can't push a grain through an opening.

Run from sim\\ (WSL venv on this laptop), at most 8 workers while optimize.py is running:
    python verify.py --study demo [--top 3] [--seeds 6] [--heavy 2] [--workers 8] [--variants normal,heavy,stiff]
    python verify.py --study demo --report           rewrite opt/VERIFY.md from the cached runs, running nothing
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np

import contact_rule
import optimize
import sweep

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "verify"
SEED0 = 100                      # fresh seeds: the optimizer ran 0, 1, 2
PROBE_SEEDS, PROBE_S = (90, 91, 92), 2.0     # the per-design contact probe: runs at each setting, shake seconds
# The demo rig: separate printed trays stacked one above the other, 5 mm over 2 mm over the catch pan
# (docs/sessions/demo-rig.md), nominal hole size as in VERTICAL.md; the firmware stroke, and shaken up and down
DEMO_RIG = [
    {"id": "demo-rig", "label": "demo rig: inserts:5mm,2mm, firmware cap stroke", "spec": "inserts:5mm,2mm",
     "inject": {}, "stroke": dict(optimize.FIRMWARE)},
    {"id": "demo-rig-up", "label": "demo rig: inserts:5mm,2mm, up and down (2 g sine at 20 Hz, VERTICAL.md)",
     "spec": "inserts:5mm,2mm", "inject": {},
     "stroke": {"profile": "sine", "amp_mm": 1.242, "freq_hz": 20, "angle_deg": 90}},
]


def candidates(study, top):
    path = optimize.OPT / ("winners.json" if study == "demo" else f"winners_{study}.json")
    w = json.loads(path.read_text(encoding="utf-8"))
    out = [{"id": x["id"], "label": f"#{x['rank']} {x['id']} ({x['family']})", "spec": x["sim_spec"],
            "inject": x.get("sim_inject") or {}, "stroke": x["stroke"], "opt": x} for x in w["winners"][:top]]
    return out + (DEMO_RIG if study == "demo" else []), w


def key_of(cfg, inject):
    return hashlib.sha1(json.dumps([cfg, inject], sort_keys=True, default=sweep.jsonable).encode()).hexdigest()[:20]


def run_job(job):
    """Child process: optimize.run_job, plus the worst overlap per tray role, read every step after the settle."""
    import mujoco
    import designs
    inner, seen = mujoco.mj_step, {}

    def tracked(m, d):
        inner(m, d)
        if "role" not in seen:   # first step: run_job has applied the inject, so this is the design it built
            roles = [g["role"] for g in designs.build(job["cfg"]["design"]).geoms]
            seen["names"], seen["role"] = sorted(set(roles)), np.full(m.ngeom, -1)
            for i, r in enumerate(roles):
                seen["role"][m.geom(f"tray{i}").id] = seen["names"].index(r)
            seen["pen"] = np.zeros(len(seen["names"]))
        if d.time >= job["cfg"]["settle_s"] and d.ncon:
            r = seen["role"][d.contact.geom[:d.ncon]].max(axis=1)
            np.maximum.at(seen["pen"], r[r >= 0], -d.contact.dist[:d.ncon][r >= 0])

    mujoco.mj_step = tracked
    rec = optimize.run_job(job)
    if "pen" in seen:
        rec["pen_role_mm"] = {r: round(float(v), 5) for r, v in zip(seen["names"], seen["pen"])}
    return rec


def run_in_child(job, job_dir):
    """optimize.run_in_child, with this file's run_job."""
    path = job_dir / f"{job['key']}.json"
    path.write_text(json.dumps(job, default=sweep.jsonable), encoding="utf-8")
    out = path.with_suffix(".out.json")
    out.unlink(missing_ok=True)
    p = subprocess.run([sys.executable, "-W", "ignore", str(Path(__file__).resolve()), "--job", str(path)],
                       cwd=HERE, capture_output=True, text=True)
    if p.returncode or not out.exists():
        return {"key": job["key"], "tags": job["tags"], "config": job["cfg"],
                "error": (p.stderr or "no result written")[-3000:]}
    rec = json.loads(out.read_text(encoding="utf-8"))
    out.unlink(missing_ok=True)
    path.unlink(missing_ok=True)
    return rec


def run_all(jobs, study, workers, cached_only=False):
    """A child process per run (optimize.py's run plus the every-step overlap), cached under out/verify/.
    cached_only: run nothing, return the cached runs only."""
    cache, job_dir = OUT / study / "runs", OUT / study / "jobs"
    cache.mkdir(parents=True, exist_ok=True)
    job_dir.mkdir(parents=True, exist_ok=True)
    if cached_only:
        return {j["key"]: json.loads((cache / f"{j['key']}.json").read_text(encoding="utf-8")) for j in jobs
                if (cache / f"{j['key']}.json").exists()}
    todo = [j for j in {j["key"]: j for j in jobs}.values() if not (cache / f"{j['key']}.json").exists()]
    if todo:
        t0 = time.time()
        print(f"{len(todo)} runs on {min(workers, len(todo))} workers ({len(jobs) - len(todo)} cached)", flush=True)
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(todo)))) as ex:
            futs = {ex.submit(run_in_child, j, job_dir): j for j in todo}
            for i, fut in enumerate(as_completed(futs), 1):
                j = futs[fut]
                try:
                    rec = fut.result()
                except Exception:
                    rec = {"key": j["key"], "tags": j["tags"], "config": j["cfg"], "error": traceback.format_exc()}
                (cache / f"{j['key']}.json").write_text(json.dumps(rec, default=sweep.jsonable), encoding="utf-8")
                if i % 8 == 0 or i == len(todo):
                    el = time.time() - t0
                    print(f"  [{i}/{len(todo)}] {el / 60:.1f} min, eta {el / i * (len(todo) - i) / 60:.1f} min",
                          flush=True)
    return {j["key"]: json.loads((cache / f"{j['key']}.json").read_text(encoding="utf-8")) for j in jobs}


def gate_pen(rec):
    roles = rec.get("pen_role_mm", {})
    return max([roles.get(r, 0.0) for r in ("gate", "screen")])


def contacts_all(cands, study, base, seeds, workers, cached_only=False):
    """{candidate id: contacts}, measured on each design itself, all in one batch: its tightest clearance (over
    0.1 s runs at every seed; it depends on the sampled grain sizes), then PROBE_SEEDS short runs at each of
    contact_rule.SETTINGS; the cheapest setting whose median every-step gate and screen overlap is at most
    PEN_FLAG x the clearance. contact_rule.pick's choice is kept beside it, as a check on the rule.
    cached_only: run nothing; every probe must be cached already."""
    order = sorted(contact_rule.SETTINGS, key=contact_rule.SETTINGS.get)
    clr_jobs, probe_jobs = {}, {}
    for c in cands:
        for seed in seeds:
            cfg = sweep.make_cfg(base, design=c["spec"], stroke=c["stroke"], duration_s=0.05, settle_s=0.05, seed=seed)
            clr_jobs.setdefault(c["id"], []).append({"cfg": cfg, "inject": c["inject"], "key": key_of(cfg, c["inject"]),
                                                     "tags": {"cand": c["id"], "fid": "clearance"}})
        for dt, tc in order:
            for seed in PROBE_SEEDS:
                cfg = sweep.make_cfg(base, design=c["spec"], stroke=c["stroke"], dt=dt, contact={"timeconst": tc},
                                     duration_s=PROBE_S, seed=seed)
                probe_jobs.setdefault((c["id"], (dt, tc)), []).append(
                    {"cfg": cfg, "inject": c["inject"], "key": key_of(cfg, c["inject"]),
                     "tags": {"cand": c["id"], "fid": "probe"}})
    jobs = [j for js in [*clr_jobs.values(), *probe_jobs.values()] for j in js]
    recs = run_all(jobs, study, workers, cached_only)
    missing = sum(j["key"] not in recs for j in jobs)
    if missing:
        raise SystemExit(f"{missing} of {len(jobs)} contact probes aren't cached yet; run without --report")
    out = {}
    for c in cands:
        clrs = []
        for j in clr_jobs[c["id"]]:
            rec = recs[j["key"]]
            if rec.get("error") or rec.get("unstable"):
                raise RuntimeError(f"{c['id']}: clearance probe failed: {(rec.get('error') or rec['unstable'])[-300:]}")
            clrs.append(optimize.clearance(rec))
        clr = min((x for x in clrs if x is not None), default=None)
        probe = {}
        for s in order:
            ok = [recs[j["key"]] for j in probe_jobs[(c["id"], s)]]
            ok = [r for r in ok if not r.get("error") and not r.get("unstable")]
            probe[s] = float(np.median([gate_pen(r) for r in ok])) if ok else None
        k = {"clearance": clr, "probe": probe, "rule": contact_rule.pick(clr, c["stroke"])}
        limit = optimize.PEN_FLAG * clr if clr is not None else None
        fit = [s for s in order if clr is not None and probe[s] is not None and probe[s] <= limit]
        if clr is None:
            k.update(dt=order[0][0], tc=order[0][1], why="no gate near size: production contacts")
        elif fit:
            k.update(dt=fit[0][0], tc=fit[0][1], why=f"median gate overlap {probe[fit[0]]:.3f} mm <= {limit:.3f} mm")
        else:
            k.update(dt=order[-1][0], tc=order[-1][1], why=f"no setting keeps the median gate overlap under "
                     f"{limit:.3f} mm: stiffest, and the results near this gate are untrustworthy")
        out[c["id"]] = k
    return out


def jobs_for(c, study, base, load, mix, seeds, sets, dt, tc, dur):
    out = []
    for label, contact in sets:
        for seed in seeds:
            cfg = sweep.make_cfg(base, design=c["spec"], stroke=c["stroke"], mix=mix, dt=dt,
                                 contact={**contact, "timeconst": tc}, duration_s=dur, seed=seed)
            out.append({"cfg": cfg, "inject": c["inject"], "key": key_of(cfg, c["inject"]),
                        "tags": {"cand": c["id"], "fid": f"verify-{load}", "set": label, "seed": seed}})
    return out


def score(rec, study):
    s = optimize.run_score(rec, study)
    if "fail" not in s:
        roles = rec.get("pen_role_mm", {})
        s["pen_step"] = max([roles.get(r, 0.0) for r in ("gate", "screen")])
        s["pen_floor"] = roles.get("floor", 0.0)
        s["flag_step"] = bool(s["clearance"] is not None and s["pen_step"] >= optimize.PEN_FLAG * s["clearance"])
    return s


def summarize(recs, jobs, study):
    """The runs' scores and counts; over the cached runs only (n of planned), None if there are none yet."""
    planned, jobs = len(jobs), [j for j in jobs if j["key"] in recs]
    if not jobs:
        return None
    rs = [(j, score(recs[j["key"]], study)) for j in jobs]
    v = np.array([x["score"] for _, x in rs])
    ok = [x for _, x in rs if "fail" not in x]
    nc = len(optimize.STUDIES[study]["classes"])
    by_set = {}
    for j, x in rs:
        by_set.setdefault(j["tags"]["set"], []).append(x["score"])
    avg = lambda xs: float(np.mean(xs)) if xs else None
    sd = float(v.std(ddof=1)) if len(v) > 1 else 0.0
    return {"n": len(rs), "planned": planned, "mean": float(v.mean()), "sd": sd, "robust": float(v.mean() - sd),
            "se": sd / np.sqrt(len(v)), "worst_set": float(min(np.mean(s) for s in by_set.values())),
            "by_set": {k: float(np.mean(s)) for k, s in by_set.items()},
            "fails": [x["fail"] for _, x in rs if "fail" in x],
            "flag_gate": sum(x["flag"] for x in ok), "flag_step": sum(x["flag_step"] for x in ok),
            "recovery": [avg([x["recovery"][i] for x in ok if x["recovery"][i] is not None]) for i in range(nc)],
            "purity": [avg([x["purity"][i] for x in ok if x["purity"][i] is not None]) for i in range(nc)],
            "between": avg([x["between"] for x in ok]), "lost": avg([x["lost"] for x in ok]),
            "t90": avg([x["t90"] for x in ok if x["t90"] is not None]),
            "t90_reached": sum(x["t90"] is not None for x in ok), "n_ok": len(ok),
            "clearance": min((x["clearance"] for x in ok if x["clearance"] is not None), default=None),
            "pen_gate": max((x["pen"] for x in ok), default=None),
            "pen_step": max((x["pen_step"] for x in ok), default=None),
            "pen_floor": max((x["pen_floor"] for x in ok), default=None),
            "matrix": np.sum([x["matrix"] for x in ok], axis=0).tolist() if ok else None,
            "cols": ok[0]["cols"] if ok else None,
            "wall_s": float(np.mean([recs[j["key"]].get("wall_total_s", 0) for j in jobs]))}


def f2(v, f="{:.2f}"):
    return "–" if v is None else f.format(v)


def ranking_verdict(cands, summ, load):
    """Does the optimizer's order hold, and are the gaps bigger than the noise? Over the winners with runs."""
    wins = [c for c in cands if "opt" in c and summ[c["id"]][load]]
    order = sorted(wins, key=lambda c: -summ[c["id"]][load]["robust"])
    same = [c["id"] for c in order] == [c["id"] for c in wins]
    gaps = []
    for a, b in zip(wins, wins[1:]):
        sa, sb = summ[a["id"]][load], summ[b["id"]][load]
        d, noise = sa["mean"] - sb["mean"], 2 * np.hypot(sa["se"], sb["se"])
        gaps.append(f"#{a['opt']['rank']} - #{b['opt']['rank']}: mean {d:+.3f} (2 se {noise:.3f}, "
                    f"{'clear' if abs(d) > noise else 'within noise'})")
    return same, [c["opt"]["rank"] for c in order], gaps


VARIANTS = ("normal", "heavy", "stiff")


def variants(study, heavy, only=VARIANTS):
    """{name: (title, mix, contacts)} for the names in only: contacts 0 = the probe's pick, 1 = one setting stiffer."""
    mix = optimize.STUDIES[study]["mix"]
    var = {"normal": ("Study load", mix, 0),
           "heavy": (f"Heavy load ({heavy}x)", {k: v * heavy for k, v in mix.items()}, 0),
           "stiff": ("Study load, contacts one setting stiffer", mix, 1)}
    return {k: v for k, v in var.items() if k in only}


def stiffer(dt, tc):
    """The next setting in contact_rule.SETTINGS after (dt, tc), or the same one if it is the stiffest."""
    order = sorted(contact_rule.SETTINGS, key=contact_rule.SETTINGS.get)
    return order[min(order.index((dt, tc)) + 1, len(order) - 1)]


def write_md(study, cands, w, summ, contacts, args):
    cl = [x["name"] for x in optimize.STUDIES[study]["classes"]]
    sets, source = sweep.param_sets()
    seeds = list(range(SEED0, SEED0 + args.seeds))
    var = variants(study, args.heavy, args.variants)
    path = optimize.OPT / ("VERIFY.md" if study == "demo" else f"VERIFY_{study}.md")
    # a hand-written reading between these markers survives a rewrite
    keep = re.search(r"<!-- summary -->.*?<!-- /summary -->", path.read_text(encoding="utf-8"), re.S) \
        if path.exists() else None
    L = [f"# Verification of the optimizer's winners ({study})", "",
         f"Physics session, {datetime.now():%Y-%m-%d %H:%M}, `sim/verify.py`. The second opinion the brief's honesty "
         "rules ask for: the optimizer's runs are the screening, this reruns its top designs independently.", "",
         f"- **Winners checked:** `opt/{'winners.json' if study == 'demo' else f'winners_{study}.json'}` generated "
         f"{w.get('generated', '?')}, top {len([c for c in cands if 'opt' in c])}, plus the demo rig "
         "(`inserts:5mm,2mm`, the stacked trays the team built) with the firmware stroke and shaken up and down.",
         f"- **Runs:** fresh seeds {seeds[0]}-{seeds[-1]} (the optimizer used 0-2) x {len(sets)} friction sets "
         f"({source}) = {len(seeds) * len(sets)} runs per design and variant, {args.duration:g} s of shaking each, "
         "scored with `optimize.run_score` (robust = mean - 1 sd, as on the leaderboard).",
         "- **Variants:** the study's mix "
         f"({', '.join(f'{k} {v}' for k, v in optimize.STUDIES[study]['mix'].items())}); "
         f"a heavy load, {args.heavy}x every kind, in the same {args.duration:g} s; and the study's mix with contacts "
         "one setting stiffer, to see whether soft contacts are doing some of the sorting.",
         f"- **Contacts:** measured per design: {len(PROBE_SEEDS)} runs of {PROBE_S:g} s at each setting, on the "
         "design's own stroke; the cheapest setting whose median every-step gate and screen overlap stays under half "
         "the design's tightest clearance. `contact_rule.py`'s pick is listed beside it (VERTICAL.md, Contact rule). "
         "The optimizer ran everything at dt 0.25 ms / timeconst 0.5 ms.",
         "- **Flags** (a run whose overlap with gates and screens reaches 0.5 x the tightest clearance): *10th* reads "
         "the overlap every 10th step, as optimize.py does; *every* reads it every step, which catches an impact's "
         "peak.",
         "- The sim is uncalibrated: these scores rank designs, they don't predict bench percentages."]
    short = [(c["label"], v, s["n"] if s else 0, len(seeds) * len(sets)) for c in cands
             for v, s in summ[c["id"]].items() if not s or s["n"] < s["planned"]]
    if short:
        L.append("- **Incomplete:** the run stopped before these finished, so their rows cover fewer runs: "
                 + "; ".join(f"{lab}, {v}: {n} of {p}" for lab, v, n, p in short) + ".")
    L.append("")
    if keep:
        L += [keep.group(0), ""]
    for v, (title, _, _) in var.items():
        same, order, gaps = ranking_verdict(cands, summ, v)
        L += [f"## {title}", "",
              f"**Ranking {'holds' if same else 'changes'}:** verified order {' > '.join(f'#{r}' for r in order)}."
              + (" " + "; ".join(gaps) + "." if gaps else ""), "",
              "| Design | Optimizer robust | Robust (mean - sd) | Mean | Worst friction set | "
              + " | ".join(f"{c} purity / recovery" for c in cl)
              + " | Jams / lost per run | t90 s (reached) | Flagged runs, 10th / every step | Fails |",
              "|---|---|---|---|---|" + "---|" * len(cl) + "---|---|---|---|"]
        for c in cands:
            s = summ[c["id"]][v]
            opt = c.get("opt", {}).get("score", {}).get("robust")
            if not s:
                L.append(f"| {c['label']} | {f2(opt, '{:.3f}')} | not run yet |" + " |" * (len(cl) + 6))
                continue
            part = f" ({s['n']} of {s['planned']} runs)" if s["n"] < s["planned"] else ""
            L.append(f"| {c['label']}{part} | {f2(opt, '{:.3f}')} | **{s['robust']:.3f}** | {s['mean']:.3f} | "
                     f"{s['worst_set']:.3f} | "
                     + " | ".join(f"{f2(p)} / {f2(r)}" for p, r in zip(s["purity"], s["recovery"]))
                     + f" | {f2(s['between'])} / {f2(s['lost'])} | {f2(s['t90'], '{:.1f}')} ({s['t90_reached']}/"
                     f"{s['n_ok']}) | {s['flag_gate']} / {s['flag_step']} of {s['n_ok']} | {len(s['fails'])} |")
        L.append("")
    L += ["## Contacts and overlap per design", "",
          "Max overlap over all runs of a variant, mm. Gate = gates and screens, read every 10th step / every step.",
          "",
          "| Design | Tightest clearance mm | Probe: median gate overlap mm at "
          + " / ".join(f"{dt * 1e3:g}" for dt, _ in sorted(contact_rule.SETTINGS, key=contact_rule.SETTINGS.get))
          + " ms | Used: dt / timeconst ms (pick; stiffer) | Why | contact_rule.py would pick | "
          + " | ".join(f"{v}: gate 10th / every, floor" for v in var) + " | Wall s per run (" + ", ".join(var) + ") |",
          "|---|---|---|---|---|---|" + "---|" * len(var) + "---|"]
    for c in cands:
        k = contacts[c["id"]]
        sdt, stc = stiffer(k["dt"], k["tc"])
        rdt, rtc, _ = k["rule"]
        cells = [f"{f2(s['pen_gate'], '{:.3f}')} / {f2(s['pen_step'], '{:.3f}')}, {f2(s['pen_floor'], '{:.3f}')}"
                 if s else "–" for s in (summ[c["id"]][v] for v in var)]
        L.append(f"| {c['label']} | {f2(k['clearance'], '{:.3f}')} | "
                 + " / ".join(f2(k["probe"][x], "{:.3f}") for x in sorted(k["probe"], key=contact_rule.SETTINGS.get))
                 + f" | {k['dt'] * 1e3:g} / {k['tc'] * 1e3:g}; {sdt * 1e3:g} / {stc * 1e3:g} | {k['why']} | "
                 f"{rdt * 1e3:g} / {rtc * 1e3:g} | " + " | ".join(cells) + " | "
                 + ", ".join(f2(summ[c["id"]][v] and summ[c["id"]][v]["wall_s"], "{:.0f}") for v in var) + " |")
    L += ["", "## Count matrices (summed over all runs; rows = class, columns = final bin)", ""]
    for c in cands:
        for v, (title, _, _) in var.items():
            s = summ[c["id"]][v]
            if not s or not s["matrix"]:
                continue
            L += [f"**{c['label']}; {title.lower()}** ({s['n_ok']} runs)", "",
                  "| Class | " + " | ".join(s["cols"]) + " |", "|---|" + "---|" * len(s["cols"])]
            L += [f"| {name} | " + " | ".join(str(x) for x in row) + " |" for name, row in zip(cl, s["matrix"])]
            L.append("")
    fails = [(c["label"], v, f) for c in cands for v in var for f in (summ[c["id"]][v] or {}).get("fails", [])]
    if fails:
        L += ["## Failed runs", ""] + [f"- {lab}, {v}: {f}" for lab, v, f in fails] + [""]
    L += ["## Reproduce", "", "```", f"python verify.py --study {study} --top {args.top} --seeds {args.seeds} "
          f"--heavy {args.heavy} --workers {args.workers}"
          + (f" --duration {args.duration:g}" if args.duration != optimize.FULL_S else "")
          + (f" --variants {','.join(args.variants)}" if tuple(args.variants) != VARIANTS else ""), "```", ""]
    path.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--study", default="demo", choices=list(optimize.STUDIES))
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--heavy", type=int, default=2, help="heavy load = this many times the study's mix")
    ap.add_argument("--workers", type=int, default=8, help="8 at most while optimize.py is running")
    ap.add_argument("--duration", type=float, default=optimize.FULL_S, help="shake seconds (the optimizer's full run)")
    ap.add_argument("--variants", default=",".join(VARIANTS), help="comma-separated, of " + ", ".join(VARIANTS))
    ap.add_argument("--report", action="store_true",
                    help="run nothing: rewrite VERIFY.md from the cached runs, listing any that are missing")
    args = ap.parse_args()
    cands, w = candidates(args.study, args.top)
    base = optimize.base_cfg(args.study)
    sets, _ = sweep.param_sets()
    seeds = range(SEED0, SEED0 + args.seeds)
    args.variants = args.variants.split(",")
    var = variants(args.study, args.heavy, args.variants)
    contacts = contacts_all(cands, args.study, base, seeds, args.workers, args.report)
    for c in cands:
        k = contacts[c["id"]]
        print(f"{c['id']}: {c['label']}\n    clearance {k['clearance']}, probe {k['probe']}: dt {k['dt']:g}, "
              f"timeconst {k['tc']:g} ({k['why']}); contact_rule: {k['rule'][2]}", flush=True)
    jobs = {}
    for c in cands:
        for v, (_, mix, stiff) in var.items():
            dt, tc = contacts[c["id"]]["dt"], contacts[c["id"]]["tc"]
            if stiff:
                dt, tc = stiffer(dt, tc)
            jobs[(c["id"], v)] = jobs_for(c, args.study, base, v, mix, seeds, sets, dt, tc, args.duration)
    alljobs = [j for js in jobs.values() for j in js]
    recs = run_all(alljobs, args.study, args.workers, args.report)
    summ = {c["id"]: {v: summarize(recs, jobs[(c["id"], v)], args.study) for v in var} for c in cands}
    write_md(args.study, cands, w, summ, contacts, args)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--job":
        job_path = Path(sys.argv[2])
        job_path.with_suffix(".out.json").write_text(
            json.dumps(run_job(json.loads(job_path.read_text(encoding="utf-8"))), default=sweep.jsonable),
            encoding="utf-8")
    else:
        main()
