"""Triage preprocessor for the PRINTED TOYS: known / question / novel against the
frozen truth they were built from (TRUTH-001, the toy Merkle KG).

There are no real insects at the bench; the printed toys are the reference set.
A photographed object is KNOWN only if it traces back, through the chain it was
built on (TRUTH-001 -> toy KG -> insect hash), to exactly one toy.

Per measurer (classical, YOLO, YOLOE, FastSAM, macOS Vision, ...):
  top view: length = long side, width = short side of the min-area rectangle, area
  candidates = TRUTH-001 subjects whose top view (envelope x/y, silhouette area)
               matches within the VALUES policy
  KNOWN    exactly one candidate (-> its insect hash)
  QUESTION several candidates (tie), no detection, or measurers disagree
  NOVEL    measurers agree and no truth subject matches
Consensus across measurers is an attestation claim ("this object is toy X");
every run is appended to the impact MMR (daisy/impact_mmr.jsonl).

Negative controls (deterministic, from the same renders):
  scaled_115  every toy printed 15% too large   -> expected NOVEL (or QUESTION)
  held_out    the toy's own subject removed from truth -> expected NOVEL or QUESTION
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from . import attest as A

POLICY = {"len_abs_mm": 0.3, "len_rel": 0.03, "area_rel": 0.12, "iou_known": 0.85, "iou_margin": 0.03}


# ------------------------------------------------------------ L6: outline shape

_REF = {}


def ref_silhouette(toy, length_mm, plan):
    """Exact top-view silhouette of the toy mesh (mm), from the frozen build spec."""
    if toy not in _REF:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union

        from .insect_kg import insect_tree
        m = insect_tree(length_mm, plan)[1]["_mesh"]
        tri = m.vertices[m.faces[m.face_normals[:, 2] > 1e-9]][:, :, :2]
        _REF[toy] = unary_union([Polygon(t) for t in tri if Polygon(t).area > 1e-12]).buffer(0)
    return _REF[toy]


def _canon(poly):
    """Centre on centroid and rotate so the min-area rectangle's long side is along x."""
    import math

    from shapely import affinity
    r = poly.minimum_rotated_rectangle
    xs = list(r.exterior.coords)[:4]
    e = max(((xs[i], xs[(i + 1) % 4]) for i in range(2)), key=lambda ab: math.dist(*ab))
    ang = math.degrees(math.atan2(e[1][1] - e[0][1], e[1][0] - e[0][0]))
    c = poly.centroid
    return affinity.rotate(affinity.translate(poly, -c.x, -c.y), -ang, origin=(0, 0))


def shape_iou(meas_poly_mm, ref_poly_mm):
    """Best IoU over the 4 flips of the canonical frames (orientation-free)."""
    from shapely import affinity
    a = _canon(meas_poly_mm); b = _canon(ref_poly_mm)
    best = 0.0
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        bb = affinity.scale(b, sx, sy, origin=(0, 0))
        u = a.union(bb).area
        best = max(best, a.intersection(bb).area / u if u else 0.0)
    return round(best, 4)


def truth_subjects(truth_path="daisy/TRUTH-001.json", kg="print/fuse1/kg"):
    t = json.loads(Path(truth_path).read_text())
    idx = {x["name"]: x for x in json.loads((Path(kg) / "index.json").read_text())}
    subs = []
    for s in t["subjects"]:
        o = idx[s["toy"]]["observation"]
        subs.append({"toy": s["toy"], "insect_hash": s["insect_hash"], "plan": s["plan"], "length_mm": s["length_mm"],
                     "top_L": max(o["envelope_mm"][:2]), "top_W": min(o["envelope_mm"][:2]), "top_area": o["top_area_mm2"]})
    return t["id"], subs


def candidates(meas, subs, pol=POLICY, exclude=None):
    out = []
    for s in subs:
        if exclude and s["toy"] == exclude:
            continue
        tolL = max(pol["len_abs_mm"], pol["len_rel"] * s["top_L"])
        tolW = max(pol["len_abs_mm"], pol["len_rel"] * s["top_W"])
        if (abs(meas["length_mm"] - s["top_L"]) <= tolL and abs(meas["width_mm"] - s["top_W"]) <= tolW
                and abs(meas["area_mm2"] - s["top_area"]) <= pol["area_rel"] * max(s["top_area"], 1.0)):
            out.append(s["toy"])
    return out


def decide(meas, subs, exclude=None, pol=POLICY):
    """L2 (size) narrows candidates; L6 (outline vs the toy's exact silhouette) decides."""
    if meas is None:
        return {"status": "QUESTION", "reason": "no detection", "toy": None, "candidates": []}
    c = candidates(meas, subs, pol, exclude=exclude)
    if not c:
        return {"status": "NOVEL", "toy": None, "candidates": [], "reason": "no truth subject matches size"}
    if meas.get("poly_mm") is None:
        return ({"status": "KNOWN", "toy": c[0], "candidates": c, "reason": "unique size match"} if len(c) == 1 else
                {"status": "QUESTION", "toy": None, "candidates": c, "reason": f"{len(c)} toys tie on size"})
    by = {s["toy"]: s for s in subs}
    ious = sorted(((shape_iou(meas["poly_mm"], ref_silhouette(t, by[t]["length_mm"], by[t]["plan"])), t) for t in c), reverse=True)
    top, t0 = ious[0]
    second = ious[1][0] if len(ious) > 1 else 0.0
    if top < pol["iou_known"]:
        return {"status": "NOVEL", "toy": None, "candidates": c, "ious": ious[:4], "reason": f"outline IoU {top} < {pol['iou_known']}"}
    if top - second < pol["iou_margin"]:
        return {"status": "QUESTION", "toy": None, "candidates": [t for i, t in ious if top - i < pol["iou_margin"]],
                "ious": ious[:4], "reason": "outline tie"}
    return {"status": "KNOWN", "toy": t0, "candidates": c, "ious": ious[:4], "reason": f"outline IoU {top}"}


def measure_contour(contour, ppm):
    if contour is None:
        return None
    from shapely.geometry import Polygon
    c = contour.reshape(-1, 1, 2).astype(np.float32)
    (_, _), (w, h), _ = cv2.minAreaRect(c)
    pts = c.reshape(-1, 2) / ppm
    poly = Polygon(pts).buffer(0) if len(pts) >= 3 else None
    return {"length_mm": round(max(w, h) / ppm, 3), "width_mm": round(min(w, h) / ppm, 3),
            "area_mm2": round(cv2.contourArea(c) / ppm ** 2, 3), "poly_mm": poly}


def calibrate(rows_meas, subs_by):
    """Leave-one-out bias per measurer x ppm: median (measured - truth) of the OTHER toys
    (a reference-set calibration, like a ruler). Returns fn(item_name, meas) -> corrected meas."""
    import statistics as st

    res = {}
    for name, toy, ppm, m in rows_meas:
        if m and toy in subs_by:
            s = subs_by[toy]
            res.setdefault((ppm,), []).append((name, m["length_mm"] - s["top_L"], m["width_mm"] - s["top_W"]))
    def fix(item, ppm, m):
        if m is None:
            return None
        others = [r for r in res.get((ppm,), []) if r[0] != item]
        if not others:
            return m
        dL = st.median(r[1] for r in others); dW = st.median(r[2] for r in others)
        out = dict(m); out["length_mm"] = round(m["length_mm"] - dL, 3); out["width_mm"] = round(m["width_mm"] - dW, 3)
        if m.get("poly_mm") is not None:            # shrink outline by the mean edge bias
            out["poly_mm"] = m["poly_mm"].buffer(-(dL + dW) / 4)
            out["area_mm2"] = round(out["poly_mm"].area, 3)
        out["bias_mm"] = [round(dL, 3), round(dW, 3)]
        return out
    return fix


def consensus(per_measurer, subs):
    """Measurer decisions -> one call. Disagreement on identity -> QUESTION."""
    calls = [d for d in per_measurer.values() if d]
    known = [d["toy"] for d in calls if d["status"] == "KNOWN"]
    novel = [d for d in calls if d["status"] == "NOVEL"]
    if known and len(set(known)) == 1 and len(known) >= max(1, len(calls) // 2 + (len(calls) % 2)):
        return {"status": "KNOWN", "toy": known[0]}
    if novel and len(novel) >= max(1, len(calls) // 2 + (len(calls) % 2)) and not known:
        return {"status": "NOVEL", "toy": None}
    return {"status": "QUESTION", "toy": None, "votes": {k: (d["status"], d["toy"]) for k, d in per_measurer.items()}}


def run(items, measurers, out_dir=None, truth_path="daisy/TRUTH-001.json", calibrate_bias=True):
    """items: [{"image", "ppm", "expected": {"status", "toy"}, "control", "exclude"}];
    measurers: {name: fn(img, ppm) -> contour or None}."""
    from .model_compare import render  # noqa: F401  (renders are produced by callers)
    tid, subs = truth_subjects(truth_path)
    by = {s["toy"]: s for s in subs}
    raw = []
    for it in items:
        img = it.get("img") if it.get("img") is not None else cv2.imread(str(it["image"]))
        ms = {}
        for name, fn in measurers.items():
            try:
                ms[name] = measure_contour(fn(img, it["ppm"]), it["ppm"])
            except Exception:  # noqa: BLE001 - fallback; the failure is recorded or degrades
                ms[name] = None
        raw.append((it, ms))
    fixers = {}
    for name in measurers:          # calibration only on true toys (control "toy@...") of the reference set
        fixers[name] = calibrate([(it.get("name"), it["expected"]["toy"], it["ppm"], ms[name]) for it, ms in raw
                                  if it.get("control", "").startswith("toy@")], by) if calibrate_bias else (lambda n, p, m: m)
    rows = []
    for it, ms in raw:
        per = {}
        for name in measurers:
            base = (it.get("name") or "").split(":")[0]
            m = fixers[name](base, it["ppm"], ms[name])
            d = decide(m, subs, exclude=it.get("exclude"))
            d["measurement"] = {k: v for k, v in (m or {}).items() if k != "poly_mm"} if m else None
            per[name] = d
        con = consensus(per, subs)
        exp = it["expected"]
        ok = lambda d, exp=exp: d["status"] == exp["status"] and (exp["status"] != "KNOWN" or d["toy"] == exp["toy"]) \
            if exp["status"] != "NOT_KNOWN" else d["status"] != "KNOWN"
        rows.append({"item": it.get("name") or Path(str(it.get("image"))).stem, "control": it.get("control", "toy"),
                     "expected": exp, "per": per, "consensus": con,
                     "correct": {**{k: ok(d) for k, d in per.items()}, "consensus": ok(con)}})
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        Path(out_dir, "toy_triage.jsonl").write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))
    return tid, rows


def summary(rows):
    out = {}
    for r in rows:
        for k, v in r["correct"].items():
            s = out.setdefault((r["control"], k), [0, 0]); s[0] += v; s[1] += 1
    calls = {}
    for r in rows:
        for k, d in list(r["per"].items()) + [("consensus", r["consensus"])]:
            c = calls.setdefault((r["control"], k), {}); c[d["status"]] = c.get(d["status"], 0) + 1
    return {f"{c}|{m}": {"correct": f"{v[0]}/{v[1]}", "calls": calls[(c, m)]} for (c, m), v in sorted(out.items())}


def render_items(ppms=(10, 20), kg="print/fuse1/kg"):
    """Toy renders + negative controls from the frozen toy KG."""
    from .model_compare import render
    idx = json.loads((Path(kg) / "index.json").read_text())
    items = []
    for ppm in ppms:
        for x in idx:
            img = render(x["length_mm"], x["plan"], ppm)
            items.append({"name": f"{x['name']}@{ppm}", "img": img, "ppm": ppm, "control": f"toy@{ppm}",
                          "expected": {"status": "KNOWN", "toy": x["name"]}})
            items.append({"name": f"{x['name']}@{ppm}:held_out", "img": img, "ppm": ppm, "control": f"held_out@{ppm}",
                          "exclude": x["name"], "expected": {"status": "NOT_KNOWN", "toy": None}})
            big = render(min(30.0, x["length_mm"]) * 1.15, x["plan"], ppm)
            items.append({"name": f"{x['name']}@{ppm}:scaled_115", "img": big, "ppm": ppm, "control": f"scaled_115@{ppm}",
                          "expected": {"status": "NOT_KNOWN", "toy": None}})
    return items


def append_mmr(tid, rows, measurer_meta, values="toy_triage_v1"):
    """One MMR event per measurer (+ consensus) with the triage attestation root."""
    from .mmr import MMRLog
    log = MMRLog("daisy/impact_mmr.jsonl")
    for name in list(rows[0]["per"]) + ["consensus"]:
        who = A.actor("measurer" if name != "consensus" else "agent", f"toy-triage:{name}",
                      measurer_meta.get(name), key=measurer_meta.get(name))
        leaves = []
        for r in rows:
            d = r["consensus"] if name == "consensus" else r["per"][name]
            c = A.claim({"truth": tid, "item": r["item"]}, "object triage against TRUTH-001", "baebugs.toy_triage.decide",
                        {"status": r["expected"]["status"], "toy": r["expected"]["toy"]}, {"abs": 0.0},
                        {"deterministic_required": False, "min_agents": 1, "quorum": 0.5})
            obs = {"status": "NOT_KNOWN" if (r["expected"]["status"] == "NOT_KNOWN" and d["status"] != "KNOWN") else d["status"],
                   "toy": d.get("toy") if r["expected"]["status"] == "KNOWN" else None}
            leaves.append(A.attest(c, who, obs, t=0))
        by = {}
        for r in rows:
            s = by.setdefault(r["control"], [0, 0]); s[0] += r["correct"][name]; s[1] += 1
        log.append({"type": "evaluation", "truth_id": tid, "actor": {"id": who["id"], "name": who["name"], "kind": who["kind"]},
                    "weights": measurer_meta.get(name), "values": values, "values_hash": A.H(POLICY), "policy": POLICY,
                    "n": len(leaves), "pass": sum(l["within_policy"] for l in leaves),
                    "attestation_root": A.merkle_root(sorted(l["leaf"] for l in leaves)),
                    "by_control": {k: f"{v[0]}/{v[1]}" for k, v in by.items()}, "passed": {}, "impact": {}})
    return log
