"""Second opinion on the designs under the rig's real motion (physics session, docs/sessions/PLAN.md physics step 2).

Every design runs on rocking.py's alternating seesaw: each tray rocks about its own pivot across its middle (axis Y,
the ends tip), neighbours in opposite phase, in the lab frame (docs/SYSTEM.md section 3). Candidates:
  - the demo rig the team built: printed 5 mm / 2 mm trays, inserts:5mm,2mm at pitch= (85 mm by default);
  - the demo study's current winners (opt/winners.json), their vibration strokes replaced by the seesaw. A one-box
    design (plinko, gated) rocks as one level on one hinge across the holder's middle, as the optimizer's seesaw
    study does it (optimize.one_box_seesaw when that is on main, else the same patch here);
  - the optimizer's seesaw winners (opt/winners_seesaw.json, when it exists) on their own seesaw strokes and on the
    default one.
Each runs 6 fresh seeds x 3 friction sets per angle, scored by optimize.run_score with the demo study's classes
(robust = mean - 1 sd, as on the leaderboard), at the optimizer's contacts (dt 0.25 ms / timeconst 0.5 ms) unless
--dt / --tc say otherwise. Cost on this laptop, dt 0.125 ms: about 45 s of wall per simulated second for the demo
rig, and about 3 min for a one-box plinko (many rods, all on the moving hinge), hence --onebox-seeds. Runs are cached under out/verify/seesaw/ (gitignored); this file only
adds the candidates, the seesaw and the write-up to verify.py's runner.

Run from sim\\ (WSL venv), at most 4 workers (PLAN.md):
    python verify_seesaw.py [--deg 10,15] [--period 2] [--seeds 6] [--duration 12] [--workers 4] [--top 3]
    python verify_seesaw.py --report        rewrite opt/VERIFY_SEESAW.md from the cached runs, running nothing
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

import optimize
import sweep
import verify

HERE = Path(__file__).resolve().parent
STUDY = "demo"                   # scoring: the demo study's classes (the optimizer's seesaw study uses the same mix)
CACHE = "seesaw"                 # out/verify/seesaw/
DT, TC = optimize.DT, optimize.TIMECONST    # the optimizer's contacts, so a difference comes from seeds and motion
PITCH = 85.0                     # mm, box bottom to box bottom: the +X tab cut off (SYSTEM.md section 3)
SHAPE = "constant_speed"         # as the firmware drives its stage (rocking.py default)


def seesaw(deg, period):
    return {"profile": "seesaw", "deg": float(deg), "period_s": float(period), "shape": SHAPE}


def one_box_seesaw():
    """optimize.one_box_seesaw if optimize.py has it; else the same patch: a design that isn't a holder tower
    (plinko: its layers stand in one holder; gated) rocks as one level on one hinge across the holder's middle."""
    if hasattr(optimize, "one_box_seesaw"):
        return optimize.one_box_seesaw()
    import designs_holder
    import rocking
    if getattr(rocking, "_one_box", False):
        return
    tower, init = rocking.find_levels, rocking.Seesaw.__init__

    def find_levels(design):
        if "catch_z_mm" in design.info:
            return tower(design)
        H = designs_holder.cad()[0].H
        return [{"name": "level0", "zone": design.zones[-1]["name"], "z0": 0.0, "pivot": [0.0, 0.0, H / 2],
                 "geoms": list(range(len(design.geoms)))}], []

    def __init__(self, stroke, design, *a):
        init(self, stroke, design, *a)
        if self.n == 1:
            self.zone_level = {z["name"]: 0 for z in design.zones}

    rocking.find_levels, rocking.Seesaw.__init__, rocking._one_box = find_levels, __init__, True


def run_in_child(job, job_dir):
    """verify.run_in_child, but the child is this file (so it gets the one-box seesaw)."""
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


def candidates(args):
    """[{id, label, spec, inject, strokes: [stroke], opt?}], in run order: the rig first."""
    pitch = f",pitch={args.pitch:g}"
    out = [{"id": "demo-rig", "label": f"demo rig: inserts:5mm,2mm{pitch}", "spec": f"inserts:5mm,2mm{pitch}",
            "inject": {}, "strokes": [], "src": "rig"}]
    w = json.loads((optimize.OPT / "winners.json").read_text(encoding="utf-8"))
    for x in w["winners"][:args.top]:
        out.append({"id": x["id"], "label": f"demo #{x['rank']} {x['id']} ({x['family']}, one box)",
                    "spec": x["sim_spec"], "inject": x.get("sim_inject") or {}, "strokes": [], "opt": x,
                    "src": f"winners.json {w.get('generated', '?')}"})
    ws = optimize.OPT / "winners_seesaw.json"
    if ws.exists():
        w2 = json.loads(ws.read_text(encoding="utf-8"))
        for x in w2["winners"][:args.top]:
            own = x["stroke"] if x["stroke"].get("profile") == "seesaw" else None
            out.append({"id": x["id"], "label": f"seesaw #{x['rank']} {x['id']} ({x['family']})",
                        "spec": x["sim_spec"], "inject": x.get("sim_inject") or {}, "opt": x,
                        "strokes": [own] if own else [], "src": f"winners_seesaw.json {w2.get('generated', '?')}"})
    defaults = [seesaw(d, args.period) for d in args.deg]
    for c in out:
        c["strokes"] = c["strokes"] + [s for s in defaults if s not in c["strokes"]]
    return out


def stroke_key(st):
    return f"+/-{st['deg']:g} deg, {st['period_s']:g} s, {st.get('shape', SHAPE).replace('_', ' ')}"


def jobs_for(c, st, base, seeds, sets, dur, dt=DT, tc=TC):
    out = []
    for label, contact in sets:
        for seed in seeds:
            cfg = sweep.make_cfg(base, design=c["spec"], stroke=st, dt=dt, contact={**contact, "timeconst": tc},
                                 duration_s=dur, seed=seed)
            out.append({"cfg": cfg, "inject": c["inject"], "key": verify.key_of(cfg, c["inject"]),
                        "tags": {"cand": c["id"], "fid": "verify-seesaw", "set": label, "seed": seed,
                                 "stroke": stroke_key(st)}})
    return out


def closest(recs, jobs):
    """The closest approach of neighbouring boxes over a row's runs, mm (rocking.clearance), or None."""
    clr = [recs[j["key"]].get("seesaw_clearance_mm") for j in jobs if j["key"] in recs]
    clr = [x for x in clr if x is not None]
    return min(clr) if clr else None


def write_md(cands, summ, clear, args, sets, source):
    cl = [x["name"] for x in optimize.STUDIES[STUDY]["classes"]]
    seeds = list(range(verify.SEED0, verify.SEED0 + args.seeds))
    path = optimize.OPT / "VERIFY_SEESAW.md"
    keep = None
    if path.exists():
        import re
        keep = re.search(r"<!-- summary -->.*?<!-- /summary -->", path.read_text(encoding="utf-8"), re.S)
    f2 = verify.f2
    L = ["# Verification under the rig's seesaw", "",
         f"Physics session, {datetime.now():%Y-%m-%d %H:%M}, `sim/verify_seesaw.py`. The designs rerun on the motion "
         "the rig really makes (docs/SYSTEM.md section 3): each tray rocks about its own pivot across its middle "
         "(the ends tip), and neighbouring levels alternate. `rocking.py`'s lab-frame hinges, one per level.", "",
         "- **Designs:** the demo rig the team built (printed 5 mm / 2 mm trays, `inserts:5mm,2mm`, "
         f"pitch {args.pitch:g} mm); the demo study's top {args.top} from `opt/winners.json`, whose vibration strokes "
         "are replaced by the seesaw (a one-box design rocks as one level about the holder's middle, as the "
         "optimizer's seesaw study does it); and the optimizer's seesaw winners from `opt/winners_seesaw.json` "
         + ("on their own strokes and on the default one." if any(c["src"].startswith("winners_seesaw") for c in cands)
            else "when that file lands (it hadn't when this ran)."),
         f"- **Runs:** fresh seeds {seeds[0]}-{seeds[-1]} x {len(sets)} friction sets ({source}) = "
         f"{len(seeds) * len(sets)} runs per design and stroke, {args.duration:g} s of seesaw after a 1 s settle, "
         f"the demo mix ({', '.join(f'{k} {v}' for k, v in optimize.STUDIES[STUDY]['mix'].items())}), scored by "
         "`optimize.run_score` with the demo study's classes (robust = mean - 1 sd, as on the leaderboard). "
         f"The optimizer's full runs are {optimize.FULL_S:g} s, so its scores aren't directly comparable: they "
         "are listed for the ranking only.",
         f"- **Contacts:** dt {args.dt * 1e3:g} ms / timeconst {args.tc * 1e3:g} ms for every run (the optimizer "
         f"runs at {optimize.DT * 1e3:g} / {optimize.TIMECONST * 1e3:g}).",
         "- **Seesaw:** constant angular speed with smoothed reversals (as the firmware drives its stage), the "
         "catch pan rocking as the next level. The user hasn't picked the angle from the 5 / 10 / 15 deg renders; "
         "+/-10 deg is the default.",
         "- The sim is uncalibrated: these scores rank designs, they don't predict bench percentages.", ""]
    short = [(c["label"], k, s["n"], s["planned"]) for c in cands for k, s in summ[c["id"]].items()
             if s and s["n"] < s["planned"]]
    if short:
        L += ["- **Incomplete:** " + "; ".join(f"{lab}, {k}: {n} of {p} runs" for lab, k, n, p in short) + ".", ""]
    if keep:
        L += [keep.group(0), ""]
    strokes = list(dict.fromkeys(k for c in cands for k in summ[c["id"]]))
    for sk in strokes:
        rows = [c for c in cands if sk in summ[c["id"]]]
        ranked = sorted([c for c in rows if summ[c["id"]][sk]], key=lambda c: -summ[c["id"]][sk]["robust"])
        L += [f"## Seesaw {sk}", ""]
        if ranked:
            L += ["**Order on robust:** " + " > ".join(c["id"] for c in ranked) + ".", ""]
        L += ["| Design | Optimizer robust (its own stroke) | Robust (mean - sd) | Mean | Worst friction set | "
              + " | ".join(f"{x} purity / recovery" for x in cl)
              + " | Jams / lost per run | t90 s (reached) | Closest boxes mm | Fails |",
              "|---|---|---|---|---|" + "---|" * len(cl) + "---|---|---|---|"]
        for c in rows:
            s = summ[c["id"]][sk]
            opt = c.get("opt", {}).get("score", {}).get("robust")
            if not s:
                L.append(f"| {c['label']} | {f2(opt, '{:.3f}')} | not run yet |" + " |" * (len(cl) + 6))
                continue
            L.append(f"| {c['label']} | {f2(opt, '{:.3f}')} | **{s['robust']:.3f}** | {s['mean']:.3f} | "
                     f"{s['worst_set']:.3f} | "
                     + " | ".join(f"{f2(p)} / {f2(r)}" for p, r in zip(s["purity"], s["recovery"]))
                     + f" | {f2(s['between'])} / {f2(s['lost'])} | {f2(s['t90'], '{:.1f}')} ({s['t90_reached']}/"
                     f"{s['n_ok']}) | {f2(clear[c['id']].get(sk), '{:.1f}')} | {len(s['fails'])} |")
        L.append("")
    L += ["## Count matrices (summed over all runs; rows = class, columns = final bin)", ""]
    for c in cands:
        for sk in strokes:
            s = summ[c["id"]].get(sk)
            if not s or not s["matrix"]:
                continue
            L += [f"**{c['label']}; seesaw {sk}** ({s['n_ok']} runs)", "",
                  "| Class | " + " | ".join(s["cols"]) + " |", "|---|" + "---|" * len(s["cols"])]
            L += [f"| {name} | " + " | ".join(str(x) for x in row) + " |" for name, row in zip(cl, s["matrix"])]
            L.append("")
    fails = [(c["label"], sk, f) for c in cands for sk in strokes for f in (summ[c["id"]].get(sk) or {}).get("fails", [])]
    if fails:
        L += ["## Failed runs", ""] + [f"- {lab}, {sk}: {f}" for lab, sk, f in fails] + [""]
    L += ["## Reproduce", "", "```", f"python verify_seesaw.py --deg {','.join(f'{d:g}' for d in args.deg)} "
          f"--period {args.period:g} --seeds {args.seeds} --duration {args.duration:g} --top {args.top} "
          f"--pitch {args.pitch:g} --workers {args.workers} --dt {args.dt:g} --tc {args.tc:g}"
          + (f" --onebox-seeds {args.onebox_seeds}" if args.onebox_seeds else ""), "```", ""]
    path.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deg", default="10", help="seesaw amplitudes, comma-separated (default 10, the user's default)")
    ap.add_argument("--period", type=float, default=2.0, help="s per cycle")
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--duration", type=float, default=12.0, help="seesaw seconds")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--pitch", type=float, default=PITCH, help="demo-rig box pitch, mm")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", default=None, help="comma-separated candidate ids to run (the report lists all)")
    ap.add_argument("--onebox-seeds", type=int, default=None,
                    help="run only this many seeds for one-box designs (a plinko seesaw run costs ~4x a tower's)")
    ap.add_argument("--dt", type=float, default=DT)
    ap.add_argument("--tc", type=float, default=TC, help="contact timeconst, s")
    ap.add_argument("--report", action="store_true", help="run nothing: rewrite VERIFY_SEESAW.md from the cache")
    args = ap.parse_args()
    args.deg = [float(x) for x in args.deg.split(",")]
    verify.run_in_child = run_in_child
    cands = candidates(args)
    base = optimize.base_cfg(STUDY)
    sets, source = sweep.param_sets()
    seeds = range(verify.SEED0, verify.SEED0 + args.seeds)
    jobs = {(c["id"], stroke_key(st)): jobs_for(c, st, base, seeds, sets, args.duration, args.dt, args.tc)
            for c in cands for st in c["strokes"]}
    only = set(args.only.split(",")) if args.only else None
    onebox = {c["id"] for c in cands if not c["spec"].startswith("inserts")}
    todo = [j for (cid, _), js in jobs.items() if only is None or cid in only for j in js
            if args.onebox_seeds is None or cid not in onebox or j["tags"]["seed"] < verify.SEED0 + args.onebox_seeds]
    recs = verify.run_all(todo, CACHE, args.workers, args.report)
    if not args.report:
        recs = verify.run_all([j for js in jobs.values() for j in js], CACHE, args.workers, cached_only=True)
    summ = {c["id"]: {stroke_key(st): verify.summarize(recs, jobs[(c["id"], stroke_key(st))], STUDY)
                      for st in c["strokes"]} for c in cands}
    clear = {c["id"]: {stroke_key(st): closest(recs, jobs[(c["id"], stroke_key(st))]) for st in c["strokes"]}
             for c in cands}
    write_md(cands, summ, clear, args, sets, source)


def run_job(job):
    """Child process: the one-box seesaw, then verify.run_job; keeps the seesaw's closest box approach."""
    import sorter
    one_box_seesaw()
    inner, seen = sorter.run, {}

    def run(cfg):
        res = inner(cfg)
        seen["seesaw"] = res.get("seesaw")
        return res

    sorter.run = run
    rec = verify.run_job(job)
    if seen.get("seesaw"):
        rec["seesaw_clearance_mm"] = seen["seesaw"]["clearance"]["min_mm"]
        rec["seesaw_touching"] = bool(seen["seesaw"]["clearance"]["touching"])
    return rec


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--job":
        job_path = Path(sys.argv[2])
        job_path.with_suffix(".out.json").write_text(
            json.dumps(run_job(json.loads(job_path.read_text(encoding="utf-8"))), default=sweep.jsonable),
            encoding="utf-8")
    else:
        main()
