#!/usr/bin/env python3
"""Generate plate_map.json from compound_list.json."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from pvjthomas.plates import generate_plate_map_from_file  # noqa: E402


def main() -> int:
    default_compound_list = REPO_ROOT / "data" / "screens" / "2" / "v2" / "compound_list.json"
    default_output = REPO_ROOT / "data" / "screens" / "2" / "v2" / "plate_map.json"
    default_copy = REPO_ROOT / "pvjthomas" / "output" / "plate_map.json"

    parser = argparse.ArgumentParser(
        description="Generate a 96-well plate map from compound_list.json."
    )
    parser.add_argument(
        "compound_list",
        nargs="?",
        type=Path,
        default=default_compound_list,
        help=f"Input compound list (default: {default_compound_list.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_output,
        help=f"Primary plate map output (default: {default_output.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--copy",
        type=Path,
        default=default_copy,
        help=f"Secondary copy under pvjthomas/output (default: {default_copy.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--vehicle-controls",
        type=int,
        help="Override vehicle control count on row A (default: 6)",
    )
    args = parser.parse_args()

    control_row = None
    if args.vehicle_controls is not None:
        control_row = {
            "vehicle": args.vehicle_controls,
            "no_tem1": 0,
            "positive": {"compound_id": "T19860", "count": 0, "concentration_uM": 50},
        }

    primary = generate_plate_map_from_file(
        args.compound_list,
        args.output,
        control_row=control_row,
    )
    copy = generate_plate_map_from_file(
        args.compound_list,
        args.copy,
        control_row=control_row,
    )

    print(primary)
    print(copy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
