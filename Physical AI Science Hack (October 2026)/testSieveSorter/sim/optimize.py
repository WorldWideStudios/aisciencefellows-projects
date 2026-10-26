"""Sim-driven design optimizer: propose design variants, run each in the sim across every friction set and
several seeds, score them, keep the leaders and refine around them. Writes the design log, the leaderboard
and the winners the CAD can build.

Run from sim\\ (on this laptop: the WSL venv ~/venvs/sieve, see docs/sessions/README.md):
    python optimize.py run --study demo [--rounds 3] [--workers 16]     baselines + Latin hypercube, then
                                                                         cross-entropy rounds; resumes from the cache
    python optimize.py report --study demo                               rebuild leaderboard / winners / log tables
    python optimize.py replay --study demo [--top 3]                     record the winners and build their view.html
    python optimize.py plan --study demo                                 print the round plan and a cost estimate
    python optimize.py verify --study demo [--top 4]                     rerun the flagged leaders with stiffer contacts
                                                                         (dt 0.125 ms, timeconst 0.25 ms); a design that
                                                                         comes back unflagged counts as clean
    python optimize.py stress --study demo [--top 3] [--ramps 0.005,0.02] [--undersize 0.05,0.25]
                                                                         rerun the leaders with other stroke reversal
                                                                         times (the 0.01 s ramp is a guess) and other
                                                                         printer undersizes (0.15 mm is assumed)

Studies (classes are what the sorter should do, not what each design's openings happen to do):
    demo      pasta + chickpea / rice / quinoa: the surrogate grains we can bench today
    insects   BugPicker's body-length classes > 6 / 2-6 / < 2 mm, generated specimens (EXPLORATORY: none measured)

Families (each maps one to one onto CAD parameters, so a winner can be printed as is):
    gated     cad/gated_container.py: floor slope, L1 strip (width gap with its own height, or tunnel), L2 tunnel,
              tunnel width, tooth, drop-slot length
    plinko    cad/plinko_layers.py LAYERS: rod gap, rod top width and rod height per layer
    inserts   cad/sieve_insert.py INSERTS: square hole and bar per insert
    gated_rib gated + a ratchet floor (PROPOSAL geometry, not in the CAD): tested and rejected, see opt/LOG.md;
              not run unless named in --families. The mid-slot tower (designs_gated.py gx=, flip=0) was rejected too.
    every family also searches the stroke within BioKEA's firmware: constant speed <= 50 mm/s, amplitude 5-15 mm

Sizes. The search runs on CAD (nominal) openings on 0.1 mm steps; the sim builds the as-printed (effective)
opening, nominal - UNDERSIZE_MM, as the sieve-gate-design skill prescribes. UNDERSIZE_MM is ASSUMED until
cad/hole_gauge.py is printed and measured. Vertical (Z) features are on 0.2 mm layer multiples.

Score of one run (classes c, each with its target bin = the c-th zone of the design in flow order):
    quality  = min over classes of min(purity_c, recovery_c)
    score    = quality - W_JAM * between/N - W_LOST * lost/N - W_T90 * t90/duration (1 if 90% never sorted)
    a run that errors, goes unstable (MuJoCo's BADQACC reset) or ends with a non-finite state scores FAIL_SCORE
Candidate: every friction set x every seed; robust score = mean - 1 sd over those runs (ranking key); the
worst friction set's mean is reported beside it. A run whose particle-vs-tray overlap reaches 0.5 x the
design's tightest gate clearance is flagged untrustworthy, and so is the candidate.
Search: successive halving. Every candidate is screened at SCREEN_S; the top PROMOTE share of each family
(at least one) and the references are rerun at FULL_S. A short screen hasn't finished sorting (the gated tower
needs well over 8 s to walk grains down two floors), so the strict worst-class score is ~0 for everything; the
screen ranks by sorting progress instead: mean class recovery - 2 x leaked share (a particle already past its
bin; drops are one-way) - W_JAM x jammed - W_LOST x lost. Latin hypercube in round 0, then cross-entropy
refinement (elite mean and spread per family, categorical weights for gate kinds; full-run results first).

Reuses sweep.py (make_cfg, param_sets, run_metrics, jsonable, FIRMWARE) without changing it. Raw runs go to
out/opt/<study>/ (gitignored); opt/LOG.md, opt/leaderboard*.md and opt/winners*.json are committed.
"""
import argparse
import dataclasses
import functools
import hashlib
import json
import math
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np

import sweep

HERE = Path(__file__).resolve().parent
OPT = HERE / "opt"
OUT = HERE / "out" / "opt"
MAX_WORKERS = 16                 # the physics session keeps the rest of the 24 cores
SCREEN_S, FULL_S = 8.0, 30.0
# Stiffer contacts than sorter.py's default (dt 0.5 ms, timeconst 2 ms): in the physics session's instability
# probe (testSieveSorter-physics sim/out/instab/probe*.jsonl, 1056 runs, none unstable) the default let particles
# sink a median 0.49 mm into the tray (max 0.81), more than the 0.15-0.3 mm clearance of the rice / quinoa
# tunnel; dt 0.25 ms with timeconst 0.5 ms gave a median 0.07 mm (max 0.18) for about 1.6x the wall time.
# Switch to sim/PERF.md's settings once the physics session commits them.
DT, TIMECONST = 2.5e-4, 5e-4
STIFF_DT, STIFF_TIMECONST = 1.25e-4, 2.5e-4   # `verify`: half the overlap, about 2x the wall time
SEEDS = (0, 1, 2)
SCREEN_SEEDS = SEEDS             # run --screen-seeds 1: screen on seed 0 only (slow seesaw runs)
FULL_SEEDS = SEEDS               # run --full-seeds 2: the full runs on the first two seeds
PROMOTE = 0.2
UNDERSIZE_MM = 0.15              # ASSUMED: nominal minus printed opening (XY); replace with hole_gauge data
Z_STEP, XY_STEP = 0.2, 0.1       # layer height for vertical features; opening step
MIN_FEATURE = 0.4
MIN_LINES = 0.8                  # bambu's build_winners.py: thinner rods / teeth / bars than two 0.4 mm lines are fragile
W_JAM, W_LOST, W_T90 = 0.5, 1.0, 0.05
FAIL_SCORE = -1.0
MIN_WINNER = 0.5                 # a winner must be a working sorter: worst class at about 50% or better
PEN_FLAG = 0.5                   # flag a run when tray overlap >= PEN_FLAG x the tightest gate clearance
SPECIAL = ("between", "lost")
FIRMWARE = dict(sweep.FIRMWARE)  # constant_speed, amp 10, 50 mm/s, ramp 0.01 s
RAMP_S = FIRMWARE["ramp_s"]

STUDIES = {
    "demo": {
        "title": "Demo set: surrogate grains (pasta + chickpea / rice / quinoa)",
        "mix": {"rice": 30, "quinoa": 30, "chickpea": 8, "pasta": 8},
        "classes": [{"name": "big (pasta, chickpea)", "kinds": ["chickpea", "pasta"]},
                    {"name": "rice", "kinds": ["rice"]},
                    {"name": "quinoa", "kinds": ["quinoa"]}],
        "exploratory": False,
    },
    "insects": {
        "title": "EXPLORATORY: generated insects in BugPicker's body-length classes",
        "mix": {"insect_compact": 25, "insect_elongate": 25, "insect_longleg": 15},
        "classes": [{"name": "> 6 mm", "min_length": 6.0},
                    {"name": "2-6 mm", "min_length": 2.0, "max_length": 6.0},
                    {"name": "< 2 mm", "max_length": 2.0}],
        "exploratory": True,
    },
}


STUDIES["smoke"] = dict(STUDIES["demo"], title="smoke test (not a result)")
# The rig's motion (SYSTEM.md section 3, the user at 10:50 and 11:20): each tray rocks about its own pivot across the
# middle (axis y, the ends tip), neighbours in opposite phase, +/-5-15 deg. rocking.py's lab-frame hinges, one per
# level; no translation. The stroke parameters are SEESAW_PARAMS instead of STROKE_PARAMS.
STUDIES["seesaw"] = dict(STUDIES["demo"], seesaw=True,
                         title="Demo set on the rig's seesaw: each tray rocks about its middle (the ends tip), "
                               "neighbours alternate, +/-5-15 deg (rocking.py)")

# ---------------------------------------------------------------- families

@dataclasses.dataclass
class P:
    name: str
    lo: float
    hi: float
    step: float
    choices: tuple = ()          # categorical when set

    def quant(self, v):
        if self.choices:
            return v
        v = min(max(v, self.lo), self.hi)
        return round(round(v / self.step) * self.step, 4)


# Two drives: BioKEA's stage (firmware: constant speed <= 50 mm/s, 5-15 mm amplitude) and a vibrating tool like the demo
# rig's (sine; frequency and peak acceleration; amplitude follows). angle_deg tilts the stroke from the design's flow axis
# (0) to straight up (90) (sorter.py stroke_axis, docs/sessions/demo-rig.md). Older candidates have no drive or angle:
# firmware and 0 deg, so their strokes and cache keys are unchanged.
STROKE_PARAMS = [P("drive", 0, 0, 0, ("firmware", "tool", "rock")), P("amp", 5.0, 15.0, 0.5),
                 P("speed", 15.0, 50.0, 1.0), P("freq", 10.0, 50.0, 1.0), P("accel", 1.0, 5.0, 0.1),
                 P("angle", 0.0, 90.0, 5.0), P("rock_axis", 0, 0, 0, ("x", "y")), P("rock_deg", 2.0, 30.0, 0.5),
                 P("rock_period", 0.4, 6.0, 0.1)]
# rock: the tray seesaws about a horizontal axis through its centre (the user, 10:10: "side to side like a seesaw",
# trays on side pivots). x = about the tray's long axis (the width tips), y = about its short axis (the ends tip).
# The tilt runs at constant angular speed between +/- rock_deg with hard reversals (the firmware's motion, mapped
# through a lever), so the reversal jolt is there too. Pivot axis and amplitude are unmeasured: searched.
# Confirmed by the user at 10:50 (SYSTEM.md section 3): the ends tip, about a pivot across the middle (axis y), about
# 20-30 deg either side, neighbouring levels in opposite phase (not modelled here: every particle turns in phase).
# Rounds up to 7 searched 2-20 deg with x as the default; only y-axis runs count as the rig's motor (RIG_ROCK_AXIS).
ROCK_DEFAULT = {"rock_axis": "y", "rock_deg": 20.0, "rock_period": 1.6}
RIG_ROCK_AXIS = "y"
# The seesaw studies' stroke: rocking.py's seesaw: stroke, alternating levels. The user hasn't picked the angle from
# the 5 / 10 / 15 deg renders (default 10), the period and profile are unmeasured: all searched. A one-box design
# (plinko) rocks as one level (one_box_seesaw). Towers are spaced by pitch (box bottom to box bottom): at +/-15 deg
# neighbours touch at 72 mm with the +X tab (rocking.py), and PLAN.md asks for 85-110.
SEESAW_PARAMS = [P("ss_deg", 5.0, 15.0, 0.5), P("ss_period", 0.4, 6.0, 0.1),
                 P("ss_shape", 0, 0, 0, ("constant_speed", "sine")), P("vib_mm", 0.0, 0.5, 0.05)]
# vib_mm (from round 1): rocking.py's buzz of the whole tower on top of the seesaw, 40 Hz straight up (the tool's);
# the seesaw session saw 0.3 mm (1.9 g) clear the stuck quinoa and chia off the 5 mm tray (SEESAW.md, 12:30).
VIB_HZ = 40.0
PITCH = P("pitch", 80.0, 110.0, 5.0)
SEESAW_DEFAULT = {"ss_deg": 10.0, "ss_period": 2.0, "ss_shape": "constant_speed", "pitch": 85.0}
FORCE_DRIVE = None                # run --drive rock: every new candidate (and reference) of this run uses that drive
CE_DEFAULTS = {"drive": "firmware", "angle": 0.0}     # what a candidate without these params ran with


def eff(nominal):
    """The as-printed opening the sim builds for a CAD opening."""
    return round(nominal - UNDERSIZE_MM, 4)


def tok(v):
    return f"{v:g}".replace(".", "p")


def cadtok(v):
    """CAD part names follow the repo: one decimal, e.g. gate_w3p0, layer_2_rods_1p4."""
    return f"{v:.1f}".replace(".", "p")


# gated -------------------------------------------------------------------------------------------
def gated_spec(p):
    s1, s2 = eff(p["s1"]), eff(p["s2"])
    l1 = f"w{tok(s1)}x{tok(eff(p['gh']))}" if p["k1"] == "w" else f"t{tok(s1)}"
    l2 = f"w{tok(s2)}x{tok(eff(p['gh']))}" if p.get("k2", "t") == "w" else f"t{tok(s2)}"
    rib = f",rib={p['rib_h']:g}x{p['rib_pitch']:g}x{p['rib_steep']:g}" if "rib_h" in p else ""
    return (f"gated:{p['slope']:g},{l1},{l2},tw={eff(p['tw']):g},tooth={p['tooth'] + UNDERSIZE_MM:g},"
            f"slot={p['slot']:g}{rib}")


def gated_ok(p):
    if p["s1"] <= p["s2"] + 0.4:
        return "L1 opening must be well above the L2 opening"
    if min(p["s1"], p["s2"], p["tw"], p["tooth"], p["gh"]) < MIN_FEATURE:
        return "feature under 0.4 mm"
    return None


def gated_cad(p):
    k2 = p.get("k2", "t")
    s1n = f"gate_{p['k1']}{cadtok(p['s1'])}"
    s2n = f"gate_{k2}{cadtok(p['s2'])}"
    out = {"file": "cad/gated_container.py",
           "constants": {"FLOOR_SLOPE_DEG": p["slope"], "GATE_H": p["gh"] if "w" in (p["k1"], k2) else 8.0,
                         "TUNNEL_W": p["tw"], "TOOTH": p["tooth"],
                         "GATE_X": round(61.0 - p["slot"] - 1.0, 3)},
           "STRIPS": {s1n: [p["k1"], p["s1"]], s2n: [k2, p["s2"]]},
           "tower": [f"L1 (top, gate at +X): {s1n}", f"L2 (flipped 180 deg): {s2n}", "catch pan under L2"],
           "note": "GATE_H applies to every w strip, TUNNEL_W to every t strip: build each winner with its own "
                   "constants. GATE_X = OPEN_X - slot - STRIP_T / 2."}
    if "rib_h" in p:
        out["ratchet_floor_PROPOSAL"] = {
            "RIB_H": p["rib_h"], "RIB_PITCH": p["rib_pitch"], "RIB_STEEP": p["rib_steep"], "RIB_CLEAR": 3.0,
            "geometry": "not in gated_container.py yet: sawtooth ribs across the full inside width on the sloped "
                        "floor, from the upstream wall to 3 mm before the strip's upstream face, one every RIB_PITCH "
                        "mm. Each rises RIB_H above the floor surface along (1 - RIB_STEEP) x RIB_PITCH toward the "
                        "gate, then drops back over RIB_STEEP x RIB_PITCH on the gate side. Print right side up; "
                        "RIB_H is a Z feature (0.2 mm layers). Sim: sim/designs_gated.py rib=<h>x<pitch>x<steep>."}
    return out


def gated_show(p):
    l1 = f"w{p['s1']:g}x{p['gh']:g}" if p["k1"] == "w" else f"t{p['s1']:g}"
    l2 = f"w{p['s2']:g}x{p['gh']:g}" if p.get("k2", "t") == "w" else f"t{p['s2']:g}"
    rib = (f"; ratchet ribs {p['rib_h']:g} tall every {p['rib_pitch']:g} (steep {p['rib_steep']:g})"
           if "rib_h" in p else "")
    return (f"L1 {l1} / L2 {l2}; slope {p['slope']:g} deg, tunnel width {p['tw']:g}, tooth {p['tooth']:g}, "
            f"slot {p['slot']:g}{rib}")


# gated_mid: the unflipped mid-slot tower (designs_gated gx= / slot= / flip=0). L1's strip sits at gx1 with its drop
# slot, then a wedge; L2 is today's container (strip at 53, slot 7). Nothing is flipped, so every gate is at +X and an
# angled throw conveys toward all of them.
MID_L2_X, MID_L2_SLOT = 53.0, 7.0


def gated_mid_spec(p):
    return gated_spec(p).replace(f"slot={p['slot']:g}", "") .rstrip(",") + \
        f",slot={p['slot']:g}/{MID_L2_SLOT:g},gx={p['gx1']:g}/{MID_L2_X:g},flip=0"


def gated_mid_ok(p):
    if p["gx1"] + 1.0 + p["slot"] > MID_L2_X - 1.0 - 7.0:
        return "L1's slot must end at least 7 mm upstream of L2's strip"
    return gated_ok(p)


def gated_mid_cad(p):
    out = gated_cad(p)
    out["constants"]["GATE_X"] = MID_L2_X      # what today's script builds: L2. L1 is in the proposal below
    out["buildable_with_todays_cad"] = False
    out["tower"] = [f"L1 (top): {list(out['STRIPS'])[0]} at x {p['gx1']:g}, drop slot {p['slot']:g} mm, wedge beyond",
                    f"L2 (NOT flipped): {list(out['STRIPS'])[1]} at x {MID_L2_X:g}, standard slot and ramp",
                    "catch pan under L2"]
    out["mid_slot_PROPOSAL"] = {"L1_GATE_X": p["gx1"], "L1_slot_mm": p["slot"], "L2_GATE_X": MID_L2_X,
                                "L2_slot_mm": MID_L2_SLOT, "flip_levels": False, "description": (
        "not in gated_container.py yet: L1 needs its strip rails at GATE_X = L1_GATE_X and its drop slot from the strip's "
        "downstream face for `slot` mm (|y| < OPEN_Y), then a solid wedge from the slot's far edge to the +X end wall, "
        "rising at 30 deg from a 0.4 mm lip and capped 2 mm under the wall top. L2 is the standard container. Levels "
        "are not flipped. Sim: sim/designs_gated.py gx= / slot= / flip=0.")}
    return out


def gated_mid_show(p):
    return gated_show(p).replace(f"slot {p['slot']:g}", f"L1 gate at x {p['gx1']:g} with slot {p['slot']:g}, "
                                                        f"L2 at x {MID_L2_X:g}, unflipped")


# plinko ------------------------------------------------------------------------------------------
PLINKO_WALLS = (12.0, 8.0, 6.0)        # cad/plinko_layers.py wall heights and tab x, unchanged
PLINKO_TABS = (0.0, -35.0, 35.0)


def plinko_layers(p, effective):
    f = eff if effective else (lambda v: v)
    return [["layer_1_rods", "rods", f(p["g1"]), p["b1"] + (UNDERSIZE_MM if effective else 0.0), p["h1"],
             PLINKO_WALLS[0], PLINKO_TABS[0]],
            ["layer_2_rods", "rods", f(p["g2"]), p["b2"] + (UNDERSIZE_MM if effective else 0.0), p["h2"],
             PLINKO_WALLS[1], PLINKO_TABS[1]],
            ["layer_3_catch", "solid", None, None, 2.0, PLINKO_WALLS[2], PLINKO_TABS[2]]]


def plinko_show(p):
    return (f"rods L1 gap {p['g1']:g} (rod {p['b1']:g} wide, {p['h1']:g} tall) / L2 gap {p['g2']:g} "
            f"(rod {p['b2']:g}, {p['h2']:g})")


def plinko_ok(p):
    taper = math.tan(math.radians(8.0))
    for b, h in ((p["b1"], p["h1"]), (p["b2"], p["h2"])):
        if b - 2 * h * taper < MIN_LINES:
            return "rod bottom under 0.8 mm, two print lines (rods taper 8 deg; bambu's build_winners.py flag)"
    if p["g1"] <= p["g2"] + 0.5:
        return "layer 1 gap must be well above layer 2's"
    return None


def plinko_cad(p):
    rows = plinko_layers(p, effective=False)
    return {"file": "cad/plinko_layers.py",
            "LAYERS": [[f"layer_1_rods_{cadtok(p['g1'])}", *rows[0][1:]], [f"layer_2_rods_{cadtok(p['g2'])}", *rows[1][1:]],
                       rows[2]],
            "note": "rows are (name, floor, gap, rod top width, rod height, wall height, tab x); walls and tabs unchanged"}


# inserts -----------------------------------------------------------------------------------------
INSERT_T = (1.6, 1.4)                  # screen thickness per insert (Z, unchanged from sieve_insert.py)


def insert_names(p):
    return [f"h{tok(eff(p['a1']))}b{tok(p['bar1'] + UNDERSIZE_MM)}", f"h{tok(eff(p['a2']))}b{tok(p['bar2'] + UNDERSIZE_MM)}"]


def inserts_spec(p):
    return "inserts:" + ",".join(insert_names(p)) + (f",pitch={p['pitch']:g}" if "pitch" in p else "")


def inserts_inject(p):
    n1, n2 = insert_names(p)
    return {"sieve_insert.INSERTS": {f"sieve_insert_{n1}": [eff(p["a1"]), p["bar1"] + UNDERSIZE_MM, INSERT_T[0]],
                                     f"sieve_insert_{n2}": [eff(p["a2"]), p["bar2"] + UNDERSIZE_MM, INSERT_T[1]]}}


def inserts_show(p):
    return f"square holes {p['a1']:g} (bar {p['bar1']:g}) / {p['a2']:g} (bar {p['bar2']:g})"


def inserts_ok(p):
    return None if p["a1"] > p["a2"] + 0.5 else "insert 1 hole must be well above insert 2's"


def inserts_cad(p):
    return {"file": "cad/sieve_insert.py",
            "INSERTS": {f"sieve_insert_{tok(p['a1'])}mm": [p["a1"], p["bar1"], INSERT_T[0]],
                        f"sieve_insert_{tok(p['a2'])}mm": [p["a2"], p["bar2"], INSERT_T[1]]},
            "note": "(hole, bar, screen thickness); one insert per holder box, coarse on top"}


FAMILIES = {
    "gated": {
        "params": [P("slope", 0.5, 4.0, 0.1), P("k1", 0, 0, 0, ("w", "t")), P("s1", 2.3, 5.4, XY_STEP),
                   P("gh", 2.4, 8.0, XY_STEP), P("s2", 1.2, 2.0, XY_STEP), P("tw", 3.0, 12.0, XY_STEP),
                   P("tooth", 0.8, 3.0, XY_STEP), P("slot", 6.0, 14.0, XY_STEP), *STROKE_PARAMS],
        "spec": gated_spec, "inject": lambda p: {}, "ok": gated_ok, "cad": gated_cad, "show": gated_show,
    },
    "gated_rib": {
        "params": [P("slope", 0.5, 4.0, 0.1), P("k1", 0, 0, 0, ("w", "t")), P("s1", 2.3, 5.4, XY_STEP),
                   P("gh", 2.4, 8.0, XY_STEP), P("s2", 1.2, 2.0, XY_STEP), P("tw", 3.0, 12.0, XY_STEP),
                   P("tooth", 0.8, 3.0, XY_STEP), P("slot", 6.0, 14.0, XY_STEP), P("rib_h", 0.4, 1.4, Z_STEP),
                   P("rib_pitch", 3.0, 12.0, XY_STEP), P("rib_steep", 0.05, 0.4, 0.05), *STROKE_PARAMS],
        "spec": gated_spec, "inject": lambda p: {}, "ok": gated_ok, "cad": gated_cad, "show": gated_show,
    },
    "gated_mid": {
        "params": [P("slope", 0.0, 4.0, 0.1), P("k1", 0, 0, 0, ("w", "t")), P("s1", 2.3, 5.4, XY_STEP),
                   P("gh", 2.4, 8.0, XY_STEP), P("s2", 1.2, 2.0, XY_STEP), P("tw", 3.0, 12.0, XY_STEP),
                   P("tooth", 0.8, 3.0, XY_STEP), P("gx1", 14.0, 38.0, XY_STEP), P("slot", 6.0, 14.0, XY_STEP),
                   *STROKE_PARAMS],
        "spec": gated_mid_spec, "inject": lambda p: {}, "ok": gated_mid_ok, "cad": gated_mid_cad, "show": gated_mid_show,
    },
    "plinko": {
        "params": [P("g1", 2.6, 5.6, XY_STEP), P("b1", 1.2, 4.0, XY_STEP), P("h1", 1.6, 4.0, Z_STEP),
                   P("g2", 1.2, 2.0, XY_STEP), P("b2", 1.0, 3.0, XY_STEP), P("h2", 1.6, 3.6, Z_STEP), *STROKE_PARAMS],
        "spec": lambda p: "plinko",
        "inject": lambda p: {"plinko_layers.LAYERS": plinko_layers(p, effective=True)},
        "ok": plinko_ok, "cad": plinko_cad, "show": plinko_show,
    },
    "inserts": {
        "params": [P("a1", 2.6, 6.0, XY_STEP), P("bar1", 0.8, 2.0, XY_STEP), P("a2", 1.2, 2.6, XY_STEP),
                   P("bar2", 0.8, 1.6, XY_STEP), *STROKE_PARAMS],
        "spec": inserts_spec, "inject": inserts_inject, "ok": inserts_ok, "cad": inserts_cad, "show": inserts_show,
    },
}

# Per-study search ranges where a study's items need other sizes: {study: {family: {param: P}}}. Insects: L1 keeps
# bodies over 6 mm (about 2-3 mm thick; gatecalc t2.75 effective), L2 keeps 2-6 mm (cut near 1 mm; gatecalc w1.05).
STUDY_RANGES = {
    "insects": {
        **{fam: {"s1": P("s1", 1.8, 4.2, XY_STEP), "k2": P("k2", 0, 0, 0, ("w", "t")), "s2": P("s2", 0.8, 1.6, XY_STEP),
                 "gh": P("gh", 1.2, 8.0, XY_STEP), "tw": P("tw", 2.0, 10.0, XY_STEP)}
           for fam in ("gated", "gated_rib", "gated_mid")},
        "plinko": {"g1": P("g1", 1.6, 4.2, XY_STEP), "g2": P("g2", 0.8, 1.6, XY_STEP), "b2": P("b2", 0.8, 3.0, XY_STEP)},
        "inserts": {"a1": P("a1", 1.8, 4.5, XY_STEP), "a2": P("a2", 0.8, 1.8, XY_STEP)},
    },
}


def params_of(family, study):
    """The family's parameters for a study: its ranges with the study's overrides, plus the study's extras."""
    over = STUDY_RANGES.get(study, {}).get(family, {})
    base = [over.get(q.name, q) for q in FAMILIES[family]["params"]]
    if STUDIES[study].get("seesaw"):
        strokes = {q.name for q in STROKE_PARAMS}
        base = [q for q in base if q.name not in strokes] + SEESAW_PARAMS + ([PITCH] if family == "inserts" else [])
    names = {q.name for q in base}
    return base + [q for n, q in over.items() if n not in names]


# Fixed reference designs, never tuned. CAD numbers as they are in the repo today, built at the effective size.
BASELINES = {
    "demo": [
        ("gated", "README final design: gated, 2 deg, existing strips w5.0 / t1.4, firmware cap stroke",
         {"slope": 2.0, "k1": "w", "s1": 5.0, "gh": 8.0, "s2": 1.4, "tw": 8.0, "tooth": 2.0, "slot": 7.0,
          "amp": 10.0, "speed": 50.0}),
        ("gated", "gatecalc plan (skill): gated, t3.8 / t1.6 nominal (its t1.55 on the 0.1 mm grid), firmware cap",
         {"slope": 2.0, "k1": "t", "s1": 3.8, "gh": 8.0, "s2": 1.6, "tw": 8.0, "tooth": 2.0, "slot": 7.0,
          "amp": 10.0, "speed": 50.0}),
        ("plinko", "plinko_layers.py as in the repo: rods 5.0 / 1.4, firmware cap stroke",
         {"g1": 5.0, "b1": 2.4, "h1": 3.0, "g2": 1.4, "b2": 2.0, "h2": 2.6, "amp": 10.0, "speed": 50.0}),
        ("inserts", "printed inserts as in the repo: 5 mm / 2 mm square holes, firmware cap stroke",
         {"a1": 5.0, "bar1": 1.2, "a2": 2.0, "bar2": 1.0, "amp": 10.0, "speed": 50.0}),
        ("inserts", "DEMO RIG the team built: stacked printed 5 mm / 2 mm trays (inserts:5mm,2mm), shaken up and down "
                    "(sine 20 Hz, 2 g, 90 deg; assumed tool motion, sim/VERTICAL.md)",
         {"a1": 5.0, "bar1": 1.2, "a2": 2.0, "bar2": 1.0, "drive": "tool", "freq": 20.0, "accel": 2.0, "angle": 90.0}),
    ],
}
BASELINES["smoke"] = BASELINES["demo"]
BASELINES["seesaw"] = [
    ("plinko", "plinko_layers.py as in the repo: rods 5.0 / 1.4, one box on the default seesaw (+/-10 deg, 2 s)",
     {"g1": 5.0, "b1": 2.4, "h1": 3.0, "g2": 1.4, "b2": 2.0, "h2": 2.6, **SEESAW_DEFAULT}),
    ("plinko", "the demo study's leader P-b192da7c (rods 4.7 / 1.6, made for a 37 Hz tool) on the default seesaw",
     {"g1": 4.7, "b1": 2.6, "h1": 2.2, "g2": 1.6, "b2": 2.3, "h2": 3.2, **SEESAW_DEFAULT}),
    ("inserts", "DEMO RIG the team built: printed 5 mm / 2 mm trays, 85 mm apart, on the default seesaw "
                "(+/-10 deg, 2 s, neighbours alternate)",
     {"a1": 5.0, "bar1": 1.2, "a2": 2.0, "bar2": 1.0, **SEESAW_DEFAULT}),
    ("inserts", "DEMO RIG on the default seesaw + a 0.3 mm buzz at 40 Hz (1.9 g; SEESAW.md 12:30)",
     {"a1": 5.0, "bar1": 1.2, "a2": 2.0, "bar2": 1.0, **SEESAW_DEFAULT, "vib_mm": 0.3}),
]
# bambu's seesaw parts (not a family: the ribs-across inserts aren't parametric yet): 5 / 2 mm holes with ridges
# along Y only and 45 deg border ramps, in the tabless seesaw holder over the deep catch pan with its lip.
ACROSS = {"family": "across", "label": "RIBS ACROSS (bambu): 5mm_across / 2mm_across in the seesaw holder, 85 mm apart",
          "spec": "inserts:5mm_across,2mm_across,pitch=85,holder=seesaw", "inject": {}, "params": {}}
BASELINES["insects"] = [
    ("gated", "gatecalc plan (skill) for the length classes: gated t2.9 / w1.2 (8 tall), firmware cap stroke",
     {"slope": 2.0, "k1": "t", "s1": 2.9, "gh": 8.0, "k2": "w", "s2": 1.2, "tw": 8.0, "tooth": 2.0, "slot": 7.0,
      "amp": 10.0, "speed": 50.0}),
    ("plinko", "plinko_layers.py as in the repo: rods 5.0 / 1.4, firmware cap stroke",
     {"g1": 5.0, "b1": 2.4, "h1": 3.0, "g2": 1.4, "b2": 2.0, "h2": 2.6, "amp": 10.0, "speed": 50.0}),
    ("inserts", "printed inserts as in the repo: 5 mm / 2 mm square holes, firmware cap stroke",
     {"a1": 5.0, "bar1": 1.2, "a2": 2.0, "bar2": 1.0, "amp": 10.0, "speed": 50.0}),
]
# Today's bench setup: glued woven mesh (not a family: it isn't printable). Reported for reference.
CURRENT = {"family": "current", "label": "TODAY on the bench: glued mesh inserts mesh5 / mesh2, firmware cap stroke",
           "spec": "inserts:mesh5,mesh2", "inject": {}, "stroke": FIRMWARE, "params": {}}
# The demo rig the team built (docs/sessions/demo-rig.md): one 5 mm printed insert on a vibrating tool, shaken up and
# down as in the video. The tool's motion is an assumption (sim/VERTICAL.md: sine 20 Hz, 2 g, 1.24 mm). It has two bins,
# so rice and quinoa share its catch: it can't do the 3-class task, by design.
DEMO_RIG = {"family": "demo_rig", "label": "one level of the demo rig: the 5 mm tray alone over a catch pan, up and down "
                                           "(sine 20 Hz, 2 g, 90 deg). The full rig is the stacked baseline above",
            "spec": "inserts:5mm", "inject": {},
            "stroke": {"profile": "sine", "amp_mm": 1.24, "freq_hz": 20.0, "angle_deg": 90.0}, "params": {}}

DEFAULT_FAMILIES = ("gated", "gated_mid", "plinko", "inserts")
ROUND0 = {"gated": 28, "gated_rib": 24, "gated_mid": 16, "plinko": 12, "inserts": 6}   # Latin hypercube per family
ROUNDN = {"gated": 12, "gated_rib": 16, "gated_mid": 10, "plinko": 8, "inserts": 2}    # cross-entropy per round
EXPLORE = {"gated": 8, "gated_rib": 6, "gated_mid": 6, "plinko": 8, "inserts": 3}      # extra Latin hypercube when a
#                                                                     family gains parameters (e.g. the stroke angle)
# Insect runs cost about 3x a grain run per step (legs: many contacts), so the insect study searches fewer candidates.
BUDGET = {"seesaw": ({"plinko": 12, "inserts": 8}, {"plinko": 8, "inserts": 5}),
          "insects": ({"gated": 10, "gated_rib": 8, "gated_mid": 8, "plinko": 8, "inserts": 3},
                      {"gated": 6, "gated_rib": 6, "gated_mid": 6, "plinko": 6, "inserts": 2})}


# ---------------------------------------------------------------- candidates

def show(c):
    """The design in CAD (nominal) numbers, for people."""
    return FAMILIES[c["family"]]["show"](c["params"]) if c["family"] in FAMILIES else c.get("label", c["spec"])


def stroke_of(p):
    if "ss_deg" in p:
        s = {"profile": "seesaw", "deg": p["ss_deg"], "period_s": p["ss_period"], "shape": p["ss_shape"]}
        if p.get("vib_mm"):
            s.update(vib_mm=p["vib_mm"], vib_hz=VIB_HZ)
        return s
    if p.get("drive", "firmware") == "rock":
        q = {**ROCK_DEFAULT, **{k: p[k] for k in ROCK_DEFAULT if k in p}}
        return {"profile": "none", "rock": {"axis": q["rock_axis"], "deg": q["rock_deg"], "period_s": q["rock_period"],
                                            "ramp_s": RAMP_S}}
    if p.get("drive", "firmware") == "tool":
        f, a = p["freq"], p["accel"]
        s = {"profile": "sine", "amp_mm": round(a * 9810.0 / (2 * math.pi * f) ** 2, 4), "freq_hz": f}
    else:
        s = {"profile": "constant_speed", "amp_mm": p["amp"], "speed_mm_s": p["speed"], "ramp_s": RAMP_S}
    if p.get("angle"):
        s["angle_deg"] = p["angle"]
    return s


def stroke_show(st):
    if st.get("profile") == "seesaw":
        shape = "sine" if st.get("shape") == "sine" else "constant speed"
        buzz = f" + {st['vib_mm']:g} mm buzz at {st['vib_hz']:g} Hz" if st.get("vib_mm") else ""
        return f"seesaw +/-{st['deg']:g} deg (ends tip, neighbours alternate), {st['period_s']:g} s per cycle, {shape}{buzz}"
    if st.get("rock"):
        r = st["rock"]
        return f"seesaw +/-{r['deg']:g} deg about the tray's {'long' if r['axis'] == 'x' else 'short'} axis, {r['period_s']:g} s per cycle"
    if st.get("profile") == "sine":
        g = st["amp_mm"] * (2 * math.pi * st["freq_hz"]) ** 2 / 9810.0
        out = f"tool sine {st['freq_hz']:g} Hz, {g:.1f} g ({st['amp_mm']:.2f} mm)"
    else:
        out = f"firmware {st['amp_mm']:g} mm at {st['speed_mm_s']:g} mm/s"
    return out + (f", {st['angle_deg']:g} deg up" if st.get("angle_deg") else ", along the tray")


def make_cand(family, params, origin, rnd, label=None, study="demo"):
    f = FAMILIES[family]
    if FORCE_DRIVE:
        params = {**params, "drive": FORCE_DRIVE}
    p = {q.name: q.quant(params[q.name]) for q in params_of(family, study) if q.name in params}
    c = {"family": family, "params": p, "spec": f["spec"](p), "inject": f["inject"](p), "stroke": stroke_of(p),
         "origin": origin, "round": rnd, "label": label}
    c["id"] = cand_id(c)
    return c


def cand_id(c):
    key = json.dumps([c["spec"], c["inject"], c["stroke"]], sort_keys=True)
    return f"{c['family'][0].upper()}-{hashlib.sha1(key.encode()).hexdigest()[:8]}"


def lhs(n, params, rng):
    """n points in [0,1)^d, one per stratum in every continuous dimension; categoricals cycle."""
    out = []
    cols = {}
    for q in params:
        if q.choices:
            cols[q.name] = [q.choices[i % len(q.choices)] for i in rng.permutation(n)]
        else:
            cols[q.name] = (rng.permutation(n) + rng.random(n)) / n
    for i in range(n):
        out.append({q.name: cols[q.name][i] if q.choices else q.lo + cols[q.name][i] * (q.hi - q.lo)
                    for q in params})
    return out


def propose(family, n, rnd, rng, existing, study="demo", fresh=False):
    """A family's first round: Latin hypercube. Later: cross-entropy around the family's elites."""
    f = FAMILIES[family]
    ps = params_of(family, study)
    out, tries = [], 0
    dist = ce_dist(family) if rnd > 0 and not fresh else None
    pool = lhs(n * 3, ps, rng) if dist is None else None
    while len(out) < n and tries < n * 50:
        tries += 1
        if dist is None:
            raw = pool[tries - 1] if tries - 1 < len(pool) else lhs(1, ps, rng)[0]
        else:
            raw = {}
            for q in ps:
                if q.choices:
                    w = dist["cat"].get(q.name)
                    if not w or len(w) != len(q.choices):
                        w = [1.0 / len(q.choices)] * len(q.choices)
                    raw[q.name] = q.choices[rng.choice(len(q.choices), p=w)]
                elif q.name not in dist["mean"]:
                    raw[q.name] = q.lo + rng.random() * (q.hi - q.lo)
                else:
                    u = rng.normal(dist["mean"][q.name], dist["sd"][q.name])
                    raw[q.name] = q.lo + min(max(u, 0.0), 1.0) * (q.hi - q.lo)
        c = make_cand(family, raw, "lhs" if dist is None else "ce", rnd, study=study)
        if f["ok"](c["params"]) or c["id"] in existing or any(o["id"] == c["id"] for o in out):
            continue
        out.append(c)
    return out


CE_STATE = {}


def ce_dist(family):
    return CE_STATE.get(family)


def ce_update(family, cands, summaries, rng, study="demo"):
    """Fit mean / sd (normalized) and categorical weights to the family's elites; smooth with the old fit."""
    ps = params_of(family, study)
    ranked = sorted((c for c in cands if c["family"] == family and best_score(summaries.get(c["id"])) is not None),
                    key=lambda c: (not summaries[c["id"]].get("full"), -best_score(summaries[c["id"]])))
    if len(ranked) < 3:
        return None
    k = max(3, math.ceil(0.25 * len(ranked)))
    elite = ranked[:k]
    old = CE_STATE.get(family)
    mean, sd, cat = {}, {}, {}
    for q in ps:
        if q.choices:
            counts = np.array([sum(c["params"].get(q.name, CE_DEFAULTS.get(q.name)) == ch for c in elite)
                               for ch in q.choices], float) + 0.5
            w = counts / counts.sum()
            w = np.maximum(w, 0.15)
            w /= w.sum()
            if old and len(old["cat"].get(q.name, [])) == len(q.choices):    # a categorical that gained a choice restarts
                w = 0.7 * w + 0.3 * np.array(old["cat"][q.name])
            cat[q.name] = (w / w.sum()).tolist()
            continue
        vals = [c["params"].get(q.name, CE_DEFAULTS.get(q.name)) for c in elite]
        vals = [v for v in vals if v is not None]
        if len(vals) < 2:              # no elite has tried this parameter yet: leave it uniform
            continue
        u = np.array([(v - q.lo) / (q.hi - q.lo) for v in vals])
        m, s = float(u.mean()), float(max(u.std(ddof=1), 0.04))
        if old and q.name in old["mean"]:
            m, s = 0.7 * m + 0.3 * old["mean"][q.name], 0.7 * s + 0.3 * old["sd"][q.name]
        mean[q.name], sd[q.name] = m, max(s, 0.04)
    CE_STATE[family] = {"mean": mean, "sd": sd, "cat": cat, "elite": [c["id"] for c in elite]}
    return CE_STATE[family]


# ---------------------------------------------------------------- jobs and the worker

def base_cfg(study):
    import sorter
    return sweep.make_cfg(dataclasses.asdict(sorter.RunConfig()), mix=STUDIES[study]["mix"], dt=DT,
                          contact={"timeconst": TIMECONST})


def at_undersize(c, us):
    """(spec, inject) of a candidate rebuilt with another printer undersize (print tolerance stress)."""
    global UNDERSIZE_MM
    if c["family"] not in FAMILIES:
        return c["spec"], c["inject"]
    keep, UNDERSIZE_MM = UNDERSIZE_MM, us
    try:
        f = FAMILIES[c["family"]]
        return f["spec"](c["params"]), f["inject"](c["params"])
    finally:
        UNDERSIZE_MM = keep


def jobs_for(c, study, fid, base, sets):
    """fid: screen, full, ramp<s> (full length, stroke reversal time changed) or us<mm> (full length, openings
    built with another printer undersize)."""
    dur = SCREEN_S if fid == "screen" else FULL_S
    stroke = dict(c["stroke"], ramp_s=float(fid[4:])) if fid.startswith("ramp") else c["stroke"]
    spec, inject = at_undersize(c, float(fid[2:])) if fid.startswith("us") else (c["spec"], c["inject"])
    stiff = {"dt": STIFF_DT, "contact": {"timeconst": STIFF_TIMECONST}} if fid == "stiff" else {}
    out = []
    for label, contact in sets:
        for seed in {"screen": SCREEN_SEEDS, "full": FULL_SEEDS}.get(fid, SEEDS):
            cfg = sweep.make_cfg(base, design=spec, stroke=stroke, contact=contact, duration_s=dur,
                                 seed=seed)
            if stiff:
                cfg = sweep.make_cfg(cfg, **stiff)
            job = {"cfg": cfg, "inject": inject,
                   "tags": {"cand": c["id"], "fid": fid, "set": label, "seed": seed}}
            job["key"] = hashlib.sha1(json.dumps([cfg, inject], sort_keys=True, default=sweep.jsonable)
                                      .encode()).hexdigest()[:20]
            out.append(job)
    return out


class Unstable(Exception):
    pass


def apply_inject(inject):
    import designs  # noqa: F401  (stubs cadquery before the CAD modules load)
    import designs_holder
    fh, si, pl = designs_holder.cad()
    mods = {"sieve_insert": si, "plinko_layers": pl, "frame_holder": fh}
    for dotted, val in inject.items():
        mod, attr = dotted.split(".")
        target = getattr(mods[mod], attr)
        if isinstance(target, dict):
            target.update({k: tuple(v) for k, v in val.items()})
        else:
            setattr(mods[mod], attr, [tuple(r) for r in val])


def run_job(job):
    """Child process: one sorter.run() with an instability check; returns a compact result record."""
    import mujoco
    import sorter
    t0 = time.time()
    rec = {"key": job["key"], "tags": job["tags"], "config": job["cfg"]}
    mujoco.mj_step = getattr(mujoco, "_orig_mj_step", mujoco.mj_step)   # one wrapper per run, never nested
    mujoco._orig_mj_step = mujoco.mj_step
    try:
        apply_inject(job.get("inject") or {})
        import designs
        roles = [g["role"] for g in designs.build(job["cfg"]["design"]).geoms]
        step, bad, seen = mujoco.mj_step, mujoco.mjtWarning.mjWARN_BADQACC, {"gate_pen": 0.0}
        settle = job["cfg"]["settle_s"]

        def checked_step(m, d):
            step(m, d)
            if "d" not in seen:
                if mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "tray0") < 0:
                    return                         # another model: clumps.py's packing pre-sim
                seen["m"], seen["d"], seen["n"] = m, d, 0
                seen["gate"] = np.array([m.geom(f"tray{i}").id for i, r in enumerate(roles) if r in ("gate", "screen")])
            seen["n"] += 1
            if seen["n"] % 10 == 0 and d.ncon and d.time >= settle and len(seen["gate"]):
                g = d.contact.geom[:d.ncon]
                hit = np.isin(g[:, 0], seen["gate"]) | np.isin(g[:, 1], seen["gate"])
                if hit.any():
                    seen["gate_pen"] = max(seen["gate_pen"], -float(d.contact.dist[:d.ncon][hit].min()))
            if seen["n"] % 50 == 0 and d.warning[bad].number:
                raise Unstable(f"BADQACC at t = {d.time:.4f} s, DOF {int(d.warning[bad].lastinfo)}")

        rock = job["cfg"]["stroke"].get("rock")
        if rock:
            checked_step = rocking(checked_step, rock, job["cfg"], seen)
        mujoco.mj_step = checked_step
        one_box_seesaw()
        res = sorter.run(sorter.RunConfig(**job["cfg"]))
        if res.get("seesaw"):
            rec["seesaw_clearance_mm"] = res["seesaw"]["clearance"]["min_mm"]
            if res["seesaw"]["clearance"]["touching"]:
                raise Unstable(f"seesaw: neighbouring trays touch ({rec['seesaw_clearance_mm']} mm); raise pitch=")
        if res.get("unstable_resets"):             # sorter.py's own reset detection (d.time going backwards)
            raise Unstable(f"MuJoCo reset the state at t = {res['unstable_resets'][:3]} s")
        m, d = seen["m"], seen["d"]
        if not (np.isfinite(d.qpos).all() and np.isfinite(d.qvel).all()):
            raise Unstable("non-finite state at the end")
        xyz = [d.xpos[m.body(p["name"]).id].round(2).tolist() for p in res["particles"]]
        for p, x in zip(res["particles"], xyz):
            p["xyz"] = x
        rec.update({k: res[k] for k in ("design", "design_info", "zones", "kinds", "counts", "particles",
                                        "max_penetration_mm", "max_penetration_particles_mm", "sim_s", "wall_s")})
        ts = res["timeseries"]
        rec["timeseries"] = {"t": ts["t"], "counts": ts["counts"]}
        rec["gate_penetration_mm"] = round(seen["gate_pen"], 5)
        if res.get("clumps"):                      # clumps.py metrics, less the per-bond and per-step arrays
            c = res["clumps"]
            rec["clumps"] = {**{k: v for k, v in c.items() if k not in ("bonds", "timeseries", "damage")},
                             "damage": {k: v for k, v in c["damage"].items() if k != "per_specimen_mN"},
                             "free_t": c["timeseries"]["t"][::5], "free": c["timeseries"]["free"][::5]}
        rec["sweep_metrics"] = {k: v for k, v in sweep.run_metrics(res).items() if not k.startswith("count:")}
    except Unstable as e:
        rec.update({"unstable": str(e)})
    except Exception:
        rec.update({"error": traceback.format_exc()[-3000:]})
    rec["wall_total_s"] = round(time.time() - t0, 2)
    return rec


def one_box_seesaw():
    """rocking.py seesaws a tower of holder boxes. A one-box design (plinko: its three layers stand in one holder)
    rocks as one level on one hinge across the holder's middle, every layer in phase since they are one part.
    Patched in here, in the child process, so rocking.py stays the seesaw session's."""
    import designs_holder
    import rocking
    if getattr(rocking, "_one_box", False):
        return
    tower, init = rocking.find_levels, rocking.Seesaw.__init__

    def find_levels(design):
        if "catch_z_mm" in design.info:
            return tower(design)
        H = designs_holder.cad()[0].H
        return [{"name": "level0", "zone": design.zones[-1]["name"], "z0": 0.0, "pivot": [0.0, 0.0, H / 2],
                 "geoms": list(range(len(design.geoms)))}], []

    def __init__(self, stroke, design, *a):
        init(self, stroke, design, *a)
        if self.n == 1:                       # every zone of the box is in the one level's frame
            self.zone_level = {z["name"]: 0 for z in design.zones}

    rocking.find_levels, rocking.Seesaw.__init__, rocking._one_box = find_levels, __init__, True


def rocking(inner, rock, cfg, seen):
    """Wrap mj_step so the tray seesaws instead of translating (the sim runs in the tray frame, sorter.py only
    translates). Before each step: gravity is rotated into the tilted tray frame, and every particle gets the
    rotating-frame forces m (-alpha x r - w x (w x r) - 2 w x v), r measured in plan from the tray centre (the
    pivot axis is taken through the centre of each tray, at the particle's own height). The tilt follows the
    firmware's constant-speed, hard-reversal profile (sorter.stroke_profile constant_speed, in radians)."""
    import mujoco
    import sorter
    dt, settle = cfg["dt"], cfg["settle_s"]
    n = round(cfg["duration_s"] / dt) + 2
    q = round(rock["period_s"] / 4 / dt)          # start a quarter cycle in, where the tilt passes level
    th_amp = np.radians(rock["deg"])
    th, om, al = sorter.stroke_profile({"profile": "constant_speed", "amp_mm": th_amp, "freq_hz": 1.0 / rock["period_s"],
                                        "ramp_s": rock.get("ramp_s", RAMP_S)}, n + q, dt)
    th, om, al = th[q:], om[q:], al[q:]
    e = np.array([1.0, 0.0, 0.0]) if rock["axis"] == "x" else np.array([0.0, 1.0, 0.0])
    st = {}

    def step(m, d):
        if "roots" not in st:
            st["roots"] = np.array([b for b in range(1, m.nbody) if m.body_rootid[b] == b])
            st["mass"] = m.body_subtreemass[st["roots"]][:, None]
            st["dof"] = m.jnt_dofadr[m.body_jntadr[st["roots"]]]
        i = int(round((d.time - settle) / dt))
        if i >= 0 and i < n:
            c, s_ = np.cos(th[i]), np.sin(th[i])
            g = np.array([0.0, 0.0, -sorter.G])
            # gravity seen from a frame rotated by th about e (Rodrigues, rotating the vector by -th)
            m.opt.gravity[:] = g * c - np.cross(e, g) * s_ + e * (e @ g) * (1 - c)
            w, a = om[i] * e, al[i] * e
            pos = d.xipos[st["roots"]].copy()
            pos[:, 2] = 0.0
            vel = d.qvel[st["dof"][:, None] + np.arange(3)]
            f = -np.cross(a, pos) - np.cross(w, np.cross(w, pos)) - 2 * np.cross(w, vel)
            d.xfrc_applied[st["roots"], :3] = st["mass"] * f
        inner(m, d)

    return step


def run_in_child(job, job_dir):
    path = job_dir / f"{job['key']}.json"
    path.write_text(json.dumps(job, default=sweep.jsonable), encoding="utf-8")
    out = path.with_suffix(".out.json")
    out.unlink(missing_ok=True)
    p = subprocess.run([sys.executable, "-W", "ignore", str(Path(__file__).resolve()), "--job", str(path)],
                       cwd=HERE, capture_output=True, text=True)
    if p.returncode or not out.exists():
        return {"key": job["key"], "tags": job["tags"], "config": job["cfg"],
                "error": (p.stderr or "no result written")[-3000:]}
    rec = json.loads(out.read_text(encoding="utf-8"))
    out.unlink(missing_ok=True)
    path.unlink(missing_ok=True)
    return rec


def run_all(jobs, study, workers):
    """Run the jobs not in the cache; returns {key: record}."""
    cache = OUT / study / "runs"
    job_dir = OUT / study / "jobs"
    cache.mkdir(parents=True, exist_ok=True)
    job_dir.mkdir(parents=True, exist_ok=True)
    todo = [j for j in {j["key"]: j for j in jobs}.values() if not (cache / f"{j['key']}.json").exists()]
    if todo:
        t0 = time.time()
        n = max(1, min(workers, len(todo)))
        print(f"{len(todo)} runs on {n} workers ({len(jobs) - len(todo)} cached)", flush=True)
        with ThreadPoolExecutor(max_workers=n) as ex:
            futs = {ex.submit(run_in_child, j, job_dir): j for j in todo}
            for i, fut in enumerate(as_completed(futs), 1):
                j = futs[fut]
                try:
                    rec = fut.result()
                except Exception:
                    rec = {"key": j["key"], "tags": j["tags"], "config": j["cfg"], "error": traceback.format_exc()}
                (cache / f"{j['key']}.json").write_text(json.dumps(rec, default=sweep.jsonable), encoding="utf-8")
                if i % 16 == 0 or i == len(todo):
                    el = time.time() - t0
                    print(f"  [{i}/{len(todo)}] {el / 60:.1f} min, eta {el / i * (len(todo) - i) / 60:.1f} min",
                          flush=True)
    return {j["key"]: json.loads((cache / f"{j['key']}.json").read_text(encoding="utf-8")) for j in jobs}


# ---------------------------------------------------------------- scoring

def class_of(study, p):
    for i, c in enumerate(STUDIES[study]["classes"]):
        if "kinds" in c and p["kind"] not in c["kinds"]:
            continue
        L = p["dims"]["length"]
        if "min_length" in c and L < c["min_length"]:
            continue
        if "max_length" in c and L >= c["max_length"]:
            continue
        return i
    return None


def kind_bins(study, zones):
    """{kind: bin zone} when the classes are defined by kind only, else None."""
    cl = STUDIES[study]["classes"]
    if not all("kinds" in c and len(c) == 2 for c in cl):
        return None
    return {k: zones[min(i, len(zones) - 1)] for i, c in enumerate(cl) for k in c["kinds"]}


def t90(rec, study, zones, n):
    ts = rec["timeseries"]
    t = np.asarray(ts["t"], float) - rec["config"]["settle_s"]
    i0 = int(np.searchsorted(t, -1e-9))
    bins = kind_bins(study, zones)
    good = np.zeros(len(t))
    for kind, zc in ts["counts"].items():
        if bins:
            good += np.asarray(zc[bins[kind]], float)
        else:                    # time to reach 90% of the end state
            for z, series in zc.items():
                s = np.asarray(series, float)
                good += np.minimum(s, s[-1])
    hit = np.flatnonzero(good[i0:] >= 0.9 * n - 1e-9)
    return float(max(0.0, t[i0 + hit[0]])) if len(hit) else None


def gates_of(info):
    """[(rule, a, b)] per gate, top first, from design_info."""
    if "levels" in info:
        return [("rect", *lv["opening_mm"]) for lv in info["levels"]]
    out = []
    for layer in info.get("layers", []):
        if layer["rule"] == "square":
            out.append(("rect", layer["opening_mm"], layer["opening_mm"]))
        elif layer["rule"] == "slot":
            out.append(("slot", layer["opening_mm"], None))
    return out


@functools.lru_cache(maxsize=None)
def passes(W, T, gate, delta=0.0):
    from common import ellipse_fits
    rule, a, b = gate
    if rule == "slot":
        return T <= a + delta
    return ellipse_fits(W, T, a + delta, b + delta)


def clearance(rec):
    """Tightest margin, over kinds (their mean W, T in this run) and the gates they meet, by which an opening
    would have to change to flip the kind's nominal routing. Soft contacts are untrustworthy inside it."""
    gates = gates_of(rec["design_info"])
    best = None
    for kind in rec["kinds"]:
        ps = [p for p in rec["particles"] if p["kind"] == kind]
        W = round(float(np.mean([p["dims"]["width"] for p in ps])), 2)
        T = round(float(np.mean([p["dims"]["thickness"] for p in ps])), 2)
        for g in gates:
            g = (g[0], *(round(v, 3) if v is not None else None for v in g[1:]))
            f0 = passes(W, T, g)
            for d in (round(0.01 * i, 2) for i in range(1, 151)):
                if passes(W, T, g, d) != f0 or passes(W, T, g, -d) != f0:
                    best = d if best is None else min(best, d)
                    break
            if not f0:
                break            # this kind stops here and meets no further gate
    return round(float(best), 3) if best is not None else None


def run_score(rec, study):
    if rec.get("error") or rec.get("unstable"):
        return {"score": FAIL_SCORE, "progress": FAIL_SCORE,
                "fail": (rec.get("unstable") or rec["error"].strip().splitlines()[-1])[:200]}
    zones = [z for z in rec["zones"] if z not in SPECIAL]
    cols = zones + list(SPECIAL)
    nc = len(STUDIES[study]["classes"])
    tg = [min(i, len(zones) - 1) for i in range(nc)]      # a design with fewer bins puts the last classes together
    C = np.zeros((nc, len(cols)), int)
    for p in rec["particles"]:
        ci = class_of(study, p)
        if ci is not None:
            C[ci, cols.index(p["final_zone"])] += 1
    n = int(C.sum())
    rec_c, pur_c = [], []
    for i in range(nc):
        ni = C[i].sum()
        rec_c.append(C[i, tg[i]] / ni if ni else None)
        tot = C[:, tg[i]].sum()
        pur_c.append(C[i, tg[i]] / tot if tot else (0.0 if ni else None))
    q = min(min(r, p) for r, p in zip(rec_c, pur_c) if r is not None)
    between, lost = int(C[:, -2].sum()), int(C[:, -1].sum())
    leaked = int(sum(C[i, j] for i in range(nc) for j in range(tg[i] + 1, len(zones))))
    beyond = sum(1 for p in rec["particles"] if p["final_zone"] in zones
                 and zones.index(p["final_zone"]) > zones.index(p["ideal_zone"]))   # squeezed past its own geometry
    progress = (float(np.mean([r for r in rec_c if r is not None])) - 2.0 * leaked / n - W_JAM * between / n
                - W_LOST * lost / n)
    dur = rec["config"]["duration_s"]
    tt = t90(rec, study, zones, n)
    score = q - W_JAM * between / n - W_LOST * lost / n - W_T90 * (tt / dur if tt is not None else 1.0)
    clr = clearance(rec)
    pen = rec.get("gate_penetration_mm", rec.get("max_penetration_mm")) or 0.0
    return {"score": float(score), "progress": progress, "leaked": leaked, "beyond": beyond, "quality": float(q), "recovery": rec_c, "purity": pur_c, "between": between,
            "lost": lost, "n": n, "t90": tt, "matrix": C.tolist(), "cols": cols, "clearance": clr, "pen": pen,
            "flag": bool(clr is not None and pen >= PEN_FLAG * clr)}


def summarize(c, study, fid, base, sets):
    jobs = jobs_for(c, study, fid, base, sets)
    cache = OUT / study / "runs"
    recs = []
    for j in jobs:
        f = cache / f"{j['key']}.json"
        if not f.exists():
            return None
        recs.append((j, json.loads(f.read_text(encoding="utf-8"))))
    rs = [(j, run_score(r, study), r) for j, r in recs]
    key = "progress" if fid == "screen" else "score"   # only the short screen ranks sorting progress (docstring)
    s = np.array([x[key] for _, x, _ in rs])
    ok = [x for _, x, _ in rs if "fail" not in x]
    by_set = {}
    for j, x, _ in rs:
        by_set.setdefault(j["tags"]["set"], []).append(x[key])
    nc = len(STUDIES[study]["classes"])
    mean_or_none = lambda vs: float(np.mean(vs)) if vs else None
    out = {"fid": fid, "key": key, "n": len(rs), "mean": float(s.mean()),
           "strict_mean": float(np.mean([x["score"] for _, x, _ in rs])),
           "leaked": mean_or_none([x["leaked"] for x in ok]),
           "beyond": int(sum(x.get("beyond", 0) for x in ok)), "sd": float(s.std(ddof=1)) if len(s) > 1 else 0.0,
           "robust": float(s.mean() - (s.std(ddof=1) if len(s) > 1 else 0.0)),
           "worst_set": float(min(np.mean(v) for v in by_set.values())),
           "by_set": {k: float(np.mean(v)) for k, v in by_set.items()},
           "fails": [x["fail"] for _, x, _ in rs if "fail" in x],
           "flagged": sum(x.get("flag", False) for x in ok),
           "recovery": [mean_or_none([x["recovery"][i] for x in ok if x["recovery"][i] is not None]) for i in range(nc)],
           "purity": [mean_or_none([x["purity"][i] for x in ok if x["purity"][i] is not None]) for i in range(nc)],
           "between": mean_or_none([x["between"] for x in ok]), "lost": mean_or_none([x["lost"] for x in ok]),
           "t90": mean_or_none([x["t90"] for x in ok if x["t90"] is not None]),
           "t90_reached": sum(x["t90"] is not None for x in ok), "n_ok": len(ok),
           "clearance": min((x["clearance"] for x in ok if x["clearance"] is not None), default=None),
           "pen": max((x["pen"] for x in ok), default=None),
           "matrix": np.sum([x["matrix"] for x in ok], axis=0).tolist() if ok else None,
           "cols": ok[0]["cols"] if ok else None,
           "wall_s": float(np.mean([r.get("wall_total_s", 0) for _, _, r in rs])),
           "diagnosis": diagnose([r for _, _, r in rs if not r.get("error") and not r.get("unstable")], study)}
    return out


def best_score(summ):
    """Ranking key across fidelities: full robust score if run at full length, else the screen's."""
    if not summ:
        return None
    s = summ.get("full") or summ.get("screen")
    return s["robust"] if s else None


# ---------------------------------------------------------------- failure analysis

def locate(p, info):
    """Where a particle sits, in words (gated designs get the strip, slot, ledge and ramp)."""
    x, y, z = p["xyz"]
    levels = info.get("levels")
    if not levels:
        for layer in info.get("layers", []):
            lo, hi = layer["surface_z_mm"] if "surface_z_mm" in layer else (layer["bottom_z_mm"], layer["bottom_z_mm"])
            if lo - 1.0 <= z <= hi + 1.0:
                return f"in the floor of {layer['zone']}"
        return f"z {z:.0f} mm"
    from designs_gated import gc
    for lv in levels:
        gate_x = lv.get("gate_x_mm", info["gate_x_mm"])        # per level: mid-slot towers differ by level
        slot_end = lv.get("slot_end_mm", gc.OPEN_X)
        z_c = lv["container_bottom_z_mm"]
        if z_c - 3.0 <= z < z_c + 22.0:
            s = 1.0 if lv["gate_end"] == "+X" else -1.0
            xl = s * x
            up, dn = gate_x - gc.STRIP_T / 2, gate_x + gc.STRIP_T / 2
            if xl < up - 10:
                where = "on the floor"
            elif xl < up:
                where = "at the gate (within 10 mm)"
            elif xl < dn:
                where = "in the strip"
            elif xl < slot_end and abs(y) < gc.OPEN_Y:
                where = "in the drop slot"
            elif xl < slot_end + 0.5:
                where = "on the ledge beside the slot"
            else:
                where = "on the ramp"
            if z > z_c + gc.WALL_H + 1:
                where = "above the walls"
            return f"{lv['level']} {where}"
    if z < levels[-1]["container_bottom_z_mm"]:
        return "catch"
    return f"z {z:.0f} mm"


def diagnose(recs, study):
    """Counts over runs: where misrouted particles of each class ended, and where between/lost ones sit."""
    if not recs:
        return {}
    out = {}
    for r in recs:
        zones = [z for z in r["zones"] if z not in SPECIAL]
        for p in r["particles"]:
            ci = class_of(study, p)
            if ci is None:
                continue
            ti = min(ci, len(zones) - 1)
            target = zones[ti]
            if p["final_zone"] == target:
                continue
            cname = STUDIES[study]["classes"][ci]["name"]
            fz = p["final_zone"]
            if fz in zones:
                kind = "held upstream" if zones.index(fz) < ti else "leaked downstream"
                where = locate(p, r["design_info"]) if kind == "held upstream" and "levels" in r["design_info"] else fz
            else:
                kind, where = fz, locate(p, r["design_info"])
            key = f"{cname}: {kind} -> {where}"
            out[key] = out.get(key, 0) + 1
    n = len(recs)
    return {k: round(v / n, 2) for k, v in sorted(out.items(), key=lambda kv: -kv[1])}


# ---------------------------------------------------------------- outputs

def fmt(v, f="{:.2f}"):
    return "-" if v is None else f.format(v)


def pct(v):
    return "-" if v is None else f"{100 * v:.0f}%"


def params_str(c):
    p = c["params"]
    if not p:
        return ""
    return ", ".join(f"{k} {v}" for k, v in p.items())


def leaderboard_md(study, cands, summ, meta):
    st = STUDIES[study]
    cl = [c["name"] for c in st["classes"]]
    ranked = ranking(cands, summ)
    lines = [f"# Leaderboard: {st['title']}", "",
             f"Generated {datetime.now():%Y-%m-%d %H:%M} by `sim/optimize.py` (study `{study}`). "
             f"{meta['n_cands']} candidates, {meta['n_runs']} sim runs so far.", ""]
    if st["exploratory"]:
        lines += ["**EXPLORATORY.** No real specimen has been measured: the insects are generated from textbook "
                  "sizes (`sim/insects.py`), and the classes use body length, which no gate cuts directly.", ""]
    lines += ["**The sim ranks designs; it does not predict real percentages.** It is uncalibrated until "
              "`calibrate.py` has bench counts, has no water, rigid particles, and about 80 particles per run. "
              "Sizes are simulated at the as-printed opening, nominal - "
              f"{UNDERSIZE_MM} mm (ASSUMED until the hole gauge is measured).", "",
              f"Ranked by the robust score (mean - 1 sd) over 3 friction sets x {len(FULL_SEEDS)} seeds at the full "
              f"{FULL_S:g} s run. Score per run = min over classes of min(purity, recovery), minus {W_JAM} x jammed "
              f"share, {W_LOST} x lost share and {W_T90} x t90/duration. Failed (unstable) runs score {FAIL_SCORE:g}. "
              "Only candidates promoted to the full run are ranked; screened-only ones are in the log. "
              f"Solver: dt {DT * 1e3:g} ms, contact timeconst {TIMECONST * 1e3:g} ms (stiffer than sorter.py's "
              "default; see optimize.py). Friction sets: " + ", ".join(lab for lab, _ in sweep.param_sets()[0]) + ".", "",
              "| # | id | family | robust | mean +/- sd | worst mu set | " +
              " | ".join(f"{c} pur / rec" for c in cl) + " | jammed | lost | t90 s | flags | design (CAD, nominal mm) "
              "| sim spec (as printed) | stroke |",
              "|" + "---|" * (13 + len(cl))]
    for i, c in enumerate(ranked[:10], 1):
        s = summ[c["id"]]["full"]
        lines.append(row(i, c, s, cl))
    lines += ["", "## Best of each family (style)", "",
              "| # | id | family | robust | mean +/- sd | worst mu set | " +
              " | ".join(f"{c} pur / rec" for c in cl) + " | jammed | lost | t90 s | flags | design (CAD, nominal mm) "
              "| sim spec (as printed) | stroke |",
              "|" + "---|" * (13 + len(cl))]
    for f in [*FAMILIES, "current", "demo_rig", "across"]:
        fam = [c for c in ranking(cands, summ, exclude_refs=False) if c["family"] == f]
        if fam:
            lines.append(row(ranking(cands, summ, exclude_refs=False).index(fam[0]) + 1, fam[0],
                             summ[fam[0]["id"]]["full"], cl))
    refs = [c for c in cands if c["origin"] in ("baseline", "current")]
    if refs:
        lines += ["", "## References (fixed, not tuned)", "",
                  "| id | what | robust | mean +/- sd | worst mu set | " +
                  " | ".join(f"{c} pur / rec" for c in cl) + " | jammed | lost | t90 s | flags | spec |",
                  "|" + "---|" * (10 + len(cl))]
        for c in refs:
            s = (summ.get(c["id"]) or {}).get("full")
            if s:
                lines.append(f"| {c['id']} | {c['label']} | {s['robust']:.3f} | {s['mean']:.3f} +/- {s['sd']:.3f} | "
                             f"{s['worst_set']:.3f} | " + " | ".join(f"{pct(s['purity'][k])} / {pct(s['recovery'][k])}"
                                                                     for k in range(len(cl)))
                             + f" | {fmt(s['between'], '{:.1f}')} | {fmt(s['lost'], '{:.1f}')} | {t90_cell(s)} | "
                             f"{flags(s)} | `{c['spec']}` |")
    pool = ranking(cands, summ, exclude_refs=False)
    stressed = [c for c in pool if any(k.startswith(("ramp", "us")) for k in summ[c["id"]])]
    if stressed:
        keys = sorted({k for c in stressed for k in summ[c["id"]] if k.startswith(("ramp", "us"))},
                      key=lambda k: (k.startswith("us"), float(k[4:] if k.startswith("ramp") else k[2:])))
        label = lambda k: f"ramp {k[4:]} s" if k.startswith("ramp") else f"undersize {k[2:]} mm"
        lines += ["", "## Stress test: the leaders under the two biggest unknowns", "",
                  "**Stroke reversal.** The firmware reverses at constant speed with no ramp; how sharp the real "
                  f"reversal is depends on the stage and is unmeasured (sweep.py FIRMWARE assumes {RAMP_S:g} s). "
                  "Transport depends on it. **Print size.** Openings are simulated at nominal - "
                  f"{UNDERSIZE_MM:g} mm (assumed); a printer that makes them 0.1 mm tighter or looser shifts every cut. "
                  "Each column reruns the design with one of these changed (full length, same 3 friction sets x 3 "
                  "seeds; robust score). A design whose score holds across columns is safer to print.", "",
                  f"| id | family | as ranked (ramp {RAMP_S:g} s, undersize {UNDERSIZE_MM:g} mm) | "
                  + " | ".join(label(k) for k in keys) + " | worst | design |", "|" + "---|" * (5 + len(keys))]
        for c in stressed:
            vals = [(summ[c["id"]].get(k) or {}).get("robust") for k in keys]
            worst = min([summ[c["id"]]["full"]["robust"], *[v for v in vals if v is not None]])
            cells = " | ".join(fmt(v, "{:.3f}") for v in vals)
            lines.append(f"| {c['id']} | {c['family']} | {summ[c['id']]['full']['robust']:.3f} | {cells} | "
                         f"**{worst:.3f}** | {show(c)} |")
    ver = [c for c in pool if (summ[c["id"]] or {}).get("stiff")]
    if ver:
        lines += ["", "## Verification of flagged leaders at stiffer contacts", "",
                  f"Rerun at dt {STIFF_DT * 1e3:g} ms and contact timeconst {STIFF_TIMECONST * 1e3:g} ms (half the "
                  f"overlap of the standard solver), 3 friction sets x {len(SEEDS)} seeds, {FULL_S:g} s. A design that comes back with "
                  "no flagged or failed run counts as clean for `winners.json`, ranked by the lower of its two scores.", "",
                  "| id | family | robust (standard) | flags (standard) | robust (stiff) | flags (stiff) | verdict | design |",
                  "|---|---|---|---|---|---|---|---|"]
        for c in ver:
            sm = summ[c["id"]]
            v = verified(sm)
            lines.append(f"| {c['id']} | {c['family']} | {sm['full']['robust']:.3f} | {flags(sm['full'])} | "
                         f"{sm['stiff']['robust']:.3f} | {flags(sm['stiff'])} | "
                         f"{'clean' if v['clean'] else 'still flagged'} | {show(c)} |")
    by_drive = {}
    for c in pool:
        if c["family"] in FAMILIES:
            by_drive.setdefault(drive_of(c), c)
    if by_drive:
        lines += ["", "## Best per drive", "",
                  "BioKEA's stage can only run the firmware stroke (constant speed); the demo rig is a vibrating tool "
                  "(sine). Best full-run design for each, whether or not it is flagged:", "",
                  "| drive | id | family | robust | flags | design (CAD, nominal mm) | stroke |", "|---|---|---|---|---|---|---|"]
        for prof, name in (("rock", "seesaw (the rig's current rocking motor; ends tip, axis y)"), ("constant_speed", "firmware (BioKEA's stage)"),
                           ("sine", "vibrating tool (demo rig)")):
            c = by_drive.get(prof)
            if c:
                sm = summ[c["id"]]["full"]
                lines.append(f"| {name} | {c['id']} | {c['family']} | {sm['robust']:.3f} | {flags(sm)} | {show(c)} | "
                             f"{stroke_show(c['stroke'])} |")
    lines += ["", f"## Count matrices of the top 3 (summed over the {3 * len(FULL_SEEDS)} full runs)", ""]
    for i, c in enumerate(ranked[:3], 1):
        lines += matrix_md(f"{i}. {c['id']} ({c['family']}) {show(c)}; sim `{c['spec']}`", summ[c["id"]]["full"], cl)
    lines += ["", "Columns: purity = share of a bin's contents that belong to its class; recovery = share of a class "
              "that ends in its bin; jammed = particles per run stuck between bins (in a strip, slot or on a ledge); "
              "lost = out of the machine; t90 = seconds until 90% of the sample sits in its target bin (n/9 = runs "
              "that got there). Flags: FAIL = runs that went unstable or errored; PEN = particle-vs-gate overlap at "
              f"or over {PEN_FLAG} x the tightest gate clearance (near-size results untrustworthy); BEYOND = particles "
              "that ended past an opening their own size can't pass (soft contacts squeezed them through; should be "
              "0, and is shown whenever it isn't).", ""]
    return "\n".join(lines)


def t90_cell(s):
    return f"{fmt(s['t90'], '{:.1f}')} ({s['t90_reached']}/{s['n']})"


def flags(s):
    f = []
    if s.get("beyond"):
        f.append(f"BEYOND {s['beyond']} (particles past an opening they can't fit)")
    if s["fails"]:
        f.append(f"FAIL {len(s['fails'])}/{s['n']}")
    if s["flagged"]:
        f.append(f"PEN {s['flagged']}/{s['n']} (clr {fmt(s['clearance'])}, pen {fmt(s['pen'], '{:.3f}')})")
    return "; ".join(f) or "ok"


def row(i, c, s, cl):
    return (f"| {i} | {c['id']} | {c['family']} | **{s['robust']:.3f}** | {s['mean']:.3f} +/- {s['sd']:.3f} | "
            f"{s['worst_set']:.3f} | " + " | ".join(f"{pct(s['purity'][k])} / {pct(s['recovery'][k])}"
                                                    for k in range(len(cl)))
            + f" | {fmt(s['between'], '{:.1f}')} | {fmt(s['lost'], '{:.1f}')} | {t90_cell(s)} | {flags(s)} | "
            f"{show(c)} | `{c['spec']}` | {stroke_show(c['stroke'])} |")


def matrix_md(title, s, cl):
    if not s or not s["matrix"]:
        return [f"**{title}**: no successful runs", ""]
    cols = s["cols"]
    out = [f"**{title}**", "", "| class \\ ended in | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 1)]
    for k, name in enumerate(cl):
        out.append(f"| {name} | " + " | ".join(str(v) for v in s["matrix"][k]) + " |")
    out.append("")
    return out


def ranking(cands, summ, exclude_refs=True):
    pool = [c for c in cands if (summ.get(c["id"]) or {}).get("full")
            and not (exclude_refs and c["origin"] == "current")]
    return sorted(pool, key=lambda c: -summ[c["id"]]["full"]["robust"])


def winners_json(study, cands, summ):
    """Top 3 among full-run candidates with no failed and no flagged run (the rule is fixed, not tuned)."""
    working = [c for c in ranking(cands, summ) if c["family"] in FAMILIES and not summ[c["id"]]["full"]["fails"]
               and summ[c["id"]]["full"]["robust"] >= MIN_WINNER
               and not FAMILIES[c["family"]]["ok"](c["params"])]    # constraints added since still apply
    clean = sorted((c for c in working if trusted(summ[c["id"]])), key=lambda c: -win_key(summ[c["id"]]))
    flagged = [c for c in working if not trusted(summ[c["id"]])]
    eligible = clean[:3] + flagged[:max(0, 3 - len(clean))]     # fill with flagged ones only if needed, marked
    out = {"study": study, "title": STUDIES[study]["title"], "exploratory": STUDIES[study]["exploratory"],
           "generated": f"{datetime.now():%Y-%m-%d %H:%M}",
           "rule": "ranked by the worst robust score over every check run on the design (full runs; stiff-contact "
                   "rerun; printer undersize 0.05 / 0.25 mm; stroke reversal 0.005 / 0.02 s for the firmware stroke); "
                   "stress_tested says whether the stress checks were run. A flagged design that `verify` reran with "
                   "stiffer contacts (dt 0.125 ms, timeconst 0.25 ms) with no failed or flagged run counts as clean. "
                   f"Otherwise: top 3 by robust full-run score (mean - 1 sd over 3 friction sets x {len(FULL_SEEDS)} seeds, {FULL_S:g} s) among working "
                   f"sorters (robust >= {MIN_WINNER}, no failed run, meeting today's print constraints) with no penetration-flagged run; if fewer than 3 "
                   "qualify, the rest are the best working flagged ones, marked flagged (see opt/LOG.md for how this "
                   "rule came about)",
           "caveat": "sim ranking only; uncalibrated; openings simulated at nominal - "
                     f"{UNDERSIZE_MM} mm (ASSUMED undersize)",
           "undersize_mm_assumed": UNDERSIZE_MM, "winners": []}
    for i, c in enumerate(eligible[:3], 1):
        s = summ[c["id"]]["full"]
        out["winners"].append({
            "rank": i, "id": c["id"], "family": c["family"], "sim_spec": c["spec"], "sim_inject": c["inject"],
            "stroke": c["stroke"], "stroke_human": stroke_show(c["stroke"]), "params_nominal": c["params"], "cad": FAMILIES[c["family"]]["cad"](c["params"]),
            "score": {"robust": round(s["robust"], 4), "mean": round(s["mean"], 4), "sd": round(s["sd"], 4),
                      "worst_friction_set": round(s["worst_set"], 4)},
            "per_class": [{"class": cl["name"], "purity": s["purity"][k], "recovery": s["recovery"][k]}
                          for k, cl in enumerate(STUDIES[study]["classes"])],
            "count_matrix": {"rows": [cl["name"] for cl in STUDIES[study]["classes"]], "cols": s["cols"],
                             "counts_over_9_runs": s["matrix"]},
            "jammed_per_run": s["between"], "lost_per_run": s["lost"], "t90_s": s["t90"],
            "flagged": not trusted(summ[c["id"]]), "flagged_runs": s["flagged"], "gate_clearance_mm": s["clearance"],
            "max_gate_overlap_mm": s["pen"],
            "verified_stiff": verified(summ[c["id"]]),
            "stress_tested": stressed(summ[c["id"]]), "worst_case_robust": round(win_key(summ[c["id"]]), 4),
            "replay": f"sim/out/opt/{study}/replay/{c['id']}/view.html"})
    out["best_by_drive"] = {}
    for drive, prof in (("seesaw (the rig's current rocking motor)", "rock"), ("firmware (BioKEA's stage)", "constant_speed"),
                        ("vibrating tool (demo rig)", "sine")):
        pick = next((c for c in clean if drive_of(c) == prof), None)
        if pick:
            s = summ[pick["id"]]["full"]
            out["best_by_drive"][drive] = {
                "id": pick["id"], "family": pick["family"], "sim_spec": pick["spec"], "stroke": pick["stroke"],
                "stroke_human": stroke_show(pick["stroke"]), "design": show(pick),
                "cad": FAMILIES[pick["family"]]["cad"](pick["params"]), "robust": round(win_key(summ[pick["id"]]), 4),
                "per_class": [{"class": cl["name"], "purity": s["purity"][k], "recovery": s["recovery"][k]}
                              for k, cl in enumerate(STUDIES[study]["classes"])]}
    return out


def drive_of(c):
    if c["stroke"].get("profile") == "seesaw":
        return "seesaw"
    r = c["stroke"].get("rock")
    if r:                         # a seesaw about the other axis is not the rig's motion
        return "rock" if r["axis"] == RIG_ROCK_AXIS else "rock_" + r["axis"]
    return c["stroke"].get("profile")


def verified(sm):
    """The stiff-contact rerun's verdict: None if not run, else whether it came back clean."""
    st = sm.get("stiff")
    if not st:
        return None
    return {"clean": not st["fails"] and not st["flagged"], "robust": round(st["robust"], 4),
            "flagged_runs": st["flagged"], "max_gate_overlap_mm": st["pen"], "clearance_mm": st["clearance"]}


def trusted(sm):
    """Unflagged at the standard solver, or verified clean (and still a working sorter) at the stiff one."""
    if not sm["full"]["flagged"]:
        return True
    v = verified(sm)
    return bool(v and v["clean"] and v["robust"] >= MIN_WINNER)


def win_key(sm):
    """Worst robust score over every check run on the design: friction x seeds at full length, the stiff-contact
    rerun, and the stress variants (printer undersize, stroke reversal)."""
    return min([sm["full"]["robust"]] + [v["robust"] for k, v in sm.items()
                                         if v and (k == "stiff" or k.startswith(("us", "ramp")))])


def stressed(sm):
    return any(k.startswith("us") for k in sm)


def log_round(study, rnd, cands, summ, new_ids, meta):
    st = STUDIES[study]
    cl = [c["name"] for c in st["classes"]]
    new = [c for c in cands if c["id"] in new_ids]
    lines = [f"## {study} round {rnd} ({datetime.now():%Y-%m-%d %H:%M}, auto)", ""]
    fams = {}
    for c in new:
        fams.setdefault(c["family"], []).append(c)
    lines.append("**Tried:** " + "; ".join(f"{f}: {len(v)} ({', '.join(sorted(set(c['origin'] for c in v)))})"
                                         for f, v in fams.items())
                 + f". {meta['round_runs']} runs, {meta['round_min']:.0f} min wall.")
    lines.append("")
    ranked = ranking(cands, summ)
    if ranked:
        top = ranked[0]
        s = summ[top["id"]]["full"]
        lines.append(f"**Leader so far:** {top['id']} ({top['family']}, round {top['round']}) {show(top)}, stroke "
                     f"{stroke_show(top['stroke'])}: robust {s['robust']:.3f} "
                     f"(mean {s['mean']:.3f} +/- {s['sd']:.3f}); " +
                     ", ".join(f"{n} {pct(s['purity'][k])} pure / {pct(s['recovery'][k])} recovered"
                               for k, n in enumerate(cl)) + f"; {flags(s)}.")
        lines.append("")
    lines += [f"**Screen results this round ({SCREEN_S:g} s, progress score), best per family:**", ""]
    for f, v in fams.items():
        sc = sorted((c for c in v if (summ.get(c["id"]) or {}).get("screen")),
                    key=lambda c: -summ[c["id"]]["screen"]["robust"])
        if sc:
            b = sc[0]
            lines.append(f"- {f}: best {b['id']} screen robust {summ[b['id']]['screen']['robust']:.3f}; median "
                         f"{np.median([summ[c['id']]['screen']['robust'] for c in sc]):.3f}; "
                         f"failures in {sum(bool(summ[c['id']]['screen']['fails']) for c in sc)} of {len(sc)} candidates")
    lines += ["", "**Why the losers failed** (particles per run, over this round's screened candidates in the bottom "
              "half of each family; the most common modes):", ""]
    agg = {}
    for f, v in fams.items():
        sc = sorted((c for c in v if (summ.get(c["id"]) or {}).get("screen")),
                    key=lambda c: -summ[c["id"]]["screen"]["robust"])
        for c in sc[len(sc) // 2:]:
            for k, val in summ[c["id"]]["screen"]["diagnosis"].items():
                agg.setdefault(f, {}).setdefault(k, []).append(val)
        if f in agg:
            items = sorted(agg[f].items(), key=lambda kv: -np.mean(kv[1]) * len(kv[1]))[:6]
            lines.append(f"- {f}: " + "; ".join(f"{k} ({np.mean(v):.1f} in {len(v)} cands)" for k, v in items))
        fails = [x for c in sc for x in summ[c["id"]]["screen"]["fails"]]
        if fails:
            lines.append(f"  - {f} failed runs: {len(fails)}, e.g. {fails[0]}")
    lines += ["", "**Leaders' remaining losses** (full runs, top 3):", ""]
    for c in ranked[:3]:
        d = summ[c["id"]]["full"]["diagnosis"]
        lines.append(f"- {c['id']}: " + ("; ".join(f"{k} {v:.1f}" for k, v in list(d.items())[:5]) or "none"))
    lines += ["", "**Parameters at a bound among each family's elite** (the range may be too narrow):", ""]
    for f in fams:
        dist = CE_STATE.get(f)
        if not dist:
            continue
        hits = []
        for q in params_of(f, study):
            if q.choices:
                if q.name in dist["cat"]:
                    hits.append(f"{q.name} " + "/".join(f"{ch} {w:.2f}" for ch, w in zip(q.choices, dist["cat"][q.name])))
            elif q.name in dist["mean"] and (dist["mean"][q.name] < 0.1 or dist["mean"][q.name] > 0.9):
                hits.append(f"{q.name} {'low' if dist['mean'][q.name] < 0.1 else 'high'} "
                            f"({q.lo + dist['mean'][q.name] * (q.hi - q.lo):.2f})")
        lines.append(f"- {f}: " + (", ".join(hits) or "none"))
    lines += ["", "**Next hypothesis (auto):** " + hypothesis(cands, summ, study), ""]
    return "\n".join(lines) + "\n"


def hypothesis(cands, summ, study):
    ranked = ranking(cands, summ)
    if not ranked:
        return "no full runs yet."
    d = summ[ranked[0]["id"]]["full"]["diagnosis"]
    s = summ[ranked[0]["id"]]["full"]
    notes = []
    held = sum(v for k, v in d.items() if "held upstream" in k and "on the floor" in k)
    parked = sum(v for k, v in d.items() if "at the gate" in k or "in the strip" in k)
    leaked = sum(v for k, v in d.items() if "leaked downstream" in k)
    stuck = sum(v for k, v in d.items() if "between" in k)
    if held >= max(parked, leaked, stuck) and held > 0:
        notes.append(f"the leader is transport-limited ({held:.1f} particles per run still on a floor at 30 s): "
                     "push slope and speed, or change the structure so items travel less (load nearer the gate, "
                     "a ratchet floor)")
    if parked > 0 and parked >= leaked:
        notes.append(f"{parked:.1f} particles per run park at a gate: long items crosswise or near-size wedging; "
                     "try guide teeth that turn long items end-first, or more clearance")
    if leaked > 0:
        notes.append(f"{leaked:.1f} particles per run leak through a gate they should not pass: tighten that gate "
                     "or cap the gap height (window gate)")
    if stuck > 0:
        notes.append(f"{stuck:.1f} particles per run jam between bins: see where in the losses list")
    if s["flagged"]:
        notes.append("the leader's near-size results are flagged (overlap vs clearance): check it at a smaller "
                     "dt or stiffer contacts before trusting it")
    return "; ".join(notes) or "the leader sorts cleanly; refine for robustness and throughput."


def write_outputs(study, cands, summ, meta):
    OPT.mkdir(exist_ok=True)
    suffix = "" if study == "demo" else f"_{study}"
    (OPT / f"leaderboard{suffix}.md").write_text(leaderboard_md(study, cands, summ, meta), encoding="utf-8")
    (OPT / f"winners{suffix}.json").write_text(json.dumps(winners_json(study, cands, summ), indent=1,
                                                          default=sweep.jsonable), encoding="utf-8")
    state = {"study": study, "cands": cands, "ce": CE_STATE,
             "summaries": {k: v for k, v in summ.items()}}
    (OUT / study / "state.json").write_text(json.dumps(state, default=sweep.jsonable), encoding="utf-8")


def append_log(text):
    OPT.mkdir(exist_ok=True)
    path = OPT / "LOG.md"
    if not path.exists():
        path.write_text("# Design optimizer log\n\nOne section per round. Auto sections are written by "
                        "`sim/optimize.py`; notes sections are the optimizer session's reading of them.\n\n",
                        encoding="utf-8")
    with open(path, "a", encoding="utf-8") as f:
        f.write(text + "\n")


# ---------------------------------------------------------------- the loop

def load_state(study):
    f = OUT / study / "state.json"
    if not f.exists():
        return [], {}
    st = json.loads(f.read_text(encoding="utf-8"))
    CE_STATE.update(st.get("ce", {}))
    labels = {r["id"]: r["label"] for r in refs(study, 0)}       # reference labels follow their current definitions
    for c in st["cands"]:
        if c["id"] in labels:
            c["label"] = labels[c["id"]]
    return st["cands"], st.get("summaries", {})


def evaluate(cands, study, fid, base, sets, workers, summ):
    jobs = [j for c in cands for j in jobs_for(c, study, fid, base, sets)]
    t0 = time.time()
    run_all(jobs, study, workers)
    for c in cands:
        summ.setdefault(c["id"], {})[fid] = summarize(c, study, fid, base, sets)
    return len(jobs), (time.time() - t0) / 60


def refs(study, rnd):
    out = [make_cand(f, p, "baseline", rnd, label, study) for f, label, p in BASELINES.get(study, [])]
    for ref in [CURRENT] + ([DEMO_RIG] if study in ("demo", "smoke") else []):   # fixed, non-family references
        if STUDIES[study].get("seesaw"):
            ref = dict(ref, spec=f"{ref['spec']},pitch={SEESAW_DEFAULT['pitch']:g}", stroke=stroke_of(SEESAW_DEFAULT),
                       label=ref["label"].split(",")[0] + ", 85 mm apart, on the default seesaw (+/-10 deg, 2 s)")
        if FORCE_DRIVE == "rock":
            ref = dict(ref, stroke=stroke_of({"drive": "rock"}), label=ref["label"].split(",")[0] + ", seesaw "
                       f"(default {ROCK_DEFAULT['rock_deg']:g} deg, {ROCK_DEFAULT['rock_period']:g} s, "
                       f"{'long axis' if ROCK_DEFAULT['rock_axis'] == 'x' else 'ends tip'})")
        cur = dict(ref, origin="current", round=rnd)
        cur["id"] = cand_id(cur)
        out.append(cur)
    if STUDIES[study].get("seesaw") and rnd >= 1:     # bambu's ribs-across parts, alone and with the buzz
        for vib, tail in ((0.0, ", default seesaw (+/-10 deg, 2 s)"), (0.3, ", default seesaw + 0.3 mm buzz at 40 Hz")):
            st = stroke_of({**SEESAW_DEFAULT, "vib_mm": vib})
            cur = dict(ACROSS, label=ACROSS["label"] + tail, stroke=st, origin="current", round=rnd)
            cur["id"] = cand_id(cur)
            out.append(cur)
    return out


def run_study(args):
    study, rng = args.study, np.random.default_rng(args.seed)
    base = base_cfg(study)
    sets, source = sweep.param_sets()
    cands, summ = load_state(study)
    refresh(study, cands, summ)
    have = {c["id"] for c in cands}
    done_rounds = max((c["round"] for c in cands), default=-1)
    fams = args.families.split(",")
    for rnd in range(done_rounds + 1, done_rounds + 1 + args.rounds):
        t0 = time.time()
        new = [c for c in refs(study, rnd) if c["id"] not in have]    # references added since are picked up too
        r0, rn = BUDGET.get(study, (ROUND0, ROUNDN))
        for f in fams:
            fresh = not any(c["family"] == f for c in cands)     # a family's first round is a Latin hypercube
            if fresh:
                n = r0[f] if not args.small else max(4, r0[f] // 4)
            else:
                ce_update(f, cands, summ, rng, study)
                n = rn[f] if not args.small else max(3, rn[f] // 4)
                gained = [q.name for q in params_of(f, study)
                          if not any(q.name in c["params"] for c in cands if c["family"] == f)]
                if gained:                 # new parameters (e.g. the stroke angle): explore them with a hypercube
                    print(f"round {rnd}: {f} gained {gained}; adding {EXPLORE[f]} hypercube candidates", flush=True)
                    batch = propose(f, EXPLORE[f], rnd, rng, have, study, fresh=True)
                    have |= {c["id"] for c in batch}
                    new += batch
            new += propose(f, n, rnd, rng, have, study, fresh)
        cands += new
        have |= {c["id"] for c in new}
        print(f"round {rnd}: {len(new)} candidates ({source}); screening at {SCREEN_S:g} s", flush=True)
        n1, m1 = evaluate(new, study, "screen", base, sets, args.workers, summ)
        ranked = sorted(new, key=lambda c: -summ[c["id"]]["screen"]["robust"])
        promote = set()
        for f in fams:                   # the top PROMOTE share of each family, so every style gets full runs
            fam = [c for c in ranked if c["family"] == f and c["origin"] not in ("baseline", "current")]
            promote |= {c["id"] for c in fam[:max(1, math.ceil(PROMOTE * len(fam)))]}
        promote |= {c["id"] for c in new if c["origin"] in ("baseline", "current")}
        prom = [c for c in new if c["id"] in promote]
        print(f"round {rnd}: promoting {len(prom)} to the full {FULL_S:g} s run", flush=True)
        n2, m2 = evaluate(prom, study, "full", base, sets, args.workers, summ)
        for f in fams:
            ce_update(f, cands, summ, rng, study)
        meta = {"n_cands": len(cands), "n_runs": len(list((OUT / study / "runs").glob("*.json"))),
                "round_runs": n1 + n2, "round_min": (time.time() - t0) / 60}
        write_outputs(study, cands, summ, meta)
        if study != "smoke":
            append_log(log_round(study, rnd, cands, summ, {c["id"] for c in new}, meta))
        print(f"round {rnd} done in {(time.time() - t0) / 60:.1f} min; leaderboard written", flush=True)


def refresh(study, cands, summ):
    """Recompute every summary from the run cache with today's scoring, so no step decides on stale numbers."""
    base = base_cfg(study)
    sets, _ = sweep.param_sets()
    for c in cands:
        for fid in ["screen", "full", *[k for k in (summ.get(c["id"]) or {}) if k.startswith(("ramp", "us", "stiff"))]]:
            s = summarize(c, study, fid, base, sets)
            if s:
                summ.setdefault(c["id"], {})[fid] = s


def report(args):
    cands, summ = load_state(args.study)
    refresh(args.study, cands, summ)
    meta = {"n_cands": len(cands), "n_runs": len(list((OUT / args.study / "runs").glob("*.json")))}
    write_outputs(args.study, cands, summ, meta)
    print("rebuilt leaderboard and winners")


def replay(args):
    """Record each winner (middle friction set, seed 0, full length) and build its view.html."""
    import sorter
    import viewer
    cands, summ = load_state(args.study)
    refresh(args.study, cands, summ)
    by_id = {c["id"]: c for c in cands}
    win = json.loads((OPT / ("winners.json" if args.study == "demo" else f"winners_{args.study}.json"))
                     .read_text(encoding="utf-8"))
    sets, _ = sweep.param_sets()
    label, contact = sets[len(sets) // 2]
    ids = [w["id"] for w in win["winners"][:args.top]] + (args.ids.split(",") if args.ids else [])
    for cid in ids:
        c = by_id[cid]
        out = OUT / args.study / "replay" / cid
        cfg = sweep.make_cfg(base_cfg(args.study), design=c["spec"], stroke=c["stroke"], contact=contact,
                             duration_s=FULL_S, seed=0)
        cfg["record_fps"], cfg["out_dir"] = args.fps, str(out)
        apply_inject(c["inject"])
        import mujoco
        mujoco.mj_step = getattr(mujoco, "_orig_mj_step", mujoco.mj_step)
        mujoco._orig_mj_step = mujoco.mj_step
        if c["stroke"].get("rock"):
            mujoco.mj_step = rocking(mujoco._orig_mj_step, c["stroke"]["rock"], cfg, {})
        one_box_seesaw()
        r = sorter.run(sorter.RunConfig(**cfg))
        page = viewer.build(out)
        print(cid, c["spec"], {k: v for k, v in r["recovery"].items()}, "->", page)


def stress(args):
    """Rerun the top designs (and the references) at other stroke reversal times."""
    cands, summ = load_state(args.study)
    refresh(args.study, cands, summ)
    base = base_cfg(args.study)
    sets, _ = sweep.param_sets()
    top = ranking(cands, summ)[:args.top]
    refs_ = [c for c in cands if c["origin"] in ("baseline", "current") and (summ.get(c["id"]) or {}).get("full")]
    win = winners_json(args.study, cands, summ)            # the current winners and the best per drive, too
    by_id = {c["id"]: c for c in cands}
    wins = [by_id[w["id"]] for w in win["winners"]] + [by_id[v["id"]] for v in win["best_by_drive"].values()]
    extra = [by_id[i] for i in (args.ids.split(",") if args.ids else []) if i in by_id]
    pick = list({c["id"]: c for c in wins + extra + top + refs_}.values())
    fids = [f"ramp{float(r):g}" for r in args.ramps.split(",") if r] + \
           [f"us{float(u):g}" for u in args.undersize.split(",") if u]
    def applies(c, fid):
        return not fid.startswith("ramp") or c["stroke"].get("profile") == "constant_speed"
    jobs = [j for c in pick for fid in fids if applies(c, fid) for j in jobs_for(c, args.study, fid, base, sets)]
    print(f"stress: {len(pick)} designs x {fids}", flush=True)
    run_all(jobs, args.study, args.workers)
    for c in pick:
        for fid in fids:
            if applies(c, fid):
                summ.setdefault(c["id"], {})[fid] = summarize(c, args.study, fid, base, sets)
    meta = {"n_cands": len(cands), "n_runs": len(list((OUT / args.study / "runs").glob("*.json")))}
    write_outputs(args.study, cands, summ, meta)
    print("stress done; leaderboard rewritten")


def verify(args):
    """Rerun the top flagged designs (full length) with stiffer contacts."""
    cands, summ = load_state(args.study)
    refresh(args.study, cands, summ)
    base = base_cfg(args.study)
    sets, _ = sweep.param_sets()
    pick = [c for c in ranking(cands, summ)[:args.top * 3] if c["family"] in FAMILIES
            and summ[c["id"]]["full"]["flagged"] and summ[c["id"]]["full"]["robust"] >= MIN_WINNER][:args.top]
    print(f"verify: {[c['id'] for c in pick]} at dt {STIFF_DT} s, timeconst {STIFF_TIMECONST} s", flush=True)
    evaluate(pick, args.study, "stiff", base, sets, args.workers, summ)
    meta = {"n_cands": len(cands), "n_runs": len(list((OUT / args.study / "runs").glob("*.json")))}
    write_outputs(args.study, cands, summ, meta)
    print("verify done; leaderboard rewritten")


def plan(args):
    sets, source = sweep.param_sets()
    r0, rn = BUDGET.get(args.study, (ROUND0, ROUNDN))
    n0 = sum(r0[f] for f in DEFAULT_FAMILIES) + len(BASELINES.get(args.study, [])) + 1
    per = len(sets) * len(SEEDS)
    print(f"param sets: {source}; {per} runs per candidate per fidelity")
    print(f"round 0: {n0} candidates -> {n0 * per} screen runs ({SCREEN_S:g} s) + ~{math.ceil(PROMOTE * n0) + 4} "
          f"promoted -> {(math.ceil(PROMOTE * n0) + 4) * per} full runs ({FULL_S:g} s)")
    n1 = sum(rn[f] for f in DEFAULT_FAMILIES)
    print(f"each later round: {n1} candidates -> {n1 * per} screen + ~{(math.ceil(PROMOTE * n1) + 3) * per} full runs")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "report", "replay", "plan", "stress", "verify"])
    ap.add_argument("--study", default="demo", choices=list(STUDIES))
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--workers", type=int, default=MAX_WORKERS)
    ap.add_argument("--families", default=",".join(DEFAULT_FAMILIES),
                    help=f"comma list from {list(FAMILIES)}; gated_rib was tested and rejected (see opt/LOG.md)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--small", action="store_true", help="a quarter of the candidates (smoke test)")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--ids", help="replay / stress: extra candidate ids, comma separated")
    ap.add_argument("--ramps", default="0.005,0.02", help="stress: reversal times to try, s")
    ap.add_argument("--drive", choices=["firmware", "tool", "rock"], help="run: every new candidate uses this drive")
    ap.add_argument("--undersize", default="0.05,0.25", help="stress: printer undersizes to try, mm")
    ap.add_argument("--fps", type=float, default=20.0)
    ap.add_argument("--screen-s", type=float, help="override the screen length (smoke tests)")
    ap.add_argument("--full-s", type=float, help="override the full length (smoke tests)")
    ap.add_argument("--screen-seeds", type=int, help="screen on the first n seeds only")
    ap.add_argument("--full-seeds", type=int, help="full runs on the first n seeds only")
    args = ap.parse_args()
    args.workers = min(args.workers, MAX_WORKERS)
    global SCREEN_S, FULL_S, FORCE_DRIVE, SCREEN_SEEDS, FULL_SEEDS
    SCREEN_S, FULL_S = args.screen_s or SCREEN_S, args.full_s or FULL_S
    FORCE_DRIVE = args.drive
    SCREEN_SEEDS = SEEDS[:args.screen_seeds] if args.screen_seeds else SEEDS
    FULL_SEEDS = SEEDS[:args.full_seeds] if args.full_seeds else SEEDS
    {"run": run_study, "report": report, "replay": replay, "plan": plan, "stress": stress,
     "verify": verify}[args.cmd](args)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--job":
        job_path = Path(sys.argv[2])
        job_path.with_suffix(".out.json").write_text(
            json.dumps(run_job(json.loads(job_path.read_text(encoding="utf-8"))), default=sweep.jsonable),
            encoding="utf-8")
    else:
        main()
