"""
Microplate format definitions and well naming.

Well names follow the SBS convention: row letters (A, B, ... Z, AA, AB, ...)
followed by a 1-based column number, e.g. ``A1``, ``P24``, ``AF48``.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class PlateFormat:
    """
    Geometry and liquid-handling defaults for one plate type.

    Parameters
    ----------
    name : str
        Display name, e.g. ``"96-well"``.
    rows : int
        Number of rows.
    columns : int
        Number of columns.
    max_volume_ul : float
        Maximum well volume in µL.
    default_working_volume_ul : float
        Typical final assay volume per well in µL.
    opentrons_load_name : str or None
        Opentrons standard labware load name, or None if no standard
        definition exists.
    """

    name: str
    rows: int
    columns: int
    max_volume_ul: float
    default_working_volume_ul: float
    opentrons_load_name: Optional[str]

    @property
    def well_count(self) -> int:
        """Total number of wells."""
        return self.rows * self.columns


PLATE_FORMATS: dict[str, PlateFormat] = {
    "6-well": PlateFormat("6-well", 2, 3, 16800, 2000, "corning_6_wellplate_16.8ml_flat"),
    "12-well": PlateFormat("12-well", 3, 4, 6900, 1000, "corning_12_wellplate_6.9ml_flat"),
    "24-well": PlateFormat("24-well", 4, 6, 3400, 500, "corning_24_wellplate_3.4ml_flat"),
    "48-well": PlateFormat("48-well", 6, 8, 1600, 300, "corning_48_wellplate_1.6ml_flat"),
    "96-well": PlateFormat("96-well", 8, 12, 360, 100, "corning_96_wellplate_360ul_flat"),
    "384-well": PlateFormat("384-well", 16, 24, 112, 50, "corning_384_wellplate_112ul_flat"),
    "1536-well": PlateFormat("1536-well", 32, 48, 12.5, 8, None),
}

DEFAULT_FORMAT = "96-well"

_WELL_PATTERN = re.compile(r"^([A-Z]+)(\d+)$")


def row_label(row_index: int) -> str:
    """
    Convert a 0-based row index to its letter label.

    Parameters
    ----------
    row_index : int
        0-based row index.

    Returns
    -------
    str
        Row label (``0 -> "A"``, ``25 -> "Z"``, ``26 -> "AA"``).

    Examples
    --------
    >>> row_label(0), row_label(15), row_label(31)
    ('A', 'P', 'AF')
    """
    if row_index < 0:
        raise ValueError("row_index must be >= 0")
    label = ""
    index = row_index + 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label


def row_index_from_label(label: str) -> int:
    """
    Convert a row letter label back to its 0-based index.

    Parameters
    ----------
    label : str
        Row label such as ``"A"`` or ``"AF"``.

    Returns
    -------
    int
        0-based row index.
    """
    index = 0
    for character in label.upper():
        index = index * 26 + (ord(character) - 64)
    return index - 1


def well_name(row_index: int, column_index: int) -> str:
    """
    Build a well name from 0-based row and column indices.

    Parameters
    ----------
    row_index : int
        0-based row index.
    column_index : int
        0-based column index.

    Returns
    -------
    str
        Well name, e.g. ``well_name(1, 6) -> "B7"``.
    """
    return f"{row_label(row_index)}{column_index + 1}"


def parse_well(name: str) -> Tuple[int, int]:
    """
    Split a well name into 0-based row and column indices.

    Parameters
    ----------
    name : str
        Well name, e.g. ``"B7"``.

    Returns
    -------
    tuple of (int, int)
        ``(row_index, column_index)``.

    Raises
    ------
    ValueError
        If the name is not a valid well name.
    """
    match = _WELL_PATTERN.match(name.strip().upper())
    if not match:
        raise ValueError(f"Invalid well name: {name!r}")
    return row_index_from_label(match.group(1)), int(match.group(2)) - 1


def well_sort_key(name: str) -> Tuple[int, int]:
    """Sort key ordering wells row-wise (A1, A2, ..., B1, ...)."""
    return parse_well(name)


def flex_compatibility_note(plate_format: PlateFormat) -> Optional[str]:
    """
    Return a warning if the format can't run on the Opentrons Flex as-is.

    Parameters
    ----------
    plate_format : PlateFormat
        Plate format to check.

    Returns
    -------
    str or None
        Warning text, or None if a standard labware definition exists.
    """
    if plate_format.opentrons_load_name is None:
        return (
            f"{plate_format.name}: no standard Opentrons labware definition. "
            "Layout design works, but the Flex can't run this plate without custom labware."
        )
    return None
