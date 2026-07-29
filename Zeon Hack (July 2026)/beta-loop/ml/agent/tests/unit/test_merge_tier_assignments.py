"""Unit tests for merge tier de-duplication."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agent.tools import selection as selection_mod


def _write_state(path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _minimal_compounds() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = {
        "T19860": ("inhibitor", False),
        "T1262": ("inhibitor", False),
        "T6685": ("inhibitor", False),
        "T14081": ("inhibitor", False),
        "T14979": ("inhibitor", False),
        "T1631": ("inhibitor", False),
        "T13038": ("inhibitor", False),
        "T1213": ("inhibitor", False),
        "T0138": ("antibiotic_substrate", False),
        "T0366": ("antibiotic_substrate", False),
        "T0198": ("antibiotic_substrate", False),
        "T1005": ("antibiotic_substrate", False),
        "T0985": ("antibiotic_substrate", False),
        "T0814": ("antibiotic_substrate", False),
        "T0224": ("other_β_lactam", False),
        "T1029": ("other_β_lactam", False),
    }
    for cid, (scaffold_class, exclude) in specs.items():
        rows.append(
            {
                "compound_id": cid,
                "name": cid,
                "scaffold_class": scaffold_class,
                "exclude": exclude,
            }
        )
    return rows


@pytest.fixture
def merge_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workflow = tmp_path / "ml" / "workflows" / "compound_selection"
    workflow.mkdir(parents=True)
    data = tmp_path / "data"
    data.mkdir()
    compounds_csv = data / "compounds.csv"

    import pandas as pd

    pd.DataFrame(_minimal_compounds()).to_csv(compounds_csv, index=False)

    monkeypatch.setattr(selection_mod, "SELECTION_STATE_JSON", workflow / "state.json")

    import agent.tools.compounds as compounds_mod

    monkeypatch.setattr(compounds_mod, "COMPOUNDS_CSV", compounds_csv)

    state = {
        "forward": {},
        "reverse": {
            "dock_rank": {
                "tier3_candidates": ["T0138", "T0198", "T0366", "T1005", "T0224", "T1029"],
            },
            "scaffold_classification": {
                "compounds": [
                    {"compound_id": cid, "scaffold_class": row["scaffold_class"]}
                    for cid, row in zip(
                        [r["compound_id"] for r in _minimal_compounds()],
                        _minimal_compounds(),
                        strict=True,
                    )
                ]
            },
        },
        "bridge": {
            "tier2_analogs": {"candidates": []},
            "clustering": {
                "representatives": [
                    {"compound_id": "T0366"},
                    {"compound_id": "T0985"},
                    {"compound_id": "T0814"},
                ]
            },
        },
    }
    _write_state(workflow / "state.json", state)
    return workflow


def test_merge_tier_assignments_has_no_overlap(merge_workspace) -> None:
    result = selection_mod.merge_tier_assignments()
    tiers = result["tiers"]

    all_ids = (
        tiers["tier1_inhibitors"]
        + tiers["tier2_analogs"]
        + tiers["tier3_docking_or_diverse"]
        + tiers["tier4_substrate_controls"]
    )
    assert len(all_ids) == len(set(all_ids)), f"duplicate tier assignments: {all_ids}"
    assert "T0366" not in tiers["tier3_docking_or_diverse"]
    assert "T0366" in tiers["tier4_substrate_controls"]
