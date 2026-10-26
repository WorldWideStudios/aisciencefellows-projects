"""Planned vs as-built: leave-one-module-out over what physically exists, with Merkle break points.

PLANNED is the lab-in-a-box graph (baebugs.labbox: modules, parts, arms, stages). AS-BUILT is the asset database
(kg/assets.json: photographed objects) plus stored software evidence (weights that resolve). Each planned node gets
the highest evidence level it has reached, every level backed by a pointer:

  PLANNED < DESIGNED (geometry/protocol file hashed) < SIMULATED (sim/test passes) < ATTEMPTED (physical try, failed)
          < BUILT (photographed object) < VERIFIED (measured / run on the bench)

Merkle: one leaf per planned node = H(node, level, evidence). The as-built root differs from the all-VERIFIED root exactly
at the nodes that are not done, so the break points are the gaps. Objects that exist but the plan does not know are
EXTRA nodes (a break point in the other direction: the plan is missing them).

LOMO on the as-built set: for each stage x platform, which physical things cover it; leave each one out and see which
stages lose their only physical cover.

  python -m baebugs.asbuilt   -> kg/asbuilt.json, docs/ASBUILT_LOMO.md, appends to daisy/labbox_mmr.jsonl
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .explore import merkle_root

LEVELS = ["PLANNED", "DESIGNED", "SIMULATED", "ATTEMPTED", "BUILT", "VERIFIED"]
STAGES = ["sort", "disperse", "image", "pick", "lyse", "incubate", "sequence"]

# planned node -> physical / stored evidence. Every entry names its source; nothing is inferred from names.
EVIDENCE = {
    "module:bugsorter_trommel": [("ATTEMPTED", "asset:fdm_trommel_attempt_1",
                                  "caps, crank, stand feet printed; perforated zones failed on FDM; split package moves zones to Fuse 1+")],
    "part:trommel_cap_inlet": [("BUILT", "asset:fdm_trommel_attempt_1", "printed (FDM, stringing), fit not checked")],
    "part:trommel_cap_outlet": [("BUILT", "asset:fdm_trommel_attempt_1", "printed (FDM, stringing), fit not checked")],
    "part:trommel_crank_hand": [("BUILT", "asset:fdm_trommel_attempt_1", "printed (FDM)")],
    "part:trommel_stand_inlet": [("ATTEMPTED", "asset:fdm_trommel_attempt_1", "feet visible; full stand not seen")],
    "part:trommel_stand_outlet": [("ATTEMPTED", "asset:fdm_trommel_attempt_1", "feet visible; full stand not seen")],
    "part:trommel_zone_2mm": [("ATTEMPTED", "asset:fdm_trommel_attempt_1", "failed (spaghetti)")],
    "part:trommel_zone_4mm": [("ATTEMPTED", "asset:fdm_trommel_attempt_1", "failed (spaghetti)")],
    "part:trommel_zone_7mm": [("ATTEMPTED", "asset:fdm_trommel_attempt_1", "failed (spaghetti)")],
    "module:vortex_sieve_kit": [("DESIGNED", "asset:vortexer", "the vortexer (platform) exists; the printed sieve kit is not printed")],
    "module:vision_gate": [("BUILT", "file:daisy/results/DAISY-BB-004/v4/DECISION.md",
                            "trained models stored and resolving (ORDER router USEFUL); bench camera not photographed")],
    "module:flex_pipette_lysis": [("BUILT", "asset:opentrons_flex", "Flex with 8-channel 1000 uL pipette photographed; lysis protocol simulated only")],
    "module:flex_heater_shaker_incubate": [("SIMULATED", "file:opentrons/protocols/baebugs_flex_line.sim.txt",
                                            "Flex present; no heater-shaker seen in the photos")],
    "arm:opentrons_flex_gripper": [("BUILT", "asset:opentrons_flex", "Flex photographed; gripper not seen")],
    "arm:human": [("VERIFIED", "asset:fuse_sift_drum", "people did every physical step today (gloved hands in the Sift photos)")],
}
# objects that exist but the plan graph has no node for (the plan must learn them)
EXTRA = {
    "asset:partabot_arm": ("arm", ["pick"], ["bench"], "a real arm at the bench; labbox lists B601/SO-101/BugPicker gantry but not Partabot"),
    "asset:tray_tower_orange": ("rack", [], ["bench"], "printed tray tower the arm works; only the bench twin knows a (wood) tower"),
    "asset:biokea_tray_frame_2x3_hex": ("tray", ["sort", "disperse"], ["bench"], "BioKEA sieve trays exist; labbox has no tray-stack module"),
    "asset:biokea_tray_frame_plain": ("tray", ["sort"], ["bench"], "insert carriers exist"),
    "asset:perforated_plate_ss": ("insert", ["sort"], ["bench"], "stainless PERF insert exists"),
    "asset:hex_grid_insert": ("insert", ["sort"], ["bench"], "printed hex insert exists"),
    "asset:cryovial_greiner_2ml": ("tube", ["sequence"], ["bench", "flex"], "Cryo.s 2 mL vials for whole-body DNA/RNA storage; no storage node in the plan"),
    "asset:cryo_rack_100_white": ("rack", ["sequence"], ["bench"], "vial rack for the specimen-to-vial hand-off"),
    "asset:plate_384_black": ("plate", ["lyse", "sequence"], ["flex"], "SBS 384 plate available"),
    "asset:fuse_sift_drum": ("instrument", [], ["bench"], "a working rotating perforated drum; fabrication tool, also a trommel analogue"),
    "asset:formlabs_fuse": ("instrument", [], ["bench"], "fabrication: prints the drum zones and toys"),
    "asset:pa12_toy_insect_batch": ("printed_part", [], ["bench"], "physical test standards (TRUTH-001 toys)"),
}


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def planned(repo):
    from . import labbox
    L = json.loads(Path(repo, "daisy/labbox.json").read_text())
    nodes = L["graph"]["nodes"]
    status = {f"module:{k}": v["status"] for k, v in labbox.MODULES.items()}
    out = {}
    for n in nodes:
        if n.startswith(("module:", "part:", "arm:")):
            base = "SIMULATED" if status.get(n) == "SIMULATED" else ("DESIGNED" if n.startswith("part:") else "PLANNED")
            out[n] = {"level": base, "evidence": [f"labbox:{status.get(n, 'node')}"]}
    return out, labbox.MODULES, L["graph"]["root"]


def build(repo="."):
    assets = {f"asset:{a['id']}": a for a in json.loads(Path(repo, "kg/assets.json").read_text())["assets"]}
    plan, MODULES, plan_root = planned(repo)
    nodes = {}
    for n, p in plan.items():
        lvl, ev = p["level"], list(p["evidence"])
        for (l2, src, note) in EVIDENCE.get(n, []):
            if src.startswith("asset:") and src not in assets:
                continue
            if src.startswith("file:") and not Path(repo, src[5:]).exists():
                continue
            if LEVELS.index(l2) > LEVELS.index(lvl):
                lvl = l2
            ev.append(f"{src} ({note})")
        nodes[n] = {"level": lvl, "evidence": ev}
    for a, (cat, stages, plats, note) in EXTRA.items():
        if a in assets:
            nodes[f"extra:{a[6:]}"] = {"level": "BUILT", "evidence": [f"{a} ({note})"], "stages": stages, "platform": plats, "category": cat}
    for n, v in nodes.items():
        v["leaf"] = H({"node": n, "level": v["level"], "evidence": v["evidence"]})
    root = merkle_root(sorted(v["leaf"] for v in nodes.values()))
    target = merkle_root(sorted(H({"node": n, "level": "VERIFIED", "evidence": ["done"]}) for n in nodes))
    breaks = sorted(n for n, v in nodes.items() if v["level"] != "VERIFIED")

    # physical cover per stage x platform (BUILT or better), modules from the plan + extras
    def physical(n, v):
        return LEVELS.index(v["level"]) >= LEVELS.index("BUILT") and n.startswith(("module:", "extra:"))
    cover = {}
    for n, v in nodes.items():
        if not physical(n, v):
            continue
        if n.startswith("module:"):
            m = MODULES[n[7:]]; st, pl = m["stages"], m["platform"]
        else:
            st, pl = v["stages"], v["platform"]
        for s in st:
            for p in pl:
                cover.setdefault(f"{p}:{s}", []).append(n)
    planned_cover = {}
    for k, m in MODULES.items():
        for s in m["stages"]:
            for p in m["platform"]:
                planned_cover.setdefault(f"{p}:{s}", []).append(f"module:{k}")
    grid = {}
    for p in ("bench", "flex"):
        for s in STAGES:
            key = f"{p}:{s}"
            grid[key] = {"planned": sorted(planned_cover.get(key, [])), "physical": sorted(cover.get(key, []))}
    lomo = {}
    for n in sorted({x for c in cover.values() for x in c}):
        lost = [k for k, c in cover.items() if c == [n]]
        lomo[n] = {"stages_lost": sorted(lost), "single_point_of_failure": bool(lost)}
    level_counts = {lv: sum(1 for v in nodes.values() if v["level"] == lv) for lv in LEVELS}
    return {"type": "asbuilt_vs_planned", "planned_graph_root": plan_root, "asbuilt_root": root, "all_verified_root": target,
            "levels": LEVELS, "level_counts": level_counts, "nodes": nodes, "break_points": breaks,
            "extras": sorted(n for n in nodes if n.startswith("extra:")), "stage_grid": grid, "lomo_physical": lomo,
            "assets_root": json.loads(Path(repo, "kg/assets.json").read_text())["root"]}


def report(R):
    L = ["# Planned vs as-built (LOMO x Merkle break points)", "",
         (f"As-built root `{R['asbuilt_root'][:16]}` vs all-verified target `{R['all_verified_root'][:16]}`; planned graph root "
          f"`{R['planned_graph_root'][:16]}`; asset database root `{R['assets_root'][:16]}`. Generated by `python -m baebugs.asbuilt`."), "",
         ("Physical cover counts only things that do a stage's work (trays, inserts, arms, vials, plates); test standards, fabrication "
          "tools and storage racks are listed as extras but cover no stage."), "",
         "Evidence levels: " + " < ".join(R["levels"]) + ". Every level points at a photo-backed asset or a stored file.", "",
         "| level | nodes |", "|---|---|"] + [f"| {k} | {v} |" for k, v in R["level_counts"].items()]
    L += ["", "## Stage coverage: planned vs physically present", "", "| stage | bench planned | bench physical | flex planned | flex physical |",
          "|---|---|---|---|---|"]
    nm = lambda xs: ", ".join(x.split(":", 1)[1] for x in xs) or "**none**"
    for s in STAGES:
        b, f = R["stage_grid"][f"bench:{s}"], R["stage_grid"][f"flex:{s}"]
        L.append(f"| {s} | {nm(b['planned'])} | {nm(b['physical'])} | {nm(f['planned'])} | {nm(f['physical'])} |")
    L += ["", "## Leave one physical thing out", "", "| left out | stages that lose their only physical cover |", "|---|---|"]
    for n, v in R["lomo_physical"].items():
        L.append(f"| {n.split(':', 1)[1]} | {', '.join(v['stages_lost']) or 'none (covered twice)'} |")
    L += ["", "## Break points", "", "**In the plan, not yet real** (below BUILT):", ""]
    for n in R["break_points"]:
        v = R["nodes"][n]
        if n.startswith("extra:") or v["level"] in ("BUILT", "VERIFIED"):
            continue
        L.append(f"- `{n}`: {v['level']}" + (f" ({v['evidence'][-1]})" if len(v["evidence"]) > 1 else ""))
    L += ["", "**Real, not in the plan** (the plan graph must add these):", ""]
    L += [f"- `{n[6:]}`: {R['nodes'][n]['evidence'][0].split(' (', 1)[1].rstrip(')')}" for n in R["extras"]]
    L += ["", "**Real but not verified** (BUILT: photographed, not yet measured or run):", ""]
    L += [f"- `{n}`" for n, v in R["nodes"].items() if v["level"] == "BUILT" and not n.startswith("extra:")]
    return "\n".join(L) + "\n"


def main(repo="."):
    from .mmr import MMRLog
    R = build(repo)
    Path(repo, "kg/asbuilt.json").write_text(json.dumps(R, indent=1, sort_keys=True) + "\n")
    Path(repo, "docs/ASBUILT_LOMO.md").write_text(report(R))
    log = MMRLog(Path(repo, "daisy/labbox_mmr.jsonl"))
    if not any(r["record"].get("asbuilt_root") == R["asbuilt_root"] for r in log.records):
        log.append({"type": "asbuilt_snapshot", "asbuilt_root": R["asbuilt_root"], "planned_graph_root": R["planned_graph_root"],
                    "assets_root": R["assets_root"], "level_counts": R["level_counts"], "n_break_points": len(R["break_points"])})
    print(json.dumps({k: R[k] for k in ("asbuilt_root", "level_counts")}), len(R["break_points"]), "break points")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
