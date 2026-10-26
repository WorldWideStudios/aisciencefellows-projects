"""Find which designs, mixes and contact settings make MuJoCo go unstable ("Nan, Inf or huge value in QACC").

MuJoCo answers a bad QPOS, QVEL or QACC by resetting mjData and carrying on, so an unstable run still
finishes (sorter.py now lists the resets in results["unstable_resets"]). This probe wraps mj_step to stop at
the first reset and record when it happened, in which phase, which warning, and which particle it hit.

Run from sim\\ (WSL venv on this laptop):
    python instab.py [--seeds 8] [--workers 22] [--duration 1] [--out out/instab.jsonl]
        [--strokes "sine:amp_mm=1.24,freq_hz=20,angle_deg=90;..."] [--designs "a;b"] [--mixes grains76,...]
"""
import argparse
import json
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
from pathlib import Path

DESIGNS = ["pool:w5p0,t1p4", "inserts:mesh5,mesh2", "inserts:5mm,2mm", "plinko"]
MIXES = {
    "grains76": {"rice": 30, "quinoa": 30, "chickpea": 8, "pasta": 8},
    "insects70": {"rice": 20, "quinoa": 20, "chickpea": 5, "pasta": 5,
                  "insect_compact": 8, "insect_elongate": 8, "insect_longleg": 4},
    "demo": {"pasta": 15, "rice": 40},
    "mixed120": {"rice": 40, "quinoa": 40, "chickpea": 10, "pasta": 10,
                 "insect_compact": 8, "insect_elongate": 8, "insect_longleg": 4},
}
SOLVER = [(5e-4, 2e-3), (2.5e-4, 5e-4), (2.5e-4, 1e-3), (1.25e-4, 5e-4)]     # (dt, timeconst)
STROKES = ["constant_speed:amp_mm=10,speed_mm_s=50,ramp_s=0.01"]                 # sorter.py --stroke syntax
SETTLE_S = 1.0


class Unstable(Exception):
    pass


def probe(job):
    import mujoco
    import numpy as np
    import designs
    import sorter
    # the pool reuses worker processes: wrap the original mj_step, not the previous job's wrapper
    step = mujoco.__dict__.setdefault("_unwrapped_mj_step", mujoco.mj_step)
    bad ={"qpos": mujoco.mjtWarning.mjWARN_BADQPOS, "qvel": mujoco.mjtWarning.mjWARN_BADQVEL,
           "qacc": mujoco.mjtWarning.mjWARN_BADQACC}
    roles = [g["role"] for g in designs.build(job["design"]).geoms]
    names = sorted(set(roles))
    seen = {"pen": np.zeros(len(names))}

    def checked_step(m, d):
        t = d.time
        step(m, d)
        if "role" not in seen:      # role index per geom, -1 off the tray
            seen["role"] = np.full(m.ngeom, -1)
            for i, r in enumerate(roles):
                seen["role"][m.geom(f"tray{i}").id] = names.index(r)
        if d.time >= SETTLE_S and d.ncon:      # worst overlap per tray role after the settle, every step (impacts
            r = seen["role"][d.contact.geom[:d.ncon]].max(axis=1)      # last a few steps; sorter samples every 10th)
            np.maximum.at(seen["pen"], r[r >= 0], -d.contact.dist[:d.ncon][r >= 0])
        if d.time < t:                                   # MuJoCo reset the state: it went unstable
            what = next((k for k, w in bad.items() if d.warning[w].number), None)
            dof = int(d.warning[bad[what]].lastinfo) if what else -1
            body = int(m.body_rootid[m.dof_bodyid[dof]]) if 0 <= dof < m.nv else -1
            raise Unstable(json.dumps({"t": round(float(t + m.opt.timestep), 5), "warning": what, "dof": dof,
                                       "body": m.body(body).name if body > 0 else None}))

    mujoco.mj_step = checked_step
    profile, _, rest = job["stroke"].partition(":")
    stroke = {"profile": profile, **sorter.parse_kv(rest)}
    cfg = sorter.RunConfig(design=job["design"], mix=MIXES[job["mix"]], stroke=stroke, duration_s=job["duration"],
                           settle_s=SETTLE_S, seed=job["seed"], dt=job["dt"],
                           contact={"friction": 0.4, "timeconst": job["tc"], "dampratio": 1.0}, record_fps=0)
    t0 = time.perf_counter()
    out = {**job, "unstable": False}
    try:
        res = sorter.run(cfg)
        out["max_pen_tray"], out["max_pen_pp"] = res["max_penetration_mm"], res["max_penetration_particles_mm"]
        out["max_pen_role"] = {r: round(float(v), 5) for r, v in zip(names, seen["pen"])}
        # gates and screens only: optimize.py's measure. Floors count too where a tunnel's ceiling sits above them
        out["max_pen_gate"] = max([out["max_pen_role"][r] for r in ("gate", "screen") if r in names], default=0.0)
    except Unstable as e:
        info = json.loads(str(e))
        out.update(unstable=True, **info, phase="settle" if info["t"] < cfg.settle_s else "shake")
        if info["body"]:                                   # p### -> kind, from the same seeded mix order
            i = int(info["body"][1:])
            out["kind"] = [k for k, n in cfg.mix.items() for _ in range(n)][i]
    except Exception:
        out["error"] = traceback.format_exc()[-1500:]
    mujoco.mj_step = step
    out["wall_s"] = round(time.perf_counter() - t0, 2)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--duration", type=float, default=1.0, help="shake seconds after the 1 s settle")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 6) - 2))
    ap.add_argument("--designs", default=";".join(DESIGNS), help="';'-separated design specs")
    ap.add_argument("--mixes", default=",".join(MIXES))
    ap.add_argument("--solver", default=";".join(f"{dt},{tc}" for dt, tc in SOLVER), help="'dt,tc;dt,tc;...'")
    ap.add_argument("--strokes", default=";".join(STROKES), help="';'-separated sorter.py --stroke specs")
    ap.add_argument("--out", default="out/instab.jsonl")
    ap.add_argument("--retry", action="store_true", help="keep the runs in --out that finished; redo the rest")
    args = ap.parse_args()
    solver = [tuple(map(float, s.split(","))) for s in args.solver.split(";")]
    jobs = [{"design": de, "mix": mx, "stroke": st, "dt": dt, "tc": tc, "seed": s, "duration": args.duration}
            for de, mx, st, (dt, tc), s in product(args.designs.split(";"), args.mixes.split(","),
                                                   args.strokes.split(";"), solver, range(args.seeds))]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    keep = []
    if args.retry and out.exists() and jobs:
        keep = [r for r in map(json.loads, out.read_text(encoding="utf-8").splitlines()) if "error" not in r]
        done = {json.dumps({k: r[k] for k in jobs[0]}, sort_keys=True) for r in keep}
        jobs = [j for j in jobs if json.dumps(j, sort_keys=True) not in done]
    print(f"{len(jobs)} runs on {args.workers} workers -> {out} ({len(keep)} kept)", flush=True)
    t0 = time.time()
    with open(out, "w", encoding="utf-8") as f, ProcessPoolExecutor(args.workers) as ex:
        f.writelines(json.dumps(r) + "\n" for r in keep)
        for n, fut in enumerate(as_completed([ex.submit(probe, j) for j in jobs]), 1):
            r = fut.result()
            f.write(json.dumps(r) + "\n")
            f.flush()
            tag = "UNSTABLE " + f"t={r['t']} {r['phase']} {r.get('kind')}" if r["unstable"] else \
                ("ERROR" if "error" in r else "ok")
            print(f"[{n}/{len(jobs)} {time.time() - t0:5.0f} s] {r['design']} {r['mix']} {r['stroke']} dt={r['dt']} "
                  f"tc={r['tc']} seed={r['seed']}: {tag}", flush=True)


if __name__ == "__main__":
    main()
