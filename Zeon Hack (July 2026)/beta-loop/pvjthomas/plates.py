"""Generate 96-well plate maps from compound_list.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

ROWS = list("ABCDEFGH")
COLS = 12

LayoutMode = Literal["compact", "spaced_interior", "column_strip"]

# ---------------------------------------------------------------------------
# Layout policy (well placement rules — independent of PNG coloring in plate_viz)
# ---------------------------------------------------------------------------
# Interior = rows B–G (index 1–6), columns 2–11 (index 1–10).
# Edge rows/cols (A, H, 1, 12) must stay empty for spaced_interior & column_strip.

INTERIOR_ROW_START = 1
INTERIOR_ROW_END = 6
INTERIOR_COL_START = 1
INTERIOR_COL_END = 10

EDGE_ROWS = frozenset({0, 7})  # A, H
EDGE_COLS = frozenset({0, 11})  # 1, 12

# Triplicate sample rows — every other interior row (B, D, F).
STRIP_SAMPLE_ROWS = (1, 3, 5)

# Spaced triplicate control columns (3, 7, 11); one group per row band.
SPACED_CONTROL_COLS = (2, 6, 10)

# Every-other interior columns — cols 2, 4, 6, 8, 10 (band 1 on B/D/F).
SPACED_SAMPLE_COLS = (1, 3, 5, 7, 9)

# Band 2 on C/E/G — cols 5, 9 (disjoint from band 1, avoids control cols on B/D/F).
COLUMN_STRIP_BAND2_COLS = (4, 8)

# Band 3 on C/E/G — cols 3, 7, 11 (checkerboard slots between band-2 samples).
COLUMN_STRIP_BAND3_COLS = SPACED_CONTROL_COLS

# Col-11 control triplicates sit one row lower (C/E/G @ 11 vs B/D/F @ 3/7).
COLUMN_STRIP_COL11_ROW_OFFSET = 1

# column_strip controls on B/D/F @ 3/7 and C/E/G @ 11; samples use C/E/G at 5/9 and 3/7.
COLUMN_STRIP_CONTROL_ROWS = (2, 4, 6)

# spaced_interior: controls share STRIP_SAMPLE_ROWS at SPACED_CONTROL_COLS only.
SPACED_INTERIOR_CONTROL_ROWS = STRIP_SAMPLE_ROWS

INTERIOR_LAYOUT_MODES = frozenset({"spaced_interior", "column_strip"})

LAYOUT_RULES: dict[str, dict[str, Any]] = {
    "compact": {
        "interior_only": False,
        "description": "Packed layout; row A controls, samples from row B.",
    },
    "spaced_interior": {
        "interior_only": True,
        "max_sample_separation": True,
        "sample_pattern": "checkerboard",
        "control_rows": "B,D,F",
        "control_cols": "3,7,11",
    },
    "column_strip": {
        "interior_only": True,
        "max_x_separation": True,
        "replicate_axis": "column",
        "sample_cols_band1": "2,4,6,8,10 on B,D,F",
        "sample_cols_band2": "5,9 on C,E,G",
        "sample_cols_band3": "3,7 on C,E,G",
        "control_rows": "B,D,F @ 3/7; C,E,G @ 11",
        "control_cols": "3,7,11",
    },
}

# Back-compat aliases
COLUMN_STRIP_SAMPLE_ROWS = STRIP_SAMPLE_ROWS
SPACED_CONTROL_ROWS = SPACED_INTERIOR_CONTROL_ROWS

DEFAULT_CONTROL_ROW: dict[str, Any] = {
    "vehicle": 3,
    "no_tem1": 3,
    "positive": {"compound_id": "T19860", "count": 3, "concentration_uM": 50},
}

# Run 3+: vehicle controls removed; no-TEM-1 and positive stay on D/F rows @ cols 3/7/11.
R3_CONTROL_ROW: dict[str, Any] = {
    "vehicle": 0,
    "no_tem1": 3,
    "positive": {"compound_id": "T19860", "count": 3, "concentration_uM": 50},
}

# Eight-compound column-strip bands when Amoxicillin (col 8) is dropped from the v5 layout.
R3_COLUMN_STRIP_BANDS: list[dict[str, Any]] = [
    {"rows": "B,D,F", "cols": [2, 4, 6, 10]},
    {"rows": "C,E,G", "cols": [5, 9]},
    {"rows": "C,E,G", "cols": [3, 7]},
]

# Clavulanic acid — default on-plate positive control; must not also appear as a sample.
DEFAULT_POSITIVE_CONTROL_COMPOUND_ID = "T19860"

COMPOUND_PLACEMENT_RULES: dict[str, Any] = {
    "positive_control_not_also_sample": {
        "description": (
            "If clavulanic acid (T19860) is used as the positive control, "
            "do not also include it in the discovery sample compound list."
        ),
        "positive_control_compound_id": DEFAULT_POSITIVE_CONTROL_COMPOUND_ID,
        "enforcement": "sample list excludes positive-control compound_id before layout",
    },
}


def _is_interior(row_idx: int, col_idx: int) -> bool:
    return (
        INTERIOR_ROW_START <= row_idx <= INTERIOR_ROW_END
        and INTERIOR_COL_START <= col_idx <= INTERIOR_COL_END
    )


def _parse_well_indices(well: str) -> tuple[int, int]:
    row_idx = ROWS.index(well[0])
    col_idx = int(well[1:]) - 1
    return row_idx, col_idx


def validate_interior_layout(wells: dict[str, dict[str, Any]], *, layout: LayoutMode) -> None:
    """Raise if an interior-only layout uses edge wells or duplicate assignments."""
    if layout not in INTERIOR_LAYOUT_MODES:
        return
    seen: set[str] = set()
    for well_id_key, _payload in wells.items():
        if well_id_key in seen:
            raise ValueError(f"Duplicate well assignment: {well_id_key}")
        seen.add(well_id_key)
        row_idx, col_idx = _parse_well_indices(well_id_key)
        if row_idx in EDGE_ROWS or col_idx in EDGE_COLS:
            raise ValueError(
                f"Layout {layout} must not use edge wells; {well_id_key} is on the plate rim"
            )
        if not _is_interior(row_idx, col_idx):
            raise ValueError(f"Well {well_id_key} is outside the interior block B–G × 2–11")


def validate_sample_x_separation(wells: dict[str, dict[str, Any]]) -> None:
    """Raise if two sample wells on the same row share an edge horizontally."""
    samples_by_row: dict[int, list[int]] = {}
    for well_key, payload in wells.items():
        if payload.get("role") != "sample":
            continue
        row_idx, col_idx = _parse_well_indices(well_key)
        samples_by_row.setdefault(row_idx, []).append(col_idx)
    for row_idx, cols in samples_by_row.items():
        for left, right in zip(sorted(cols), sorted(cols)[1:]):
            if right - left == 1:
                raise ValueError(
                    f"Samples on row {ROWS[row_idx]} are horizontally adjacent "
                    f"(cols {left + 1} and {right + 1}); layout requires x-maximal separation"
                )


def positive_control_compound_id(control_row: dict[str, Any]) -> str | None:
    """Return compound_id plated as positive control, or None if count is zero."""
    positive = control_row.get("positive") or {}
    if int(positive.get("count", 0)) <= 0:
        return None
    return positive.get("compound_id", DEFAULT_POSITIVE_CONTROL_COMPOUND_ID)


def sample_compounds_excluding_positive_control(
    compounds: list[dict[str, Any]],
    *,
    control_row: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Drop positive-control compound from discovery samples (see COMPOUND_PLACEMENT_RULES)."""
    pos_id = positive_control_compound_id(control_row)
    if not pos_id:
        return compounds, []
    excluded = [c["compound_id"] for c in compounds if c.get("compound_id") == pos_id]
    samples = [c for c in compounds if c.get("compound_id") != pos_id]
    return samples, excluded


def well_id(row_idx: int, col_idx: int) -> str:
    """Return standard well label (e.g. B3) from 0-based row/col indices."""
    if not 0 <= row_idx < len(ROWS):
        raise ValueError(f"row_idx {row_idx} out of range (0–{len(ROWS) - 1})")
    if not 0 <= col_idx < COLS:
        raise ValueError(f"col_idx {col_idx} out of range (0–{COLS - 1})")
    return f"{ROWS[row_idx]}{col_idx + 1}"


def _vehicle_well() -> dict[str, Any]:
    return {
        "compound_id": None,
        "concentration_uM": 0,
        "role": "vehicle",
        "bucket": "control",
    }


def _no_tem1_well() -> dict[str, Any]:
    return {
        "compound_id": None,
        "concentration_uM": 0,
        "role": "no_tem1",
        "bucket": "control",
    }


def _positive_control_well(compound_id: str, concentration_uM: float) -> dict[str, Any]:
    return {
        "compound_id": compound_id,
        "concentration_uM": concentration_uM,
        "role": "pos-ctrl-clavaculin",
        "bucket": "control",
    }


def _sample_well(compound: dict[str, Any], replicate: int) -> dict[str, Any]:
    well: dict[str, Any] = {
        "compound_id": compound["compound_id"],
        "concentration_uM": compound.get("screen_conc_uM", 50),
        "role": "sample",
        "bucket": compound.get("bucket", "sample"),
        "replicate": replicate,
    }
    if functional_class := compound.get("functional_class"):
        well["functional_class"] = functional_class
    return well


def add_control_row(
    wells: dict[str, dict[str, Any]],
    *,
    control_row: dict[str, Any] | None = None,
    row_idx: int = 0,
) -> None:
    """Fill row A (by default) with vehicle, no-enzyme, and positive controls."""
    cfg = control_row if control_row is not None else DEFAULT_CONTROL_ROW
    col = 0

    for _ in range(int(cfg.get("vehicle", 0))):
        wells[well_id(row_idx, col)] = _vehicle_well()
        col += 1

    for _ in range(int(cfg.get("no_tem1", 0))):
        wells[well_id(row_idx, col)] = _no_tem1_well()
        col += 1

    positive = cfg.get("positive") or {}
    pos_count = int(positive.get("count", 0))
    pos_id = positive.get("compound_id", "T19860")
    pos_conc = float(positive.get("concentration_uM", 50))
    for _ in range(pos_count):
        wells[well_id(row_idx, col)] = _positive_control_well(pos_id, pos_conc)
        col += 1


def add_compound_block(
    wells: dict[str, dict[str, Any]],
    compounds: list[dict[str, Any]],
    *,
    replicates: int = 3,
    start_row: int = 1,
    start_col: int = 0,
) -> None:
    """Place compounds left-to-right, top-to-bottom; three replicates per compound."""
    idx = 0
    for compound in compounds:
        for rep in range(1, replicates + 1):
            linear = start_col + idx
            row = start_row + linear // COLS
            col = linear % COLS
            wells[well_id(row, col)] = _sample_well(compound, rep)
            idx += 1


def _checkerboard_sample_positions() -> list[tuple[int, int]]:
    """Interior wells on a checkerboard — 30 cells, no orthogonal neighbors."""
    positions: list[tuple[int, int]] = []
    for row in range(INTERIOR_ROW_START, INTERIOR_ROW_END + 1):
        for col in range(INTERIOR_COL_START, INTERIOR_COL_END + 1):
            if (row + col) % 2 == 0:
                positions.append((row, col))
    return positions


def _triplicate_control_positions(
    control_row: dict[str, Any],
    *,
    control_rows: tuple[int, ...],
    control_cols: tuple[int, ...] = SPACED_CONTROL_COLS,
) -> list[tuple[int, int]]:
    """Place 3+3+3 controls on spaced interior cells (one band per control type)."""
    vehicle = int(control_row.get("vehicle", 0))
    no_tem1 = int(control_row.get("no_tem1", 0))
    positive = control_row.get("positive") or {}
    pos_count = int(positive.get("count", 0))
    groups = [vehicle, no_tem1, pos_count]
    positions: list[tuple[int, int]] = []

    for group_size, row in zip(groups, control_rows, strict=True):
        for col in control_cols[:group_size]:
            positions.append((row, col))
    return positions


def _spaced_control_positions(control_row: dict[str, Any]) -> list[tuple[int, int]]:
    """Place triplicate controls on complement cells, spaced across B / D / F."""
    return _triplicate_control_positions(
        control_row,
        control_rows=SPACED_INTERIOR_CONTROL_ROWS,
    )


def add_spaced_interior_layout(
    wells: dict[str, dict[str, Any]],
    compounds: list[dict[str, Any]],
    *,
    replicates: int = 3,
    control_row: dict[str, Any] | None = None,
) -> None:
    """Fill interior wells only, checkerboard samples + spaced control rows."""
    cfg = control_row if control_row is not None else DEFAULT_CONTROL_ROW
    positive = cfg.get("positive") or {}
    pos_id = positive.get("compound_id", "T19860")
    pos_conc = float(positive.get("concentration_uM", 50))

    control_positions = _spaced_control_positions(cfg)
    vehicle_n = int(cfg.get("vehicle", 0))
    no_tem1_n = int(cfg.get("no_tem1", 0))
    pos_n = int(positive.get("count", 0))

    idx = 0
    for _ in range(vehicle_n):
        wells[well_id(*control_positions[idx])] = _vehicle_well()
        idx += 1
    for _ in range(no_tem1_n):
        wells[well_id(*control_positions[idx])] = _no_tem1_well()
        idx += 1
    for _ in range(pos_n):
        wells[well_id(*control_positions[idx])] = _positive_control_well(pos_id, pos_conc)
        idx += 1

    sample_positions = _checkerboard_sample_positions()
    expected = len(compounds) * replicates
    if len(sample_positions) != expected:
        raise ValueError(
            f"Checkerboard interior has {len(sample_positions)} sample slots, "
            f"need {expected} ({len(compounds)} compounds × {replicates} replicates)"
        )

    slot = 0
    for compound in compounds:
        for rep in range(1, replicates + 1):
            row, col = sample_positions[slot]
            wells[well_id(row, col)] = _sample_well(compound, rep)
            slot += 1


def _column_strip_control_positions(control_row: dict[str, Any]) -> list[tuple[int, int]]:
    """Controls @ 3/7 on B/D/F; col-11 triplicates shifted one row down to C/E/G."""
    positions = _triplicate_control_positions(
        control_row,
        control_rows=STRIP_SAMPLE_ROWS,
    )
    col11 = SPACED_CONTROL_COLS[-1]
    return [
        (row + COLUMN_STRIP_COL11_ROW_OFFSET, col) if col == col11 else (row, col)
        for row, col in positions
    ]


def _parse_row_band(row_spec: str) -> tuple[int, ...]:
    """Parse 'B,D,F' into 0-based row indices."""
    return tuple(ROWS.index(part.strip()) for part in row_spec.split(",") if part.strip())


def _column_strip_bands_from_spec(
    band_spec: list[dict[str, Any]],
    *,
    compound_count: int,
) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
    """Build band tuples from compound_list column_strip_bands override."""
    bands: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    slot_total = 0
    for entry in band_spec:
        rows = _parse_row_band(str(entry["rows"]))
        cols = tuple(int(c) - 1 for c in entry["cols"])
        bands.append((rows, cols))
        slot_total += len(cols)
    if slot_total != compound_count:
        raise ValueError(
            f"column_strip_bands defines {slot_total} compound slots, "
            f"but compound list has {compound_count} compounds"
        )
    return bands


def resolve_column_strip_bands(
    compound_list: dict[str, Any],
    compound_count: int,
) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
    """Return explicit band override or default auto bands for compound count."""
    if band_spec := compound_list.get("column_strip_bands"):
        return _column_strip_bands_from_spec(band_spec, compound_count=compound_count)
    return _spaced_column_strip_bands(compound_count)


def resolve_control_row(
    compound_list: dict[str, Any],
    *,
    control_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge explicit control_row arg with compound_list.control_row fallback."""
    if control_row is not None:
        return control_row
    if cfg := compound_list.get("control_row"):
        return cfg
    return DEFAULT_CONTROL_ROW


def _spaced_column_strip_bands(
    compound_count: int,
) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
    """Three x-spaced bands: B/D/F (2/4/6/8/10), then C/E/G (5/9), then C/E/G (3/7/11)."""
    max_compounds = len(SPACED_SAMPLE_COLS) + len(COLUMN_STRIP_BAND2_COLS) + len(
        COLUMN_STRIP_BAND3_COLS
    )
    if compound_count > max_compounds:
        raise ValueError(
            f"column_strip layout supports at most {max_compounds} compounds "
            f"with x-maximal separation, got {compound_count}"
        )
    bands: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    remaining = compound_count

    band1 = min(remaining, len(SPACED_SAMPLE_COLS))
    if band1:
        bands.append((STRIP_SAMPLE_ROWS, SPACED_SAMPLE_COLS[:band1]))
        remaining -= band1

    band2 = min(remaining, len(COLUMN_STRIP_BAND2_COLS))
    if band2:
        bands.append((COLUMN_STRIP_CONTROL_ROWS, COLUMN_STRIP_BAND2_COLS[:band2]))
        remaining -= band2

    band3 = min(remaining, len(COLUMN_STRIP_BAND3_COLS))
    if band3:
        bands.append((COLUMN_STRIP_CONTROL_ROWS, COLUMN_STRIP_BAND3_COLS[:band3]))
        remaining -= band3

    if remaining:
        raise ValueError(f"Could not place {remaining} compounds in x-spaced column_strip bands")
    return bands


def add_column_strip_layout(
    wells: dict[str, dict[str, Any]],
    compounds: list[dict[str, Any]],
    *,
    replicates: int = 3,
    control_row: dict[str, Any] | None = None,
    column_strip_bands: list[tuple[tuple[int, ...], tuple[int, ...]]] | None = None,
) -> None:
    """One compound per x-spaced column; triplicates vertically (B/D/F, then C/E/G)."""
    cfg = control_row if control_row is not None else DEFAULT_CONTROL_ROW
    positive = cfg.get("positive") or {}
    pos_id = positive.get("compound_id", "T19860")
    pos_conc = float(positive.get("concentration_uM", 50))

    if replicates != len(STRIP_SAMPLE_ROWS):
        raise ValueError(
            f"column_strip layout requires {len(STRIP_SAMPLE_ROWS)} replicates, got {replicates}"
        )

    bands = column_strip_bands if column_strip_bands is not None else _spaced_column_strip_bands(
        len(compounds)
    )

    control_positions = _column_strip_control_positions(cfg)
    vehicle_n = int(cfg.get("vehicle", 0))
    no_tem1_n = int(cfg.get("no_tem1", 0))
    pos_n = int(positive.get("count", 0))

    idx = 0
    for _ in range(vehicle_n):
        wells[well_id(*control_positions[idx])] = _vehicle_well()
        idx += 1
    for _ in range(no_tem1_n):
        wells[well_id(*control_positions[idx])] = _no_tem1_well()
        idx += 1
    for _ in range(pos_n):
        wells[well_id(*control_positions[idx])] = _positive_control_well(pos_id, pos_conc)
        idx += 1

    compound_idx = 0
    for sample_rows, cols in bands:
        for col in cols:
            compound = compounds[compound_idx]
            for rep, row in enumerate(sample_rows, start=1):
                wells[well_id(row, col)] = _sample_well(compound, rep)
            compound_idx += 1


def _variable_concentration_note(
    compounds: list[dict[str, Any]],
    *,
    default_uM: float = 50,
) -> str:
    """Append note when compounds use different screen concentrations."""
    non_default = [
        f"{c['compound_id']} @ {c['screen_conc_uM']} µM"
        + (f" (rule {c['concentration_rule']})" if c.get("concentration_rule") else "")
        for c in compounds
        if c.get("screen_conc_uM", default_uM) != default_uM
    ]
    if not non_default:
        return ""
    return (
        ". "
        + "; ".join(non_default)
        + f"; all others @ {default_uM} µM unless noted in compound_list.json"
    )


def _layout_notes(
    compounds: list[dict[str, Any]],
    *,
    replicates: int,
    control_row: dict[str, Any],
    default_uM: float = 50,
    layout: LayoutMode = "compact",
) -> str:
    vehicle = int(control_row.get("vehicle", 0))
    no_tem1 = int(control_row.get("no_tem1", 0))
    positive = control_row.get("positive") or {}
    pos_count = int(positive.get("count", 0))
    control_total = vehicle + no_tem1 + pos_count
    sample_total = len(compounds) * replicates

    if layout == "spaced_interior":
        return (
            "96-well flat bottom, spaced interior layout: no edge wells (rows A/H, cols 1/12 empty). "
            f"Controls ({control_total}) on B/D/F at cols 3/7/11; "
            f"{sample_total} sample wells ({len(compounds)} compounds × {replicates}) "
            "on an interior checkerboard (no sample–sample edge contact; "
            "controls on spaced complement cells at cols 3/7/11)"
            + _variable_concentration_note(compounds, default_uM=default_uM)
            + "."
        )

    if layout == "column_strip":
        vehicle = int(control_row.get("vehicle", 0))
        band_note = (
            "B/D/F @ 2/4/6/10, then C/E/G @ 5/9, then C/E/G @ 3/7"
            if vehicle == 0 and len(compounds) == 8
            else "B/D/F @ 2/4/6/8/10, then C/E/G @ 5/9, then C/E/G @ 3/7 for overflow"
        )
        control_note = (
            f"Controls ({control_total}): 3× no-TEM-1 @ D3/D7/E11; "
            f"3× clavulanic acid @ F3/F7/G11. No vehicle controls"
            if vehicle == 0
            else f"Controls ({control_total}) on B/D/F @ 3/7 and C/E/G @ 11"
        )
        return (
            "96-well flat bottom, column-strip layout: no edge wells (rows A/H, cols 1/12 empty). "
            f"X-spaced sample columns only (no horizontally adjacent samples): {band_note}. "
            f"{control_note}"
            + _variable_concentration_note(compounds, default_uM=default_uM)
            + "."
        )

    buckets: dict[str, list[str]] = {}
    for compound in compounds:
        bucket = compound.get("bucket", "sample")
        buckets.setdefault(bucket, []).append(compound["compound_id"])

    bucket_bits: list[str] = []
    if tier1 := buckets.get("tier1_inhibitor"):
        bucket_bits.append(f"row B = {len(tier1)} tier-1 inhibitors × {replicates}")
    if substrate := buckets.get("substrate_control"):
        bucket_bits.append(f"row C = {len(substrate)} substrate controls × {replicates}")
    if diverse := buckets.get("diverse_pick"):
        bucket_bits.append(f"row D = {len(diverse)} diverse picks × {replicates}")

    sample_desc = "; ".join(bucket_bits) if bucket_bits else f"{len(compounds)} compounds × {replicates}"
    return (
        f"96-well flat bottom: row A = {control_total} plate controls; "
        f"{sample_desc} ({sample_total} sample wells, {len(compounds)} unique compounds)"
        + _variable_concentration_note(compounds, default_uM=default_uM)
        + ". Rows E–H empty/reserved."
    )


def design_single_point_plate(
    compound_list: dict[str, Any],
    *,
    control_row: dict[str, Any] | None = None,
    layout: LayoutMode | None = None,
) -> dict[str, Any]:
    """Build a plate map dict from a compound_list.json payload."""
    cfg = resolve_control_row(compound_list, control_row=control_row)
    compounds_raw = compound_list["compounds"]
    compounds, excluded_from_samples = sample_compounds_excluding_positive_control(
        compounds_raw,
        control_row=cfg,
    )
    replicates = int(compound_list.get("replicates_per_compound", 3))
    screen_conc = compound_list.get("default_screen_conc_uM", 50)
    working_multiplier = compound_list.get("working_solution_multiplier", 10)
    compound_volume = compound_list.get("compound_volume_ul", 5)
    final_volume = compound_list.get("final_volume_ul", 50)
    layout_mode: LayoutMode = layout or compound_list.get("layout", "compact")

    wells: dict[str, dict[str, Any]] = {}
    if layout_mode == "spaced_interior":
        add_spaced_interior_layout(
            wells,
            compounds,
            replicates=replicates,
            control_row=cfg,
        )
    elif layout_mode == "column_strip":
        strip_bands = resolve_column_strip_bands(compound_list, len(compounds))
        add_column_strip_layout(
            wells,
            compounds,
            replicates=replicates,
            control_row=cfg,
            column_strip_bands=strip_bands,
        )
    else:
        add_control_row(wells, control_row=cfg)
        add_compound_block(wells, compounds, replicates=replicates)

    validate_interior_layout(wells, layout=layout_mode)
    if layout_mode in INTERIOR_LAYOUT_MODES:
        validate_sample_x_separation(wells)

    run = compound_list.get("run")
    version = compound_list.get("version")
    version_label = compound_list.get("version_label")
    versioned_path = (
        f"data/screens/{run}/v{version}/plate_map.json"
        if run is not None and version is not None
        else None
    )
    compound_list_path = compound_list.get(
        "compound_list",
        versioned_path.replace("plate_map.json", "compound_list.json")
        if versioned_path
        else None,
    )
    screen_concs = {c.get("screen_conc_uM", screen_conc) for c in compounds}
    variable_concentrations = len(screen_concs) > 1

    plate_map: dict[str, Any] = {
        "run": run,
        "version": version,
        "round": compound_list.get("round"),
        "assay_type": compound_list.get("assay_type", "single_point"),
        "final_volume_ul": final_volume,
        "compound_volume_ul": compound_volume,
        "replicates_per_compound": replicates,
        "exclude_compound_ids": compound_list.get("exclude_compound_ids", []),
        "compound_list": compound_list_path,
        "rationale_doc": compound_list.get("rationale_doc"),
        "layout_notes": _layout_notes(
            compounds,
            replicates=replicates,
            control_row=cfg,
            default_uM=screen_conc,
            layout=layout_mode,
        ),
        "layout": layout_mode,
        "layout_rules": LAYOUT_RULES[layout_mode],
        "compound_placement_rules": COMPOUND_PLACEMENT_RULES,
        "wells": wells,
        "versioned_path": versioned_path,
        "rationale_doc_active": "pvjthomas/selection_rationale.md",
        "version_label": version_label,
    }
    if excluded_from_samples:
        plate_map["excluded_from_samples"] = excluded_from_samples
        plate_map["excluded_from_samples_reason"] = (
            "Compound(s) plated as positive control — not duplicated as discovery samples "
            f"(see compound_placement_rules.positive_control_not_also_sample)"
        )

    vehicle_n = int(cfg.get("vehicle", 0))
    no_tem1_n = int(cfg.get("no_tem1", 0))
    pos_n = int((cfg.get("positive") or {}).get("count", 0))
    plate_map["control_summary"] = {
        "vehicle": vehicle_n,
        "no_tem1": no_tem1_n,
        "positive_clavulanic_T19860": pos_n,
        "total": vehicle_n + no_tem1_n + pos_n,
    }
    plate_map["sample_summary"] = {
        "compounds": len(compounds),
        "wells": len(compounds) * replicates,
    }

    if variable_concentrations:
        plate_map["default_compound_concentration_uM"] = screen_conc
        plate_map["concentrations_from"] = compound_list_path
        plate_map["working_solution_uM"] = screen_conc * working_multiplier
        desc = (
            f"Round {compound_list.get('round')} discovery v{version} — "
            f"{len(compounds)} compounds in triplicate with literature-backed "
            "per-compound concentrations (see compound_list.json)"
        )
    else:
        plate_map["compound_concentration_uM"] = screen_conc
        plate_map["working_solution_uM"] = screen_conc * working_multiplier
        desc = (
            f"Round {compound_list.get('round')} discovery v{version} — "
            f"{len(compounds)} compounds in triplicate @ {screen_conc} µM"
            + (f" (reduced from 24 in v{version - 1})" if version and version > 1 else "")
        )
    if layout_mode == "spaced_interior":
        desc += "; spaced interior layout (no edge wells)"
    elif layout_mode == "column_strip":
        desc += "; column-strip layout (x-spaced columns, triplicates on B/D/F and C/E/G)"
        if vehicle_n == 0:
            desc += "; no vehicle controls"
    plate_map["description"] = desc

    return plate_map


def load_compound_list(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def write_plate_map(plate_map: dict[str, Any], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plate_map, indent=2) + "\n")
    return out


def write_compound_list_csv(compound_list: dict[str, Any], path: str | Path) -> Path:
    """Write spreadsheet-friendly compound_list.csv from compound_list.json payload."""
    import csv

    fieldnames = [
        "slot",
        "compound_id",
        "name",
        "bucket",
        "functional_class",
        "screen_conc_uM",
        "working_solution_uM",
        "concentration_rule",
        "screen_conc_source",
        "expected_at_screen_conc",
        "source_plate",
        "source_well",
        "refs_file",
        "reference_summary",
    ]
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for compound in compound_list.get("compounds", []):
            ref = compound.get("concentration_reference") or {}
            summary = ref.get("citation") or ref.get("note") or ref.get("evidence_type", "")
            if ref.get("chembl"):
                chembl = ref["chembl"]
                summary = (
                    f"ChEMBL {chembl.get('document_chembl_id')} "
                    f"IC50={chembl.get('standard_value_uM')} µM"
                )
            writer.writerow(
                {
                    "slot": compound.get("slot"),
                    "compound_id": compound.get("compound_id"),
                    "name": compound.get("name"),
                    "bucket": compound.get("bucket"),
                    "functional_class": compound.get("functional_class"),
                    "screen_conc_uM": compound.get("screen_conc_uM"),
                    "working_solution_uM": compound.get("working_solution_uM"),
                    "concentration_rule": compound.get("concentration_rule"),
                    "screen_conc_source": compound.get("screen_conc_source"),
                    "expected_at_screen_conc": compound.get("expected_at_screen_conc"),
                    "source_plate": compound.get("source_plate"),
                    "source_well": compound.get("source_well"),
                    "refs_file": compound.get("refs_file"),
                    "reference_summary": str(summary)[:200],
                }
            )
    return out


def generate_plate_map_from_file(
    compound_list_path: str | Path,
    output_path: str | Path,
    *,
    control_row: dict[str, Any] | None = None,
) -> Path:
    compound_list = load_compound_list(compound_list_path)
    plate_map = design_single_point_plate(compound_list, control_row=control_row)
    return write_plate_map(plate_map, output_path)
