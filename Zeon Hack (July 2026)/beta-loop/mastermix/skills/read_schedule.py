"""Plate-reader kinetic read timing helpers."""

from __future__ import annotations

from dataclasses import dataclass

# BioTek ELx808IU 4-zone incubator: ambient +6 to 50 °C; operate room 18–40 °C.
ELX808_MIN_INCUBATION_C = 18.0
ELX808_MAX_INCUBATION_C = 50.0

# Literature nitrocefin TEM-1 assays commonly run at 25 °C.
DEFAULT_NITROCEFIN_TEMPERATURE_C = 25.0


@dataclass(frozen=True)
class ReadTimepoint:
    """One scheduled A490 read relative to kinetic t0 (first read after equilibration)."""

    index: int
    time_s: float
    wait_s: float
    read_label: str

    def absolute_time_s(self, equilibration_s: float) -> float:
        """Seconds from plate close / incubator start to this read."""
        return equilibration_s + self.time_s


@dataclass(frozen=True)
class KineticReadSchedule:
    """Full plate-reader kinetic plan including temperature and analysis window."""

    temperature_c: float | None
    equilibration_s: float
    slope_window_start_s: float | None
    slope_window_end_s: float | None
    read_points: tuple[ReadTimepoint, ...]

    @property
    def incubator_required(self) -> bool:
        return self.temperature_c is not None

    @property
    def kinetic_duration_s(self) -> float:
        if not self.read_points:
            return 0.0
        return self.read_points[-1].time_s

    @property
    def total_plate_time_s(self) -> float:
        return self.equilibration_s + self.kinetic_duration_s

    def gen5_protocol_notes(self) -> list[str]:
        """Human/AutoGUI checklist for programming Gen5 on the bench."""
        notes = [
            "Set read mode to kinetic (not endpoint-only).",
            f"Schedule {len(self.read_points)} reads: initial, then every "
            f"{self._interval_s():g}s until {self.kinetic_duration_s:g}s kinetic time.",
        ]
        if self.incubator_required:
            notes.insert(
                0,
                f"Enable incubation at {self.temperature_c:g} °C; Gen5 waits for setpoint "
                f"before the first read when the IU incubator is installed.",
            )
            if self.equilibration_s > 0:
                notes.append(
                    f"Hold at {self.temperature_c:g} °C for {self.equilibration_s:g}s "
                    "after lid close before the first kinetic read (cold-start warm-up)."
                )
        else:
            notes.insert(0, "Incubation off (ambient); cold nitrocefin wells will warm unevenly.")
        if self.slope_window_start_s is not None and self.slope_window_end_s is not None:
            notes.append(
                "Score slope on kinetic times "
                f"{self.slope_window_start_s:g}–{self.slope_window_end_s:g}s "
                f"({self.slope_window_start_s + self.equilibration_s:g}–"
                f"{self.slope_window_end_s + self.equilibration_s:g}s from plate close)."
            )
        notes.append(
            "Robot control: temperature is not set by platereader_measure today — "
            "bake these values into the saved Gen5 protocol or add AutoGUI steps."
        )
        return notes

    def _interval_s(self) -> float:
        if len(self.read_points) < 2:
            return 0.0
        return self.read_points[2].time_s - self.read_points[1].time_s if len(self.read_points) > 2 else (
            self.read_points[1].time_s - self.read_points[0].time_s
        )


def build_read_schedule(
    second_read_s: float,
    interval_s: float,
    total_time_s: float,
    *,
    initial_read_s: float = 0.0,
    temperature_c: float | None = DEFAULT_NITROCEFIN_TEMPERATURE_C,
    equilibration_s: float = 120.0,
    slope_window_start_s: float | None = None,
    slope_window_end_s: float | None = None,
) -> KineticReadSchedule:
    """Build a kinetic read plan with optional incubator setpoint and warm-up.

    Read times (``ReadTimepoint.time_s``) are relative to **kinetic t0** — the
    first read **after** ``equilibration_s`` at ``temperature_c``. Workflow order:

    1. Load plate, close lid, set incubator to ``temperature_c`` (Gen5 / AutoGUI).
    2. Wait ``equilibration_s`` for thermal equilibration (critical for ice-cold
       nitrocefin dispenses).
    3. First read at ``initial_read_s`` (default 0 = immediately after equilibration).
    4. Second read at ``second_read_s``, then ``interval_s`` steps until
       ``total_time_s``.

    Args:
        second_read_s: Kinetic time of the second read (seconds after kinetic t0).
        interval_s: Seconds between reads after the second read.
        total_time_s: End of kinetic window (seconds after kinetic t0).
        initial_read_s: Kinetic time of the first read (default 0).
        temperature_c: Incubator setpoint in °C, or ``None`` for ambient/no control.
            ELx808IU supports ~18–50 °C when the 4-zone incubator is installed.
        equilibration_s: Seconds at setpoint after lid close before kinetic t0.
        slope_window_start_s: Start of slope-fit window (kinetic time); defaults to
            180 s when ``total_time_s`` >= 600, else 60 s.
        slope_window_end_s: End of slope-fit window (kinetic time); defaults to
            ``total_time_s - 120`` when ``total_time_s`` >= 600, else ``total_time_s``.

    Returns:
        :class:`KineticReadSchedule` with read points and temperature metadata.

    Examples:
        >>> s = build_read_schedule(30, 30, 600)
        >>> s.temperature_c
        25.0
        >>> [p.time_s for p in s.read_points[:3]]
        [0.0, 30.0, 60.0]
        >>> s.total_plate_time_s
        720.0
    """
    if interval_s <= 0:
        raise ValueError(f"interval_s must be > 0 (got {interval_s})")
    if total_time_s < initial_read_s:
        raise ValueError(
            f"total_time_s must be >= initial_read_s ({total_time_s} < {initial_read_s})"
        )
    if second_read_s < initial_read_s:
        raise ValueError(
            f"second_read_s must be >= initial_read_s ({second_read_s} < {initial_read_s})"
        )
    if equilibration_s < 0:
        raise ValueError(f"equilibration_s must be >= 0 (got {equilibration_s})")
    if temperature_c is not None and not (
        ELX808_MIN_INCUBATION_C <= temperature_c <= ELX808_MAX_INCUBATION_C
    ):
        raise ValueError(
            f"temperature_c must be between {ELX808_MIN_INCUBATION_C} and "
            f"{ELX808_MAX_INCUBATION_C} (got {temperature_c})"
        )

    if slope_window_start_s is None or slope_window_end_s is None:
        default_start, default_end = _default_slope_window(total_time_s)
        if slope_window_start_s is None:
            slope_window_start_s = default_start
        if slope_window_end_s is None:
            slope_window_end_s = default_end

    if slope_window_start_s < 0 or slope_window_end_s < slope_window_start_s:
        raise ValueError("invalid slope window")
    if slope_window_end_s > total_time_s + 1e-9:
        raise ValueError(
            f"slope_window_end_s must be <= total_time_s ({slope_window_end_s} > {total_time_s})"
        )

    times: list[float] = [float(initial_read_s)]
    if second_read_s > initial_read_s + 1e-9:
        times.append(float(second_read_s))

    t = times[-1]
    while True:
        next_t = t + interval_s
        if next_t > total_time_s + 1e-9:
            break
        times.append(next_t)
        t = next_t

    if abs(times[-1] - total_time_s) > 1e-9:
        times.append(float(total_time_s))

    points: list[ReadTimepoint] = []
    prev = 0.0
    for index, time_s in enumerate(times):
        wait_s = 0.0 if index == 0 else time_s - prev
        points.append(
            ReadTimepoint(
                index=index,
                time_s=time_s,
                wait_s=wait_s,
                read_label=_read_label(index, time_s),
            )
        )
        prev = time_s

    return KineticReadSchedule(
        temperature_c=temperature_c,
        equilibration_s=float(equilibration_s),
        slope_window_start_s=float(slope_window_start_s),
        slope_window_end_s=float(slope_window_end_s),
        read_points=tuple(points),
    )


def _default_slope_window(total_time_s: float) -> tuple[float, float]:
    if total_time_s >= 600:
        return 180.0, total_time_s - 120.0
    if total_time_s >= 180:
        return 60.0, total_time_s
    return 0.0, total_time_s


def nitrocefin_tem1_default_schedule() -> KineticReadSchedule:
    """Validated nitrocefin TEM-1 screen: 25 °C, 2 min equilibration, 30 s × 10 min."""
    return build_read_schedule(
        second_read_s=30.0,
        interval_s=30.0,
        total_time_s=600.0,
        temperature_c=25.0,
        equilibration_s=120.0,
        slope_window_start_s=180.0,
        slope_window_end_s=480.0,
    )


def schedule_to_dict(schedule: KineticReadSchedule) -> dict:
    """Serialize a schedule for run logs and analysis metadata."""
    return {
        "temperature_c": schedule.temperature_c,
        "equilibration_s": schedule.equilibration_s,
        "slope_window_start_s": schedule.slope_window_start_s,
        "slope_window_end_s": schedule.slope_window_end_s,
        "kinetic_duration_s": schedule.kinetic_duration_s,
        "total_plate_time_s": schedule.total_plate_time_s,
        "read_points": [
            {
                "index": p.index,
                "time_s": p.time_s,
                "wait_s": p.wait_s,
                "read_label": p.read_label,
                "absolute_time_s": p.absolute_time_s(schedule.equilibration_s),
            }
            for p in schedule.read_points
        ],
        "gen5_protocol_notes": schedule.gen5_protocol_notes(),
    }


def _read_label(index: int, time_s: float) -> str:
    if index == 0:
        return "initial"
    seconds = int(round(time_s))
    return f"t{seconds:03d}s"
