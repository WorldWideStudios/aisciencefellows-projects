"""One call from image -> measurements -> sieve plan -> preflight."""
from __future__ import annotations

from .measure import YoloMeasurer, classical_measure, consensus
from .sieve import plan_stack
from .twin import LabTwin


def analyze(image, px_per_mm, yolo_weights=None, inventory=None, insects=None,
            twin: LabTwin | None = None):
    classical = classical_measure(image, px_per_mm)
    if yolo_weights:
        yolo = YoloMeasurer(yolo_weights)(image, px_per_mm)
        ms = consensus(yolo, classical, px_per_mm)
    else:
        ms = classical
    trusted = [m for m in ms if m.flag is None]
    plan = plan_stack([m.width_mm for m in trusted], inventory, insects)
    twin = twin or LabTwin(inventory)
    return {"measurements": ms, "plan": plan, "preflight_errors": twin.preflight(plan),
            "flagged": [m for m in ms if m.flag]}
