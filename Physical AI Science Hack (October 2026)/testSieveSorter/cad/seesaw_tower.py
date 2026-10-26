"""Seesaw tower: how far apart the holder boxes have to hang when each tips about its own pivot across
its middle and neighbours tip opposite ways (docs/SYSTEM.md section 3, confirmed by the user at 10:50).

Each level is a box turned by +/-tilt about a Y axis through PIVOT (the middle of the box body at
mid-height: where seesaw_holder.py puts its pins). For each tilt the smallest pitch (pivot to pivot) that
leaves CLEAR mm between neighbours is found from the real solids: frame_holder.py's box with its +X
mounting tab, and seesaw_holder.py's box (no tab, pivot lugs in the middle of the long walls). The catch
pan keeps a box's rim and pivot and only reaches further down, so the same pitch holds above it.

The pitch is also roughly how far a specimen drops from one screen to the next (more at the end that
tips down). The clump session found those drops give the largest impact force on specimens, so the
smallest pitch that clears is the gentlest.

Writes out/seesaw_tower.png (SHOW_TILT, seesaw holders with the ribs-across inserts over the catch pan, at
the seesaw holder's pitch rounded up to 5 mm), its checks with the pitch table, and prints the table.

Run from this folder:  <venv python> seesaw_tower.py [tilt_deg ...]
"""
import json
import sys
import cadquery as cq
from cadkit import OUT, export_all
import frame_holder as box
import seesaw_holder as sh

PIVOT = (0.0, 0.0, sh.PIVOT_Z)     # body centre, mid-height
CLEAR = 3.0                        # mm left between neighbours at full tilt
TILTS = (5.0, 10.0, 15.0, 20.0, 25.0)   # the user is choosing among 5 / 10 / 15 (SYSTEM.md section 3)
SHOW_TILT = 10.0                   # the default until the user picks
LEVELS = ("sieve_insert_5mm_across", "sieve_insert_2mm_across")   # top first, then the catch pan


def level(b, tilt, z, pivot=PIVOT):
    """A solid tipped by tilt (deg, about +Y through pivot), raised by z."""
    p = cq.Vector(*pivot)
    return b.rotate(p, p + cq.Vector(0, 1, 0), tilt).translate((0, 0, z))


def clearance(b, tilt, pitch):
    """The smaller gap over both half-cycles: the -X ends close in on one, the +X ends on the other."""
    return min(level(b, s * tilt, 0).val().distance(level(b, -s * tilt, pitch).val()) for s in (1, -1))


def min_pitch(b, tilt, clear=CLEAR):
    lo, hi = box.H, 300.0          # touching at lo (rim on rim), clear at hi
    while hi - lo > 0.25:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if clearance(b, tilt, mid) < clear else (lo, mid)
    return hi


def tower(tilt, pitch):
    """Seesaw holders with LEVELS' inserts (top first) over the catch pan, neighbours tipped opposite ways,
    the catch pan +X end up. A compound, not a union: a preview, and the 2 mm screen is slow to fuse. The
    inserts come from their STEP files in out/ (run sieve_insert.py first)."""
    pan, pan_info = sh.catch_pan()
    pivot_pan = tuple(pan_info["pivot_mm"])
    parts = [level(pan, -tilt, -pivot_pan[2], pivot_pan)]          # its pivot at z = 0
    for k, name in enumerate(reversed(LEVELS), start=1):          # bottom box first
        t = tilt if k % 2 else -tilt
        z = k * pitch - PIVOT[2]
        insert = cq.importers.importStep(str(OUT / f"{name}.step"))
        parts.append(level(sh.holder()[0], t, z))
        parts.append(level(insert.translate((0, 0, box.LEDGE_T)), t, z))
    return cq.Workplane("XY").add(cq.Compound.makeCompound([p.val() for p in parts]))


if __name__ == "__main__":
    tilts = [float(a) for a in sys.argv[1:]] or list(TILTS)
    with_tab, seesaw = box.frame(), sh.holder()[0]
    table = []
    for t in tilts:
        row = {"tilt_deg": t, "min_pitch_mm_frame_holder_with_tab": round(min_pitch(with_tab, t), 1),
               "min_pitch_mm_seesaw_holder": round(min_pitch(seesaw, t), 1)}
        table.append(row)
        print(json.dumps(row))
    show = next((r for r in table if r["tilt_deg"] == SHOW_TILT), table[len(table) // 2])
    pitch = -(-show["min_pitch_mm_seesaw_holder"] // 5) * 5          # rounded up to 5 mm
    info = {"preview_only": True, "pivot_mm": list(PIVOT), "clearance_mm": CLEAR, "levels_top_first": [*LEVELS, "seesaw_catch_pan"],
            "shown_tilt_deg": show["tilt_deg"], "shown_pitch_mm": pitch, "pitch_table": table,
            "note": "pitch = pivot to pivot, about the drop from screen to screen; neighbours tip opposite ways"}
    print("seesaw_tower", json.dumps(export_all(tower(show["tilt_deg"], pitch), "seesaw_tower", info)))
