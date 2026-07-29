#!/usr/bin/env python3
"""Resolve TargetMol compound IDs to robot source-plate locations.

The vendor library file at ./Compound_List.csv uses source plate IDs such as
PHD215176 plus row/column coordinates. The Zeon world exposes those three source
plates as wellplate_pcr_parts_1..3. This helper bridges those names and returns
the source wells to use in workflows/canvases.

Examples:
  python scripts/compound_plate_lookup.py T19860 T1262
  python scripts/compound_plate_lookup.py --target-csv data/screens/2/v2/compound_list.csv
  python scripts/compound_plate_lookup.py --default-tem1-test --json
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY_CSV = ROOT / "Compound_List.csv"

SOURCE_PLATE_TO_WORLD_OBJECT = {
    "PHD215176": "wellplate_pcr_parts_1",
    "PHD215177": "wellplate_pcr_parts_2",
    "PHD215178": "wellplate_pcr_parts_3",
}

# Current TEM-1 activity-screen set: known-active control plus 10 test compounds.
DEFAULT_TEM1_TEST_IDS = [
    "T19860",  # Clavulanic Acid; fixed positive control
    "T14979",
    "T6685",
    "T1262",
    "T14081",
    "T1631",
    "T13038",
    "T0814L",
    "T20022",
    "T0224",
    "T7733",
]


@dataclass(frozen=True)
class CompoundLocation:
    compound_id: str
    name: str
    source_plate: str
    source_row: str
    source_col: str
    source_well: str
    zeon_object: str
    concentration_mM: str
    solvent: str


def _norm_id(compound_id: str) -> str:
    return str(compound_id).strip().upper()


def _source_well(row: str, col: str) -> str:
    return f"{str(row).strip().upper()}{str(col).strip()}"


def load_compound_library(csv_path: Path = DEFAULT_LIBRARY_CSV) -> dict[str, dict[str, str]]:
    """Load Compound_List.csv keyed by normalized compound ID."""
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    out: dict[str, dict[str, str]] = {}
    for row in rows:
        compound_id = _norm_id(row.get("ID", ""))
        if not compound_id:
            continue
        out[compound_id] = {k: (v or "") for k, v in row.items()}
    return out


def resolve_compound_locations(
    compound_ids: Iterable[str],
    csv_path: Path = DEFAULT_LIBRARY_CSV,
) -> list[CompoundLocation]:
    """Resolve compound IDs to source plate, source well, and Zeon object name."""
    library = load_compound_library(csv_path)
    resolved: list[CompoundLocation] = []
    missing: list[str] = []

    for raw_id in compound_ids:
        compound_id = _norm_id(raw_id)
        row = library.get(compound_id)
        if row is None:
            missing.append(compound_id)
            continue

        source_plate = row.get("Plate", "").strip()
        source_row = row.get("Row", "").strip()
        source_col = row.get("Col", "").strip()
        zeon_object = SOURCE_PLATE_TO_WORLD_OBJECT.get(source_plate, source_plate)
        resolved.append(
            CompoundLocation(
                compound_id=compound_id,
                name=row.get("Name", "").strip(),
                source_plate=source_plate,
                source_row=source_row,
                source_col=source_col,
                source_well=_source_well(source_row, source_col),
                zeon_object=zeon_object,
                concentration_mM=row.get("Concentration（mM）", "").strip(),
                solvent=row.get("Solvent", "").strip(),
            )
        )

    if missing:
        raise KeyError(f"Compound IDs not found in {csv_path}: {', '.join(missing)}")
    return resolved


def load_target_ids(target_csv: Path) -> list[str]:
    """Load target compound IDs from a CSV with compound_id or ID column."""
    with target_csv.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    ids: list[str] = []
    for row in rows:
        compound_id = row.get("compound_id") or row.get("ID") or row.get("id")
        if compound_id:
            ids.append(_norm_id(compound_id))
    return ids


def to_workflow_defaults(locations: list[CompoundLocation]) -> dict[str, str]:
    """Return workflow/canvas-style defaults for positive + 10 test compounds.

    The first location is treated as the known-active positive control; remaining
    locations fill compound_1..compound_N.
    """
    if not locations:
        return {}

    defaults = {
        "positive_source_plate": locations[0].zeon_object,
        "positive_source_well": locations[0].source_well,
    }
    for i, loc in enumerate(locations[1:], start=1):
        defaults[f"compound_{i}_source_plate"] = loc.zeon_object
        defaults[f"compound_{i}_source_well"] = loc.source_well
    return defaults


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compound_ids", nargs="*", help="Compound IDs to resolve, e.g. T19860 T1262")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY_CSV, help="Path to Compound_List.csv")
    parser.add_argument("--target-csv", type=Path, help="CSV containing compound_id or ID column")
    parser.add_argument("--default-tem1-test", action="store_true", help="Resolve the current TEM-1 test compound set")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--workflow-defaults", action="store_true", help="Emit workflow/canvas default mapping")
    args = parser.parse_args()

    if args.target_csv:
        compound_ids = load_target_ids(args.target_csv)
    elif args.default_tem1_test or not args.compound_ids:
        compound_ids = DEFAULT_TEM1_TEST_IDS
    else:
        compound_ids = [_norm_id(x) for x in args.compound_ids]

    locations = resolve_compound_locations(compound_ids, args.library)

    if args.workflow_defaults:
        data = to_workflow_defaults(locations)
    else:
        data = [asdict(loc) for loc in locations]

    if args.json or args.workflow_defaults:
        print(json.dumps(data, indent=2))
    else:
        for loc in locations:
            print(f"{loc.compound_id}\t{loc.name}\t{loc.source_plate}\t{loc.source_well}\t{loc.zeon_object}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
