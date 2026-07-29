#!/usr/bin/env python3
"""Generate simplified R3 decision-tree flowchart (slope primary + endpoint fallback)."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

COLOR_DEFAULT = "#E8EEF4"
COLOR_BORDER = "#2C3E50"
COLOR_PASS = "#D5F5E3"
COLOR_PASS_BORDER = "#27AE60"
COLOR_WARN = "#FCF3CF"
COLOR_WARN_BORDER = "#F39C12"
COLOR_FAIL = "#FADBD8"
COLOR_FAIL_BORDER = "#E74C3C"
COLOR_BRANCH = "#EBF5FB"
COLOR_BRANCH_BORDER = "#3498DB"
COLOR_PRIMARY = "#D4EFDF"
COLOR_PRIMARY_BORDER = "#1E8449"


def draw_box(ax, xy, text, *, width=3.8, height=0.82, facecolor=COLOR_DEFAULT, edgecolor=COLOR_BORDER,
             linewidth=1.8, fontsize=11, fontweight="normal", zorder=2):
    x, y = xy
    patch = FancyBboxPatch(
        (x - width / 2, y - height / 2), width, height,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth, zorder=zorder,
    )
    ax.add_patch(patch)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize, fontweight=fontweight,
            color="#1A1A1A", zorder=zorder + 1, wrap=True)
    return patch


def draw_diamond(ax, xy, text, *, size=1.05, facecolor=COLOR_DEFAULT, edgecolor=COLOR_BORDER,
                 linewidth=1.8, fontsize=10.5, fontweight="bold", zorder=2):
    x, y = xy
    verts = [(x, y + size * 0.55), (x + size * 0.95, y), (x, y - size * 0.55), (x - size * 0.95, y)]
    patch = plt.Polygon(verts, closed=True, facecolor=facecolor, edgecolor=edgecolor,
                        linewidth=linewidth, zorder=zorder)
    ax.add_patch(patch)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize, fontweight=fontweight,
            color="#1A1A1A", zorder=zorder + 1)
    return patch


def draw_arrow(ax, start, end, *, color=COLOR_BORDER, linewidth=2.0, label="", label_offset=(0, 0),
               label_color=COLOR_BORDER, label_fontweight="bold", label_fontsize=10, zorder=1):
    arrow = FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=14, linewidth=linewidth, color=color,
        connectionstyle="arc3,rad=0", zorder=zorder,
    )
    ax.add_patch(arrow)
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=label_fontsize,
                fontweight=label_fontweight, color=label_color,
                bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none", alpha=0.9),
                zorder=4)


def draw_note(ax, xy, text, *, ha="left", va="center", width_hint=2.8, fontsize=8.5,
              facecolor="#FAFAFA", edgecolor="#AAB7B8", text_color="#2C3E50"):
    """Small side annotation box."""
    x, y = xy
    ax.text(
        x, y, text, ha=ha, va=va, fontsize=fontsize, color=text_color, style="italic",
        linespacing=1.25,
        bbox=dict(boxstyle="round,pad=0.35", facecolor=facecolor, edgecolor=edgecolor, alpha=0.95),
        zorder=3, wrap=True,
    )


def build_figure(*, show_fallback: bool = True) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(14.5, 9.5), dpi=150)
    ax.set_xlim(0, 14.5)
    ax.set_ylim(-0.2, 10.2)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    cx = 4.2
    fx = 9.4  # fallback column

    ax.text(7.2, 10.0, "Run 3 v1: sync hand nitrocefin → slope QC → endpoint fallback if needed",
            ha="center", va="center", fontsize=14, fontweight="bold", color="#1A5276")

    # Primary column (expected path)
    y = 9.0
    draw_box(ax, (cx, y), "R3 kinetic CSV\n+ sync nitrocefin timing", width=3.6, height=0.78,
             facecolor="#F4F6F7", fontweight="bold")
    draw_arrow(ax, (cx, y - 0.45), (cx, 8.05))

    draw_diamond(ax, (cx, 7.6), "Q1: Data OK?\n≥24/30 wells")
    draw_note(
        ax,
        (cx + 2.15, 7.6),
        "≥24/30 wells have a valid readout:\n"
        "Gen5 CSV has well, time, A490\n"
        "and ≥2 points in the aligned\n"
        "180–480 s kinetic window.",
        ha="left",
    )
    draw_arrow(ax, (cx, 7.05), (cx, 6.55))

    draw_diamond(ax, (cx, 6.1), "Q1T: Sync dose?\n≤ 2 min target", facecolor=COLOR_PASS,
                 edgecolor=COLOR_PASS_BORDER)
    draw_note(
        ax,
        (cx - 2.35, 6.1),
        "Nitrocefin added to all wells\n"
        "within ≤2 min (hand multichannel).\n"
        "R2 failed here: robot stagger\n"
        "spanned ~16 min.",
        ha="right",
    )
    draw_arrow(ax, (cx + 1.0, 6.1), (cx + 2.0, 6.1), color=COLOR_PASS_BORDER, label="PASS",
               label_offset=(0, 0.2), label_color=COLOR_PASS_BORDER)
    draw_arrow(ax, (cx, 5.55), (cx, 5.05))

    draw_diamond(ax, (cx, 4.6), "Q2: Substrate HOT\nno-TEM-1 FLAT?", facecolor=COLOR_PRIMARY,
                 edgecolor=COLOR_PRIMARY_BORDER)
    draw_note(
        ax,
        (cx - 2.35, 4.6),
        "Enzyme QC on A490 slopes\n"
        "(180–480 s window):\n"
        "HOT = fast yellow buildup\n"
        "(substrate wells, ≥6/9);\n"
        "FLAT = no turnover\n"
        "(no-TEM-1 wells, ≥2/3).",
        ha="right",
    )
    draw_arrow(ax, (cx + 1.0, 4.6), (cx + 2.0, 4.6), color=COLOR_PRIMARY_BORDER, linewidth=2.5,
               label="PASS\n(expected)", label_offset=(0, 0.25), label_color=COLOR_PRIMARY_BORDER)

    draw_diamond(ax, (cx, 3.15), "Q3: Clavulanic\nslope ≥50%?", facecolor=COLOR_PASS,
                 edgecolor=COLOR_PASS_BORDER)
    draw_note(
        ax,
        (cx - 2.35, 3.15),
        "Inhibition score from slopes\n"
        "(not slope size itself):\n"
        "0% = substrate-like (hot);\n"
        "100% = no-TEM-1-like (flat).\n"
        "Clavulanic median ≥50%\n"
        "= inhibition detectable.",
        ha="right",
    )
    draw_arrow(ax, (cx, 4.05), (cx, 3.65))
    draw_arrow(ax, (cx + 1.0, 3.15), (cx + 2.0, 3.15), color=COLOR_PASS_BORDER, linewidth=2.5,
               label="PASS", label_offset=(0, 0.18), label_color=COLOR_PASS_BORDER)

    draw_box(ax, (cx, 2.2), "Classify 8 compounds\n(scoring_mode = slope)", width=3.5, height=0.75,
             facecolor=COLOR_PRIMARY, edgecolor=COLOR_PRIMARY_BORDER, fontweight="bold")
    draw_arrow(ax, (cx, 2.65), (cx, 2.55))

    draw_box(ax, (cx, 1.2), "Step 4: DR or close\nR2 artifact calls", width=3.5, height=0.72,
             facecolor=COLOR_PASS, edgecolor=COLOR_PASS_BORDER, fontweight="bold")
    draw_arrow(ax, (cx, 1.82), (cx, 1.58))

    ax.text(cx, 0.45, "Primary path · anchor = substrate controls (no vehicle)",
            ha="center", fontsize=10, color="#566573", style="italic")

    if show_fallback:
        # Fallback branch from Q2
        draw_arrow(ax, (cx + 1.0, 4.35), (fx - 1.2, 4.35), color=COLOR_FAIL_BORDER, linewidth=2.2,
                   label="FAIL", label_offset=(0, 0.22), label_color=COLOR_FAIL_BORDER)
        ax.text(fx, 4.85, "Endpoint fallback\n(same as R2 Q2E/Q3E)", ha="center", fontsize=9.5,
                color="#922B21", style="italic",
                bbox=dict(boxstyle="round,pad=0.25", facecolor=COLOR_FAIL, edgecolor=COLOR_FAIL_BORDER))

        draw_box(ax, (fx, 4.35), "Endpoint analysis\nA490 @ t0+600s", width=3.2, height=0.72,
                 facecolor=COLOR_BRANCH, edgecolor=COLOR_BRANCH_BORDER, fontsize=10.5)
        draw_arrow(ax, (fx, 3.95), (fx, 3.45))

        draw_diamond(ax, (fx, 3.0), "Q2E: substrate − NT\nA490 ≥ 0.02?", facecolor=COLOR_BRANCH,
                     edgecolor=COLOR_BRANCH_BORDER, fontsize=10)
        draw_arrow(ax, (fx + 1.0, 3.0), (fx + 2.05, 3.0), color=COLOR_FAIL_BORDER, label="FAIL",
                   label_offset=(0, 0.18), label_color=COLOR_FAIL_BORDER)
        ax.text(fx + 2.35, 3.0, "hand_q2", ha="left", va="center", fontsize=9, color="#922B21",
                fontweight="bold")
        draw_arrow(ax, (fx, 2.45), (fx, 1.95))

        draw_diamond(ax, (fx, 1.5), "Q3: Clavulanic\nendpoint ≥50%?", facecolor=COLOR_BRANCH,
                     edgecolor=COLOR_BRANCH_BORDER, fontsize=10)
        draw_arrow(ax, (fx + 1.0, 1.5), (fx + 2.05, 1.5), color=COLOR_FAIL_BORDER, label="FAIL",
                   label_offset=(0, 0.18), label_color=COLOR_FAIL_BORDER)
        ax.text(fx + 2.35, 1.5, "hand_q3", ha="left", va="center", fontsize=9, color="#922B21",
                fontweight="bold")
        draw_arrow(ax, (fx, 1.05), (fx, 0.55), color=COLOR_BRANCH_BORDER, linewidth=2.5,
                   label="PASS", label_offset=(-0.55, 0), label_color=COLOR_BRANCH_BORDER)

        draw_box(ax, (fx, 0.15), "Classify compounds\n(scoring_mode = endpoint)", width=3.3,
                 height=0.68, facecolor=COLOR_BRANCH, edgecolor=COLOR_BRANCH_BORDER,
                 fontsize=10, fontweight="bold")

        # Bracket
        ax.plot([12.35, 12.35], [-0.05, 4.75], color=COLOR_BRANCH_BORDER, linewidth=3.5,
                solid_capstyle="round")
        ax.text(12.55, 2.35, "Kinetics\nfallback", ha="left", va="center", fontsize=11,
                fontweight="bold", color=COLOR_BRANCH_BORDER, rotation=90)

    legend_handles = [
        mpatches.Patch(facecolor=COLOR_PRIMARY, edgecolor=COLOR_PRIMARY_BORDER, label="Primary (slope)"),
        mpatches.Patch(facecolor=COLOR_BRANCH, edgecolor=COLOR_BRANCH_BORDER, label="Fallback (endpoint)"),
        mpatches.Patch(facecolor=COLOR_PASS, edgecolor=COLOR_PASS_BORDER, label="PASS"),
        mpatches.Patch(facecolor=COLOR_FAIL, edgecolor=COLOR_FAIL_BORDER, label="FAIL → hand protocol"),
    ]
    ax.legend(handles=legend_handles, loc="upper left", fontsize=9, title="Paths", title_fontsize=9.5,
              bbox_to_anchor=(0.01, 0.99))

    ax.text(7.2, -0.05, "R2 = endpoint discovery (stagger artifact)  ·  R3 = kinetics validation (sync dose)",
            ha="center", fontsize=10.5, color="#566573", style="italic")

    fig.tight_layout(pad=0.35)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("pvjthomas/runs/3/v1/r3_decision_tree.png"),
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig = build_figure()
    fig.savefig(output, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
