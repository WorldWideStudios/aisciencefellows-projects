"""Tier 3 — offline forward pipeline on full 105-compound library."""

from __future__ import annotations

import json
from pathlib import Path

from agent.tools.forward import SEED_INHIBITORS

FULL_LIBRARY_COMPOUND_COUNT = 105


def test_full_library_pipeline_offline(forward_full_library_pipeline_result: dict) -> None:
    match = forward_full_library_pipeline_result["match"]
    paths: dict[str, Path] = forward_full_library_pipeline_result["paths"]

    from agent.tools.compounds import load_compounds

    assert len(load_compounds()) == FULL_LIBRARY_COMPOUND_COUNT
    assert match["status"] == "ok"
    assert match["direct_and_analog_matches"] >= len(SEED_INHIBITORS)
    assert match["literature_only_count"] == 0
    assert match["compound_group_count"] >= 3

    run_dir = paths["FORWARD_RUNS_DIR"] / "v1"
    for name in (
        "manifest.json",
        "reference_inhibitors.csv",
        "state_forward.json",
        "literature_summary_patch.json",
    ):
        assert (run_dir / name).exists(), f"missing {name}"

    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["agent"] == "forward_agent"
    assert manifest["status"] == "complete"
    assert manifest["match_count"] >= len(SEED_INHIBITORS)

    ref_ids = manifest["ref_compound_ids"]
    assert ref_ids == sorted(ref_ids)
    assert len(ref_ids) == len(set(ref_ids))
    assert "T19860" in ref_ids
    assert (run_dir / "refs" / "T19860.json").exists()

    matched_ids = {entry["compound_id"] for entry in match["matches"]}
    assert {"T19860", "T1262", "T14081"} <= matched_ids
