"""
benchmate_hardware.py
=====================
Bridge between Benchmate and a drug-dose + resazurin (alamarBlue) viability rig
running benchmate_rig.ino.

Drop in co_scientist/ and expose run_experiment() as a tool in tools.py, the same
way geneformer_neighbors() is exposed. Viability time-series land in data/rig/ as
CSVs the Generation/Reflection agents read like the Geneformer perturbation cache.

Verbs (mirror the firmware endpoints):
    set_switch(ch, on)      POST /set        stir / aerate / valve
    dose(ch, sec)           POST /dose       ch0 = drug, ch1 = resazurin dye
    read_viability()        GET  /read_viability
    set_blank()             POST /set_blank  oxidized-dye reference

Resazurin readout:
    Live cells reduce resazurin (blue, A600) to resorufin (pink, A570). The rig
    returns a ratiometric index = A570 - A600 that rises with metabolic activity.
    viability_percent(index) maps it to 0-100% using two calibration points:
        DEAD_INDEX  = reading from a no-cell / killed-cell control  (0%)
        LIVE_INDEX  = reading from an untreated control             (100%)
    Set them from controls (set_live_control / set_dead_control) or via env vars.

Env vars:
    BENCHMATE_RIG_URL        http://<rig-ip>
    BENCHMATE_RIG_SIMULATE   "1" (default) dry-run; "0" drive real hardware
    BENCHMATE_LIVE_INDEX     calibration: index of 100%-viable control
    BENCHMATE_DEAD_INDEX     calibration: index of 0%-viable control
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import pathlib
import time
import uuid
from typing import Any

import requests

RIG_URL = os.environ.get("BENCHMATE_RIG_URL", "http://192.168.1.50").rstrip("/")
SIMULATE = os.environ.get("BENCHMATE_RIG_SIMULATE", "1") == "1"
TIMEOUT_S = 10
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "rig"

# Viability calibration (overridable at runtime via set_live_control/set_dead_control)
LIVE_INDEX = float(os.environ.get("BENCHMATE_LIVE_INDEX", "1.0"))
DEAD_INDEX = float(os.environ.get("BENCHMATE_DEAD_INDEX", "0.0"))

LIMITS = {
    "dose_max_sec": 60.0,
    "total_dose_max_sec": 600.0,
    "max_steps": 5000,
    "channels": (0, 1),
}
VERBS = {"set_switch", "dose", "read_viability", "wait"}


# --------------------------------------------------------------------------- #
#  Low-level verbs
# --------------------------------------------------------------------------- #
def _get(path: str) -> dict:
    r = requests.get(f"{RIG_URL}{path}", timeout=TIMEOUT_S); r.raise_for_status(); return r.json()


def _post(path: str, params: dict | None = None) -> dict:
    r = requests.post(f"{RIG_URL}{path}", params=params or {}, timeout=TIMEOUT_S); r.raise_for_status(); return r.json()


def status() -> dict:
    return _get("/status")


def set_switch(ch: int, on: bool) -> dict:
    """Switch a relay channel (stir / aerate / valve)."""
    return _post("/set", {"ch": ch, "on": 1 if on else 0})


def dose(ch: int, sec: float) -> dict:
    """Run pump ch (0 = drug, 1 = resazurin) for sec seconds (firmware clamps to dose_max_sec)."""
    return _post("/dose", {"ch": ch, "sec": sec})


def set_blank() -> dict:
    """Store the current 570/600 readings of fully-oxidized dye (no cells) as the blank."""
    return _post("/set_blank")


def read_viability() -> dict:
    """Raw reading: {i570, i600, dark, a570, a600, index}. index rises with viability."""
    return _get("/read_viability")


def viability_percent(index: float | None) -> float | None:
    """Map a ratiometric index to 0-100% viability using the live/dead calibration."""
    if index is None or LIVE_INDEX == DEAD_INDEX:
        return None
    pct = (index - DEAD_INDEX) / (LIVE_INDEX - DEAD_INDEX) * 100.0
    return max(0.0, min(100.0, pct))


def set_live_control() -> float:
    """Read an untreated well NOW and store its index as 100% viability. Returns the index."""
    global LIVE_INDEX
    LIVE_INDEX = float(read_viability()["index"]); return LIVE_INDEX


def set_dead_control() -> float:
    """Read a no-cell / killed well NOW and store its index as 0% viability. Returns the index."""
    global DEAD_INDEX
    DEAD_INDEX = float(read_viability()["index"]); return DEAD_INDEX


# --------------------------------------------------------------------------- #
#  Protocol validation
# --------------------------------------------------------------------------- #
class ProtocolError(ValueError):
    pass


def validate(protocol: list[dict]) -> None:
    if not isinstance(protocol, list) or not protocol:
        raise ProtocolError("protocol must be a non-empty list of steps")
    if len(protocol) > LIMITS["max_steps"]:
        raise ProtocolError(f"too many steps (>{LIMITS['max_steps']})")
    total_dose = 0.0
    for i, step in enumerate(protocol):
        verb = step.get("verb")
        if verb not in VERBS:
            raise ProtocolError(f"step {i}: unknown verb {verb!r}")
        if verb in ("set_switch", "dose") and step.get("ch") not in LIMITS["channels"]:
            raise ProtocolError(f"step {i}: ch must be one of {LIMITS['channels']}")
        if verb == "dose":
            sec = float(step.get("sec", 0))
            if not (0 < sec <= LIMITS["dose_max_sec"]):
                raise ProtocolError(f"step {i}: dose sec must be in (0, {LIMITS['dose_max_sec']}]")
            total_dose += sec
        if verb == "wait" and float(step.get("sec", 0)) < 0:
            raise ProtocolError(f"step {i}: wait sec must be >= 0")
    if total_dose > LIMITS["total_dose_max_sec"]:
        raise ProtocolError(f"cumulative dosing {total_dose}s exceeds cap {LIMITS['total_dose_max_sec']}s")


# --------------------------------------------------------------------------- #
#  The one entry point the agents call
# --------------------------------------------------------------------------- #
def run_experiment(protocol: list[dict], approve: bool = False, note: str = "") -> dict:
    """Validate, (simulate or) execute a protocol, log viability readings, return a summary."""
    validate(protocol)
    run_id = _dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]

    if SIMULATE:
        return {"run_id": run_id, "mode": "simulated", "steps": len(protocol),
                "note": note, "would_execute": protocol}

    if not approve:
        raise PermissionError(
            "real run requires approve=True (human-in-the-loop gate). "
            "Set BENCHMATE_RIG_SIMULATE=0 and pass approve=True to actuate hardware."
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / f"{run_id}.csv"
    readings: list[dict] = []
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_s", "step", "verb", "a570", "a600", "index", "viability_pct"])
        t0 = time.time()
        for i, step in enumerate(protocol):
            verb = step["verb"]
            a570 = a600 = idx = pct = ""
            if verb == "set_switch":
                set_switch(step["ch"], bool(step["on"]))
            elif verb == "dose":
                dose(step["ch"], float(step["sec"]))
                time.sleep(float(step["sec"]) + 0.5)
            elif verb == "read_viability":
                rd = read_viability()
                a570, a600, idx = rd.get("a570"), rd.get("a600"), rd.get("index")
                pct = viability_percent(idx)
                readings.append({"t_s": round(time.time() - t0, 1), "index": idx, "viability_pct": pct})
            elif verb == "wait":
                time.sleep(float(step.get("sec", 0)))
            w.writerow([round(time.time() - t0, 1), i, verb, a570, a600, idx, pct])

    return {"run_id": run_id, "mode": "executed", "steps": len(protocol),
            "note": note, "csv": str(csv_path), "readings": readings}


def latest_run() -> dict | None:
    """Most recent recorded run as {run_id, csv, rows} — for the evidence cache."""
    if not DATA_DIR.exists():
        return None
    files = sorted(DATA_DIR.glob("*.csv"))
    if not files:
        return None
    with open(files[-1]) as fh:
        rows = list(csv.DictReader(fh))
    return {"run_id": files[-1].stem, "csv": str(files[-1]), "rows": rows}


# --------------------------------------------------------------------------- #
#  Assay builder: drug dose -> incubate -> add dye -> kinetic viability read
# --------------------------------------------------------------------------- #
def viability_assay(
    drug_sec: float,
    incubation_h: float = 24.0,
    dye_sec: float = 6.0,
    develop_h: float = 3.0,
    read_every_min: float = 20.0,
    drug_ch: int = 0,
    dye_ch: int = 1,
    stir_ch: int | None = 0,
) -> list[dict]:
    """One-vessel resazurin assay: dose drug, incubate, add dye, then read viability
    repeatedly while the dye develops. The plateau of viability_pct is your endpoint.
    (For a full dose-response CURVE, run this at several drug_sec values, or build a
    multi-vessel rig — one vessel measures one condition.)"""
    steps: list[dict] = []
    if stir_ch is not None:
        steps.append({"verb": "set_switch", "ch": stir_ch, "on": True})
    steps.append({"verb": "read_viability"})                       # baseline (pre-drug)
    steps.append({"verb": "dose", "ch": drug_ch, "sec": drug_sec})
    steps.append({"verb": "wait", "sec": incubation_h * 3600})
    steps.append({"verb": "dose", "ch": dye_ch, "sec": dye_sec})   # add resazurin
    n = max(1, int((develop_h * 60) / read_every_min))
    for _ in range(n):
        steps.append({"verb": "read_viability"})
        steps.append({"verb": "wait", "sec": read_every_min * 60})
    if stir_ch is not None:
        steps.append({"verb": "set_switch", "ch": stir_ch, "on": False})
    return steps


# --------------------------------------------------------------------------- #
#  CLI (mirrors hermes/benchmate_runner.py)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Benchmate resazurin viability rig CLI")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("blank")
    sub.add_parser("read")                       # one viability reading
    sub.add_parser("live")                        # store current well as 100% control
    sub.add_parser("dead")                        # store current well as 0% control
    d = sub.add_parser("dose"); d.add_argument("ch", type=int); d.add_argument("sec", type=float)
    a = sub.add_parser("assay")
    a.add_argument("--drug-sec", type=float, required=True)
    a.add_argument("--incubation-h", type=float, default=24)
    a.add_argument("--develop-h", type=float, default=3)
    a.add_argument("--read-every-min", type=float, default=20)
    a.add_argument("--approve", action="store_true")
    args = p.parse_args()

    if args.cmd == "status":
        print(json.dumps(status(), indent=2))
    elif args.cmd == "blank":
        print(json.dumps(set_blank(), indent=2))
    elif args.cmd == "read":
        rd = read_viability(); rd["viability_pct"] = viability_percent(rd.get("index"))
        print(json.dumps(rd, indent=2))
    elif args.cmd == "live":
        print("LIVE_INDEX =", set_live_control())
    elif args.cmd == "dead":
        print("DEAD_INDEX =", set_dead_control())
    elif args.cmd == "dose":
        print(json.dumps(dose(args.ch, args.sec), indent=2))
    elif args.cmd == "assay":
        proto = viability_assay(args.drug_sec, args.incubation_h,
                                develop_h=args.develop_h, read_every_min=args.read_every_min)
        print(json.dumps(run_experiment(proto, approve=args.approve), indent=2))
