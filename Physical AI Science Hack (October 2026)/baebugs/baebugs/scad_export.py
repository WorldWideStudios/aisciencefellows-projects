"""OpenSCAD sources for the toy insects and the filter plates.

The STLs stay canonical (they carry the Merkle insect hashes); the .scad files
are editable equivalents generated from the same specs:
  print/fuse1/scad/<toy>.scad        exact primitives of each toy (ellipsoids,
                                     rods as hulled spheres, wing plates), unioned
  print/fuse1/scad/toy_lib.scad      modules: ellipsoid(), rod(), plate()
  print/filters/scad/<filter>.scad   hole outline + every hole centre of the plate
  print/filters/scad/filter_plate.scad  hand-editable parametric plate (shape,
                                     size, pitch, web, border, thickness)
Rods are hull(sphere, sphere): same envelope as the STL's capped cylinder,
smoother facets. Render with OpenSCAD >= 2021 (F6, export STL).

  python -m baebugs.scad_export
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from . import punch_filters as PF
from .printmodels import insect_parts

TOY_LIB = """// baebugs toy insect primitives (TOY models, not replicas)
$fn = 40;
module ellipsoid(c, r) { translate(c) scale(r) sphere(1); }
module rod(a, b, d)    { hull() { translate(a) sphere(d / 2); translate(b) sphere(d / 2); } }
module plate(c, e)     { translate(c) cube(e, center = true); }
"""

FILTER_LIB = """// baebugs parametric filter plate (nominal sizes: measure the real punch / sheet)
// shape: "circle" | "square" | "hexagon" | "slot" | "star"
shape = "slot";
size = 3.2;          // circle/hex: diameter / across-flats; square: side; slot: width; star: outer diameter
slot_length = 19.05; // slot only
plate = 50;          // plate side (mm)
thickness = 1.6;     // Fuse 1+ PA12 >= 0.8; metal sheet ~0.5-1.0
border = 3;
web = 1.0;           // material between holes (Fuse >= 0.8)
hex_grid = true;     // stagger alternate rows
$fn = 48;

module hole2d() {
  if (shape == "circle") circle(d = size);
  else if (shape == "square") square(size, center = true);
  else if (shape == "hexagon") circle(d = size / cos(30), $fn = 6);
  else if (shape == "slot") hull() { translate([-(slot_length - size) / 2, 0]) circle(d = size);
                                     translate([(slot_length - size) / 2, 0]) circle(d = size); }
  else if (shape == "star") polygon([for (i = [0:9]) let(r = i % 2 ? size * 0.225 : size / 2, a = 90 + 36 * i)
                                     [r * cos(a), r * sin(a)]]);
}
hw = shape == "slot" ? slot_length : size;
px = hw + web; py = size + web;
difference() {
  cube([plate, plate, thickness]);
  for (j = [0 : floor((plate - 2 * border - size) / py)])
    for (i = [0 : floor((plate - 2 * border - hw) / px)])
      let(off = (hex_grid && j % 2 == 1) ? px / 2 : 0,
          x = border + hw / 2 + off + i * px, y = border + size / 2 + j * py)
      if (x + hw / 2 <= plate - border)
        translate([x, y, -1]) linear_extrude(thickness + 2) hole2d();
}
"""


def _v(xs, nd=4):
    return "[" + ", ".join(f"{float(x):.{nd}f}" for x in xs) + "]"


def toy_scad(length_mm, plan, header):
    prims, feats, _d = insect_parts(length_mm, plan)
    lines = [f"// {header}", f"// plan={plan} length={length_mm} mm features: {'; '.join(feats) or 'body only'}",
             "// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.",
             'use <toy_lib.scad>', "union() {"]
    for p in prims:
        s = p["spec"]
        if p["kind"] == "ellipsoid":
            lines.append(f"  ellipsoid({_v(s['center'])}, {_v(s['radii'])});  // {p['part']}")
        elif p["kind"] == "rod":
            lines.append(f"  rod({_v(s['a'])}, {_v(s['b'])}, {s['d']:.4f});  // {p['part']}.{p['seg']}")
        else:
            lines.append(f"  plate({_v(s['center'])}, {_v(s['extents'])});  // {p['part']}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def filter_scad(entry, size_mm=50.0, thickness_mm=1.6, web_mm=1.0):
    grid = "square" if entry[1] == "plastic canvas" else "hex"
    h = PF.hole(entry)
    _, holes, oa = PF.plate(entry, size_mm, web_mm=web_mm, grid=grid)
    pts = list(h.exterior.coords)[:-1]
    centres = [(round(x.centroid.x, 4), round(x.centroid.y, 4)) for x in holes]
    sp = PF.spec(entry)
    return (f"// {entry[0]}: {entry[5]} ({entry[1]}, realisation {entry[2]}) NOMINAL size, measure before use\n"
            f"// hole: {entry[3]} {json.dumps(sp['params_mm'])}; inscribed {sp['inscribed_d_mm']} mm; "
            f"{len(holes)} holes; open area {oa}; spec hash {sp['hash'][:16]}\n"
            f"plate = {size_mm}; thickness = {thickness_mm};\n"
            f"hole = [{', '.join(f'[{x:.4f}, {y:.4f}]' for x, y in pts)}];\n"
            f"centres = [{', '.join(f'[{x}, {y}]' for x, y in centres)}];\n"
            "difference() {\n  cube([plate, plate, thickness]);\n"
            "  for (c = centres) translate([c[0], c[1], -1]) linear_extrude(thickness + 2) polygon(hole);\n}\n")


def export(fuse_dir="print/fuse1", filt_dir="print/filters"):
    td = Path(fuse_dir) / "scad"; td.mkdir(parents=True, exist_ok=True)
    (td / "toy_lib.scad").write_text(TOY_LIB)
    n_toy = 0
    with open(Path(fuse_dir) / "manifest.csv") as fh:
        manifest = list(csv.DictReader(fh))
    for r in manifest:
        stem = Path(r["file"]).stem
        hdr = f"{r['family']} {r['level']} | {r['size_source']} | size_flag: {r.get('size_flag', '')} | STL: {r['file']}"
        (td / f"{stem}.scad").write_text(toy_scad(float(r["length_mm"]), r["plan"], hdr)); n_toy += 1
    fd = Path(filt_dir) / "scad"; fd.mkdir(parents=True, exist_ok=True)
    (fd / "filter_plate.scad").write_text(FILTER_LIB)
    n_f = 0
    for e in PF.LIBRARY:
        (fd / f"{e[0].replace('/', '-')}.scad").write_text(filter_scad(e)); n_f += 1
    return n_toy, n_f


if __name__ == "__main__":
    print(export())
