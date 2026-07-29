"""Render nitrocefin plate map JSON as PNG with typed colors and well labels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, Rectangle
from wellmap.util import ij_from_well

PLATE_ROWS = 8
PLATE_COLS = 12
EMPTY_COLOR = "#F3F4F6"

ColorMode = Literal["sample_type", "compound", "concentration"]

SAMPLE_TYPE_COLORS: dict[str, str] = {
    "vehicle": "#9CA3AF",
    "no_tem1": "#F59E0B",
    "pos_ctrl": "#DC2626",
    "tier1_inhibitor": "#2563EB",
    "substrate_control": "#16A34A",
    "diverse_pick": "#9333EA",
    "dose_response": "#0E7490",
    "sample": "#64748B",
    "control": "#9CA3AF",
}

SAMPLE_TYPE_LABELS: dict[str, str] = {
    "vehicle": "Vehicle (DMSO)",
    "no_tem1": "No TEM-1",
    "pos_ctrl": "Positive control",
    "tier1_inhibitor": "Tier-1 inhibitor",
    "substrate_control": "Substrate control",
    "diverse_pick": "Diverse pick",
    "dose_response": "Dose response",
    "sample": "Sample",
    "control": "Control",
}

CONTROL_GROUP_LABELS: dict[str, str] = {
    "vehicle": "Vehicle (DMSO)",
    "no_tem1": "No TEM-1",
    "pos_ctrl": "Positive control (POS)",
}

CONTROL_WELL_LABELS: dict[str, str] = {
    "vehicle": "VEH",
    "no_tem1": "noTEM1",
    "pos-ctrl-clavaculin": "POS",
}

# Hatch pattern per category (matplotlib hatch strings).
CATEGORY_HATCH: dict[str, str | None] = {
    "vehicle": "....",
    "no_tem1": "++",
    "pos_ctrl": "///",
    "tier1_inhibitor": None,
    "substrate_control": "---",
    "diverse_pick": "xxx",
    "dose_response": "\\\\\\",
    "sample": "||",
    "control": "..",
}

HATCH_LEGEND_ITEMS: list[tuple[str, str | None, str]] = [
    ("tier1_inhibitor", None, "Tier-1 inhibitor — solid fill"),
    ("substrate_control", "---", "Substrate control — horizontal lines"),
    ("diverse_pick", "xxx", "Diverse / unknown — crosshatch"),
    ("vehicle", "....", "Vehicle (DMSO) — dots"),
    ("no_tem1", "++", "No TEM-1 — grid"),
    ("pos_ctrl", "///", "Positive control — diagonal lines"),
]

COMPOUND_PALETTE: list[str] = [
    "#2563EB",
    "#DC2626",
    "#16A34A",
    "#9333EA",
    "#EA580C",
    "#0891B2",
    "#CA8A04",
    "#DB2777",
    "#059669",
    "#7C3AED",
    "#B45309",
    "#0D9488",
    "#4F46E5",
    "#E11D48",
    "#65A30D",
    "#C026D3",
    "#0284C7",
    "#D97706",
    "#10B981",
    "#6366F1",
    "#F43F5E",
    "#84CC16",
    "#8B5CF6",
    "#14B8A6",
]


def _choose_foreground_color(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    grey = r * 0.299 + g * 0.587 + b * 0.114
    return "black" if grey > 0.588 else "white"


def _sample_type(well: dict) -> str:
    role = well.get("role")
    if role == "vehicle":
        return "vehicle"
    if role == "no_tem1":
        return "no_tem1"
    if role == "pos-ctrl-clavaculin":
        return "pos_ctrl"
    if bucket := well.get("bucket"):
        if bucket in SAMPLE_TYPE_COLORS:
            return bucket
        if bucket == "control":
            return "control"
    if role == "sample":
        return "sample"
    return role or "sample"


def _compound_group(well: dict) -> str:
    role = well.get("role")
    if role == "vehicle":
        return "vehicle"
    if role == "no_tem1":
        return "no_tem1"
    if role == "pos-ctrl-clavaculin":
        return "pos_ctrl"
    if compound_id := well.get("compound_id"):
        return str(compound_id)
    return role or "unknown"


def _concentration_label(well: dict) -> str:
    conc = well.get("concentration_uM")
    if conc is None:
        return ""
    if conc == 0:
        role = well.get("role")
        if role == "no_tem1":
            return "0"
        if role == "vehicle":
            return "VEH"
        return "0"
    if float(conc).is_integer():
        return f"{int(conc)}"
    return f"{conc:g}"


def _well_label(well: dict, *, color_by: ColorMode = "sample_type") -> str:
    if color_by == "concentration":
        return _concentration_label(well)
    role = well.get("role")
    if role in CONTROL_WELL_LABELS:
        return CONTROL_WELL_LABELS[role]
    if compound_id := well.get("compound_id"):
        return str(compound_id)
    return ""


def _resolve_compound_list_path(plate_map: dict, plate_map_path: Path | None) -> Path | None:
    rel = plate_map.get("compound_list")
    if not rel:
        return None
    rel_path = Path(rel)
    if rel_path.is_file():
        return rel_path
    if plate_map_path is not None:
        candidates = [
            plate_map_path.parent / rel_path.name,
            plate_map_path.parents[2] / rel_path if len(plate_map_path.parents) > 2 else None,
            Path.cwd() / rel_path,
        ]
        for candidate in candidates:
            if candidate is not None and candidate.is_file():
                return candidate
    cwd_candidate = Path.cwd() / rel_path
    return cwd_candidate if cwd_candidate.is_file() else None


def _load_compound_catalog(
    plate_map: dict,
    *,
    plate_map_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """compound_id -> {name, bucket, slot} from compound_list.json."""
    catalog: dict[str, dict[str, Any]] = {}
    list_path = _resolve_compound_list_path(plate_map, plate_map_path)
    if list_path is None:
        return catalog
    try:
        payload = json.loads(list_path.read_text())
    except (OSError, json.JSONDecodeError):
        return catalog
    for entry in payload.get("compounds", []):
        cid = entry.get("compound_id")
        if not cid:
            continue
        catalog[str(cid)] = {
            "name": entry.get("name") or "",
            "bucket": entry.get("bucket") or "sample",
            "slot": entry.get("slot"),
        }
    return catalog


def plate_map_to_df(plate_map: dict, *, color_by: ColorMode = "sample_type") -> pd.DataFrame:
    """Flatten plate_map['wells'] into a tidy DataFrame."""
    rows: list[dict] = []
    for well_id, well in plate_map.get("wells", {}).items():
        compound_id = well.get("compound_id")
        row = {
            "well": well_id,
            "role": well.get("role"),
            "sample_type": _sample_type(well),
            "compound_group": _compound_group(well),
            "label": _well_label(well, color_by=color_by),
            "compound_id": compound_id if compound_id is not None else "—",
            "concentration_uM": well.get("concentration_uM"),
            "bucket": well.get("bucket"),
        }
        if "replicate" in well:
            row["replicate"] = well["replicate"]
        row_i, col_j = ij_from_well(well_id)
        row["row_i"] = row_i
        row["col_j"] = col_j
        rows.append(row)
    return pd.DataFrame(rows)


def _default_output_path(json_path: Path, *, color_by: ColorMode = "sample_type") -> Path:
    if json_path.name == "plate_map.json":
        if color_by == "compound":
            return json_path.with_name("plate_map_by_compound.png")
        if color_by == "concentration":
            return json_path.with_name("plate_map_concentrations.png")
        return json_path.with_name("plate_map.png")
    if color_by == "compound":
        return json_path.with_name(f"{json_path.stem}_by_compound.png")
    if color_by == "concentration":
        return json_path.with_name(f"{json_path.stem}_concentrations.png")
    return json_path.with_suffix(".png")


def _build_title(plate_map: dict, *, color_by: ColorMode) -> str:
    parts: list[str] = []
    if label := plate_map.get("version_label"):
        parts.append(str(label))
    if assay_type := plate_map.get("assay_type"):
        parts.append(str(assay_type))
    parts.append(
        "by sample type"
        if color_by == "sample_type"
        else "by compound"
        if color_by == "compound"
        else "concentrations (µM)"
    )
    if notes := plate_map.get("layout_notes"):
        note = str(notes)
        if len(note) > 100:
            note = note[:97] + "..."
        parts.append(note)
    return " · ".join(parts) if parts else "Plate map"


def _colors_for_sample_types(present_types: list[str]) -> tuple[list[str], dict[str, str]]:
    colors = dict(SAMPLE_TYPE_COLORS)
    fallback_palette = ["#EC4899", "#14B8A6", "#EAB308", "#6366F1"]
    extra_types = [t for t in present_types if t not in colors]
    for idx, sample_type in enumerate(extra_types):
        colors[sample_type] = fallback_palette[idx % len(fallback_palette)]

    type_order = [t for t in SAMPLE_TYPE_COLORS if t in present_types]
    type_order.extend(t for t in present_types if t not in type_order)
    return type_order, colors


def _colors_for_compounds(present_groups: list[str]) -> tuple[list[str], dict[str, str]]:
    group_order = list(dict.fromkeys(present_groups))
    colors = {
        group: COMPOUND_PALETTE[idx % len(COMPOUND_PALETTE)]
        for idx, group in enumerate(group_order)
    }
    return group_order, colors


def _group_category(
    group: str,
    *,
    color_by: ColorMode,
    catalog: dict[str, dict[str, Any]],
) -> str:
    if group in {"vehicle", "no_tem1", "pos_ctrl"}:
        return group
    if color_by == "sample_type":
        return group
    if group in catalog:
        return str(catalog[group].get("bucket") or "sample")
    return "sample"


def _legend_label(
    group: str,
    *,
    color_by: ColorMode,
    catalog: dict[str, dict[str, Any]],
) -> str:
    if color_by == "sample_type":
        return SAMPLE_TYPE_LABELS.get(group, group.replace("_", " ").title())
    if color_by == "concentration":
        return SAMPLE_TYPE_LABELS.get(group, group.replace("_", " ").title())
    if group in CONTROL_GROUP_LABELS:
        label = CONTROL_GROUP_LABELS[group]
        if group == "pos_ctrl" and "T19860" in catalog:
            name = catalog["T19860"].get("name")
            if name:
                return f"{label} — {name}"
        return label
    meta = catalog.get(group, {})
    name = meta.get("name") or ""
    slot = meta.get("slot")
    if slot is not None and name:
        return f"{slot}. {group} — {name}"
    if name:
        return f"{group} — {name}"
    return group


def _draw_well_label(ax: plt.Axes, *, col: int, row: int, label: str) -> None:
    """Draw well ID text on a solid black background for legibility over hatch fills."""
    ax.text(
        col,
        row,
        label,
        ha="center",
        va="center",
        fontsize=5.5,
        color="white",
        weight="bold",
        bbox={
            "boxstyle": "square,pad=0.12",
            "facecolor": "black",
            "edgecolor": "none",
            "linewidth": 0,
        },
        zorder=10,
    )


def _draw_well(
    ax: plt.Axes,
    *,
    row: int,
    col: int,
    facecolor: str,
    hatch: str | None,
) -> None:
    rect = Rectangle(
        (col - 0.5, row - 0.5),
        1,
        1,
        facecolor=facecolor,
        edgecolor="white",
        linewidth=1.5,
        hatch=hatch,
        zorder=1,
    )
    ax.add_patch(rect)


def _color_legend_groups(
    legend: plt.Legend,
    group_order: list[str],
    highlight_groups: set[str],
    *,
    color: str = "#DC2626",
) -> None:
    for text, group in zip(legend.get_texts(), group_order):
        if group in highlight_groups:
            text.set_color(color)
            text.set_fontweight("bold")



def _add_hatch_legend_below(
    ax: plt.Axes,
    compound_legend: plt.Legend,
    *,
    legend_bbox_x: float = 1.01,
) -> None:
    """Draw a B&W hatch-pattern key directly under the compound legend."""
    fig = ax.figure
    fig.canvas.draw()
    bbox_axes = compound_legend.get_window_extent().transformed(ax.transAxes.inverted())

    row_h = 0.034
    swatch_w = 0.038
    swatch_h = 0.022
    text_x = legend_bbox_x + swatch_w + 0.012
    y = bbox_axes.y0 - 0.03

    ax.text(
        legend_bbox_x,
        y,
        "Hatch Legend",
        transform=ax.transAxes,
        fontsize=8,
        fontweight="bold",
        va="top",
        ha="left",
        color="black",
        clip_on=False,
    )
    y -= 0.028

    with plt.rc_context({"hatch.color": "black", "hatch.linewidth": 1.4}):
        for _, hatch, label in HATCH_LEGEND_ITEMS:
            swatch = Rectangle(
                (legend_bbox_x, y - swatch_h),
                swatch_w,
                swatch_h,
                transform=ax.transAxes,
                facecolor="white",
                edgecolor="black",
                linewidth=1.4,
                hatch=hatch,
                clip_on=False,
                zorder=10,
            )
            ax.add_patch(swatch)
            ax.text(
                text_x,
                y - swatch_h / 2,
                label,
                transform=ax.transAxes,
                va="center",
                ha="left",
                fontsize=7,
                color="black",
                clip_on=False,
            )
            y -= row_h


def draw_plate_map_on_axes(
    ax: plt.Axes,
    df: pd.DataFrame,
    *,
    color_by: ColorMode = "sample_type",
    catalog: dict[str, dict[str, Any]] | None = None,
    highlight_groups: set[str] | None = None,
    include_hatch_legend: bool = False,
    legend_bbox_x: float = 1.01,
) -> None:
    """Draw a plate map on an existing axes with optional hatch legend below compound legend."""
    catalog = catalog or {}
    highlight_groups = highlight_groups or set()
    color_column = (
        "sample_type"
        if color_by in {"sample_type", "concentration"}
        else "compound_group"
    )
    present_groups = list(dict.fromkeys(df[color_column].tolist()))

    if color_by == "sample_type":
        group_order, colors = _colors_for_sample_types(present_groups)
        legend_title = "Sample type"
    elif color_by == "concentration":
        group_order, colors = _colors_for_sample_types(present_groups)
        legend_title = "Sample type (µM labels)"
    else:
        group_order, colors = _colors_for_compounds(present_groups)
        legend_title = "Compound"

    group_to_idx = {group: idx for idx, group in enumerate(group_order)}

    matrix = np.full((PLATE_ROWS, PLATE_COLS), np.nan)
    labels = [["" for _ in range(PLATE_COLS)] for _ in range(PLATE_ROWS)]
    categories = [["" for _ in range(PLATE_COLS)] for _ in range(PLATE_ROWS)]

    for _, row in df.iterrows():
        i = int(row["row_i"])
        j = int(row["col_j"])
        group = row[color_column]
        matrix[i, j] = group_to_idx[group]
        labels[i][j] = row["label"]
        categories[i][j] = _group_category(group, color_by=color_by, catalog=catalog)

    legend_cols = 1 if len(group_order) <= 12 else 2
    legend_fontsize = 6.5 if color_by == "compound" else 8

    ax.set_xlim(-0.5, PLATE_COLS - 0.5)
    ax.set_ylim(PLATE_ROWS - 0.5, -0.5)
    ax.set_facecolor(EMPTY_COLOR)

    for i in range(PLATE_ROWS):
        for j in range(PLATE_COLS):
            if np.isnan(matrix[i, j]):
                continue
            group = group_order[int(matrix[i, j])]
            cat = categories[i][j]
            _draw_well(
                ax,
                row=i,
                col=j,
                facecolor=colors[group],
                hatch=CATEGORY_HATCH.get(cat),
            )
            label = labels[i][j]
            if label:
                _draw_well_label(ax, col=j, row=i, label=label)

    ax.set_xticks(range(PLATE_COLS))
    ax.set_xticklabels(range(1, PLATE_COLS + 1))
    ax.set_yticks(range(PLATE_ROWS))
    ax.set_yticklabels(list("ABCDEFGH"))
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")
    ax.tick_params(length=0)
    ax.set_aspect("equal")

    legend_handles = [
        Patch(
            facecolor=colors[group],
            edgecolor="#374151",
            linewidth=0.8,
            hatch=CATEGORY_HATCH.get(
                _group_category(group, color_by=color_by, catalog=catalog)
            ),
            label=_legend_label(group, color_by=color_by, catalog=catalog),
        )
        for group in group_order
    ]
    compound_legend = ax.legend(
        handles=legend_handles,
        title=legend_title,
        loc="upper left",
        bbox_to_anchor=(legend_bbox_x, 1.0),
        frameon=True,
        fontsize=legend_fontsize,
        title_fontsize=9,
        ncol=legend_cols,
    )
    _color_legend_groups(compound_legend, group_order, highlight_groups)

    if include_hatch_legend:
        ax.add_artist(compound_legend)
        _add_hatch_legend_below(
            ax,
            compound_legend,
            legend_bbox_x=legend_bbox_x,
        )


def _render_colored_plate(
    df: pd.DataFrame,
    *,
    color_by: ColorMode = "sample_type",
    title: str | None = None,
    catalog: dict[str, dict[str, Any]] | None = None,
) -> plt.Figure:
    """Draw a 96-well plate colored by sample type or compound group."""
    legend_cols = 1
    color_column = (
        "sample_type"
        if color_by in {"sample_type", "concentration"}
        else "compound_group"
    )
    present_groups = list(dict.fromkeys(df[color_column].tolist()))
    group_count = len(present_groups)
    legend_cols = 1 if group_count <= 12 else 2
    fig_width = 14 if legend_cols == 1 else 16
    fig, ax = plt.subplots(figsize=(fig_width, 5.8))
    draw_plate_map_on_axes(
        ax,
        df,
        color_by=color_by,
        catalog=catalog,
    )

    if title:
        fig.suptitle(title, fontsize=10, y=1.02)

    fig.tight_layout()
    return fig


def render_plate_map(
    plate_map: dict,
    output_path: Path,
    *,
    color_by: ColorMode = "sample_type",
    cols: list[str] | None = None,
    plate_map_path: Path | None = None,
) -> Path:
    """Render a plate map dict to PNG with well labels."""
    del cols  # kept for CLI compatibility
    df = plate_map_to_df(plate_map, color_by=color_by)
    if df.empty:
        raise ValueError("Plate map has no wells to render")

    catalog = _load_compound_catalog(plate_map, plate_map_path=plate_map_path)
    fig = _render_colored_plate(
        df,
        color_by=color_by,
        title=_build_title(plate_map, color_by=color_by),
        catalog=catalog,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def load_and_render(
    path: str | Path,
    output_path: str | Path | None = None,
    *,
    color_by: ColorMode = "sample_type",
    cols: list[str] | None = None,
) -> Path:
    """Load plate map JSON and write PNG alongside it by default."""
    json_path = Path(path)
    plate_map = json.loads(json_path.read_text())
    out = (
        Path(output_path)
        if output_path is not None
        else _default_output_path(json_path, color_by=color_by)
    )
    return render_plate_map(
        plate_map,
        out,
        color_by=color_by,
        cols=cols,
        plate_map_path=json_path,
    )
