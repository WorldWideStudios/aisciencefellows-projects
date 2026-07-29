#!/usr/bin/env python3
"""Generate hackathon demo slide images for plate comparison and hand nitrocefin schematic."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "ml"))

from analysis.plate_viz import (  # noqa: E402
    _load_compound_catalog,
    draw_plate_map_on_axes,
    plate_map_to_df,
)

OUT_DIR = REPO / "data" / "screens" / "demo"
PRESENTATION_OUT_DIR = REPO / "pvjthomas" / "output"
PRESENTATION_PLATES_NAME = "r2_vs_r3_plates_presentation_v1.png"
DPI = 150
R2_PLATE_JSON = REPO / "data" / "screens" / "2" / "v5" / "plate_map.json"
R3_PLATE_JSON = REPO / "data" / "screens" / "3" / "v1" / "plate_map.json"


def _add_plate_caption(ax: plt.Axes, text: str) -> None:
    """Place a large caption directly under the Column axis label."""
    ax.set_xlabel("Column", fontsize=11, labelpad=2)
    fig = ax.figure
    fig.canvas.draw()
    col_bbox = ax.xaxis.get_label().get_window_extent().transformed(ax.transAxes.inverted())
    ax.text(
        0.5,
        col_bbox.y0 - 0.028,
        text,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=20,
        color="#333333",
        style="italic",
        clip_on=False,
    )


def stitch_r2_vs_r3() -> Path:
    """Side-by-side plate map comparison with hatch legend below compound legend."""
    out_path = OUT_DIR / "r2_vs_r3_plates.png"

    r2_plate = json.loads(R2_PLATE_JSON.read_text())
    r3_plate = json.loads(R3_PLATE_JSON.read_text())
    r2_df = plate_map_to_df(r2_plate, color_by="compound")
    r3_df = plate_map_to_df(r3_plate, color_by="compound")
    r2_catalog = _load_compound_catalog(r2_plate, plate_map_path=R2_PLATE_JSON)
    r3_catalog = _load_compound_catalog(r3_plate, plate_map_path=R3_PLATE_JSON)

    fig, (ax_r2, ax_r3) = plt.subplots(
        1,
        2,
        figsize=(34, 9.5),
        dpi=DPI,
        gridspec_kw={"wspace": 0.48, "width_ratios": [1, 1]},
    )
    fig.patch.set_facecolor("white")
    fig.subplots_adjust(left=0.03, right=0.82, top=0.9, bottom=0.1)

    draw_plate_map_on_axes(
        ax_r2,
        r2_df,
        color_by="compound",
        catalog=r2_catalog,
        include_hatch_legend=True,
    )
    draw_plate_map_on_axes(
        ax_r3,
        r3_df,
        color_by="compound",
        catalog=r3_catalog,
        include_hatch_legend=True,
    )

    titles = [
        (ax_r2, "Round 2 v5 (assay validation)"),
        (ax_r3, "Round 3 v1 (kinetics validation)"),
    ]
    for ax, text in titles:
        ax.set_title(text, fontsize=14, fontweight="bold", color="#1a1a1a", pad=12)

    annotations = [
        (
            ax_r2,
            "Robot nitrocefin · 3 tier-1 positives + 6 substrate negatives · vehicle controls",
        ),
        (ax_r3, "Hand sync nitrocefin · 8 compounds · no vehicle (no DMSO)"),
    ]
    for ax, text in annotations:
        _add_plate_caption(ax, text)

    fig.savefig(out_path, dpi=DPI, bbox_inches="tight", facecolor="white", pad_inches=0.45)
    plt.close(fig)

    PRESENTATION_OUT_DIR.mkdir(parents=True, exist_ok=True)
    presentation_path = PRESENTATION_OUT_DIR / PRESENTATION_PLATES_NAME
    shutil.copy2(out_path, presentation_path)
    return out_path, presentation_path


def draw_hand_nitrocefin_schematic() -> Path:
    """Schematic of sync hand nitrocefin addition vs robot stagger."""
    out_path = OUT_DIR / "hand_nitrocefin_schematic.png"

    fig, ax = plt.subplots(figsize=(10, 7), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.set_aspect("equal")
    ax.axis("off")

    # Title block
    fig.text(0.5, 0.96, "Round 3 protocol — hand nitrocefin addition", ha="center", va="top",
             fontsize=18, fontweight="bold", color="#1a1a1a")
    fig.text(0.5, 0.915, "AI scientist recommendation from decision tree", ha="center", va="top",
             fontsize=12, color="#555555", style="italic")

    # 96-well plate (12 cols x 8 rows) — simplified top-down view
    plate_x, plate_y = 0.8, 1.0
    n_cols, n_rows = 12, 8
    well_size = 0.32
    gap = 0.05
    plate_w = n_cols * well_size + (n_cols - 1) * gap + 0.25
    plate_h = n_rows * well_size + (n_rows - 1) * gap + 0.25

    plate = Rectangle(
        (plate_x - 0.15, plate_y - 0.15),
        plate_w + 0.15,
        plate_h + 0.15,
        linewidth=2,
        edgecolor="#333333",
        facecolor="#f8f9fa",
        zorder=1,
    )
    ax.add_patch(plate)

    for row in range(n_rows):
        for col in range(n_cols):
            wx = plate_x + col * (well_size + gap)
            wy = plate_y + (n_rows - 1 - row) * (well_size + gap)
            color = "#dce6f5" if (row + col) % 2 == 0 else "#c8d8ec"
            well = Rectangle(
                (wx, wy), well_size, well_size,
                linewidth=0.6, edgecolor="#8899aa", facecolor=color, zorder=2,
            )
            ax.add_patch(well)

    # Row/column hints (not all 96 labels)
    for col, label in enumerate(["1", "", "4", "", "8", "", "12"] + [""] * 5):
        if label:
            ax.text(plate_x + col * (well_size + gap) + well_size / 2, plate_y - 0.3,
                    label, ha="center", va="top", fontsize=7, color="#666666")
    for row, label in enumerate(["A", "C", "E", "H"]):
        ry = plate_y + (n_rows - 1 - [0, 2, 4, 7][row]) * (well_size + gap) + well_size / 2
        ax.text(plate_x - 0.3, ry, label, ha="right", va="center", fontsize=7, color="#666666")

    ax.text(plate_x + plate_w / 2, plate_y + plate_h + 0.25, "96-well plate (top view)",
            ha="center", va="bottom", fontsize=11, fontweight="bold", color="#333333")

    # Multichannel pipette above plate (12 tips spanning columns)
    pip_x = plate_x + 0.05
    pip_y = plate_y + plate_h + 1.4
    pip_w = plate_w - 0.1
    pip_h = 0.45
    pip_body = Rectangle(
        (pip_x, pip_y), pip_w, pip_h,
        linewidth=1.5, edgecolor="#2c5282", facecolor="#4299e1", zorder=4,
    )
    ax.add_patch(pip_body)
    # 12 tips across full plate width
    tip_w = 0.08
    tip_spacing = (pip_w - 0.2 - 12 * tip_w) / 11
    for i in range(12):
        tx = pip_x + 0.1 + i * (tip_w + tip_spacing)
        tip = Rectangle((tx, pip_y - 0.3), tip_w, 0.3,
                        linewidth=0.8, edgecolor="#2c5282", facecolor="#63b3ed", zorder=4)
        ax.add_patch(tip)
    ax.text(pip_x + pip_w / 2, pip_y + pip_h + 0.12, "12-channel pipette — sync add",
            ha="center", va="bottom", fontsize=9, color="#2c5282", fontweight="bold")

    # Arrows from pipette to all wells (representative fan)
    for col in range(0, n_cols, 2):
        wx = plate_x + col * (well_size + gap) + well_size / 2
        for row in range(n_rows):
            wy = plate_y + (n_rows - 1 - row) * (well_size + gap) + well_size / 2
            tip_x = pip_x + 0.1 + col * (tip_w + tip_spacing) + tip_w / 2
            arrow = FancyArrowPatch(
                (tip_x, pip_y - 0.02),
                (wx, wy + well_size / 2),
                arrowstyle="-|>",
                mutation_scale=7,
                linewidth=0.9,
                color="#e53e3e",
                alpha=0.45,
                zorder=3,
            )
            ax.add_patch(arrow)

    ax.text(plate_x + plate_w / 2, 0.55, "Operator sync add — all wells ≤ 2 min",
            ha="center", va="center", fontsize=13, fontweight="bold", color="#276749",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f0fff4", edgecolor="#68d391", lw=1.5))

    # Robot contrast inset (faded, crossed out)
    inset_x, inset_y = 7.2, 4.6
    inset_w, inset_h = 2.6, 1.6
    inset = Rectangle(
        (inset_x, inset_y), inset_w, inset_h,
        linewidth=1.2, edgecolor="#bbbbbb", facecolor="#f5f5f5", alpha=0.85, zorder=5,
    )
    ax.add_patch(inset)
    ax.text(inset_x + inset_w / 2, inset_y + inset_h * 0.65,
            "Robot: 13 batches / 16 min",
            ha="center", va="center", fontsize=10, color="#999999", alpha=0.9)
    ax.text(inset_x + inset_w / 2, inset_y + inset_h * 0.35,
            "staggered dosing",
            ha="center", va="center", fontsize=8, color="#aaaaaa", alpha=0.85)
    # Cross-out lines
    ax.plot([inset_x + 0.15, inset_x + inset_w - 0.15],
            [inset_y + 0.2, inset_y + inset_h - 0.2],
            color="#cc4444", lw=2, alpha=0.7, zorder=6)
    ax.plot([inset_x + 0.15, inset_x + inset_w - 0.15],
            [inset_y + inset_h - 0.2, inset_y + 0.2],
            color="#cc4444", lw=2, alpha=0.7, zorder=6)
    ax.text(inset_x + inset_w / 2, inset_y + inset_h + 0.2, "Round 2 (avoid)",
            ha="center", va="bottom", fontsize=8, color="#999999")

    # Arrow from inset to main plate
    contrast_arrow = FancyArrowPatch(
        (inset_x, inset_y + inset_h / 2),
        (plate_x + plate_w + 0.1, plate_y + plate_h / 2),
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=1.2,
        color="#999999",
        linestyle="dashed",
        alpha=0.6,
        zorder=5,
    )
    ax.add_patch(contrast_arrow)
    ax.text((inset_x + plate_x + plate_w) / 2 + 0.3, plate_y + plate_h / 2 + 0.35,
            "vs.", ha="center", fontsize=10, color="#777777", style="italic")

    fig.savefig(out_path, dpi=DPI, bbox_inches="tight", facecolor="white", pad_inches=0.15)
    plt.close(fig)
    return out_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p1, p1_presentation = stitch_r2_vs_r3()
    p2 = draw_hand_nitrocefin_schematic()
    print(f"Created: {p1}")
    print(f"Created: {p1_presentation}")
    print(f"Created: {p2}")


if __name__ == "__main__":
    main()
