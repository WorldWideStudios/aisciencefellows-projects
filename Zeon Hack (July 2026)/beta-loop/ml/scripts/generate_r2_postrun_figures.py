#!/usr/bin/env python3
"""Regenerate Round 2 post-run v2 figures and conclusions under post-run/v2/."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ml"))
sys.path.insert(0, str(REPO / "ml" / "scripts"))

from generate_hackathon_demo_charts import (  # noqa: E402
    plot_endpoint_bars,
    plot_nitrocefin_timeline,
    _apply_slide_style,
)
from generate_hackathon_demo_images import stitch_r2_vs_r3  # noqa: E402

V2_DIR = REPO / "data" / "screens" / "2" / "post-run" / "v2"
FIG_DIR = V2_DIR / "figures"
V1_EDA = REPO / "data" / "screens" / "2" / "post-run" / "v1" / "analysis" / "r2_round_summary_eda.json"
V2_EDA = V2_DIR / "analysis" / "r2_round_summary_eda.json"
PVJ_OUT = REPO / "pvjthomas" / "output"

FIGURES = {
    "r2_endpoint_inhibition_bars.png": "Endpoint % inhibition bar chart (v2 scoring)",
    "r2_nitrocefin_stagger_timeline.png": "Nitrocefin dosing stagger timeline",
    "r2_decision_tree_multichannel_nitrocefin.png": "Closed-loop decision tree (slope Q2 → endpoint → human multichannel nitrocefin addition)",
    "r2_tsne_over_library.png": "t-SNE of R2 compound picks over library",
    "r2_vs_r3_plates.png": "R2 vs R3 plate layout comparison",
}


def _load_eda(path: Path) -> dict:
    return json.loads(path.read_text())


def _compound_table(eda: dict) -> list[tuple[str, float, str]]:
    rows = []
    for cid, info in sorted(eda.get("compounds", {}).items()):
        rows.append((cid, float(info.get("median_pct_inhibition", 0)), str(info.get("label", "—"))))
    return rows


def write_conclusions(v1: dict, v2: dict, out_path: Path) -> None:
    v1_qc = v1.get("qc_gates", {})
    v2_qc = v2.get("qc_gates", {})
    v1_rows = _compound_table(v1)
    v2_rows = _compound_table(v2)

    lines = [
        "# Round 2 post-run v2 — conclusions",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        "**Analysis:** endpoint fallback (`scoring_mode = endpoint`) after slope Q2 fail  ",
        "**Spec:** [run2_decision_tree.md](../../../pvjthomas/runs/2/v5/run2_decision_tree.md)",
        "",
        "---",
        "",
        "## Executive summary",
        "",
        "Run 2 v5 kinetic data are usable for **control QC via endpoint A490**, but **not** for a clean",
        "9-compound discovery scorecard. Slope Q2 failed (vehicle and no-TEM-1 both near-flat); endpoint",
        "rescued Q2E and Q3 (clavulanic ~83%). Most sample wells failed the 0–150% score window due to",
        "16 min nitrocefin stagger and high initial absorbance on early-dosed wells.",
        "",
        "**Verdict:** Proceed to **human multichannel nitrocefin addition** for substrate priors and tier-1 inhibitors;",
        "do not treat v2 surprise hits (T1005, T0224) as confirmed inhibitors without that retest.",
        "",
        "---",
        "",
        "## QC gates (v1 slope vs v2 endpoint)",
        "",
        "| Gate | v1 (slope) | v2 (endpoint fallback) |",
        "|------|------------|-------------------------|",
        f"| Q2 slope | {'PASS' if v1_qc.get('q2_pass') else 'FAIL'} | {'PASS' if v2_qc.get('q2_pass') else 'FAIL'} |",
        f"| Q2E endpoint range | — | {'PASS' if v2_qc.get('q2_endpoint_pass') else 'FAIL'} |",
        f"| Q3 clavulanic | {v1_qc.get('pos_ctrl_median_pct', '?')}% ({'PASS' if v1_qc.get('q3_pass') else 'FAIL'}) | "
        f"{v2_qc.get('pos_ctrl_median_pct', '?')}% ({'PASS' if v2_qc.get('q3_pass') else 'FAIL'}) |",
        f"| Scoring mode | slope | {v2.get('scoring_mode', 'endpoint')} |",
        f"| Timing stagger | {v1.get('timing_stagger_min', '?')} min | {v2.get('timing_stagger_min', '?')} min |",
        "",
        "---",
        "",
        "## Compound calls",
        "",
        "### v1 (slope-only) — superseded",
        "",
        "| ID | Median % | Label |",
        "|----|----------|-------|",
    ]
    for cid, pct, label in v1_rows:
        lines.append(f"| {cid} | {pct:.1f} | `{label}` |")
    if not v1_rows:
        lines.append("| — | — | — |")

    lines.extend(
        [
            "",
            "### v2 (endpoint) — active",
            "",
            "| ID | Median % | Label |",
            "|----|----------|-------|",
        ]
    )
    for cid, pct, label in v2_rows:
        lines.append(f"| {cid} | {pct:.1f} | `{label}` |")
    if not v2_rows:
        lines.append("| — | — | — |")

    v1_hits = {cid for cid, _, lab in v1_rows if lab in {"confirmed_hit", "surprise_hit", "novel_hit"}}
    v2_hits = {cid for cid, _, lab in v2_rows if lab in {"confirmed_hit", "surprise_hit", "novel_hit"}}

    lines.extend(
        [
            "",
            "---",
            "",
            "## What changed v1 → v2",
            "",
            f"- **Hits in v1 not in v2:** {', '.join(sorted(v1_hits - v2_hits)) or '—'}",
            f"- **Hits in v2 not in v1:** {', '.join(sorted(v2_hits - v1_hits)) or '—'}",
            f"- **Failed wells (v2):** {len(v2.get('failed_wells', []))} sample wells outside 0–150% endpoint score",
            "",
            "Tier-1 inhibitors (T1262, T14081) and most substrates scored as hits on v1 slopes but **failed**",
            "endpoint QC in v2 (A490 above vehicle at aligned read — stagger artifact, not super-activation).",
            "",
            "---",
            "",
            "## Figures",
            "",
            "See [`figures/`](figures/) and [`figure_comparison.md`](figure_comparison.md).",
            "",
            "| Figure | Takeaway |",
            "|--------|----------|",
            "| Endpoint bars | Fewer callable compounds; pos ctrl ~83%; surprise hits T1005/T0224 only |",
            "| Stagger timeline | Same as before — 16 min span drives timing artifacts |",
            "| Decision tree | Q2 slope FAIL → endpoint branch; Q3 PASS @ 83% |",
            "| t-SNE | Unchanged — chemical-space rationale for R2 picks |",
            "| R2 vs R3 plates | Unchanged — layout comparison for human multichannel nitrocefin retest plate |",
            "",
            "---",
            "",
            "## Recommended next steps",
            "",
            "1. **Human multichannel nitrocefin addition** — add nitrocefin to all wells at once on substrate priors + tier-1 inhibitors.",
            "2. **Round 3** — kinetics validation plate already designed from v1 calls; revisit picks using v2 skepticism.",
            "3. **Do not advance dose-response** on T1005/T0224 until human multichannel nitrocefin addition confirms inhibition vs delayed substrate turnover.",
            "",
        ]
    )
    out_path.write_text("\n".join(lines))


def write_figure_comparison(out_path: Path) -> None:
    pvj_figs = {
        "r2_endpoint_inhibition_bars_v1gen.png": PVJ_OUT / "r2_endpoint_inhibition_bars_v1gen.png",
        "r2_nitrocefin_stagger_timeline_v1gen.png": PVJ_OUT / "r2_nitrocefin_stagger_timeline_v1gen.png",
        "r2_tsne_over_library_v1gen.png": PVJ_OUT / "r2_tsne_over_library_v1gen.png",
        "r2_vs_r3_plates_presentation_v1.png": PVJ_OUT / "r2_vs_r3_plates_presentation_v1.png",
    }
    v2_map = {
        "r2_endpoint_inhibition_bars_v1gen.png": FIG_DIR / "r2_endpoint_inhibition_bars.png",
        "r2_nitrocefin_stagger_timeline_v1gen.png": FIG_DIR / "r2_nitrocefin_stagger_timeline.png",
        "r2_tsne_over_library_v1gen.png": FIG_DIR / "r2_tsne_over_library.png",
        "r2_vs_r3_plates_presentation_v1.png": FIG_DIR / "r2_vs_r3_plates.png",
    }

    lines = [
        "# Figure comparison — pvjthomas/output vs post-run/v2/figures",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| pvjthomas/output | post-run/v2/figures | Change |",
        "|------------------|---------------------|--------|",
    ]

    for old_name, old_path in pvj_figs.items():
        new_path = v2_map.get(old_name)
        if not old_path.exists():
            lines.append(f"| `{old_name}` | `{new_path.name if new_path else '?'}` | Old file missing |")
            continue
        if not new_path or not new_path.exists():
            lines.append(f"| `{old_name}` | — | Not regenerated |")
            continue
        old_sz = old_path.stat().st_size
        new_sz = new_path.stat().st_size
        delta_pct = ((new_sz - old_sz) / old_sz * 100) if old_sz else 0
        if old_name.startswith("r2_endpoint"):
            change = "**Major** — v2 endpoint data: 3 compounds + pos ctrl vs 9+ bars in old chart (v1 EDA mislabeled as endpoint but used slope scores)"
        elif old_name.startswith("r2_nitrocefin"):
            change = "**Minimal** — same timing JSON; layout may differ slightly"
        elif old_name.startswith("r2_tsne"):
            change = "**None expected** — same library embedding and R2 compound picks"
        elif old_name.startswith("r2_vs_r3"):
            change = "**Minimal** — same plate maps; caption/legend unchanged"
        else:
            change = "See notes"
        lines.append(
            f"| `{old_name}` ({old_sz:,} B) | `{new_path.name}` ({new_sz:,} B, {delta_pct:+.0f}%) | {change} |"
        )

    lines.extend(
        [
            "",
            "## New in v2 bundle",
            "",
            "- `r2_decision_tree_multichannel_nitrocefin.png` — Q3 label updated to **83.3%** (v2 endpoint pos ctrl), not 107.7%",
            "- [`conclusions.md`](../conclusions.md) — narrative tied to v2 decision report",
            "",
        ]
    )
    out_path.write_text("\n".join(lines))


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    _apply_slide_style()

    plot_endpoint_bars(FIG_DIR / "r2_endpoint_inhibition_bars.png")
    plot_nitrocefin_timeline(FIG_DIR / "r2_nitrocefin_stagger_timeline.png")
    stitch_r2_vs_r3()
    shutil.copy2(
        REPO / "data" / "screens" / "demo" / "r2_vs_r3_plates.png",
        FIG_DIR / "r2_vs_r3_plates.png",
    )

    dt_script = REPO / "ml" / "scripts" / "generate_hackathon_decision_tree_figure.py"
    subprocess.run(
        [
            sys.executable,
            str(dt_script),
            "--output",
            str(FIG_DIR / "r2_decision_tree_multichannel_nitrocefin.png"),
            "--eda-json",
            str(V2_EDA),
        ],
        check=True,
        cwd=REPO,
    )

    tsne_script = REPO / "ml" / "scripts" / "generate_hackathon_tsne_figures.py"
    tsne_dest = FIG_DIR / "r2_tsne_over_library.png"
    tsne_src = PVJ_OUT / "r2_tsne_over_library_v1gen.png"
    try:
        subprocess.run([sys.executable, str(tsne_script)], check=True, cwd=REPO)
        if tsne_src.exists():
            shutil.copy2(tsne_src, tsne_dest)
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"Note: t-SNE regeneration skipped ({exc}); copying existing pvjthomas/output figure")
        if tsne_src.exists():
            shutil.copy2(tsne_src, tsne_dest)
        else:
            print(f"Warning: missing {tsne_src}")

    v1 = _load_eda(V1_EDA)
    v2 = _load_eda(V2_EDA)
    write_conclusions(v1, v2, V2_DIR / "conclusions.md")
    write_figure_comparison(V2_DIR / "figure_comparison.md")

    manifest = {
        "analysis_version": "v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "figures": {name: f"data/screens/2/post-run/v2/figures/{name}" for name in FIGURES},
        "conclusions": "data/screens/2/post-run/v2/conclusions.md",
        "figure_comparison": "data/screens/2/post-run/v2/figure_comparison.md",
    }
    (FIG_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    for path in sorted(FIG_DIR.glob("*")):
        print(f"Wrote {path.relative_to(REPO)} ({path.stat().st_size:,} bytes)")
    for doc in (V2_DIR / "conclusions.md", V2_DIR / "figure_comparison.md"):
        print(f"Wrote {doc.relative_to(REPO)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
