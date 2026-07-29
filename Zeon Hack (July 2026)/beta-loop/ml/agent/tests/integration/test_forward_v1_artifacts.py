"""Tier 2 — v1 artifact contract + clavulanic gold assertions."""

from __future__ import annotations

import json
from pathlib import Path


def test_v1_manifest_contract(forward_pipeline_result: dict) -> None:
    paths: dict[str, Path] = forward_pipeline_result["paths"]
    run_dir = paths["FORWARD_RUNS_DIR"] / "v1"
    manifest = json.loads((run_dir / "manifest.json").read_text())

    assert manifest["agent"] == "forward_agent"
    assert manifest["version"] == 1
    assert manifest["label"] == "forward-research-agent-v1"
    assert manifest["status"] == "complete"
    assert manifest["match_count"] >= 4
    assert manifest["literature_only_count"] == 0
    assert manifest["compound_group_count"] >= 3

    ref_ids = manifest["ref_compound_ids"]
    assert ref_ids == sorted(ref_ids)
    assert len(ref_ids) == len(set(ref_ids))

    # Snapshot artifacts under run_dir
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "reference_inhibitors.csv").exists()
    assert (run_dir / "state_forward.json").exists()
    assert (run_dir / "literature_summary_patch.json").exists()
    assert (run_dir / "refs" / "T19860.json").exists()

    # Active paths (written outside run_dir snapshot)
    assert paths["REFERENCE_INHIBITORS_CSV"].exists()
    assert paths["SELECTION_STATE_JSON"].exists()


def test_clavulanic_gold_assertions(forward_pipeline_result: dict) -> None:
    paths: dict[str, Path] = forward_pipeline_result["paths"]
    run_dir = paths["FORWARD_RUNS_DIR"] / "v1"
    manifest = json.loads((run_dir / "manifest.json").read_text())

    clav_group = next(g for g in manifest["compound_groups"] if g["group_id"] == "clavulanate")
    assert clav_group["canonical_compound_id"] == "T19860"
    assert set(clav_group["compound_ids"]) == {"T19860", "T14979"}

    t19860 = json.loads((run_dir / "refs" / "T19860.json").read_text())
    assert t19860["compound_id"] == "T19860"
    ki_entry = next(e for e in t19860["entries"] if e.get("pmid") == "40484381")
    assert ki_entry["ki_uM"] == 0.85
    assert t19860.get("assay_recommendations", {}).get("tem1_nitrocefin", {}).get("screen_conc_uM") == 50

    priors = json.loads(paths["LITERATURE_SUMMARY_JSON"].read_text())
    assert priors["compound_assay_priors"]["T19860"]["expected_at_50uM"] == ">=50% inhibition"

    t14979 = json.loads((run_dir / "refs" / "T14979.json").read_text())
    assert t14979["canonical_compound_id"] == "T19860"
    assert t14979["entries"] == []


def test_state_forward_snapshot_fields(forward_pipeline_result: dict) -> None:
    paths: dict[str, Path] = forward_pipeline_result["paths"]
    snapshot = json.loads((paths["FORWARD_RUNS_DIR"] / "v1" / "state_forward.json").read_text())
    assert snapshot["agent"] == "forward_agent"
    assert snapshot["agent_version"] == "v1"
    assert snapshot["run_label"] == "forward-research-agent-v1"
    forward = snapshot["forward"]
    assert forward.get("library_matches")
    assert forward.get("compound_groups")

    # finalized_at lives on active selection state, not the forward-only snapshot blob
    state = json.loads(paths["SELECTION_STATE_JSON"].read_text())
    assert state["forward"].get("finalized_at")
    assert state["forward"].get("manifest").endswith(
        "ml/workflows/compound_selection/snapshots/forward/v1/manifest.json"
    )
