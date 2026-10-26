"""Multi-tier sieve tower twin: first spill photo -> which filter trays the arm
mounts in the active tiers -> emulated arm/rail actions, checked before any move.

Hardware (BioKEA bench): a wooden post with cantilevered plywood rail arms on two
faces (levels staggered by half a pitch). STORAGE face = parked trays; FILTER face =
a couple of active tiers over a catch tray on the lowest level, water from the top;
overflow trays sit in a bench rack. Trays are printed 2x3 frames with side
handles that slide in and out along the rail arms; a Partabot servo arm on a linear
rail moves them with a fork. Geometry: config/tower.yaml (MEASURE placeholders).

1. objects  from the spill photo (vision lane: length, width per detection)
2. passage  each object is an ellipsoid L x W x H (H = 0.8 W unless known); for
            each filter its flat / side / end-on silhouettes are tested against the
            hole shape (shapely, same fit test as the mesh passage twin), weighted
            by how likely shaking/flow finds that orientation -> P(pass)
3. plan     choose and order k trays (coarse -> fine, top -> bottom) from what is
            in the tower to maximise expected fraction purity over the size classes
            (config/insects.yaml), penalising uncertain passage; objects no filter can
            separate are flagged VIP for a human
4. emulate  arm + rail discrete-event run: fetch tray from storage slot, insert in
            filter tier, pour, rinse, pull each tier to the camera station, return.
            Preflight fails closed (reach, slot occupancy, order, catch tray, water).
            Every action is a Merkle leaf; the plan root identifies the run.

  python -m baebugs.tower_twin plan --objects objects.jsonl
  python -m baebugs.tower_twin demo
"""
from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass, field
from pathlib import Path

from shapely import affinity
from shapely.geometry import Point

from . import punch_filters as PF
from .explore import merkle_root
from .sieve import classify, load_yaml

# ------------------------------------------------------------------ filters

def tower_inventory(extra_ids=("SS-PERF-3.2", "SS-SLOT-3.2x19", "SS-PERF-6.4", "SS-MESH-1.0")):
    """Trays physically available: the kit (from sieves.yaml) + rack options."""
    kit = load_yaml("sieves.yaml")
    shape_of = {"perforated_round": "circle", "printed_square": "square", "hex_wire": "hexagon",
                "woven_screen": "square"}
    inv = []
    for s in kit["sieves"]:
        if s["aperture_mm"] <= 0:
            inv.append({"id": s["id"], "kind": "catch", "entry": None, "source": "kit"}); continue
        sh = shape_of.get(s["kind"], "circle")
        key = {"circle": "d", "square": "s", "hexagon": "across_flats"}[sh]
        inv.append({"id": s["id"], "kind": "filter", "source": "kit",
                    "entry": (s["id"], "kit", "kit", sh, {key: s["aperture_mm"]}, s.get("note", ""))})
    lib = {e[0]: e for e in PF.LIBRARY}
    for fid in extra_ids:
        if fid in lib:
            inv.append({"id": fid, "kind": "filter", "source": "rack", "entry": lib[fid]})
    for it in inv:
        if it["entry"]:
            h = PF.hole(it["entry"])
            it["hole"], it["metrics"] = h, PF.hole_metrics(h)
    return inv


def _ellipse(a, b):
    return affinity.scale(Point(0, 0).buffer(1.0, 48), a / 2, b / 2)


def p_pass(obj, filt, cfg):
    """P(object passes the filter) from ellipsoid silhouettes x orientation weights."""
    from .passage_twin import fits
    L, W = obj["length_mm"], obj["width_mm"]
    H = obj.get("height_mm") or W * cfg["passage"]["height_over_width"]
    w = cfg["passage"]["orientation_weight"]
    views = {"flat": _ellipse(L, W), "side": _ellipse(L, H), "end_on": _ellipse(W, H)}
    best = 0.0
    for name in ("flat", "side", "end_on"):
        if fits(views[name], filt["hole"], filt["metrics"]):
            best = max(best, w[name])
    return best


# ----------------------------------------------------------------- planning

def plan_tiers(objects, inventory=None, cfg=None, k=None):
    """Exhaustive search over ordered k-subsets of available filters."""
    cfg = cfg or load_yaml("tower.yaml")
    inv = inventory or tower_inventory()
    k = k or cfg["tower"]["filter_face"]["active_tiers"]
    classes = load_yaml("insects.yaml")["classes"]
    filters = [f for f in inv if f["kind"] == "filter"]
    cls = [classify(o["width_mm"], classes) for o in objects]
    names = sorted(set(cls))
    P = {f["id"]: [p_pass(o, f, cfg) for o in objects] for f in filters}
    best = []
    for combo in itertools.combinations(filters, k):
        order = sorted(combo, key=lambda f: -f["metrics"]["inscribed_d_mm"])   # coarse on top
        frac = [{} for _ in range(k + 1)]          # tier 0..k-1, k = catch tray
        unc = 0.0
        for i, c in enumerate(cls):
            reach = 1.0
            for t, f in enumerate(order):
                p = P[f["id"]][i]
                stay = reach * (1 - p)
                frac[t][c] = frac[t].get(c, 0) + stay
                unc += reach * p * (1 - p)
                reach *= p
            frac[k][c] = frac[k].get(c, 0) + reach
        n = max(len(objects), 1)
        purity = sum(max(f.values()) for f in frac if f) / n
        used = sum(1 for f in frac if sum(f.values()) > 0.05 * n)
        score = purity - 0.5 * unc / n + 0.02 * used
        best.append({"tiers": [f["id"] for f in order], "score": round(score, 4), "purity": round(purity, 4),
                     "uncertainty": round(unc / n, 4), "fractions_used": used,
                     "fractions": [{c: round(v, 1) for c, v in sorted(f.items())} for f in frac]})
    best.sort(key=lambda b: -b["score"])
    # VIP: objects no available filter retains AND no filter passes with confidence -> human
    vip = []
    for i, o in enumerate(objects):
        ps = [P[f["id"]][i] for f in filters]
        if all(0.05 < p < 0.95 for p in ps) or o["length_mm"] > 30 or o["length_mm"] < 1:
            vip.append({"index": i, **{k2: o[k2] for k2 in ("length_mm", "width_mm")}, "class": cls[i],
                        "reason": "outside 1-30 mm" if (o["length_mm"] > 30 or o["length_mm"] < 1) else "no filter separates it confidently"})
    return {"best": best[0] if best else None, "alternatives": best[1:4], "classes": names,
            "class_counts": {c: cls.count(c) for c in names}, "vip": vip, "n_objects": len(objects)}


# ---------------------------------------------------------------- emulation

class PreflightError(Exception):
    pass


@dataclass
class TowerState:
    storage: dict = field(default_factory=dict)       # "A<level>" (storage face) or "R<n>" (bench rack) -> tray id
    filter_side: dict = field(default_factory=dict)   # filter-face level -> tray id
    holding: str | None = None
    rail_x: float = 0.0
    water_l: float = 5.0


def initial_state(cfg, inventory):
    st = TowerState()
    T = cfg["tower"]
    spots = [f"A{l}" for l in range(T["levels_per_face"])] + [f"R{i}" for i in range(cfg["bench_rack"]["slots"])]
    catch = next((f["id"] for f in inventory if f["kind"] == "catch"), None)
    k = 0
    for f in inventory:
        if f["id"] == catch:
            st.filter_side[T["filter_face"]["catch_level"]] = f["id"]
        elif k < len(spots):
            st.storage[spots[k]] = f["id"]; k += 1
    st.water_l = load_yaml("sieves.yaml")["water"]["reservoir_l"]
    return st


def slot_z(cfg, level, face="filter"):
    T = cfg["tower"]
    return T["first_level_z_mm"] + level * T["level_pitch_mm"] + (T["stagger_mm"] if face == "filter" else 0.0)


def spot_x(cfg, spot):
    return cfg["bench_rack"]["x_mm"] if str(spot).startswith("R") else cfg["tower"]["x_mm"]


def actions_for(plan, cfg, state):
    """Arm program for one run (top tier first so the stack builds coarse -> fine)."""
    k = len(plan["tiers"])
    catch = cfg["tower"]["filter_face"]["catch_level"]
    tiers = {catch + k - i: tid for i, tid in enumerate(plan["tiers"])}        # coarse highest
    acts = []
    for slot in sorted(tiers, reverse=True):
        tid = tiers[slot]
        src = next((s for s, t in state.storage.items() if t == tid), None)
        acts += [("fetch", {"tray": tid, "from_storage": src}), ("insert", {"tray": tid, "filter_slot": slot})]
    acts += [("pour", {"z_mm": cfg["tower"]["filter_face"]["pour_z_mm"]}),
             ("rinse", {"litres": round(cfg["water"]["rinse_l_per_tier"] * (k + 1), 3)})]
    for slot in sorted(tiers, reverse=True) + [catch]:
        tid = tiers.get(slot, state.filter_side.get(slot))
        home = next((s for s, t in state.storage.items() if t == tid), None)
        acts += [("pull", {"tray": tid, "filter_slot": slot}), ("image", {"tray": tid}),
                 ("return", {"tray": tid, "to": home if slot != catch else f"filter level {catch}"})]
    return acts


def emulate(acts, cfg, state, inventory):
    """Discrete-event run with preflight. Returns (log, seconds). Raises on violation."""
    A, T = cfg["arm"], cfg["tower"]
    ap = {f["id"]: f.get("metrics", {}).get("inscribed_d_mm", 0.0) for f in inventory}
    errs = []
    # preflight: order, occupancy, reach, catch, water
    ins = [(p["filter_slot"], p["tray"]) for a, p in acts if a == "insert"]
    by_height = [ap[t] for _, t in sorted(ins, reverse=True)]
    if by_height != sorted(by_height, reverse=True):
        errs.append("stack not coarse->fine top->bottom")
    if len(ins) + 1 > T["levels_per_face"]:
        errs.append(f"{len(ins)} tiers + catch exceed {T['levels_per_face']} filter-face levels")
    for s, t in ins:
        if s in state.filter_side:
            errs.append(f"filter slot {s} occupied by {state.filter_side[s]}")
        z = slot_z(cfg, s, "filter")
        if not (A["min_z_mm"] <= z <= A["max_z_mm"]):
            errs.append(f"slot {s} at z={z} outside arm range")
    if T["filter_face"]["catch_level"] not in state.filter_side:
        errs.append("no catch tray")
    for a, p in acts:
        if a == "fetch" and p["from_storage"] is None:
            errs.append(f"{p['tray']} not in storage")
    need = sum(p["litres"] for a, p in acts if a == "rinse")
    if state.water_l - need < load_yaml("sieves.yaml")["water"]["min_reserve_l"]:
        errs.append(f"water: need {need} L")
    if errs:
        raise PreflightError("; ".join(errs))
    log, t = [], 0.0
    fs = dict(state.filter_side)

    def move_to(x):
        nonlocal t
        d = abs(x - state.rail_x); state.rail_x = x; t += d / A["rail_speed_mm_s"] + A["joint_move_s"]

    slide = cfg["tray"]["insert_depth_mm"] / A["slide_speed_mm_s"]
    face = "storage"
    for a, p in acts:
        if a in ("fetch", "return"):
            spot = p.get("from_storage") or p.get("to")
            move_to(spot_x(cfg, spot))
            if not str(spot).startswith("R") and face != "storage":
                t += A["face_turn_s"]; face = "storage"
            t += slide
        if a in ("insert", "pull"):
            move_to(T["x_mm"])
            if face != "filter":
                t += A["face_turn_s"]; face = "filter"
            t += slide
        if a == "insert":
            fs[p["filter_slot"]] = p["tray"]
        if a == "pull":
            fs.pop(p["filter_slot"], None)
        if a == "image":
            move_to(cfg["camera_station"]["x_mm"]); t += 2.0
        if a == "pour":
            t += cfg["water"]["pour_s"]
        if a == "rinse":
            state.water_l -= p["litres"]; t += 10.0 * p["litres"] / 0.25
        rec = {"t_s": round(t, 1), "action": a, **p}
        rec["leaf"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
        log.append(rec)
    return log, round(t, 1)


def run(objects, k=None, cfg=None):
    cfg = cfg or load_yaml("tower.yaml")
    inv = tower_inventory()
    pl = plan_tiers(objects, inv, cfg, k)
    st = initial_state(cfg, inv)
    acts = actions_for(pl["best"], cfg, st)
    log, secs = emulate(acts, cfg, st, inv)
    return {"plan": pl, "actions": log, "seconds": secs, "run_root": merkle_root([r["leaf"] for r in log]),
            "geometry_status": "PLACEHOLDER (config/tower.yaml MEASURE values)"}


def demo_objects():
    """Food-analog spill (the bench test, not insects): sizes from the analog test."""
    import random
    rnd = random.Random(7)
    spec = [("ditalini", 30, (7.0, 6.0)), ("red rice", 40, (5.3, 2.4)), ("white rice", 60, (6.5, 2.3)),
            ("wild rice", 15, (13.0, 1.6)), ("chia", 80, (2.1, 1.3)), ("couscous", 60, (1.5, 1.2))]
    out = []
    for name, n, (L, W) in spec:
        for _ in range(n):
            out.append({"label": name, "length_mm": round(L * rnd.uniform(0.85, 1.15), 2),
                        "width_mm": round(W * rnd.uniform(0.85, 1.15), 2)})
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-tower")
    ap.add_argument("cmd", choices=["plan", "demo"])
    ap.add_argument("--objects", help="jsonl with length_mm, width_mm (e.g. BugPicker objects.jsonl from baebugs)")
    ap.add_argument("--tiers", type=int)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    objs = demo_objects() if a.cmd == "demo" else [json.loads(l) for l in Path(a.objects).read_text().splitlines() if l.strip()]
    r = run(objs, a.tiers)
    b = r["plan"]["best"]
    print(f"{r['plan']['n_objects']} objects, classes {r['plan']['class_counts']}")
    print(f"mount (top->bottom): {b['tiers']} + catch | purity {b['purity']} uncertainty {b['uncertainty']}")
    for i, f in enumerate(b["fractions"]):
        print(f"  {'tier ' + str(i + 1) if i < len(b['tiers']) else 'catch '}: {f}")
    print(f"emulated run {r['seconds']} s, {len(r['actions'])} actions, root {r['run_root'][:16]}, VIP {len(r['plan']['vip'])}")
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1, default=str))


if __name__ == "__main__":
    main()
