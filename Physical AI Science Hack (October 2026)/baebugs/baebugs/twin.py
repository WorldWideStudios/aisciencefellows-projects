"""Lab digital twin + preflight, in the spirit of Google Research's VERID:
the agent never sends an arm command that the twin hasn't checked against live
state (sieve exists, free, ordered coarse->fine, enough water). Every action is
logged so a run can be replayed and audited.
"""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path

from .sieve import SievePlan, load_yaml


class PreflightError(Exception):
    pass


class LabTwin:
    def __init__(self, inventory=None, log_path="runs/actions.jsonl"):
        self.state = copy.deepcopy(inventory or load_yaml("sieves.yaml"))
        self.log_path = Path(log_path)

    def _sieve(self, sid):
        for s in self.state["sieves"]:
            if s["id"] == sid:
                return s
        return None

    def preflight(self, plan: SievePlan) -> list[str]:
        errs, last = [], float("inf")
        slots = set()
        for st in plan.steps:
            s = self._sieve(st.sieve_id)
            if s is None:
                errs.append(f"{st.sieve_id}: not in inventory"); continue
            if s.get("in_use"):
                errs.append(f"{st.sieve_id}: already in use")
            if s["aperture_mm"] >= last:
                errs.append(f"{st.sieve_id}: stack not coarse->fine")
            if s["slot"] in slots:
                errs.append(f"{st.sieve_id}: slot {s['slot']} reused")
            last, _ = s["aperture_mm"], slots.add(s["slot"])
        w = self.state["water"]
        if w["reservoir_l"] - plan.water_l < w["min_reserve_l"]:
            errs.append(f"water: need {plan.water_l} L, have "
                        f"{w['reservoir_l'] - w['min_reserve_l']:.2f} L above reserve")
        return errs

    def execute(self, plan: SievePlan, robot=None, dry_run=True):
        errs = self.preflight(plan)
        if errs:
            self.log("preflight_failed", errors=errs)
            raise PreflightError("; ".join(errs))
        for st in plan.steps:
            self._sieve(st.sieve_id)["in_use"] = True
            self.log("place_sieve", sieve=st.sieve_id, slot=st.slot, dry_run=dry_run)
            if robot and not dry_run:
                robot.place_sieve(st.slot)
        for st in plan.steps:
            self.state["water"]["reservoir_l"] -= st.rinse_l
            self.log("rinse", sieve=st.sieve_id, flow=st.flow_l_per_min,
                     litres=st.rinse_l, dry_run=dry_run)
            if robot and not dry_run:
                robot.rinse(st.flow_l_per_min, st.rinse_l)
        return self.state

    def release(self, plan: SievePlan):
        for st in plan.steps:
            self._sieve(st.sieve_id)["in_use"] = False
        self.log("release", sieves=[s.sieve_id for s in plan.steps])

    def log(self, action, **kw):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a") as f:
            f.write(json.dumps({"t": time.time(), "action": action, **kw}) + "\n")


class RobotAdapter:
    """Interface the arm driver implements. Swap in the hackathon's arm SDK."""
    def place_sieve(self, slot: str): raise NotImplementedError
    def rinse(self, flow_l_per_min: float, litres: float): raise NotImplementedError
