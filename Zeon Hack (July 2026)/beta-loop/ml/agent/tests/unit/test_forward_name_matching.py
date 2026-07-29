"""Tier 1 — forward name matching (no network)."""

from __future__ import annotations

from typing import Any

from agent.tools.forward import _best_name_match


def test_enmetazobactam_matches_t14081_not_t1262(compounds_clavulanate: list[dict[str, Any]]) -> None:
    match = _best_name_match("enmetazobactam", compounds_clavulanate)
    assert match is not None
    assert match["compound_id"] == "T14081"
    assert match["compound_id"] != "T1262"


def test_clavulanic_prefers_t19860_free_acid(compounds_clavulanate: list[dict[str, Any]]) -> None:
    match = _best_name_match("clavulanic acid", compounds_clavulanate)
    assert match is not None
    assert match["compound_id"] == "T19860"


def test_clavulanate_lithium_matches_t14979(compounds_clavulanate: list[dict[str, Any]]) -> None:
    match = _best_name_match("clavulanate lithium", compounds_clavulanate)
    assert match is not None
    assert match["compound_id"] == "T14979"


def test_excluded_nitrocefin_never_matches(compounds_clavulanate: list[dict[str, Any]]) -> None:
    match = _best_name_match("nitrocefin", compounds_clavulanate)
    assert match is None
