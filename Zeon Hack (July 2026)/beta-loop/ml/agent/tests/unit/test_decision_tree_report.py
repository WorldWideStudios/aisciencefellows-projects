"""Tests for Run 2 decision tree markdown report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "ml"))

from analysis.decision_tree_report import (  # noqa: E402
    format_decision_tree_report,
    infer_next_action,
    write_decision_tree_report,
)

SUMMARY = REPO_ROOT / "data" / "assay" / "run_2_summary.json"


@pytest.mark.skipif(not SUMMARY.exists(), reason="run_2_summary.json missing")
def test_format_decision_tree_report_sections() -> None:
    summary = json.loads(SUMMARY.read_text())
    md = format_decision_tree_report(summary)
    assert "# Run 2 decision tree report" in md
    assert "## QC gates" in md
    assert "## Compound calls" in md
    assert "## Verdict" in md


@pytest.mark.skipif(not SUMMARY.exists(), reason="run_2_summary.json missing")
def test_infer_next_action_q2_fail() -> None:
    summary = json.loads(SUMMARY.read_text())
    headline, _ = infer_next_action(summary)
    if not summary["qc_gates"]["q2_pass"]:
        assert "Q2" in headline or "enzyme" in headline.lower()


@pytest.mark.skipif(not SUMMARY.exists(), reason="run_2_summary.json missing")
def test_write_decision_tree_report(tmp_path: Path) -> None:
    out = write_decision_tree_report(SUMMARY, tmp_path / "report.md")
    assert out.exists()
    assert "Run 2 decision tree report" in out.read_text()
