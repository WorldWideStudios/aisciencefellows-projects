"""Build the design optimizer's winners as printable parts: out/<prefix><part> (STEP, STL, PNG, checks).

Run in the WSL venv from this folder:  ~/venvs/sieve/bin/python build_winners.py [../sim/opt/winners.json]
winners.py runs it from Windows and then slices every part. The prefix is win<rank>_ for the demo study
and <study>_win<rank>_ for the others (winners_<study>.json).

Each winner's "cad" block (sim/optimize.py) names the script ("file", which picks the builder) and the
numbers, in nominal (CAD) sizes:
    gated    gated_container.py: "constants" (module constants) and "STRIPS", top level first; a
             "mid_slot_PROPOSAL" (L<n>_GATE_X, L<n>_slot_mm, flip_levels) builds one container per level
    plinko   plinko_layers.py: "LAYERS" rows, top first
    inserts  sieve_insert.py: "INSERTS", coarse first
    breaker  breaker_layer.py: "spec" (breaker:open=..,bar=..,...), built and flagged by the script itself
The script is imported fresh for each winner, those tables are replaced, and the script's own builders
make the parts, so a winner is built exactly like the hand-made parts. Each winner also gets a preview
of its assembled tower. Printability flags go into the checks and into out/winners_build.json.
"""
import importlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

from cadkit import OUT, export_all

LINES = 0.8          # two 0.4 mm extrusion lines: thinner walls and teeth print, but fragile or ragged


def fresh(module):
    m = importlib.import_module(module)
    return importlib.reload(m)            # back to the file's own numbers before this winner's overrides


def gated(cad):
    gc = fresh("gated_container")
    for k, v in cad.get("constants", {}).items():
        if not hasattr(gc, k):
            raise SystemExit(f"build_winners: gated_container.py has no constant {k}")
        setattr(gc, k, v)
    gc.STRIPS = {n: (kind, float(size)) for n, (kind, size) in cad["STRIPS"].items()}
    levels = list(gc.STRIPS)
    # mid-slot towers give each level its own gate position and slot, so each level gets its own container
    mid = cad.get("mid_slot_PROPOSAL") or {}
    gxs = [mid.get(f"L{i + 1}_GATE_X") for i in range(len(levels))]
    slots = [mid.get(f"L{i + 1}_slot_mm") for i in range(len(levels))]
    flip = mid.get("flip_levels", True)
    if any(g is not None for g in gxs):
        parts = {f"gated_container_L{i + 1}": (lambda g=g, s=s: gc.container(g, s))
                 for i, (g, s) in enumerate(zip(gxs, slots))}
    else:
        parts = {"gated_container": gc.container}
    parts.update({n: (lambda n=n: gc.strip(n)) for n in levels})
    previews = {"tower": lambda: gc.tower(levels, gxs, slots, flip)}
    flags = []
    if gc.TOOTH < LINES:
        flags.append(f"teeth between openings are {gc.TOOTH:g} mm: under two 0.4 mm lines, fragile")
    for n, (kind, size) in gc.STRIPS.items():
        if size < LINES:
            flags.append(f"{n}: {size:g} mm opening may close up on the first layer")
    for i, (g, s) in enumerate(zip(gxs, slots)):
        slot = s if s is not None else gc.OPEN_X - ((gc.GATE_X if g is None else g) + gc.STRIP_T / 2)
        if slot < 3.0:
            flags.append(f"L{i + 1} drop slot is {slot:g} mm long: under 3 mm, check that the gate rails still fit")
    return parts, previews, flags


def plinko(cad):
    pl = fresh("plinko_layers")
    pl.LAYERS = [tuple(row) for row in cad["LAYERS"]]
    parts = {name: (lambda n=name: pl.layer(n)) for name, *_ in pl.LAYERS}
    previews = {"tower": pl.section}
    flags = []
    for name, floor, gap, b_top, h, *_ in pl.LAYERS:
        if floor != "rods":
            continue
        b_bot = b_top - 2 * h * math.tan(math.radians(pl.RELIEF_DEG))
        if b_bot < LINES:
            flags.append(f"{name}: rods are {b_bot:.2f} mm wide at the bed (taper), under two lines")
        if gap < LINES:
            flags.append(f"{name}: {gap:g} mm gap may close up on the first layer")
    return parts, previews, flags


def inserts(cad):
    si = fresh("sieve_insert")
    si.INSERTS = {n: tuple(v) for n, v in cad["INSERTS"].items()}
    parts = {n: (lambda n=n: si.insert(n)) for n in si.INSERTS}
    previews = {"tower": lambda: insert_tower(si, list(si.INSERTS))}
    flags = []
    for n, (hole, bar, _t) in si.INSERTS.items():
        if bar < LINES:
            flags.append(f"{n}: {bar:g} mm bars between holes, under two lines")
        if hole < LINES:
            flags.append(f"{n}: {hole:g} mm holes may close up on the first layer")
    return parts, previews, flags


def insert_tower(si, names):
    """One holder box per insert (coarse on top) stacked rim on rim over a catch pan, cut in half."""
    import cadquery as cq
    import frame_holder as box
    from gated_container import half
    stack = box.frame().union(cq.Workplane("XY").box(box.OPEN_L + 1, box.OPEN_W + 1, box.LEDGE_T,
                                                     centered=(True, True, False)))
    for i, n in enumerate(names):
        z = (len(names) - i) * box.H
        stack = stack.union(box.frame().translate((0, 0, z))).union(si.insert(n)[0].translate((0, 0, z + box.LEDGE_T)))
    return half(stack), {"preview_only": True, "levels_top_first": names}


def breaker(cad):
    bl = fresh("breaker_layer")
    p = bl.spec(cad["spec"])
    parts = {bl.name(p): lambda: bl.layer(p)}
    previews = {"preview": lambda: bl.preview(p)}
    return parts, previews, bl.layer(p)[1]["printability_flags"]


BUILDERS = {"gated_container.py": gated, "plinko_layers.py": plinko, "sieve_insert.py": inserts,
            "breaker_layer.py": breaker}   # by cad.file


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "../sim/opt/winners.json").resolve()
    data = json.loads(src.read_text(encoding="utf-8"))
    study = data.get("study", "demo")
    built = {"source": str(src), "study": study, "built": f"{datetime.now():%Y-%m-%d %H:%M}",
             "caveat": data.get("caveat") or data.get("note"), "undersize_mm_assumed": data.get("undersize_mm_assumed"), "winners": []}
    for i, w in enumerate(data["winners"], 1):
        w = {**w, "rank": w.get("rank") or i}          # the malaise study leaves rank null: file order is rank
        script = Path((w.get("cad") or {}).get("file", "")).name     # the family name can be a variant (gated_mid)
        if script not in BUILDERS:
            print(f"build_winners: rank {w['rank']}: no CAD builder for {script or 'a winner without cad.file'} "
                  f"({w['family']}), skipped")
            continue
        prefix = f"win{w['rank']}_" if study == "demo" else f"{study}_win{w['rank']}_"
        parts, previews, flags = BUILDERS[script](w["cad"])
        entry = {k: w.get(k) for k in ("rank", "id", "family", "sim_spec", "stroke", "stroke_human", "score",
                                       "params_nominal")}
        entry.update({"assembly": w["cad"].get("tower"), "flags": flags, "parts": [],
                      "family": w.get("family") or script.split("_")[0]})
        for name, make in [*parts.items(), *previews.items()]:
            part, info = make()
            out = prefix + name
            checks = export_all(part, out, {**info, "winner": w["rank"], "printability_flags": flags})
            ok = all(checks[k] for k in ("valid_solid", "single_solid", "watertight_mesh", "fits_bed"))
            entry["parts"].append({"name": out, "print": name in parts, "checks_ok": ok,
                                   "bbox_mm": checks["bbox_mm"], "volume_cm3": checks["volume_cm3"]})
            print(f"{out}: {'ok' if ok else 'CHECKS FAILED'} {checks['bbox_mm']}")
        for f in flags:
            print(f"  flag: {f}")
        built["winners"].append(entry)
    name = "winners_build.json" if study == "demo" else f"winners_build_{study}.json"
    (OUT / name).write_text(json.dumps(built, indent=1), encoding="utf-8")
    print(f"build_winners: wrote {OUT / name}")


if __name__ == "__main__":
    main()
