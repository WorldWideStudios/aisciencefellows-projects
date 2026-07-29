"""Tests for kinetic read scheduling."""

from __future__ import annotations

import pytest

from analysis.read_schedule import (
    DEFAULT_NITROCEFIN_TEMPERATURE_C,
    KineticReadSchedule,
    ReadTimepoint,
    build_read_schedule,
    nitrocefin_tem1_default_schedule,
    platereader_kinetic_test_schedule,
    schedule_to_dict,
)


def test_uniform_30s_grid_to_10_min() -> None:
    schedule = build_read_schedule(second_read_s=30, interval_s=30, total_time_s=600)
    points = schedule.read_points
    assert [p.time_s for p in points] == [float(i * 30) for i in range(21)]
    assert points[0].read_label == "initial"
    assert points[1].read_label == "t030s"
    assert points[0].wait_s == 0.0
    assert points[1].wait_s == 30.0
    assert schedule.temperature_c == DEFAULT_NITROCEFIN_TEMPERATURE_C
    assert schedule.equilibration_s == 120.0
    assert schedule.total_plate_time_s == 720.0
    assert schedule.slope_window_start_s == 180.0
    assert schedule.slope_window_end_s == 480.0


def test_delayed_second_read_then_interval() -> None:
    schedule = build_read_schedule(second_read_s=60, interval_s=30, total_time_s=600)
    points = schedule.read_points
    assert [p.time_s for p in points[:4]] == [0.0, 60.0, 90.0, 120.0]
    assert points[1].wait_s == 60.0
    assert points[2].wait_s == 30.0


def test_appends_total_when_not_on_grid() -> None:
    schedule = build_read_schedule(second_read_s=30, interval_s=30, total_time_s=605)
    points = schedule.read_points
    assert points[-2].time_s == 600.0
    assert points[-1].time_s == 605.0
    assert points[-1].wait_s == 5.0


def test_single_read_when_total_equals_initial() -> None:
    schedule = build_read_schedule(second_read_s=0, interval_s=30, total_time_s=0)
    assert len(schedule.read_points) == 1
    assert schedule.read_points[0].time_s == 0.0


def test_rejects_invalid_interval() -> None:
    with pytest.raises(ValueError, match="interval_s"):
        build_read_schedule(second_read_s=30, interval_s=0, total_time_s=600)


def test_rejects_second_before_initial() -> None:
    with pytest.raises(ValueError, match="second_read_s"):
        build_read_schedule(second_read_s=10, interval_s=30, total_time_s=600, initial_read_s=20)


def test_non_zero_initial_read() -> None:
    schedule = build_read_schedule(
        second_read_s=45,
        interval_s=15,
        total_time_s=75,
        initial_read_s=15,
    )
    points = schedule.read_points
    assert [p.time_s for p in points] == [15.0, 45.0, 60.0, 75.0]
    assert points[0].wait_s == 0.0
    assert points[1].wait_s == 30.0


def test_ambient_mode_disables_incubator() -> None:
    schedule = build_read_schedule(
        second_read_s=30,
        interval_s=30,
        total_time_s=300,
        temperature_c=None,
        equilibration_s=0,
    )
    assert not schedule.incubator_required
    assert schedule.total_plate_time_s == 300.0
    assert any("Incubation off" in note for note in schedule.gen5_protocol_notes())


def test_rejects_out_of_range_temperature() -> None:
    with pytest.raises(ValueError, match="temperature_c"):
        build_read_schedule(second_read_s=30, interval_s=30, total_time_s=600, temperature_c=55)


def test_absolute_time_includes_equilibration() -> None:
    schedule = build_read_schedule(
        second_read_s=30,
        interval_s=30,
        total_time_s=60,
        equilibration_s=90,
    )
    assert schedule.read_points[1].absolute_time_s(schedule.equilibration_s) == 120.0


def test_gen5_notes_mention_temperature_and_equilibration() -> None:
    schedule = build_read_schedule(second_read_s=30, interval_s=30, total_time_s=600)
    notes = "\n".join(schedule.gen5_protocol_notes())
    assert "25" in notes
    assert "120" in notes
    assert "180" in notes and "480" in notes


def test_platereader_kinetic_test_schedule_3_min() -> None:
    """Plate reader unit-test workflow: 25 C, 30 s interval, 3 min window."""
    schedule = platereader_kinetic_test_schedule()
    assert schedule.temperature_c == 25.0
    assert schedule.equilibration_s == 30.0
    assert schedule.kinetic_duration_s == 180.0
    assert schedule.total_plate_time_s == 210.0
    assert [p.time_s for p in schedule.read_points] == [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
    assert len(schedule.read_points) == 7
    assert schedule.slope_window_start_s == 60.0
    assert schedule.slope_window_end_s == 180.0


def test_nitrocefin_tem1_default_schedule() -> None:
    schedule = nitrocefin_tem1_default_schedule()
    assert schedule.temperature_c == 25.0
    assert schedule.equilibration_s == 120.0
    assert schedule.slope_window_start_s == 180.0
    assert schedule.slope_window_end_s == 480.0
    assert len(schedule.read_points) == 21
    assert schedule.total_plate_time_s == 720.0


def test_schedule_to_dict_round_trip_fields() -> None:
    schedule = nitrocefin_tem1_default_schedule()
    payload = schedule_to_dict(schedule)
    assert payload["temperature_c"] == 25.0
    assert len(payload["read_points"]) == 21
    assert payload["read_points"][0]["read_label"] == "initial"


def test_read_timepoint_is_frozen() -> None:
    point = ReadTimepoint(index=0, time_s=0.0, wait_s=0.0, read_label="initial")
    with pytest.raises(Exception):
        point.time_s = 1.0  # type: ignore[misc]


def test_schedule_is_frozen() -> None:
    schedule = build_read_schedule(second_read_s=30, interval_s=30, total_time_s=60)
    assert isinstance(schedule, KineticReadSchedule)
    with pytest.raises(Exception):
        schedule.equilibration_s = 0.0  # type: ignore[misc]
