"""Tests for nitrocefin kinetics analysis (Run 2 decision tree)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from analysis.kinetics import (
    HIT_THRESHOLD_PCT,
    align_slope_window,
    analyze_kinetics_file,
    classify_slope,
    compute_pct_inhibition,
    compute_pct_inhibition_endpoint,
)


def _write_kinetics_csv(path: Path, wells: dict[str, float], times: list[float] | None = None) -> None:
    """Write CSV with linear A490 = slope * time for each well."""
    if times is None:
        times = [float(t) for t in range(0, 601, 30)]
    rows = []
    for well, slope in wells.items():
        for t in times:
            rows.append({"well": well, "time_s": t, "a490": slope * t})
    pd.DataFrame(rows).to_csv(path, index=False)


def _write_kinetics_csv_plateau(
    path: Path,
    plateaus: dict[str, float],
    times: list[float] | None = None,
) -> None:
    """Write CSV with flat endpoint A490 (ramps to plateau by t=60 s)."""
    if times is None:
        times = [float(t) for t in range(0, 901, 30)]
    rows = []
    for well, plateau in plateaus.items():
        for t in times:
            a490 = plateau if t >= 60 else plateau * t / 60.0
            rows.append({"well": well, "time_s": t, "a490": a490})
    pd.DataFrame(rows).to_csv(path, index=False)


def _write_plate_map(path: Path) -> None:
    wells = {
        "B3": {"role": "vehicle", "compound_id": None, "concentration_uM": 0},
        "B7": {"role": "vehicle", "compound_id": None, "concentration_uM": 0},
        "C11": {"role": "vehicle", "compound_id": None, "concentration_uM": 0},
        "D3": {"role": "no_tem1", "compound_id": None, "concentration_uM": 0},
        "D7": {"role": "no_tem1", "compound_id": None, "concentration_uM": 0},
        "E11": {"role": "no_tem1", "compound_id": None, "concentration_uM": 0},
        "F3": {"role": "pos-ctrl-clavaculin", "compound_id": "T19860", "concentration_uM": 50},
        "F7": {"role": "pos-ctrl-clavaculin", "compound_id": "T19860", "concentration_uM": 50},
        "G11": {"role": "pos-ctrl-clavaculin", "compound_id": "T19860", "concentration_uM": 50},
        "B2": {"role": "sample", "compound_id": "T1262", "concentration_uM": 1.0},
        "D2": {"role": "sample", "compound_id": "T1262", "concentration_uM": 1.0},
        "F2": {"role": "sample", "compound_id": "T1262", "concentration_uM": 1.0},
        "B5": {"role": "sample", "compound_id": "T1005", "concentration_uM": 50},
        "D5": {"role": "sample", "compound_id": "T1005", "concentration_uM": 50},
        "F5": {"role": "sample", "compound_id": "T1005", "concentration_uM": 50},
    }
    path.write_text(json.dumps({"wells": wells}, indent=2) + "\n")


def _write_timing(
    path: Path,
    well_offsets_min: dict[str, float],
    base: datetime | None = None,
) -> None:
    """Write timing JSON; offsets are minutes before reader lid close."""
    base = base or datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    reader_close = base
    events = []
    for well, offset_min in well_offsets_min.items():
        t0 = reader_close - timedelta(minutes=offset_min)
        events.append(
            {
                "t0_utc": t0.isoformat(),
                "condition": well,
                "well": well,
                "source_anchor": "test",
                "volume_ul": 25.0,
            }
        )
    path.write_text(json.dumps({"run_id": "test", "events": events}, indent=2) + "\n")


def test_classify_slope_flat_hot() -> None:
    assert classify_slope(0.0005, 0.0002) == "flat"
    assert classify_slope(0.01, 0.0002) == "hot"
    assert classify_slope(0.002, 0.0002) == "ambiguous"


def test_align_slope_window_without_timing() -> None:
    start, end = align_slope_window(None, None)
    assert start == 180.0
    assert end == 480.0


def test_compute_pct_inhibition() -> None:
    assert compute_pct_inhibition(0.01, 0.01, 0.0) == pytest.approx(0.0)
    assert compute_pct_inhibition(0.0, 0.01, 0.0) == pytest.approx(100.0)
    assert compute_pct_inhibition(0.005, 0.01, 0.0) == pytest.approx(50.0)


def test_compute_pct_inhibition_endpoint() -> None:
    assert compute_pct_inhibition_endpoint(0.12, 0.12, 0.06) == pytest.approx(0.0)
    assert compute_pct_inhibition_endpoint(0.06, 0.12, 0.06) == pytest.approx(100.0)
    assert compute_pct_inhibition_endpoint(0.09, 0.12, 0.06) == pytest.approx(50.0)


def test_q2_pass_vehicle_hot_nt_flat(tmp_path: Path) -> None:
    csv_path = tmp_path / "kinetics.csv"
    map_path = tmp_path / "plate_map.json"
    _write_plate_map(map_path)
    slopes = {
        "B3": 0.01,
        "B7": 0.012,
        "C11": 0.011,
        "D3": 0.0002,
        "D7": 0.0001,
        "E11": 0.0002,
        "F3": 0.0002,
        "F7": 0.0001,
        "G11": 0.0002,
        "B2": 0.0002,
        "D2": 0.0001,
        "F2": 0.0002,
        "B5": 0.01,
        "D5": 0.011,
        "F5": 0.012,
    }
    _write_kinetics_csv(csv_path, slopes)

    result = analyze_kinetics_file(csv_path, plate_map_json=map_path, round_number=2)
    assert result["qc_gates"]["q2_pass"] is True
    assert result["scoring_mode"] == "slope"
    assert result["qc_gates"]["q3_pass"] is True
    assert result["qc_gates"]["pos_ctrl_median_pct"] >= HIT_THRESHOLD_PCT
    assert "T1262" in result["compounds"]
    assert result["compounds"]["T1262"]["label"] == "confirmed_hit"


def test_q2_fail_falls_back_to_endpoint_scoring(tmp_path: Path) -> None:
    """When slope Q2 fails (all flat), score compounds via aligned endpoint A490."""
    csv_path = tmp_path / "kinetics.csv"
    map_path = tmp_path / "plate_map.json"
    _write_plate_map(map_path)
    plateaus = {
        "B3": 0.12,
        "B7": 0.12,
        "C11": 0.12,
        "D3": 0.06,
        "D7": 0.06,
        "E11": 0.06,
        "F3": 0.07,
        "F7": 0.07,
        "G11": 0.07,
        "B2": 0.08,
        "D2": 0.08,
        "F2": 0.08,
        "B5": 0.11,
        "D5": 0.11,
        "F5": 0.11,
    }
    _write_kinetics_csv_plateau(csv_path, plateaus)

    result = analyze_kinetics_file(csv_path, plate_map_json=map_path, round_number=2)
    assert result["qc_gates"]["q2_pass"] is False
    assert result["qc_gates"]["q2_endpoint_pass"] is True
    assert result["scoring_mode"] == "endpoint"
    assert result["qc_gates"]["q3_pass"] is True
    assert result["qc_gates"]["pos_ctrl_median_pct"] >= HIT_THRESHOLD_PCT
    assert result["compounds"]["T1262"]["label"] == "confirmed_hit"
    assert result["compounds"]["T1005"]["label"] == "confirmed_substrate"
    assert "T1005" not in {h["compound_id"] for h in result["hits"]}


def test_q2_fail_both_flat(tmp_path: Path) -> None:
    csv_path = tmp_path / "kinetics.csv"
    map_path = tmp_path / "plate_map.json"
    _write_plate_map(map_path)
    flat = 0.0002
    slopes = {well: flat for well in [
        "B3", "B7", "C11", "D3", "D7", "E11", "F3", "F7", "G11",
        "B2", "D2", "F2", "B5", "D5", "F5",
    ]}
    _write_kinetics_csv(csv_path, slopes)

    result = analyze_kinetics_file(csv_path, plate_map_json=map_path, round_number=2)
    assert result["qc_gates"]["q2_pass"] is False


def test_timing_suspect_early_substrate_flat(tmp_path: Path) -> None:
    csv_path = tmp_path / "kinetics.csv"
    map_path = tmp_path / "plate_map.json"
    timing_path = tmp_path / "nitrocefin_timing.json"
    _write_plate_map(map_path)

    reader_close = datetime(2026, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
    _write_timing(
        timing_path,
        {
            "D3": 25.0,
            "D7": 25.0,
            "E11": 25.0,
            "F3": 20.0,
            "F7": 20.0,
            "G11": 20.0,
            "B5": 20.0,
            "D5": 20.0,
            "F5": 20.0,
            "B2": 20.0,
            "D2": 20.0,
            "F2": 20.0,
            "B3": 2.0,
            "B7": 2.0,
            "C11": 2.0,
        },
        base=reader_close,
    )

    slopes = {
        "B3": 0.01,
        "B7": 0.012,
        "C11": 0.011,
        "D3": 0.0002,
        "D7": 0.0001,
        "E11": 0.0002,
        "F3": 0.01,
        "F7": 0.011,
        "G11": 0.012,
        "B2": 0.0002,
        "D2": 0.0001,
        "F2": 0.0002,
        "B5": 0.0002,
        "D5": 0.0001,
        "F5": 0.0002,
    }
    _write_kinetics_csv(csv_path, slopes)

    result = analyze_kinetics_file(
        csv_path,
        plate_map_json=map_path,
        nitrocefin_timing_json=timing_path,
        reader_lid_close_utc=reader_close.isoformat(),
        round_number=2,
    )

    assert result["qc_gates"]["q2_pass"] is True
    assert result["qc_gates"]["q1t_timing_stagger"] is True
    assert "B5" in result["wells_timing_suspect"]
    assert result["compounds"]["T1005"]["label"] == "false_flat_substrate"
    assert "T1005" not in {h["compound_id"] for h in result["hits"]}


def test_aligned_hot_vs_global_flat(tmp_path: Path) -> None:
    """Substrate well flat globally but hot when window is aligned to early t0."""
    csv_path = tmp_path / "kinetics.csv"
    map_path = tmp_path / "plate_map.json"
    timing_path = tmp_path / "nitrocefin_timing.json"
    _write_plate_map(map_path)

    reader_close = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # B5 dosed 4 min before reader — aligned window overlaps reader 180–480 s
    _write_timing(
        timing_path,
        {"B5": 4.0, "B3": 1.0, "B7": 1.0, "C11": 1.0},
        base=reader_close,
    )

    times = [float(t) for t in range(0, 601, 30)]
    rows = []
    for well, slope in {
        "B3": 0.01,
        "B7": 0.01,
        "C11": 0.01,
        "D3": 0.0002,
        "D7": 0.0002,
        "E11": 0.0002,
        "F3": 0.0002,
        "F7": 0.0002,
        "G11": 0.0002,
        "B2": 0.0002,
        "D2": 0.0002,
        "F2": 0.0002,
        "D5": 0.0002,
        "F5": 0.0002,
    }.items():
        for t in times:
            rows.append({"well": well, "time_s": t, "a490": slope * t})

    # B5: hot slope in aligned window (180–240 s), flat plateau in global window (240–480 s)
    for t in times:
        if t <= 240:
            a490 = 0.01 * t
        else:
            a490 = 0.01 * 240  # plateau — flat in 240–480 portion of global window
        rows.append({"well": "B5", "time_s": t, "a490": a490})

    pd.DataFrame(rows).to_csv(csv_path, index=False)

    result = analyze_kinetics_file(
        csv_path,
        plate_map_json=map_path,
        nitrocefin_timing_json=timing_path,
        reader_lid_close_utc=reader_close.isoformat(),
        round_number=2,
    )

    b5 = result["wells"]["B5"]
    assert b5["slope_class_aligned"] == "hot"
    assert b5["slope_class_global"] != "hot"
    assert b5["timing_suspect"] is True


def _write_r3_plate_map(path: Path) -> None:
    """Minimal Run 3 v1 layout — no vehicle, substrate controls anchor scoring."""
    wells = {
        "D3": {"role": "no_tem1", "compound_id": None, "concentration_uM": 0},
        "D7": {"role": "no_tem1", "compound_id": None, "concentration_uM": 0},
        "E11": {"role": "no_tem1", "compound_id": None, "concentration_uM": 0},
        "F3": {"role": "pos-ctrl-clavaculin", "compound_id": "T19860", "concentration_uM": 50},
        "F7": {"role": "pos-ctrl-clavaculin", "compound_id": "T19860", "concentration_uM": 50},
        "G11": {"role": "pos-ctrl-clavaculin", "compound_id": "T19860", "concentration_uM": 50},
        "B2": {"role": "sample", "compound_id": "T1262", "bucket": "tier1_inhibitor", "concentration_uM": 1.0},
        "D2": {"role": "sample", "compound_id": "T1262", "bucket": "tier1_inhibitor", "concentration_uM": 1.0},
        "F2": {"role": "sample", "compound_id": "T1262", "bucket": "tier1_inhibitor", "concentration_uM": 1.0},
        "B10": {"role": "sample", "compound_id": "T1008", "bucket": "substrate_control", "concentration_uM": 50},
        "D10": {"role": "sample", "compound_id": "T1008", "bucket": "substrate_control", "concentration_uM": 50},
        "F10": {"role": "sample", "compound_id": "T1008", "bucket": "substrate_control", "concentration_uM": 50},
        "C5": {"role": "sample", "compound_id": "T0224", "bucket": "substrate_control", "concentration_uM": 50},
        "E5": {"role": "sample", "compound_id": "T0224", "bucket": "substrate_control", "concentration_uM": 50},
        "G5": {"role": "sample", "compound_id": "T0224", "bucket": "substrate_control", "concentration_uM": 50},
        "C9": {"role": "sample", "compound_id": "T0985", "bucket": "substrate_control", "concentration_uM": 50},
        "E9": {"role": "sample", "compound_id": "T0985", "bucket": "substrate_control", "concentration_uM": 50},
        "G9": {"role": "sample", "compound_id": "T0985", "bucket": "substrate_control", "concentration_uM": 50},
    }
    path.write_text(json.dumps({"wells": wells}, indent=2) + "\n")


def test_r3_substrate_anchor_q2_pass_slope_mode(tmp_path: Path) -> None:
    csv_path = tmp_path / "kinetics.csv"
    map_path = tmp_path / "plate_map.json"
    _write_r3_plate_map(map_path)
    slopes = {
        "D3": 0.0002,
        "D7": 0.0001,
        "E11": 0.0002,
        "F3": 0.0002,
        "F7": 0.0001,
        "G11": 0.0002,
        "B2": 0.0002,
        "D2": 0.0001,
        "F2": 0.0002,
        "B10": 0.01,
        "D10": 0.012,
        "F10": 0.011,
        "C5": 0.01,
        "E5": 0.011,
        "G5": 0.012,
        "C9": 0.01,
        "E9": 0.011,
        "G9": 0.012,
    }
    _write_kinetics_csv(csv_path, slopes)

    result = analyze_kinetics_file(csv_path, plate_map_json=map_path, round_number=3)
    assert result["control_stats"]["anchor_mode"] == "substrate"
    assert result["qc_gates"]["q2_pass"] is True
    assert result["scoring_mode"] == "slope"
    assert result["qc_gates"]["q3_pass"] is True
    assert result["compounds"]["T1262"]["label"] == "confirmed_hit"


def test_r3_substrate_anchor_endpoint_fallback(tmp_path: Path) -> None:
    """Run 3: when slope Q2 fails, fall back to endpoint scoring via substrate anchor."""
    csv_path = tmp_path / "kinetics.csv"
    map_path = tmp_path / "plate_map.json"
    _write_r3_plate_map(map_path)
    plateaus = {
        "D3": 0.06,
        "D7": 0.06,
        "E11": 0.06,
        "F3": 0.07,
        "F7": 0.07,
        "G11": 0.07,
        "B2": 0.08,
        "D2": 0.08,
        "F2": 0.08,
        "B10": 0.12,
        "D10": 0.12,
        "F10": 0.12,
        "C5": 0.11,
        "E5": 0.11,
        "G5": 0.11,
        "C9": 0.12,
        "E9": 0.12,
        "G9": 0.12,
    }
    _write_kinetics_csv_plateau(csv_path, plateaus)

    result = analyze_kinetics_file(csv_path, plate_map_json=map_path, round_number=3)
    assert result["control_stats"]["anchor_mode"] == "substrate"
    assert result["qc_gates"]["q2_pass"] is False
    assert result["qc_gates"]["q2_endpoint_pass"] is True
    assert result["scoring_mode"] == "endpoint"
    assert result["qc_gates"]["q3_pass"] is True
    assert result["compounds"]["T1262"]["label"] == "confirmed_hit"
