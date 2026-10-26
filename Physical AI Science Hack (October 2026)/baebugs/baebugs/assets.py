"""Digital asset database: every physical object at the bench, content-addressed and tied to the photos that show it.

Each asset is a record with: what it is, maker/ref when readable, which photos show it (by sha256), its role in
the BioKEA line, its interfaces (SBS footprint, rail tray, rod...), and dimensions with their SOURCE:
  spec           published standard or manufacturer figure (incl. Opentrons shared-data labware definitions)
  design         measured from a CAD/STL file (e.g. the pinned BugPicker tray designs)
  ruler-photo    read off the Helix ruler in a photo (still needs calipers)
  not measured   nothing claimed
Library candidates (PyLabRobot / Opentrons resource libraries) are kept apart from dims: a near match with a reason it is
not exact, never silently promoted to a measurement.
Leaf = H(record); root = Merkle over sorted leaves; every change is appended to daisy/assets_mmr.jsonl.
Photo boxes come from an open-vocabulary detector and are kept separately as INFERRED (assets/boxes.json).

  python -m baebugs.assets            -> kg/assets.json + daisy/assets_mmr.jsonl
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .explore import merkle_root
from .mmr import MMRLog

SBS = [127.76, 85.48]          # ANSI/SLAS 1-2004 microplate footprint

ASSETS = [
    # --- bench / BioKEA line --------------------------------------------------------------------------------------
    {"id": "tray_tower_orange", "name": "Printed tray tower (orange), 5 levels, two prongs per level", "category": "rack",
     "photos": ["tower_arm_side_1", "tower_arm_side_2", "tower_top", "tower_arm_side_3"], "role": "tray storage / filter face for the arm",
     "interfaces": ["rail_tray", "arm_reach"], "dims_source": "not measured",
     "notes": "printed replacement for the wood tower; prong pitch and level pitch to measure (twin still uses wood-tower guesses)"},
    {"id": "tray_tower_mount_orange", "name": "Printed L-bracket / wall mount (orange, 2 screw holes)", "category": "fixture",
     "photos": ["tower_arm_side_1", "tower_arm_side_2", "tower_top", "tower_arm_side_3"], "role": "mount for the tray tower",
     "interfaces": ["screw_m3_or_wood"], "dims_source": "not measured"},
    {"id": "wood_tray_tower", "name": "Wood post tower with plywood rail arms", "category": "rack",
     "photos": ["tower_arm_side_1", "tower_arm_side_2", "tower_arm_side_3"], "role": "first tray tower (bench twin config/tower.yaml)",
     "interfaces": ["rail_tray"], "dims_source": "not measured", "notes": "twin values are MEASURE estimates"},
    {"id": "partabot_arm", "name": "Partabot servo arm", "category": "arm", "maker": "Partabot",
     "photos": ["tower_arm_side_1", "tower_arm_side_2", "tower_top", "tower_arm_side_3"], "role": "pick / tray handling",
     "interfaces": ["fork_or_gripper", "clamp_mount"], "dims_source": "not measured", "notes": "clamped to the MDF bench board"},
    {"id": "vortexer", "name": "Vortex mixer (blue)", "category": "instrument",
     "photos": ["tower_arm_side_1", "tower_arm_side_3"], "role": "vortex sieve kit platform (vortex_puck_76)",
     "interfaces": ["vortex_platform"], "dims_source": "not measured"},
    {"id": "biokea_tray_frame_2x3_hex", "name": "BioKEA printed tray frame, 2x3 cells, hex mesh insert", "category": "tray",
     "photos": ["biokea_frames_tub", "tower_arm_side_1", "tower_arm_side_3"], "role": "sieve tray (HEX mesh)",
     "interfaces": ["rail_tray", "side_tab_handle"], "dims_mm": [103.0, 140.0, 12.5], "dims_source": "design",
     "notes": "matches BioKEA/BugPicker Designs/tray.stl (pinned upstream, measured not copied)"},
    {"id": "biokea_tray_frame_plain", "name": "BioKEA printed tray frame, open (insert holder), side tab", "category": "tray",
     "count": 2, "photos": ["biokea_frames_tub"], "role": "carrier for swappable inserts",
     "interfaces": ["rail_tray", "side_tab_handle", "insert_pocket"], "dims_mm": [113.6, 149.7, 10.0], "dims_source": "design",
     "notes": "closest pinned design: screentray.stl; confirm with calipers"},
    {"id": "hex_grid_insert", "name": "Printed hex grid insert (coarse)", "category": "insert", "photos": ["biokea_frames_tub", "tower_arm_side_1"],
     "role": "coarse sieve insert (GRID/HEX)", "interfaces": ["insert_pocket"], "dims_source": "not measured"},
    {"id": "perforated_plate_ss", "name": "Stainless perforated plate (round holes)", "category": "insert", "photos": ["biokea_frames_tub"],
     "role": "PERF sieve insert", "interfaces": ["insert_pocket"], "dims_source": "not measured", "notes": "hole size to measure (PERF-5 in config)"},
    {"id": "yellow_tub", "name": "Yellow plastic tub", "category": "container", "photos": ["biokea_frames_tub", "labware_overview_1", "labware_overview_3"],
     "role": "wash / catch basin", "interfaces": [], "dims_source": "not measured"},
    {"id": "ss_frame_3bay", "name": "Stainless 3-bay frame with notched rail", "category": "rack", "photos": ["labware_overview_1", "labware_overview_3", "labware_angle"],
     "role": "candidate tray rack over the tub", "interfaces": ["rail_tray?"], "dims_source": "not measured"},
    {"id": "breadboard_half", "name": "Solderless breadboard, half size (30 rows)", "category": "electronics", "photos": ["breadboard_ruler"],
     "role": "sensor / camera trigger wiring", "interfaces": [], "dims_source": "ruler-photo", "dims_mm": [83, 55, 9],
     "notes": "length read off the ruler ~8.3 cm; width/height typical for half-size boards"},
    # --- Opentrons / instruments --------------------------------------------------------------------------------------
    {"id": "opentrons_flex", "name": "Opentrons Flex with 8-channel 1000 uL pipette", "category": "instrument", "maker": "Opentrons",
     "photos": ["opentrons_flex_deck"], "role": "lyse / incubate / liquid handling (flex route)",
     "interfaces": ["flex_deck_slot", "SBS"], "dims_source": "not measured", "notes": "deck A1-D4; photo shows tip racks, deep-well plate, reservoir"},
    {"id": "opentrons_flex_tiprack_50ul_filter", "name": "Opentrons Flex 96 Filter Tip Rack 50 uL", "category": "tip_box",
     "maker": "Opentrons", "count": 2, "photos": ["lift_columns"], "role": "tips for the Flex 8-channel",
     "interfaces": ["flex_deck_slot", "SBS"], "dims_mm": [127.75, 85.75, 99.0], "dims_source": "spec",
     "spec_ref": "Opentrons shared-data labware definition opentrons_flex_96_filtertiprack_50ul (v1)"},
    {"id": "manual_lift_columns", "name": "Aluminium manual lift columns with handwheels (x3)", "category": "stage", "count": 3,
     "photos": ["lift_columns"], "role": "camera / tower height stage", "interfaces": ["T-slot_plate"], "dims_source": "not measured"},
    {"id": "formlabs_fuse", "name": "Formlabs Fuse 1+ printer and Fuse Sift", "category": "instrument", "maker": "Formlabs",
     "photos": ["formlabs_fuse"], "role": "PA12 powder prints (toy insects, parts)", "interfaces": [],
     "dims_mm": [165, 165, 300], "dims_source": "spec", "notes": "dims = Fuse 1+ build volume"},
    {"id": "fuse_sift_drum", "name": "Fuse Sift tumbler: rotating perforated steel drum with mat liner, glove box, air nozzle",
     "category": "instrument", "maker": "Formlabs",
     "photos": ["sift_floor_1", "sift_floor_2", "sift_gloves_overview", "sift_floor_3", "sift_drum_load", "sift_tumble_1", "sift_tumble_2"],
     "role": "depowders PA12 prints; also a working example of a rotating perforated drum (prebuilt trommel analogue)",
     "interfaces": ["glove_box", "perforated_floor"], "dims_source": "not measured",
     "notes": "videos show the PA12 toy insects tumbling; fines fall through the drum and the perforated floor"},
    {"id": "pa12_toy_insect_batch", "name": "Printed PA12 toy insects (print/fuse1 set), depowdering", "category": "printed_part",
     "photos": ["sift_drum_load", "sift_tumble_2", "sift_floor_1", "sift_floor_3", "pa12_toys_box", "pa12_toys_two_on_floor"],
     "role": "physical size standards for the sieve and vision lanes", "status": "PRINTED + DEPOWDERED (observed)",
     "interfaces": [], "dims_source": "design",
     "notes": "geometry in print/fuse1 (91 STLs, Merkle-addressed). Box photo: wings, legs and antennae mostly intact; count and per-toy "
              "identity not yet checked against the manifest; a few blue FDM strings cling to some toys (cross-contamination to remove "
              "before imaging); one blue FDM part is in the box"},
    {"id": "fdm_trommel_attempt_1", "name": "FDM print attempt 1 of the trommel (blue translucent filament)", "category": "printed_part",
     "photos": ["fdm_trommel_attempt1"], "role": "trommel parts: caps with spokes, drum rings, crank, stand feet",
     "interfaces": [], "dims_source": "not measured", "status": "FAILED (observed)",
     "notes": "caps, crank and stand feet printed; the perforated drum zones failed (spaghetti / loose loops) and rings show heavy stringing"},
    # --- labware & consumables ----------------------------------------------------------------------------------------
    {"id": "plate_384_black", "name": "384-well plate, black", "category": "plate", "maker": "PerkinElmer",
     "photos": ["plate384_ruler", "plate384_top"], "role": "imaging / assay plate", "interfaces": ["SBS"],
     "dims_mm": SBS + [None], "dims_source": "spec", "notes": "footprint is the SBS standard; height depends on the exact product",
     "library_candidates": [{"library": "pylabrobot 0.2.2", "resource": "Revvity_384_wellplate_28ul_Ub", "size_mm": [127.76, 85.48, 14.35],
                             "why_not_exact": "ProxiPlate-384 Plus is white; photographed plate is black (PerkinElmer = Revvity)"},
                            {"library": "pylabrobot 0.2.2", "resource": "Greiner_384_wellplate_28ul_Fb", "size_mm": [127.76, 85.48, 14.4],
                             "why_not_exact": "different maker; same SBS 384 format"}]},
    {"id": "tipbox_vwr_purple", "name": "Tip box, purple, hinged lid", "category": "tip_box", "maker": "VWR",
     "photos": ["labware_overview_1", "labware_angle", "labware_overview_2", "labware_overview_3"], "role": "tips",
     "interfaces": ["SBS?"], "dims_source": "not measured"},
    {"id": "tipbox_kashi", "name": "Tip box, clear (96 tips)", "category": "tip_box", "maker": "KASHI",
     "photos": ["labware_overview_1", "labware_angle", "labware_overview_2", "labware_overview_3"], "role": "tips",
     "interfaces": ["SBS?"], "dims_source": "not measured"},
    {"id": "tipbox_xtip4_1000", "name": "xTIP4 1000 uL tip box with blue rack", "category": "tip_box", "maker": "Biotix",
     "photos": ["xtip4_box", "rack_edge_ruler", "labware_overview_1", "labware_overview_2", "labware_overview_3"], "role": "tips",
     "interfaces": ["SBS?"], "dims_source": "not measured"},
    {"id": "rack_96_pink", "name": "96-position rack, pink", "category": "rack",
     "photos": ["rack_edge_ruler", "labware_overview_1", "labware_angle", "labware_overview_2", "labware_overview_3"],
     "role": "microtube rack", "interfaces": ["SBS?"], "dims_source": "ruler-photo", "notes": "length ~14 cm read off the ruler (rack_edge_ruler)"},
    {"id": "rack_96_purple", "name": "96-position rack, purple (deep)", "category": "rack",
     "photos": ["labware_overview_1", "labware_angle", "labware_overview_2", "labware_overview_3"], "role": "microtube rack", "interfaces": [], "dims_source": "not measured"},
    {"id": "rack_60_purple", "name": "60-position tube rack, purple (5 x 12)", "category": "rack",
     "photos": ["labware_overview_1", "labware_angle", "racks_closeup_ruler", "labware_overview_2", "labware_overview_3", "racks_diagonal_ruler"],
     "role": "1.5-2 mL tube rack", "interfaces": [], "dims_source": "not measured"},
    {"id": "rack_4way_orange", "name": "4-way tube rack, orange (50 mL / 15 mL / micro)", "category": "rack",
     "photos": ["labware_overview_1", "labware_angle", "labware_overview_2"], "role": "conical tube rack", "interfaces": [], "dims_source": "not measured"},
    {"id": "rack_18_white", "name": "18-hole rack, white (3 x 6)", "category": "rack",
     "photos": ["labware_overview_1", "labware_angle", "racks_closeup_ruler", "racks_diagonal_ruler", "labware_overview_3"],
     "role": "15 mL tube rack", "interfaces": [], "dims_source": "not measured"},
    {"id": "cryo_grid_81_blue", "name": "81-cell cryobox grid, blue (9 x 9)", "category": "rack",
     "photos": ["labware_overview_1", "labware_angle", "racks_closeup_ruler", "racks_diagonal_ruler", "labware_overview_3"],
     "role": "cryovial storage", "interfaces": [], "dims_source": "not measured"},
    {"id": "cryo_rack_100_white", "name": "100-position numbered cryo rack, white", "category": "rack",
     "photos": ["labware_overview_1", "racks_closeup_ruler", "racks_diagonal_ruler", "labware_overview_2", "labware_overview_3"],
     "role": "cryovial storage (specimen-to-vial hand-off)", "interfaces": [], "dims_source": "not measured"},
    {"id": "cryo_box_biologix", "name": "Clear cryo box", "category": "container", "maker": "Biologix",
     "photos": ["labware_overview_1", "racks_closeup_ruler", "racks_diagonal_ruler", "labware_overview_2", "labware_overview_3"],
     "role": "vial box", "interfaces": [], "dims_source": "not measured"},
    {"id": "cryovial_greiner_2ml", "name": "Cryo.s 2 mL PP cryovial, round bottom, external thread, starfoot, sterile", "category": "tube",
     "maker": "Greiner Bio-One", "ref": "126263", "lot": "E23093DQ", "expiry": "2028-09-12", "count": 100,
     "photos": ["greiner_cryos_bag", "racks_closeup_ruler", "racks_diagonal_ruler"], "role": "whole-body specimen storage for DNA/RNA",
     "interfaces": ["cryo_rack"], "dims_source": "not measured", "notes": "read from the bag label"},
    {"id": "conical_50ml_vwr", "name": "50 mL conical tube, green cap", "category": "tube", "maker": "VWR",
     "photos": ["labware_overview_1", "labware_angle", "xtip4_box", "labware_overview_2"], "role": "bulk sample / ethanol",
     "interfaces": ["rack_4way"], "dims_source": "not measured",
     "library_candidates": [{"library": "pylabrobot 0.2.2", "resource": "cor_falcon_tube_50mL_Vb", "size_mm": [30, 30, 115],
                             "why_not_exact": "Corning Falcon, not VWR; standard 50 mL conical format"}]},
    {"id": "tip_1000ul", "name": "1000 uL pipette tip (loose)", "category": "tip", "photos": ["labware_overview_1", "racks_diagonal_ruler"],
     "role": "transfer", "interfaces": [], "dims_source": "not measured"},
    {"id": "ruler_helix_46cm", "name": "Helix 46 cm steel ruler (scale reference in photos)", "category": "reference", "maker": "Helix",
     "photos": ["breadboard_ruler", "plate384_ruler", "rack_edge_ruler", "racks_closeup_ruler", "racks_diagonal_ruler", "labware_overview_1"],
     "role": "photo scale", "interfaces": [], "dims_mm": [460, None, None], "dims_source": "spec"},
]


def leaf(rec):
    return hashlib.sha256(json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build(repo="."):
    repo = Path(repo)
    photos = {p["photo_id"]: p for p in json.loads((repo / "assets/photos.json").read_text())}
    out = []
    for a in ASSETS:
        missing = [p for p in a["photos"] if p not in photos]
        if missing:
            raise ValueError(f"{a['id']}: unknown photos {missing}")
        rec = {**a, "count": a.get("count", 1), "dims_mm": a.get("dims_mm"),
               "photo_sha256": sorted(photos[p]["original_sha256"] for p in a["photos"])}
        rec["leaf"] = leaf(rec)
        out.append(rec)
    root = merkle_root(sorted(r["leaf"] for r in out))
    photo_root = merkle_root(sorted(p["original_sha256"] for p in photos.values()))
    by_source = {}
    for r in out:
        by_source[r["dims_source"]] = by_source.get(r["dims_source"], 0) + 1
    return {"type": "asset_db", "root": root, "photos_root": photo_root, "n_assets": len(out), "n_photos": len(photos),
            "dims_by_source": by_source, "assets": out}


def main(repo="."):
    db = build(repo)
    Path(repo, "kg").mkdir(exist_ok=True)
    Path(repo, "kg/assets.json").write_text(json.dumps(db, indent=1, sort_keys=True) + "\n")
    log = MMRLog(Path(repo, "daisy/assets_mmr.jsonl"))
    if not log.records or log.records[-1]["record"].get("root") != db["root"]:
        log.append({"type": "asset_db_version", "root": db["root"], "photos_root": db["photos_root"], "n_assets": db["n_assets"],
                    "leaves": sorted(r["leaf"] for r in db["assets"])})
    print(json.dumps({k: db[k] for k in ("root", "n_assets", "n_photos", "dims_by_source")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
