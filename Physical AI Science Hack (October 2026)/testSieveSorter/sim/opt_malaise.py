"""EXPLORATORY: the malaise study. Breaker layers (designs_breaker.py, cad/breaker_layer.py) on the demo rig's seesaw
tower, ranked on a Malaise clump (clumps.py): break-up first, then gentleness, then sort (docs/sessions/PLAN.md).

Nobody has measured what holds a Malaise clump together, the insect bodies are generated (insects.py
insect_malaise, sized to EntoSieve's counts), and the sim isn't calibrated against bench counts. So the scores rank
designs against each other; they are not percentages to quote.

Per run (one clump, one bond set):
    break   = 0.75 * free + 0.25 * speed     free: share of the clump's specimens with no live bond at the end;
                                             speed: 1 - t90 / duration (half credit from t50 when t90 never comes)
    gentle  = 0.5 (1 - share of specimens over clumps.FRAGILE_MN (5 mN, ASSUMED) while still in the clump)
              + 0.5 g90,  g90 = 1 - log10(p90 / 5 mN) / 2 clipped to [0, 1]: 1 at 5 mN, 0 at 500 mN, where p90 is the
              specimens' peak contact force over the whole run (drops between levels included). Over the whole run
              almost every grain passes 5 mN (98% on the CAD default: an 85 mm drop), so that share can't rank.
    sort    = share of the clump's specimens that end in their ideal zone (the square-hole rule)
    score   = 0.5 break + 0.3 gentle + 0.2 sort;  a NaN / unstable run scores -1
The clump is the bench-demo GRAIN SURROGATE (rice, quinoa, pasta with a leaf, twigs and dirt): at 12:55 every
insect clump (insect_malaise and its class kinds, insect_compact + insect_elongate) blew up in clumps.pack's
pre-sim (QACC NaN, diameters of metres), so the real Malaise insect clump waits for the clump session's fix.
Per candidate: the three bond sets (weak / medium / strong, clumps.BOND_SETS) at friction 0.4, seed 0; ranked by
mean - sd, like the friction sets in optimize.py.

Search: the breaker's six CAD keys, plus the seesaw (5-15 deg, 0.4-6 s) and its buzz (0-0.4 mm at 40 Hz, straight
up; rocking.py vib_mm). The trays under it stay the demo rig's: 5 mm over 2 mm over the catch pan, 85 mm apart.
Round 0: a Latin hypercube; later rounds: cross-entropy around the top quarter.

Run from sim\\ in WSL (<= 12 workers):
    python opt_malaise.py run --rounds 1 --workers 12
    python opt_malaise.py report
    python opt_malaise.py replay --top 1 --ids <no-breaker id>      # view.html under out/opt/malaise/replay/
Writes opt/leaderboard_malaise.md, opt/winners_malaise.json and a round entry in opt/LOG.md; runs are cached under
out/opt/malaise/.
"""
import argparse
import hashlib
import json
import math
import time
from datetime import datetime

import numpy as np

import optimize as o
import sweep

STUDY = "malaise"
CLUMP = {"kinds": {"rice": 30, "quinoa": 20, "pasta": 4, "leaf": 1, "twig": 2, "dirt": 6}}
BONDS = ("weak", "medium", "strong")
UNDER, TOWER = "5mm+2mm", 85.0
DURATION_S = 4.0                           # 2 cycles at 2 s; the CAD default frees 96% in 0.3 s (medium bonds)
DT, TIMECONST = 2.5e-4, 5e-4               # optimize.py's: the clump study's stiffer 1.25e-4 / 2.5e-4 costs 2x
FRICTION = 0.4
W_BREAK, W_GENTLE, W_SORT = 0.5, 0.3, 0.2
P = o.P
PARAMS = [P("open", 5.0, 12.0, 0.1), P("bar", 0.8, 2.4, 0.1), P("pin_d", 1.2, 4.0, 0.1), P("pin_h", 4.0, 16.0, 0.2),
          P("pitch", 6.0, 20.0, 0.1), P("tip", 0, 0, 0, ("round", "flat")),
          P("ss_deg", 5.0, 15.0, 0.5), P("ss_period", 0.4, 6.0, 0.1), P("vib_mm", 0.0, 0.4, 0.05)]
DEFAULT_STROKE = {"ss_deg": 10.0, "ss_period": 2.0, "vib_mm": 0.0}
CAD_DEFAULT = {"open": 8.0, "bar": 1.6, "pin_d": 2.5, "pin_h": 12.0, "pitch": 10.0, "tip": "round"}
ROUND0, ROUNDN = 12, 8
OUT = o.OUT / STUDY
CE = {}


def spec_of(p):
    if p.get("breaker") is False:
        return f"inserts:{UNDER.replace('+', ',')},pitch={TOWER:g}"
    return ("breaker:" + ",".join(f"{k}={p[k]}" if k == "tip" else f"{k}={p[k]:g}" for k in CAD_DEFAULT)
            + f",under={UNDER},tower={TOWER:g}")


def stroke_of(p):
    s = {"profile": "seesaw", "deg": p["ss_deg"], "period_s": p["ss_period"], "shape": "constant_speed"}
    if p.get("vib_mm"):
        s.update(vib_mm=p["vib_mm"], vib_hz=40.0)
    return s


def ok(p):
    """cad/breaker_layer.py's printability flags, as constraints."""
    if p.get("breaker") is False:
        return None
    if p["pin_h"] > 8 * p["pin_d"]:
        return "pins taller than 8 diameters"
    if p["pin_d"] >= p["pitch"] - 1.0:
        return "pins nearly touching"
    return None


def make(p, origin, rnd, label=None):
    q = {k.name: k.quant(p[k.name]) for k in PARAMS if k.name in p}
    if p.get("breaker") is False:
        q["breaker"] = False
    c = {"family": "breaker" if q.get("breaker") is not False else "none", "params": q, "spec": spec_of(q),
         "stroke": stroke_of(q), "origin": origin, "round": rnd, "label": label}
    c["id"] = "B-" + hashlib.sha1(json.dumps([c["spec"], c["stroke"]], sort_keys=True).encode()).hexdigest()[:8]
    return c


def refs(rnd):
    return [make({**DEFAULT_STROKE, "breaker": False}, "baseline", rnd,
                 "NO BREAKER: the clump straight onto the demo rig's 5 mm / 2 mm trays, default seesaw (+/-10 deg, 2 s)"),
            make({**CAD_DEFAULT, **DEFAULT_STROKE}, "baseline", rnd,
                 "cad/breaker_layer.py default (open 8, pins 2.5 x 12 every 10, round) on the default seesaw"),
            make({**CAD_DEFAULT, **DEFAULT_STROKE, "vib_mm": 0.3}, "baseline", rnd,
                 "the CAD default breaker, default seesaw + 0.3 mm buzz at 40 Hz (1.9 g, the tool's)")]


def jobs_for(c, base, seed=0):
    out = []
    for bond in BONDS:
        cfg = sweep.make_cfg(base, design=c["spec"], stroke=c["stroke"], duration_s=DURATION_S, seed=seed,
                             contact={"friction": FRICTION}, clump={**CLUMP, "bond": bond}, mix={})
        job = {"cfg": cfg, "inject": {}, "tags": {"cand": c["id"], "fid": "full", "set": bond, "seed": seed}}
        job["key"] = hashlib.sha1(json.dumps([cfg], sort_keys=True, default=sweep.jsonable).encode()).hexdigest()[:20]
        out.append(job)
    return out


def run_score(rec):
    if rec.get("error") or rec.get("unstable") or not rec.get("clumps"):
        return None
    c = rec["clumps"]
    free = c["free_frac"]
    speed = (1 - c["t90_s"] / DURATION_S) if c["t90_s"] is not None else \
        (0.5 * (1 - c["t50_s"] / DURATION_S) if c["t50_s"] is not None else 0.0)
    brk = 0.75 * free + 0.25 * max(speed, 0.0)
    g90 = min(max(1 - math.log10(max(c["damage"]["p90_mN"], 1e-9) / 5.0) / 2, 0.0), 1.0)
    gentle = 0.5 * (1 - c["damage"]["bonded_share_over"]) + 0.5 * g90
    n = sum(s["n"] for s in c["sort"].values())
    sort = sum(s["n"] * s["ideal"] for s in c["sort"].values()) / n if n else 0.0
    return {"score": W_BREAK * brk + W_GENTLE * gentle + W_SORT * sort, "break": brk, "free": free, "gentle": gentle,
            "sort": sort, "t50": c["t50_s"], "t90": c["t90_s"], "largest": c["largest_cluster"],
            "p90_mN": c["damage"]["p90_mN"], "over": c["damage"]["share_over"],
            "bonded_over": c["damage"]["bonded_share_over"], "blind": c.get("blinding") or {},
            "debris": c.get("debris_zones") or {}, "lost": sum(v.get("lost", 0) for v in rec["counts"].values()),
            "between": sum(v.get("between", 0) for v in rec["counts"].values()), "wall": rec.get("wall_total_s")}


def summarize(c, recs):
    rows = {r["tags"]["set"]: run_score(r) for r in recs}
    scores = [(-1.0 if v is None else v["score"]) for v in rows.values()]
    ok_rows = [v for v in rows.values() if v]
    mean = lambda k: float(np.mean([v[k] for v in ok_rows])) if ok_rows else None
    return {"robust": float(np.mean(scores) - np.std(scores)), "mean": float(np.mean(scores)), "fails": scores.count(-1.0),
            "by_bond": rows, **{k: mean(k) for k in ("break", "free", "gentle", "sort", "p90_mN", "over", "largest")}}


def evaluate(cands, base, workers, summ):
    jobs = [j for c in cands for j in jobs_for(c, base)]
    recs = o.run_all(jobs, STUDY, workers)
    for c in cands:
        summ[c["id"]] = summarize(c, [recs[j["key"]] for j in jobs_for(c, base)])


def lhs(n, rng):
    return o.lhs(n, PARAMS, rng)


def ce_update(cands, summ):
    fam = sorted((c for c in cands if c["family"] == "breaker" and c["id"] in summ), key=lambda c: -summ[c["id"]]["robust"])
    if len(fam) < 4:
        return
    elite = fam[:max(3, math.ceil(0.25 * len(fam)))]
    mean, sd, cat = {}, {}, {}
    for q in PARAMS:
        if q.choices:
            w = np.array([sum(c["params"][q.name] == ch for c in elite) for ch in q.choices], float) + 0.5
            w = np.maximum(w / w.sum(), 0.15)
            cat[q.name] = (w / w.sum()).tolist()
        else:
            u = np.array([(c["params"][q.name] - q.lo) / (q.hi - q.lo) for c in elite])
            m, s = float(u.mean()), float(max(u.std(ddof=1), 0.06))
            if q.name in CE.get("mean", {}):
                m, s = 0.7 * m + 0.3 * CE["mean"][q.name], 0.7 * s + 0.3 * CE["sd"][q.name]
            mean[q.name], sd[q.name] = m, max(s, 0.06)
    CE.update(mean=mean, sd=sd, cat=cat, elite=[c["id"] for c in elite])


def propose(n, rnd, rng, have):
    out, tries = [], 0
    pool = lhs(n * 4, rng) if not CE else None
    while len(out) < n and tries < n * 60:
        tries += 1
        if pool is not None:
            raw = pool[tries - 1] if tries - 1 < len(pool) else lhs(1, rng)[0]
        else:
            raw = {}
            for q in PARAMS:
                if q.choices:
                    raw[q.name] = q.choices[rng.choice(len(q.choices), p=CE["cat"][q.name])]
                else:
                    u = rng.normal(CE["mean"][q.name], CE["sd"][q.name])
                    raw[q.name] = q.lo + min(max(u, 0.0), 1.0) * (q.hi - q.lo)
        c = make(raw, "lhs" if pool is not None else "ce", rnd)
        if ok(c["params"]) or c["id"] in have or any(x["id"] == c["id"] for x in out):
            continue
        out.append(c)
    return out


def load():
    f = OUT / "state.json"
    if not f.exists():
        return [], {}
    st = json.loads(f.read_text(encoding="utf-8"))
    CE.update(st.get("ce", {}))
    return st["cands"], st["summ"]


def save(cands, summ):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "state.json").write_text(json.dumps({"cands": cands, "summ": summ, "ce": CE}, default=float), encoding="utf-8")


def base_cfg():
    import sorter
    import dataclasses
    return sweep.make_cfg(dataclasses.asdict(sorter.RunConfig()), mix={}, dt=DT, contact={"timeconst": TIMECONST})


# ---------------------------------------------------------------- reporting

def show(c):
    p = c["params"]
    st = f"seesaw +/-{p['ss_deg']:g} deg, {p['ss_period']:g} s" + (f" + {p['vib_mm']:g} mm buzz at 40 Hz" if p.get("vib_mm") else "")
    if p.get("breaker") is False:
        return f"no breaker; {st}"
    g = p["open"] + p["bar"]                     # pins stand on grid nodes: every k-th, k = round(pitch / step)
    return (f"grid {p['open']:g} mm (bars {p['bar']:g}), pins {p['pin_d']:g} x {p['pin_h']:g} mm {p['tip']} every "
            f"{max(1, round(p['pitch'] / g)) * g:.1f} mm; {st}")


def f2(v, fmt="{:.2f}"):
    return "-" if v is None else fmt.format(v)


def pct(v):
    return "-" if v is None else f"{100 * v:.0f}%"


def table(rows, summ):
    out = ["| # | id | design and stroke | robust | mean | free | break | gentle | sort | largest cluster | "
           "peak force p90 (mN) | fails |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, c in enumerate(rows, 1):
        s = summ[c["id"]]
        out.append(f"| {i} | {c['id']} | {c.get('label') or show(c)} | {s['robust']:.3f} | {s['mean']:.3f} | {pct(s['free'])} | "
                   f"{f2(s['break'])} | {pct(s['gentle'])} | {pct(s['sort'])} | {f2(s['largest'], '{:.1f}')} | "
                   f"{f2(s['p90_mN'])} | {s['fails']} |")
    return "\n".join(out)


def by_bond(c, summ):
    out = [f"**{c['id']}**: {show(c)}", "", "| bond | score | free | t50 (s) | t90 (s) | largest | over 5 mN | in the clump over 5 mN | "
           "sort | lost | debris |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for b in BONDS:
        v = summ[c["id"]]["by_bond"].get(b)
        if v is None:
            out.append(f"| {b} | FAIL | | | | | | | | | |")
            continue
        deb = "; ".join(f"{k}: " + ", ".join(f"{z} {n}" for z, n in zs.items()) for k, zs in v["debris"].items())
        out.append(f"| {b} | {v['score']:.3f} | {pct(v['free'])} | {f2(v['t50'])} | {f2(v['t90'])} | {v['largest']} | "
                   f"{pct(v['over'])} | {pct(v['bonded_over'])} | {pct(v['sort'])} | {v['lost']} | {deb} |")
    return "\n".join(out)


def ranking(cands, summ, refs_too=False):
    return sorted((c for c in cands if c["id"] in summ and (refs_too or c["origin"] != "baseline")),
                  key=lambda c: -summ[c["id"]]["robust"])


def win_key(s):
    """A verified design's winner score: the lower of its seed-0 robust and its robust over every seed (checking a
    design can only lower it). None if not verified."""
    v = s.get("verify")
    return None if not v else min(s["robust"], v["robust_all_seeds"])


def winners(cands, summ):
    return sorted((c for c in ranking(cands, summ) if win_key(summ[c["id"]]) is not None),
                  key=lambda c: -win_key(summ[c["id"]]))


def why(cands, summ):
    """Why the losers lost: the bottom half against the top half on each metric, and each parameter's rank
    correlation with the robust score."""
    rk = ranking(cands, summ)
    if len(rk) < 6:
        return []
    top, bot = rk[:len(rk) // 2], rk[len(rk) // 2:]
    lines = []
    for k, name in (("free", "free at the end"), ("gentle", "gentleness"), ("sort", "in the ideal zone"),
                    ("largest", "largest cluster left"), ("p90_mN", "peak force p90, mN")):
        a = [summ[c["id"]][k] for c in top if summ[c["id"]][k] is not None]
        b = [summ[c["id"]][k] for c in bot if summ[c["id"]][k] is not None]
        if a and b:
            lines.append(f"- {name}: top half {np.mean(a):.2f}, bottom half {np.mean(b):.2f}")
    sc = np.array([summ[c["id"]]["robust"] for c in rk])
    cors = []
    for q in PARAMS:
        if q.choices:
            for ch in q.choices:
                x = np.array([c["params"][q.name] == ch for c in rk], float)
                if 0 < x.sum() < len(x):
                    cors.append((f"{q.name}={ch}", float(np.corrcoef(x, sc)[0, 1])))
            continue
        x = np.array([c["params"][q.name] for c in rk], float)
        if x.std() > 0:
            rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(sc))
            cors.append((q.name, float(np.corrcoef(rx, ry)[0, 1])))
    cors.sort(key=lambda t: -abs(t[1]))
    lines.append("- rank correlation with the robust score (+ helps): " +
                 ", ".join(f"{n} {r:+.2f}" for n, r in cors[:6]))
    return lines


def write(cands, summ, meta):
    rk, refs_ = ranking(cands, summ), [c for c in cands if c["origin"] == "baseline" and c["id"] in summ]
    md = [f"# EXPLORATORY: clump break-up leaderboard (study malaise)", "",
          f"Updated {datetime.now():%Y-%m-%d %H:%M} by `sim/opt_malaise.py` ({meta['n_cands']} candidates, {meta['n_runs']} runs).",
          "", "**EXPLORATORY. The sim ranks designs; it isn't calibrated against bench counts.** The clump's bond strengths "
          "are assumed (clumps.py) and so is the 5 mN damage line. Read the scores as a ranking, not as percentages.", "",
          "**The clump is the bench-demo grain surrogate, not insects.** Every insect clump (`insect_malaise` and its "
          "class kinds, `insect_compact` + `insect_elongate`) blew up in `clumps.pack`'s pre-sim at 12:55 (QACC NaN), so "
          "the real Malaise clump waits for that fix.", "",
          f"- **Clump:** {', '.join(f'{k} {n}' for k, n in CLUMP['kinds'].items())}. Robust = mean - sd over the three bond "
          f"sets (weak / medium / strong) at friction {FRICTION:g}, seed 0, {DURATION_S:g} s of seesaw after a 1 s settle, "
          f"no spray (dry bonds: the hardest case).",
          f"- **Tower:** the breaker in a holder box on top of the demo rig's trays ({UNDER.replace('+', ' over ')} over the "
          f"catch pan), {TOWER:g} mm apart. Every level rocks on its own hinge across its middle, and neighbours alternate "
          f"(rocking.py).",
          f"- **Score per run:** {W_BREAK:g} x break-up (0.75 x free share + 0.25 x speed from t90) + {W_GENTLE:g} x "
          f"gentleness (half: share never over 5 mN while still in the clump; half: the peak-force p90 on a log scale, "
          f"1 at 5 mN, 0 at 500 mN) + {W_SORT:g} x sort (specimens in their ideal zone). A failed run scores -1.",
          "- **Winners** are verified designs only (rerun on freshly packed clumps, seeds 1-2), ranked by the lower of "
          "the seed-0 robust and the robust over every seed. The top-10 table is seed 0 only.", ""]
    wn = winners(cands, summ)
    if wn:
        md += ["## Winners (verified on fresh clumps)", "",
               "| # | id | design and stroke | winner score | robust, all seeds | free, fresh seeds | breaker for the CAD |",
               "|---|---|---|---|---|---|---|"]
        import designs
        for i, c in enumerate(wn[:3], 1):
            s, v = summ[c["id"]], summ[c["id"]]["verify"]
            md.append(f"| {i} | {c['id']} | {show(c)} | **{win_key(s):.3f}** | {v['robust_all_seeds']:.3f} | {pct(v['free'])} | "
                      f"`{designs.build(c['spec']).info['breaker']['cad_spec']}` |")
        md.append("")
    md += ["## Top 10 (seed 0)", "", table(rk[:10], summ), "", "## References", "", table(refs_, summ), ""]
    ver = [c for c in rk[:10] + refs_ if summ[c["id"]].get("verify")]
    if ver:
        md += ["## Verified on fresh clumps", "", "Each seed packs a different clump. The same 3 bond sets per seed; robust "
               "(all seeds) pools seed 0 with the fresh ones.", "",
               "| id | design and stroke | robust, seed 0 | robust, fresh seeds | robust, all seeds | free, fresh seeds | fails |",
               "|---|---|---|---|---|---|---|"]
        for c in ver:
            v = summ[c["id"]]["verify"]
            md.append(f"| {c['id']} | {c.get('label') or show(c)} | {summ[c['id']]['robust']:.3f} | {v['robust']:.3f} "
                      f"(seeds {', '.join(map(str, v['seeds']))}) | **{v['robust_all_seeds']:.3f}** | {pct(v['free'])} | {v['fails']} |")
        md.append("")
    md += ["## Per bond set, top 3 and the no-breaker reference", ""]
    for c in rk[:3] + [r for r in refs_ if r["params"].get("breaker") is False]:
        md += [by_bond(c, summ), ""]
    md += ["## Why the losers lost", ""] + (why(cands, summ) or ["(too few candidates yet)"]) + [""]
    (o.OPT / "leaderboard_malaise.md").write_text("\n".join(md), encoding="utf-8")
    import designs
    win = []
    for c in winners(cands, summ)[:3]:
        d = designs.build(c["spec"])
        win.append({"id": c["id"], "winner_score": round(win_key(summ[c["id"]]), 4),
                    "robust": round(summ[c["id"]]["robust"], 4), "mean": round(summ[c["id"]]["mean"], 4),
                    "design": show(c), "cad": {"file": "cad/breaker_layer.py", "spec": d.info["breaker"]["cad_spec"],
                                               "facts": {k: v for k, v in d.info["breaker"].items() if k not in ("params", "cad_spec")}},
                    "sim_spec": c["spec"], "stroke": c["stroke"], "params": c["params"],
                    "metrics": {k: summ[c["id"]][k] for k in ("free", "break", "gentle", "sort", "largest", "p90_mN", "over")},
                    "by_bond": summ[c["id"]]["by_bond"], "verify": summ[c["id"]].get("verify")})
    (o.OPT / "winners_malaise.json").write_text(json.dumps(
        {"study": "malaise", "exploratory": True, "note": "EXPLORATORY: the sim ranks designs; it isn't calibrated against "
         "bench counts. The clump is the grain surrogate (insect clumps don't pack yet); bond strengths and the 5 mN "
         "damage line are assumed. Winners are verified on fresh clumps, ranked by winner_score = min(robust seed 0, "
         "robust over all seeds).", "updated": f"{datetime.now():%Y-%m-%d %H:%M}",
         "clump": CLUMP, "tower": {"under": UNDER, "pitch_mm": TOWER}, "winners": win}, indent=1, default=float), encoding="utf-8")


def log_round(rnd, new, cands, summ, meta):
    rk = ranking(cands, summ)
    ref = {c["label"].split(":")[0]: summ[c["id"]] for c in cands if c["origin"] == "baseline" and c["id"] in summ}
    lines = [f"", f"## malaise round {rnd} (EXPLORATORY, {datetime.now():%Y-%m-%d %H:%M}, auto)", "",
             f"**Tried:** {len(new)} candidates ({', '.join(sorted({c['origin'] for c in new}))}), {meta['round_runs']} runs, "
             f"{meta['round_min']:.0f} min wall.", ""]
    if rk:
        b = rk[0]
        s = summ[b["id"]]
        lines += [f"**Leader:** {b['id']}: {show(b)}. Robust {s['robust']:.3f} (mean {s['mean']:.3f}); free {pct(s['free'])}, "
                  f"gentle {pct(s['gentle'])}, sort {pct(s['sort'])}, largest cluster {f2(s['largest'], '{:.1f}')}.", ""]
    for k, s in ref.items():
        lines.append(f"- reference {k}: robust {s['robust']:.3f}; free {pct(s['free'])}, gentle {pct(s['gentle'])}, sort {pct(s['sort'])}")
    lines += ["", "**Why the losers lost:**", ""] + (why(cands, summ) or ["(too few candidates yet)"])
    o.append_log("\n".join(lines) + "\n")


def run(args):
    rng = np.random.default_rng(args.seed)
    base = base_cfg()
    cands, summ = load()
    have = {c["id"] for c in cands}
    done = max((c["round"] for c in cands), default=-1)
    for rnd in range(done + 1, done + 1 + args.rounds):
        t0 = time.time()
        new = [c for c in refs(rnd) if c["id"] not in have]
        ce_update(cands, summ)
        new += propose(ROUND0 if rnd == 0 else ROUNDN, rnd, rng, have)
        cands += new
        have |= {c["id"] for c in new}
        print(f"malaise round {rnd}: {len(new)} candidates x {len(BONDS)} bond sets", flush=True)
        evaluate(new, base, args.workers, summ)
        ce_update(cands, summ)
        save(cands, summ)
        meta = {"n_cands": len(cands), "n_runs": len(list((OUT / "runs").glob("*.json"))), "round_runs": len(new) * len(BONDS),
                "round_min": (time.time() - t0) / 60}
        write(cands, summ, meta)
        log_round(rnd, new, cands, summ, meta)
        print(f"malaise round {rnd} done in {meta['round_min']:.1f} min", flush=True)


def verify(args):
    """Rerun the top designs (and the references) on fresh clump seeds: each seed packs a different clump."""
    base = base_cfg()
    cands, summ = load()
    seeds = [int(x) for x in args.seeds.split(",")]
    pick = ranking(cands, summ)[:args.top] + [c for c in cands if c["origin"] == "baseline"]
    jobs = [j for c in pick for sd in seeds for j in jobs_for(c, base, sd)]
    recs = o.run_all(jobs, STUDY, args.workers)
    for c in pick:
        rows = [recs[j["key"]] for sd in seeds for j in jobs_for(c, base, sd)]
        scores = [(-1.0 if run_score(r) is None else run_score(r)["score"]) for r in rows]
        allsc = scores + [(-1.0 if v is None else v["score"]) for v in summ[c["id"]]["by_bond"].values()]
        free = [run_score(r)["free"] for r in rows if run_score(r)]
        summ[c["id"]]["verify"] = {"seeds": seeds, "robust": float(np.mean(scores) - np.std(scores)),
                                   "robust_all_seeds": float(np.mean(allsc) - np.std(allsc)),
                                   "free": float(np.mean(free)) if free else None, "fails": scores.count(-1.0),
                                   "by_seed_bond": {f"{r['tags']['seed']}/{r['tags']['set']}": run_score(r) and round(run_score(r)["score"], 3)
                                                    for r in rows}}
        print(c["id"], show(c), json.dumps({k: v for k, v in summ[c["id"]]["verify"].items() if k != "by_seed_bond"}), flush=True)
    save(cands, summ)
    write(cands, summ, {"n_cands": len(cands), "n_runs": len(list((OUT / "runs").glob("*.json")))})


def replay(args):
    """Record the top winners (and --ids) on the medium bond set, seed 0, and build each view.html (bambu's hero clip)."""
    import sorter
    import viewer
    cands, summ = load()
    by_id = {c["id"]: c for c in cands}
    ids = [c["id"] for c in (winners(cands, summ) or ranking(cands, summ))[:args.top]] + (args.ids.split(",") if args.ids else [])
    o.one_box_seesaw()
    for cid in ids:
        c = by_id[cid]
        out = OUT / "replay" / cid
        cfg = sweep.make_cfg(base_cfg(), design=c["spec"], stroke=c["stroke"], duration_s=args.duration or DURATION_S,
                             seed=0, contact={"friction": FRICTION}, clump={**CLUMP, "bond": "medium"}, mix={})
        cfg["record_fps"], cfg["out_dir"] = 30.0, str(out)
        r = sorter.run(sorter.RunConfig(**cfg))
        print(cid, show(c), f"free {r['clumps']['free_frac']:.0%}", "->", viewer.build(out, rig="bugsorter"), flush=True)


def report(args):
    cands, summ = load()
    write(cands, summ, {"n_cands": len(cands), "n_runs": len(list((OUT / "runs").glob("*.json")))})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["run", "report", "replay", "verify"])
    ap.add_argument("--seeds", default="1,2", help="verify: fresh clump seeds")
    ap.add_argument("--top", type=int, default=1)
    ap.add_argument("--ids", help="replay: extra candidate ids, comma separated")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--duration", type=float, help="override the run length, s (smoke tests)")
    args = ap.parse_args()
    global DURATION_S
    DURATION_S = args.duration or DURATION_S
    {"run": run, "report": report, "replay": replay, "verify": verify}[args.cmd](args)


if __name__ == "__main__":
    main()
