"""
Supporting modules for epipette grey tip attachment operations.
"""

from execution.execution_functions import *


def compute_tip_position_from_index(tip_index, tipbox_xyz, row_offsets, col_offsets, tip_height):
    """Compute tip position for a 96-tip rack (8 rows A-H x 12 cols 1-12).

    Traversal: tip_index=0 -> row 0 (A), col 0 (1); increments rightward across cols first,
    then upward through rows.
        up_index    = tip_index // 12   # row 0..7 -> A..H
        right_index = tip_index % 12    # col 0..11 -> 1..12

    Args:
        tip_index:   Tip index 0-95.
        tipbox_xyz:  [x, y, z] world pose of the tipbox.
        row_offsets: List of 8 scalar dx per row (A-H), relative to tipbox_xyz x.
        col_offsets: List of 12 scalar dy per column (1-12), relative to tipbox_xyz y.
        tip_height:  Absolute z height (world frame) of the tip tops.

    Returns:
        Tuple of (tip_position, up_index, right_index).
    """
    tip_index = int(tip_index)
    up_index = tip_index // 12
    right_index = tip_index % 12

    tip_position = [
        tipbox_xyz[0] + row_offsets[up_index],
        tipbox_xyz[1] + col_offsets[right_index],
        tip_height,
    ]

    return tip_position, up_index, right_index
