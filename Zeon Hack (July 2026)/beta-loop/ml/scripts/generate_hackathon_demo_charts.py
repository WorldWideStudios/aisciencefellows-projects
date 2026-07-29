#!/usr/bin/env python3
"""Generate hackathon demo charts for Round 2 endpoint inhibition and nitrocefin stagger."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "data" / "screens" / "demo"
PVJ_OUTPUT = REPO_ROOT / "pvjthomas" / "output"
R2_EDA = REPO_ROOT / "data" / "screens" / "2" / "post-run" / "v2" / "analysis" / "r2_round_summary_eda.json"
NITROCEFIN_TIMING = REPO_ROOT / "data" / "screens" / "2" / "post-run" / "nitrocefin_timing.json"
READER_LID_CLOSE = REPO_ROOT / "data" / "screens" / "2" / "post-run" / "reader_lid_close_utc.txt"
R2_COMPOUND_LIST = REPO_ROOT / "data" / "screens" / "2" / "v5" / "compound_list.json"
# R3 v1 skipped T1005 (col 8 empty) — do not show on R2→R3 endpoint bar chart
R2_BAR_EXCLUDE_COMPOUND_IDS = frozenset({"T1005"})
COMPOUND_LIST = REPO_ROOT / "data" / "screens" / "3" / "v1" / "compound_list.json"
COMPOUND_TABLE = REPO_ROOT / "data" / "screens" / "3" / "v1" / "compound_table.md"

DPI = 150
FIGSIZE_BARS = (12, 7.5)

HIT_TYPE_ORDER = [
    "confirmed_hit",
    "surprise_hit",
    "novel_hit",
    "likely substrate",
    "borderline",
    "pos_ctrl",
]

HIT_TYPE_DESCRIPTIONS = {
    "confirmed_hit": "Confirmed hit — tier-1 β-lactamase inhibitor, ≥50%\n(expected positive; validates assay)",
    "surprise_hit": "Surprise hit — substrate control, ≥50%\n(antibiotic usually hydrolyzed; unexpected inhibition)",
    "novel_hit": "Novel hit — unknown / diverse compound, ≥50%\n(new signal worth follow-up)",
    "likely substrate": "Likely substrate — substrate control, <50%\n(expected negative; weak competition with nitrocefin)",
    "borderline": "Borderline — unknown compound, 20–49%\n(ambiguous; retest or mini dose-response)",
    "pos_ctrl": "Positive control — clavulanic acid reference",
}

PRIOR_LABELS = {
    "tier1_inhibitor": "tier-1 inhibitor",
    "substrate_control": "substrate control",
    "diverse_pick": "unknown / diverse",
}

LABEL_COLORS = {
    "confirmed_hit": "#2563EB",
    "surprise_hit": "#F97316",
    "novel_hit": "#9333EA",
    "likely substrate": "#9CA3AF",
    "borderline": "#9CA3AF",
    "pos_ctrl": "#DC2626",
}

CONDITION_COLORS = {
    "no_tem1": "#F59E0B",
    "pos-ctrl-clavaculin": "#DC2626",
    "vehicle": "#9CA3AF",
    "T1262": "#2563EB",
    "T6685": "#1D4ED8",
    "T14081": "#3B82F6",
    "T1005": "#F97316",
    "T1008": "#FB923C",
    "T0224": "#EA580C",
    "T0985": "#FBBF24",
    "T0138": "#9333EA",
    "T8390": "#A855F7",
}


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


def load_compound_names() -> dict[str, str]:
    names: dict[str, str] = {}
    for path in (R2_COMPOUND_LIST, COMPOUND_LIST):
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        for entry in data.get("compounds", []):
            cid = entry.get("compound_id")
            name = entry.get("name")
            if cid and name:
                names[cid] = name
    if COMPOUND_TABLE.exists():
        for line in COMPOUND_TABLE.read_text().splitlines():
            for pattern in (
                r"^\|\s*\d+\s*\|\s*(T\d+)\s*\|\s*([^|]+?)\s*\|",
                r"^\|\s*(T\d+)\s*\|\s*([^|]+?)\s*\|",
            ):
                match = re.match(pattern, line)
                if match:
                    names.setdefault(match.group(1), match.group(2).strip())
                    break
    return names


def load_compound_priors() -> dict[str, str]:
    priors: dict[str, str] = {}
    if not R2_COMPOUND_LIST.exists():
        return priors
    data = json.loads(R2_COMPOUND_LIST.read_text())
    for entry in data.get("compounds", []):
        cid = entry.get("compound_id")
        bucket = entry.get("bucket")
        if cid and bucket:
            priors[cid] = PRIOR_LABELS.get(bucket, bucket.replace("_", " "))
    return priors


def _hit_type_sort_key(label: str) -> tuple[int, int]:
    order = {name: idx for idx, name in enumerate(HIT_TYPE_ORDER)}
    return (order.get(label, len(HIT_TYPE_ORDER)), 0)


def compound_display(compound_id: str, names: dict[str, str]) -> str:
    name = names.get(compound_id)
    if name:
        return f"{name}\n({compound_id})"
    return compound_id


def _parse_utc(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def _load_reader_lid_close_utc() -> datetime:
    line = READER_LID_CLOSE.read_text().strip().splitlines()[0].strip()
    return _parse_utc(line)


def load_avg_nitrocefin_minutes_until_reader() -> dict[str, float]:
    """Minutes from mean nitrocefin add per condition to plate reader lid close."""
    timing = json.loads(NITROCEFIN_TIMING.read_text())
    events = timing.get("events", [])
    if not events:
        return {}

    reader_t0 = _load_reader_lid_close_utc()

    by_condition: dict[str, list[float]] = {}
    for ev in events:
        minutes = (reader_t0 - _parse_utc(ev["t0_utc"])).total_seconds() / 60.0
        by_condition.setdefault(ev["condition"], []).append(minutes)

    return {condition: sum(times) / len(times) for condition, times in by_condition.items()}


def plot_endpoint_bars(out_path: Path) -> None:
    eda = json.loads(R2_EDA.read_text())
    names = load_compound_names()
    priors = load_compound_priors()
    nitro_stagger = load_avg_nitrocefin_minutes_until_reader()

    rows: list[dict] = []
    for compound_id, info in eda["compounds"].items():
        if compound_id in R2_BAR_EXCLUDE_COMPOUND_IDS:
            continue
        prior = priors.get(compound_id, "")
        rows.append(
            {
                "id": compound_id,
                "label": info["label"],
                "pct": info["median_pct_inhibition"],
                "display": compound_display(compound_id, names),
                "prior": prior,
                "nitro_min_to_reader": nitro_stagger.get(compound_id),
            }
        )

    pos_pct = eda["qc_gates"]["pos_ctrl_median_pct"]
    pos_row = {
        "id": "pos_ctrl",
        "label": "pos_ctrl",
        "pct": pos_pct,
        "display": "Clavulanic\n(pos ctrl)",
        "prior": "reference inhibitor",
        "nitro_min_to_reader": nitro_stagger.get("pos-ctrl-clavaculin"),
    }

    rows.sort(
        key=lambda r: (
            _hit_type_sort_key(r["label"]),
            -(r.get("nitro_min_to_reader") or 0),
        )
    )
    rows.insert(0, pos_row)
    labels = [r["display"] for r in rows]
    values = [r["pct"] for r in rows]
    colors = [LABEL_COLORS.get(r["label"], "#64748B") for r in rows]

    fig, ax = plt.subplots(figsize=FIGSIZE_BARS)
    x = list(range(len(labels)))
    ax.bar(x, values, color=colors, edgecolor="white", linewidth=0.8, width=0.72)
    ax.axhline(50, color="#6B7280", linestyle="--", linewidth=1.5, zorder=0)
    ax.text(
        len(labels) - 0.5,
        52,
        "50% hit threshold",
        ha="right",
        va="bottom",
        fontsize=9,
        color="#6B7280",
        style="italic",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("% inhibition (median)")
    ax.set_ylim(-max(values) * 0.14, max(values) * 1.18)
    ax.yaxis.grid(True, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.set_title(
        "Round 2 — endpoint % inhibition (A490 @ ~900 s)\n"
        "Hit type = endpoint score × compound prior",
        pad=12,
        fontsize=13,
    )

    for i, row in enumerate(rows):
        nitro_min = row.get("nitro_min_to_reader")
        if nitro_min is not None:
            ax.text(
                i,
                -2.8,
                f"{nitro_min:.1f}m",
                ha="center",
                va="top",
                fontsize=7,
                color="#DC2626",
                fontweight="bold",
            )
        if row["prior"]:
            ax.text(
                i,
                -max(values) * 0.11,
                row["prior"],
                ha="right",
                va="top",
                fontsize=7,
                color="#6B7280",
                rotation=35,
            )

    group_spans: list[tuple[str, int, int]] = []
    start = 0
    for idx in range(1, len(rows) + 1):
        if idx == len(rows) or rows[idx]["label"] != rows[start]["label"]:
            group_spans.append((rows[start]["label"], start, idx - 1))
            start = idx

    for label, i0, i1 in group_spans:
        group_max = max(values[i0 : i1 + 1])
        # Anchor labels above each group's bars so shorter right-side groups
        # stay clear of the upper-right legend.
        y_group = group_max + 6.0
        if i0 == i1:
            cx = i0
        else:
            cx = (i0 + i1) / 2
            ax.plot(
                [i0 - 0.38, i1 + 0.38],
                [y_group, y_group],
                color=LABEL_COLORS.get(label, "#64748B"),
                linewidth=1.2,
                clip_on=False,
            )
            ax.plot(
                [i0 - 0.38, i0 - 0.38],
                [y_group - 1.5, y_group],
                color=LABEL_COLORS.get(label, "#64748B"),
                linewidth=1.2,
                clip_on=False,
            )
            ax.plot(
                [i1 + 0.38, i1 + 0.38],
                [y_group - 1.5, y_group],
                color=LABEL_COLORS.get(label, "#64748B"),
                linewidth=1.2,
                clip_on=False,
            )
        short = label.replace("_", " ")
        ax.text(
            cx,
            y_group + 2.5,
            short,
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
            color=LABEL_COLORS.get(label, "#64748B"),
        )

    for (_, _, prev_end), (_, next_start, _) in zip(group_spans[:-1], group_spans[1:]):
        sep_x = (prev_end + next_start) / 2
        ax.axvline(sep_x, color="#D1D5DB", linestyle=":", linewidth=1.0, zorder=0)

    for i, val in enumerate(values):
        ax.text(i, val + 1.5, f"{val:.1f}%", ha="center", va="bottom", fontsize=8)

    present_labels = []
    seen: set[str] = set()
    for row in rows:
        if row["label"] not in seen:
            seen.add(row["label"])
            present_labels.append(row["label"])

    legend_handles = [
        mpatches.Patch(
            color=LABEL_COLORS.get(label, "#64748B"),
            label=HIT_TYPE_DESCRIPTIONS.get(label, label.replace("_", " ")),
        )
        for label in present_labels
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper right",
        bbox_to_anchor=(0.99, 0.99),
        frameon=True,
        fontsize=7.5,
        handlelength=1.2,
        labelspacing=0.9,
    )

    fig.text(
        0.5,
        0.01,
        "Same endpoint readout, different stories: priors set expectations; "
        "endpoint score sets hit vs miss — surprise hits drive Round 3 retests",
        ha="center",
        fontsize=9,
        color="#374151",
        style="italic",
    )

    fig.tight_layout(rect=(0, 0.05, 1, 1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def _well_label_xytext_and_ha(well: str, rank: int, n: int) -> tuple[tuple[int, int], str]:
    """Spread well labels horizontally; 3-character names need more room."""
    spread = 16 if len(well) >= 3 else 7
    y_offset = 7
    if n <= 1:
        return (0, y_offset), "center"
    if rank == 0:
        return (-spread, y_offset), "right"
    if rank == n - 1:
        return (spread, y_offset), "left"
    return (0, y_offset), "center"


def _condition_row_label(condition: str, names: dict[str, str]) -> str:
    if condition == "no_tem1":
        return "No TEM-1"
    if condition == "pos-ctrl-clavaculin":
        return "Clavulanic (+ctrl)"
    if condition == "vehicle":
        return "Vehicle (DMSO)"
    name = names.get(condition)
    if name:
        return f"{name} ({condition})"
    return condition


def plot_nitrocefin_timeline(out_path: Path) -> None:
    timing = json.loads(NITROCEFIN_TIMING.read_text())
    names = load_compound_names()
    events = timing["events"]
    reader_t0 = _load_reader_lid_close_utc()

    def minutes_until_reader(ts: str) -> float:
        delta = reader_t0 - _parse_utc(ts)
        return delta.total_seconds() / 60.0

    enriched = []
    for ev in events:
        enriched.append(
            {
                **ev,
                "minutes": minutes_until_reader(ev["t0_utc"]),
            }
        )

    all_minutes = [e["minutes"] for e in enriched]

    group_order = ["no_tem1", "pos-ctrl-clavaculin"]
    compound_ids = sorted(
        {e["condition"] for e in enriched if e["condition"] not in {"no_tem1", "pos-ctrl-clavaculin", "vehicle"}},
        key=lambda cid: -min(e["minutes"] for e in enriched if e["condition"] == cid),
    )
    group_order.extend(compound_ids)
    group_order.append("vehicle")

    y_positions = {cond: i for i, cond in enumerate(reversed(group_order))}

    wells_by_condition: dict[str, list[dict]] = {}
    for ev in enriched:
        wells_by_condition.setdefault(ev["condition"], []).append(ev)
    for cond_events in wells_by_condition.values():
        cond_events.sort(key=lambda e: e["minutes"])

    fig, ax = plt.subplots(figsize=(12, 7))

    plotted_conditions: set[str] = set()
    for cond, cond_events in wells_by_condition.items():
        n = len(cond_events)
        for rank, ev in enumerate(cond_events):
            y = y_positions[cond]
            color = CONDITION_COLORS.get(cond, "#64748B")
            xytext, ha = _well_label_xytext_and_ha(ev["well"], rank, n)
            ax.scatter(
                ev["minutes"],
                y,
                s=90,
                color=color,
                edgecolors="white",
                linewidths=0.8,
                zorder=3,
            )
            ax.annotate(
                ev["well"],
                (ev["minutes"], y),
                textcoords="offset points",
                xytext=xytext,
                ha=ha,
                fontsize=7,
                color="#374151",
            )
            plotted_conditions.add(cond)

    yticks = [y_positions[c] for c in reversed(group_order)]
    ylabels = [_condition_row_label(c, names) for c in reversed(group_order)]
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels)
    ax.set_xlabel("Minutes until plate reader load")
    ax.set_xlim(min(all_minutes) - 0.5, max(all_minutes) + 0.5)
    ax.xaxis.grid(True, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.text(
        10.0,
        0.98,
        "Robot batched dosing (3 wells / ~22 s per batch)\n→ wells read at different kinetic offsets",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=9,
        color="#374151",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#FEF3C7", edgecolor="#F59E0B", alpha=0.95),
    )

    ax.set_title("Round 2 — robot nitrocefin dosing stagger", pad=12)
    fig.text(
        0.5,
        0.01,
        "AI decision tree → sync hand add for Round 3",
        ha="center",
        fontsize=13,
        color="#6B7280",
        style="italic",
    )

    fig.tight_layout(rect=(0, 0.05, 1, 1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    _apply_slide_style()
    bar_path = OUT_DIR / "r2_endpoint_inhibition_bars.png"
    timeline_path = OUT_DIR / "r2_nitrocefin_stagger_timeline.png"

    plot_endpoint_bars(bar_path)
    plot_nitrocefin_timeline(timeline_path)

    v1gen_bar_path = PVJ_OUTPUT / "r2_endpoint_inhibition_bars_v1gen.png"
    v1gen_timeline_path = PVJ_OUTPUT / "r2_nitrocefin_stagger_timeline_v1gen.png"
    PVJ_OUTPUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bar_path, v1gen_bar_path)
    shutil.copy2(timeline_path, v1gen_timeline_path)

    for path in (bar_path, timeline_path, v1gen_bar_path, v1gen_timeline_path):
        if not path.exists():
            raise SystemExit(f"Failed to write {path}")
        print(f"Wrote {path} ({path.stat().st_size:,} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
