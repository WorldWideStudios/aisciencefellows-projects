"""Tier 1 — Case B literature-only forms (no network)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agent.tools.forward import (
    MAX_LITERATURE_ONLY_QUERIES,
    MAX_PAPERCLIP_SEARCHES_PER_RUN,
    match_literature_to_library,
    search_literature_only_forms,
    seed_reference_inhibitors,
)


def _fake_paperclip_search(
    query: str,
    source: str,
    *,
    save_raw: bool,
    save_dir: Path | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    del save_raw, filename
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "stub.txt").write_text(f"offline stub for {query}\n")
    return {
        "status": "ok",
        "query": query,
        "source": source,
        "result_id": "s_offline_test",
        "output": f"offline results for {query}",
        "elapsed_ms": 1,
    }


def _seed_match_literature_only(
    workspace: dict[str, Path],
    extra_known_inhibitors: list[str] | None = None,
) -> dict[str, Any]:
    if extra_known_inhibitors:
        summary_path = workspace["LITERATURE_SUMMARY_JSON"]
        summary = json.loads(summary_path.read_text())
        known = list(summary.get("known_inhibitors", []))
        for name in extra_known_inhibitors:
            if name not in known:
                known.append(name)
        summary["known_inhibitors"] = known
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    seed_reference_inhibitors()
    return match_literature_to_library()


def test_match_routes_unknown_inhibitor_to_literature_only(
    clavulanate_with_literature_only: dict[str, Path],
) -> None:
    result = _seed_match_literature_only(clavulanate_with_literature_only)

    assert result["literature_only_count"] == 1
    literature_only = result["literature_only"]
    assert literature_only[0]["reference"]["name"] == "avibactam"
    assert literature_only[0]["match"] == "none"

    state = json.loads(clavulanate_with_literature_only["SELECTION_STATE_JSON"].read_text())
    stored = state["forward"]["library_matches"]["literature_only"]
    assert stored[0]["reference"]["name"] == "avibactam"


def test_search_literature_only_no_forms_returns_ok(clavulanate_workspace: dict[str, Path]) -> None:
    seed_reference_inhibitors()
    match_literature_to_library()

    outcome = search_literature_only_forms(save_raw=False)

    assert outcome["status"] == "ok"
    assert outcome["message"] == "no literature_only forms"
    assert outcome["search_results"] == []


def test_search_literature_only_writes_stub(
    clavulanate_with_literature_only: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agent.tools.forward as forward_mod

    monkeypatch.setattr(forward_mod, "_run_capped_search", _fake_paperclip_search)
    _seed_match_literature_only(clavulanate_with_literature_only)

    outcome = search_literature_only_forms(save_raw=False)

    assert outcome["status"] == "ok"
    assert outcome["literature_only_searched"] == 1
    assert len(outcome["search_results"]) == 1
    assert outcome["search_results"][0]["result_id"] == "s_offline_test"

    lo_refs = clavulanate_with_literature_only["LITERATURE_ONLY_REFS_DIR"]
    stub_path = lo_refs / "avibactam.json"
    assert stub_path.exists()
    stub = json.loads(stub_path.read_text())
    assert stub["name"] == "avibactam"
    assert stub["match"] == "literature_only"
    assert stub["entries"] == []
    assert stub["search"]["status"] == "ok"
    assert "TEM-1 avibactam beta-lactamase inhibitor nitrocefin" in stub["query"]

    state = json.loads(clavulanate_with_literature_only["SELECTION_STATE_JSON"].read_text())
    lit = state["forward"]["literature_searches"]
    assert lit["search_count"] == 1
    assert lit["results"][0]["result_id"] == "s_offline_test"


def test_search_literature_only_truncates_when_budget_exhausted(
    clavulanate_with_literature_only: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agent.tools.forward as forward_mod

    monkeypatch.setattr(forward_mod, "_run_capped_search", _fake_paperclip_search)
    _seed_match_literature_only(
        clavulanate_with_literature_only,
        extra_known_inhibitors=["relebactam", "vaborbactam"],
    )

    state_path = clavulanate_with_literature_only["SELECTION_STATE_JSON"]
    state = json.loads(state_path.read_text())
    prior_results = [
        {"status": "ok", "query": f"prior-{idx}", "result_id": f"s_prior_{idx}", "elapsed_ms": 1}
        for idx in range(MAX_PAPERCLIP_SEARCHES_PER_RUN - 1)
    ]
    state["forward"]["literature_searches"] = {
        "search_count": len(prior_results),
        "results": prior_results,
        "truncated": [],
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n")

    outcome = search_literature_only_forms(save_raw=False)

    assert outcome["status"] == "ok"
    assert outcome["literature_only_searched"] == 1
    assert outcome["truncated"] == ["relebactam", "vaborbactam"]

    updated = json.loads(state_path.read_text())
    lit = updated["forward"]["literature_searches"]
    assert lit["search_count"] == MAX_PAPERCLIP_SEARCHES_PER_RUN
    assert lit["truncated"] == ["relebactam", "vaborbactam"]


def test_search_literature_only_cap_exhausted_returns_error(
    clavulanate_with_literature_only: dict[str, Path],
) -> None:
    _seed_match_literature_only(clavulanate_with_literature_only)

    state_path = clavulanate_with_literature_only["SELECTION_STATE_JSON"]
    state = json.loads(state_path.read_text())
    prior_results = [
        {"status": "ok", "query": f"prior-{idx}", "result_id": f"s_prior_{idx}", "elapsed_ms": 1}
        for idx in range(MAX_PAPERCLIP_SEARCHES_PER_RUN)
    ]
    state["forward"]["literature_searches"] = {
        "search_count": len(prior_results),
        "results": prior_results,
        "truncated": [],
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n")

    outcome = search_literature_only_forms(save_raw=False)

    assert outcome["status"] == "error"
    assert str(MAX_PAPERCLIP_SEARCHES_PER_RUN) in outcome["message"]
    assert outcome["search_results"] == []


def test_search_literature_only_respects_literature_only_query_cap(
    clavulanate_with_literature_only: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agent.tools.forward as forward_mod

    monkeypatch.setattr(forward_mod, "_run_capped_search", _fake_paperclip_search)
    extras = [f"literature_only_{idx}" for idx in range(MAX_LITERATURE_ONLY_QUERIES + 2)]
    _seed_match_literature_only(clavulanate_with_literature_only, extra_known_inhibitors=extras)

    outcome = search_literature_only_forms(save_raw=False)

    assert outcome["status"] == "ok"
    assert outcome["literature_only_searched"] == MAX_LITERATURE_ONLY_QUERIES
    assert len(outcome["truncated"]) == 3

    lo_refs = clavulanate_with_literature_only["LITERATURE_ONLY_REFS_DIR"]
    assert len(list(lo_refs.glob("*.json"))) == MAX_LITERATURE_ONLY_QUERIES
