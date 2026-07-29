#!/usr/bin/env python3
"""Build data/screens/3/v{N} — Run 3 plates.

Versions:
  v1 — 8 compounds from v5 minus T1005; col 8 empty (active plate design)
  v2 — DEPRECATED — 6-compound alternate layout (history only)

Incremental steps (--only):
  compounds | csv | plate_map | images | manifest | rationale | all
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "ml"))

from analysis.plate_viz import load_and_render  # noqa: E402
from pvjthomas.plates import (  # noqa: E402
    R3_COLUMN_STRIP_BANDS,
    R3_CONTROL_ROW,
    generate_plate_map_from_file,
    write_compound_list_csv,
    write_plate_map,
)

V5 = REPO / "data/screens/2/v5"
OUTPUT = REPO / "pvjthomas/output"
R2_EDA = REPO / "data/screens/2/post-run/v2/analysis/r2_round_summary_eda.json"
R2_KINETICS = REPO / "data/screens/2/post-run/v2/analysis/r2_kinetics_annotated.csv"

# Run 3 v2 — explicit selection (order → column-strip layout).
# Cut expected tier-1 hits + expected substrate; keep surprises/novels; add unknowns.
R3_V2_COMPOUND_IDS: tuple[str, ...] = (
    "T1008",  # surprise_hit — substrate retest
    "T0224",  # surprise_hit — substrate retest
    "T0138",  # novel_hit — diverse unknown
    "T1005",  # surprise_hit on substrate prior — @ col 8 (slot 4)
    "T8390",  # borderline — diverse unknown
    "T0198",  # new tier-3 pick — not in Run 2
)

R3_V2_RUN2_LABELS: dict[str, dict[str, str]] = {
    "T1008": {"run2_label": "surprise_hit", "selection_reason": "substrate → inhibition retest"},
    "T0224": {"run2_label": "surprise_hit", "selection_reason": "substrate → inhibition retest"},
    "T0138": {"run2_label": "novel_hit", "selection_reason": "diverse unknown with signal"},
    "T1005": {"run2_label": "surprise_hit", "selection_reason": "substrate prior, inhib signal in R2"},
    "T8390": {"run2_label": "borderline", "selection_reason": "diverse unknown, weak signal"},
    "T0198": {"run2_label": "new", "selection_reason": "tier-3 diverse, not screened in R2"},
}

R3_V2_CUT_FROM_V1: tuple[str, ...] = (
    "T1262",
    "T6685",
    "T14081",
    "T0985",
)


@dataclass(frozen=True)
class ScreenVersion:
    version: int
    drop_compound_ids: tuple[str, ...]
    include_compound_ids: tuple[str, ...] | None
    column_strip_bands: list[dict] | None
    supersedes: str
    note: str
    manifest_note: str
    rationale_title: str
    rationale_diff: list[str]


VERSIONS: dict[int, ScreenVersion] = {
    1: ScreenVersion(
        version=1,
        drop_compound_ids=("T1005",),
        include_compound_ids=None,
        column_strip_bands=R3_COLUMN_STRIP_BANDS,
        supersedes="data/screens/2/v5/compound_list.json",
        note=(
            "Round 3 v1 — 8 discovery compounds; 6 QC controls (vehicle removed vs v5); "
            "column-strip bands skip col 8 (former Amoxicillin column)."
        ),
        manifest_note=(
            "Run 3 v1 — 8 compounds × triplicate + 6 QC controls; col 8 empty"
        ),
        rationale_title="legacy confirmation plate (8 compounds, col 8 empty)",
        rationale_diff=[
            "| Compounds | 9 (v5) | **8** (T1005 dropped) |",
            "| Col 8 | T1005 | **Empty** |",
        ],
    ),
    2: ScreenVersion(
        version=2,
        drop_compound_ids=(),
        include_compound_ids=R3_V2_COMPOUND_IDS,
        column_strip_bands=None,
        supersedes="data/screens/3/v1/compound_list.json",
        note=(
            "Round 3 v2 — cut expected tier-1 hits and expected substrates; "
            "retest surprise/novel/borderline compounds in triplicate; "
            "add T1005 (R2 surprise) + T0198 (new tier-3 unknown). 6 QC controls, no vehicle."
        ),
        manifest_note=(
            "Run 3 v2 — 6 compounds × triplicate + 6 QC controls; "
            "surprise/novel/borderline focus; T1005 @ B8/D8/F8; T0198 new"
        ),
        rationale_title="surprise & unknown retest plate (6 compounds)",
        rationale_diff=[
            "| Selection policy | v1 mixed | **Cut expected ±, add unknowns** |",
            "| Compounds | 8 | **6** (4 cut, 1 re-added, 1 new) |",
            "| Cut (expected +) | T1262, T6685, T14081 on v1 | **Removed** |",
            "| Cut (expected −) | T0985 on v1 | **Removed** |",
            "| Add | — | **T1005** (surprise), **T0198** (new) |",
        ],
    ),
}


def _v5_compounds_by_id() -> dict[str, dict]:
    v5 = json.loads((V5 / "compound_list.json").read_text())
    return {c["compound_id"]: copy.deepcopy(c) for c in v5["compounds"]}


def _build_t0198_compound() -> dict:
    """Tier-3 compound not on Run 2 v5 plate."""
    refs_path = REPO / "data/compound_literature/refs/T0198.json"
    ref = json.loads(refs_path.read_text()) if refs_path.exists() else {}
    assay = ref.get("assay_recommendations", {}).get("tem1_nitrocefin", {})
    conc = float(assay.get("screen_conc_uM", 50))
    return {
        "compound_id": "T0198",
        "name": "Ceftiofur sodium",
        "bucket": "diverse_pick",
        "functional_class": "unknown",
        "screen_conc_uM": conc,
        "working_solution_uM": conc * 10,
        "screen_conc_source": assay.get("screen_conc_source", "project_default"),
        "expected_at_screen_conc": "uncertain",
        "source_plate": "PHD215176",
        "source_well": "a3",
        "refs_file": "data/compound_literature/refs/T0198.json",
        "concentration_rule": 3,
        "screen_rationale": assay.get(
            "screen_rationale",
            "Project default; tier-3 diverse pick not screened in Run 2.",
        ),
        "concentration_reference": {
            "concentration_rule": 3,
            "screen_conc_source": "project_default",
            "refs_file": "data/compound_literature/refs/T0198.json",
            "literature_search_at": "2026-07-26T01:35:51Z",
            "evidence_type": "project_default",
            "note": "Tier-3 docking/diverse candidate; not on Run 2 plate.",
        },
    }


def _resolve_compound(compound_id: str, v5_by_id: dict[str, dict]) -> dict:
    if compound_id in v5_by_id:
        return copy.deepcopy(v5_by_id[compound_id])
    if compound_id == "T0198":
        return _build_t0198_compound()
    raise KeyError(f"Unknown compound_id {compound_id!r} — add builder or v5 entry")


def _build_compound_list(cfg: ScreenVersion) -> dict:
    v5 = json.loads((V5 / "compound_list.json").read_text())
    v5_by_id = _v5_compounds_by_id()

    if cfg.include_compound_ids is not None:
        compounds = [_resolve_compound(cid, v5_by_id) for cid in cfg.include_compound_ids]
        labels = R3_V2_RUN2_LABELS if cfg.version == 2 else {}
        for i, compound in enumerate(compounds, start=1):
            compound["slot"] = i
            if meta := labels.get(compound["compound_id"]):
                compound.update(meta)
    else:
        compounds = [c for c in v5["compounds"] if c["compound_id"] not in cfg.drop_compound_ids]
        for i, compound in enumerate(compounds, start=1):
            compound["slot"] = i

    compound_list = {
        **{
            k: v
            for k, v in v5.items()
            if k not in ("compounds", "rationale_doc", "note", "column_strip_bands")
        },
        "run": 3,
        "round": 3,
        "version": cfg.version,
        "version_label": f"r3-discovery-v{cfg.version}",
        "compound_count": len(compounds),
        "supersedes": cfg.supersedes,
        "rationale_doc": f"pvjthomas/runs/3/v{cfg.version}/selection_rationale.md",
        "layout": "column_strip",
        "control_row": R3_CONTROL_ROW,
        "note": cfg.note,
        "compounds": compounds,
    }
    if cfg.column_strip_bands is not None:
        compound_list["column_strip_bands"] = cfg.column_strip_bands
    if cfg.version == 2:
        compound_list["selection_policy"] = {
            "cut_expected_positive": list(R3_V2_CUT_FROM_V1[:3]),
            "cut_expected_negative": ["T0985"],
            "keep": ["T1008", "T0224", "T0138", "T8390"],
            "add_r2_surprise": ["T1005"],
            "add_new_unknown": ["T0198"],
            "replicates_per_compound": 3,
        }
    return compound_list


def _r2_endpoint_by_well() -> dict[str, float]:
    last_t: dict[str, float] = defaultdict(float)
    endpoint: dict[str, float] = {}
    if not R2_KINETICS.exists():
        return endpoint
    with R2_KINETICS.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("wavelength_nm") != "490":
                continue
            well, t = row["well"], float(row["time_s"])
            if t >= last_t[well]:
                last_t[well] = t
                endpoint[well] = float(row["absorbance_a490"])
    return endpoint


def _r2_prior_context(compound_list: dict) -> dict[str, dict]:
    """Per-compound Run 2 wells, labels, and long-endpoint absorbance."""
    if not R2_EDA.exists():
        return {}
    eda = json.loads(R2_EDA.read_text())
    failed = set(eda.get("failed_wells", []))
    r2_pm = json.loads((V5 / "plate_map.json").read_text())
    endpoint = _r2_endpoint_by_well()

    r2_wells: dict[str, list[str]] = defaultdict(list)
    for well, data in r2_pm["wells"].items():
        if cid := data.get("compound_id"):
            r2_wells[cid].append(well)

    out: dict[str, dict] = {}
    for compound in compound_list["compounds"]:
        cid = compound["compound_id"]
        wells = sorted(r2_wells.get(cid, []))
        comp_eda = eda.get("compounds", {}).get(cid, {})
        ok = [w for w in wells if w not in failed]
        ends_ok = [endpoint[w] for w in ok if w in endpoint]
        out[cid] = {
            "wells": wells,
            "failed": [w for w in wells if w in failed],
            "label": comp_eda.get("label", "—"),
            "median_pct": comp_eda.get("median_pct_inhibition"),
            "A490_end": round(statistics.median(ends_ok), 3) if ends_ok else None,
            "well_pcts": [
                (w["well"], w["pct_inhibition"], w["well"] in failed)
                for w in comp_eda.get("wells", [])
            ],
        }
    return out


def _format_r2_v1_table(
    compound_list: dict,
    r2_prior: dict[str, dict],
    r3_wells: dict[str, list[str]] | None = None,
    *,
    standalone: bool = False,
) -> list[str]:
    eda_link = (
        "[`r2_round_summary_eda.json`](../../2/post-run/v2/analysis/r2_round_summary_eda.json)"
        if standalone
        else "[`r2_round_summary_eda.json`](../../../../data/screens/2/post-run/v2/analysis/r2_round_summary_eda.json)"
    )
    lines = [
        "## Compound table (concentrations, class, R2 history)" if not standalone else "",
        "" if not standalone else None,
        (
            "All eight compounds were on **Run 2 v5** at the concentrations below "
            "(T1262 @ 1 µM in both rounds). R2 post-run analysis: "
            f"{eda_link}. Long endpoint = median **A490 at last kinetic read (~900 s)** "
            "over R2 replicate wells **not** flagged failed by enzyme QC."
        ),
        "",
        "| Slot | ID | Name | Bucket | Class | Screen µM | Work µM | R2 wells | R2 QC fail | "
        "R2 label | R2 % inhib (med) | R2 A490 end (med)"
        + (" | R3 wells |" if r3_wells is not None else " |"),
        "|------|-----|------|--------|-------|-----------|---------|----------|------------|"
        "----------|------------------|-------------------"
        + ("|----------|" if r3_wells is not None else "|"),
    ]
    lines = [ln for ln in lines if ln is not None]

    def _pct_markers(cid: str, pct: float | None) -> str:
        if pct is None:
            return "—"
        if cid in ("T1008", "T0224", "T0138") and r2_prior.get(cid, {}).get("failed"):
            return f"{pct}†"
        return str(pct)

    def _a_end_markers(cid: str, a_end: float | None) -> str:
        if a_end is None:
            return "—"
        if cid == "T0224":
            return f"{a_end:.3f}‡"
        return f"{a_end:.3f}"

    for compound in compound_list["compounds"]:
        cid = compound["compound_id"]
        prior = r2_prior.get(cid, {})
        wells = ", ".join(prior.get("wells", [])) or "—"
        fail = ", ".join(prior.get("failed", [])) or "—"
        pct_s = _pct_markers(cid, prior.get("median_pct"))
        a_end_s = _a_end_markers(cid, prior.get("A490_end"))
        if r3_wells is not None:
            r3 = ", ".join(sorted(r3_wells.get(cid, []))) or "—"
            lines.append(
                f"| {compound['slot']} | {cid} | {compound['name']} | {compound['bucket']} | "
                f"{compound['functional_class']} | {compound['screen_conc_uM']} | "
                f"{compound['working_solution_uM']} | {wells} | {fail} | {prior.get('label', '—')} | "
                f"{pct_s} | {a_end_s} | {r3} |"
            )
        else:
            lines.append(
                f"| {compound['slot']} | {cid} | {compound['name']} | {compound['bucket']} | "
                f"{compound['functional_class']} | {compound['screen_conc_uM']} | "
                f"{compound['working_solution_uM']} | {wells} | {fail} | {prior.get('label', '—')} | "
                f"{pct_s} | {a_end_s} |"
            )

    if standalone:
        lines.extend(
            [
                "",
                "**Footnotes**",
                "",
                "- † Median % inhibition uses all R2 replicate wells in EDA; only **one** non-failed rep "
                "for T1008 (F10), T0224 (C5), T0138 (C3, E3).",
                "- ‡ C5 alone shows strong inhibition (A490 ≈ 0.06); failed reps E5/G5 had high endpoint "
                "absorbance — treat Meropenem as ambiguous pending R3 retest.",
                "- R2 enzyme QC failed (wells Q2, Q3); nine sample wells flagged `failed_wells` — "
                "interpret single-rep hits cautiously.",
                "",
                "### Per-replicate R2 % inhibition",
                "",
                "| ID | R2 wells | % inhib per well |",
                "|----|----------|------------------|",
            ]
        )
        rep_labels = {
            "T1262": "B2, D2, F2",
            "T6685": "B4, D4, F4",
            "T14081": "B6, D6, F6",
            "T1008": "B10†, D10†, F10",
            "T0224": "C5, E5†, G5†",
            "T0985": "C9, E9†, G9†",
            "T0138": "C3, E3, G3†",
            "T8390": "C7†, E7†, G7",
        }
        rep_pcts = {
            "T1262": "84.6, 53.8, 92.3",
            "T6685": "130.8, 84.6, 107.7",
            "T14081": "61.5, 76.9, 30.8",
            "T1008": "failed, failed, 76.9",
            "T0224": "100.0, failed, failed",
            "T0985": "30.8, failed, failed",
            "T0138": "100.0, 23.1, failed",
            "T8390": "failed, failed, 30.8",
        }
        for compound in compound_list["compounds"]:
            cid = compound["compound_id"]
            lines.append(f"| {cid} | {rep_labels[cid]} | {rep_pcts[cid]} |")
        lines.extend(
            [
                "",
                "† = R2 QC failed well",
                "",
                "### Dropped from v1 (was on R2 v5)",
                "",
                "| ID | Name | R2 label | R2 wells | Why dropped |",
                "|----|------|----------|----------|-------------|",
                "| T1005 | Amoxicillin | surprise_hit (ambiguous) | B8, D8, F8 | Col 8 left empty; "
                "R2 kinetics messy — not a clean inhibitor retest candidate |",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Full table with footnotes: "
                "[`compound_table.md`](../../../../data/screens/3/v1/compound_table.md).",
                "",
            ]
        )
    return lines


def _write_v1_compound_table(
    screen_dir: Path,
    compound_list: dict,
    plate_map: dict,
    r2_prior: dict[str, dict],
) -> Path:
    r3_wells: dict[str, list[str]] = defaultdict(list)
    for well, data in plate_map["wells"].items():
        if cid := data.get("compound_id"):
            r3_wells[cid].append(well)

    lines = [
        "# Run 3 v1 — compound table",
        "",
        "**Round:** 3 · **Version:** 1 (`r3-discovery-v1`)  ",
        "**Plate map:** [`plate_map.json`](plate_map.json) · "
        "**Compound list:** [`compound_list.json`](compound_list.json)  ",
        "**Rationale:** [`selection_rationale.md`](../../../pvjthomas/runs/3/v1/selection_rationale.md)",
        "",
        "---",
        "",
        * _format_r2_v1_table(compound_list, r2_prior, r3_wells, standalone=True),
    ]
    path = screen_dir / "compound_table.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def make_steps(cfg: ScreenVersion):
    screen_dir = _screen_dir(cfg.version)
    runs_dir = _runs_dir(cfg.version)

    def step_compounds() -> Path:
        screen_dir.mkdir(parents=True, exist_ok=True)
        path = screen_dir / "compound_list.json"
        path.write_text(json.dumps(_build_compound_list(cfg), indent=2) + "\n")
        return path

    def step_csv() -> Path:
        compound_list = json.loads((screen_dir / "compound_list.json").read_text())
        return write_compound_list_csv(compound_list, screen_dir / "compound_list.csv")

    def step_plate_map() -> Path:
        compound_path = screen_dir / "compound_list.json"
        plate_map_path = generate_plate_map_from_file(compound_path, screen_dir / "plate_map.json")
        plate_map = json.loads(plate_map_path.read_text())
        plate_map["rationale_doc"] = f"pvjthomas/runs/3/v{cfg.version}/selection_rationale.md"
        plate_map["rationale_doc_active"] = "pvjthomas/selection_rationale.md"
        return write_plate_map(plate_map, plate_map_path)

    def step_images() -> list[Path]:
        plate_json = screen_dir / "plate_map.json"
        outputs = [
            load_and_render(plate_json, color_by="sample_type"),
            load_and_render(plate_json, screen_dir / "plate_map_by_compound.png", color_by="compound"),
            load_and_render(
                plate_json, screen_dir / "plate_map_concentrations.png", color_by="concentration"
            ),
        ]
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT / f"plate_map_r3_v{cfg.version}.json").write_text(plate_json.read_text())
        return outputs

    def step_manifest() -> Path:
        plate_map = json.loads((screen_dir / "plate_map.json").read_text())
        prev = (
            f"data/screens/3/v{cfg.version - 1}/manifest.json"
            if cfg.version > 1
            else "data/screens/2/v5/manifest.json"
        )
        manifest = {
            "run": 3,
            "round": 3,
            "version": cfg.version,
            "label": f"r3-discovery-v{cfg.version}",
            "created_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
            "author": "pvjthomas",
            "status": "deprecated" if cfg.version == 2 else "pending_signoff",
            "supersedes": prev,
            "note": cfg.manifest_note,
            "description": plate_map.get("description"),
            "layout": "column_strip",
            "control_policy": {
                "vehicle": 0,
                "no_tem1": 3,
                "positive_T19860": 3,
                "change_from_v5": "vehicle controls removed",
            },
            "files": {
                "compound_list": f"{_screen_data_prefix(cfg.version)}/compound_list.json",
                "compound_list_csv": f"{_screen_data_prefix(cfg.version)}/compound_list.csv",
                "plate_map": f"{_screen_data_prefix(cfg.version)}/plate_map.json",
                "plate_map_png": f"{_screen_data_prefix(cfg.version)}/plate_map.png",
                "plate_map_by_compound_png": f"{_screen_data_prefix(cfg.version)}/plate_map_by_compound.png",
                "plate_map_concentrations_png": f"{_screen_data_prefix(cfg.version)}/plate_map_concentrations.png",
                "selection_rationale": f"pvjthomas/runs/3/v{cfg.version}/selection_rationale.md",
                "active_plate_map": "data/plate_map_r3.json",
                "active_selection_rationale": "pvjthomas/selection_rationale.md",
            },
        }
        if cfg.version == 2:
            manifest.update(
                {
                    "deprecated_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d"),
                    "deprecated_reason": (
                        "Alternate 6-compound layout superseded; Run 3 v1 is the active plate design. "
                        "Do not schedule on robot."
                    ),
                    "superseded_by": "data/screens/3/v1/manifest.json",
                    "files": {
                        **manifest["files"],
                        "deprecated_notice": "data/screens/3/v2-deprecated/DEPRECATED.md",
                    },
                }
            )
            manifest["note"] = (
                "DEPRECATED — Run 3 v2 — 6 compounds × triplicate + 6 QC controls; kept for history only"
            )
        elif cfg.version == 1:
            manifest["note"] = (
                "Run 3 v1 (active) — 8 compounds × triplicate + 6 QC controls "
                "(no vehicle vs v5); column-strip bands skip col 8; v2 deprecated"
            )
            manifest["files"]["compound_table"] = "data/screens/3/v1/compound_table.md"
        path = screen_dir / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        return path

    def step_rationale() -> Path:
        runs_dir.mkdir(parents=True, exist_ok=True)
        compound_list = json.loads((screen_dir / "compound_list.json").read_text())
        plate_map = json.loads((screen_dir / "plate_map.json").read_text())
        prev_label = f"v{cfg.version - 1}" if cfg.version > 1 else "Run 2 v5"

        lines = [
            f"# Round 3 / version {cfg.version} — {cfg.rationale_title}",
            "",
        ]
        if cfg.version == 2:
            lines.extend(
                [
                    "> **DEPRECATED** — Do not use. Active design is "
                    "[Run 3 v1](../v1/selection_rationale.md). See "
                    "[`DEPRECATED.md`](../../../../data/screens/3/v2-deprecated/DEPRECATED.md).",
                    "",
                    f"**Round:** 3 · **Version:** {cfg.version} (`r3-discovery-v{cfg.version}`)  ",
                    "**Status:** deprecated  ",
                    f"**Supersedes:** `{cfg.supersedes}`  ",
                    "**Superseded by:** [`data/screens/3/v1/`](../../../../data/screens/3/v1/)  ",
                    f"**Canonical list:** [`compound_list.json`](../../../../{_screen_data_prefix(cfg.version)}/compound_list.json)",
                ]
            )
        else:
            lines.extend(
                [
                    f"**Round:** 3 · **Version:** {cfg.version} (`r3-discovery-v{cfg.version}`)  ",
                    "**Status:** pending sign-off  ",
                    f"**Supersedes:** `{cfg.supersedes}`  ",
                    f"**Canonical list:** [`compound_list.json`](../../../../{_screen_data_prefix(cfg.version)}/compound_list.json)",
                    "",
                    "> **Note:** Run 3 v2 is "
                    "[deprecated](../../../../data/screens/3/v2-deprecated/DEPRECATED.md). This v1 plate is the active design.",
                ]
            )
        lines.extend(
            [
                "",
                "---",
                "",
                f"## What changed from {prev_label}",
                "",
                "| Aspect | Prior | This version |",
                "|--------|-------|--------------|",
                "| Vehicle controls | 3 @ B3/B7/C11 (v5) | **Removed** |",
                "| QC controls | — | **6** (3× no-TEM-1 + 3× clavulanic) |",
                *cfg.rationale_diff,
                "",
            ]
        )

        if cfg.version == 1:
            r2_prior = _r2_prior_context(compound_list)
            _write_v1_compound_table(screen_dir, compound_list, plate_map, r2_prior)
            lines.extend(["---", ""])
            lines.extend(
                _format_r2_v1_table(compound_list, r2_prior, standalone=False)
            )

        if cfg.version == 2:
            lines.extend(
                [
                    "---",
                    "",
                    "## Selection policy",
                    "",
                    "Run 3 v2 follows: **cut expected positives, cut expected negatives, "
                    "retest interesting/unknowns, triplicate everything.**",
                    "",
                    "### Cut from v1",
                    "",
                    "| ID | Name | Run 2 label | Why cut |",
                    "|----|------|-------------|---------|",
                    "| T1262 | Tazobactam | confirmed_hit | Expected tier-1 inhibitor — validated |",
                    "| T6685 | Sulbactam sodium | confirmed_hit | Expected tier-1 inhibitor — validated |",
                    "| T14081 | Enmetazobactam | confirmed_hit | Expected tier-1 inhibitor — validated |",
                    "| T0985 | Oxacillin | likely substrate | Expected negative — behaved as substrate |",
                    "",
                    "### Kept / added",
                    "",
                    "| ID | Name | Run 2 label | Why on plate |",
                    "|----|------|-------------|--------------|",
                    "| T1008 | Cephalexin | surprise_hit | Substrate that inhibited — retest |",
                    "| T0224 | Meropenem | surprise_hit | Substrate that inhibited — retest |",
                    "| T0138 | Cefpiramide | novel_hit | Diverse unknown with signal |",
                    "| T1005 | Amoxicillin | surprise_hit | Substrate prior but inhibited in R2 |",
                    "| T8390 | Cefazolin | borderline | Weak/ambiguous — retest |",
                    "| T0198 | Ceftiofur sodium | **new** | Tier-3 diverse — not screened in R2 |",
                    "",
                ]
            )

        wells_by_cid: dict[str, list[str]] = {}
        for well, data in plate_map["wells"].items():
            if cid := data.get("compound_id"):
                wells_by_cid.setdefault(cid, []).append(well)

        lines.extend(
            [
                "---",
                "",
                "## Compounds & well layout",
                "",
                "| Slot | ID | Name | µM | Wells (triplicate) |",
                "|------|-----|------|-----|-------------------|",
            ]
        )
        for compound in compound_list["compounds"]:
            cid = compound["compound_id"]
            well_str = ", ".join(sorted(wells_by_cid.get(cid, [])))
            lines.append(
                f"| {compound['slot']} | {cid} | {compound['name']} | "
                f"{compound['screen_conc_uM']} | {well_str} |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## Controls",
                "",
                "| Role | Wells |",
                "|------|-------|",
                "| no-TEM-1 | D3, D7, E11 |",
                "| Clavulanic acid (T19860) @ 50 µM | F3, F7, G11 |",
                "",
                "```bash",
                f"python ml/scripts/build_screen3.py --version {cfg.version}",
                f"python ml/scripts/build_screen3.py --version {cfg.version} --only plate_map images",
                "```",
            ]
        )
        path = runs_dir / "selection_rationale.md"
        path.write_text("\n".join(lines) + "\n")
        return path

    return {
        "compounds": step_compounds,
        "csv": step_csv,
        "plate_map": step_plate_map,
        "images": step_images,
        "manifest": step_manifest,
        "rationale": step_rationale,
    }


def _screen_subdir(version: int) -> str:
    """On-disk folder name; deprecated v2 lives outside the normal v{N} path."""
    if version == 2:
        return "v2-deprecated"
    return f"v{version}"


def _screen_data_prefix(version: int) -> str:
    return f"data/screens/3/{_screen_subdir(version)}"


def _screen_dir(version: int) -> Path:
    return REPO / "data" / "screens" / "3" / _screen_subdir(version)


def _runs_dir(version: int) -> Path:
    return REPO / "pvjthomas/runs" / "3" / f"v{version}"


ALL_ORDER = ("compounds", "csv", "plate_map", "images", "manifest", "rationale")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Run 3 screen artifacts incrementally.")
    parser.add_argument("--version", type=int, choices=sorted(VERSIONS), default=1)
    parser.add_argument(
        "--only",
        choices=[*ALL_ORDER, "all"],
        default="all",
        help="Run a single step or all steps (default: all)",
    )
    args = parser.parse_args()

    cfg = VERSIONS[args.version]
    steps = make_steps(cfg)
    to_run = ALL_ORDER if args.only == "all" else (args.only,)
    for name in to_run:
        result = steps[name]()
        if isinstance(result, list):
            for path in result:
                print(path)
        else:
            print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
