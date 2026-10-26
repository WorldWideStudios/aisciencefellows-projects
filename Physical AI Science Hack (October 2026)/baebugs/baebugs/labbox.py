"""Lab in a box: BioKEA modules, their bench and Opentrons translations, printable parts, arms
(including bring-your-own), upstream repos and protocols as one content-addressed graph.

Line stages (the BioKEA order): sort -> disperse -> image -> pick -> lyse -> incubate -> sequence.
Each MODULE covers one or more stages on one or more platforms ("bench", "flex"). A ROUTE for a
specimen class (routine, VIP, novel) is the chain of modules that covers every stage on a platform;
a stage nobody covers is a break point. Leave-one-module-out shows which stages lose coverage, so
the graph says what each module is worth before anyone prints it.

Arms (and any BYO arm) declare their interfaces; a module's handling interface must match one:
  parallel_jaw (with jaw range), suction_pad, sbs_gripper (Flex), crank_knob.
Every node is hashed (parts by their STL sha256 from parts.json, upstream repos by their pinned
commit + file root), the graph has a Merkle root, and each build is appended to daisy/labbox_mmr.jsonl.
Status per module is honest: CONCEPT (designed), SIMULATED (passes a simulator or twin),
PRINTED, BENCH_TESTED, QUALIFIED. Nothing here is past SIMULATED yet.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

from .explore import merkle_root

STAGES = ["sort", "disperse", "image", "pick", "lyse", "incubate", "sequence"]
MATERIALS = {
    "PLA": "fit checks and dry demos only (creeps when warm, absorbs water)",
    "PETG": "wet bench use, better chemical resistance than PLA",
    "PA12 powder (Fuse 1+)": "wet use, fine holes >= 1.0 mm, durable; seal if porosity matters",
    "tough resin (post-cured)": "fine detail; full post-cure + solvent/lysis-buffer check before contact",
    "316L stainless insert": "wet-contact filter plates (laser cut / perforated / woven), see inserts.py",
}

MODULES = {
    "bugsorter_trommel": {"biokea": 1, "stages": ["sort"], "platform": ["bench"], "handling": ["crank_knob", "parallel_jaw"],
                          "parts": "print/parts", "part_names": ["trommel_zone_2mm", "trommel_zone_4mm", "trommel_zone_7mm",
                          "trommel_cap_inlet", "trommel_cap_outlet", "trommel_stand_inlet", "trommel_stand_outlet",
                          "trommel_crank_hand", "trommel_crank_arm", "trommel_bin", "trommel_bin_oversize"],
                          "materials": ["PLA", "PETG", "PA12 powder (Fuse 1+)"], "upstream": ["BioKEA/BugSorter", "zlite/entosieve"],
                          "status": "CONCEPT", "evidence": ["tests/test_print_parts.py"]},
    "variable_aperture": {"biokea": 1, "stages": ["sort"], "platform": ["bench"], "handling": ["parallel_jaw"],
                          "parts": None, "part_names": [], "materials": ["316L stainless insert"],
                          "upstream": ["BioKEA/BugSorter"], "status": "SIMULATED", "evidence": ["tests/test_variable_aperture.py"]},
    "vortex_sieve_kit": {"biokea": 2, "stages": ["sort", "disperse"], "platform": ["bench"], "handling": ["parallel_jaw"],
                         "parts": "print/parts", "part_names": ["vortex_puck_76", "vortex_mini_sieve_1.5mm", "vortex_mini_sieve_3mm",
                         "vortex_mini_sieve_5mm", "vortex_mini_pan", "vortex_mini_lid"], "materials": ["PETG", "PA12 powder (Fuse 1+)"],
                         "upstream": ["zlite/disperser"], "status": "CONCEPT", "evidence": ["tests/test_print_parts.py"]},
    "centrifuge_strainer": {"biokea": 1, "stages": ["sort"], "platform": ["bench"], "handling": ["parallel_jaw"],
                            "parts": "print/parts", "part_names": ["centrifuge_tube_strainer_1.5mm", "centrifuge_tube_strainer_3mm"],
                            "materials": ["PETG", "tough resin (post-cured)"], "upstream": [], "status": "CONCEPT",
                            "evidence": ["tests/test_print_parts.py"]},
    "flex_sieve_adapter": {"biokea": 2, "stages": ["sort", "disperse"], "platform": ["flex"], "handling": ["sbs_gripper"],
                           "parts": "opentrons", "part_names": ["ot_sieve_adapter"], "labware": ["baebugs_sieve_adapter_50mm"],
                           "materials": ["PETG", "PA12 powder (Fuse 1+)"], "upstream": ["zlite/disperser"], "status": "SIMULATED",
                           "evidence": ["opentrons/protocols/baebugs_flex_line.sim.txt"]},
    "flex_mini_trommel": {"biokea": 1, "stages": ["sort"], "platform": ["flex"], "handling": ["sbs_gripper"],
                          "parts": "opentrons", "part_names": ["ot_mini_trommel_base", "ot_mini_trommel_drum"],
                          "labware": ["baebugs_mini_trommel_4bin"], "materials": ["PETG", "PA12 powder (Fuse 1+)"],
                          "upstream": ["BioKEA/BugSorter"], "status": "SIMULATED", "evidence": ["opentrons/protocols/baebugs_flex_line.sim.txt"]},
    "vision_gate": {"biokea": 3, "stages": ["image"], "platform": ["bench", "flex"], "handling": [],
                    "parts": None, "part_names": [], "materials": [], "upstream": ["BioKEA/BugPicker", "zlite/B601"],
                    "status": "SIMULATED", "evidence": ["daisy/results/DAISY-BB-002a/v2/DECISION.md"]},
    "handoff_carrier": {"biokea": 3, "stages": ["pick"], "platform": ["bench", "flex"], "handling": ["parallel_jaw", "suction_pad", "sbs_gripper"],
                        "parts": "opentrons", "part_names": ["ot_handoff_plate"], "labware": ["baebugs_handoff_plate"],
                        "materials": ["PETG", "PA12 powder (Fuse 1+)"], "upstream": ["BioKEA/BugPicker", "BioKEA/BugPicker-arm-demo"],
                        "status": "SIMULATED", "evidence": ["opentrons/protocols/baebugs_flex_line.sim.txt"]},
    "bugpicker_suction": {"biokea": 3, "stages": ["pick"], "platform": ["bench"], "handling": ["suction_pad"], "parts": None,
                          "part_names": [], "materials": [], "upstream": ["BioKEA/BugPicker"], "status": "CONCEPT", "evidence": []},
    "flex_pipette_lysis": {"biokea": 4, "stages": ["lyse"], "platform": ["flex"], "handling": ["sbs_gripper"], "parts": None,
                           "part_names": [], "materials": [], "upstream": ["zlite/liquid-handler-marlin"], "status": "SIMULATED",
                           "evidence": ["opentrons/protocols/baebugs_flex_line.sim.txt"]},
    "bench_enzyme_dispenser": {"biokea": 4, "stages": ["lyse"], "platform": ["bench"], "handling": ["parallel_jaw"], "parts": None,
                               "part_names": [], "materials": [], "upstream": ["zlite/liquid-handler-marlin", "zlite/liquid-handler"],
                               "status": "CONCEPT", "evidence": []},
    "flex_heater_shaker_incubate": {"biokea": 5, "stages": ["incubate"], "platform": ["flex"], "handling": ["sbs_gripper"],
                                    "parts": None, "part_names": [], "materials": [], "upstream": [], "status": "SIMULATED",
                                    "evidence": ["opentrons/protocols/baebugs_flex_line.sim.txt"]},
    "turnstile_incubator": {"biokea": 5, "stages": ["incubate"], "platform": ["bench"], "handling": ["parallel_jaw"], "parts": None,
                            "part_names": [], "materials": [], "upstream": [], "status": "CONCEPT", "evidence": []},
    "edna_filter": {"biokea": None, "stages": ["sequence"], "platform": ["bench", "flex"], "handling": [], "parts": None,
                    "part_names": [], "materials": [], "upstream": [], "status": "CONCEPT", "evidence": ["dashboard/twin/bench_twin.html"]},
    "barcode_sequencing": {"biokea": None, "stages": ["sequence"], "platform": ["bench", "flex"], "handling": [], "parts": None,
                           "part_names": [], "materials": [], "upstream": [], "status": "CONCEPT", "evidence": []},
}

ARMS = {  # reach / jaw numbers are PLACEHOLDERS until measured
    "seeed_b601_dm": {"interfaces": ["parallel_jaw", "crank_knob"], "jaw_mm": [0, 40], "reach_mm": 380, "platform": ["bench"]},
    "so101": {"interfaces": ["parallel_jaw", "crank_knob"], "jaw_mm": [0, 35], "reach_mm": 280, "platform": ["bench"]},
    "bugpicker_gantry": {"interfaces": ["suction_pad"], "jaw_mm": None, "reach_mm": 300, "platform": ["bench"]},
    "opentrons_flex_gripper": {"interfaces": ["sbs_gripper"], "jaw_mm": None, "reach_mm": None, "platform": ["flex"]},
    "human": {"interfaces": ["parallel_jaw", "suction_pad", "sbs_gripper", "crank_knob"], "jaw_mm": [0, 120], "reach_mm": None,
              "platform": ["bench", "flex"]},
}
BYO_ARM_TEMPLATE = {"interfaces": ["parallel_jaw"], "jaw_mm": [0, 0], "reach_mm": 0, "platform": ["bench"],
                    "note": "copy, fill in measured values, add with add_arm(name, spec)"}
ROUTES = {  # specimen class -> required stages and preferences
    "routine": {"stages": STAGES, "prefer": "flex"},
    "vip": {"stages": STAGES, "prefer": "bench", "require_expert": True, "keep_intact": True},
    "novel": {"stages": ["sort", "disperse", "image", "pick", "lyse", "incubate", "sequence"], "prefer": "bench",
              "require_expert": True, "keep_intact": True},
}


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def add_arm(name, spec):
    ARMS[name] = {**BYO_ARM_TEMPLATE, **spec, "byo": True}
    return H({"arm": name, **ARMS[name]})


def _part_hashes(repo, m):
    if not m.get("parts"):
        return {}
    pj = Path(repo, m["parts"], "parts.json")
    if not pj.exists():
        return {n: None for n in m["part_names"]}
    rows = {r["part"]: r["sha256"] for r in json.loads(pj.read_text())["parts"]}
    return {n: rows.get(n) for n in m["part_names"]}


def build(repo=".", leave_out=None):
    up = json.loads(Path(repo, "daisy/upstream.json").read_text()) if Path(repo, "daisy/upstream.json").exists() else {}
    nodes, edges = {}, []
    for name, m in MODULES.items():
        if name == leave_out:
            continue
        parts = _part_hashes(repo, m)
        nodes[f"module:{name}"] = H({"module": name, **{k: m[k] for k in ("biokea", "stages", "platform", "handling", "status")},
                                     "parts": parts})
        for p, s in parts.items():
            nodes[f"part:{p}"] = s or H({"part": p, "missing": True})
            edges.append(("realized_by", f"module:{name}", f"part:{p}"))
        for u in m["upstream"]:
            pin = up.get(u)
            nodes[f"upstream:{u}"] = H({"repo": u, "commit": pin and pin["commit"], "root": pin and pin["sha256_root"]})
            edges.append(("derives_from", f"module:{name}", f"upstream:{u}"))
        for st in m["stages"]:
            for pl in m["platform"]:
                edges.append(("covers", f"module:{name}", f"stage:{pl}:{st}"))
    for a, spec in ARMS.items():
        nodes[f"arm:{a}"] = H({"arm": a, **spec})
        for name, m in MODULES.items():
            if name == leave_out:
                continue
            if set(m["handling"]) & set(spec["interfaces"]) and set(m["platform"]) & set(spec["platform"]):
                edges.append(("can_handle", f"arm:{a}", f"module:{name}"))
    for pl in ("bench", "flex"):
        for st in STAGES:
            nodes[f"stage:{pl}:{st}"] = H({"stage": st, "platform": pl})
    leaves = sorted(set(nodes.values()) | {H(e) for e in edges})
    return {"nodes": nodes, "edges": edges, "root": merkle_root(leaves), "leave_out": leave_out}


def coverage(g):
    cov = {pl: {st: [] for st in STAGES} for pl in ("bench", "flex")}
    for kind, src, dst in g["edges"]:
        if kind == "covers":
            _, pl, st = dst.split(":")
            cov[pl][st].append(src.split(":", 1)[1])
    return cov


def route(g, cls="routine"):
    """Pick a platform that covers every stage the class needs; mixed platforms allowed via the
    hand-off carrier. Uncovered stages are break points."""
    r = ROUTES[cls]; cov = coverage(g)
    order = [r["prefer"], "flex" if r["prefer"] == "bench" else "bench"]
    steps, breaks = [], []
    handoff = "module:handoff_carrier" in g["nodes"]
    for st in r["stages"]:
        pick = next(((pl, cov[pl][st]) for pl in order if cov[pl][st]), None)
        if not pick:
            breaks.append(st); steps.append({"stage": st, "platform": None, "modules": []}); continue
        steps.append({"stage": st, "platform": pick[0], "modules": sorted(pick[1])})
    switches = sum(1 for a, b in itertools.pairwise(steps) if a["platform"] and b["platform"] and a["platform"] != b["platform"])
    if switches and not handoff:
        breaks.append("platform switch without hand-off carrier")
    return {"class": cls, "steps": steps, "platform_switches": switches, "breaks": breaks,
            "requires_expert": r.get("require_expert", False), "keep_intact": r.get("keep_intact", False)}


def lomo(repo="."):
    base = build(repo); bcov = coverage(base)
    out = {"root": base["root"], "modules": {}}
    for m in MODULES:
        g = build(repo, leave_out=m); c = coverage(g)
        lost = [f"{pl}:{st}" for pl in c for st in STAGES if bcov[pl][st] and not c[pl][st]]
        routes = {cls: route(g, cls)["breaks"] for cls in ROUTES}
        out["modules"][m] = {"stages_lost": lost, "route_breaks": {k: v for k, v in routes.items() if v}, "root_without": g["root"],
                             "status": MODULES[m]["status"]}
    return out


def main(repo="."):
    from .mmr import MMRLog
    g = build(repo); L = lomo(repo)
    rec = {"type": "labbox_build", "root": g["root"], "nodes": len(g["nodes"]), "edges": len(g["edges"]),
           "routes": {c: route(g, c) for c in ROUTES}, "lomo": {m: {k: v for k, v in x.items() if k != "root_without"}
                                                              for m, x in L["modules"].items()}}
    Path(repo, "daisy/labbox.json").write_text(json.dumps({"graph": g, "lomo": L, "routes": rec["routes"],
                                                           "materials": MATERIALS, "byo_arm_template": BYO_ARM_TEMPLATE}, indent=1))
    log = MMRLog(Path(repo, "daisy/labbox_mmr.jsonl")); log.append(rec)
    return rec


if __name__ == "__main__":
    r = main()
    print("root", r["root"][:16], r["nodes"], "nodes", r["edges"], "edges")
    for c, x in r["routes"].items():
        print(c, [(s["stage"], s["platform"]) for s in x["steps"]], "breaks", x["breaks"])
    for m, x in r["lomo"].items():
        if x["stages_lost"] or x["route_breaks"]:
            print("LOMO", m, x["stages_lost"], x["route_breaks"])
