"""
Turn a dilution plan into an Opentrons Flex Python protocol.

The generated file is self-contained: deck constants at the top (edit them
to match the robot), the tube map as a comment block for whoever loads the
rack, and the planner's transfer list replayed in order. The camera takes a
"before" picture first and an "after" picture last.
"""

import math
from datetime import datetime

from dilution_planner import ASSAY, INTERMEDIATE, INTERMEDIATE_LABWARE, MEDIUM, STOCK, DilutionPlan
from plate_layout import PlateLayout

API_LEVEL = "2.30"

# Studio45: one Flex 8-channel 1000 µL pipette (left), used through a single nozzle
# so it can dose individual wells. Its minimum volume is 5 µL. Right mount is empty.
PIPETTE = ("flex_8channel_1000", "left")
PIPETTE_MIN_UL = 5.0
SMALL_TIP_MAX_UL = 50.0
LARGE_TIP_MAX_UL = 1000.0
TIPS_50 = "opentrons_flex_96_tiprack_50ul"
TIPS_1000 = "opentrons_flex_96_tiprack_1000ul"
STOCK_RACK = "opentrons_24_tuberack_nest_1.5ml_snapcap"
STOCK_TUBE_CAPACITY_UL = 1500.0
MEDIUM_RESERVOIR = "nest_1_reservoir_195ml"
MEDIUM_CAPACITY_UL = 195000.0

# Deck for single-nozzle (H1) work, found by simulation: the 7 spare nozzles hang
# toward the back, so the slot behind anything we touch must be empty or low, and
# row A can't be reached at all. Row A stays empty apart from the trash; C1/C3 stay
# empty because a tip rack there blocks D1/D3.
DECK = {
    "trash": "A3",
    STOCK: "B1",
    ASSAY: "B2",
    INTERMEDIATE: "B3",
    MEDIUM: "C2",
}
TIP_SLOTS = ["D1", "D2", "D3"]
TUBE_POSITIONS = [f"{row}{col}" for col in range(1, 7) for row in "ABCD"]
DEAD_VOLUME_UL = {STOCK: 20.0, MEDIUM: 1000.0}


def _comment_text(text: str) -> str:
    """
    Make user text safe inside a ``#`` comment or the module docstring.

    Line breaks of any kind would end the comment and start code, and a
    backslash or quote could end the docstring, so all of them are replaced.
    """
    cleaned = "".join(ch if ch.isprintable() else " " for ch in text)
    return cleaned.replace("\\", "/").replace('"', "'")


class ProtocolError(ValueError):
    """The layout or plan can't be turned into a Flex protocol."""


def tube_map(plan: DilutionPlan) -> dict[str, str]:
    """
    Stock tube position for every stock or solvent the plan draws from.

    Tubes are filled A1, B1, C1, D1, A2, ... in order of first use.

    Raises
    ------
    ProtocolError
        If more liquids are needed than the 24-tube rack holds.
    """
    mapping: dict[str, str] = {}
    for transfer in plan.transfers:
        if transfer.source_labware == STOCK and transfer.source_well not in mapping:
            if len(mapping) == len(TUBE_POSITIONS):
                needed = len({t.source_well for t in plan.transfers if t.source_labware == STOCK})
                raise ProtocolError(
                    f"The plan needs {needed} stock tubes but the rack holds {len(TUBE_POSITIONS)}."
                )
            mapping[transfer.source_well] = TUBE_POSITIONS[len(mapping)]
    return mapping


def _pipette_parts(volume_ul: float) -> tuple[str, int]:
    """Which tip size moves ``volume_ul`` and in how many equal parts."""
    if volume_ul <= SMALL_TIP_MAX_UL:
        return "small", 1
    return "large", math.ceil(volume_ul / LARGE_TIP_MAX_UL)


def _check_plan_fits(plan: DilutionPlan) -> None:
    """Refuse plans the planner couldn't place, e.g. when the intermediate plate is full."""
    if any("—" in (t.source_well, t.dest_well) for t in plan.transfers):
        reasons = sorted(set(plan.warnings)) or ["some wells have no source"]
        raise ProtocolError(f"The plan doesn't fit on the deck: {'; '.join(reasons)}.")


def _check_minimum(plan: DilutionPlan) -> None:
    """Refuse transfers the pipette can't do accurately."""
    too_small = [t for t in plan.transfers if t.volume_ul < PIPETTE_MIN_UL - 1e-9]
    if too_small:
        raise ProtocolError(
            f"{len(too_small)} transfer(s) are below the {PIPETTE_MIN_UL:g} µL minimum of the Flex "
            f"8-channel 1000 µL pipette (smallest: {min(t.volume_ul for t in too_small):.3g} µL). "
            f"Set Min. transfer to {PIPETTE_MIN_UL:g} µL or more and update the plan."
        )


def _tip_racks(plan: DilutionPlan) -> tuple[list[str], list[str]]:
    """Deck slots for the 50 µL and 1000 µL tip racks the plan needs."""
    tips = {"small": 0, "large": 0}
    for transfer in plan.transfers:
        pipette, parts = _pipette_parts(transfer.volume_ul)
        tips[pipette] += parts
    small_racks = math.ceil(tips["small"] / 96)
    large_racks = math.ceil(tips["large"] / 96)
    if small_racks + large_racks > len(TIP_SLOTS):
        raise ProtocolError(
            f"The plan needs {tips['small'] + tips['large']} tips "
            f"({small_racks + large_racks} racks); the deck has room for {len(TIP_SLOTS)} racks."
        )
    return TIP_SLOTS[:small_racks], TIP_SLOTS[small_racks:small_racks + large_racks]


def _liquid_volumes(plan: DilutionPlan, tubes: dict[str, str]) -> dict[str, float]:
    """Volume to load per stock liquid and for the medium, including dead volume."""
    used: dict[str, float] = {}
    for transfer in plan.transfers:
        if transfer.source_labware in (STOCK, MEDIUM):
            key = transfer.source_well if transfer.source_labware == STOCK else MEDIUM
            used[key] = used.get(key, 0.0) + transfer.volume_ul
    volumes: dict[str, float] = {}
    for liquid in tubes:
        volumes[liquid] = round(used[liquid] + DEAD_VOLUME_UL[STOCK], 1)
        if volumes[liquid] > STOCK_TUBE_CAPACITY_UL:
            raise ProtocolError(
                f"{liquid} needs {volumes[liquid]:g} µL but a stock tube holds {STOCK_TUBE_CAPACITY_UL:g} µL."
            )
    if MEDIUM in used:
        volumes[MEDIUM] = round(used[MEDIUM] + DEAD_VOLUME_UL[MEDIUM], 1)
        if volumes[MEDIUM] > MEDIUM_CAPACITY_UL:
            raise ProtocolError(f"The plan needs {volumes[MEDIUM]:g} µL of medium; the reservoir holds 195 mL.")
    return volumes


def generate_protocol(layout: PlateLayout, plan: DilutionPlan) -> str:
    """
    Build the Flex protocol source for ``plan``.

    Parameters
    ----------
    layout : PlateLayout
        Layout the plan was made for (plate name and labware).
    plan : DilutionPlan
        Plan from ``plan_dilutions``.

    Returns
    -------
    str
        Python source of an Opentrons protocol (apiLevel 2.30).

    Raises
    ------
    ProtocolError
        If the plate has no Opentrons labware or the plan doesn't fit the deck.
    """
    fmt = layout.plate_format
    if fmt.opentrons_load_name is None:
        raise ProtocolError(f"{fmt.name}: no Opentrons labware definition, can't run on the Flex.")
    _check_plan_fits(plan)
    _check_minimum(plan)
    tubes = tube_map(plan)
    small_slots, large_slots = _tip_racks(plan)
    volumes = _liquid_volumes(plan, tubes)

    tube_lines = "\n".join(
        f"#   {tube}: {_comment_text(liquid)} ({volumes[liquid]:g} µL)" for liquid, tube in tubes.items()
    ) or "#   (no stock tubes needed)"
    medium_line = (
        f"#   Medium reservoir {DECK[MEDIUM]}: {volumes[MEDIUM]:g} µL"
        if MEDIUM in volumes else "#   Medium reservoir: not needed"
    )
    transfer_lines = "".join(
        f"    ({t.phase!r}, {t.source_labware!r}, {t.source_well!r}, {t.dest_labware!r}, "
        f"{t.dest_well!r}, {round(t.volume_ul, 3)!r}),\n"
        for t in plan.transfers
    )
    transfers_literal = f"[\n{transfer_lines}]" if transfer_lines else "[]"

    return f'''"""
{_comment_text(layout.name)}: drug screen protocol for the Opentrons Flex.

Generated by drug-screen-platform on {datetime.now().isoformat(timespec="seconds")}.
The assay plate is expected to be pre-filled (cells in medium); this protocol
only adds the planned transfers.
"""

# Load the robot before starting:
#   Assay plate {fmt.opentrons_load_name} in {DECK[ASSAY]}
#   Intermediate plate {INTERMEDIATE_LABWARE} in {DECK[INTERMEDIATE]} (empty)
#   Stock tubes ({STOCK_RACK} in {DECK[STOCK]}):
{tube_lines}
{medium_line}
#   Tip racks: 50 µL in {small_slots or "-"}, 1000 µL in {large_slots or "-"} (full racks, no adapter)
#   Pipette: Flex 8-channel 1000 µL on the left mount, used through its front nozzle (H1)

from opentrons.protocol_api import SINGLE

requirements = {{"robotType": "Flex", "apiLevel": "{API_LEVEL}"}}
metadata = {{
    "protocolName": {layout.name!r},
    "author": "drug-screen-platform",
    "description": "Generated from a plate layout; before/after camera images.",
}}

# Deck: edit these to match the robot.
ASSAY_PLATE = ({fmt.opentrons_load_name!r}, {DECK[ASSAY]!r})
INTERMEDIATE_PLATE = ({INTERMEDIATE_LABWARE!r}, {DECK[INTERMEDIATE]!r})
STOCK_RACK = ({STOCK_RACK!r}, {DECK[STOCK]!r})
MEDIUM_RESERVOIR = ({MEDIUM_RESERVOIR!r}, {DECK[MEDIUM]!r})
TRASH_SLOT = {DECK["trash"]!r}
PIPETTE = ({PIPETTE[0]!r}, {PIPETTE[1]!r})
TIPS_50_SLOTS = {small_slots!r}
TIPS_1000_SLOTS = {large_slots!r}

STOCK_TUBES = {tubes!r}
LIQUID_VOLUMES = {volumes!r}

# (phase, source labware, source well, destination labware, destination well, volume µL)
TRANSFERS = {transfers_literal}


def run(protocol):
    protocol.capture_image(home_before=True, filename="before")

    protocol.load_trash_bin(TRASH_SLOT)
    labware = {{
        "assay": protocol.load_labware(*ASSAY_PLATE),
        "intermediate": protocol.load_labware(*INTERMEDIATE_PLATE),
        "stock": protocol.load_labware(*STOCK_RACK),
        "medium": protocol.load_labware(*MEDIUM_RESERVOIR),
    }}
    tips_50 = [protocol.load_labware({TIPS_50!r}, slot) for slot in TIPS_50_SLOTS]
    tips_1000 = [protocol.load_labware({TIPS_1000!r}, slot) for slot in TIPS_1000_SLOTS]
    pipette = protocol.load_instrument(*PIPETTE)
    # One nozzle of the 8-channel, so each transfer touches a single well. Tips are
    # taken row by row so spare tips can't cling to the empty nozzles.
    pipette.configure_nozzle_layout(style=SINGLE, start="H1")
    tips = {{
        "small": [well for rack in tips_50 for well in sum(rack.rows(), [])],
        "large": [well for rack in tips_1000 for well in sum(rack.rows(), [])],
    }}

    for liquid, tube in STOCK_TUBES.items():
        defined = protocol.define_liquid(name=liquid)
        labware["stock"].load_liquid(wells=[tube], volume=LIQUID_VOLUMES[liquid], liquid=defined)
    if "medium" in LIQUID_VOLUMES:
        defined = protocol.define_liquid(name="Medium")
        labware["medium"].load_liquid(wells=["A1"], volume=LIQUID_VOLUMES["medium"], liquid=defined)

    for phase, source_labware, source_well, dest_labware, dest_well, volume in TRANSFERS:
        if source_labware == "stock":
            source_well = STOCK_TUBES[source_well]
        elif source_labware == "medium":
            source_well = "A1"
        source = labware[source_labware][source_well]
        destination = labware[dest_labware][dest_well]
        if volume <= {SMALL_TIP_MAX_UL:g}:
            tip_size, parts = "small", 1
        else:
            tip_size, parts = "large", -(-volume // {LARGE_TIP_MAX_UL:g})
        part = volume / parts
        for _ in range(int(parts)):
            pipette.pick_up_tip(tips[tip_size].pop(0))
            pipette.aspirate(part, source)
            pipette.dispense(part, destination)
            pipette.drop_tip()

    protocol.capture_image(home_before=True, filename="after")
'''
