"""No-op. Shaker running-state tracking has been removed.

Kept as a harmless stub so existing workflow nodes that still call it don't break.
It records nothing and touches no hardware.
"""

from .modules import print_log


def wellplate_shaker_set_state(shaker=None, running: str = "no"):
    """Do nothing — state tracking disabled."""
    print_log(
        "wellplate_shaker_set_state: state tracking disabled (no-op)",
        runlog=True,
        runlog_type="event",
    )
    return {"success": True}
