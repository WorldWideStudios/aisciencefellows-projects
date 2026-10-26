"""Turn measured insect widths into a sieve stack + water-flow plan.

A body is retained on square mesh when its narrowest axis exceeds the aperture
(times a margin, since bodies are soft and orient in flow). To split class k from
smaller classes we pick the largest inventory aperture that still retains class k.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import yaml

CONFIG = Path(__file__).parent / "config"


def load_yaml(name_or_path):
    p = Path(name_or_path)
    if not p.exists():
        p = CONFIG / name_or_path
    return yaml.safe_load(p.read_text())


@dataclass
class StackStep:
    sieve_id: str
    aperture_mm: float
    slot: str
    purpose: str
    flow_l_per_min: float
    rinse_l: float
    expected_count: int = 0


@dataclass
class SievePlan:
    steps: list[StackStep] = field(default_factory=list)
    passthrough_expected: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def water_l(self):
        return round(sum(s.rinse_l for s in self.steps), 3)

    def to_dict(self):
        return {"steps": [asdict(s) for s in self.steps],
                "passthrough_expected": self.passthrough_expected,
                "water_l": self.water_l, "notes": self.notes}


def classify(width_mm: float, classes) -> str:
    for c in classes:
        lo, hi = c["width_mm"]
        if lo <= width_mm < hi:
            return c["name"]
    return "unclassified"


def flow_for(aperture_mm, base):
    # finer mesh -> gentler flow so bodies aren't forced through or damaged
    return round(base * float(np.clip(aperture_mm / 1.0, 0.25, 1.5)), 3)


def plan_stack(widths_mm, inventory=None, insects=None,
               rinse_l_per_sieve=0.5, catch_all=True) -> SievePlan:
    inventory = inventory or load_yaml("sieves.yaml")
    insects = insects or load_yaml("insects.yaml")
    margin = insects.get("retention_margin", 1.1)
    base = inventory["water"]["flow_l_per_min_default"]
    avail = sorted([s for s in inventory["sieves"] if not s.get("in_use")],
                   key=lambda s: -s["aperture_mm"])
    widths = np.asarray(sorted(widths_mm))
    plan = SievePlan()
    if widths.size == 0:
        plan.notes.append("no insects measured; nothing to sieve")
        return plan

    present = {classify(w, insects["classes"]) for w in widths}
    # cut points: lower width bound of each present class, largest first
    cuts = sorted({c["width_mm"][0] for c in insects["classes"] if c["name"] in present},
                  reverse=True)
    if catch_all:
        cuts.append(float(widths.min()))  # catch everything above the drain
    chosen = []
    for i, cut in enumerate(cuts):
        last_ap = chosen[-1]["aperture_mm"] if chosen else float("inf")
        cands = [s for s in avail if s["aperture_mm"] < last_ap]
        if not cands:
            plan.notes.append(f"no sieve left to split at width {cut:.3f} mm")
            continue
        if catch_all and i == len(cuts) - 1:
            # final catch: largest sieve that still retains the smallest body
            fine = [s for s in cands if s["aperture_mm"] * margin <= cut]
            if not fine:
                plan.notes.append(f"nothing fine enough to catch width {cut:.3f} mm")
                continue
            chosen.append(fine[0])
            continue
        # split: effective cut (aperture*margin) closest to the class boundary
        s = min(cands, key=lambda s: abs(s["aperture_mm"] * margin - cut))
        chosen.append(s)

    remaining = widths.copy()
    for s in chosen:
        retained = remaining[remaining * 1.0 >= s["aperture_mm"] * margin]
        remaining = remaining[remaining < s["aperture_mm"] * margin]
        plan.steps.append(StackStep(
            s["id"], s["aperture_mm"], s["slot"],
            purpose=f"retain width >= {s['aperture_mm'] * margin:.3f} mm",
            flow_l_per_min=flow_for(s["aperture_mm"], base),
            rinse_l=rinse_l_per_sieve, expected_count=int(retained.size)))
    plan.passthrough_expected = int(remaining.size)
    if remaining.size:
        plan.notes.append(f"{remaining.size} bodies predicted to pass the finest sieve")
    return plan
