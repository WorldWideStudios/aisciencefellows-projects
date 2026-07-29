"""Tier 4 — Paperclip integration (manual / nightly)."""

from __future__ import annotations

import json
import os
import warnings

import pytest

from agent.tools.forward import (
    FORWARD_QUERIES,
    MAX_PAPERCLIP_SEARCHES_PER_RUN,
    PAPERCLIP_QUERY_LIMIT,
    _run_capped_search,
    run_forward_literature_searches,
)

PAPERCLIP_LATENCY_BUDGET_MS = 30_000
CLAVULANIC_BENCHMARK_QUERY = "TEM-1 clavulanic acid Ki nitrocefin"
CLAVULANIC_PMID = "40484381"
CLAVULANIC_DOI = "10.1016/j.jbc.2025.110347"
CLAVULANIC_PMCID = "PMC12274840"


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.getenv("PAPERCLIP_API_KEY"), reason="PAPERCLIP_API_KEY not set"),
]


def test_paperclip_batch_query_1(capsys: pytest.CaptureFixture[str]) -> None:
    """Batch query 1 (FORWARD_QUERIES[0]): status ok, elapsed < 30 s."""
    query, source = FORWARD_QUERIES[0]
    result = _run_capped_search(query, source, save_raw=False)

    assert result["status"] == "ok", result.get("error", result)
    assert result.get("result_id")
    assert result["elapsed_ms"] < PAPERCLIP_LATENCY_BUDGET_MS

    print(
        f"batch_query_1 elapsed_ms={result['elapsed_ms']} "
        f"result_id={result.get('result_id')} limit={PAPERCLIP_QUERY_LIMIT}"
    )


def test_paperclip_clavulanic_benchmark(capsys: pytest.CaptureFixture[str]) -> None:
    """Clavulanic-specific query — soft assert on gold citation (top-N may vary)."""
    result = _run_capped_search(CLAVULANIC_BENCHMARK_QUERY, "pmc", save_raw=False)

    assert result["status"] == "ok", result.get("error", result)
    assert result.get("result_id")
    assert result["elapsed_ms"] < PAPERCLIP_LATENCY_BUDGET_MS

    output = result.get("output") or ""
    output_lower = output.lower()
    assert "clavulanic" in output_lower, "expected clavulanic-related Paperclip hits"

    has_benchmark_citation = any(
        marker in output
        for marker in (CLAVULANIC_PMID, CLAVULANIC_DOI, CLAVULANIC_PMCID)
    )
    if not has_benchmark_citation:
        warnings.warn(
            UserWarning(
                f"benchmark citation (PMID {CLAVULANIC_PMID} / DOI {CLAVULANIC_DOI}) "
                f"not in top-{PAPERCLIP_QUERY_LIMIT} results "
                f"(result_id={result.get('result_id')}); "
                "re-run nightly or follow up with Paperclip map --from"
            ),
            stacklevel=1,
        )

    print(
        f"clavulanic_query elapsed_ms={result['elapsed_ms']} "
        f"result_id={result.get('result_id')} "
        f"benchmark_citation={'yes' if has_benchmark_citation else 'soft-miss'} "
        f"limit={PAPERCLIP_QUERY_LIMIT}"
    )


def test_forward_literature_search_cost_log(forward_paths: dict) -> None:
    """run_forward_literature_searches logs elapsed_ms per query; ≤6 searches per v1 run."""
    outcome = run_forward_literature_searches(save_raw=False)

    assert outcome["status"] == "ok"
    assert outcome["search_count"] <= MAX_PAPERCLIP_SEARCHES_PER_RUN

    state = json.loads(forward_paths["SELECTION_STATE_JSON"].read_text())
    lit = state["forward"]["literature_searches"]
    results = lit["results"]

    assert len(results) == outcome["search_count"]
    for entry in results:
        assert entry.get("status") == "ok", entry
        assert isinstance(entry.get("elapsed_ms"), int)
        assert entry["elapsed_ms"] < PAPERCLIP_LATENCY_BUDGET_MS
        assert entry.get("result_id")

    assert lit["search_count"] <= MAX_PAPERCLIP_SEARCHES_PER_RUN
    print(f"forward_batch search_count={lit['search_count']} total_elapsed_ms={sum(r['elapsed_ms'] for r in results)}")
