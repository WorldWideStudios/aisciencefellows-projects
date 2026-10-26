"""Run a protocol through the Opentrons simulator."""

import io
from dataclasses import dataclass


@dataclass
class SimulationResult:
    """Outcome of ``simulate_protocol``."""

    ok: bool
    steps: int
    log: str
    error: str = ""


def simulate_protocol(source: str, filename: str = "protocol.py") -> SimulationResult:
    """
    Simulate an Opentrons protocol; never raises for protocol errors.

    Parameters
    ----------
    source : str
        Protocol Python source.
    filename : str, default="protocol.py"
        Name used in simulator messages.
    """
    from opentrons.simulate import format_runlog, simulate

    try:
        runlog, _ = simulate(io.StringIO(source), filename)
    except Exception as error:  # the simulator raises many types for bad protocols
        return SimulationResult(False, 0, "", f"{type(error).__name__}: {error}")
    return SimulationResult(True, len(runlog), format_runlog(runlog))
