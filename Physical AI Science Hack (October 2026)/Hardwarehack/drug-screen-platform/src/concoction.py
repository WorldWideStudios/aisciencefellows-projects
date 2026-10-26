"""
Concoctions on demand: per-column recipes drawn from the 12-trough reservoir.

The 8-channel draws from one trough with all 8 tips and dispenses into one
plate column, so a recipe applies to a whole column (wells A-H). Every draw
uses a fresh column of tips that goes to the trash afterwards, so no tip that
touched a well ever goes back into a trough. Draws up to 50 µL use the 50 µL
filter tips (A2); larger draws use the 1000 µL tips (A1). After the last
ingredient the same tip mixes the well.
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Optional

from medium_fill import (
    API_LEVEL, MIN_VOLUME_UL, PCR_PLATE, RESERVOIR, STOCK_PLATE, TIPS_1000, TIPS_50_FILTER, TRASH_SLOT,
)

COLUMNS = 12
TROUGHS = 12
CHANNELS = 8
WELL_CAPACITY_UL = 200.0      # Armadillo 96-well PCR plate
SMALL_TIP_MAX_UL = 50.0       # 50 µL filter tips
LARGE_TIP_MAX_UL = 1000.0     # 1000 µL tips
TIP_COLUMNS_PER_RACK = 12
MIX_REPETITIONS = 3


@dataclass
class Ingredient:
    """``volume_ul`` per well from reservoir ``trough`` (1-12)."""

    trough: int
    volume_ul: float


@dataclass
class Recipe:
    """What goes into every well of plate ``column`` (1-12), in order."""

    column: int
    ingredients: list[Ingredient] = field(default_factory=list)
    name: str = ""

    @property
    def total_ul(self) -> float:
        return sum(i.volume_ul for i in self.ingredients)


def _is_small(volume_ul: float) -> bool:
    return volume_ul <= SMALL_TIP_MAX_UL


def order_summary(recipes: Iterable[Recipe]) -> dict:
    """Tips needed per size, total draw per trough (8 channels) and total per column."""
    recipes = list(recipes)
    draws = defaultdict(float)
    for recipe in recipes:
        for ingredient in recipe.ingredients:
            draws[ingredient.trough] += CHANNELS * ingredient.volume_ul
    draws_list = [i for r in recipes for i in r.ingredients]
    return {
        "small_tips": sum(_is_small(i.volume_ul) for i in draws_list),
        "large_tips": sum(not _is_small(i.volume_ul) for i in draws_list),
        "trough_draw_ul": {t: round(v, 3) for t, v in sorted(draws.items())},
        "column_totals": {r.column: round(r.total_ul, 3) for r in recipes},
    }


def validate_order(
    recipes: Iterable[Recipe],
    used_columns: Iterable[int] = (),
    trough_volumes_ul: Optional[dict[int, float]] = None,
    small_tips_left: int = TIP_COLUMNS_PER_RACK,
    large_tips_left: int = TIP_COLUMNS_PER_RACK,
) -> list[str]:
    """Every reason the order can't be brewed (empty if it can)."""
    recipes = list(recipes)
    used = set(used_columns)
    problems: list[str] = []
    seen: set[int] = set()
    for recipe in recipes:
        column = recipe.column
        if not 1 <= column <= COLUMNS:
            problems.append(f"column {column} doesn't exist (1-{COLUMNS})")
            continue
        if column in seen:
            problems.append(f"column {column} is ordered twice")
        seen.add(column)
        if column in used:
            problems.append(f"column {column} already holds a concoction")
        if not recipe.ingredients:
            problems.append(f"column {column} has no ingredients")
        for ingredient in recipe.ingredients:
            if not 1 <= ingredient.trough <= TROUGHS:
                problems.append(f"column {column}: trough {ingredient.trough} doesn't exist (1-{TROUGHS})")
            if not math.isfinite(ingredient.volume_ul):
                problems.append(f"column {column}: {ingredient.volume_ul:g} µL from trough {ingredient.trough} "
                                "is not a volume")
            elif ingredient.volume_ul < MIN_VOLUME_UL:
                problems.append(f"column {column}: {ingredient.volume_ul:g} µL from trough {ingredient.trough} "
                                f"is below the {MIN_VOLUME_UL:g} µL minimum")
        if recipe.total_ul > WELL_CAPACITY_UL:
            problems.append(f"column {column}: {recipe.total_ul:g} µL is more than a well holds "
                            f"({WELL_CAPACITY_UL:g} µL)")
    summary = order_summary(recipes)
    if summary["small_tips"] > small_tips_left:
        problems.append(f"needs {summary['small_tips']} columns of 50 µL tips but {small_tips_left} are left")
    if summary["large_tips"] > large_tips_left:
        problems.append(f"needs {summary['large_tips']} columns of 1000 µL tips but {large_tips_left} are left")
    for trough, needed in summary["trough_draw_ul"].items():
        available = (trough_volumes_ul or {}).get(trough)
        if available is not None and needed > available:
            problems.append(f"trough {trough} needs {needed:g} µL but holds {available:g} µL")
    return problems


def protocol_source(recipes: Iterable[Recipe], small_tip_start: int = 1, large_tip_start: int = 1) -> str:
    """
    Opentrons protocol that brews ``recipes``, taking tip columns from the given starts.

    Raises
    ------
    ValueError
        If the order breaks a rule (see ``validate_order``).
    """
    recipes = list(recipes)
    problems = validate_order(recipes, small_tips_left=TIP_COLUMNS_PER_RACK - small_tip_start + 1,
                              large_tips_left=TIP_COLUMNS_PER_RACK - large_tip_start + 1)
    if problems:
        raise ValueError("; ".join(problems))
    # Plain data only: names travel as repr() literals, never as code or comments.
    order = [(r.column, r.name, [(i.trough, float(i.volume_ul)) for i in r.ingredients]) for r in recipes]
    return f'''"""
Concoctions on demand: {len(recipes)} column(s) from the 12-trough reservoir into the Armadillo plate.

Generated by drug-screen-platform. Deck: 1000 µL tips A1, 50 µL filter tips A2, 12-trough
reservoir B1, stock plate B2, Armadillo 96-well PCR plate on a deep-well riser B3 (needs the
calibrated offset), trash A3. A fresh tip column for every draw; the last tip mixes the well.
"""

requirements = {{"robotType": "Flex", "apiLevel": "{API_LEVEL}"}}
metadata = {{"protocolName": "Concoctions on demand", "author": "drug-screen-platform"}}

SMALL_TIP_MAX_UL = {SMALL_TIP_MAX_UL!r}
MIX_REPETITIONS = {MIX_REPETITIONS!r}
SMALL_TIP_START = {small_tip_start!r}
LARGE_TIP_START = {large_tip_start!r}

# (plate column, recipe name, [(trough, µL per well), ...]) in brewing order
ORDER = {order!r}


def run(protocol):
    protocol.load_trash_bin({TRASH_SLOT!r})
    large_tips = protocol.load_labware(*{TIPS_1000!r})
    small_tips = protocol.load_labware(*{TIPS_50_FILTER!r})
    reservoir = protocol.load_labware(*{RESERVOIR!r})
    protocol.load_labware(*{STOCK_PLATE!r})
    plate = protocol.load_labware(*{PCR_PLATE!r})
    pipette = protocol.load_instrument("flex_8channel_1000", "left")

    next_tip = {{"small": SMALL_TIP_START, "large": LARGE_TIP_START}}
    for column, name, ingredients in ORDER:
        total = sum(volume for _, volume in ingredients)
        for index, (trough, volume) in enumerate(ingredients):
            size = "small" if volume <= SMALL_TIP_MAX_UL else "large"
            rack = small_tips if size == "small" else large_tips
            pipette.pick_up_tip(rack[f"A{{next_tip[size]}}"])
            next_tip[size] += 1
            pipette.aspirate(volume, reservoir[f"A{{trough}}"])
            pipette.dispense(volume, plate[f"A{{column}}"])
            if index == len(ingredients) - 1:
                tip_max = SMALL_TIP_MAX_UL if size == "small" else 1000.0
                pipette.mix(MIX_REPETITIONS, min(max(total / 2, 5.0), tip_max), plate[f"A{{column}}"])
            pipette.drop_tip()
    protocol.home()
'''
