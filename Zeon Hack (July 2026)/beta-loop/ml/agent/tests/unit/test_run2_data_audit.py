"""Tests for Run 2 data organization audit."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "ml"))

from analysis.run2_data_audit import audit_run2_data, format_audit_markdown  # noqa: E402
from analysis.run2_paths import R2_KINETICS_CSV, R2_POST_RUN_DIR  # noqa: E402


def test_audit_run2_data_structure() -> None:
    report = audit_run2_data()
    assert report.post_run_dir == "data/screens/2/post-run"
    assert isinstance(report.findings, list)
    assert len(report.findings) >= 10
    assert "move_to_post_run" in report.summary or "keep_in_place" in report.summary


def test_audit_markdown_includes_sections() -> None:
    report = audit_run2_data()
    md = format_audit_markdown(report)
    assert "# Run 2 data organization audit" in md
    assert "Executive summary" in md
    assert "Detailed findings" in md


@pytest.mark.skipif(not R2_KINETICS_CSV.exists(), reason="Run 2 kinetics CSV missing")
def test_r2_kinetics_csv_in_post_run() -> None:
    report = audit_run2_data()
    paths = {f["path"] for f in report.findings if f.get("exists")}
    rel = str(R2_KINETICS_CSV.relative_to(REPO_ROOT))
    assert rel in paths
    assert str(R2_POST_RUN_DIR.relative_to(REPO_ROOT)) in report.post_run_dir
