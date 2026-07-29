from .modules import is_sim_mode, pause_aware_sleep, print_log


def wait_minutes(minutes: float = 10.0, label: str = "Timed wait"):
    """Wait for a configurable number of minutes.

    Args:
        minutes: Duration to wait, in minutes. Must be zero or positive.
        label: Human-readable reason shown in the run log.
    """
    print_log(runlog=True, runlog_type="step_start")
    minutes = float(minutes)
    if minutes < 0:
        raise ValueError(f"wait_minutes: minutes must be >= 0 (got {minutes})")

    seconds = minutes * 60.0
    print_log(f"{label}: waiting {minutes:g} minute(s)", runlog=True, runlog_type="event")

    if is_sim_mode():
        dwell = min(seconds, 2.0)
        print_log(f"[SIM] shortening {seconds:g} second wait to {dwell:g} second(s)")
        pause_aware_sleep(dwell)
    else:
        pause_aware_sleep(seconds)

    print_log(f"{label}: wait complete", runlog=True, runlog_type="event")
    return {"success": True, "minutes": minutes}
