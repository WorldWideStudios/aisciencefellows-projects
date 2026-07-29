"""Put back whichever pipette is actually in the hand.

The CFPS workflow swaps pipettes mid-run based on transfer volume, so the one
held at the end isn't necessarily the one the workflow started with. This reads
``in_hand`` from live_state and places that one, instead of trusting a fixed
workflow input.
"""

from protocol_schema import SkillObject
from utils import find_pipettes, pipette_in_hand, pipette_name

from epipette_place.robotic_code import epipette_place

from .modules import print_log


def place_current_pipette(pipette: SkillObject):
    """Place the pipette that is currently in hand.

    Args:
        pipette: Fallback — placed only if live_state says nothing is held
            (e.g. a fresh world where no grab has run yet).
    """
    print_log(runlog=True, runlog_type="step_start")

    held = pipette_in_hand(find_pipettes())
    if held is None:
        held = pipette
        print_log(f"place_current_pipette: nothing marked in_hand; falling back to {pipette_name(pipette)}")

    print_log(f"▶ Returning {pipette_name(held)} to its stand", runlog=True, runlog_type="event")
    epipette_place(pipette=held)
    return {"success": True, "placed": pipette_name(held)}
