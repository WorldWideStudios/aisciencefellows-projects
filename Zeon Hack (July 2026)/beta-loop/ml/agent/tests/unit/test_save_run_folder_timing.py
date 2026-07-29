"""Tests for save_run_folder timing summary helper."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_DIR = REPO_ROOT / "mastermix" / "skills" / "save_run_folder"
SAMPLE_LOG = (
    REPO_ROOT
    / "data"
    / "screens"
    / "2"
    / "post-run"
    / "run_log_exec_tem1_activity_screen_hack_world_22_20260725_230432.txt"
)
WORKFLOW_JSON = REPO_ROOT / "mastermix" / "workflows" / "tem1_activity_screen.json"

sys.path.insert(0, str(SKILLS_DIR))

from timing_summary import (  # noqa: E402
    find_repo_root,
    workflow_id_from_metadata,
    write_run_log_timing_summary,
)


def test_find_repo_root_from_project_data() -> None:
    project_data = REPO_ROOT / "mastermix" / "data"
    assert find_repo_root(project_data=project_data) == REPO_ROOT


def test_workflow_id_from_metadata(tmp_path: Path) -> None:
    meta = tmp_path / "metadata.json"
    meta.write_text(json.dumps({"workflow_id": "tem1_activity_screen_hack_world_22"}))
    assert workflow_id_from_metadata(meta) == "tem1_activity_screen_hack_world_22"
    assert workflow_id_from_metadata(tmp_path / "missing.json") is None


def test_write_timing_summary_from_jsonl(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    jl = logs / "run_log.jsonl"
    jl.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "t": "2026-07-25T23:04:32+00:00",
                        "type": "step_start",
                        "label": "Pick Up Pipette",
                        "msg": "",
                    }
                ),
                json.dumps(
                    {
                        "t": "2026-07-25T23:05:00+00:00",
                        "type": "step_start",
                        "label": "Prepare Dilutions",
                        "msg": "",
                    }
                ),
            ]
        )
        + "\n"
    )

    out = write_run_log_timing_summary(
        logs,
        workflow_id="tem1_activity_screen",
        repo_root=REPO_ROOT,
    )
    assert out == logs / "timing_summary.json"
    assert out.exists()
    payload = json.loads(out.read_text())
    assert payload["header"]["duration_human"]
    assert len(payload["step_spans"]) >= 1


@pytest.mark.skipif(not SAMPLE_LOG.exists(), reason="sample rendered log missing")
def test_write_timing_summary_from_rendered_txt(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "run_log.txt").write_text(SAMPLE_LOG.read_text())

    out = write_run_log_timing_summary(
        logs,
        workflow_id="tem1_activity_screen",
        repo_root=REPO_ROOT,
    )
    assert out is not None
    payload = json.loads(out.read_text())
    assert payload["header"]["execution_id"].startswith("exec_tem1_activity_screen")
    assert payload["phase_summaries"]


def test_write_timing_summary_best_effort_on_bad_log(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "run_log.txt").write_text("not a valid log\n")

    warnings: list[str] = []
    out = write_run_log_timing_summary(
        logs,
        repo_root=REPO_ROOT,
        log_warning=warnings.append,
    )
    # Parser is tolerant; best-effort means no exception and optional empty artifact.
    assert out is None or out.exists()
    assert not warnings
