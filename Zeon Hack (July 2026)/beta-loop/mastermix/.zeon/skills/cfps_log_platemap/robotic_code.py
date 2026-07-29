"""Super-skill: print the destination plate map to the run log as text art.

Renders an 8x12 (A-H x 1-12) grid marking which wells are Positive (P), Negative
(N), or Sample (S), so the operator can see the planned layout in the run log.
Logging only — no arm motion, no liquid handling.
"""

from protocol_schema import SkillObject
from utils import object_display_name

from .modules import print_log

ROWS = "ABCDEFGH"
NCOLS = 12
EMPTY = "."


def _rl(msg, kind="event"):
    """Emit a run-log line (shown in the run log panel)."""
    print_log(msg, runlog=True, runlog_type=kind)


def _parse(wells):
    return [w.strip().upper() for w in str(wells).replace(";", ",").split(",") if w.strip()]


def cfps_log_platemap(
    reaction_plate: SkillObject = None,
    pos_wells: str = "",
    neg_wells: str = "",
    sample_wells: str = "",
):
    """Log the destination plate layout as a text grid (P / N / S / .).

    Args:
        reaction_plate: Destination plate (used only to name the map).
        pos_wells, neg_wells, sample_wells: comma-separated well lists per
            condition (e.g. "A1", "A2", "A3,A4").
    """
    print_log(runlog=True, runlog_type="step_start")
    plate_name = object_display_name(reaction_plate, fallback="destination plate") if reaction_plate is not None else "destination plate"

    mapping = {}
    for sym, wells in (("P", pos_wells), ("N", neg_wells), ("S", sample_wells)):
        for w in _parse(wells):
            mapping[w] = sym

    counts = {"P": 0, "N": 0, "S": 0}
    for v in mapping.values():
        if v in counts:
            counts[v] += 1

    _rl(f"+-- Plate map: {plate_name}   (P=positive  N=negative  S=sample  .=empty) --+")
    _rl("     " + " ".join(f"{c:>2}" for c in range(1, NCOLS + 1)))
    for r in ROWS:
        cells = " ".join(f"{mapping.get(f'{r}{c}', EMPTY):>2}" for c in range(1, NCOLS + 1))
        _rl(f"  {r}  {cells}")
    _rl(f"+-- Wells: {counts['P']} positive, {counts['N']} negative, {counts['S']} sample ({sum(counts.values())} total) --+")

    return {"success": True, "counts": counts}
