"""Audit scattered Round 2 (Run 2) artifacts and recommend consolidation.

Canonical post-run home: ``data/screens/2/post-run/``
Pre-run design home: ``data/screens/2/v5/``
Agent/analysis promotion targets: ``data/kinetics_r2.csv``, ``data/plate_map_r2.json``,
``data/assay/run_2_summary.json``
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from analysis.run2_paths import (
    R2_ANALYSIS_DIR,
    R2_GEN5_PDF,
    R2_KINETICS_ANNOTATED_CSV,
    R2_KINETICS_CSV,
    R2_KINETICS_CSV_PROMOTED,
    R2_LLM_CONTEXT_JSON,
    R2_LLM_CONTEXT_MD,
    R2_PARSED_JSON,
    R2_PATTERN_SUMMARY_JSON,
    R2_PATTERN_SUMMARY_MD,
    R2_POST_RUN_DIR,
    R2_ROUND_SUMMARY_EDA_JSON,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
SCREENS_DIR = DATA_DIR / "screens"
POST_RUN_DIR = R2_POST_RUN_DIR
V5_DIR = SCREENS_DIR / "2" / "v5"
PVJ_OUTPUT = REPO_ROOT / "pvjthomas" / "output"
ASSAY_DIR = DATA_DIR / "assay"
PLATEREADER_DIR = REPO_ROOT / "mastermix" / "data" / "platereader"


class Relevance(str, Enum):
    REQUIRED = "required_for_analysis"
    USEFUL = "useful_derivative"
    DESIGN = "pre_run_design"
    DUPLICATE = "duplicate_working_copy"
    ARCHIVE = "superseded_version"
    UNRELATED = "unrelated_or_unclear"
    MISSING = "missing_expected"


class Action(str, Enum):
    MOVE_TO_POST_RUN = "move_to_post_run"
    PROMOTE_TO_DATA = "promote_to_data"
    KEEP = "keep_in_place"
    DEDUPE = "dedupe_do_not_move"
    ARCHIVE_OK = "archive_ok"
    GENERATE = "generate_from_existing"
    REVIEW = "human_review"


@dataclass
class FileFinding:
    path: str
    exists: bool
    size_bytes: int | None = None
    sha256_prefix: str | None = None
    relevance: str = Relevance.UNRELATED.value
    action: str = Action.REVIEW.value
    suggested_target: str | None = None
    reason: str = ""
    duplicate_of: str | None = None


@dataclass
class AuditReport:
    generated_at: str
    post_run_dir: str
    summary: dict[str, int] = field(default_factory=dict)
    missing_for_decision_tree: list[str] = field(default_factory=list)
    move_recommendations: list[dict[str, str]] = field(default_factory=list)
    keep_recommendations: list[dict[str, str]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_prefix(path: Path, nbytes: int = 65536) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read(nbytes))
        if path.stat().st_size > nbytes:
            h.update(str(path.stat().st_size).encode())
    return h.hexdigest()[:16]


def _finding(
    path: Path,
    *,
    relevance: Relevance,
    action: Action,
    reason: str,
    suggested_target: Path | None = None,
    duplicate_of: Path | None = None,
) -> FileFinding:
    exists = path.exists()
    size = path.stat().st_size if exists and path.is_file() else None
    return FileFinding(
        path=str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
        exists=exists,
        size_bytes=size,
        sha256_prefix=_sha256_prefix(path) if exists and path.is_file() else None,
        relevance=relevance.value,
        action=action.value,
        suggested_target=(
            str(suggested_target.relative_to(REPO_ROOT))
            if suggested_target and suggested_target.is_relative_to(REPO_ROOT)
            else (str(suggested_target) if suggested_target else None)
        ),
        reason=reason,
        duplicate_of=(
            str(duplicate_of.relative_to(REPO_ROOT))
            if duplicate_of and duplicate_of.is_relative_to(REPO_ROOT)
            else (str(duplicate_of) if duplicate_of else None)
        ),
    )


def _glob_findings(
    directory: Path,
    pattern: str,
    *,
    relevance: Relevance,
    action: Action,
    reason: str,
    suggested_target_fn: Callable[[Path], Path | None] | None = None,
) -> list[FileFinding]:
    if not directory.exists():
        return []
    out: list[FileFinding] = []
    for path in sorted(directory.glob(pattern)):
        if not path.is_file():
            continue
        target = suggested_target_fn(path) if suggested_target_fn else None
        out.append(
            _finding(
                path,
                relevance=relevance,
                action=action,
                reason=reason,
                suggested_target=target,
            )
        )
    return out


def _compare_to_canonical(findings: list[FileFinding], canonical_path: Path) -> None:
    if not canonical_path.exists():
        return
    canon_hash = _sha256_prefix(canonical_path)
    for f in findings:
        p = REPO_ROOT / f.path
        if p.resolve() == canonical_path.resolve():
            continue
        if f.sha256_prefix and f.sha256_prefix == canon_hash:
            f.duplicate_of = str(canonical_path.relative_to(REPO_ROOT))
            if f.action == Action.MOVE_TO_POST_RUN.value:
                f.action = Action.DEDUPE.value
                f.reason = f"{f.reason} (byte-identical to canonical copy)"


def audit_run2_data() -> AuditReport:
    """Scan known Run 2 locations and return structured audit findings."""
    findings: list[FileFinding] = []

    # --- Expected decision-tree inputs (may be missing) ---
    expected = [
        (POST_RUN_DIR / "kinetics_r2.csv", "Kinetic CSV for Q1–Q3 analysis"),
        (POST_RUN_DIR / "nitrocefin_timing.json", "Per-well t0 from robot dispense log (Q1T)"),
        (POST_RUN_DIR / "reader_lid_close_utc.txt", "Plate reader lid-close timestamp"),
        (DATA_DIR / "plate_map_r2.json", "Promoted active plate map for analyze_kinetics()"),
        (ASSAY_DIR / "run_2_summary.json", "Decision-tree output summary"),
        (DATA_DIR / "kinetics_r2.csv", "Agent tool path expected by analyze_kinetics(round=2)"),
        (DATA_DIR / "round_summary_r2.json", "Legacy agent round summary path"),
    ]
    missing: list[str] = []
    for path, desc in expected:
        if path.exists():
            findings.append(
                _finding(
                    path,
                    relevance=Relevance.REQUIRED,
                    action=Action.KEEP,
                    reason=f"Present: {desc}",
                )
            )
        else:
            missing.append(f"{path.relative_to(REPO_ROOT)} — {desc}")
            findings.append(
                FileFinding(
                    path=str(path.relative_to(REPO_ROOT)),
                    exists=False,
                    relevance=Relevance.MISSING.value,
                    action=Action.GENERATE.value if "timing" in path.name else Action.REVIEW.value,
                    reason=f"Missing: {desc}",
                )
            )

    # --- Post-run artifacts already in place ---
    for name, reason in [
        ("run_log_exec_tem1_activity_screen_hack_world_22_20260725_230432.txt", "Robot run log"),
        ("r2_timing_log_analysis.md", "Timing budget write-up"),
        ("manifest.json", "Post-run manifest"),
        ("README.md", "Post-run index"),
    ]:
        findings.append(
            _finding(
                POST_RUN_DIR / name,
                relevance=Relevance.REQUIRED,
                action=Action.KEEP,
                reason=reason,
            )
        )

    # --- Consolidated post-run readout (canonical Run 2 layout) ---
    for path, desc in [
        (R2_KINETICS_CSV, "Primary Gen5 kinetic CSV for Run 2 v5"),
        (R2_GEN5_PDF, "Source Gen5 PDF export for Run 2"),
        (R2_KINETICS_ANNOTATED_CSV, "Annotated kinetic CSV (EDA pipeline)"),
        (R2_PARSED_JSON, "Parsed Gen5 PDF JSON (96-well Max V)"),
        (R2_ROUND_SUMMARY_EDA_JSON, "Q1/Q2/Q3 round summary from EDA"),
        (R2_PATTERN_SUMMARY_JSON, "Pattern summary JSON"),
        (R2_PATTERN_SUMMARY_MD, "Pattern summary markdown"),
        (R2_LLM_CONTEXT_JSON, "LLM context bundle"),
        (R2_LLM_CONTEXT_MD, "LLM context markdown"),
    ]:
        if path.exists():
            findings.append(
                _finding(
                    path,
                    relevance=Relevance.REQUIRED if path.parent == POST_RUN_DIR else Relevance.USEFUL,
                    action=Action.KEEP,
                    reason=f"Run 2 post-run: {desc}",
                )
            )
        elif path.parent == R2_ANALYSIS_DIR:
            findings.append(
                _finding(
                    path,
                    relevance=Relevance.USEFUL,
                    action=Action.GENERATE,
                    reason=f"Missing derivative: {desc}; run analyze_kinetics_run() on kinetics_r2.csv",
                )
            )

    # --- Pre-run v5 design (keep) ---
    for fname in [
        "plate_map.json",
        "plate_map.png",
        "plate_map_by_compound.png",
        "compound_list.json",
        "compound_list.csv",
        "kinetic_schedule.json",
        "manifest.json",
    ]:
        p = V5_DIR / fname
        if p.exists():
            findings.append(
                _finding(
                    p,
                    relevance=Relevance.DESIGN,
                    action=Action.KEEP,
                    reason="Pre-run plate design v5 — canonical under data/screens/2/v5/",
                )
            )

    # --- pvjthomas/output working copies ---
    pvj_dupes = [
        ("plate_map_r2_v5.json", V5_DIR / "plate_map.json"),
        ("plate_map_r2_v5.png", V5_DIR / "plate_map.png"),
        ("plate_map_r2_v5_by_compound.png", V5_DIR / "plate_map_by_compound.png"),
        ("compound_list_r2_v5.json", V5_DIR / "compound_list.json"),
        ("kinetic_schedule_r2_v5.json", V5_DIR / "kinetic_schedule.json"),
    ]
    for fname, canonical in pvj_dupes:
        p = PVJ_OUTPUT / fname
        if p.exists():
            findings.append(
                _finding(
                    p,
                    relevance=Relevance.DUPLICATE,
                    action=Action.DEDUPE,
                    reason="Working copy; canonical version lives under data/screens/2/v5/",
                    duplicate_of=canonical,
                )
            )

    # Phase A / concentration tables — not Run 2 post-run
    for fname in [
        "phase_a_report.md",
        "concentration_table.md",
        "concentration_table.json",
        "concentration_literature_run.log",
        "tier1example.md",
        "tier2example.md",
        "status.md",
    ]:
        p = PVJ_OUTPUT / fname
        if p.exists():
            findings.append(
                _finding(
                    p,
                    relevance=Relevance.UNRELATED,
                    action=Action.KEEP,
                    reason="Philip workspace report — not a Run 2 execution artifact",
                )
            )

    # --- Superseded R2 plate versions ---
    for ver in ("v1", "v2", "v3", "v4"):
        ver_dir = SCREENS_DIR / "2" / ver
        if ver_dir.exists():
            findings.append(
                _finding(
                    ver_dir / "manifest.json",
                    relevance=Relevance.ARCHIVE,
                    action=Action.ARCHIVE_OK,
                    reason=f"Superseded Round 2 design {ver}; keep for history",
                )
            )

    # --- Stray root / mastermix plate reader PDFs ---
    root_skill_pdf = REPO_ROOT / "skill_platereader_measure_20260724_231705.pdf"
    if root_skill_pdf.exists():
        findings.append(
            _finding(
                root_skill_pdf,
                relevance=Relevance.UNRELATED,
                action=Action.REVIEW,
                reason=(
                    "Plate reader skill PDF at repo root (~109 KB); smaller than r2_gen5_export.pdf "
                    "(~153 KB) — likely a different/partial read; confirm before moving"
                ),
                suggested_target=POST_RUN_DIR / root_skill_pdf.name,
            )
        )

    findings.extend(
        _glob_findings(
            PLATEREADER_DIR,
            "**/*.pdf",
            relevance=Relevance.UNRELATED,
            action=Action.REVIEW,
            reason="Mastermix platereader skill capture — compare to r2_gen5_export.pdf before consolidating",
        )
    )

    # --- Promotion copies for agent tools ---
    if R2_KINETICS_CSV.exists() and not R2_KINETICS_CSV_PROMOTED.exists():
        findings.append(
            FileFinding(
                path=str(R2_KINETICS_CSV_PROMOTED.relative_to(REPO_ROOT)),
                exists=False,
                relevance=Relevance.MISSING.value,
                action=Action.PROMOTE_TO_DATA.value,
                suggested_target=str(R2_KINETICS_CSV_PROMOTED.relative_to(REPO_ROOT)),
                reason=(
                    "Copy post-run/kinetics_r2.csv to data/kinetics_r2.csv "
                    "for analyze_kinetics(round_number=2)"
                ),
            )
        )

    if (V5_DIR / "plate_map.json").exists() and not (DATA_DIR / "plate_map_r2.json").exists():
        findings.append(
            FileFinding(
                path=str((DATA_DIR / "plate_map_r2.json").relative_to(REPO_ROOT)),
                exists=False,
                relevance=Relevance.MISSING.value,
                action=Action.PROMOTE_TO_DATA.value,
                suggested_target=str((DATA_DIR / "plate_map_r2.json").relative_to(REPO_ROOT)),
                reason="Promote v5 plate map after human sign-off (see pvjthomas/output/status.md)",
            )
        )

    if R2_ROUND_SUMMARY_EDA_JSON.exists() and not (ASSAY_DIR / "run_2_summary.json").exists():
        findings.append(
            _finding(
                ASSAY_DIR / "run_2_summary.json",
                relevance=Relevance.REQUIRED,
                action=Action.PROMOTE_TO_DATA,
                suggested_target=ASSAY_DIR / "run_2_summary.json",
                reason=(
                    "Copy/adapt r2_round_summary_eda.json into data/assay/run_2_summary.json "
                    "after median-scoring pass"
                ),
            )
        )

    # Duplicate detection among CSV copies
    csv_candidates = [R2_KINETICS_CSV, R2_KINETICS_CSV_PROMOTED]
    existing_csvs = [p for p in csv_candidates if p.exists()]
    if len(existing_csvs) > 1:
        _compare_to_canonical(
            [f for f in findings if f.path.endswith(".csv")],
            existing_csvs[0],
        )

    move_recs = [
        {"from": f.path, "to": f.suggested_target, "reason": f.reason}
        for f in findings
        if f.action == Action.MOVE_TO_POST_RUN.value and f.suggested_target
    ]
    keep_recs = [
        {"path": f.path, "reason": f.reason}
        for f in findings
        if f.action in (Action.KEEP.value, Action.DEDUPE.value, Action.ARCHIVE_OK.value)
    ]

    action_counts: dict[str, int] = {}
    for f in findings:
        action_counts[f.action] = action_counts.get(f.action, 0) + 1

    return AuditReport(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        post_run_dir=str(POST_RUN_DIR.relative_to(REPO_ROOT)),
        summary=action_counts,
        missing_for_decision_tree=missing,
        move_recommendations=move_recs,
        keep_recommendations=keep_recs,
        findings=[asdict(f) for f in findings],
    )


def format_audit_markdown(report: AuditReport) -> str:
    """Render audit report as markdown for humans."""
    lines = [
        "# Run 2 data organization audit",
        "",
        f"Generated: {report.generated_at}",
        "",
        "This report lists scattered Round 2 artifacts and recommends whether to consolidate "
        "under [`data/screens/2/post-run/`](../../data/screens/2/post-run/) or leave in place.",
        "",
        "## Executive summary",
        "",
    ]

    if report.move_recommendations:
        lines.append("**Move to `post-run/` (recommended):**")
        for rec in report.move_recommendations:
            lines.append(f"- `{rec['from']}` → `{rec['to']}` — {rec['reason']}")
        lines.append("")
    else:
        lines.append("No file moves recommended — post-run folder looks consolidated.")
        lines.append("")

    if report.missing_for_decision_tree:
        lines.append("**Still missing for decision-tree analysis:**")
        for item in report.missing_for_decision_tree:
            lines.append(f"- `{item}`")
        lines.append("")

    lines.extend(
        [
            "## Action counts",
            "",
            "| Action | Count |",
            "|--------|------:|",
        ]
    )
    for action, count in sorted(report.summary.items()):
        lines.append(f"| `{action}` | {count} |")

    lines.extend(["", "## Detailed findings", ""])
    for f in report.findings:
        if not f.get("exists") and f.get("relevance") != Relevance.MISSING.value:
            continue
        flag = "✓" if f.get("exists") else "✗"
        lines.append(f"### {flag} `{f['path']}`")
        lines.append(f"- **Relevance:** `{f['relevance']}`")
        lines.append(f"- **Action:** `{f['action']}`")
        if f.get("suggested_target"):
            lines.append(f"- **Suggested target:** `{f['suggested_target']}`")
        if f.get("duplicate_of"):
            lines.append(f"- **Duplicate of:** `{f['duplicate_of']}`")
        if f.get("size_bytes") is not None:
            lines.append(f"- **Size:** {f['size_bytes']:,} bytes")
        lines.append(f"- **Reason:** {f['reason']}")
        lines.append("")

    lines.extend(
        [
            "## Suggested promotion commands (manual — not executed by audit)",
            "",
            "```bash",
            "# Agent/analysis promotion (after sign-off)",
            "cp data/screens/2/v5/plate_map.json data/plate_map_r2.json",
            "cp data/screens/2/post-run/kinetics_r2.csv data/kinetics_r2.csv",
            "cp data/screens/2/post-run/v2/analysis/r2_round_summary_eda.json data/assay/run_2_summary.json",
            "```",
            "",
            "Regenerate: `python ml/scripts/audit_run2_data.py`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_audit_report(report: AuditReport | None = None) -> Path:
    """Write markdown + JSON audit artifacts under post-run/."""
    report = report or audit_run2_data()
    POST_RUN_DIR.mkdir(parents=True, exist_ok=True)
    md_path = POST_RUN_DIR / "DATA_ORGANIZATION_AUDIT.md"
    json_path = POST_RUN_DIR / "data_organization_audit.json"
    md_path.write_text(format_audit_markdown(report))
    json_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n")
    return md_path
