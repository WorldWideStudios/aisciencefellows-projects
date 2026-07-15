"""Smoke tests — no data downloads required.

These check the invariants that make the score interpretable: the package
imports, the axis list and weight table agree, and the weights sum to 1 so
that every candidate's total_score stays on a 0-1 scale.
"""
import math

import har_annotator
from har_annotator import score


def test_package_imports_and_version():
    assert har_annotator.__version__


def test_weights_sum_to_one():
    total = sum(score.WEIGHTS.values())
    assert math.isclose(total, 1.0, abs_tol=1e-9), f"weights sum to {total}, not 1.0"


def test_components_match_weight_keys():
    assert set(score.COMPONENTS) == set(score.WEIGHTS), (
        "COMPONENTS and WEIGHTS must cover the same axes"
    )


def test_all_weights_positive():
    assert all(w > 0 for w in score.WEIGHTS.values())
