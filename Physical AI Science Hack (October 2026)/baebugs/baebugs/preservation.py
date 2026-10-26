"""Damage risk for each body part given material, flow, agitation and how the
specimen was preserved. Hard parts tolerate stiff, rough meshes; wings,
scales and long legs need smooth monofilament, low flow and submerged handling.
risk = 1 - exp(-k * fragility * stress), stress from abrasion, flow, agitation,
brittleness. Placeholder constants; fit them from verify-step damage counts."""
from __future__ import annotations

import math

from .sieve import load_yaml


def _cfg():
    return load_yaml("materials.yaml")


def stress(material: dict, flow_l_per_min: float, agitation: float,
           preservation: str, cfg=None) -> float:
    cfg = cfg or _cfg()
    brittle = cfg["preservation"][preservation]["brittleness"]
    return (0.5 + material["abrasion"]) * (0.3 + flow_l_per_min) * \
           (0.5 + agitation) * (0.5 + brittle)


def part_risks(profile: str, material: dict, flow_l_per_min=1.0, agitation=0.3,
               preservation="ethanol_70", k=0.8, cfg=None) -> dict[str, float]:
    cfg = cfg or _cfg()
    s = stress(material, flow_l_per_min, agitation, preservation, cfg)
    parts = cfg["specimen_profiles"][profile]["parts"]
    return {p: round(1 - math.exp(-k * f * s), 3) for p, f in parts.items()}


def worst(profile, material, **kw) -> tuple[str, float]:
    r = part_risks(profile, material, **kw)
    p = max(r, key=r.get)
    return p, r[p]


def gentlest_settings(profile, material, preservation="ethanol_70",
                      max_risk=0.25, cfg=None) -> dict:
    """Highest flow/agitation that keeps every part under max_risk on this
    material (coarse grid search); None if even the gentlest setting fails."""
    cfg = cfg or _cfg()
    best = None
    for flow in [0.1, 0.25, 0.5, 0.75, 1.0, 1.5]:
        for ag in [0.0, 0.1, 0.3, 0.5]:
            part, r = worst(profile, material, flow_l_per_min=flow, agitation=ag,
                            preservation=preservation, cfg=cfg)
            if r <= max_risk and (best is None or flow + ag > best["flow"] + best["agitation"]):
                best = {"flow": flow, "agitation": ag, "worst_part": part, "risk": r}
    return best
