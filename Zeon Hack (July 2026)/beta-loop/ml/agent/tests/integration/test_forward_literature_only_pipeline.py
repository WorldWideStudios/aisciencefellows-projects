"""Tier 2 — offline pipeline with Case B literature-only forms."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agent.tools.forward import (
    finalize_forward_run,
    match_literature_to_library,
    search_literature_only_forms,
    seed_reference_inhibitors,
    write_literature_summary_from_forward,
)


def _fake_paperclip_search(
    query: str,
    source: str,
    *,
    save_raw: bool,
    save_dir: Path | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    del save_raw, filename
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
    return {
        "status": "ok",
        "query": query,
        "source": source,
        "result_id": "s_offline_pipeline",
        "output": f"offline results for {query}",
        "elapsed_ms": 1,
    }


def test_forward_pipeline_with_literature_only_finalize(
    clavulanate_with_literature_only: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agent.tools.forward as forward_mod

    monkeypatch.setattr(forward_mod, "_run_capped_search", _fake_paperclip_search)

    seed_reference_inhibitors()
    match = match_literature_to_library()
    assert match["literature_only_count"] == 1

    lit_outcome = search_literature_only_forms(save_raw=False)
    assert lit_outcome["status"] == "ok"
    assert lit_outcome["literature_only_searched"] == 1

    write_literature_summary_from_forward()
    finalized = finalize_forward_run(version=1)
    assert finalized["status"] == "ok"

    run_dir = clavulanate_with_literature_only["FORWARD_RUNS_DIR"] / "v1"
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["literature_only_count"] == 1
    assert manifest["status"] == "complete"

    lo_stub = run_dir / "refs" / "_literature_only" / "avibactam.json"
    assert lo_stub.exists()
    stub = json.loads(lo_stub.read_text())
    assert stub["match"] == "literature_only"

    snapshot = json.loads((run_dir / "state_forward.json").read_text())
    literature_only = snapshot["forward"]["library_matches"]["literature_only"]
    assert literature_only[0]["reference"]["name"] == "avibactam"
