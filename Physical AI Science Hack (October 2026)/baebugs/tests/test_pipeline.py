import numpy as np
import pytest

from baebugs.measure import classical_measure, consensus
from baebugs.method import update_margin, verify
from baebugs.sieve import load_yaml, plan_stack
from baebugs.synthetic import make_sample
from baebugs.twin import LabTwin, PreflightError


def _match(ms, truth, ppm):
    pairs = []
    for t in truth:
        d = [np.hypot(m.cx - t["cx"], m.cy - t["cy"]) for m in ms]
        i = int(np.argmin(d))
        if d[i] < 0.5 * ppm:
            pairs.append((ms[i], t))
    return pairs


def test_classical_sizes_within_tolerance():
    ppm = 40.0
    img, truth = make_sample(n=20, px_per_mm=ppm, seed=1)
    ms = classical_measure(img, ppm)
    pairs = _match(ms, truth, ppm)
    assert len(pairs) >= 18
    err_L = np.median([abs(m.length_mm - t["length_mm"]) / t["length_mm"] for m, t in pairs])
    err_W = np.median([abs(m.width_mm - t["width_mm"]) / t["width_mm"] for m, t in pairs])
    assert err_L < 0.08 and err_W < 0.15


def test_consensus_flags_disagreement():
    ppm = 40.0
    img, _ = make_sample(n=5, px_per_mm=ppm, seed=2)
    a = classical_measure(img, ppm)
    b = classical_measure(img, ppm)
    b[0].width_mm *= 2
    out = consensus(a, b, ppm)
    assert sum(m.flag is not None for m in out) == 1


def test_plan_is_coarse_to_fine_and_passes_preflight(tmp_path):
    plan = plan_stack([0.1, 0.3, 0.7, 1.0, 2.0, 3.0])
    ap = [s.aperture_mm for s in plan.steps]
    assert ap == sorted(ap, reverse=True) and len(ap) >= 3
    assert sum(s.expected_count for s in plan.steps) + plan.passthrough_expected == 6
    twin = LabTwin(log_path=tmp_path / "log.jsonl")
    assert twin.preflight(plan) == []
    twin.execute(plan)
    with pytest.raises(PreflightError):  # sieves now in use
        twin.execute(plan)


def test_water_preflight():
    inv = load_yaml("sieves.yaml")
    inv["water"]["reservoir_l"] = 0.6
    plan = plan_stack([0.3, 1.0, 2.0], inventory=inv)
    assert any("water" in e for e in LabTwin(inv).preflight(plan))


def test_margin_update_direction():
    plan = plan_stack([0.6, 0.7, 2.0, 3.0])
    top = plan.steps[0]
    v = verify(plan, {top.sieve_id: top.expected_count + 2})
    assert update_margin(1.1, v) < 1.1
