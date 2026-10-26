"""Physical passage twin: which toy insects pass which hole shapes.

For each toy (Merkle-KG insect mesh) and each hole (kit sieve or punch filter):
the toy is treated as a RIGID body bounded by its convex hull (a lower bound on
real passage: legs and wings fold). For orientations sampled uniformly on the
sphere (Fibonacci, 64 directions), the hull is projected onto the plate plane;
it passes in that orientation if some in-plane rotation (every 7.5 deg) of the
projection fits inside the hole (centroid and bbox-centre placements).

  passage_score  fraction of orientations that pass (how likely shaking finds one)
  flat_pass      passes lying flat (the resting orientation on a sieve)
  end_on_only    passes only within 35 deg of its body axis (needs flow alignment)
  result         pass_flat | pass_tumbled | end_on_only | retained

Every hole is a node (shape hash), every (toy, hole) test an edge leaf; the
passage root covers all edges. Leave-one-plate-out tests whether a simple
width rule (pass iff body width < k x hole inscribed width, k fit on the other
plates) predicts the held-out plate: where it breaks, hole SHAPE matters.

  python -m baebugs.passage_twin --out print/filters/passage
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from shapely import affinity
from shapely.geometry import MultiPoint

from . import punch_filters as PF
from .explore import merkle_root
from .insect_kg import insect_tree

N_DIRS = 64
ROT_STEP = 7.5
END_ON_DEG = 35.0


def fib_dirs(n=N_DIRS):
    """n directions on the upper hemisphere (a projection along d equals -d)."""
    out = []
    g = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - (i + 0.5) / n          # (0, 1]
        r = math.sqrt(1 - z * z)
        out.append((r * math.cos(g * i), r * math.sin(g * i), z))
    return np.array(out)


def profiles(mesh, dirs):
    hull = mesh.convex_hull.vertices
    out = []
    for d in dirs:
        d = d / np.linalg.norm(d)
        a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
        u = np.cross(d, a); u /= np.linalg.norm(u); v = np.cross(d, u)
        P = MultiPoint(np.stack([hull @ u, hull @ v], 1).tolist()).convex_hull
        ang = math.degrees(math.acos(min(1.0, abs(d[0]))))        # angle to body (x) axis
        out.append({"poly": P, "end_on": ang <= END_ON_DEG, "flat": d[2] > 0.97,
                    "mbr": P.minimum_bounding_radius() if hasattr(P, "minimum_bounding_radius") else None})
    return out


def _mbr(p):
    from shapely import minimum_bounding_radius
    return float(minimum_bounding_radius(p))


def fits(P, hole, hm):
    """Does convex polygon P fit inside hole for some rotation?"""
    r = _mbr(P)
    if r * 2 <= hm["inscribed_d_mm"]:
        return True                                      # fits in the inscribed circle, any rotation
    mrr = P.minimum_rotated_rectangle
    xs = list(mrr.exterior.coords)[:4]
    pmin = min(math.dist(xs[0], xs[1]), math.dist(xs[1], xs[2]))
    if pmin > hm["max_width_mm"] + 1e-9:
        return False
    hole_t = hole.buffer(1e-6)
    hc = hole.centroid
    for k in range(int(180 / ROT_STEP)):
        Q = affinity.rotate(P, k * ROT_STEP, origin="centroid")
        for c in (Q.centroid, Q.envelope.centroid):
            Qt = affinity.translate(Q, hc.x - c.x, hc.y - c.y)
            if hole_t.contains(Qt):
                return True
    return False


def holes():
    """Kit sieves (as their nominal shapes) + punch filters."""
    from .sieve import load_yaml
    kit = load_yaml("sieves.yaml")
    shape_of = {"perforated_round": "circle", "printed_square": "square", "hex_wire": "hexagon", "woven_screen": "square"}
    out = []
    for s in kit["sieves"]:
        if s["aperture_mm"] <= 0:
            continue
        sh = shape_of.get(s["kind"], "circle")
        key = {"circle": "d", "square": "s", "hexagon": "across_flats"}[sh]
        e = (s["id"], "BioKEA kit (estimated aperture)", "kit", sh, {key: s["aperture_mm"]}, s.get("note", ""))
        out.append(e)
    return out + list(PF.LIBRARY)


def body_mesh(length_mm, plan, mode):
    """toy_rigid: the printed toy (legs, antennae, wings fixed);
    body_folded: body segments only (real insect with appendages folded)."""
    if mode == "toy_rigid":
        return insect_tree(length_mm, plan)[1]["_mesh"]
    import trimesh

    from .printmodels import insect_parts
    prims, _, _ = insect_parts(length_mm, plan)
    return trimesh.util.concatenate([m for p in prims if p["part"].endswith("_body") for m in p["meshes"]])


def run(kg_dir="print/fuse1/kg", out_dir="print/filters/passage", ledger=None, mode="toy_rigid"):
    index = json.loads((Path(kg_dir) / "index.json").read_text())
    dirs = fib_dirs()
    H = [(e, PF.hole(e), PF.hole_metrics(PF.hole(e)), PF.spec(e)) for e in holes()]
    edges = []
    for x in index:
        prof = profiles(body_mesh(x["length_mm"], x["plan"], mode), dirs)
        for e, h, hm, sp in H:
            ok = [fits(p["poly"], h, hm) for p in prof]
            score = sum(ok) / len(ok)
            flat = any(o for o, p in zip(ok, prof) if p["flat"])
            non_end = any(o for o, p in zip(ok, prof) if not p["end_on"])
            res = ("pass_flat" if flat else "pass_tumbled" if non_end else "end_on_only" if any(ok) else "retained")
            rec = {"mode": mode, "insect": x["name"], "insect_hash": x["insect_hash"], "plan": x["plan"], "length_mm": x["length_mm"],
                   "body_width_mm": x["body_width_mm"], "training_role": x.get("training_role"),
                   "hole": e[0], "hole_hash": sp["hash"], "shape": e[3], "realisation": e[2],
                   "inscribed_d_mm": hm["inscribed_d_mm"], "passage_score": round(score, 3), "result": res}
            rec["leaf"] = hashlib.sha256(json.dumps({k: rec[k] for k in ("mode", "insect_hash", "hole_hash", "passage_score", "result")},
                                                    sort_keys=True).encode()).hexdigest()
            edges.append(rec)
        print(f"[passage] {x['name']}", flush=True) if len(edges) % (len(H) * 10) == 0 else None
    out = Path(out_dir) / mode; out.mkdir(parents=True, exist_ok=True)
    (out / "edges.jsonl").write_text("".join(json.dumps(r) + "\n" for r in edges))
    summ = summarize(edges, H)
    summ["passage_root"] = merkle_root(sorted(r["leaf"] for r in edges))
    (out / "summary.json").write_text(json.dumps(summ, indent=1))
    write_csv(out, summ)
    if ledger is not None:
        ledger.append(f"passage_twin_{mode}", {"root": summ["passage_root"], "edges": len(edges), "holes": len(H),
                                       "lopo": summ["lopo"]["overall"]}, files={"edges": out / "edges.jsonl"})
    return summ


def summarize(edges, H):
    by_hole = {}
    for r in edges:
        by_hole.setdefault(r["hole"], []).append(r)
    holes_out = {}
    for e, h, hm, sp in H:
        rs = by_hole[e[0]]
        passing = [r for r in rs if r["result"] != "retained"]
        # effective cut: body width where flat passage switches (logistic-free: midpoint of overlap)
        wp = sorted(r["body_width_mm"] for r in rs if r["result"] == "pass_flat")
        wr = sorted(r["body_width_mm"] for r in rs if r["result"] != "pass_flat")
        cut = None
        if wp and wr:
            cut = round((max(wp) + min([w for w in wr if w >= max(wp)] or [max(wp)])) / 2, 2)
        plans = {}
        for r in rs:
            p = plans.setdefault(r["plan"], [0, 0]); p[0] += 1; p[1] += r["result"] != "retained"
        holes_out[e[0]] = {"shape": e[3], "realisation": e[2], "inscribed_d_mm": hm["inscribed_d_mm"],
                           "max_width_mm": hm["max_width_mm"], "passes_any": len(passing),
                           "pass_flat": sum(r["result"] == "pass_flat" for r in rs),
                           "pass_tumbled": sum(r["result"] == "pass_tumbled" for r in rs),
                           "end_on_only": sum(r["result"] == "end_on_only" for r in rs),
                           "retained": sum(r["result"] == "retained" for r in rs),
                           "flat_cut_body_width_mm": cut,
                           "cut_over_inscribed": round(cut / hm["inscribed_d_mm"], 2) if cut else None,
                           "pass_rate_by_plan": {k: f"{v[1]}/{v[0]}" for k, v in sorted(plans.items())}}
    return {"holes": holes_out, "lopo": lopo(edges, H)}


def lopo(edges, H):
    """Leave-one-plate-out: predict 'passes in some orientation' from body width
    vs k x inscribed width, k fit on the other plates. Where accuracy drops,
    the hole's SHAPE (not just its size) decides passage."""
    names = [e[0] for e, *_ in H]
    rows = [(r["hole"], r["body_width_mm"], r["inscribed_d_mm"], r["result"] != "retained") for r in edges]
    ks = np.round(np.arange(0.5, 3.01, 0.02), 2)
    per = {}
    for hname in names:
        train = [r for r in rows if r[0] != hname]
        test = [r for r in rows if r[0] == hname]
        acc = [np.mean([(w < k * d) == y for _, w, d, y in train]) for k in ks]
        k = float(ks[int(np.argmax(acc))])
        a = float(np.mean([(w < k * d) == y for _, w, d, y in test]))
        per[hname] = {"k": k, "accuracy": round(a, 3), "errors": round((1 - a) * len(test))}
    worst = sorted(per.items(), key=lambda kv: kv[1]["accuracy"])[:6]
    return {"per_plate": per, "overall": round(float(np.mean([v["accuracy"] for v in per.values()])), 3),
            "shape_matters_most": [w[0] for w in worst]}


def write_csv(out, summ):
    import csv
    with (Path(out) / "holes.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hole", "shape", "realisation", "inscribed_d_mm", "max_width_mm", "pass_flat", "pass_tumbled",
                    "end_on_only", "retained", "flat_cut_body_width_mm", "cut_over_inscribed", "lopo_k", "lopo_accuracy"])
        for h, s in summ["holes"].items():
            lp = summ["lopo"]["per_plate"][h]
            w.writerow([h, s["shape"], s["realisation"], s["inscribed_d_mm"], s["max_width_mm"], s["pass_flat"],
                        s["pass_tumbled"], s["end_on_only"], s["retained"], s["flat_cut_body_width_mm"],
                        s["cut_over_inscribed"], lp["k"], lp["accuracy"]])


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--kg", default="print/fuse1/kg")
    ap.add_argument("--out", default="print/filters/passage")
    ap.add_argument("--ledger", action="store_true")
    ap.add_argument("--modes", default="toy_rigid,body_folded")
    a = ap.parse_args()
    led = None
    if a.ledger:
        from .git_ledger import GitLedger
        led = GitLedger("filters", ".")
    for mode in a.modes.split(","):
        s = run(a.kg, a.out, led, mode)
        print(mode, json.dumps({"lopo": s["lopo"]["overall"], "shape_matters_most": s["lopo"]["shape_matters_most"],
                                "root": s["passage_root"][:16]}))
