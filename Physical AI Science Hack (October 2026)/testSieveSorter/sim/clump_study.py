"""Clump break-up study: one clump on one design and stroke, across bond sets x spray on/off x seeds (CLUMPS.md).

Run from sim\\ (workers <= 4 while the optimizer runs: memory is short):
    <venv python> clump_study.py --name spray10 --workers 4
Each run is a sorter.run with a clump (clumps.py). Writes out/clump_study/<name>.json (one row per run) and
prints a markdown table, averaged over seeds.
"""
import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

import clumps
import sorter

KEEP = ("n_specimens", "n_debris", "diameter_mm", "n_bonds", "broken", "broken_in_settle", "free_frac", "t50_s",
        "t90_s", "largest_cluster", "blinding", "sort", "debris_zones")


def one(job):
    cfg = sorter.RunConfig(**job["cfg"])
    t0 = time.perf_counter()
    r = sorter.run(cfg)
    c = r["clumps"]
    dmg = {k: v for k, v in c["damage"].items() if k != "per_specimen_mN"}
    row = {**job["tags"], "wall_s": round(time.perf_counter() - t0, 1), "resets": len(r["unstable_resets"]),
           "max_pen_mm": r["max_penetration_mm"], **{k: c[k] for k in KEEP}, "damage": dmg,
           "free_t": c["timeseries"]["t"], "free": c["timeseries"]["free"], "counts": r["counts"]}
    print(f"  {job['tags']}: free {c['free_frac']:.2f}, t50 {c['t50_s']}, t90 {c['t90_s']}, "
          f"largest {c['largest_cluster']}, {row['wall_s']} s wall", flush=True)
    return row


def table(rows, keys=("bond", "spray")):
    """Markdown summary, mean over seeds per (bond, spray)."""
    groups = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in keys), []).append(r)

    def mean(vals, fmt="{:.2f}"):
        v = [x for x in vals if x is not None]
        if not v:
            return "never"
        s = fmt.format(np.mean(v))
        return s + (f" ({len(v)}/{len(vals)})" if len(v) < len(vals) else "")

    out = ["| bond | spray | free at end | t50 (s) | t90 (s) | largest cluster | peak force p90 (mN) | over fragile | "
           "leaf blinding (top) | clump specimens in ideal zone | seeds |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    order = {b: i for i, b in enumerate(clumps.BOND_SETS)}
    for key in sorted(groups, key=lambda k: (order.get(k[0], 9), str(k[1]))):
        g = groups[key]
        top = [next(iter(r["blinding"].values()), None) if r["blinding"] else None for r in g]
        ideal = [np.mean([s["ideal"] for s in r["sort"].values()]) if r["sort"] else None for r in g]
        out.append(f"| {key[0]} | {key[1]} | {mean([r['free_frac'] for r in g], '{:.0%}')} | {mean([r['t50_s'] for r in g])} | "
                   f"{mean([r['t90_s'] for r in g])} | {mean([r['largest_cluster'] for r in g], '{:.1f}')} | "
                   f"{mean([r['damage']['p90_mN'] for r in g])} | {mean([r['damage']['share_over'] for r in g], '{:.0%}')} | "
                   f"{mean(top, '{:.0%}')} | {mean(ideal, '{:.0%}')} | {len(g)} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--name", default="study")
    ap.add_argument("--design", default="inserts:5mm,2mm,pitch=85")
    ap.add_argument("--clump", default="rice=50,quinoa=50,pasta=6,leaf=1,twig=2,dirt=10")
    ap.add_argument("--mix", default="")
    ap.add_argument("--stroke", default="seesaw:deg=10,period_s=2")
    ap.add_argument("--bonds", default=",".join(clumps.BOND_SETS))
    ap.add_argument("--spray", default="none,default", help="comma list of none / default / bench")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--duration", type=float, default=10.0)
    ap.add_argument("--dt", type=float, default=1.25e-4)
    ap.add_argument("--timeconst", type=float, default=2.5e-4)
    ap.add_argument("--friction", type=float, default=0.4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--record", action="store_true", help="also record each run to out/clump_study/<name>/<tag>")
    args = ap.parse_args()
    profile, _, rest = args.stroke.partition(":")
    stroke = {"profile": profile, **sorter.parse_kv(rest)}
    base = clumps.parse(args.clump)
    jobs = []
    for bond in args.bonds.split(","):
        for spray in args.spray.split(","):
            for seed in map(int, args.seeds.split(",")):
                tag = f"{bond}_{spray}_s{seed}"
                cfg = {"design": args.design, "mix": sorter.parse_kv(args.mix), "stroke": stroke,
                       "duration_s": args.duration, "seed": seed, "dt": args.dt,
                       "contact": {"friction": args.friction, "timeconst": args.timeconst, "dampratio": 1.0},
                       "spray": None if spray == "none" else {"jets": spray},
                       "clump": {**base, "bond": bond},
                       "record_fps": 30.0 if args.record else 0.0,
                       "out_dir": str(Path("out/clump_study") / args.name / tag) if args.record else None}
                jobs.append({"cfg": cfg, "tags": {"bond": bond, "spray": spray, "seed": seed}})
    workers = max(1, min(args.workers, 4, len(jobs)))
    print(f"{len(jobs)} runs on {workers} workers: {args.design}, {args.stroke}, clump {args.clump}", flush=True)
    with mp.get_context("spawn").Pool(workers, maxtasksperchild=1) as pool:
        rows = pool.map(one, jobs, chunksize=1)
    out = Path("out/clump_study")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.name}.json").write_text(json.dumps({"args": vars(args), "rows": rows}, indent=1, default=float))
    print(table(rows))
    print("wrote", out / f"{args.name}.json")


if __name__ == "__main__":
    main()
