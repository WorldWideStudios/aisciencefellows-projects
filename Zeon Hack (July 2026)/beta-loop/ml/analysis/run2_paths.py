"""Canonical paths for Round 2 post-run artifacts."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
SCREENS_DIR = DATA_DIR / "screens"

R2_POST_RUN_DIR = SCREENS_DIR / "2" / "post-run"
R2_PLATE_DESIGN_DIR = SCREENS_DIR / "2" / "v5"

# Active post-run analysis version (endpoint fallback scoring)
R2_ANALYSIS_VERSION = "v2"
R2_V1_DIR = R2_POST_RUN_DIR / "v1"
R2_V2_DIR = R2_POST_RUN_DIR / "v2"

# Primary post-run exports (shared across analysis versions)
R2_KINETICS_CSV = R2_POST_RUN_DIR / "kinetics_r2.csv"
R2_GEN5_PDF = R2_POST_RUN_DIR / "r2_gen5_export.pdf"
R2_TIMING_JSON = R2_POST_RUN_DIR / "nitrocefin_timing.json"
R2_READER_LID_CLOSE_TXT = R2_POST_RUN_DIR / "reader_lid_close_utc.txt"
R2_DECISION_REPORT = R2_V2_DIR / "run2_decision_report.md"

# Agent tool promotion target (symlink/copy of kinetics_r2.csv)
R2_KINETICS_CSV_PROMOTED = DATA_DIR / "kinetics_r2.csv"


def r2_version_dir(version: str | None = None) -> Path:
    """Return ``post-run/v{1|2}`` for a versioned analysis bundle."""
    ver = version or R2_ANALYSIS_VERSION
    if ver not in {"v1", "v2"}:
        raise ValueError(f"Unknown Run 2 post-run analysis version: {ver}")
    return R2_POST_RUN_DIR / ver


def r2_analysis_dir(version: str | None = None) -> Path:
    """Return ``post-run/v*/analysis`` for EDA derivatives."""
    return r2_version_dir(version) / "analysis"


# Active analysis paths (v2)
R2_ANALYSIS_DIR = r2_analysis_dir(R2_ANALYSIS_VERSION)
R2_KINETICS_ANNOTATED_CSV = R2_ANALYSIS_DIR / "r2_kinetics_annotated.csv"
R2_PARSED_JSON = R2_ANALYSIS_DIR / "r2_parsed.json"
R2_ROUND_SUMMARY_EDA_JSON = R2_ANALYSIS_DIR / "r2_round_summary_eda.json"
R2_PATTERN_SUMMARY_JSON = R2_ANALYSIS_DIR / "r2_pattern_summary.json"
R2_PATTERN_SUMMARY_MD = R2_ANALYSIS_DIR / "r2_pattern_summary.md"
R2_LLM_CONTEXT_JSON = R2_ANALYSIS_DIR / "r2_kinetics_llm_context.json"
R2_LLM_CONTEXT_MD = R2_ANALYSIS_DIR / "r2_kinetics_llm_context.md"

# Frozen v1 paths (slope-only scoring snapshot)
R2_V1_ANALYSIS_DIR = r2_analysis_dir("v1")
R2_V1_ROUND_SUMMARY = R2_V1_ANALYSIS_DIR / "r2_round_summary_eda.json"
R2_V1_DECISION_REPORT = R2_V1_DIR / "run2_decision_report.md"

R2_ARTIFACT_PATHS = {
    "analysis_version": R2_ANALYSIS_VERSION,
    "kinetics_csv": R2_KINETICS_CSV,
    "gen5_pdf": R2_GEN5_PDF,
    "annotated_csv": R2_KINETICS_ANNOTATED_CSV,
    "parsed_json": R2_PARSED_JSON,
    "round_summary_json": R2_ROUND_SUMMARY_EDA_JSON,
    "pattern_summary_json": R2_PATTERN_SUMMARY_JSON,
    "pattern_summary_md": R2_PATTERN_SUMMARY_MD,
    "llm_context_json": R2_LLM_CONTEXT_JSON,
    "llm_context_md": R2_LLM_CONTEXT_MD,
    "decision_report_md": R2_DECISION_REPORT,
}
