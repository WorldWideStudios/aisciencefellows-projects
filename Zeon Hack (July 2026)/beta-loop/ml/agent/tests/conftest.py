"""Shared fixtures for forward agent tests — tmp_path only, never repo data/."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(REPO_ROOT / ".env")


def _patch_agent_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Path]:
    """Redirect agent.paths (and tool imports) to an isolated tmp data tree."""
    data = tmp_path / "data"
    literature = data / "literature"
    refs = literature / "refs"
    lo_refs = refs / "_literature_only"
    ml_root = tmp_path / "ml"
    workflow = ml_root / "workflows" / "compound_selection"
    forward_snapshots = workflow / "snapshots" / "forward"
    local_lit = tmp_path / "pvjthomas" / "local" / "literature"

    for directory in (refs, lo_refs, workflow, forward_snapshots, local_lit):
        directory.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {
        "REPO_ROOT": tmp_path,
        "ML_ROOT": ml_root,
        "PVJ_ROOT": tmp_path / "pvjthomas",
        "DATA_DIR": data,
        "LITERATURE_DIR": literature,
        "LITERATURE_REFS_DIR": refs,
        "LITERATURE_ONLY_REFS_DIR": lo_refs,
        "COMPOUNDS_CSV": data / "compounds.csv",
        "LITERATURE_SUMMARY_JSON": data / "literature_summary.json",
        "REFERENCE_INHIBITORS_CSV": data / "reference_inhibitors.csv",
        "WORKFLOW_COMPOUND_SELECTION": workflow,
        "SELECTION_STATE_JSON": workflow / "state.json",
        "LITERATURE_SEARCH_CACHE_JSON": workflow / "literature_search_cache.json",
        "SELECTION_DRAFT_PLATE_JSON": workflow / "plate_map_r2_draft.json",
        "SIMILARITY_NEIGHBORS_JSON": workflow / "neighbors.json",
        "FORWARD_SNAPSHOTS_DIR": forward_snapshots,
        "FORWARD_RUNS_DIR": forward_snapshots,
        "LOCAL_LITERATURE": local_lit,
    }

    import agent.paths as agent_paths
    import agent.tools.compounds as compounds_mod
    import agent.tools.forward as forward_mod
    import agent.tools.literature as literature_mod
    import agent.tools.reverse as reverse_mod

    for key, value in paths.items():
        monkeypatch.setattr(agent_paths, key, value)
        if hasattr(forward_mod, key):
            monkeypatch.setattr(forward_mod, key, value)
        if hasattr(reverse_mod, key):
            monkeypatch.setattr(reverse_mod, key, value)
        if key == "COMPOUNDS_CSV":
            monkeypatch.setattr(compounds_mod, "COMPOUNDS_CSV", value)
        if key in ("LITERATURE_SUMMARY_JSON", "LITERATURE_DIR"):
            monkeypatch.setattr(literature_mod, key, value)

    return paths


@pytest.fixture
def forward_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    return _patch_agent_paths(monkeypatch, tmp_path)


@pytest.fixture
def clavulanate_workspace(forward_paths: dict[str, Path]) -> dict[str, Path]:
    """6-compound fixture library + literature summary + curated T19860 ref."""
    shutil.copy(FIXTURES_DIR / "compounds_clavulanate_subset.csv", forward_paths["COMPOUNDS_CSV"])
    shutil.copy(
        FIXTURES_DIR / "literature_summary_clavulanate.json",
        forward_paths["LITERATURE_SUMMARY_JSON"],
    )
    shutil.copy(
        FIXTURES_DIR / "refs" / "T19860.json",
        forward_paths["LITERATURE_REFS_DIR"] / "T19860.json",
    )
    return forward_paths


@pytest.fixture
def clavulanate_with_literature_only(clavulanate_workspace: dict[str, Path]) -> dict[str, Path]:
    """Clavulanate fixture plus avibactam (not in the 6-compound library) for Case B tests."""
    summary_path = clavulanate_workspace["LITERATURE_SUMMARY_JSON"]
    summary = json.loads(summary_path.read_text())
    known = list(summary.get("known_inhibitors", []))
    if "avibactam" not in known:
        known.append("avibactam")
    summary["known_inhibitors"] = known
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return clavulanate_workspace


@pytest.fixture
def compounds_clavulanate(clavulanate_workspace: dict[str, Path]) -> list[dict[str, Any]]:
    from agent.tools.compounds import load_compounds

    return load_compounds()


@pytest.fixture
def forward_pipeline_result(clavulanate_workspace: dict[str, Path]) -> dict[str, Any]:
    """Run full offline forward pipeline in tmp_path."""
    from agent.tools.forward import (
        finalize_forward_run,
        match_literature_to_library,
        seed_reference_inhibitors,
        write_literature_summary_from_forward,
    )

    seed_reference_inhibitors()
    match = match_literature_to_library()
    write_literature_summary_from_forward()
    finalized = finalize_forward_run(version=1)
    return {"match": match, "finalized": finalized, "paths": clavulanate_workspace}


@pytest.fixture
def screen_workspace(forward_paths: dict[str, Path]) -> dict[str, Path]:
    """Round 1 v3 plate compounds (23 IDs) + project literature summary + curated T19860 ref."""
    shutil.copy(FIXTURES_DIR / "compounds_screen_v3_subset.csv", forward_paths["COMPOUNDS_CSV"])
    repo_summary = REPO_ROOT / "data" / "literature_summary.json"
    if repo_summary.exists():
        shutil.copy(repo_summary, forward_paths["LITERATURE_SUMMARY_JSON"])
    else:
        shutil.copy(
            FIXTURES_DIR / "literature_summary_clavulanate.json",
            forward_paths["LITERATURE_SUMMARY_JSON"],
        )
    shutil.copy(
        FIXTURES_DIR / "refs" / "T19860.json",
        forward_paths["LITERATURE_REFS_DIR"] / "T19860.json",
    )
    return forward_paths


@pytest.fixture
def forward_screen_pipeline_result(screen_workspace: dict[str, Path]) -> dict[str, Any]:
    """Run full offline forward pipeline on the v3 screen compound subset."""
    from agent.tools.forward import (
        finalize_forward_run,
        match_literature_to_library,
        seed_reference_inhibitors,
        write_literature_summary_from_forward,
    )

    seed_reference_inhibitors()
    match = match_literature_to_library()
    write_literature_summary_from_forward()
    finalized = finalize_forward_run(version=1)
    return {"match": match, "finalized": finalized, "paths": screen_workspace}


@pytest.fixture
def full_library_workspace(forward_paths: dict[str, Path]) -> dict[str, Path]:
    """Full 105-compound library in tmp_path (read-only copy from repo data/)."""
    repo_data = REPO_ROOT / "data"
    shutil.copy(repo_data / "compounds.csv", forward_paths["COMPOUNDS_CSV"])
    summary_src = repo_data / "literature_summary.json"
    if summary_src.exists():
        shutil.copy(summary_src, forward_paths["LITERATURE_SUMMARY_JSON"])
    else:
        shutil.copy(
            FIXTURES_DIR / "literature_summary_clavulanate.json",
            forward_paths["LITERATURE_SUMMARY_JSON"],
        )
    shutil.copy(
        FIXTURES_DIR / "refs" / "T19860.json",
        forward_paths["LITERATURE_REFS_DIR"] / "T19860.json",
    )
    return forward_paths


@pytest.fixture
def forward_full_library_pipeline_result(full_library_workspace: dict[str, Path]) -> dict[str, Any]:
    """Run full offline forward pipeline on the 105-compound library."""
    from agent.tools.forward import (
        finalize_forward_run,
        match_literature_to_library,
        seed_reference_inhibitors,
        write_literature_summary_from_forward,
    )

    seed_reference_inhibitors()
    match = match_literature_to_library()
    write_literature_summary_from_forward()
    finalized = finalize_forward_run(version=1)
    return {"match": match, "finalized": finalized, "paths": full_library_workspace}
