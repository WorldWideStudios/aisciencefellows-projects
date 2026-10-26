"""Variable-aperture sorter: one stainless stage whose opening steps down through size classes.

Mechanism (proof of concept, uncalibrated): two identical laser-cut 316L slot plates stacked; the
top plate slides across the slot width on a lead screw. Effective slot width w = w0 - offset, so one
stage covers 0..w0 continuously. A run steps the width DOWN through a schedule; at each width the
retained fraction is flushed into its own capture tray (largest class first), then the plate moves
to the next width. Everything that passes the smallest width lands in the pass-through tray.

Gates at every step (each one a Merkle leaf in an MMR, so a failed step is a break point):
  G_empty     the plates may only move when the stage is drained and empty (sliding edges shear:
              legs, antennae and wings would be cut) -> BREAK if specimens are present
  G_measured  camera-measured opening within tol_mm of the commanded width -> BREAK otherwise
  G_capture   every specimen retained at this width is accounted for in the capture tray
Passage model (geometric, rigid, orientation-free): a body with principal dimensions a >= b >= c
passes a slot of width w and length L when c <= w * fit and b <= L. Real, soft, wet or clumped
specimens differ; this is a planning model, not a measured sieve curve.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .mmr import MMR

# Bug analogs from the BioKEA Track A kit (nominal sizes from the kickoff deck; shapes and the
# other two dimensions are assumptions for planning, not measurements)
ANALOGS = {
    "chia seed":   {"nominal_mm": 1,  "dims": (2.0, 1.4, 1.0)},
    "couscous":    {"nominal_mm": 2,  "dims": (2.0, 1.8, 1.6)},
    "white rice":  {"nominal_mm": 6,  "dims": (6.0, 2.0, 1.6)},
    "ditalini":    {"nominal_mm": 7,  "dims": (7.0, 6.0, 6.0)},
    "wild rice":   {"nominal_mm": 10, "dims": (10.0, 1.6, 1.4)},
    "fideo":       {"nominal_mm": 15, "dims": (15.0, 1.2, 1.2)},
    "egg noodle":  {"nominal_mm": 20, "dims": (20.0, 6.0, 1.0)},
    "campanelle":  {"nominal_mm": 25, "dims": (25.0, 14.0, 12.0)},
    "farfalle":    {"nominal_mm": 35, "dims": (35.0, 22.0, 8.0)},
}


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class SlotPair:
    w0_mm: float = 6.0            # slot width of each plate (fully open)
    length_mm: float = 19.05      # slot length (3/4 in, matches SS-SLOT stock)
    pitch_mm: float = 9.0         # slot centre spacing across the width
    thickness_mm: float = 0.5     # 316L sheet, vendor-confirmed 0.3-0.8 mm range
    lead_mm: float = 1.25         # M8 lead screw pitch
    steps_per_rev: int = 3200     # 200-step motor x 16 microsteps
    material: str = "316L stainless (304 as cost comparator)"
    mode: str = "slot"            # "slot": sorts by thickness (smallest dim); "square": diagonal slide of two
                                  # square-hole plates, overlap stays square -> sorts by body width (2nd dim)

    def width(self, offset_mm):
        """slot: plate moves offset across the slot. square: plate moves offset along x AND y (diagonal,
        travel = offset * sqrt 2) and the overlap stays a square of side w0 - offset."""
        return round(max(0.0, self.w0_mm - offset_mm), 4)

    def offset_for(self, width_mm):
        if not 0 <= width_mm <= self.w0_mm:
            raise ValueError(f"width {width_mm} outside 0..{self.w0_mm} mm")
        return round(self.w0_mm - width_mm, 4)

    def travel_for(self, width_mm):
        return round(self.offset_for(width_mm) * (2 ** 0.5 if self.mode == "square" else 1.0), 4)

    def steps_for(self, width_mm):
        return round(self.travel_for(width_mm) / self.lead_mm * self.steps_per_rev)

    @property
    def resolution_mm(self):
        return self.lead_mm / self.steps_per_rev

    def open_area_fraction(self, width_mm):
        if self.mode == "square":
            return round(width_mm ** 2 / self.pitch_mm ** 2, 4)
        return round((width_mm * self.length_mm) / (self.pitch_mm * (self.length_mm + 2.0)), 4)


DEFAULT_PAIR = SlotPair()


def passes(dims, width_mm, length_mm, fit=0.95, mode="slot"):
    _a, b, c = sorted(dims, reverse=True)
    if mode == "square":
        return b <= width_mm * fit and c <= width_mm * fit
    return c <= width_mm * fit and b <= length_mm


def run(objects, widths, pair=DEFAULT_PAIR, measure=None, tol_mm=0.10, actuate_with_load=False):
    """objects: list of {"id", "name", "dims"}. widths: descending list (mm).
    measure(width) -> camera-measured width (default: exact). Returns trays, steps, mmr root, status."""
    widths = sorted(widths, reverse=True)
    measure = measure or (lambda w: w)
    on_stage, trays, steps, mmr = list(objects), {}, [], MMR()
    load = []                                          # specimens currently sitting on the plates
    status, break_at = "COMPLETED", None
    for k, w in enumerate(widths):
        g_empty = len(load) == 0
        leaf = {"step": k, "action": "set_width", "width_mm": w, "offset_mm": pair.offset_for(w),
                "travel_mm": pair.travel_for(w), "motor_steps": pair.steps_for(w), "mode": pair.mode, "G_empty": g_empty, "load": [o["id"] for o in load]}
        if not g_empty:
            leaf["result"] = "BREAK: plates would shear specimens"
            steps.append({**leaf, "leaf": H(leaf)}); mmr.append(steps[-1]["leaf"])
            status, break_at = "STOPPED_AT_BREAK_POINT", k; break
        m = measure(w)
        leaf["measured_mm"] = m; leaf["G_measured"] = abs(m - w) <= tol_mm
        if not leaf["G_measured"]:
            leaf["result"] = f"BREAK: measured {m} vs commanded {w} (tol {tol_mm})"
            steps.append({**leaf, "leaf": H(leaf)}); mmr.append(steps[-1]["leaf"])
            status, break_at = "STOPPED_AT_BREAK_POINT", k; break
        retained = [o for o in on_stage if not passes(o["dims"], m, pair.length_mm, mode=pair.mode)]
        passed = [o for o in on_stage if o not in retained]
        tray = f"T{k + 1} >= {w:g} mm"
        trays[tray] = [o["id"] for o in retained]
        leaf.update({"retained": [o["id"] for o in retained], "capture_tray": tray,
                     "G_capture": len(trays[tray]) == len(retained), "passed_n": len(passed), "result": "OK"})
        steps.append({**leaf, "leaf": H(leaf)}); mmr.append(steps[-1]["leaf"])
        on_stage = passed
        # retained specimens are flushed into the capture tray, leaving the stage empty for the next move;
        # fault injection: skip that flush, so the next actuation would happen under load
        load = retained if actuate_with_load else []
    if status == "COMPLETED":
        trays[f"pass-through < {widths[-1]:g} mm"] = [o["id"] for o in on_stage]
    return {"pair": pair.__dict__, "widths": widths, "trays": trays, "steps": steps, "status": status,
            "break_at": break_at, "mmr_root": mmr.root, "accounted": sum(len(v) for v in trays.values()) == len(objects)
            if status == "COMPLETED" else None}


def analog_objects(per=3):
    return [{"id": f"{n.replace(' ', '_')}#{i}", "name": n, "dims": v["dims"]} for n, v in ANALOGS.items() for i in range(per)]


def scad(pair=DEFAULT_PAIR, n_slots=5, rows=3):
    """OpenSCAD for the fixed plate, sliding plate and guide frame (mm). Slots run along y; the
    sliding plate moves along x by offset = w0 - width."""
    W = n_slots * pair.pitch_mm + 10; Lp = rows * (pair.length_mm + 4) + 8
    return f"""// baebugs variable-aperture slot pair (proof of concept; laser-cut 316L, deburr all edges)
// w0={pair.w0_mm} mm, slot length={pair.length_mm} mm, pitch={pair.pitch_mm} mm, sheet={pair.thickness_mm} mm
offset = 0;   // 0 = fully open ({pair.w0_mm} mm); width = {pair.w0_mm} - offset
module slot_plate(t) {{
  difference() {{
    cube([{W}, {Lp}, t]);
    for (i = [0:{n_slots - 1}], j = [0:{rows - 1}])
      translate([5 + i*{pair.pitch_mm}, 4 + j*{pair.length_mm + 4}, -1]) cube([{pair.w0_mm}, {pair.length_mm}, t + 2]);
    for (x = [2.5, {W - 2.5}], y = [2.5, {Lp - 2.5}]) translate([x, y, -1]) cylinder(d=2.2, h=t+2, $fn=24);
  }}
}}
slot_plate({pair.thickness_mm});                                        // fixed plate
color("silver") translate([offset, 0, {pair.thickness_mm}]) slot_plate({pair.thickness_mm});   // sliding plate
// printed guide frame: rails either side of the sliding plate, lead-screw boss on +x
color("white") difference() {{
  translate([-4, -4, -2]) cube([{W + 8 + 12}, {Lp + 8}, 2 + 2*{pair.thickness_mm} + 1.5]);
  translate([-0.2, -0.2, -0.1]) cube([{W} + 0.4 + {pair.w0_mm}, {Lp} + 0.4, 10]);
  translate([4, 4, -3]) cube([{W - 8}, {Lp - 8}, 5]);
}}
translate([{W + 10}, {Lp / 2}, {pair.thickness_mm}]) rotate([0, 90, 0]) color("gray") cylinder(d=8, h=40, $fn=24); // M8 lead screw
"""


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser("baebugs-variable-aperture")
    ap.add_argument("--out", default="print/filters/variable_aperture")
    ap.add_argument("--widths", default="6,3,1.5")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for mode in ("slot", "square"):
        r = run(analog_objects(), [float(x) for x in a.widths.split(",")], pair=SlotPair(mode=mode))
        (out / f"demo_run_{mode}.json").write_text(json.dumps(r, indent=1))
        print(mode, r["status"], r["mmr_root"][:16], {k: sorted({x.split("#")[0] for x in v}) for k, v in r["trays"].items()})
    (out / "slot_pair.scad").write_text(scad())

