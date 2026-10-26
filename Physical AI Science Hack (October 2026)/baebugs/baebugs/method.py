"""Mechanical scientific method loop around the sieve.

1. Observe   - image the raw sample, measure (two models + consensus)
2. Hypothesize - predict how many bodies each sieve retains (plan_stack)
3. Test      - twin preflight, then the arm runs the stack
4. Verify    - image each sieve's fraction, measure again, compare to prediction
5. Update    - adjust retention_margin so the next prediction is better
"""
from __future__ import annotations

from dataclasses import dataclass

from .sieve import SievePlan


@dataclass
class Verdict:
    sieve_id: str
    predicted: int
    observed: int

    @property
    def error(self):
        return self.observed - self.predicted


def verify(plan: SievePlan, observed_counts: dict[str, int],
           observed_passthrough: int | None = None) -> list[Verdict]:
    v = [Verdict(s.sieve_id, s.expected_count, observed_counts.get(s.sieve_id, 0))
         for s in plan.steps]
    if observed_passthrough is not None:
        v.append(Verdict("drain", plan.passthrough_expected, observed_passthrough))
    return v


def update_margin(margin: float, verdicts: list[Verdict], lr: float = 0.05,
                  lo: float = 0.8, hi: float = 1.6) -> float:
    """If coarse sieves catch MORE than predicted, bodies are being retained
    more easily than assumed -> lower the margin; fewer -> raise it."""
    coarse = [v for v in verdicts if v.sieve_id != "drain"]
    if not coarse:
        return margin
    top = coarse[0]
    denom = max(top.predicted, 1)
    signal = top.error / denom
    return float(min(hi, max(lo, margin * (1 - lr * signal))))
