"""Unit tests for reverse_literature_check — mocked Paperclip, no network."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from agent.tools.reverse import (
    MAX_REVERSE_LITERATURE_COMPOUNDS,
    MAX_REVERSE_MAP_PER_RUN,
    REVERSE_SEARCH_VERSION,
    _assay_recommendations_from_entry,
    _build_reverse_query,
    _load_literature_search_cache,
    _max_assay_conc_uM,
    _normalize_tier,
    _parse_activity_entry,
    _recommend_screen_conc_uM,
    _run_reverse_search,
    _select_literature_targets,
    reverse_literature_check,
)


def test_normalize_tier_handles_float_and_string() -> None:
    assert _normalize_tier(1.0) == 1
    assert _normalize_tier("1.0") == 1
    assert _normalize_tier(None) is None
    assert _normalize_tier("") is None


def test_select_literature_targets_default_tier1(compounds_clavulanate: list[dict]) -> None:
    targets = _select_literature_targets(compounds_clavulanate, None, [1])
    ids = {c["compound_id"] for c in targets}
    assert "T1262" in ids
    assert "T19709" not in ids
    assert len(ids) == 6


def test_select_literature_targets_all_library(compounds_clavulanate: list[dict]) -> None:
    targets = _select_literature_targets(compounds_clavulanate, None, None, all_library=True)
    ids = {c["compound_id"] for c in targets}
    assert "T1262" in ids
    assert "T19709" not in ids
    assert len(ids) == 6


def test_build_reverse_query_tier_aware() -> None:
    assert "Ki IC50" in _build_reverse_query("Tazobactam", "inhibitor")
    assert "hydrolysis substrate" in _build_reverse_query("Ampicillin", "antibiotic_substrate")
    assert "nitrocefin" in _build_reverse_query("7-ACA", "other_β_lactam")


def test_parse_activity_entry_extracts_ki_and_pmid() -> None:
    text = "TEM-1 Ki = 0.85 µM for tazobactam. PMID: 12345678. PMC9100253."
    entry = _parse_activity_entry(text, compound_name="Tazobactam", search_id="s_abc", map_id="m_def")
    assert entry["ki_uM"] == 0.85
    assert entry["pmid"] == "12345678"
    assert entry["pmcid"] == "PMC9100253"
    assert entry["paperclip_search_id"] == "s_abc"
    assert entry["paperclip_map_id"] == "m_def"


def test_parse_activity_entry_extracts_literature_assay_concentrations() -> None:
    text = (
        "Screened at 50 µM against TEM-1. Ki = 0.85 µM. "
        "Methods: 0.25 nM TEM-1, clavulanic acid 0.25–5 µM, 200 µM nitrocefin."
    )
    entry = _parse_activity_entry(text, compound_name="Clavulanic Acid", search_id=None, map_id=None)
    assert entry["literature_inhibitor_uM"] == 50
    assert entry["literature_inhibitor_source"] == "explicit_screen"
    assert entry["inhibitor_uM_range"] == [0.25, 5.0]
    assert entry["nitrocefin_uM"] == 200
    assert entry["enzyme_nM"] == 0.25


def test_recommend_screen_conc_prefers_literature_over_activity(compounds_clavulanate: list[dict]) -> None:
    compound = next(c for c in compounds_clavulanate if c["compound_id"] == "T1262")
    entry = {"literature_inhibitor_uM": 50, "ic50_uM": 1.2}
    rec = _recommend_screen_conc_uM(entry, compound)
    assert rec["screen_conc_uM"] == 50
    assert rec["screen_conc_source"] == "literature"


def test_recommend_screen_conc_uses_10x_ic50_capped_at_solubility(compounds_clavulanate: list[dict]) -> None:
    compound = next(c for c in compounds_clavulanate if c["compound_id"] == "T1262")
    entry = {"ic50_uM": 150.0}
    rec = _recommend_screen_conc_uM(entry, compound)
    assert rec["screen_conc_uM"] == 1000
    assert rec["screen_conc_source"] == "10x_ic50"
    assert "capped at library solubility" in rec["screen_rationale"]


def test_recommend_screen_conc_uses_10x_ki_when_no_ic50(compounds_clavulanate: list[dict]) -> None:
    compound = next(c for c in compounds_clavulanate if c["compound_id"] == "T1262")
    entry = {"ki_uM": 1.2}
    rec = _recommend_screen_conc_uM(entry, compound)
    assert rec["screen_conc_uM"] == 12
    assert rec["screen_conc_source"] == "10x_ki"


def test_assay_recommendations_include_parsed_assay_fields(compounds_clavulanate: list[dict]) -> None:
    compound = next(c for c in compounds_clavulanate if c["compound_id"] == "T1262")
    entry = {
        "ki_uM": 1.2,
        "literature_inhibitor_uM": 50,
        "nitrocefin_uM": 200,
        "enzyme_nM": 0.25,
    }
    rec = _assay_recommendations_from_entry(entry, compound)
    block = rec["tem1_nitrocefin"]
    assert block["screen_conc_uM"] == 50
    assert block["nitrocefin_uM"] == 200
    assert block["enzyme_nM"] == 0.25


def test_max_assay_conc_from_library_stock(compounds_clavulanate: list[dict]) -> None:
    compound = next(c for c in compounds_clavulanate if c["compound_id"] == "T1262")
    assert _max_assay_conc_uM(compound) == 1000


@patch("agent.tools.reverse.search_literature")
def test_run_reverse_search_uses_cache(
    mock_search,
    clavulanate_workspace: dict,
) -> None:
    mock_search.return_value = {
        "status": "ok",
        "query": "q",
        "result_id": "s_cached",
        "output": "paper hit",
    }
    cache = _load_literature_search_cache()

    first = _run_reverse_search(
        "TEM-1 tazobactam nitrocefin",
        source="pmc",
        limit=30,
        save_raw=False,
        compound_id="T1262",
        cache=cache,
        use_cache=True,
        search_version=REVERSE_SEARCH_VERSION,
    )
    assert first["cache_hit"] is False
    assert mock_search.call_count == 1

    second = _run_reverse_search(
        "TEM-1 tazobactam nitrocefin",
        source="pmc",
        limit=30,
        save_raw=False,
        compound_id="T1262",
        cache=cache,
        use_cache=True,
        search_version=REVERSE_SEARCH_VERSION,
    )
    assert second["cache_hit"] is True
    assert second["result_id"] == "s_cached"
    assert mock_search.call_count == 1


@patch("agent.tools.reverse.map_literature_results")
@patch("agent.tools.reverse.search_literature")
def test_reverse_literature_check_default_finds_tier1(
    mock_search,
    mock_map,
    clavulanate_workspace: dict,
) -> None:
    mock_search.return_value = {
        "status": "ok",
        "query": "q",
        "result_id": "s_test",
        "output": "paper hit",
    }
    mock_map.return_value = {
        "status": "ok",
        "result_id": "m_test",
        "output": "Ki = 1.2 µM against TEM-1 nitrocefin. PMID: 99999999.",
        "elapsed_ms": 100,
    }

    outcome = reverse_literature_check(
        write_refs=True,
        save_raw=False,
        skip_curated=False,
        sources=["pmc"],
    )

    assert outcome["status"] == "ok"
    assert outcome["checked"] == 6
    assert outcome["map_count"] == 6
    assert mock_search.call_count == 6
    assert mock_map.call_count == 6

    state = json.loads(clavulanate_workspace["SELECTION_STATE_JSON"].read_text())
    lit = state["reverse"]["literature_checks"]
    assert lit["search_count"] == 6
    assert lit["caps"]["max_compounds"] == MAX_REVERSE_LITERATURE_COMPOUNDS
    assert lit["search_version"] == REVERSE_SEARCH_VERSION
    for row in lit["results"]:
        assert row["searches"][0]["elapsed_ms"] >= 0
        assert row["searches"][0]["result_id"] == "s_test"

    t1262_ref = clavulanate_workspace["LITERATURE_REFS_DIR"] / "T1262.json"
    assert t1262_ref.exists()
    payload = json.loads(t1262_ref.read_text())
    assert payload["entries"]
    assert payload["entries"][-1].get("ki_uM") == 1.2
    assay = payload["assay_recommendations"]["tem1_nitrocefin"]
    assert assay["screen_conc_uM"] == 12
    assert assay["screen_conc_source"] == "10x_ki"


@patch("agent.tools.reverse.map_literature_results")
@patch("agent.tools.reverse.search_literature")
def test_reverse_literature_check_skips_curated_ref(
    mock_search,
    mock_map,
    clavulanate_workspace: dict,
) -> None:
    mock_search.return_value = {"status": "ok", "result_id": "s_x", "output": "hit"}
    mock_map.return_value = {"status": "ok", "result_id": "m_x", "output": "Ki = 0.5 µM"}

    outcome = reverse_literature_check(
        compound_ids=["T19860", "T1262"],
        skip_curated=True,
        save_raw=False,
        sources=["pmc"],
    )

    assert "T19860" in outcome["refs_skipped_curated"]
    assert "T1262" in outcome["refs_written"]
    assert mock_search.call_count == 2


@patch("agent.tools.reverse.map_literature_results")
@patch("agent.tools.reverse.search_literature")
def test_reverse_literature_check_truncates_compound_cap(
    mock_search,
    mock_map,
    clavulanate_workspace: dict,
) -> None:
    mock_search.return_value = {"status": "ok", "result_id": "s_x", "output": "hit"}
    mock_map.return_value = {"status": "ok", "result_id": "m_x", "output": "no values"}

    with patch("agent.tools.reverse.MAX_REVERSE_LITERATURE_COMPOUNDS", 2):
        outcome = reverse_literature_check(
            skip_curated=False,
            save_raw=False,
            sources=["pmc"],
            max_compounds_per_run=2,
            max_map_per_run=1,
        )

    assert outcome["checked"] == 2
    assert len(outcome["truncated_compound_ids"]) == 4
    assert outcome["map_count"] == 1
    assert mock_map.call_count == 1


@patch("agent.tools.reverse.map_literature_results")
@patch("agent.tools.reverse.search_literature")
def test_reverse_literature_check_repository_skips_map(
    mock_search,
    mock_map,
    clavulanate_workspace: dict,
) -> None:
    mock_search.return_value = {
        "status": "ok",
        "result_id": "repo_chembl_abc123",
        "output": "Ki=0.5 uM vs TEM-1 beta-lactamase",
    }

    outcome = reverse_literature_check(
        compound_ids=["T1262"],
        skip_curated=False,
        save_raw=False,
        sources=["chembl"],
    )

    assert outcome["checked"] == 1
    assert mock_search.call_count == 1
    mock_map.assert_not_called()
    row = outcome["results"][0]
    assert row["searches"][0]["status"] == "ok"
    assert row.get("maps") is None


@patch("agent.tools.reverse.map_literature_results")
@patch("agent.tools.reverse.search_literature")
def test_reverse_literature_check_multi_source(
    mock_search,
    mock_map,
    clavulanate_workspace: dict,
) -> None:
    mock_search.return_value = {"status": "ok", "result_id": "s_x", "output": "hit"}
    mock_map.return_value = {"status": "ok", "result_id": "m_x", "output": "Ki = 2 µM"}

    outcome = reverse_literature_check(
        compound_ids=["T1262"],
        skip_curated=False,
        save_raw=False,
        sources=["pmc", "biorxiv", "proteins"],
    )

    assert outcome["checked"] == 1
    assert mock_search.call_count == 3
    assert mock_map.call_count == 1
    assert outcome["map_count"] == 3
    assert outcome["map_cache_hits"] == 2
