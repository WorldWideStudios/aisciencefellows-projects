"""Turn measured object sizes into a filter plan for the 3-slot rig.

An object passes a filter if its width (short side, mm) is smaller than the filter's hole size.
Filters are stacked coarse (top) to fine (bottom), so the rig sorts objects into 4 fractions:
caught on the top, middle or bottom shelf, or passed through everything.

Modes:
  split   (default) pick the 3 filters that sort the objects into as many separate groups as
          possible, with hole sizes as far as possible from any object's width.
  target  pick filters so one shelf catches objects whose width is between MIN and MAX mm.
  coarse  for a pile, from pile_types.py's estimate: pick filters that give the largest common
          types a shelf of their own first. Each type's width comes from types.json.

Usage:
  python filter_plan.py objects.json [--filters filters.json] [--target MIN MAX]
                        [--json plan.json] [--image photo.jpg --out plan.png]
  python filter_plan.py --estimate estimate.json [--min-share 0.05] [--json plan.json]
"""
import argparse
import itertools
import json
import math
from pathlib import Path

SHELVES = ["top", "middle", "bottom"]
FRACTIONS = SHELVES + ["through"]
COLORS = {"top": (60, 60, 230), "middle": (0, 165, 255), "bottom": (60, 200, 60), "through": (230, 160, 40)}  # BGR


def load_filters(path, include_planned=True):
    """Return {filter_id: hole_mm} from a filters.json file, optionally leaving out filters not made yet."""
    data = json.loads(Path(path).read_text())
    planned = set(data.get("planned", [])) if not include_planned else set()
    return {fid: float(hole) for fid, hole in data["filters"].items() if fid not in planned}


def fraction_of(width, holes):
    """Index of the fraction an object lands in, for holes ordered top (coarse) to bottom (fine)."""
    for i, hole in enumerate(holes):
        if hole is not None and width >= hole:
            return i
    return len(holes)


def closest_call(widths, holes):
    """(log-ratio gap, width, hole) of the object width nearest to any hole size.

    Objects close to a hole size might go either way, so a bigger gap means a more reliable split.
    """
    return min((abs(math.log(w / h)), w, h) for w in widths for h in holes if h is not None)


def plan_split(widths, filters):
    """Filter ids, top to bottom, that split `widths` into the most groups with the widest gaps."""
    if len(filters) < 3:
        raise ValueError("need at least 3 filters")
    best = None
    for combo in itertools.combinations(filters, 3):
        ordered = sorted(combo, key=lambda f: -filters[f])
        holes = [filters[f] for f in ordered]
        groups = len({fraction_of(w, holes) for w in widths})
        score = (groups, closest_call(widths, holes)[0] if widths else 0)
        if best is None or score > best[0]:
            best = (score, ordered)
    return best[1]


def plan_coarse(widths, filters):
    """Filter ids, top to bottom, that separate the largest types first.

    `widths` are the reference widths of the types present. Going from the widest type down, a rig
    scores one point per type that gets a fraction to itself, stopping at the first type that shares
    one. Ties go to more separate groups, then to the widest gap between any width and any hole.
    """
    if len(filters) < 3:
        raise ValueError("need at least 3 filters")
    widths = sorted(widths, reverse=True)
    best = None
    for combo in itertools.combinations(filters, 3):
        ordered = sorted(combo, key=lambda f: -filters[f])
        holes = [filters[f] for f in ordered]
        fractions = [fraction_of(w, holes) for w in widths]
        separated = next((k for k, f in enumerate(fractions) if fractions.count(f) > 1), len(fractions))
        score = (separated, len(set(fractions)), closest_call(widths, holes)[0] if widths else 0)
        if best is None or score > best[0]:
            best = (score, ordered)
    return best[1]


def plan_target(filters, lo, hi):
    """Filter ids, top to bottom, so one shelf catches widths in [lo, hi].

    The catcher is the coarsest hole <= lo (everything at least that wide stops on it); the guard
    above it is the finest hole > hi (stops bigger objects first). Filters with holes between the
    two would split the target, so the remaining slot(s) take finer filters below the catcher,
    then coarser ones above the guard. A slot is left empty (None) if nothing fits.
    """
    by_size = sorted(filters, key=lambda f: filters[f])  # fine to coarse
    catchers = [f for f in by_size if filters[f] <= lo]
    if not catchers:
        raise ValueError(f"no filter has holes <= {lo} mm, so nothing can catch the target")
    catcher = catchers[-1]
    guards = [f for f in by_size if filters[f] > hi]
    guard = guards[0] if guards else None

    chosen = [catcher] + ([guard] if guard else [])
    finer = [f for f in reversed(by_size) if filters[f] < filters[catcher]]
    coarser = [f for f in by_size if guard and filters[f] > filters[guard]]
    for f in finer + coarser:
        if len(chosen) == 3:
            break
        chosen.append(f)
    ordered = sorted(chosen, key=lambda f: -filters[f])
    return ordered + [None] * (3 - len(ordered))


def build_plan(objects, filters, rig, mode, target=None):
    holes = [filters[f] if f else None for f in rig]
    widths = [o["width_mm"] for o in objects]
    fractions = {name: [] for name in FRACTIONS}
    for o in objects:
        fractions[FRACTIONS[fraction_of(o["width_mm"], holes)]].append(o["id"])

    # each fraction catches widths from its own hole up to the nearest hole above it
    ranges, upper = {}, None
    for name, hole in zip(SHELVES, holes):
        ranges[name] = [hole, upper] if hole is not None else None
        upper = hole if hole is not None else upper
    ranges["through"] = [0, upper]

    plan = {
        "mode": mode,
        "rig": dict(zip(SHELVES, rig)),
        "holes_mm": dict(zip(SHELVES, holes)),
        "fractions": {name: {"range_mm": ranges[name], "objects": fractions[name]} for name in FRACTIONS},
    }
    if widths:
        gap, w, h = closest_call(widths, holes)
        plan["closest_call"] = {"width_mm": w, "hole_mm": h, "apart_pct": round((math.exp(gap) - 1) * 100)}
    if target:
        # holes run coarse to fine, so the first one at or below the target's minimum catches it
        shelf = next(name for name, h in zip(SHELVES, holes) if h is not None and h <= target[0])
        plan["target"] = {"range_mm": list(target), "shelf": shelf, "caught_range_mm": ranges[shelf]}
    return plan


def describe(plan):
    def fmt_range(r):
        if r is None:
            return "empty slot"
        lo, hi = r
        return f">= {lo:g} mm" if hi is None else (f"< {hi:g} mm" if lo == 0 else f"{lo:g}-{hi:g} mm")

    rig = " | ".join(f"{f} {h:g} mm" if f else "empty" for f, h in zip(plan["rig"].values(), plan["holes_mm"].values()))
    lines = [f"mode: {plan['mode']}", f"rig (top to bottom): {rig}"]
    for name, frac in plan["fractions"].items():
        # measured objects are numbered; types in coarse mode are listed by name
        ids = ", ".join(f"#{i}" if isinstance(i, int) else i for i in frac["objects"]) or "-"
        lines.append(f"  {name:8s} {fmt_range(frac['range_mm']):14s} {ids}")
    if "ignored" in plan:
        lines.append(f"ignored (under {plan['min_share']:.0%} of the pile): {', '.join(plan['ignored']) or '-'}")
    if "closest_call" in plan:
        c = plan["closest_call"]
        lines.append(f"closest call: a {c['width_mm']:g} mm wide object vs the {c['hole_mm']:g} mm hole ({c['apart_pct']}% apart)")
    if "target" in plan:
        t = plan["target"]
        lines.append(f"target {t['range_mm'][0]:g}-{t['range_mm'][1]:g} mm lands on the {t['shelf']} shelf "
                     f"(which actually catches {fmt_range(t['caught_range_mm'])})")
    return "\n".join(lines)


def draw(image_path, objects, plan, out_path):
    import cv2
    import numpy as np

    img = cv2.imread(image_path)
    if img is None:
        raise SystemExit(f"cannot read {image_path}")
    shelf_of = {i: name for name, frac in plan["fractions"].items() for i in frac["objects"]}
    for o in objects:
        color = COLORS[shelf_of[o["id"]]]
        cv2.polylines(img, [np.array(o["box_px"], np.int32)], True, color, 2)
        x, y = o["center_px"]
        label = f"#{o['id']} {o['width_mm']:g}mm"
        cv2.putText(img, label, (x + 12, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(img, label, (x + 12, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
    for row, name in enumerate(FRACTIONS):
        f, h = plan["rig"].get(name), plan["holes_mm"].get(name)
        text = f"{name}: {f} ({h:g} mm)" if f else name
        cv2.rectangle(img, (10, 10 + row * 24), (26, 26 + row * 24), COLORS[name], -1)
        cv2.putText(img, text, (34, 24 + row * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(img, text, (34, 24 + row * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imwrite(out_path, img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("objects", nargs="?", help="objects JSON written by dish_sizer.py --json")
    ap.add_argument("--estimate", help="estimate JSON written by pile_types.py --json (coarse mode)")
    ap.add_argument("--types", default=str(Path(__file__).with_name("types.json")), help="reference width of each type")
    ap.add_argument("--min-share", type=float, default=0.05, help="coarse mode: ignore types below this share of the pile")
    ap.add_argument("--filters", default=str(Path(__file__).with_name("filters.json")))
    ap.add_argument("--made-only", action="store_true", help="leave out filters listed as planned (not made yet)")
    ap.add_argument("--target", type=float, nargs=2, metavar=("MIN", "MAX"), help="catch widths in this range, mm")
    ap.add_argument("--json", help="write the plan here")
    ap.add_argument("--image", help="photo to draw the plan on (the one dish_sizer measured)")
    ap.add_argument("--out", default="plan.png")
    args = ap.parse_args()
    if bool(args.objects) == bool(args.estimate):
        ap.error("give either an objects JSON or --estimate")

    filters = load_filters(args.filters, include_planned=not args.made_only)
    if args.estimate:
        # a rough per-type estimate of a pile: each common type stands in as one "object" at its reference width
        shares = json.loads(Path(args.estimate).read_text())["shares"]
        widths = {name: t["width_mm"] for name, t in json.loads(Path(args.types).read_text())["types"].items()}
        common = [name for name, share in sorted(shares.items(), key=lambda kv: -kv[1]) if share >= args.min_share]
        objects = [{"id": name, "width_mm": widths[name], "share": shares[name]} for name in common]
        plan = build_plan(objects, filters, plan_coarse([o["width_mm"] for o in objects], filters), "coarse")
        plan["min_share"] = args.min_share
        plan["ignored"] = [name for name in shares if name not in common]
        print(describe(plan))
        if args.json:
            Path(args.json).write_text(json.dumps(plan, indent=2))
        return

    objects = json.loads(Path(args.objects).read_text())
    if args.target:
        lo, hi = sorted(args.target)
        plan = build_plan(objects, filters, plan_target(filters, lo, hi), "target", (lo, hi))
    else:
        plan = build_plan(objects, filters, plan_split([o["width_mm"] for o in objects], filters), "split")

    print(describe(plan))
    if args.json:
        Path(args.json).write_text(json.dumps(plan, indent=2))
    if args.image:
        draw(args.image, objects, plan, args.out)


if __name__ == "__main__":
    main()
