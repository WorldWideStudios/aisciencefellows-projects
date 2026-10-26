"""gatecalc: geometry-only passability calculator for printed sieve gates (BugSorter tower).

Turns a sample spec (TOML) into one gate per tower level before any simulation, checks a given
gate sequence, checks whether items fit a 96-well plate, and summarises sim runs (sim/sorter.py
results.json) against the same rules. Stdlib + numpy only.

Run with the repo venv (Windows):  .venv\Scripts\python.exe
    gatecalc.py plan  SPEC.toml [--log LOG.md] [--json plan.json]
    gatecalc.py check SPEC.toml --gates w2.4,t1.4 [--effective] [--log LOG.md]
    gatecalc.py item  6.5x2.0x1.7 [more items] [--gates w2.0,t1.4] [--plate std96_flat,deep96_square_2ml]
    gatecalc.py sim   RUN_DIR_or_results.json [...] [--log LOG.md]

Sample run (2026-10-24, templates/sample-spec.toml, pantry grains): L1 t3.65 effective (print t3.8),
L2 t1.4 effective (print t1.55), quinoa in the catch; 100% predicted recovery per class, worst case
4.9 misroutes of 60 at L2. Output is markdown; --log appends it to a run log.

Model (derivation and sources: references/passability.md, references/well-fit.md)
  Items are rigid, roughly elliptical in cross-section, dims L >= W >= T (body only; appendage
  span is checked separately). They pass a gate end-first, so LENGTH NEVER LIMITS A GATE.
  Shaking lays items flat (T vertical); rolling onto an edge is possible but not the resting
  pose, so every gate gives two answers:
    flat  passes in the resting pose
    any   passes at some roll angle. For a rectangular opening a across x b up and an elliptical
          cross-section W x T this is exact:  T < min(a, b)  and  W^2 + T^2 < a^2 + b^2
  An item that passes "any" but not "flat" passes with probability p_roll (spec [rules]).
  Gate tokens (first number = the cut, optional second after "x"):
    w<s>[x<H>]   width gaps s wide, H tall (default 8: gated_container and pool w strips)
    p<g>[x<H>]   pillar comb, clear gap g (same geometry as w, two-point contact)  PROPOSAL
    win<s>x<h>   window: a w gap with its height capped at h                         PROPOSAL
    t<h>[x<Wt>]  tunnels h tall, Wt wide (default 8: t strips)
    sq<a>        square floor hole (sieve_insert.py): aligned W < a; diagonal sqrt((W^2+T^2)/2) < a
    o<d>         round hole: W < d                                                    PROPOSAL in the holder tower
    slot<g>      long floor slot or rod gap (plinko, round_stack): T < g
  --gates sizes are NOMINAL (as drawn in CAD); the printed opening is nominal minus the spec's
  [print] undersize (or read off its hole-gauge table) unless --effective is given.
"""
import argparse
import csv
import datetime as dt
import json
import math
import re
import sys
import tomllib
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
SIM_DIR = REPO / "sim"
PY = str(REPO / ".venv" / "Scripts" / "python.exe")

# Inner well geometry, mm: shape, top inner size, bottom inner size, depth, max volume uL.
# Sources and caveats: references/well-fit.md. Override any of these in the spec's [well] table.
PLATES = {
    "std96_flat": ("round", 6.96, 6.39, 10.9, 382),           # Greiner 655101 F-bottom (Corning 3595: 6.86/6.35, 10.67)
    "std96_round": ("round", 6.94, 5.5, 10.3, 323),           # Greiner 650101 U-bottom; bottom 5.5 ASSUMED for the hemisphere
    "pcr96": ("round", 5.46, 2.64, 14.81, 200),               # Bio-Rad HSP96 skirted PCR plate, conical well
    "deep96_round_1ml": ("round", 7.0, 5.97, 38.2, 1220),     # Greiner 780261 MASTERBLOCK 1 mL, U-bottom
    "deep96_square_2ml": ("square", 8.2, 7.37, 41.0, 2420),   # Greiner 780270 MASTERBLOCK 2 mL, V-bottom
}

DEFAULTS = {"undersize_mm": 0.15, "tolerance_mm": 0.10, "pass_clearance_mm": 0.15, "block_margin_mm": 0.10,
            "p_roll": 0.5, "w_height_mm": 8.0, "t_width_mm": 8.0, "min_mm": 0.8, "max_mm": 12.0,
            "step_mm": 0.05, "samples": 4000, "seed": 1, "near_band_mm": 0.15, "gate_menu": ["w", "t"],
            "sim_max_particles": 80}
GATE_RE = re.compile(r"^(win|slot|sq|w|p|t|o)(\d+(?:\.\d+)?)(?:x(\d+(?:\.\d+)?))?$")


# ----------------------------------------------------------------------------- gates

def parse_gates(text, rules):
    out = []
    for tok in filter(None, (s.strip() for s in text.split(","))):
        m = GATE_RE.match(tok)
        if not m:
            raise SystemExit(f"bad gate {tok!r}: use w2.4, t1.4, p2.4, win2.4x3, sq2.0, o6.0, slot1.4")
        kind, a, b = m.group(1), float(m.group(2)), m.group(3)
        if kind == "win" and b is None:
            raise SystemExit(f"{tok}: a window needs its height, e.g. win2.4x3.0")
        second = float(b) if b else (rules["t_width_mm"] if kind == "t" else rules["w_height_mm"])
        out.append({"kind": kind, "size": a, "second": second})
    return out


def gate_label(g, size=None):
    s = g["size"] if size is None else size
    extra = f"x{g['second']:g}" if g["kind"] == "win" or (g["kind"] in ("w", "p") and g["second"] != 8.0) else ""
    return f"{g['kind']}{s:g}{extra}"


def cad_name(kind, s):
    txt = f"{s:.2f}".rstrip("0")
    txt = txt + "0" if txt.endswith(".") else txt
    return f"{kind}{txt.replace('.', 'p')}"


def passes(kind, s, second, W, T):
    """(flat, any) boolean arrays: does each item pass an opening of effective size s?"""
    if kind in ("w", "p", "win", "t", "rect"):
        a, b = (second, s) if kind == "t" else (s, second)     # a across, b up
        flat = (W < a) & (T < b)
        anyp = (T < min(a, b)) & (W * W + T * T < a * a + b * b)
    elif kind == "sq":
        flat = W < s
        anyp = np.minimum(W, np.sqrt((W * W + T * T) / 2)) < s
    elif kind == "o":
        flat = anyp = W < s
    elif kind == "slot":
        flat = anyp = T < s
    else:
        raise ValueError(kind)
    return flat, flat | anyp


def p_pass(kind, s, second, W, T, p_roll):
    flat, anyp = passes(kind, s, second, W, T)
    return np.where(flat, 1.0, np.where(anyp, p_roll, 0.0))


def control_dim(kind, W, T):
    """The dimension that decides a resting item at this gate (for near-size and clearance)."""
    return T if kind in ("t", "slot") else W


# ----------------------------------------------------------------------------- print correction

def make_print(spec):
    p = spec.get("print", {})
    under = float(p.get("undersize_mm", DEFAULTS["undersize_mm"]))
    gauge = sorted((float(n), float(m)) for n, m in p.get("gauge", []))
    def to_nominal(eff):
        if len(gauge) >= 2:
            nom, meas = np.array(gauge).T
            if eff < meas[0]:
                return eff + (nom[0] - meas[0])
            if eff > meas[-1]:
                return eff + (nom[-1] - meas[-1])
            return float(np.interp(eff, meas, nom))
        return eff + under
    def to_effective(nom):
        if len(gauge) >= 2:
            n, m = np.array(gauge).T
            if nom < n[0]:
                return nom - (n[0] - m[0])
            if nom > n[-1]:
                return nom - (n[-1] - m[-1])
            return float(np.interp(nom, n, m))
        return nom - under
    src = f"hole-gauge table ({len(gauge)} points)" if len(gauge) >= 2 else f"flat undersize {under:g} mm"
    return to_nominal, to_effective, src, float(p.get("tolerance_mm", DEFAULTS["tolerance_mm"]))


# ----------------------------------------------------------------------------- items

def dim_draw(v, n, rng, name):
    if isinstance(v, (int, float)):
        return np.full(n, float(v))
    if isinstance(v, list) and len(v) == 2:          # [lo, hi]: truncated normal, mean mid, sd = range / 4
        lo, hi = sorted(map(float, v))
        mean, sd, lim = (lo + hi) / 2, max((hi - lo) / 4, 1e-6), (lo, hi)
    elif isinstance(v, dict) and "mean" in v:
        mean, sd = float(v["mean"]), float(v.get("sd", 0.0)) or 1e-6
        lim = (max(0.02, mean - 3 * sd), mean + 3 * sd)
    else:
        raise SystemExit(f"{name}: give a number, [lo, hi] or {{mean = .., sd = ..}}")
    x = rng.normal(mean, sd, n)
    for _ in range(30):
        bad = (x < lim[0]) | (x > lim[1])
        if not bad.any():
            break
        x[bad] = rng.normal(mean, sd, bad.sum())
    return np.clip(x, *lim)


def sim_draw(kind, n, rng):
    """Dims from the sim's own particle generator (sim/grains.py, sim/insects.py), read-only."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(SIM_DIR))
    try:
        mod = __import__("insects" if kind.startswith("insect_") else "grains")
        dims = [mod.make(kind, rng).dims for _ in range(n)]
    except Exception as e:                            # the sim is edited by another session
        raise SystemExit(f"could not draw {kind} from sim/: {type(e).__name__}: {e}")
    return {k: np.array([d[k] for d in dims], float) for k in ("length", "width", "thickness", "span")}


def draw_item(it, n, rng, base):
    name = it["name"]
    if it.get("source") == "sim":
        d = sim_draw(it["sim_kind"], min(n, 1500), rng)
        L, W, T, S = d["length"], d["width"], d["thickness"], d["span"]
    elif "measured" in it:                            # bootstrap whole rows (keeps L/W/T correlated)
        path = (base / it["measured"]).resolve()
        want = it.get("measured_kind", name)
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = [r for r in csv.DictReader(f) if r.get("kind", "").strip() == want]
        if not rows:
            raise SystemExit(f"{name}: no rows with kind == {want!r} in {path}")
        a = np.array([[float(r["length_mm"]), float(r["width_mm"]), float(r["thickness_mm"])] for r in rows])
        a = np.sort(a[rng.integers(0, len(a), n)], axis=1)[:, ::-1]
        L, W, T = a.T
        S = dim_draw(it["span"], n, rng, name) if "span" in it else L.copy()
    else:
        cols = [dim_draw(it[k], n, rng, f"{name}.{k}") for k in ("length", "width", "thickness")]
        L, W, T = np.sort(np.stack(cols), axis=0)[::-1]
        S = dim_draw(it["span"], n, rng, name) if "span" in it else L.copy()
    return {"L": L, "W": W, "T": T, "S": np.maximum(S, L)}


# ----------------------------------------------------------------------------- well fit

def plate_of(spec):
    w = spec.get("well", {})
    base = PLATES.get(w.get("plate", "std96_flat"))
    if base is None and "shape" not in w:
        raise SystemExit(f"unknown plate {w.get('plate')!r}: use one of {list(PLATES)} or give shape/top/bottom/depth")
    shape, top, bot, depth, vol = base or (None,) * 5
    p = {"name": w.get("plate", "custom"), "shape": w.get("shape", shape), "top": float(w.get("top_mm", top)),
         "bottom": float(w.get("bottom_mm", bot)), "depth": float(w.get("depth_mm", depth)),
         "margin": float(w.get("margin_mm", 0.3)), "require": w.get("require", "below_rim"),
         "accept_lean": bool(w.get("accept_lean", True)), "fill_ul": w.get("fill_ul")}
    area = math.pi * p["bottom"] ** 2 / 4 if p["shape"] == "round" else p["bottom"] ** 2
    p["fill_h"] = min(p["depth"], float(p["fill_ul"]) / area) if p["fill_ul"] else p["depth"]
    p["height"] = p["fill_h"] if p["require"] == "submerged" else p["depth"]
    return p


def well_fit(L, W, T, p):
    """'flat' (lies on the bottom), 'leans' (fits tilted, below the rim or the liquid), 'no'."""
    top, bot, H = p["top"] - p["margin"], p["bottom"] - p["margin"], p["height"]
    sq = p["shape"] == "square"
    enter = (np.minimum(W, np.sqrt((W * W + T * T) / 2)) if sq else W) <= top   # cross-section through the mouth
    flat = ((L <= bot) | (L <= math.sqrt(2) * bot - W)) if sq else (L * L + W * W <= bot * bot)
    flat &= T <= H
    reach = math.sqrt(2) * bot if sq else bot          # widest horizontal line across the bottom
    a = np.radians(np.linspace(0, 90, 91))[:, None]    # lean angle; T lies in the lean plane
    lean = ((L * np.cos(a) + T * np.sin(a) <= reach) & (L * np.sin(a) + T * np.cos(a) <= H)).any(axis=0)
    return np.where(~enter, "no", np.where(flat, "flat", np.where(lean, "leans", "no")))


def fits_well(cat, p):
    return (cat == "flat") | ((cat == "leans") & p["accept_lean"])


# ----------------------------------------------------------------------------- population

def population(spec, base):
    rules = {**DEFAULTS, **spec.get("rules", {})}
    rules["tolerance_mm"] = float(spec.get("print", {}).get("tolerance_mm", DEFAULTS["tolerance_mm"]))
    rng = np.random.default_rng(int(rules["seed"]))
    plate = plate_of(spec)
    items, cols = [], {k: [] for k in ("L", "W", "T", "S", "item", "wt", "cat")}
    for it in spec.get("item", []):
        d = draw_item(it, int(rules["samples"]), rng, base)
        n = len(d["L"])
        cat = well_fit(d["L"], d["W"], d["T"], plate)
        items.append({**it, "n": n})
        for k in ("L", "W", "T", "S"):
            cols[k].append(d[k])
        cols["item"].append(np.full(n, len(items) - 1))
        cols["wt"].append(np.full(n, float(it.get("count", 1)) / n))
        cols["cat"].append(cat)
    if not items:
        raise SystemExit("spec has no [[item]] entries")
    pop = {k: np.concatenate(v) for k, v in cols.items()}
    classes = spec.get("class", [])
    cls = np.full(len(pop["L"]), -1)
    for ci, c in enumerate(classes):
        names = c.get("items")
        m = np.isin(pop["item"], [i for i, it in enumerate(items) if names is None or it["name"] in names])
        if "well" in c:
            ok = fits_well(pop["cat"], plate)
            m &= ok if c["well"] == "fits" else ~ok
        for key, col in (("length", "L"), ("width", "W"), ("thickness", "T")):
            if f"min_{key}" in c:
                m &= pop[col] >= float(c[f"min_{key}"])
            if f"max_{key}" in c:
                m &= pop[col] <= float(c[f"max_{key}"])
        cls = np.where((cls < 0) & m, ci, cls)
    pop["cls"] = cls
    return pop, items, classes, rules, plate


def route(pop, gates, rules, p_roll):
    """Expected fraction of each sample retained at each level (gates) and in the catch (last)."""
    reach = np.ones(len(pop["L"]))
    out = []
    for g in gates:
        pp = p_pass(g["kind"], g["eff"], g["second"], pop["W"], pop["T"], p_roll)
        out.append(reach * (1 - pp))
        reach = reach * pp
    return out + [reach]


# ----------------------------------------------------------------------------- planning

def choose_gate(pop, reach, k, rules, tol, menu):
    """Best gate for level k: keeps class k, passes classes below it. Returns (gate, alternatives)."""
    w = reach * pop["wt"]
    keep, pass_ = (pop["cls"] == k) & (w > 0), (pop["cls"] > k) & (w > 0)
    sizes = np.round(np.arange(rules["min_mm"], rules["max_mm"] + 1e-9, rules["step_mm"]), 3)
    pr, clear, margin = rules["p_roll"], rules["pass_clearance_mm"], rules["block_margin_mm"]
    eps = max(0.05, 0.002 * w[keep | pass_].sum())
    best = []
    for kind in menu:
        second = rules["t_width_mm"] if kind == "t" else rules["w_height_mm"]
        score = np.empty(len(sizes))
        for j, s in enumerate(sizes):
            leak = p_pass(kind, s + tol + margin, second, pop["W"][keep], pop["T"][keep], pr)
            blk = 1 - p_pass(kind, s - tol - clear, second, pop["W"][pass_], pop["T"][pass_], pr)
            score[j] = (w[keep] * leak).sum() + (w[pass_] * blk).sum()
        j0 = int(np.argmin(score))
        lo = hi = j0
        while lo > 0 and score[lo - 1] <= score[j0] + eps:
            lo -= 1
        while hi < len(sizes) - 1 and score[hi + 1] <= score[j0] + eps:
            hi += 1
        jm = (lo + hi) // 2
        best.append({"kind": kind, "eff": float(sizes[jm]), "second": second, "score": float(score[jm]),
                     "window": [float(sizes[lo]), float(sizes[hi])]})
    best.sort(key=lambda b: (round(b["score"], 2), -(b["window"][1] - b["window"][0])))
    return best[0], best[1:]


def level_report(pop, reach, k, g, rules, tol):
    """Leak of the kept class, blocked passers, near-size and on-edge counts at one gate."""
    w = reach * pop["wt"]
    keep, pass_ = (pop["cls"] == k) & (w > 0), (pop["cls"] > k) & (w > 0)
    W, T = pop["W"], pop["T"]
    flat, anyp = passes(g["kind"], g["eff"], g["second"], W, T)
    roll = anyp & ~flat
    near = np.abs(control_dim(g["kind"], W, T) - g["eff"]) < rules["near_band_mm"]
    snag = (g["kind"] in ("w", "p", "win")) & (pop["S"] > pop["L"] * 1.05) & (pop["S"] > g["eff"] + 1) & flat
    return {"keep_n": w[keep].sum(), "pass_n": w[pass_].sum(),
            "leak_flat": w[keep & flat].sum(), "leak_roll": w[keep & roll].sum(),
            "blocked": w[pass_ & ~anyp].sum(), "blocked_roll": w[pass_ & roll].sum(),
            "near": w[near & (keep | pass_)].sum(), "snag": w[snag & pass_].sum(),
            "keep_T_lo": float(np.percentile(T[keep], 1)) if keep.any() else None,
            "pass_T_hi": float(np.percentile(T[pass_], 99)) if pass_.any() else None,
            "keep_W_lo": float(np.percentile(W[keep], 1)) if keep.any() else None,
            "keep_r2_lo": float(np.percentile(W[keep] ** 2 + T[keep] ** 2, 1)) if keep.any() else None}


# ----------------------------------------------------------------------------- report

def pct(a, q):
    return f"{np.percentile(a, q):.2f}"


def items_table(pop, items, plate):
    rows = ["| item | count | L p5-p95 | W p5-p95 | T p5-p95 | well: flat / leans / no | sim kind |",
            "|---|---|---|---|---|---|---|"]
    for i, it in enumerate(items):
        m = pop["item"] == i
        L, W, T, cat = pop["L"][m], pop["W"][m], pop["T"][m], pop["cat"][m]
        f = [np.mean(cat == c) * 100 for c in ("flat", "leans", "no")]
        rows.append(f"| {it['name']} | {it.get('count', 1):g} | {pct(L, 5)}-{pct(L, 95)} | {pct(W, 5)}-{pct(W, 95)} "
                    f"| {pct(T, 5)}-{pct(T, 95)} | {f[0]:.0f}% / {f[1]:.0f}% / {f[2]:.0f}% | {it.get('sim_kind', '-')} |")
    p = plate
    rows.append(f"\nWell: `{p['name']}` {p['shape']} top {p['top']:g} / bottom {p['bottom']:g} mm, depth "
                f"{p['depth']:g} mm, must sit {'below the liquid (' + format(p['fill_h'], '.1f') + ' mm)' if p['require'] == 'submerged' else 'below the rim'}, "
                f"margin {p['margin']:g} mm, leaning {'accepted' if p['accept_lean'] else 'not accepted'}.")
    return "\n".join(rows)


def routing_table(pop, items, gates, rules):
    names = [f"L{k + 1} {gate_label(g, g['eff'])}" for k, g in enumerate(gates)] + ["catch"]
    mid = route(pop, gates, rules, rules["p_roll"])
    lo, hi = route(pop, gates, rules, 0.0), route(pop, gates, rules, 1.0)
    rows = ["| item | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for i, it in enumerate(items):
        m = pop["item"] == i
        cells = []
        for a, b, c in zip(mid, lo, hi):
            x, y, z = (100 * v[m].mean() for v in (a, b, c))
            cells.append(f"{x:.0f}%" + (f" ({min(y, z):.0f}-{max(y, z):.0f})" if abs(y - z) >= 1 else ""))
        rows.append(f"| {it['name']} | " + " | ".join(cells) + " |")
    return "\n".join(rows) + (f"\n\nPercent of each item retained per level (effective sizes), p_roll = "
                              f"{rules['p_roll']:g}; brackets = flat-only vs any-roll bounds where they differ.")


def class_matrix(pop, classes, gates, rules):
    mid = route(pop, gates, rules, rules["p_roll"])
    rows = ["| class (target level) | " + " | ".join(f"L{k + 1}" for k in range(len(gates))) + " | catch | recovery |",
            "|---|" + "---|" * (len(gates) + 2)]
    for ci, c in enumerate(classes):
        m = pop["cls"] == ci
        tot = pop["wt"][m].sum()
        if tot == 0:
            continue
        vals = [(pop["wt"][m] * v[m]).sum() for v in mid]
        rows.append(f"| {c['name']} ({f'L{ci + 1}' if ci < len(gates) else 'catch'}) | " +
                    " | ".join(f"{v:.1f}" for v in vals) + f" | {100 * vals[ci] / tot:.0f}% |")
    purity, known = [], pop["cls"] >= 0
    for k in range(len(gates) + 1):
        tot = (pop["wt"] * mid[k] * known).sum()
        good = (pop["wt"] * mid[k] * (pop["cls"] == k)).sum()
        purity.append(f"{f'L{k + 1}' if k < len(gates) else 'catch'} {100 * good / tot:.0f}%" if tot > 0 else "")
    return "\n".join(rows) + "\n\nExpected counts per level (spec counts). Purity: " + ", ".join(p for p in purity if p)


def warnings(pop, items, classes, gates, rules, plate, reports):
    out = []
    mid = route(pop, gates, rules, rules["p_roll"])
    for k, g in enumerate(gates):
        m = pop["cls"] == k
        tot, kept = pop["wt"][m].sum(), (pop["wt"] * mid[k])[m].sum()
        if tot <= 0.5:
            out.append(f"- L{k + 1}: fewer than 0.5 expected items belong to {classes[k]['name']}; its gate is "
                       f"arbitrary and the level can be dropped.")
        elif kept < 0.8 * tot:
            band = rules["pass_clearance_mm"] + rules["block_margin_mm"] + 2 * rules["tolerance_mm"]
            why = (f" If the class boundary lies inside a continuous size range, every item within about "
                   f"{band:.2f} mm of it (clearance + margin + 2 x tolerance) is at risk; widen the gap between "
                   f"classes or accept the loss.")
            if classes[k].get("well") == "too_big":
                wide = (pop["W"] > plate["top"] - plate["margin"])[m]
                why = (f" Of these items {100 * (pop['wt'][m] * wide).sum() / tot:.0f}% are too wide for the well "
                       f"mouth; the rest are too long or too deep, which no gate can cut (well-fit.md 'Length').")
            out.append(f"- L{k + 1} keeps only {kept:.1f} of {tot:.1f} {classes[k]['name']} items.{why}")
    for k, (g, r) in enumerate(zip(gates, reports)):
        if r["leak_roll"] > 0.5 and g["kind"] in ("w", "p") and r["pass_T_hi"] is not None and r["keep_r2_lo"]:
            # a capped height h blocks a kept item at every roll if T >= h or W^2 + T^2 >= s^2 + h^2
            tol, mg = rules["tolerance_mm"], rules["block_margin_mm"]
            h_min = r["pass_T_hi"] + rules["pass_clearance_mm"] + tol
            h_max = max(r["keep_T_lo"] - mg - tol, math.sqrt(max(0.0, r["keep_r2_lo"] - (g["eff"] + tol + mg) ** 2)))
            fix = (f" A window gate win{g['eff']:g}x{(h_min + h_max) / 2:.2f} (effective; any height "
                   f"{h_min:.2f}-{h_max:.2f}) would block that roll: verify with `check`." if h_min < h_max else
                   " No height cap fixes it (passers too thick for the kept items' cross-section); use a round "
                   "hole (o) or a tunnel instead.")
            out.append(f"- L{k + 1}: {r['leak_roll']:.1f} kept items can roll on edge through the {g['second']:g} mm "
                       f"tall gaps.{fix}")
        if r["near"] > 0.05 * (r["keep_n"] + r["pass_n"]):
            out.append(f"- L{k + 1}: {r['near']:.1f} items are within {rules['near_band_mm']:g} mm of the opening: "
                       f"wedging risk. Round pillars or a downstream-widening gap help (passability.md).")
        if r["snag"] > 0:
            out.append(f"- L{k + 1}: {r['snag']:.1f} passing items have appendages wider than the gap: snag risk.")
    if any(c.get("well") == "fits" for c in classes):
        ok = fits_well(pop["cat"], plate)
        # items that pass every gate meant to remove too-big items but still do not fit (length or depth)
        for ci, c in enumerate(classes):
            if c.get("well") == "fits":
                landed = sum(mid[k] for k in range(ci, len(mid)))
                bad = (pop["wt"] * landed * ~ok).sum()
                if bad > 0.05:
                    by = {items[i]["name"]: (pop["wt"] * landed * ~ok * (pop["item"] == i)).sum()
                          for i in range(len(items))}
                    worst = ", ".join(f"{n} {v:.1f}" for n, v in sorted(by.items(), key=lambda x: -x[1]) if v > 0.05)
                    out.append(f"- Length/depth: {bad:.1f} items reach the 'fits' levels but do not fit the well "
                               f"({worst}). Gates cannot cut length; see well-fit.md 'Length'.")
                break
    frag = [i for i, it in enumerate(items) if it.get("fragile")]
    if frag:
        t_hi = np.percentile(pop["T"][np.isin(pop["item"], frag)], 95)
        for k, g in enumerate(gates):
            if g["kind"] in ("t", "slot") and g["eff"] < t_hi + 0.5:
                out.append(f"- L{k + 1}: fragile items ({', '.join(items[i]['name'] for i in frag)}) squeeze through "
                           f"a {g['eff']:g} mm {g['kind']} opening: check damage on the bench.")
    if (pop["cls"] < 0).any():
        miss = sorted({items[i]["name"] for i in np.unique(pop["item"][pop["cls"] < 0])})
        out.append(f"- Samples of {', '.join(miss)} match no [[class]]; they are left out of the scores.")
    return out


def commands(gates, items, pop, rules, to_nominal):
    lines, strips, pool = [], [], []
    for g in gates:
        nom = round(round(to_nominal(g["eff"]) / 0.05) * 0.05, 2)
        g["nominal"] = nom
        name = cad_name(g["kind"], nom)
        if g["kind"] in ("w", "t") and g["second"] == 8.0:      # GATE_H / TUNNEL_W in both CAD scripts
            strips.append(f'"gate_{name}": ("{g["kind"]}", {nom:g}),')
            eff = round(round(g["eff"] / 0.05) * 0.05, 2)      # the sim gets the as-printed size
            pname = cad_name(g["kind"], eff)
            pool.append((pname, f'"pool_gate_{pname}": ("{g["kind"]}", {eff:g}),'))
        else:
            pool.append((None, None))
    lines.append("CAD (gated container strips; skip names that already exist):")
    lines.append(f"  add to STRIPS in cad/gated_container.py: {' '.join(strips) or '(none: see proposals)'}")
    lines.append(f"  cd cad; {PY} gated_container.py " + " ".join(s.split('"')[1] for s in strips))
    other = [gate_label(g, g["nominal"]) for g in gates if g["kind"] not in ("w", "t")]
    if other:
        lines.append(f"  not a gated_container strip yet: {', '.join(other)} (see references/sim-and-cad.md, Proposals)")
    # sim: pool proxy, two gates per run, each pair with the population that reaches it
    kinds = {}
    for i, it in enumerate(items):
        if it.get("sim_kind"):
            kinds.setdefault(it["sim_kind"], []).append(i)
    pairs = [(0, 1)] if len(gates) == 2 else [(k, k + 1) for k in range(len(gates) - 1)] if len(gates) > 2 else [(0, None)]
    reach_all = [np.ones(len(pop["L"]))]
    for g in gates:
        reach_all.append(reach_all[-1] * p_pass(g["kind"], g["eff"], g["second"], pop["W"], pop["T"], rules["p_roll"]))
    lines.append("\nSIM (pool proxy at the as-printed size; read references/sim-and-cad.md section 2 first):")
    lines.append("  add to STRIPS in cad/sieve_system.py: " + (" ".join(p for _, p in pool if p) or "(none)"))
    lines.append("  log the mapping: " + ", ".join(f"sim {p[0]} = print {gate_label(g, g['nominal'])}"
                                                   for p, g in zip(pool, gates) if p[0]))
    for a, b in pairs:
        ga, gb = pool[a][0], (pool[b][0] if b is not None else "w5p0")
        if ga is None or gb is None:
            lines.append(f"  levels {a + 1}-{(b or a) + 1}: no sim design for this gate kind yet")
            continue
        counts = {k: sum((pop["wt"] * reach_all[a] * (pop["item"] == i)).sum() for i in idx) for k, idx in kinds.items()}
        tot = sum(counts.values()) or 1
        scale = min(1.0, rules["sim_max_particles"] / tot)
        mix = ",".join(f"{k}={max(1, round(v * scale))}" for k, v in counts.items() if v * scale >= 0.5)
        lines.append(f"  levels {a + 1}-{(b if b is not None else a) + 1}, from sim\\, seeds 0 1 2:")
        lines.append(f"    {PY} sorter.py --design pool:{ga},{gb} --mix {mix} --stroke constant_speed:amp_mm=10,"
                     f"speed_mm_s=50,ramp_s=0.01 --duration 30 --seed 0 --fps 0 --out out\\runs\\<sample>\\itNN_L{a + 1}_s0")
    missing = [it["name"] for it in items if not it.get("sim_kind")]
    if missing:
        lines.append(f"  not simulable (no sim_kind): {', '.join(missing)}")
    return "\n".join(lines)


def sim_size_check(items, pop):
    out = []
    for i, it in enumerate(items):
        k = it.get("sim_kind")
        if not k or it.get("source") == "sim":
            continue
        try:
            d = sim_draw(k, 400, np.random.default_rng(0))
        except SystemExit as e:
            return [f"- sim size check skipped: {e}"]
        m = pop["item"] == i
        for dim, key in (("W", "width"), ("T", "thickness")):
            a, b = np.median(pop[dim][m]), np.median(d[key])
            if abs(a - b) > 0.1 * a:
                out.append(f"- {it['name']}: median {dim} {a:.2f} mm in the spec vs {b:.2f} mm for sim kind {k}. "
                           f"The sim tests transport and jams, not this item's cut.")
    return out


def header(cmd, spec_path, spec, rules, print_src, tol):
    s = spec.get("sample", {})
    return (f"## gatecalc {cmd}: {s.get('name', Path(spec_path).stem)} ({dt.datetime.now():%Y-%m-%d %H:%M})\n\n"
            f"Spec `{spec_path}`; {rules['samples']} draws per item, seed {rules['seed']}; condition "
            f"{s.get('condition', 'unstated')}. Print: {print_src}, +/-{tol:g} mm. Margins: passers need "
            f"{rules['pass_clearance_mm']:g} mm clearance, kept items {rules['block_margin_mm']:g} mm overlap; "
            f"p_roll {rules['p_roll']:g}.\n")


def emit(text, log):
    print(text)
    if log:
        p = Path(log)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n" + text + "\n")
        print(f"\n(appended to {p})")


def load_spec(path):
    p = Path(path)
    return tomllib.loads(p.read_text(encoding="utf-8")), p.resolve().parent


def cmd_plan(a):
    spec, base = load_spec(a.spec)
    pop, items, classes, rules, plate = population(spec, base)
    to_nom, _, src, tol = make_print(spec)
    if len(classes) < 2:
        raise SystemExit("plan needs at least two [[class]] entries, top level first")
    gates, alts, reports, reach = [], [], [], np.ones(len(pop["L"]))
    for k in range(len(classes) - 1):
        g, alt = choose_gate(pop, reach, k, rules, tol, rules["gate_menu"])
        gates.append(g)
        alts.append(alt)
        reports.append(level_report(pop, reach, k, g, rules, tol))
        reach = reach * p_pass(g["kind"], g["eff"], g["second"], pop["W"], pop["T"], rules["p_roll"])
    out = [header("plan", a.spec, spec, rules, src, tol), "### Items\n", items_table(pop, items, plate)]
    cmds = commands(gates, items, pop, rules, to_nom)
    out += ["\n### Gate sequence (top level first)\n",
            "| level | keeps | gate (effective) | print as (nominal) | same-score window (eff) | worst-case "
            "misroutes | at effective size: kept leaking (flat + roll) | passers blocked (+ roll-only) | near-size |",
            "|---|---|---|---|---|---|---|---|---|"]
    for k, (g, r) in enumerate(zip(gates, reports)):
        out.append(f"| L{k + 1} | {classes[k]['name']} | {gate_label(g, g['eff'])} | {gate_label(g, g['nominal'])} "
                   f"| {g['window'][0]:g}-{g['window'][1]:g} | {g['score']:.1f} | {r['leak_flat']:.1f} + "
                   f"{r['leak_roll']:.1f} of {r['keep_n']:.1f} | {r['blocked']:.1f} (+{r['blocked_roll']:.1f}) of "
                   f"{r['pass_n']:.1f} | {r['near']:.1f} |")
    out.append(f"| catch | {classes[-1]['name']} | | | | | | | |")
    out.append("\nWorst case = opening at +/- print tolerance, passers needing their clearance and kept items their "
               "margin, items that only fit on edge passing with p_roll. Counts are spec counts.")
    out.append("\nRunners-up per level: " + "; ".join(
        f"L{k + 1} " + (", ".join(f"{gate_label(b, b['eff'])} (score {b['score']:.1f})" for b in al) or "none")
        for k, al in enumerate(alts)))
    out += ["\n### Predicted routing\n", routing_table(pop, items, gates, rules),
            "\n### Classes\n", class_matrix(pop, classes, gates, rules)]
    warn = warnings(pop, items, classes, gates, rules, plate, reports) + sim_size_check(items, pop)
    out += ["\n### Warnings\n", "\n".join(warn) or "- none", "\n### Next commands\n", "```", cmds, "```"]
    emit("\n".join(out), a.log)
    if a.json:
        Path(a.json).write_text(json.dumps({"spec": str(a.spec), "gates": gates, "classes": [c["name"] for c in classes],
                                            "rules": rules}, indent=1, default=float), encoding="utf-8")


def cmd_check(a):
    spec, base = load_spec(a.spec)
    pop, items, classes, rules, plate = population(spec, base)
    to_nom, to_eff, src, tol = make_print(spec)
    gates = parse_gates(a.gates, rules)
    for g in gates:
        g["eff"] = g["size"] if a.effective else to_eff(g["size"])
        g["nominal"] = to_nom(g["size"]) if a.effective else g["size"]
    out = [header("check " + a.gates, a.spec, spec, rules, src, tol), "### Items\n", items_table(pop, items, plate),
           "\nGates: " + ", ".join(f"L{k + 1} {gate_label(g, g['nominal'])} nominal = {g['eff']:.2f} effective"
                                   for k, g in enumerate(gates)),
           "\n### Predicted routing\n", routing_table(pop, items, gates, rules)]
    if len(classes) == len(gates) + 1:
        reach, reports = np.ones(len(pop["L"])), []
        for k, g in enumerate(gates):
            reports.append(level_report(pop, reach, k, g, rules, tol))
            reach = reach * p_pass(g["kind"], g["eff"], g["second"], pop["W"], pop["T"], rules["p_roll"])
        out += ["\n### Classes\n", class_matrix(pop, classes, gates, rules), "\n### Warnings\n",
                "\n".join(warnings(pop, items, classes, gates, rules, plate, reports)) or "- none"]
    else:
        out.append(f"\n(class table skipped: {len(classes)} classes for {len(gates)} gates; need gates + 1)")
    out += ["\n```", commands(gates, items, pop, rules, to_nom), "```"]
    emit("\n".join(out), a.log)


def cmd_item(a):
    rules = dict(DEFAULTS)
    for dims in a.dims:
        L, W, T = sorted((float(x) for x in dims.lower().split("x")), reverse=True)
        print(f"item L {L:g} x W {W:g} x T {T:g} mm")
        for name in a.plate.split(","):
            p = plate_of({"well": {"plate": name}})
            cat = well_fit(np.array([L]), np.array([W]), np.array([T]), p)[0]
            print(f"  well {name}: {cat}  (top {p['top']:g}, bottom {p['bottom']:g}, depth {p['depth']:g} mm, "
                  f"margin {p['margin']:g})")
        for g in parse_gates(a.gates or "", rules):
            eff = g["size"] if a.effective else g["size"] - a.undersize
            fl, an = passes(g["kind"], eff, g["second"], np.array([W]), np.array([T]))
            verdict = "passes flat" if fl[0] else ("passes only by rolling on edge" if an[0] else "blocked")
            print(f"  {gate_label(g)} (effective {eff:.2f}): {verdict}")


# ----------------------------------------------------------------------------- sim summary

def sim_gates(info):
    """Gates of a sim design from results['design_info'], top first, as (kind, size, second)."""
    if "openings_gap_x_height_mm" in info:            # pool: each opening is a rectangle, across x up
        return [("rect", a, b) for a, b in info["openings_gap_x_height_mm"]]
    return [("sq" if l["rule"] == "square" else "slot", l["opening_mm"], 0.0)   # inserts / plinko layers
            for l in info.get("layers", []) if l.get("rule") in ("square", "slot")]


def clearance(kind, s, second, W, T):
    """Room left around a flat-passing item (for the overlap check)."""
    if kind == "rect":
        return min(s - W, second - T)
    return s - (T if kind == "slot" else W)


def cmd_sim(a):
    runs = []
    for r in a.runs:
        p = Path(r)
        p = p / "results.json" if p.is_dir() else p
        runs.append(json.loads(p.read_text(encoding="utf-8")))
    groups = {}
    for r in runs:
        c = r["config"]
        key = (r["design"], json.dumps(c["stroke"], sort_keys=True), c["duration_s"], json.dumps(c.get("spray")),
               c["contact"]["friction"])
        groups.setdefault(key, []).append(r)
    out = [f"## gatecalc sim ({dt.datetime.now():%Y-%m-%d %H:%M})\n"]
    for (design, stroke, dur, spray, mu), rs in groups.items():
        zones, kinds = rs[0]["zones"], rs[0]["kinds"]
        real = [z for z in zones if z not in ("between", "lost")]
        out.append(f"### `{design}`, stroke {stroke}, {dur:g} s, spray {spray}, friction {mu:g}: "
                   f"{len(rs)} run(s), seeds {sorted(r['config']['seed'] for r in rs)}\n")
        out.append("| kind | " + " | ".join(zones) + " | recovery | t90 s |")
        out.append("|---|" + "---|" * (len(zones) + 2))
        for k in kinds:
            cnt = np.array([[r["counts"][k][z] for z in zones] for r in rs], float)
            rec = np.array([r["recovery"].get(k, np.nan) for r in rs])
            t90 = [t for t in (sim_t90(r, k) for r in rs) if t is not None]
            sd = lambda v: f" +/-{v:.1f}" if len(rs) > 1 else ""
            out.append(f"| {k} | " + " | ".join(f"{m:.1f}{sd(s)}" for m, s in zip(cnt.mean(0), cnt.std(0))) +
                       f" | {np.nanmean(rec):.2f} | {f'{np.mean(t90):.1f} ({len(t90)}/{len(rs)})' if t90 else 'not reached'} |")
        parts = [p for r in rs for p in r["particles"]]
        cont = []
        for z in real:
            inz = [p for p in parts if p["final_zone"] == z]
            if inz:
                cont.append(f"{z} {sum(p['ideal_zone'] != z for p in inz) / len(inz):.2f}")
        out.append("\nContamination (share of a zone's contents that belongs elsewhere, sim ideal zones): " + ", ".join(cont))
        gates = sim_gates(rs[0].get("design_info", {}))
        if gates and len(gates) == len(real) - 1:
            tally, rolled, roll_n = {"as flat rule": 0, "rolled through": 0, "upstream (transport)": 0,
                                     "beyond geometry": 0, "between/lost": 0}, 0, 0
            clear = []
            for p in parts:
                W, T = np.array([p["dims"]["width"]]), np.array([p["dims"]["thickness"]])
                kf = ka = len(gates)
                for gi, (kind, s, second) in enumerate(gates):
                    fl, an = passes(kind, s, second, W, T)
                    if fl[0]:
                        clear.append(clearance(kind, s, second, W[0], T[0]))
                    kf = gi if (kf == len(gates) and not fl[0]) else kf
                    ka = gi if (ka == len(gates) and not an[0]) else ka
                if p["final_zone"] not in real:
                    tally["between/lost"] += 1
                    continue
                z = real.index(p["final_zone"])
                if ka != kf:
                    roll_n += 1
                    rolled += z > kf
                tally["as flat rule" if z == kf else "rolled through" if kf < z <= ka else
                      "upstream (transport)" if z < kf else "beyond geometry"] += 1
            out.append("\nAgainst gatecalc geometry (per particle, all runs): " +
                       ", ".join(f"{k} {v}" for k, v in tally.items()))
            if roll_n:
                out.append(f"Roll-only particles that got past their flat-rule gate: {rolled}/{roll_n} "
                           f"= p_roll estimate {rolled / roll_n:.2f} (sim, uncalibrated).")
            pen = max(r["max_penetration_mm"] for r in rs)
            tight = min([c for c in clear if c > 0] or [float("nan")])
            out.append(f"Max particle-vs-tray overlap {pen:.3f} mm; tightest clearance of a passing particle "
                       f"{tight:.2f} mm" + (" -> overlap above half the clearance: tighten contacts before trusting "
                                             "near-size results." if pen > 0.5 * tight else "."))
        jams = [r["counts"][k].get("between", 0) for r in rs for k in kinds]
        out.append(f"Jams (between) per run {sum(jams) / len(rs):.1f}; lost per run "
                   f"{sum(r['counts'][k].get('lost', 0) for r in rs for k in kinds) / len(rs):.1f}; wall "
                   f"{np.mean([r['wall_s'] for r in rs]):.0f} s per run.\n")
    emit("\n".join(out), a.log)


def sim_t90(r, kind):
    ts = r.get("timeseries") or {}
    if not ts.get("t"):
        return None
    t = np.asarray(ts["t"]) - r["config"].get("settle_s", 0.0)
    n_ideal = {}
    for p in r["particles"]:
        if p["kind"] == kind:
            n_ideal[p["ideal_zone"]] = n_ideal.get(p["ideal_zone"], 0) + 1
    n = sum(n_ideal.values())
    inside = sum(np.minimum(np.asarray(ts["counts"][kind][z], float), c) for z, c in n_ideal.items())
    hit = np.flatnonzero(inside >= 0.9 * n - 1e-9)
    return max(0.0, float(t[hit[0]])) if len(hit) and n else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="choose one gate per level for the spec's classes")
    p.add_argument("spec")
    p.add_argument("--log")
    p.add_argument("--json")
    c = sub.add_parser("check", help="route the spec's items through a given gate sequence")
    c.add_argument("spec")
    c.add_argument("--gates", required=True, help="nominal sizes, top first, e.g. w2.4,t1.4")
    c.add_argument("--effective", action="store_true", help="--gates are printed (measured) sizes")
    c.add_argument("--log")
    i = sub.add_parser("item", help="one item against gates and a plate")
    i.add_argument("dims", nargs="+", help="LxWxT in mm, any order, e.g. 6.5x2.0x1.7; several allowed")
    i.add_argument("--gates", default="")
    i.add_argument("--plate", default="std96_flat", help=f"comma list of {', '.join(PLATES)}")
    i.add_argument("--undersize", type=float, default=DEFAULTS["undersize_mm"])
    i.add_argument("--effective", action="store_true")
    s = sub.add_parser("sim", help="summarise sim/sorter.py runs against the same geometry")
    s.add_argument("runs", nargs="+", help="run dirs (with results.json) or results.json files")
    s.add_argument("--log")
    a = ap.parse_args()
    {"plan": cmd_plan, "check": cmd_check, "item": cmd_item, "sim": cmd_sim}[a.cmd](a)


if __name__ == "__main__":
    main()
