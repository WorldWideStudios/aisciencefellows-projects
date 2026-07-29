"""Tier 3 — offline matching timing benchmarks."""

from __future__ import annotations

import time
from typing import Any

import pytest

from agent.tools.compounds import load_compounds
from agent.tools.forward import (
    SEED_INHIBITORS,
    _best_name_match,
    match_literature_to_library,
    seed_reference_inhibitors,
)

# v1 budgets — see FORWARD_TEST_PLAN.md
TOTAL_MATCH_BUDGET_MS = 500
PER_REFERENCE_BUDGET_MS = 100
FULL_LIBRARY_COMPOUND_COUNT = 105


@pytest.mark.benchmark
@pytest.mark.parametrize("reference", ["clavulanic acid", "enmetazobactam"])
def test_per_reference_match_timing(
    full_library_workspace: dict[str, Any],
    reference: str,
) -> None:
    """Record per-reference match latency against full library."""
    load_start = time.perf_counter()
    compounds = load_compounds()
    library_scan_ms = int((time.perf_counter() - load_start) * 1000)

    assert len(compounds) == FULL_LIBRARY_COMPOUND_COUNT

    match_start = time.perf_counter()
    hit = _best_name_match(reference, compounds)
    match_ms = int((time.perf_counter() - match_start) * 1000)

    assert hit is not None, f"{reference} should match library"
    print(f"{reference:20} match_ms={match_ms:4d}  library_scan_ms={library_scan_ms:4d}")

    assert match_ms < PER_REFERENCE_BUDGET_MS, (
        f"{reference} match took {match_ms} ms (budget {PER_REFERENCE_BUDGET_MS} ms)"
    )


@pytest.mark.benchmark
def test_full_library_match_timing_budget(full_library_workspace: dict[str, Any]) -> None:
    """v1 budget: seed + match on 105 compounds and 5 seeds completes under 500 ms."""
    seed_reference_inhibitors()

    start = time.perf_counter()
    result = match_literature_to_library()
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    assert result["status"] == "ok"
    assert result["direct_and_analog_matches"] >= len(SEED_INHIBITORS)
    print(f"full_library_match_ms={elapsed_ms}")

    assert elapsed_ms < TOTAL_MATCH_BUDGET_MS, (
        f"full match took {elapsed_ms} ms (budget {TOTAL_MATCH_BUDGET_MS} ms)"
    )
