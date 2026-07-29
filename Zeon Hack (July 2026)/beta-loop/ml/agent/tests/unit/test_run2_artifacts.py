"""Tests for Run 2 artifact generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "ml"))

from analysis.run2_artifacts import (  # noqa: E402
    extract_nitrocefin_timing_from_run_log,
    extract_reader_lid_close_utc,
)

RUN_LOG = REPO_ROOT / "data/screens/2/post-run/run_log_exec_tem1_activity_screen_hack_world_22_20260725_230432.txt"
PLATE_MAP = REPO_ROOT / "data/screens/2/v5/plate_map.json"
GEN5_PDF = REPO_ROOT / "data/screens/2/post-run/r2_gen5_export.pdf"


@pytest.mark.skipif(not RUN_LOG.exists(), reason="Run 2 log missing")
def test_extract_nitrocefin_timing_event_count() -> None:
    timing = extract_nitrocefin_timing_from_run_log(RUN_LOG, plate_map_json=PLATE_MAP)
    assert timing["event_count"] == 36
    wells = {e["well"] for e in timing["events"]}
    assert len(wells) == 36
    assert all(e["volume_ul"] == 25.0 for e in timing["events"])
    assert timing["events"][0]["t0_utc"].endswith("Z")


@pytest.mark.skipif(not GEN5_PDF.exists(), reason="Gen5 PDF missing")
def test_extract_reader_lid_close_utc() -> None:
    utc, meta = extract_reader_lid_close_utc(GEN5_PDF)
    assert utc.endswith("Z")
    assert "protocol start" in meta["note"]


@pytest.mark.skipif(not RUN_LOG.exists(), reason="Run 2 log missing")
def test_nitrocefin_timing_json_roundtrip(tmp_path: Path) -> None:
    timing = extract_nitrocefin_timing_from_run_log(RUN_LOG, plate_map_json=PLATE_MAP)
    out = tmp_path / "nitrocefin_timing.json"
    out.write_text(json.dumps(timing, indent=2))
    loaded = json.loads(out.read_text())
    assert loaded["event_count"] == 36
