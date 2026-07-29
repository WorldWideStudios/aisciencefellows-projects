"""Generate Run 3 post-run artifacts from Gen5 PDF, synthetic timing, and kinetics CSV."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from analysis.decision_tree_report import write_decision_tree_report
from analysis.kinetics import analyze_kinetics_file
from analysis.run2_artifacts import extract_reader_lid_close_utc
from analysis.run3_paths import (
    PLATE_MAP_R3,
    R3_ANALYSIS_VERSION,
    R3_DECISION_REPORT,
    R3_GEN5_PDF,
    R3_GEN5_PDF_SOURCE,
    R3_KINETICS_CSV,
    R3_KINETICS_CSV_PROMOTED,
    R3_PARSED_JSON,
    R3_POST_RUN_DIR,
    R3_READER_LID_CLOSE_TXT,
    R3_TIMING_JSON,
    R3_V1_DIR,
    RUN3_SUMMARY,
    r3_analysis_dir,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
V1_PLATE_MAP = REPO_ROOT / "data" / "screens" / "3" / "v1" / "plate_map.json"
ASSAY_DIR = REPO_ROOT / "data" / "assay"
DOSE_SPAN_S = 120.0


def _load_plate_map(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _resolve_gen5_pdf(gen5_pdf: Path | None = None) -> Path:
    if gen5_pdf and gen5_pdf.exists():
        return gen5_pdf
    if R3_GEN5_PDF.exists():
        return R3_GEN5_PDF
    if R3_GEN5_PDF_SOURCE.exists():
        return R3_GEN5_PDF_SOURCE
    raise FileNotFoundError("No Gen5 PDF found under data/screens/3/post-run/")


def extract_kinetics_from_gen5_pdf(
    gen5_pdf: Path,
    *,
    kinetics_csv: Path = R3_KINETICS_CSV,
    parsed_json: Path = R3_PARSED_JSON,
) -> Path:
    """Parse Gen5 kinetic PDF and write ``kinetics_r3.csv`` + ``r3_parsed.json``."""
    try:
        from gen5_pdf import parse_gen5_kinetic_pdf, write_kinetics_csv  # type: ignore[import-not-found]
    except ImportError:
        import sys

        sys.path.insert(0, str(REPO_ROOT / "mastermix" / "skills"))
        from gen5_pdf import parse_gen5_kinetic_pdf, write_kinetics_csv  # type: ignore[import-not-found]

    parsed = parse_gen5_kinetic_pdf(gen5_pdf)
    kinetics_csv.parent.mkdir(parents=True, exist_ok=True)
    write_kinetics_csv(parsed, kinetics_csv, wavelength_nm=490)
    parsed_json.write_text(json.dumps(parsed, indent=2) + "\n")
    return kinetics_csv


def reanchor_nitrocefin_timing(
    *,
    reader_lid_close_utc: str,
    timing_json: Path = R3_TIMING_JSON,
    dose_span_s: float = DOSE_SPAN_S,
) -> dict[str, Any]:
    """Shift synthetic operator-estimate timing so last batch ends at reader lid close."""
    if not timing_json.exists():
        raise FileNotFoundError(f"Missing nitrocefin timing: {timing_json}")

    timing = json.loads(timing_json.read_text())
    events = timing.get("events", [])
    if not events:
        raise ValueError("nitrocefin_timing.json has no events")

    reader_t0 = datetime.fromisoformat(reader_lid_close_utc.replace("Z", "+00:00"))
    first_t0 = reader_t0 - timedelta(seconds=dose_span_s)

    batches: dict[int, list[dict[str, Any]]] = {}
    for ev in events:
        batch = int(ev.get("dispense_batch") or 1)
        batches.setdefault(batch, []).append(ev)

    batch_ids = sorted(batches)
    n_batches = len(batch_ids)
    interval_s = dose_span_s / max(n_batches - 1, 1)

    new_events: list[dict[str, Any]] = []
    for i, batch_id in enumerate(batch_ids):
        batch_t = first_t0 + timedelta(seconds=i * interval_s)
        for ev in batches[batch_id]:
            new_ev = dict(ev)
            new_ev["t0_utc"] = batch_t.isoformat().replace("+00:00", "Z")
            new_events.append(new_ev)

    new_events.sort(key=lambda e: e["t0_utc"])
    timing["events"] = new_events
    timing["generated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    timing["reader_anchor_utc"] = reader_lid_close_utc
    timing["dose_span_s"] = dose_span_s
    timing["note"] = (
        "Operator estimate: 12-channel pipette, 6 dispenses, ~2 min span. "
        "Re-anchored to Gen5 protocol start (reader lid close) from PDF metadata."
    )
    timing_json.write_text(json.dumps(timing, indent=2) + "\n")
    return timing


def build_run_3_summary(
    *,
    kinetics_csv: Path = R3_KINETICS_CSV,
    plate_map_json: Path = PLATE_MAP_R3,
    nitrocefin_timing_json: Path = R3_TIMING_JSON,
    reader_lid_close_utc: str,
) -> dict[str, Any]:
    analysis = analyze_kinetics_file(
        kinetics_csv,
        plate_map_json=plate_map_json,
        round_number=3,
        nitrocefin_timing_json=nitrocefin_timing_json,
        reader_lid_close_utc=reader_lid_close_utc,
    )

    plate = _load_plate_map(plate_map_json)
    substrate_wells = [
        w
        for w, s in plate.get("wells", {}).items()
        if s.get("bucket") == "substrate_control" or s.get("compound_id") in {"T1008", "T0224", "T0985"}
    ]
    no_tem1_wells = [w for w, s in plate.get("wells", {}).items() if s.get("role") == "no_tem1"]
    pos_wells = [w for w, s in plate.get("wells", {}).items() if s.get("role") == "pos-ctrl-clavaculin"]

    summary: dict[str, Any] = {
        "run": 3,
        "round": 3,
        "plan_version": 1,
        "plan_label": "r3-discovery-v1",
        "analysis_version": R3_ANALYSIS_VERSION,
        "status": "complete",
        "plate_map_active": str(plate_map_json.relative_to(REPO_ROOT)),
        "plate_map_snapshot": "data/screens/3/v1/plate_map.json",
        "source_csv_git": str(kinetics_csv.relative_to(REPO_ROOT)),
        "source_csv_local": None,
        "gen5_pdf": str(_resolve_gen5_pdf().relative_to(REPO_ROOT)),
        "nitrocefin_timing_json": str(nitrocefin_timing_json.relative_to(REPO_ROOT)),
        "reader_lid_close_utc": reader_lid_close_utc,
        "analysis_dir": str(r3_analysis_dir(R3_ANALYSIS_VERSION).relative_to(REPO_ROOT)),
        "normalization": {
            "anchor_mode": "substrate",
            "substrate_control_wells": sorted(substrate_wells),
            "no_tem1_wells": sorted(no_tem1_wells),
            "pos_ctrl_clavaculin_wells": sorted(pos_wells),
        },
    }
    summary.update(analysis)
    return summary


def write_run3_artifacts(
    *,
    gen5_pdf: Path | None = None,
    kinetics_csv: Path = R3_KINETICS_CSV,
    plate_map_v1: Path = V1_PLATE_MAP,
    analysis_version: str = R3_ANALYSIS_VERSION,
) -> dict[str, Path]:
    """Generate Run 3 post-run artifacts; return paths written."""
    R3_POST_RUN_DIR.mkdir(parents=True, exist_ok=True)
    r3_analysis_dir(analysis_version).mkdir(parents=True, exist_ok=True)
    ASSAY_DIR.mkdir(parents=True, exist_ok=True)

    pdf_path = _resolve_gen5_pdf(gen5_pdf)
    if pdf_path != R3_GEN5_PDF:
        shutil.copy2(pdf_path, R3_GEN5_PDF)

    extract_kinetics_from_gen5_pdf(R3_GEN5_PDF, kinetics_csv=kinetics_csv)

    reader_utc, reader_meta = extract_reader_lid_close_utc(R3_GEN5_PDF)
    R3_READER_LID_CLOSE_TXT.write_text(
        f"{reader_utc}\n"
        f"# {reader_meta['note']}\n"
        f"# source: {reader_meta['source_pdf']}\n"
    )

    reanchor_nitrocefin_timing(reader_lid_close_utc=reader_utc)

    summary = build_run_3_summary(
        kinetics_csv=kinetics_csv,
        plate_map_json=PLATE_MAP_R3,
        nitrocefin_timing_json=R3_TIMING_JSON,
        reader_lid_close_utc=reader_utc,
    )
    RUN3_SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")

    from analysis.plates import analyze_kinetics_run

    analyze_kinetics_run(
        kinetics_csv,
        plate_map_json=PLATE_MAP_R3,
        run=3,
        version=1,
        round_number=3,
        output_dir=r3_analysis_dir(analysis_version),
        analysis_version=analysis_version,
        nitrocefin_timing_json=R3_TIMING_JSON,
        reader_lid_close_utc=reader_utc,
        parsed_json=R3_PARSED_JSON,
    )

    write_decision_tree_report(
        RUN3_SUMMARY,
        R3_DECISION_REPORT,
        compound_list_path=plate_map_v1.parent / "compound_list.json",
    )

    if not R3_KINETICS_CSV_PROMOTED.exists() or R3_KINETICS_CSV_PROMOTED.stat().st_size != kinetics_csv.stat().st_size:
        shutil.copy2(kinetics_csv, R3_KINETICS_CSV_PROMOTED)

    return {
        "kinetics_csv": kinetics_csv,
        "gen5_pdf": R3_GEN5_PDF,
        "nitrocefin_timing_json": R3_TIMING_JSON,
        "reader_lid_close_utc_txt": R3_READER_LID_CLOSE_TXT,
        "run_3_summary_json": RUN3_SUMMARY,
        "decision_report_md": R3_DECISION_REPORT,
        "analysis_dir": r3_analysis_dir(analysis_version),
    }
