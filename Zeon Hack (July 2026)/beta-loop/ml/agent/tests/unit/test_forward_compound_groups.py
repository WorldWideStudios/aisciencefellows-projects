"""Tier 1 — alternate-form compound grouping (Case A)."""

from __future__ import annotations

from typing import Any

from agent.tools.forward import build_compound_groups


def test_clavulanate_group(compounds_clavulanate: list[dict[str, Any]]) -> None:
    groups = build_compound_groups(compounds_clavulanate, {"T19860", "T14979"})
    clav = next(g for g in groups if g["group_id"] == "clavulanate")
    assert set(clav["compound_ids"]) == {"T19860", "T14979"}
    assert clav["canonical_compound_id"] == "T19860"
    canonical_forms = [f for f in clav["forms"] if f["is_canonical"]]
    assert len(canonical_forms) == 1
    assert canonical_forms[0]["compound_id"] == "T19860"


def test_sulbactam_group(compounds_clavulanate: list[dict[str, Any]]) -> None:
    groups = build_compound_groups(compounds_clavulanate, {"T1631", "T6685"})
    sul = next(g for g in groups if g["group_id"] == "sulbactam")
    assert set(sul["compound_ids"]) == {"T1631", "T6685"}
    assert sul["canonical_compound_id"] == "T1631"


def test_single_match_expands_manual_form_group(compounds_clavulanate: list[dict[str, Any]]) -> None:
    """Matching only T14979 should still pull in canonical T19860 via MANUAL_FORM_GROUPS."""
    groups = build_compound_groups(compounds_clavulanate, {"T14979"})
    clav = next(g for g in groups if g["group_id"] == "clavulanate")
    assert "T19860" in clav["compound_ids"]
    assert clav["canonical_compound_id"] == "T19860"
