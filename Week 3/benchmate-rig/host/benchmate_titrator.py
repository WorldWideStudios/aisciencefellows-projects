"""
benchmate_titrator.py
=====================
Host-side closed-loop colorimetric titrator. Talks to a Pico (pico_titrator.py)
over USB serial, runs the dose -> read color -> decide loop, and stops at the
indicator endpoint. Logs every step to data/rig/ so Benchmate can ingest it.

Same read_color() reads the TCS34725 RGB sensor, and the red/blue metric is the
SAME signal alamarBlue produces (blue resazurin -> pink resorufin). Once this
works on kitchen chemistry, read_viability() reuses it for cells.

Try it with no hardware at all:
    python benchmate_titrator.py demo

Env:
    BENCHMATE_TITRATOR_PORT       serial port, e.g. /dev/cu.usbmodem... or COM5
    BENCHMATE_TITRATOR_SIMULATE   "1" = fake sensor (models a titration curve)
    BENCHMATE_UL_PER_MS           pump calibration (microliters per ms of pulse)
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import math
import os
import pathlib
import time

PORT = os.environ.get("BENCHMATE_TITRATOR_PORT", "/dev/ttyACM0")
SIMULATE = os.environ.get("BENCHMATE_TITRATOR_SIMULATE", "0") == "1"
UL_PER_MS = float(os.environ.get("BENCHMATE_UL_PER_MS", "1.5"))  # calibrate yours!
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "rig"

MAX_TOTAL_MS = 30000      # safety: never dispense more than this per run
SETTLE_S = 2.0            # mixing + reaction time between a pulse and a read


# --------------------------------------------------------------------------- #
#  Transport: real serial, or a simulator that models a titration curve
# --------------------------------------------------------------------------- #
class _SerialLink:
    def __init__(self, port):
        import serial  # pyserial, imported lazily so simulate mode needs nothing
        self.ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(2)

    def cmd(self, line: str) -> str:
        self.ser.reset_input_buffer()
        self.ser.write((line + "\n").encode())
        return self.ser.readline().decode().strip()


class _SimLink:
    """Models a sigmoidal titration: the color metric swings through `target`
    as cumulative dispensed volume passes an equivalence point."""
    def __init__(self, eq_ul=900.0, width_ul=120.0, lo=0.6, hi=3.0):
        self.vol_ul = 0.0
        self.eq, self.w, self.lo, self.hi = eq_ul, width_ul, lo, hi

    def _metric(self) -> float:
        s = 1.0 / (1.0 + math.exp(-(self.vol_ul - self.eq) / self.w))
        return self.lo + (self.hi - self.lo) * s

    def cmd(self, line: str) -> str:
        if line == "READ":
            m = self._metric()
            b = 4000.0; r = m * b
            return "%d,%d,%d,%d" % (int(r), int(b), int(b), int(r + 2 * b))
        if line.startswith("PULSE"):
            self.vol_ul += int(line.split()[1]) * UL_PER_MS
            return "OK"
        if line in ("ON", "OFF", "PING"):
            return "PONG" if line == "PING" else "OK"
        return "ERR"


_link = None
def link():
    global _link
    if _link is None:
        _link = _SimLink() if SIMULATE else _SerialLink(PORT)
    return _link


# --------------------------------------------------------------------------- #
#  Primitives
# --------------------------------------------------------------------------- #
def read_color() -> dict:
    """Return {r,g,b,c, rb} where rb = red/blue ratio (rises blue->pink)."""
    r, g, b, c = (int(x) for x in link().cmd("READ").split(","))
    rb = r / b if b else 0.0
    return {"r": r, "g": g, "b": b, "c": c, "rb": round(rb, 4)}


def pulse(ms: int) -> None:
    """Dispense titrant for `ms` milliseconds."""
    link().cmd("PULSE %d" % int(ms))


def _demo_line(step, total_ms, rb, lo=0.6, hi=3.0):
    """A colored terminal bar that shifts blue -> pink as the metric rises."""
    frac = max(0.0, min(1.0, (rb - lo) / (hi - lo)))
    n = 22; filled = int(round(frac * n))
    bar = "#" * filled + "." * (n - filled)
    col = "\033[94m" if frac < 0.5 else "\033[95m"            # blue -> magenta
    tag = "blue" if frac < 0.34 else ("turning pink" if frac < 0.7 else "PINK")
    return f"{col}  step {step:>2} | {total_ms:>4} ms | rb {rb:5.2f} [{bar}] {tag}\033[0m"


# --------------------------------------------------------------------------- #
#  The closed loop
# --------------------------------------------------------------------------- #
def titrate(target: float, direction: str = "above",
            coarse_ms: int = 120, fine_ms: int = 20, fine_band: float = 0.8,
            settle_s: float = SETTLE_S, metric_key: str = "rb",
            note: str = "", approve: bool = False, verbose: bool = False) -> dict:
    """Dose titrant until the color metric crosses `target`. Far from target ->
    coarse pulses; within `fine_band` -> fine pulses, so it slows and doesn't
    overshoot. Returns dispensed volume and logs the curve to data/rig/."""
    if not SIMULATE and not approve:
        raise PermissionError("real titration requires approve=True (human-in-the-loop gate)")

    def crossed(m):
        return m >= target if direction == "above" else m <= target

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    run_id = _dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + ("sim" if SIMULATE else "run")
    csv_path = DATA_DIR / f"titration-{run_id}.csv"

    total_ms = 0
    steps = 0
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["step", "total_ms", "volume_ul", metric_key])
        if verbose:
            print(f"\n  Closed-loop titration {'(SIMULATED)' if SIMULATE else '(LIVE)'} — driving the dye blue -> pink")
            print(f"  target rb = {target:.2f}\n")
        m = read_color()[metric_key]
        w.writerow([0, 0, 0.0, m])
        if verbose:
            print(_demo_line(0, 0, m))
        while not crossed(m):
            if total_ms >= MAX_TOTAL_MS:
                return {"run_id": run_id, "status": "aborted_no_endpoint",
                        "volume_ul": round(total_ms * UL_PER_MS, 1), "csv": str(csv_path)}
            step_ms = fine_ms if abs(m - target) <= fine_band else coarse_ms
            pulse(step_ms)
            total_ms += step_ms
            steps += 1
            time.sleep(settle_s)
            m = read_color()[metric_key]
            w.writerow([steps, total_ms, round(total_ms * UL_PER_MS, 1), m])
            if verbose:
                print(_demo_line(steps, total_ms, m))

    if verbose:
        print(f"\n  \033[95m* endpoint reached - pink!\033[0m  dispensed "
              f"{round(total_ms * UL_PER_MS, 1)} uL in {steps} pulses.\n")
    return {
        "run_id": run_id, "status": "endpoint_reached", "mode": "simulated" if SIMULATE else "executed",
        "endpoint_metric": round(m, 4), "volume_ul": round(total_ms * UL_PER_MS, 1),
        "pulses": steps, "csv": str(csv_path), "note": note,
    }


def read_viability(live_rb: float, dead_rb: float) -> float | None:
    """Same sensor, different interpretation. alamarBlue: live cells push the
    red/blue ratio up. Map the current rb between a dead control (0%) and a
    live control (100%)."""
    if live_rb == dead_rb:
        return None
    rb = read_color()["rb"]
    return max(0.0, min(100.0, (rb - dead_rb) / (live_rb - dead_rb) * 100.0))


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Benchmate colorimetric titrator")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("read")
    pp = sub.add_parser("pulse"); pp.add_argument("ms", type=int)
    tt = sub.add_parser("titrate")
    tt.add_argument("--target", type=float, required=True)
    tt.add_argument("--direction", choices=["above", "below"], default="above")
    tt.add_argument("--coarse-ms", type=int, default=120)
    tt.add_argument("--fine-ms", type=int, default=20)
    tt.add_argument("--settle", type=float, default=0.5)
    tt.add_argument("--verbose", action="store_true")
    tt.add_argument("--approve", action="store_true")
    sub.add_parser("demo")   # zero-hardware live demo of the closed loop
    a = p.parse_args()

    if a.cmd == "read":
        print(json.dumps(read_color(), indent=2))
    elif a.cmd == "pulse":
        pulse(a.ms); print("dispensed", round(a.ms * UL_PER_MS, 1), "uL")
    elif a.cmd == "titrate":
        print(json.dumps(titrate(a.target, a.direction, a.coarse_ms, a.fine_ms,
                                 settle_s=a.settle, verbose=a.verbose, approve=a.approve), indent=2))
    elif a.cmd == "demo":
        globals()["SIMULATE"] = True; globals()["_link"] = None
        res = titrate(target=1.8, direction="above", settle_s=0.5, verbose=True)
        print("  data: " + res["csv"])
        print('  plot: python plot_run.py "%s"\n' % res["csv"])
