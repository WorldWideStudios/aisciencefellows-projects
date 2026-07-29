#!/usr/bin/env python3
"""Generate simplified R2 decision-tree flowchart for hackathon slides."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


# Slide-ready palette
COLOR_DEFAULT = "#E8EEF4"
COLOR_BORDER = "#2C3E50"
COLOR_PASS = "#D5F5E3"
COLOR_PASS_BORDER = "#27AE60"
COLOR_WARN = "#FCF3CF"
COLOR_WARN_BORDER = "#F39C12"
COLOR_FAIL = "#FADBD8"
COLOR_FAIL_BORDER = "#E74C3C"
COLOR_STAG = "#FDEBD0"
COLOR_STAG_BORDER = "#E67E22"
COLOR_BRANCH = "#EBF5FB"
COLOR_BRANCH_BORDER = "#3498DB"


def draw_box(
    ax,
    xy: tuple[float, float],
    text: str,
    *,
    width: float = 3.6,
    height: float = 0.85,
    facecolor: str = COLOR_DEFAULT,
    edgecolor: str = COLOR_BORDER,
    linewidth: float = 1.8,
    fontsize: float = 11,
    fontweight: str = "normal",
    text_color: str = "#1A1A1A",
    boxstyle: str = "round,pad=0.02,rounding_size=0.08",
    zorder: int = 2,
) -> FancyBboxPatch:
    """Draw a rounded box centered at xy and return the patch."""
    x, y = xy
    patch = FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width,
        height,
        boxstyle=boxstyle,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        zorder=zorder,
    )
    ax.add_patch(patch)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=fontweight,
        color=text_color,
        wrap=True,
        zorder=zorder + 1,
    )
    return patch


def draw_diamond(
    ax,
    xy: tuple[float, float],
    text: str,
    *,
    size: float = 1.05,
    facecolor: str = COLOR_DEFAULT,
    edgecolor: str = COLOR_BORDER,
    fontsize: float = 10.5,
    fontweight: str = "bold",
) -> None:
    """Draw a decision diamond centered at xy."""
    x, y = xy
    diamond = plt.Polygon(
        [(x, y + size), (x + size * 1.35, y), (x, y - size), (x - size * 1.35, y)],
        closed=True,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=1.8,
        zorder=2,
    )
    ax.add_patch(diamond)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=fontweight,
        color="#1A1A1A",
        zorder=3,
    )


def draw_arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = COLOR_BORDER,
    linewidth: float = 2.0,
    style: str = "-|>",
    connectionstyle: str = "arc3,rad=0.0",
    label: str | None = None,
    label_offset: tuple[float, float] = (0.0, 0.0),
    label_color: str = "#555555",
    label_fontsize: float = 9.5,
    label_fontweight: str = "normal",
    zorder: int = 1,
) -> None:
    """Draw an arrow between two points."""
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle=style,
        mutation_scale=14,
        linewidth=linewidth,
        color=color,
        connectionstyle=connectionstyle,
        zorder=zorder,
    )
    ax.add_patch(arrow)
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(
            mx,
            my,
            label,
            ha="center",
            va="center",
            fontsize=label_fontsize,
            fontweight=label_fontweight,
            color=label_color,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.85),
            zorder=4,
        )


def build_figure(*, pos_ctrl_pct: float = 83.3, q2_slope_pass: bool = False) -> plt.Figure:
    """Build the simplified closed-loop R2→R3 decision tree."""
    fig, ax = plt.subplots(figsize=(12, 8), dpi=150)
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.15, 10)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Column centers (top-to-bottom flow)
    cx = 6.0
    y_start = 9.0
    y_q1 = 7.55
    y_q1t = 6.1
    y_q2 = 4.65
    y_branch = 3.35
    y_q3 = 2.05
    y_stag = 1.15

    # Title
    ax.text(
        cx,
        9.72,
        "Run 2 closed-loop: stagger artifact → endpoint rescue → human multichannel nitrocefin addition",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color="#1A5276",
    )

    # 1 — Inputs
    draw_box(
        ax,
        (cx, y_start),
        "Messy R2 kinetic CSV\n+ nitrocefin_timing.json",
        width=4.2,
        height=0.95,
        facecolor="#F4F6F7",
        fontsize=11.5,
        fontweight="bold",
    )
    draw_arrow(ax, (cx, y_start - 0.55), (cx, y_q1 + 0.75))

    # 2 — Q1
    draw_diamond(ax, (cx, y_q1), "Q1: Data OK?\n≥29/36 wells")
    draw_arrow(
        ax,
        (cx + 1.5, y_q1),
        (cx + 2.8, y_q1),
        color=COLOR_PASS_BORDER,
        label="PASS",
        label_offset=(0.0, 0.18),
        label_color=COLOR_PASS_BORDER,
        label_fontweight="bold",
    )
    draw_arrow(ax, (cx, y_q1 - 0.95), (cx, y_q1t + 0.75))

    # 3 — Q1T
    draw_diamond(ax, (cx, y_q1t), "Q1T: Stagger?\nstagger span")
    draw_arrow(
        ax,
        (cx + 1.5, y_q1t),
        (cx + 2.8, y_q1t),
        color=COLOR_WARN_BORDER,
        label='WARN\n"16 min stagger"',
        label_offset=(0.0, 0.22),
        label_color=COLOR_WARN_BORDER,
        label_fontweight="bold",
    )
    draw_arrow(ax, (cx, y_q1t - 0.95), (cx, y_q2 + 0.75))

    # 4 — Q2 FAIL (red highlight)
    draw_diamond(
        ax,
        (cx, y_q2),
        "Q2: Enzyme QC\n(slopes)?",
        facecolor=COLOR_FAIL,
        edgecolor=COLOR_FAIL_BORDER,
    )
    draw_arrow(
        ax,
        (cx + 1.5, y_q2),
        (cx + 2.8, y_q2),
        color=COLOR_FAIL_BORDER,
        linewidth=2.5,
        label="FAIL",
        label_offset=(0.0, 0.18),
        label_color=COLOR_FAIL_BORDER,
        label_fontweight="bold",
        label_fontsize=11,
    )

    # Side annotation for Q2 fail context
    ax.text(
        10.35,
        y_q2,
        "Vehicle / no-TEM-1\nslopes ambiguous\n→ hand_q2 route",
        ha="center",
        va="center",
        fontsize=9,
        color="#922B21",
        style="italic",
        bbox=dict(boxstyle="round,pad=0.3", facecolor=COLOR_FAIL, edgecolor=COLOR_FAIL_BORDER, alpha=0.9),
    )

    # Branch down to endpoint analysis
    draw_arrow(
        ax,
        (cx, y_q2 - 0.95),
        (cx, y_branch + 0.45),
        color=COLOR_BRANCH_BORDER,
        linewidth=2.2,
        label="Endpoint analysis",
        label_offset=(-1.35, 0.0),
        label_color=COLOR_BRANCH_BORDER,
        label_fontweight="bold",
    )

    draw_box(
        ax,
        (cx, y_branch),
        "Endpoint analysis\n(inhibition score @ 490 nm)",
        width=3.8,
        height=0.75,
        facecolor=COLOR_BRANCH,
        edgecolor=COLOR_BRANCH_BORDER,
        fontsize=10.5,
    )
    draw_arrow(ax, (cx, y_branch - 0.45), (cx, y_q3 + 0.75))

    # 5 — Q3 PASS (green)
    draw_diamond(
        ax,
        (cx, y_q3),
        "Q3: Clavulanic\n≥50%?",
        facecolor=COLOR_PASS,
        edgecolor=COLOR_PASS_BORDER,
    )
    draw_arrow(
        ax,
        (cx + 1.5, y_q3),
        (cx + 2.8, y_q3),
        color=COLOR_PASS_BORDER,
        linewidth=2.5,
        label=f"PASS\n@ {pos_ctrl_pct:.1f}%",
        label_offset=(0.0, 0.22),
        label_color=COLOR_PASS_BORDER,
        label_fontweight="bold",
        label_fontsize=10.5,
    )

    # 6 & 7 — human multichannel nitrocefin addition path (orange, bold)
    stag_y_top = y_stag + 0.55
    stag_y_bot = y_stag - 0.55

    draw_arrow(
        ax,
        (cx, y_q3 - 0.95),
        (cx, stag_y_top + 0.45),
        color=COLOR_STAG_BORDER,
        linewidth=3.0,
    )

    draw_box(
        ax,
        (cx, stag_y_top),
        "Step 4: Human multichannel nitrocefin addition",
        width=4.4,
        height=0.72,
        facecolor=COLOR_STAG,
        edgecolor=COLOR_STAG_BORDER,
        linewidth=3.0,
        fontsize=11.5,
        fontweight="bold",
    )

    draw_arrow(
        ax,
        (cx, stag_y_top - 0.42),
        (cx, stag_y_bot + 0.42),
        color=COLOR_STAG_BORDER,
        linewidth=3.0,
    )

    draw_box(
        ax,
        (cx, stag_y_bot),
        "AI redesign: hand nitrocefin\n+ drop vehicle + R3 plate",
        width=4.6,
        height=0.82,
        facecolor=COLOR_STAG,
        edgecolor=COLOR_STAG_BORDER,
        linewidth=3.0,
        fontsize=11.5,
        fontweight="bold",
    )

    # Human multichannel nitrocefin path bracket / highlight on the right
    bracket_x = 9.55
    ax.plot(
        [bracket_x, bracket_x],
        [stag_y_bot - 0.5, stag_y_top + 0.5],
        color=COLOR_STAG_BORDER,
        linewidth=4,
        solid_capstyle="round",
        zorder=1,
    )
    ax.text(
        bracket_x + 0.15,
        (stag_y_top + stag_y_bot) / 2,
        "Human multichannel\nnitrocefin addition",
        ha="left",
        va="center",
        fontsize=11,
        fontweight="bold",
        color=COLOR_STAG_BORDER,
        rotation=90,
    )

    # Footer note (below multichannel nitrocefin boxes)
    ax.text(
        cx,
        -0.02,
        "R2 = endpoint discovery  ·  R3 = kinetics validation",
        ha="center",
        va="top",
        fontsize=10.5,
        color="#566573",
        style="italic",
    )

    # Legend
    legend_handles = [
        mpatches.Patch(facecolor=COLOR_PASS, edgecolor=COLOR_PASS_BORDER, label="PASS"),
        mpatches.Patch(facecolor=COLOR_WARN, edgecolor=COLOR_WARN_BORDER, label="WARN"),
        mpatches.Patch(facecolor=COLOR_FAIL, edgecolor=COLOR_FAIL_BORDER, label="FAIL"),
        mpatches.Patch(facecolor=COLOR_STAG, edgecolor=COLOR_STAG_BORDER, label="Human multichannel nitrocefin addition"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper left",
        frameon=True,
        fontsize=9,
        title="Gate outcomes",
        title_fontsize=9.5,
    )

    fig.tight_layout(pad=0.4)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/screens/demo/r2_decision_tree_multichannel_nitrocefin.png"),
        help="Output PNG path (relative to repo root or absolute)",
    )
    parser.add_argument(
        "--eda-json",
        type=Path,
        default=None,
        help="Optional round summary JSON for Q3 pos-ctrl pct (default 83.3)",
    )
    args = parser.parse_args()

    pos_ctrl_pct = 83.3
    q2_slope_pass = False
    if args.eda_json and args.eda_json.exists():
        import json

        eda = json.loads(args.eda_json.read_text())
        pos_ctrl_pct = float(eda.get("qc_gates", {}).get("pos_ctrl_median_pct", pos_ctrl_pct))
        q2_slope_pass = bool(eda.get("qc_gates", {}).get("q2_pass", False))

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    fig = build_figure(pos_ctrl_pct=pos_ctrl_pct, q2_slope_pass=q2_slope_pass)
    fig.savefig(output, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
