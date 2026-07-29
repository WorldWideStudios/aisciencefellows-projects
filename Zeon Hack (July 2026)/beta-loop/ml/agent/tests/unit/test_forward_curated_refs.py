"""Tier 1 — curated ref guard (Paperclip entries must survive matching)."""

from __future__ import annotations

import json
from pathlib import Path

from agent.tools.forward import match_literature_to_library, seed_reference_inhibitors


def test_match_preserves_curated_t19860_paperclip_entries(clavulanate_workspace: dict[str, Path]) -> None:
    refs_dir = clavulanate_workspace["LITERATURE_REFS_DIR"]
    before = json.loads((refs_dir / "T19860.json").read_text())

    seed_reference_inhibitors()
    match_literature_to_library()

    after = json.loads((refs_dir / "T19860.json").read_text())
    pmids = [entry.get("pmid") for entry in after.get("entries", [])]
    assert "40484381" in pmids
    assert after.get("assay_recommendations") == before.get("assay_recommendations")
    assert after.get("mechanism") == before.get("mechanism")


def test_alternate_form_ref_has_empty_entries(clavulanate_workspace: dict[str, Path]) -> None:
    seed_reference_inhibitors()
    match_literature_to_library()

    t14979 = json.loads((clavulanate_workspace["LITERATURE_REFS_DIR"] / "T14979.json").read_text())
    assert t14979["canonical_compound_id"] == "T19860"
    assert t14979["entries"] == []
    assert t14979["group_id"] == "clavulanate"
