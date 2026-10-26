"""Explore filters x hardware x capture methods with an append-only Merkle ledger.

Every run is a leaf: hash(config + results). The ledger is append-only (MMR
style: earlier leaves never change); after every append the root is recorded as
a break point, so any claim ("SCREEN-1 + partabot + AmScope is best") is pinned
to a root that commits to all the evidence before it.

Two ways to ask "what actually helps", compared side by side:

* LOMO (leave-one-level-out): for each factor level, the best score achievable
  with that level removed from the options vs. with everything. A big drop means
  the level is irreplaceable; zero means something else does as well.
* Merkle break points: the steps where the golden path (best config so far)
  changed, with the root at that moment and the size of the jump. Levels that
  enter the golden path at a break point are the ones that moved the frontier.

Agreement between the two = robust finding. Disagreement = run more combinations
(LOMO sees the whole ledger; break points see order of discovery).
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field

import numpy as np

from .preservation import part_risks
from .sieve import load_yaml

FACTORS = ("filter", "hardware", "capture")

HARDWARE = {  # flow multiplier, agitation, flow jitter
    "manual":          {"flow_x": 1.0, "agitation": 0.5, "jitter": 0.30},
    "partabot_arm":    {"flow_x": 1.0, "agitation": 0.3, "jitter": 0.15},
    "esp32_bugsorter": {"flow_x": 1.0, "agitation": 0.2, "jitter": 0.08},
}
CAPTURE = {  # relative sizing noise, detection miss rate
    "amscope_md300a":   {"noise": 0.03, "miss": 0.02},
    "bugpicker_topcam": {"noise": 0.05, "miss": 0.04},
    "phone":            {"noise": 0.09, "miss": 0.08},
}


def _h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return "0" * 64
    level = leaves[:]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [_h((a + b).encode()) for a, b in zip(level[::2], level[1::2])]
    return level[0]


def score(results: dict, w_damage=1.5, w_size=2.0, w_contam=0.6) -> float:
    return (results["recovery"] - w_damage * results["damage"]
            - w_size * results["size_error"] - w_contam * results.get("contamination", 0.0))


@dataclass
class Ledger:
    runs: list[dict] = field(default_factory=list)
    leaves: list[str] = field(default_factory=list)
    breakpoints: list[dict] = field(default_factory=list)

    def append(self, config: dict, results: dict):
        rec = {"config": config, "results": results, "score": round(score(results), 4)}
        leaf = _h(json.dumps(rec, sort_keys=True).encode())
        self.runs.append(rec); self.leaves.append(leaf)
        best = max(self.runs, key=lambda r: r["score"])
        prev = self.breakpoints[-1]["best"] if self.breakpoints else None
        changed = prev is None or best["config"] != prev["config"]
        self.breakpoints.append({
            "step": len(self.runs), "leaf": leaf, "root": merkle_root(self.leaves),
            "best": best, "golden_path_changed": changed,
            "delta": round(best["score"] - (prev["score"] if prev else 0.0), 4)})
        return leaf

    def golden_path(self):
        return [b for b in self.breakpoints if b["golden_path_changed"]]

    def verify(self) -> bool:
        for i, r in enumerate(self.runs):
            if _h(json.dumps(r, sort_keys=True).encode()) != self.leaves[i]:
                return False
            if self.breakpoints[i]["root"] != merkle_root(self.leaves[:i + 1]):
                return False
        return True


def lomo(ledger: Ledger, factor: str) -> list[dict]:
    best_all = max(r["score"] for r in ledger.runs)
    levels = sorted({r["config"][factor] for r in ledger.runs})
    out = []
    for lv in levels:
        rest = [r["score"] for r in ledger.runs if r["config"][factor] != lv]
        best_wo = max(rest) if rest else -math.inf
        out.append({"factor": factor, "level": lv,
                    "n_runs": sum(r["config"][factor] == lv for r in ledger.runs),
                    "best_without": round(best_wo, 4),
                    "drop_if_removed": round(best_all - best_wo, 4)})
    return sorted(out, key=lambda d: -d["drop_if_removed"])


def compare_lomo_breakpoints(ledger: Ledger, min_drop: float = 0.02) -> dict:
    gp = ledger.golden_path()
    final = gp[-1]["best"]["config"]
    rep = {}
    for f in FACTORS:
        top = lomo(ledger, f)[0]
        entered = [b["best"]["config"][f] for b in gp]
        rep[f] = {"lomo_top": top["level"], "lomo_drop": top["drop_if_removed"],
                  "golden_path_final": final[f], "golden_path_history": entered,
                  "agree": top["level"] == final[f],
                  "verdict": ("robust" if top["level"] == final[f] and top["drop_if_removed"] >= min_drop
                              else "weak - run more combinations" if top["level"] == final[f]
                              else "disagree - run more combinations")}
    return rep


# ---------------- simulator for test cases ----------------

def simulate_run(config: dict, bodies: list[dict], target: tuple[float, float],
                 materials=None, seed=0, margin=1.1) -> dict:
    """bodies: [{width_mm, profile}], target: width band we want retained.
    recovery = fraction of target-band bodies retained intact and detected;
    contamination = share of the retained fraction that is smaller bycatch;
    damage = mean worst-part damage probability; size_error = capture noise
    (+ jitter-induced misplacement)."""
    rng = np.random.default_rng(seed)
    materials = materials or {m["id"]: m for m in load_yaml("materials.yaml")["materials"]}
    m = materials[config["filter"]]
    hw, cap = HARDWARE[config["hardware"]], CAPTURE[config["capture"]]
    flow = config.get("flow", 0.5) * hw["flow_x"] * (1 + rng.normal(0, hw["jitter"]))
    flow = max(0.05, flow)
    a = m["aperture_mm"]
    lo, hi = target
    got = tgt = off = off_kept = 0
    dmg = []
    for b in bodies:
        w = b["width_mm"]
        p_ret = 1.0 if a == 0 else 1 / (1 + math.exp(-(w - a * margin) / (0.08 * a + 0.02)))
        risks = part_risks(b["profile"], m, flow_l_per_min=flow, agitation=hw["agitation"],
                           preservation=config.get("preservation", "ethanol_70"))
        worst = max(risks.values())
        dmg.append(worst)
        if lo <= w < hi:
            tgt += 1
            intact = rng.random() > worst
            seen = rng.random() > cap["miss"]
            got += int(rng.random() < p_ret and intact and seen)
        elif w < lo:  # smaller than the band: should pass; kept = bycatch in the fraction
            off += 1
            off_kept += int(rng.random() < p_ret)
    kept_total = got + off_kept
    return {"recovery": round(got / max(tgt, 1), 4),
            "contamination": round(off_kept / max(kept_total, 1), 4),
            "damage": round(float(np.mean(dmg)), 4),
            "size_error": round(cap["noise"] * (1 + hw["jitter"]), 4), "flow": round(flow, 3)}
