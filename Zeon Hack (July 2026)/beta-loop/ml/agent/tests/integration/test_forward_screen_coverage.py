"""Tier 2.5 — forward pipeline on Round 1 v3 screen compound subset."""

from __future__ import annotations

import json
from pathlib import Path

from agent.tools.forward import (
    finalize_forward_run,
    match_literature_to_library,
    seed_reference_inhibitors,
)

# Bucket 1 — Tier-1 inhibitors on data/screens/1/v3/plate_map.json (B1–B4)
TIER1_INHIBITOR_IDS = frozenset({"T19860", "T1262", "T6685", "T14081"})

# Bucket 2 — inhibitor-adjacent wells (C1–C3); C4 (T1213) is an intentional substrate wildcard
INHIBITOR_ANALOG_IDS = frozenset({"T14979", "T1631", "T13038"})

# Representative substrate / exploration wells — forward seeds must not map here
SUBSTRATE_SCREEN_IDS = frozenset(
    {
        "T1005",
        "T1008",
        "T0199",
        "T0198",
        "T0814",
        "T1213",
        "T0138",
        "T0366",
        "T30787",
    }
)

SCREEN_COMPOUND_COUNT = 23


def test_screen_subset_library_size(screen_workspace: dict[str, Path]) -> None:
    from agent.tools.compounds import load_compounds

    compounds = load_compounds()
    assert len(compounds) == SCREEN_COMPOUND_COUNT
    assert {c["compound_id"] for c in compounds} == TIER1_INHIBITOR_IDS | INHIBITOR_ANALOG_IDS | SUBSTRATE_SCREEN_IDS | {
        "T0234",
        "T0985",
        "T1001",
        "T6385",
        "T67978",
        "T8390",
        "TQ0056",
    }


def test_forward_covers_tier1_inhibitors_on_screen(forward_screen_pipeline_result: dict) -> None:
    match = forward_screen_pipeline_result["match"]
    assert match["status"] == "ok"

    matched_ids = {entry["compound_id"] for entry in match["matches"]}
    related_ids = set(matched_ids)
    for entry in match["matches"]:
        related_ids.update(entry.get("related_forms") or [])

    assert TIER1_INHIBITOR_IDS <= related_ids, (
        f"missing Tier-1 inhibitor coverage (direct or related form): "
        f"{TIER1_INHIBITOR_IDS - related_ids}"
    )

    by_ref = {entry["reference_name"]: entry for entry in match["matches"]}
    assert by_ref["enmetazobactam"]["compound_id"] == "T14081"
    assert by_ref["enmetazobactam"]["compound_id"] != "T1262"
    assert by_ref["clavulanic acid"]["compound_id"] == "T19860"
    assert by_ref["tazobactam"]["compound_id"] == "T1262"
    assert by_ref["sulbactam"]["compound_id"] in {"T1631", "T6685"}
    assert "T6685" in (by_ref["sulbactam"].get("related_forms") or [])


def test_forward_does_not_match_substrate_wells(forward_screen_pipeline_result: dict) -> None:
    matched_ids = {entry["compound_id"] for entry in forward_screen_pipeline_result["match"]["matches"]}
    overlap = matched_ids & SUBSTRATE_SCREEN_IDS
    assert not overlap, f"substrate wells incorrectly matched as inhibitors: {sorted(overlap)}"


def test_screen_clavulanate_group_and_analog_refs(forward_screen_pipeline_result: dict) -> None:
    paths: dict[str, Path] = forward_screen_pipeline_result["paths"]
    run_dir = paths["FORWARD_RUNS_DIR"] / "v1"
    manifest = json.loads((run_dir / "manifest.json").read_text())

    clav_group = next(g for g in manifest["compound_groups"] if g["group_id"] == "clavulanate")
    assert clav_group["canonical_compound_id"] == "T19860"
    assert "T14979" in clav_group["compound_ids"]

    t14979 = json.loads((run_dir / "refs" / "T14979.json").read_text())
    assert t14979["canonical_compound_id"] == "T19860"
    assert t14979["entries"] == []


def test_screen_pipeline_finalize_artifacts(forward_screen_pipeline_result: dict) -> None:
    paths: dict[str, Path] = forward_screen_pipeline_result["paths"]
    run_dir = paths["FORWARD_RUNS_DIR"] / "v1"

    for name in (
        "manifest.json",
        "reference_inhibitors.csv",
        "state_forward.json",
        "literature_summary_patch.json",
    ):
        assert (run_dir / name).exists(), f"missing {name}"

    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["match_count"] >= len(TIER1_INHIBITOR_IDS)
    assert manifest["literature_only_count"] == 0


def test_screen_offline_pipeline_end_to_end(screen_workspace: dict[str, Path]) -> None:
    assert seed_reference_inhibitors()["status"] == "ok"
    match = match_literature_to_library()
    assert match["status"] == "ok"
    assert match["direct_and_analog_matches"] >= len(TIER1_INHIBITOR_IDS)

    finalized = finalize_forward_run(version=1)
    assert finalized["status"] == "ok"
    assert (screen_workspace["FORWARD_RUNS_DIR"] / "v1" / "refs" / "T19860.json").exists()
