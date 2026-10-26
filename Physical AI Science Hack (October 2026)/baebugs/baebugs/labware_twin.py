"""Labware twin: photographed bench labware -> parametric SBS remixes, Opentrons defs, Merkle custody.

Nineteen parts seen in Byron's 2026-10-25 bench photos (tip boxes, tube racks, a 10x10 cryo box,
2 mL cryotubes, printed frames, freezer rack, instruments) are cataloged with estimated sizes, then
remixed into eight printable parts. Seven sit on the SBS footprint so they drop into an Opentrons
deck slot; the cryo-box grid keeps its 133 mm size.

Every part (observed or printed) is split into named fragments and hashed into its own Merkle tree;
part roots roll up into one lab root and a hash-linked custody log seals the build.

  canonical JSON : sorted keys, no whitespace, UTF-8, integral floats written as ints
  leaf           : sha256(0x00 || name || "\\n" || canonical JSON)
  node           : sha256(0x01 || left || right); an odd node is carried up unchanged
  fragments      : sorted by name before building the tree
  derivation     : a remix commits to the roots of the observed parts it came from

All observed dimensions are ESTIMATES from photos against an 18 in steel rule (est=True in data).
Vendor names and marks are deliberately left out: parts are described by function and color only.
The photos themselves are not in the repo (they show vendor marks), so photo evidence leaves are
recorded as BREAKs: the hash is pinned, the bytes live off-repo.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "print" / "labware"
SCAD_LIB = OUT / "scad" / "labware.scad"
SBS_X, SBS_Y = 127.76, 85.48  # ANSI/SLAS 1-2004 footprint, mm
DATE = "2026-10-25"

# sha256 of the original JPEGs (bytes off-repo; see module docstring)
PHOTOS = {
    "46901": "bf2add091eae09de201aff68aed6aea8516fb3ca1b51d0da60c0081b276b5528",
    "46902": "96fc3f4ad4dd9f26e7225261f17537e58e8b6d3f3354b2c4ddd219f4a60d7b15",
    "46903": "f6abbcdd00e69bf5f88daf52a9c0efe6a2bd52eb76aad523b48295ab9bae176b",
    "46904": "c46be60cd0b94647b22edb1fdba0966949e55e7c5c46ee23023c62e6ba0e9231",
    "46905": "21d41ff54de656f8c245e93f92fb8e031c50e831664a047e2542b367c2bb909f",
    "46906": "76712fa492d3284eed4dec3a1a558bcbdd61195b5634543b4d0f1b4c892384d1",
    "46907": "cdd431171cc9044ccf0a2ecbfbe6e1daf9c1139cc2fe957e273d8a3e88a610ec",
    "46908": "0d219e2da0b2f1c1294c2b1c6528263b63d480f0dd32eb1e11f7eda89b18870f",
    "46909": "194742f25f983868db0bff29ee2fae6931fd59a4742b9c5a1cd6151e00147881",
    "46910": "cad86112e86249bece0d208cee6a448089184e6c0e1831802c7edd388397e8ea",
    "46911": "6ee77b2174922ce7d0d04ccc4f001d5558cde72c72e3e2aca702e2c0bae2c011",
    "46912": "e4422ccd4ce160437d97b22d614c5cff61bf878759c5841523be9de2c05e601c",
    "46914": "c8f21843b4296a1bdee4121489b7b23dca3b72aa96624ecdc3c8ae473932fc54",
    "46915": "e10aa2155c6563f5b5b601c7147bdce865760a3016aef056ca2efcb8afe4a993",
    "46916": "6053dc9bab4f4a70354517eb22e5e479a59844fc541c71f2737a91e25c5eb73a",
    "46917": "d2506c29f6a5c73b7f9e1ae655b6f2555273a8e632ba52374896433d61a2977e",
}

MATERIAL = {"PLA": (1.24, 20.0), "PETG": (1.27, 22.0), "PP (filament)": (0.90, 45.0)}  # g/cm3, USD/kg est.
FILL = 0.75  # fraction of mesh volume printed solid (thin-walled parts)


def _obs(id, name, kind, photos, dims, grid, material, reuse, remix, mfg, ip, **extra):
    return dict(id=id, name=name, kind=kind, vendor="commercial (brand withheld)" if kind in
                ("tip rack", "cryo box", "consumable") else "unbranded / in-house", photos=photos,
                dims=dims, grid=grid, material=material, reuse=reuse, remix=remix, mfg=mfg, ip=ip, **extra)


OBSERVED = [
    _obs("obs-tipbox-1000-blue", "1000 µL tip box, blue insert", "tip rack", ["46905", "46906", "46916"],
         {"x": 122, "y": 82, "z": 95, "est": True, "basis": "ruler, photo 46907; insert ~120x80"},
         {"rows": 8, "cols": 12, "pitch": 9.0, "hole_d": 7.6, "est": True, "basis": "SBS 96 pitch; hole from 1000 µL collar"},
         "PP insert, clear PP hinged box", "tip refill rack, SBS insert donor", "print-rack-96",
         {"level": "med", "notes": "Molded PP, ribbed walls, textured floor. Printed copies lose the ~0.1 mm tip-seat tolerance robots need."},
         {"level": "high", "notes": "Lid carries a vendor wordmark and product name; the spined insert and box form may carry design rights. Remix only the public SBS 96 grid."}),
    _obs("obs-tipbox-200f-magenta", "200 µL filter tip box, magenta insert", "tip rack",
         ["46901", "46911", "46914", "46916", "46917"],
         {"x": 124, "y": 84, "z": 70, "est": True, "basis": "insert spans ~127 mm on rule, photo 46917"},
         {"rows": 8, "cols": 12, "pitch": 9.0, "hole_d": 5.6, "est": True, "basis": "SBS 96 pitch; hole from 200 µL tip"},
         "PP insert, clear PP box", "tip refill rack", "print-rack-96",
         {"level": "med", "notes": "Filter-tip sterility ends when the box is opened; a refilled box is non-sterile unless autoclaved."},
         {"level": "med", "notes": "Vendor name on lid label only. Generic 96 grid."}),
    _obs("obs-tipbox-purple-hinged", "Purple hinged tip box", "tip rack", ["46901", "46903", "46904", "46914"],
         {"x": 118, "y": 82, "z": 60, "est": True, "basis": "photo 46914 against SBS neighbors"},
         {"rows": 8, "cols": 12, "pitch": 9.0, "hole_d": 5.4, "est": True, "basis": "SBS 96 pitch"},
         "PP, purple base + clear lid", "tip rack, small-parts case", "print-rack-96",
         {"level": "low", "notes": "Simple box; useful as a dust case for printed parts."},
         {"level": "med", "notes": "Lid has an embossed vendor logo. Do not reproduce it."}),
    _obs("obs-microtube-96-purple", "Purple 96-place microtube rack with base", "tube rack", ["46908", "46911", "46914"],
         {"x": 125, "y": 85, "z": 55, "est": True, "basis": "photo 46914"},
         {"rows": 8, "cols": 12, "pitch": 9.0, "hole_d": 6.5, "est": True, "basis": "96 format"},
         "PP", "PCR strip / 0.5 mL tube rack", "print-rack-96",
         {"level": "low", "notes": "Generic; easy to print in PETG."}, {"level": "low", "notes": "No visible branding."}),
    _obs("obs-microtube-50-purple", "Purple 5x10 microtube rack", "tube rack", ["46908", "46910", "46911", "46915"],
         {"x": 250, "y": 75, "z": 40, "est": True, "basis": "~10 in on rule, photo 46908"},
         {"rows": 5, "cols": 10, "pitch": 13.0, "hole_d": 11.0, "est": True, "basis": "1.5/2 mL rack convention"},
         "PP", "1.5/2 mL and cryotube holding", "print-cryo-24",
         {"level": "low", "notes": "Longer than an SBS slot; the 4x6 remix fixes that."}, {"level": "low", "notes": "No visible branding."}),
    _obs("obs-cryobox-100", "100-place cryo box, 10x10 numbered", "cryo box", ["46902", "46907", "46908", "46910", "46915"],
         {"x": 133, "y": 133, "z": 52, "est": True, "basis": "lid ~131 mm on rule, photo 46907; 2 in box convention"},
         {"rows": 10, "cols": 10, "pitch": 13.0, "hole_d": 12.8, "est": True, "basis": "numbered grid 1-100, photo 46902"},
         "PC lid, PP grid insert", "cryotube storage, -80 C", "print-cryo-100",
         {"level": "high", "notes": "Rated for -80 C / LN2 vapor. Printed PLA/PETG embrittle below ~-20 C; a printed copy is not a cryo box. 133 mm does not fit a deck slot."},
         {"level": "high", "notes": "Vendor wordmark printed on the lid. Numbered-cell layout is a common format; keep numbering, drop the mark."}),
    _obs("obs-cryotube-2ml", "2 mL external-thread cryotube, sterile", "consumable", ["46909", "46910", "46915"],
         {"x": 12.5, "y": 12.5, "z": 48.5, "est": True, "basis": "2 mL external-thread cryotube convention"},
         None, "PP, screw cap, round bottom, star foot, sterile", "sample unit; the 'bug' container", None,
         {"level": "high", "notes": "Sterility and nuclease/pyrogen-free claims hold only for unopened bags. Never print substitutes. Track lot and expiry."},
         {"level": "med", "notes": "Product name and vendor are trademarks; the tube outline is a functional dimension used to size racks."},
         lot={"lot": "E23093DQ", "expiry": "2028-09-12", "pack": "100 pcs/bag"}),
    _obs("obs-conical-50", "50 mL conical tube, green cap", "consumable", ["46911", "46914", "46916"],
         {"x": 29.0, "y": 29.0, "z": 115, "est": True, "basis": "50 mL conical convention"},
         None, "PP", "bulk media, specimen", "print-conical-50",
         {"level": "low", "notes": "Standard consumable."}, {"level": "low", "notes": "Label not legible in photos."}),
    _obs("obs-rack-18-white", "White 3x6 two-tier tube rack", "tube rack", ["46908", "46910", "46914", "46915"],
         {"x": 150, "y": 85, "z": 60, "est": True, "basis": "~6 in on rule, photo 46915"},
         {"rows": 3, "cols": 6, "pitch": 24.0, "hole_d": 17.5, "est": True, "basis": "15 mL conical rack convention"},
         "PP", "15 mL conicals", "print-conical-15",
         {"level": "low", "notes": "Slightly longer than SBS; the 3x5 remix fits a slot."}, {"level": "low", "notes": "Handwritten label only."}),
    _obs("obs-rack-4way-orange", "Orange 4-way tube rack", "tube rack", ["46911", "46914"],
         {"x": 135, "y": 95, "z": 90, "est": True, "basis": "photo 46911 vs 50 mL tube"},
         {"rows": 2, "cols": 3, "pitch": 32.0, "hole_d": 30.0, "est": True, "basis": "50 mL face"},
         "PP", "mixed 50/15/1.5 mL holding", "print-conical-50",
         {"level": "low", "notes": "Each face is a different tube size; the remix splits faces into SBS plates."},
         {"level": "med", "notes": "Interlocking 4-way cube forms may carry design patents. Remix single faces, not the cube."}),
    _obs("obs-freezer-rack-3bay", "Stainless chest-freezer rack, 3 bays", "storage", ["46907", "46908", "46911", "46912"],
         {"x": 430, "y": 140, "z": 150, "est": True, "basis": "~17 in on rule, photo 46907; bays fit 133 mm boxes"},
         {"rows": 1, "cols": 3, "pitch": 140.0, "hole_d": None, "est": True, "basis": "3 bays"},
         "stainless (est.)", "holds 3 cryo boxes per tier", None,
         {"level": "low", "notes": "Reuse as-is; container node in the twin."}, {"level": "low", "notes": "Generic."}),
    _obs("obs-tub-yellow", "Yellow polypropylene tub", "storage", ["46902", "46907", "46908", "46912"],
         {"x": 380, "y": 300, "z": 150, "est": True, "basis": "~15 in on rule, photo 46907"},
         None, "PP", "ice bath, wash tray, enclosure base", None,
         {"level": "low", "notes": "Reuse as-is."}, {"level": "low", "notes": "Generic."}),
    _obs("obs-printed-frame-open", "3D-printed open frames (2, lipped)", "printed frame", ["46912"],
         {"x": 127.76, "y": 85.48, "z": 12, "est": True, "basis": "photo 46912 proportions match SBS; set to SBS"},
         None, "PLA (est.)", "the 'folder' frame family; holds inserts", "print-frame-sbs",
         {"level": "med", "notes": "PLA warps above ~55 C, no autoclave. Reprint in PETG/PP for wet use."},
         {"level": "low", "notes": "In-house design."}),
    _obs("obs-printed-grid-mesh", "3D-printed 2x3 grid frame with mesh", "printed frame", ["46912"],
         {"x": 127.76, "y": 85.48, "z": 8, "est": True, "basis": "photo 46912"},
         {"rows": 2, "cols": 3, "pitch": 40.0, "hole_d": None, "est": True, "basis": "6 windows"},
         "PLA + fine mesh (est.)", "screened compartments for insects", "print-grid-mesh",
         {"level": "med", "notes": "Mesh aperture sets which insects stay in."}, {"level": "low", "notes": "In-house design."}),
    _obs("obs-printed-honeycomb", "3D-printed honeycomb lattice", "printed insert", ["46912"],
         {"x": 120, "y": 60, "z": 6, "est": True, "basis": "photo 46912"},
         {"rows": 3, "cols": 6, "pitch": 16.0, "hole_d": 14.0, "est": True, "basis": "hex cell across flats"},
         "PLA (est.)", "nesting cells / partitions", "print-honeycomb",
         {"level": "low", "notes": "Prints fast, no supports."}, {"level": "low", "notes": "Hex lattice is public-domain geometry."}),
    _obs("obs-perforated-sheet", "Perforated steel sheet", "insert", ["46912"],
         {"x": 140, "y": 100, "z": 0.8, "est": True, "basis": "photo 46912"},
         {"rows": None, "cols": None, "pitch": 3.0, "hole_d": 2.0, "est": True, "basis": "staggered round holes"},
         "steel (est.)", "floor screen for grid frame", "print-grid-mesh",
         {"level": "med", "notes": "Sharp cut edges; deburr or edge-wrap."}, {"level": "low", "notes": "Generic stock."}),
    _obs("obs-minicentrifuge", "Mini centrifuge, teal lid", "instrument", ["46901"],
         {"x": 150, "y": 150, "z": 110, "est": True, "basis": "photo 46901 vs tip box"},
         None, "ABS housing", "spin-down station node", None,
         {"level": "high", "notes": "Never print rotors or spinning adapters."}, {"level": "low", "notes": "Black-box node."}),
    _obs("obs-vortexer", "Vortex mixer, dimpled cup head", "instrument", ["46901"],
         {"x": 160, "y": 130, "z": 160, "est": True, "basis": "photo 46901"},
         None, "cast body, rubber head", "mixing station node", None,
         {"level": "med", "notes": "Printed head adapters are common; keep mass low."}, {"level": "low", "notes": "Black-box node."}),
    _obs("obs-steel-rule-18in", "18 in / 46 cm steel rule", "reference",
         ["46907", "46908", "46910", "46915", "46917"],
         {"x": 457, "y": 25, "z": 1, "est": False, "basis": "nominal 18 in"},
         None, "stainless", "scale reference for every estimate", None,
         {"level": "low", "notes": "Scale reference only."}, {"level": "low", "notes": "n/a"}),
]

PRINTS = [
    {"id": "print-rack-96", "name": "SBS 96 rack, 9 mm pitch", "family": "sbs-plate",
         "params": {"rows": 8, "cols": 12, "pitch": 9.0, "hole_d": 5.8, "height": 20.0, "a1_x": 14.38, "a1_y": 11.24,
                     "footprint_x": SBS_X, "footprint_y": SBS_Y},
         "derived_from": ["obs-tipbox-1000-blue", "obs-tipbox-200f-magenta", "obs-tipbox-purple-hinged", "obs-microtube-96-purple"],
         "ot": {"well_depth": 18.0, "well_vol": 200, "display": "BaeBugs 96 microtube rack (printed)"},
         "material": "PETG", "license": "MIT"},
    {"id": "print-cryo-24", "name": "SBS 4x6 rack, 2 mL cryotubes", "family": "sbs-plate",
         "params": {"rows": 4, "cols": 6, "pitch": 19.3, "hole_d": 13.2, "height": 30.0, "a1_x": 15.63, "a1_y": 13.79,
                     "footprint_x": SBS_X, "footprint_y": SBS_Y},
         "derived_from": ["obs-cryotube-2ml", "obs-microtube-50-purple"],
         "ot": {"well_depth": 42.0, "well_vol": 2000, "display": "BaeBugs 24 rack, 2 mL cryotube (printed)"},
         "material": "PETG", "license": "MIT"},
    {"id": "print-conical-15", "name": "SBS 3x5 rack, 15 mL conicals", "family": "sbs-plate",
         "params": {"rows": 3, "cols": 5, "pitch": 25.0, "hole_d": 17.5, "height": 40.0, "a1_x": 13.88, "a1_y": 17.74,
                     "footprint_x": SBS_X, "footprint_y": SBS_Y},
         "derived_from": ["obs-rack-18-white"],
         "ot": {"well_depth": 110.0, "well_vol": 15000, "display": "BaeBugs 15 rack, 15 mL conical (printed)"},
         "material": "PETG", "license": "MIT"},
    {"id": "print-conical-50", "name": "SBS 2x3 rack, 50 mL conicals", "family": "sbs-plate",
         "params": {"rows": 2, "cols": 3, "pitch": 35.0, "hole_d": 29.5, "height": 40.0, "a1_x": 28.88, "a1_y": 25.24,
                     "footprint_x": SBS_X, "footprint_y": SBS_Y},
         "derived_from": ["obs-conical-50", "obs-rack-4way-orange"],
         "ot": {"well_depth": 110.0, "well_vol": 50000, "display": "BaeBugs 6 rack, 50 mL conical (printed)"},
         "material": "PETG", "license": "MIT"},
    {"id": "print-cryo-100", "name": "10x10 cryo grid insert, 133 mm", "family": "grid-insert",
         "params": {"rows": 10, "cols": 10, "pitch": 13.0, "hole_d": 12.6, "height": 12.0, "a1_x": 8.0, "a1_y": 8.0,
                     "footprint_x": 133.0, "footprint_y": 133.0},
         "derived_from": ["obs-cryobox-100"], "ot": None, "material": "PP (filament)", "license": "MIT"},
    {"id": "print-frame-sbs", "name": "SBS lipped frame ('folder')", "family": "frame",
         "params": {"footprint_x": SBS_X, "footprint_y": SBS_Y, "height": 12.0, "wall": 5.0, "lip": 2.0, "lip_z": 2.0},
         "derived_from": ["obs-printed-frame-open"], "ot": None, "material": "PETG", "license": "MIT"},
    {"id": "print-grid-mesh", "name": "SBS 2x3 screened grid frame", "family": "grid-frame",
         "params": {"footprint_x": SBS_X, "footprint_y": SBS_Y, "height": 8.0, "wall": 4.0, "rows": 2, "cols": 3,
                     "rib": 3.0, "floor": 1.2, "mesh_hole": 2.0, "mesh_pitch": 3.0},
         "derived_from": ["obs-printed-grid-mesh", "obs-perforated-sheet"], "ot": None, "material": "PETG", "license": "MIT"},
    {"id": "print-honeycomb", "name": "Honeycomb insert for SBS frame", "family": "honeycomb",
         "params": {"footprint_x": 117.16, "footprint_y": 74.88, "height": 6.0, "cell": 14.0, "wall": 1.6},
         "derived_from": ["obs-printed-honeycomb"], "ot": None, "material": "PLA", "license": "MIT"},
]

MODULE = {"sbs-plate": "sbs_plate", "grid-insert": "grid_insert", "frame": "frame",
          "grid-frame": "grid_frame", "honeycomb": "honeycomb"}


# ---------- hashing ----------
def _norm(o):
    if isinstance(o, float) and o.is_integer():
        return int(o)
    if isinstance(o, dict):
        return {k: _norm(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_norm(v) for v in o]
    return o


def canon(obj) -> str:
    return json.dumps(_norm(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def leaf(name: str, payload) -> str:
    return sha(b"\x00" + (name + "\n" + canon(payload)).encode())


def node(left: str, right: str) -> str:
    return sha(b"\x01" + bytes.fromhex(left) + bytes.fromhex(right))


def merkle(leaves: list[str]):
    level, levels = list(leaves), [list(leaves)]
    while len(level) > 1:
        nxt = [node(level[i], level[i + 1]) for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
        levels.append(level)
    return level[0], levels


def _proof(levels, idx):
    out = []
    for level in levels[:-1]:
        sib = idx ^ 1
        if sib < len(level):
            out.append({"side": "L" if sib < idx else "R", "hash": level[sib]})
        idx //= 2
    return out


def climb(h: str, proof: list[dict]) -> str:
    for s in proof:
        h = node(s["hash"], h) if s["side"] == "L" else node(h, s["hash"])
    return h


def tree(fragments):
    fragments = sorted(fragments, key=lambda f: f[0])
    leaves = [leaf(n, p) for n, p in fragments]
    root, levels = merkle(leaves)
    return {"root": root, "fragments": [{"name": n, "payload": p, "leaf": h, "proof": _proof(levels, i)}
                                        for i, ((n, p), h) in enumerate(zip(fragments, leaves))]}


# ---------- outputs ----------
def scad_source(p: dict, lib_hash: str) -> str:
    """The library hash is part of the wrapper text, so a library edit re-renders every STL."""
    args = ", ".join(f"{k} = {v}" for k, v in p["params"].items())
    return (f"// {p['name']}\n// part id: {p['id']}  license: {p['license']}\n"
            f"// labware.scad sha256: {lib_hash}\n"
            f"// derived from: {', '.join(p['derived_from'])}\n"
            f"// Edit the parameters to remix. Catalog dimensions marked est. need calipers before a production run.\n"
            f"use <labware.scad>\n\n{MODULE[p['family']]}({args});\n")


def opentrons_def(p: dict) -> dict:
    q, ot = p["params"], p["ot"]
    letters, wells, ordering = "ABCDEFGHIJKLMNOP", {}, []
    for c in range(q["cols"]):
        col = []
        for r in range(q["rows"]):
            n = f"{letters[r]}{c + 1}"
            col.append(n)
            wells[n] = {"depth": ot["well_depth"], "totalLiquidVolume": ot["well_vol"], "shape": "circular",
                        "diameter": q["hole_d"], "x": round(q["a1_x"] + c * q["pitch"], 2),
                        "y": round(q["footprint_y"] - q["a1_y"] - r * q["pitch"], 2),
                        "z": round(q["height"] - ot["well_depth"] if q["height"] > ot["well_depth"] else 1.5, 2)}
        ordering.append(col)
    return {
        "ordering": ordering,
        "brand": {"brand": "BaeBugs (printed)", "brandId": [p["id"]]},
        "metadata": {"displayName": ot["display"], "displayCategory": "tubeRack", "displayVolumeUnits": "µL",
                     "tags": ["baebugs", "3d-printed", "estimated-dims"]},
        "dimensions": {"xDimension": q["footprint_x"], "yDimension": q["footprint_y"],
                       "zDimension": max(q["height"], ot["well_depth"] + 1.5)},
        "wells": wells,
        "groups": [{"metadata": {"wellBottomShape": "v" if ot["well_vol"] >= 15000 else "u"},
                    "wells": [w for col in ordering for w in col]}],
        "parameters": {"format": "irregular", "quirks": [], "isTiprack": False,
                       "isMagneticModuleCompatible": False, "loadName": load_name(p)},
        "namespace": "custom_beta", "version": 1, "schemaVersion": 2,
        "cornerOffsetFromSlot": {"x": 0, "y": 0, "z": 0},
    }


def load_name(p: dict) -> str:
    return "baebugs_" + p["id"].replace("print-", "").replace("-", "_")


def _render(scad: Path, stl: Path):
    exe = shutil.which("openscad")
    if not exe:
        raise RuntimeError("openscad not found; install it or keep the committed STLs (verify() still works)")
    r = subprocess.run([exe, "-o", str(stl), str(scad)], capture_output=True, text=True, timeout=900, check=False)
    if r.returncode:
        raise RuntimeError(f"openscad failed for {scad.name}:\n{r.stderr[-2000:]}")


def build(out: Path | str = OUT, prints: list[dict] | None = None, photo_dir: Path | str | None = None) -> dict:
    """Write SCAD, render STL (only when the SCAD changed), Opentrons defs, Merkle trees, custody log.

    `prints` lets a notebook swap in edited remix params. `photo_dir` (optional) re-hashes the original
    JPEGs; without it the pinned PHOTOS hashes are used and recorded as BREAKs (bytes off-repo).
    """
    import trimesh

    out = Path(out)
    prints = PRINTS if prints is None else prints
    for d in ("scad", "stl", "opentrons", "merkle"):
        (out / d).mkdir(parents=True, exist_ok=True)
    if (out / "scad" / "labware.scad").resolve() != SCAD_LIB.resolve():
        shutil.copy(SCAD_LIB, out / "scad" / "labware.scad")
    lib_hash = sha((out / "scad" / "labware.scad").read_bytes())

    photo_hash, breaks = dict(PHOTOS), []
    if photo_dir:
        for f in Path(photo_dir).iterdir():
            for pid in photo_hash:
                if f.name.endswith(pid + ".jpg"):
                    photo_hash[pid] = sha(f.read_bytes())
    for pid, h in sorted(photo_hash.items()):
        breaks.append({"ref": f"photo:{pid}", "sha256": h, "status": "BREAK",
                       "reason": "photo bytes kept off-repo (show vendor marks)"})

    trees = {}
    for p in OBSERVED:
        frags = [("identity", {k: p[k] for k in ("id", "name", "kind", "vendor")}),
                 ("dimensions", p["dims"]), ("grid", p["grid"]),
                 ("material", {"material": p["material"], "reuse": p["reuse"]}),
                 ("risk.manufacturing", p["mfg"]), ("risk.knowledge", p["ip"])]
        if p.get("lot"):
            frags.append(("lot", p["lot"]))
        frags += [(f"evidence.photo.{pid}", {"photo": pid, "sha256": photo_hash[pid], "resolves": False})
                  for pid in p["photos"]]
        trees[p["id"]] = tree(frags)

    meta = {}
    for p in prints:
        scad, stl = out / "scad" / f"{p['id']}.scad", out / "stl" / f"{p['id']}.stl"
        src = scad_source(p, lib_hash)
        changed = not scad.exists() or scad.read_text() != src
        if changed:
            scad.write_text(src)
        if changed or not stl.exists():
            _render(scad, stl)
            trimesh.load(stl).export(stl, file_type="stl")      # OpenSCAD 2021 writes ASCII; store binary (~5x smaller)
        mesh = trimesh.load(stl)
        dens, usd_kg = MATERIAL[p["material"]]
        grams = abs(mesh.volume) / 1000 * dens * FILL
        bbox = [round(float(v), 2) for v in mesh.extents]
        frags = [
            ("identity", {"id": p["id"], "name": p["name"], "family": p["family"]}),
            ("params", p["params"]),
            ("derivation", {"from": {d: trees[d]["root"] for d in p["derived_from"]}}),
            ("source.scad", {"file": f"scad/{p['id']}.scad", "sha256": sha(scad.read_bytes()), "library_sha256": lib_hash}),
            ("output.stl", {"file": f"stl/{p['id']}.stl", "sha256": sha(stl.read_bytes()), "bbox_mm": bbox,
                            "watertight": bool(mesh.is_watertight)}),
            ("manufacturing", {"material": p["material"], "grams_est": round(grams, 1),
                               "filament_usd_est": round(grams / 1000 * usd_kg, 2), "fill_factor": FILL}),
            ("license", {"spdx": p["license"]}),
        ]
        if p["ot"]:
            d = opentrons_def(p)
            f = out / "opentrons" / f"{load_name(p)}.json"
            f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
            frags.append(("output.opentrons", {"file": f"opentrons/{f.name}", "loadName": load_name(p),
                                               "sha256": sha(f.read_bytes())}))
        trees[p["id"]] = tree(frags)
        meta[p["id"]] = {"grams": round(grams, 1), "usd": round(grams / 1000 * usd_kg, 2), "bbox": bbox,
                         "watertight": bool(mesh.is_watertight)}

    ids = sorted(trees)
    lab_root, levels = merkle([trees[i]["root"] for i in ids])
    lab = {"root": lab_root, "parts": [{"id": i, "root": trees[i]["root"], "proof": _proof(levels, n)}
                                       for n, i in enumerate(ids)]}
    events = [
        {"seq": 0, "date": DATE, "actor": "Byron", "action": "captured",
         "detail": f"{len(photo_hash)} bench photos (bytes off-repo, recorded as BREAKs)", "commits_to": {"photos": photo_hash}},
        {"seq": 1, "date": DATE, "actor": "Claude (agent)", "action": "cataloged",
         "detail": f"{len(OBSERVED)} observed parts; dimensions are photo estimates against an 18 in rule",
         "commits_to": {p["id"]: trees[p["id"]]["root"] for p in OBSERVED}},
        {"seq": 2, "date": DATE, "actor": "Claude (agent)", "action": "modeled",
         "detail": f"{len(prints)} parametric remixes rendered with OpenSCAD; Opentrons defs for SBS racks",
         "commits_to": {p["id"]: trees[p["id"]]["root"] for p in prints}},
        {"seq": 3, "date": DATE, "actor": "Claude (agent)", "action": "sealed",
         "detail": "lab Merkle root over all part roots", "commits_to": {"lab_root": lab_root}},
    ]
    prev = "0" * 64
    for e in events:
        e["prev"] = prev
        e["hash"] = sha(canon(e).encode())
        prev = e["hash"]

    def dump(name, obj):
        (out / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")

    dump("merkle/parts.json", trees)
    dump("merkle/lab_root.json", lab)
    dump("merkle/custody_log.json", events)
    dump("merkle/breaks.json", breaks)
    dump("catalog.json", {"generated": DATE, "observed": OBSERVED, "prints": prints, "print_meta": meta,
                          "lab_root": lab_root})
    return {"lab_root": lab_root, "custody_head": prev, "print_meta": meta, "breaks": len(breaks),
            "filament_usd_total": round(float(sum(m["usd"] for m in meta.values())), 2)}


def verify(out: Path | str = OUT) -> dict:
    """Recompute every leaf, proof, part root, the lab root and the custody chain; re-hash referenced files."""
    out = Path(out)
    parts = json.loads((out / "merkle" / "parts.json").read_text())
    lab = json.loads((out / "merkle" / "lab_root.json").read_text())
    log = json.loads((out / "merkle" / "custody_log.json").read_text())
    fails, n, libs = [], 0, set()
    for pid, t in parts.items():
        names = [f["name"] for f in t["fragments"]]
        if names != sorted(set(names)) or merkle([f["leaf"] for f in t["fragments"]])[0] != t["root"]:
            fails.append(f"part tree {pid}")             # a dropped or reordered fragment changes the root
        for f in t["fragments"]:
            n += 1
            if leaf(f["name"], f["payload"]) != f["leaf"] or climb(f["leaf"], f["proof"]) != t["root"]:
                fails.append(f"fragment {pid}/{f['name']}")
            pl = f["payload"]
            if isinstance(pl, dict) and pl.get("file"):
                fp = out / pl["file"]
                if not fp.exists() or sha(fp.read_bytes()) != pl["sha256"]:
                    fails.append(f"file {pl['file']}")
                if pl.get("library_sha256"):
                    libs.add(pl["library_sha256"])
    lib = out / "scad" / "labware.scad"
    if libs and (not lib.exists() or {sha(lib.read_bytes())} != libs):
        fails.append("file scad/labware.scad")
    if merkle([parts[i]["root"] for i in sorted(parts)])[0] != lab["root"]:
        fails.append("lab root")
    for p in lab["parts"]:
        if parts[p["id"]]["root"] != p["root"] or climb(p["root"], p["proof"]) != lab["root"]:
            fails.append(f"part root {p['id']}")
    prev = "0" * 64
    for e in log:
        if e["prev"] != prev or sha(canon({k: v for k, v in e.items() if k != "hash"}).encode()) != e["hash"]:
            fails.append(f"custody event {e['seq']}")
        prev = e["hash"]
    if log[-1]["commits_to"].get("lab_root") != lab["root"]:
        fails.append("custody log does not seal the lab root")
    return {"ok": not fails, "fragments": n, "lab_root": lab["root"], "fails": fails}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--photos", default=None, help="directory with the original JPEGs (optional)")
    ap.add_argument("--verify-only", action="store_true")
    a = ap.parse_args()
    if not a.verify_only:
        print(json.dumps(build(a.out, photo_dir=a.photos), indent=1))
    print(json.dumps(verify(a.out), indent=1))
