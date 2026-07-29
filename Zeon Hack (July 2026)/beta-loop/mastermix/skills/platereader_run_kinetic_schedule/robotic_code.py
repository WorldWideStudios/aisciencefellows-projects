"""Execute the nitrocefin TEM-1 kinetic A490 read schedule on the plate reader."""

from __future__ import annotations

import json

from platereader_measure.robotic_code import platereader_measure
from read_schedule import build_read_schedule, schedule_to_dict

from .modules import ExecutionInfoContext, is_sim_mode, pause_aware_sleep, print_log, project_data_dir


def _sim_wait(seconds: float) -> None:
    dwell = min(float(seconds), 2.0)
    print_log(f"[SIM] shortening {seconds:g}s wait to {dwell:g}s")
    pause_aware_sleep(dwell)


def _wait_seconds(seconds: float, label: str) -> None:
    if seconds <= 0:
        return
    print_log(f"{label}: waiting {seconds:g}s", runlog=True, runlog_type="event")
    if is_sim_mode():
        _sim_wait(seconds)
    else:
        pause_aware_sleep(seconds)


def platereader_run_kinetic_schedule(
    second_read_s: float = 30.0,
    interval_s: float = 30.0,
    total_time_s: float = 600.0,
    temperature_c: float = 25.0,
    equilibration_s: float = 120.0,
    slope_window_start_s: float = 180.0,
    slope_window_end_s: float = 480.0,
    initial_read_s: float = 0.0,
):
    """Run the configured nitrocefin kinetic schedule on a loaded, closed plate reader.

    Default parameters match the validated TEM-1 nitrocefin table: 25 °C incubator,
    120 s equilibration after lid close, A490 every 30 s for 10 min, slope window
    180–480 s. Temperature setpoint is recorded in the schedule JSON for Gen5;
    ``platereader_measure`` does not yet drive the incubator via AutoGUI.

    Args:
        second_read_s: Second read time (seconds after kinetic t0).
        interval_s: Interval between subsequent reads.
        total_time_s: End of kinetic window (seconds after kinetic t0).
        temperature_c: Incubator setpoint (°C) to record and program in Gen5.
        equilibration_s: Warm-up at setpoint after lid close, before first read.
        slope_window_start_s: Analysis slope-fit start (kinetic time, seconds).
        slope_window_end_s: Analysis slope-fit end (kinetic time, seconds).
        initial_read_s: First read time after equilibration (default 0).
    """
    print_log(runlog=True, runlog_type="step_start")

    schedule = build_read_schedule(
        second_read_s=second_read_s,
        interval_s=interval_s,
        total_time_s=total_time_s,
        initial_read_s=initial_read_s,
        temperature_c=temperature_c,
        equilibration_s=equilibration_s,
        slope_window_start_s=slope_window_start_s,
        slope_window_end_s=slope_window_end_s,
    )

    run_id = ExecutionInfoContext.get().execution_id or "no_execution"
    out_dir = project_data_dir(f"platereader/{run_id}", create=True)
    schedule_path = out_dir / f"{run_id}_kinetic_schedule.json"
    schedule_path.write_text(json.dumps(schedule_to_dict(schedule), indent=2))

    print_log(
        f"Kinetic schedule: {len(schedule.read_points)} reads, "
        f"{schedule.temperature_c} °C, {schedule.equilibration_s}s equilibration, "
        f"slope {schedule.slope_window_start_s}–{schedule.slope_window_end_s}s",
        runlog=True,
    )
    for note in schedule.gen5_protocol_notes():
        print_log(f"  Gen5: {note}", runlog=True)

    if schedule.incubator_required:
        print_log(
            f"Incubator setpoint {schedule.temperature_c} °C — ensure Gen5 protocol matches",
            runlog=True,
            runlog_type="event",
        )

    _wait_seconds(
        schedule.equilibration_s,
        f"Plate reader equilibration at {schedule.temperature_c} °C",
    )

    read_results = []
    for point in schedule.read_points:
        _wait_seconds(point.wait_s, f"Wait before {point.read_label}")
        result = platereader_measure(read_label=point.read_label)
        read_results.append(
            {
                "read_label": point.read_label,
                "kinetic_time_s": point.time_s,
                "absolute_time_s": point.absolute_time_s(schedule.equilibration_s),
                "export_path": result.get("export_path"),
            }
        )
        print_log(
            f"Completed read {point.index + 1}/{len(schedule.read_points)} "
            f"({point.read_label}, kinetic t={point.time_s:g}s)",
            runlog=True,
            runlog_type="event",
        )

    print_log(
        f"platereader_run_kinetic_schedule completed — {len(read_results)} reads, "
        f"schedule saved to {schedule_path}",
        runlog=True,
    )
    return {
        "success": True,
        "schedule_path": str(schedule_path),
        "read_count": len(read_results),
        "reads": read_results,
        "temperature_c": schedule.temperature_c,
        "equilibration_s": schedule.equilibration_s,
        "slope_window_start_s": schedule.slope_window_start_s,
        "slope_window_end_s": schedule.slope_window_end_s,
    }
