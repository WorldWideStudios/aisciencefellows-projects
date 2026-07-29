"""Canonical paths for Round 3 post-run artifacts."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
SCREENS_DIR = DATA_DIR / "screens"

R3_POST_RUN_DIR = SCREENS_DIR / "3" / "post-run"
R3_PLATE_DESIGN_DIR = SCREENS_DIR / "3" / "v1"
R3_ANALYSIS_VERSION = "v1"
R3_V1_DIR = R3_POST_RUN_DIR / "v1"

R3_KINETICS_CSV = R3_POST_RUN_DIR / "kinetics_r3.csv"
R3_GEN5_PDF = R3_POST_RUN_DIR / "r3_gen5_export.pdf"
R3_GEN5_PDF_SOURCE = R3_POST_RUN_DIR / "Team_3_FINAL_SUNDAY.pdf"
R3_TIMING_JSON = R3_POST_RUN_DIR / "nitrocefin_timing.json"
R3_READER_LID_CLOSE_TXT = R3_POST_RUN_DIR / "reader_lid_close_utc.txt"
R3_PARSED_JSON = R3_POST_RUN_DIR / "r3_parsed.json"
R3_DECISION_REPORT = R3_V1_DIR / "run3_decision_report.md"

PLATE_MAP_R3 = DATA_DIR / "plate_map_r3.json"
RUN3_SUMMARY = DATA_DIR / "assay" / "run_3_summary.json"
R3_KINETICS_CSV_PROMOTED = DATA_DIR / "kinetics_r3.csv"


def r3_version_dir(version: str | None = None) -> Path:
    ver = version or R3_ANALYSIS_VERSION
    if ver != "v1":
        raise ValueError(f"Unknown Run 3 post-run analysis version: {ver}")
    return R3_POST_RUN_DIR / ver


def r3_analysis_dir(version: str | None = None) -> Path:
    return r3_version_dir(version) / "analysis"


R3_ANALYSIS_DIR = r3_analysis_dir(R3_ANALYSIS_VERSION)
R3_KINETICS_ANNOTATED_CSV = R3_ANALYSIS_DIR / "r3_kinetics_annotated.csv"
R3_ROUND_SUMMARY_EDA_JSON = R3_ANALYSIS_DIR / "r3_round_summary_eda.json"
R3_PATTERN_SUMMARY_JSON = R3_ANALYSIS_DIR / "r3_pattern_summary.json"
R3_PATTERN_SUMMARY_MD = R3_ANALYSIS_DIR / "r3_pattern_summary.md"
R3_LLM_CONTEXT_JSON = R3_ANALYSIS_DIR / "r3_kinetics_llm_context.json"
R3_LLM_CONTEXT_MD = R3_ANALYSIS_DIR / "r3_kinetics_llm_context.md"
