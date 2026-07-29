"""Tests for run log timing parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis.run_log_timing import (
    DEFAULT_PHASE_RULES,
    analyze_run_log,
    baseline_filename,
    check_timing_regression,
    format_text_summary,
    load_timing_baseline,
    load_timing_phases,
    load_workflow_step_index,
    parse_run_log_path,
    report_to_dict,
    resolve_timing_baseline_path,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SAMPLE_LOG = (
    REPO_ROOT
    / "data"
    / "screens"
    / "2"
    / "post-run"
    / "run_log_exec_tem1_activity_screen_hack_world_22_20260725_230432.txt"
)
WORKFLOW_JSON = REPO_ROOT / "mastermix" / "workflows" / "tem1_activity_screen.json"
TEM1_BASELINE = (
    REPO_ROOT / "ml" / "analysis" / "timing_baselines" / baseline_filename("tem1_activity_screen", "1.0.0")
)


@pytest.fixture
def sample_report():
    if not SAMPLE_LOG.exists():
        pytest.skip(f"missing sample log: {SAMPLE_LOG}")
    return analyze_run_log(SAMPLE_LOG, workflow_json=WORKFLOW_JSON)


def test_parse_sample_log_duration(sample_report) -> None:
    assert sample_report.total_seconds == pytest.approx(171 * 60 + 21, rel=0.02)
    assert sample_report.header.execution_id.startswith("exec_tem1_activity_screen")


def test_workflow_mapping(sample_report) -> None:
    assert sample_report.workflow_mapping["mapped_count"] >= 30
    assert sample_report.workflow_mapping["unmatched_labels"] == []

    prepare = next(s for s in sample_report.step_spans if s.label == "Prepare Dilutions")
    assert prepare.node_id == "prepare_dilutions"
    assert prepare.skill_id == "prepare_tem1_dilution_plate"
    assert prepare.phase == "setup"


def test_nitrocefin_steps(sample_report) -> None:
    nitro_prep = next(s for s in sample_report.step_spans if s.label == "Prepare Nitrocefin")
    assert nitro_prep.duration_seconds == pytest.approx(19 * 60 + 4, rel=0.05)
    assert nitro_prep.phase == "nitrocefin_prep"

    nitro_spans = [s for s in sample_report.step_spans if s.label.startswith("Nitrocefin:")]
    assert len(nitro_spans) == 12
    total_nitro_dispense = sum(s.duration_seconds for s in nitro_spans)
    assert total_nitro_dispense == pytest.approx(17 * 60 + 3, rel=0.05)


def test_phase_budget(sample_report) -> None:
    phases = {p.phase: p.duration_seconds for p in sample_report.phase_summaries}
    assert phases["setup"] == pytest.approx(75 * 60 + 59, rel=0.05)
    assert phases["nitrocefin_prep"] == pytest.approx(19 * 60 + 4, rel=0.05)
    assert phases["nitrocefin_dispense"] == pytest.approx(17 * 60 + 3, rel=0.05)


def test_idle_gaps_include_dilution_incubation(sample_report) -> None:
    long_gaps = [g for g in sample_report.idle_gaps if g.duration_seconds > 30 * 60]
    assert len(long_gaps) >= 1
    assert any(g.after_step == "Prepare Dilutions" for g in long_gaps)


def test_dispense_intervals(sample_report) -> None:
    assert len(sample_report.dispense_intervals) >= 50
    deltas = [d.delta_seconds for d in sample_report.dispense_intervals if d.delta_seconds is not None]
    assert max(deltas) > 30 * 60


def test_report_to_dict_json_serializable(sample_report) -> None:
    payload = report_to_dict(sample_report)
    text = json.dumps(payload)
    assert "phase_summaries" in text
    assert payload["header"]["duration_human"]


def test_format_text_summary(sample_report) -> None:
    text = format_text_summary(sample_report)
    assert "Phase budget" in text
    assert "Prepare Dilutions" in text


def test_load_workflow_step_index() -> None:
    index, phase_rules = load_workflow_step_index(WORKFLOW_JSON)
    assert "Dispense Test Compound 1" in index
    assert index["Dispense Test Compound 1"].node_id == "dispense_compound_1"
    assert index["Nitrocefin: Compound 1"].timing_label == "compound_1"
    assert index["Prepare Dilutions"].phase == "setup"
    assert phase_rules[0][0] == "setup"


def test_load_timing_phases_from_workflow_json() -> None:
    data = json.loads(WORKFLOW_JSON.read_text())
    rules = load_timing_phases(data)
    assert rules[0] == ("setup", ("prepare dilutions", "pick up pipette"))
    assert any(phase == "nitrocefin_dispense" for phase, _ in rules)


def test_load_timing_phases_fallback() -> None:
    assert load_timing_phases({}) == DEFAULT_PHASE_RULES


def test_cfps_workflow_has_custom_phases() -> None:
    cfps_json = REPO_ROOT / "mastermix" / "workflows" / "cfps_mastermix.json"
    index, phase_rules = load_workflow_step_index(cfps_json)
    assert index["Make Positive-Control Master Mix"].phase == "mastermix_build"
    assert index["Dispense Sample Mix"].phase == "plate_loading"
    assert index["Start Shaker"].phase == "incubation"
    assert any(phase == "mastermix_build" for phase, _ in phase_rules)


def test_resolve_timing_baseline_from_workflow_json() -> None:
    path = resolve_timing_baseline_path(workflow_json=WORKFLOW_JSON)
    assert path == TEM1_BASELINE
    assert path.exists()


def test_sample_log_within_timing_baseline(sample_report) -> None:
    baseline = load_timing_baseline(TEM1_BASELINE)
    violations = check_timing_regression(sample_report, baseline)
    assert violations == [], f"unexpected timing regressions: {violations}"


def test_check_timing_regression_detects_slow_phase(sample_report) -> None:
    baseline = load_timing_baseline(TEM1_BASELINE)
    slow = sample_report.phase_summaries[0]
    slow.duration_seconds *= 1.5
    sample_report.phase_summaries[0] = slow
    violations = check_timing_regression(sample_report, baseline)
    assert len(violations) >= 1
    assert slow.phase in violations[0]
    assert "exceeds baseline" in violations[0]


def test_parse_jsonl_minimal(tmp_path: Path) -> None:
    jl = tmp_path / "run_log.jsonl"
    jl.write_text(
        "\n".join(
            [
                json.dumps({"t": "2026-07-25T23:04:32+00:00", "type": "step_start", "label": "Pick Up Pipette", "msg": ""}),
                json.dumps({"t": "2026-07-25T23:05:00+00:00", "type": "event", "label": "", "msg": "grabbed pipette"}),
            ]
        )
        + "\n"
    )
    report = parse_run_log_path(jl)
    assert len(report.step_spans) == 1
    assert report.step_spans[0].label == "Pick Up Pipette"
