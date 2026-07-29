#!/usr/bin/env python3
"""Regenerate Round 3 post-run v1 figures and conclusions."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ml"))
sys.path.insert(0, str(REPO / "ml" / "scripts"))

from generate_hackathon_demo_charts import (  # noqa: E402
    LABEL_COLORS,
    _apply_slide_style,
    _hit_type_sort_key,
    compound_display,
    load_compound_names,
    load_compound_priors,
    plot_nitrocefin_timeline,
)

V1_DIR = REPO / "data" / "screens" / "3" / "post-run" / "v1"
FIG_DIR = V1_DIR / "figures"
R3_EDA = V1_DIR / "analysis" / "r3_round_summary_eda.json"
R3_SUMMARY = REPO / "data" / "assay" / "run_3_summary.json"
R3_COMPOUND_LIST = REPO / "data" / "screens" / "3" / "v1" / "compound_list.json"
R3_TIMING = REPO / "data" / "screens" / "3" / "post-run" / "nitrocefin_timing.json"
R3_READER = REPO / "data" / "screens" / "3" / "post-run" / "reader_lid_close_utc.txt"

FIGSIZE_BARS = (12, 6.5)

PRIOR_LABELS = {
    "tier1_inhibitor": "tier-1 inhibitor",
    "substrate_control": "substrate prior",
    "diverse_pick": "diverse unknown",
}


def _load_r3_names() -> dict[str, str]:
    names: dict[str, str] = {}
    if R3_COMPOUND_LIST.exists():
        data = json.loads(R3_COMPOUND_LIST.read_text())
        for entry in data.get("compounds", []):
            cid = entry.get("compound_id")
            name = entry.get("name")
            if cid and name:
                names[cid] = name
    return names


def _load_r3_priors() -> dict[str, str]:
    priors: dict[str, str] = {}
    if R3_COMPOUND_LIST.exists():
        data = json.loads(R3_COMPOUND_LIST.read_text())
        for entry in data.get("compounds", []):
            cid = entry.get("compound_id")
            bucket = entry.get("bucket")
            if cid and bucket:
                priors[cid] = PRIOR_LABELS.get(bucket, bucket.replace("_", " "))
    return priors


def plot_r3_endpoint_bars(out_path: Path) -> None:
    eda = json.loads(R3_EDA.read_text())
    names = _load_r3_names()
    priors = _load_r3_priors()

    rows: list[dict] = []
    for compound_id, info in eda["compounds"].items():
        rows.append(
            {
                "id": compound_id,
                "label": info["label"],
                "pct": info["median_pct_inhibition"],
                "display": compound_display(compound_id, names),
                "prior": priors.get(compound_id, ""),
            }
        )

    pos_pct = eda["qc_gates"]["pos_ctrl_median_pct"]
    rows.insert(
        0,
        {
            "id": "pos_ctrl",
            "label": "pos_ctrl",
            "pct": pos_pct,
            "display": "Clavulanic\n(pos ctrl)",
            "prior": "reference inhibitor",
        },
    )
    rows.sort(key=lambda r: (_hit_type_sort_key(r["label"]), -r["pct"]))

    labels = [r["display"] for r in rows]
    values = [r["pct"] for r in rows]
    colors = [LABEL_COLORS.get(r["label"], "#64748B") for r in rows]

    fig, ax = plt.subplots(figsize=FIGSIZE_BARS)
    x = list(range(len(labels)))
    ax.bar(x, values, color=colors, edgecolor="white", linewidth=0.8, width=0.72)
    ax.axhline(50, color="#6B7280", linestyle="--", linewidth=1.5, zorder=0)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("% inhibition (median)")
    ymax = max(values) if values else 100
    ax.set_ylim(-ymax * 0.08, ymax * 1.12)
    ax.yaxis.grid(True, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    scoring = eda.get("scoring_mode", "endpoint")
    ax.set_title(
        f"Round 3 — endpoint % inhibition (substrate anchor)\n"
        f"scoring_mode = {scoring} · sync manual nitrocefin",
        pad=12,
        fontsize=13,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def write_conclusions(out_path: Path) -> None:
    eda = json.loads(R3_EDA.read_text())
    qc = eda.get("qc_gates", {})
    compounds = eda.get("compounds", {})

    scoring_mode = eda.get("scoring_mode", "endpoint")
    lines = [
        "# Round 3 post-run v1 — conclusions",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Scoring mode:** `{scoring_mode}`  ",
        "**Spec:** [run3_decision_tree.md](../../../pvjthomas/runs/3/v1/run3_decision_tree.md)",
        "",
        "---",
        "",
        "## Executive summary",
        "",
        "Run 3 v1 kinetic data passed **Q1, Q1T, Q2E, and Q3** with sync manual nitrocefin dosing (~2 min span).",
        "Slope Q2 failed (substrate and no-TEM-1 slopes both near-flat), so compound calls use **endpoint fallback**",
        f"(`{scoring_mode}`). Positive control clavulanic scored {qc.get('pos_ctrl_median_pct', '?')}%.",
        "",
        "**Tier-1 inhibitors (T1262, T6685, T14081) all confirmed hits.** T0224 (substrate prior) scored as a",
        "**surprise_hit** at ~98% — priority dose-response before treating as a true inhibitor.",
        "",
        "T1008 substrate control wells largely **failed** the 0–150% score window (8 failed wells total),",
        "so substrate-anchor QC should be interpreted cautiously despite Q2E passing on endpoint dynamic range.",
        "",
        "---",
        "",
        "## QC gates",
        "",
        "| Gate | Result | Notes |",
        "|------|--------|-------|",
        f"| Q1 data | {'PASS' if qc.get('q1_pass') else 'FAIL'} | ≥24/30 assay wells |",
        f"| Q1T sync dose | {'PASS' if not qc.get('q1t_timing_stagger') else 'WARN'} | {eda.get('timing_stagger_min', '?')} min span |",
        f"| Q2 slope | {'PASS' if qc.get('q2_pass') else 'FAIL'} | substrate vs no-TEM-1 slope separation |",
        f"| Q2E endpoint | {'PASS' if qc.get('q2_endpoint_pass') else 'FAIL'} | Δ A490 = {eda.get('control_stats', {}).get('endpoint_dynamic_range', '?')} |",
        f"| Q3 clavulanic | {'PASS' if qc.get('q3_pass') else 'FAIL'} | {qc.get('pos_ctrl_median_pct', '?')}% |",
        "",
        "---",
        "",
        "## Compound calls",
        "",
        "| ID | Median % | Label |",
        "|----|----------|-------|",
    ]
    for cid, info in sorted(
        compounds.items(),
        key=lambda kv: (-float(kv[1].get("median_pct_inhibition") or 0), kv[0]),
    ):
        lines.append(
            f"| {cid} | {info.get('median_pct_inhibition', '—')} | `{info.get('label', '—')}` |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Recommended next steps",
            "",
            "1. **8-point dose-response on T0224** — surprise hit on a substrate prior; confirm before advancing.",
            "2. **Advance tier-1 confirmed hits** (T1262, T6685, T14081) to dose-response design.",
            "3. **Investigate T1008 well failures** — substrate anchor wells B10/D10/F10 failed scoring; check replicates and raw traces.",
            "4. **Do not treat T0138/T8390 as hits** — inactive on endpoint scoring.",
            "",
            "See [`run3_decision_report.md`](../run3_decision_report.md) for full per-well detail.",
            "",
        ]
    )
    out_path.write_text("\n".join(lines))


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    _apply_slide_style()

    plot_r3_endpoint_bars(FIG_DIR / "r3_endpoint_inhibition_bars.png")

    # Nitrocefin timeline — patch module-level paths temporarily
    import generate_hackathon_demo_charts as charts

    charts.NITROCEFIN_TIMING = R3_TIMING
    charts.READER_LID_CLOSE = R3_READER
    plot_nitrocefin_timeline(FIG_DIR / "r3_nitrocefin_sync_timeline.png")

    dt_script = REPO / "ml" / "scripts" / "generate_r3_decision_tree_figure.py"
    subprocess.run(
        [
            sys.executable,
            str(dt_script),
            "--output",
            str(FIG_DIR / "r3_decision_tree_multichannel_nitrocefin.png"),
        ],
        check=True,
        cwd=REPO,
    )

    tsne_script = REPO / "ml" / "scripts" / "generate_hackathon_tsne_figures.py"
    tsne_dest = FIG_DIR / "r3_tsne_over_library.png"
    tsne_src = REPO / "pvjthomas" / "output" / "r3_tsne_over_library_v1gen.png"
    try:
        subprocess.run([sys.executable, str(tsne_script)], check=True, cwd=REPO)
        if tsne_src.exists():
            shutil.copy2(tsne_src, tsne_dest)
    except (subprocess.CalledProcessError, OSError):
        if tsne_src.exists():
            shutil.copy2(tsne_src, tsne_dest)

    write_conclusions(V1_DIR / "conclusions.md")

    manifest = {
        "analysis_version": "v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "figures": {
            "r3_endpoint_inhibition_bars.png": "data/screens/3/post-run/v1/figures/r3_endpoint_inhibition_bars.png",
            "r3_nitrocefin_sync_timeline.png": "data/screens/3/post-run/v1/figures/r3_nitrocefin_sync_timeline.png",
            "r3_decision_tree_multichannel_nitrocefin.png": "data/screens/3/post-run/v1/figures/r3_decision_tree_multichannel_nitrocefin.png",
            "r3_tsne_over_library.png": "data/screens/3/post-run/v1/figures/r3_tsne_over_library.png",
        },
        "conclusions": "data/screens/3/post-run/v1/conclusions.md",
        "decision_report": "data/screens/3/post-run/v1/run3_decision_report.md",
    }
    (FIG_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    for path in sorted(FIG_DIR.glob("*")):
        print(f"Wrote {path.relative_to(REPO)} ({path.stat().st_size:,} bytes)")
    print(f"Wrote {V1_DIR / 'conclusions.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
