"""Tier 2 — offline forward pipeline integration (tmp_path only)."""

from __future__ import annotations

import json
from pathlib import Path

from agent.tools.forward import (
    finalize_forward_run,
    match_literature_to_library,
    seed_reference_inhibitors,
    write_literature_summary_from_forward,
)


def test_forward_pipeline_offline(clavulanate_workspace: dict[str, Path]) -> None:
    assert seed_reference_inhibitors()["status"] == "ok"
    match = match_literature_to_library()
    assert match["status"] == "ok"
    assert match["direct_and_analog_matches"] >= 5
    assert match["literature_only_count"] == 0
    assert match["compound_group_count"] >= 3

    summary = write_literature_summary_from_forward()
    assert summary["status"] == "ok"
    assert clavulanate_workspace["LITERATURE_SUMMARY_JSON"].exists()

    finalized = finalize_forward_run(version=1)
    assert finalized["status"] == "ok"

    run_dir = clavulanate_workspace["FORWARD_RUNS_DIR"] / "v1"
    for name in (
        "manifest.json",
        "reference_inhibitors.csv",
        "state_forward.json",
        "literature_summary_patch.json",
    ):
        assert (run_dir / name).exists(), f"missing {name}"
    assert (run_dir / "refs").is_dir()
    assert (run_dir / "refs" / "T19860.json").exists()


def test_pipeline_writes_selection_state(clavulanate_workspace: dict[str, Path]) -> None:
    seed_reference_inhibitors()
    match_literature_to_library()
    finalize_forward_run(version=1)

    state = json.loads(clavulanate_workspace["SELECTION_STATE_JSON"].read_text())
    forward = state["forward"]
    assert forward["agent_version"] == "v1"
    assert forward["run_label"] == "forward-research-agent-v1"
    assert forward["manifest"].endswith("ml/workflows/compound_selection/snapshots/forward/v1/manifest.json")
    assert forward.get("finalized_at")
    assert forward.get("compound_groups")
    assert forward["library_matches"]["matches"]
