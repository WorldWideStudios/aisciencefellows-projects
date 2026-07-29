#!/usr/bin/env python3
"""Generate t-SNE chemical-space figures for R2/R3 chosen compounds over the library."""

from __future__ import annotations

import json
import re
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from rdkit import DataStructs
from sklearn.manifold import TSNE

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "ml"))

from agent.tools.chem import morgan_fp, parse_smiles, rdkit_status  # noqa: E402
from agent.tools.compounds import load_compounds  # noqa: E402
from analysis.plate_viz import SAMPLE_TYPE_COLORS  # noqa: E402

OUT_DIR = REPO / "pvjthomas" / "output"
R2_COMPOUND_LIST = REPO / "data" / "screens" / "2" / "v5" / "compound_list.json"
R3_COMPOUND_LIST = REPO / "data" / "screens" / "3" / "v1" / "compound_list.json"
R3_COMPOUND_TABLE = REPO / "data" / "screens" / "3" / "v1" / "compound_table.md"

DPI = 150
FIGSIZE = (11, 8.5)

R3_HIT_COLORS = {
    "confirmed_hit": "#2563EB",
    "surprise_hit": "#F97316",
    "novel_hit": "#9333EA",
    "likely substrate": "#9CA3AF",
    "borderline": "#A855F7",
}

R3_HIT_LABELS = {
    "confirmed_hit": "Confirmed hit",
    "surprise_hit": "Surprise hit",
    "novel_hit": "Novel hit",
    "likely substrate": "Likely substrate",
    "borderline": "Borderline",
}

R2_BUCKET_LABELS = {
    "tier1_inhibitor": "Tier-1 inhibitor",
    "substrate_control": "Substrate control",
    "diverse_pick": "Diverse pick",
}

# Shared embedding: Morgan FP (r=2, 2048-bit) → Tanimoto distance → t-SNE on full library.
TSNE_BASIS_LABEL = "Morgan FP r=2, Tanimoto distance"

R2_FOOTER_NOTE = (
    "We didn't explore bottom-right because R2 traded breadth for a clean assay narrative — "
    "once we had inhibitor positives, one penicillin/ceph/carbapenem negative each, and two "
    "uncertain cephs, adding ~30 more cephalosporin analogs (plus monobactams we'd already "
    "seen in R1) was low marginal value for plate slots and robot time.\n\n"
    "If you want to close that gap in a future round, the natural picks would be one monobactam "
    "rep (Aztreonam) plus one extended-spectrum ceph from that cluster (e.g. Ceftazidime or "
    "Ceftaroline) — scaffolds we never retested after R1."
)


def _marker_text_color(hex_color: str) -> str:
    rgb = tuple(int(hex_color.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4))
    luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    return "#111827" if luminance > 0.62 else "white"


def _apply_slide_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#374151",
            "axes.labelcolor": "#111827",
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "xtick.color": "#374151",
            "ytick.color": "#374151",
            "font.size": 10,
            "grid.color": "#E5E7EB",
            "grid.linestyle": "-",
            "grid.linewidth": 0.6,
        }
    )


def _load_compound_list(path: Path) -> list[dict]:
    payload = json.loads(path.read_text())
    return payload.get("compounds", [])


def _load_r3_hit_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    if not R3_COMPOUND_TABLE.exists():
        return labels
    for line in R3_COMPOUND_TABLE.read_text().splitlines():
        match = re.match(
            r"^\|\s*\d+\s*\|\s*(T\d+)\s*\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|\s*[^|]*\|\s*([^|]+?)\s*\|",
            line,
        )
        if match:
            labels[match.group(1)] = match.group(2).strip()
    return labels


def _fingerprint_matrix(compounds: list[dict]) -> tuple[list[str], np.ndarray, list[str | None]]:
    compound_ids: list[str] = []
    names: list[str] = []
    fps: list = []
    for compound in compounds:
        smiles = compound.get("smiles") or ""
        mol = parse_smiles(smiles)
        fp = morgan_fp(mol)
        if fp is None:
            continue
        compound_ids.append(str(compound["compound_id"]))
        names.append(str(compound.get("name") or compound["compound_id"]))
        fps.append(fp)
    if not fps:
        raise RuntimeError("No valid Morgan fingerprints computed from library SMILES.")
    matrix = np.zeros((len(fps), len(fps)), dtype=float)
    for i in range(len(fps)):
        for j in range(i + 1, len(fps)):
            sim = DataStructs.TanimotoSimilarity(fps[i], fps[j])
            dist = 1.0 - sim
            matrix[i, j] = dist
            matrix[j, i] = dist
    return compound_ids, matrix, names


def _run_tsne(distance_matrix: np.ndarray, *, random_state: int = 42) -> np.ndarray:
    n = distance_matrix.shape[0]
    perplexity = min(30.0, max(5.0, (n - 1) / 3))
    tsne = TSNE(
        n_components=2,
        metric="precomputed",
        init="random",
        perplexity=perplexity,
        random_state=random_state,
        learning_rate="auto",
    )
    return tsne.fit_transform(distance_matrix)


def _format_footer_note(text: str, *, width: int = 108) -> str:
    paragraphs = text.strip().split("\n\n")
    return "\n\n".join(textwrap.fill(paragraph, width=width) for paragraph in paragraphs)


def _plot_tsne(
    *,
    coords: np.ndarray,
    compound_ids: list[str],
    names: list[str],
    chosen: list[dict],
    color_key: str,
    color_map: dict[str, str],
    label_map: dict[str, str],
    title: str,
    out_path: Path,
    footer_note: str | None = None,
) -> None:
    chosen_ids = {str(entry["compound_id"]) for entry in chosen}
    id_to_idx = {cid: idx for idx, cid in enumerate(compound_ids)}

    if footer_note:
        fig = plt.figure(figsize=(11, 10.5))
        gs = fig.add_gridspec(
            3,
            1,
            height_ratios=[5.2, 0.45, 1.35],
            hspace=0.02,
        )
        ax = fig.add_subplot(gs[0])
        spacer_ax = fig.add_subplot(gs[1])
        note_ax = fig.add_subplot(gs[2])
        spacer_ax.axis("off")
        spacer_ax.set_facecolor("white")
    else:
        fig, ax = plt.subplots(figsize=FIGSIZE, layout="constrained")
        note_ax = None

    background_x: list[float] = []
    background_y: list[float] = []
    for idx, cid in enumerate(compound_ids):
        if cid in chosen_ids:
            continue
        background_x.append(coords[idx, 0])
        background_y.append(coords[idx, 1])

    ax.scatter(
        background_x,
        background_y,
        s=28,
        c="#D1D5DB",
        alpha=0.75,
        edgecolors="#9CA3AF",
        linewidths=0.4,
        zorder=1,
        label="_nolegend_",
    )

    legend_keys: list[str] = []
    key_rows: list[tuple[int, str, str, str]] = []
    for entry in chosen:
        cid = str(entry["compound_id"])
        idx = id_to_idx[cid]
        slot = int(entry.get("slot") or len(key_rows) + 1)
        key = str(entry.get(color_key) or "unknown")
        color = color_map.get(key, "#64748B")
        display_name = str(entry.get("name") or names[idx])
        key_rows.append((slot, display_name, cid, color))

        ax.scatter(
            coords[idx, 0],
            coords[idx, 1],
            s=72,
            c=color,
            edgecolors="#111827",
            linewidths=0.9,
            zorder=3,
        )
        ax.text(
            coords[idx, 0],
            coords[idx, 1],
            str(slot),
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
            color=_marker_text_color(color),
            zorder=4,
        )
        if key not in legend_keys:
            legend_keys.append(key)

    compound_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=color,
            markeredgecolor="#111827",
            markersize=7,
            label=f"{slot}  {name} ({cid})",
        )
        for slot, name, cid, color in key_rows
    ]

    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#D1D5DB",
            markeredgecolor="#9CA3AF",
            markersize=7,
            label="Library (not selected)",
        )
    ]
    for key in legend_keys:
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor=color_map.get(key, "#64748B"),
                markeredgecolor="#111827",
                markersize=8,
                label=label_map.get(key, key.replace("_", " ")),
            )
        )

    ax.set_title(title)
    ax.set_xlabel("t-SNE 1")
    ax.set_ylabel("t-SNE 2")
    ax.grid(True, alpha=0.55)
    category_legend = ax.legend(handles=handles, loc="upper left", frameon=True, framealpha=0.95)
    ax.add_artist(category_legend)
    compound_legend = ax.legend(
        handles=compound_handles,
        loc="upper right",
        bbox_to_anchor=(0.94, 0.985),
        frameon=True,
        framealpha=0.96,
        fontsize=8.5,
        borderpad=0.55,
        labelspacing=0.35,
        handletextpad=0.55,
    )
    compound_legend.get_frame().set_edgecolor("#E5E7EB")

    if note_ax is not None and footer_note:
        note_ax.set_xlim(0, 1)
        note_ax.set_ylim(0, 1)
        note_ax.axis("off")
        note_ax.set_facecolor("#F9FAFB")
        note_ax.add_patch(
            Rectangle(
                (0, 0),
                1,
                1,
                transform=note_ax.transAxes,
                fill=False,
                edgecolor="#D1D5DB",
                linewidth=1.0,
                clip_on=False,
            )
        )
        note_ax.text(
            0.015,
            0.92,
            "Note",
            transform=note_ax.transAxes,
            ha="left",
            va="top",
            fontsize=8.5,
            fontweight="bold",
            color="#6B7280",
        )
        note_ax.text(
            0.015,
            0.82,
            _format_footer_note(footer_note),
            transform=note_ax.transAxes,
            ha="left",
            va="top",
            fontsize=8.8,
            color="#374151",
            linespacing=1.35,
        )

    if footer_note:
        fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.04, hspace=0.02)
        fig.savefig(out_path, dpi=DPI, bbox_inches="tight", pad_inches=0.08)
    else:
        fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    if not rdkit_status()["available"]:
        raise SystemExit("RDKit is required for Morgan fingerprints.")

    _apply_slide_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    library = [c for c in load_compounds() if not c.get("exclude")]
    compound_ids, distance_matrix, names = _fingerprint_matrix(library)
    coords = _run_tsne(distance_matrix)

    r2_compounds = _load_compound_list(R2_COMPOUND_LIST)
    r3_compounds = _load_compound_list(R3_COMPOUND_LIST)
    r3_hit_labels = _load_r3_hit_labels()
    for entry in r3_compounds:
        cid = str(entry["compound_id"])
        if cid in r3_hit_labels:
            entry["r2_hit_label"] = r3_hit_labels[cid]

    r2_out = OUT_DIR / "r2_tsne_over_library_v1gen.png"
    r3_out = OUT_DIR / "r3_tsne_over_library_v1gen.png"

    _plot_tsne(
        coords=coords,
        compound_ids=compound_ids,
        names=names,
        chosen=r2_compounds,
        color_key="bucket",
        color_map=SAMPLE_TYPE_COLORS,
        label_map=R2_BUCKET_LABELS,
        title=f"Round 2 — Assay validation of known classes ({TSNE_BASIS_LABEL})",
        out_path=r2_out,
        footer_note=R2_FOOTER_NOTE,
    )
    _plot_tsne(
        coords=coords,
        compound_ids=compound_ids,
        names=names,
        chosen=r3_compounds,
        color_key="r2_hit_label",
        color_map=R3_HIT_COLORS,
        label_map=R3_HIT_LABELS,
        title=f"Round 3 — Assay kinetics of known classes ({TSNE_BASIS_LABEL})",
        out_path=r3_out,
    )

    print(f"Wrote {r2_out}")
    print(f"Wrote {r3_out}")


if __name__ == "__main__":
    main()
