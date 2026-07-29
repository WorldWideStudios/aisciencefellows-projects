"""Generate Run 2 post-run artifacts from run log, Gen5 export, and kinetics CSV."""

from __future__ import annotations

import ast
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from analysis.decision_tree_report import write_decision_tree_report
from analysis.kinetics import analyze_kinetics_file
from analysis.run_log_timing import analyze_run_log
from analysis.run2_paths import (
    R2_ANALYSIS_VERSION,
    R2_DECISION_REPORT,
    R2_GEN5_PDF,
    R2_KINETICS_CSV,
    R2_POST_RUN_DIR,
    R2_READER_LID_CLOSE_TXT,
    R2_TIMING_JSON,
    R2_V2_DIR,
    r2_analysis_dir,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
V5_PLATE_MAP = REPO_ROOT / "data" / "screens" / "2" / "v5" / "plate_map.json"
PLATE_MAP_R2 = REPO_ROOT / "data" / "plate_map_r2.json"
ASSAY_DIR = REPO_ROOT / "data" / "assay"
RUN2_SUMMARY = ASSAY_DIR / "run_2_summary.json"
GEN5_PDF = R2_GEN5_PDF
KINETICS_CSV = R2_KINETICS_CSV
RUN_LOG = R2_POST_RUN_DIR / "run_log_exec_tem1_activity_screen_hack_world_22_20260725_230432.txt"
TIMING_JSON = R2_TIMING_JSON
READER_LID_CLOSE_TXT = R2_READER_LID_CLOSE_TXT
DECISION_REPORT = R2_DECISION_REPORT

PACIFIC = ZoneInfo("America/Los_Angeles")


def _load_plate_map(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _condition_label(well: str, plate_map: dict[str, Any]) -> str:
    spec = plate_map.get("wells", {}).get(well, {})
    role = spec.get("role", "sample")
    if role == "sample":
        return str(spec.get("compound_id") or "sample")
    return str(role)


def _batch_well_times_from_report(report) -> list[tuple[list[str], datetime, datetime]]:
    """Return (wells, batch_start, batch_end) for each hole_10 nitrocefin batch."""
    batches: list[tuple[list[str], datetime, datetime]] = []
    pending_wells: list[str] | None = None
    pending_start: datetime | None = None

    for ev in report.events:
        msg = ev.message
        if ev.kind == "dispense_batch" and "hole_10" in msg and "25.0 uL" in msg:
            m = re.search(r"to (\[[^\]]+\])", msg)
            if m:
                pending_wells = ast.literal_eval(m.group(1))
                pending_start = ev.timestamp
            continue
        if (
            ev.kind == "dispense_batch_complete"
            and "hole_10" in msg
            and pending_wells
            and pending_start
        ):
            batches.append((pending_wells, pending_start, ev.timestamp))
            pending_wells = None
            pending_start = None

    return batches


def extract_nitrocefin_timing_from_run_log(
    log_path: str | Path,
    *,
    plate_map_json: str | Path | None = None,
) -> dict[str, Any]:
    """Build ``nitrocefin_timing.json`` from hole_10 batched dispense lines in a run log."""
    log_path = Path(log_path)
    report = analyze_run_log(log_path)
    plate_map = _load_plate_map(Path(plate_map_json)) if plate_map_json else {}

    batches = _batch_well_times_from_report(report)
    if not batches:
        raise ValueError(f"No hole_10 nitrocefin batches found in {log_path}")

    events: list[dict[str, Any]] = []
    for wells, start_dt, end_dt in batches:
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=PACIFIC)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=PACIFIC)
        start_utc = start_dt.astimezone(timezone.utc)
        end_utc = end_dt.astimezone(timezone.utc)
        span_s = max((end_utc - start_utc).total_seconds(), 1.0)
        n = len(wells)
        for i, well in enumerate(wells):
            frac = (i + 0.5) / n
            t0 = start_utc + timedelta(seconds=span_s * frac)
            events.append(
                {
                    "t0_utc": t0.isoformat().replace("+00:00", "Z"),
                    "condition": _condition_label(well, plate_map),
                    "well": well,
                    "source_anchor": "hole_10",
                    "volume_ul": 25.0,
                }
            )

    events.sort(key=lambda e: e["t0_utc"])
    return {
        "run_id": report.header.execution_id,
        "source_log": str(log_path.relative_to(REPO_ROOT)) if log_path.is_relative_to(REPO_ROOT) else str(log_path),
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "method": "run_log_hole_10_batch_interpolation",
        "event_count": len(events),
        "events": events,
    }


def extract_reader_lid_close_utc(
    gen5_pdf: str | Path,
    *,
    equilibration_s: float = 0.0,
) -> tuple[str, dict[str, Any]]:
    """Return ISO-8601 UTC lid-close time from Gen5 kinetic PDF metadata.

    Gen5 ``Date``/``Time`` is treated as when the operator started the kinetic
    method after transferring the plate to the reader (lid closed, protocol running).
    Set ``equilibration_s`` only if you need to back-date before the Gen5 timestamp.
    """
    gen5_pdf = Path(gen5_pdf)
    try:
        from gen5_pdf import parse_gen5_kinetic_pdf  # type: ignore[import-not-found]
    except ImportError:
        import sys

        sys.path.insert(0, str(REPO_ROOT / "mastermix" / "skills"))
        from gen5_pdf import parse_gen5_kinetic_pdf  # type: ignore[import-not-found]

    parsed = parse_gen5_kinetic_pdf(gen5_pdf)
    meta = parsed.get("metadata", {})
    date_str = str(meta.get("date", "")).strip()
    time_str = str(meta.get("time", "")).strip()
    if not date_str or not time_str:
        raise ValueError(f"Gen5 PDF missing Date/Time metadata: {gen5_pdf}")

    protocol_start_local = datetime.strptime(
        f"{date_str} {time_str}",
        "%m/%d/%Y %I:%M:%S %p",
    ).replace(tzinfo=PACIFIC)
    lid_close_local = protocol_start_local - timedelta(seconds=equilibration_s)
    lid_close_utc = lid_close_local.astimezone(timezone.utc)

    note = (
        f"Derived from Gen5 export Date={date_str} Time={time_str} ({PACIFIC.key}) "
        f"as plate-in-reader / kinetic protocol start"
        + (f", minus {equilibration_s:.0f}s offset" if equilibration_s else "")
        + f". Protocol start local: {protocol_start_local.isoformat()}."
    )
    meta_out = {
        "source_pdf": str(gen5_pdf.relative_to(REPO_ROOT)) if gen5_pdf.is_relative_to(REPO_ROOT) else str(gen5_pdf),
        "protocol_start_local": protocol_start_local.isoformat(),
        "lid_close_local": lid_close_local.isoformat(),
        "equilibration_s": equilibration_s,
        "note": note,
    }
    return lid_close_utc.isoformat().replace("+00:00", "Z"), meta_out


def promote_plate_map_r2(
    *,
    source: Path = V5_PLATE_MAP,
    target: Path = PLATE_MAP_R2,
    sign_off_date: str = "2026-07-25",
) -> Path:
    """Copy signed-off v5 plate map to ``data/plate_map_r2.json``."""
    plate = _load_plate_map(source)
    plate["status"] = "active"
    plate["promoted_from"] = str(source.relative_to(REPO_ROOT))
    plate["sign_off_date"] = sign_off_date
    plate["sign_off_note"] = "v5 column-strip layout run on robot 2026-07-25/26"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plate, indent=2) + "\n")
    return target


def build_run_2_summary(
    *,
    kinetics_csv: Path = KINETICS_CSV,
    plate_map_json: Path = PLATE_MAP_R2,
    nitrocefin_timing_json: Path = TIMING_JSON,
    reader_lid_close_utc: str,
) -> dict[str, Any]:
    """Run median-scoring pipeline and wrap as ``data/assay/run_2_summary.json``."""
    analysis = analyze_kinetics_file(
        kinetics_csv,
        plate_map_json=plate_map_json,
        round_number=2,
        nitrocefin_timing_json=nitrocefin_timing_json,
        reader_lid_close_utc=reader_lid_close_utc,
    )

    plate = _load_plate_map(plate_map_json)
    vehicle_wells = [w for w, s in plate.get("wells", {}).items() if s.get("role") == "vehicle"]
    no_tem1_wells = [w for w, s in plate.get("wells", {}).items() if s.get("role") == "no_tem1"]
    pos_wells = [w for w, s in plate.get("wells", {}).items() if s.get("role") == "pos-ctrl-clavaculin"]

    summary: dict[str, Any] = {
        "run": 2,
        "round": 2,
        "plan_version": 5,
        "plan_label": "r2-discovery-v5",
        "analysis_version": R2_ANALYSIS_VERSION,
        "status": "complete",
        "plate_map_active": str(plate_map_json.relative_to(REPO_ROOT)),
        "plate_map_snapshot": "data/screens/2/v5/plate_map.json",
        "source_csv_git": str(kinetics_csv.relative_to(REPO_ROOT)),
        "source_csv_local": None,
        "nitrocefin_timing_json": str(nitrocefin_timing_json.relative_to(REPO_ROOT)),
        "reader_lid_close_utc": reader_lid_close_utc,
        "analysis_dir": str(r2_analysis_dir(R2_ANALYSIS_VERSION).relative_to(REPO_ROOT)),
        "normalization": {
            "vehicle_wells": sorted(vehicle_wells),
            "no_tem1_wells": sorted(no_tem1_wells),
            "pos_ctrl_clavaculin_wells": sorted(pos_wells),
        },
    }
    summary.update(analysis)
    return summary


def write_run2_artifacts(
    *,
    log_path: Path = RUN_LOG,
    gen5_pdf: Path = GEN5_PDF,
    kinetics_csv: Path = KINETICS_CSV,
    plate_map_v5: Path = V5_PLATE_MAP,
    analysis_version: str = R2_ANALYSIS_VERSION,
) -> dict[str, Path]:
    """Generate Run 2 post-run artifacts; return paths written."""
    R2_POST_RUN_DIR.mkdir(parents=True, exist_ok=True)
    r2_analysis_dir(analysis_version).mkdir(parents=True, exist_ok=True)
    ASSAY_DIR.mkdir(parents=True, exist_ok=True)

    timing = extract_nitrocefin_timing_from_run_log(log_path, plate_map_json=plate_map_v5)
    TIMING_JSON.write_text(json.dumps(timing, indent=2) + "\n")

    reader_utc, reader_meta = extract_reader_lid_close_utc(gen5_pdf)
    READER_LID_CLOSE_TXT.write_text(
        f"{reader_utc}\n"
        f"# {reader_meta['note']}\n"
        f"# source: {reader_meta['source_pdf']}\n"
    )

    promote_plate_map_r2(source=plate_map_v5, target=PLATE_MAP_R2)

    summary = build_run_2_summary(
        kinetics_csv=kinetics_csv,
        plate_map_json=PLATE_MAP_R2,
        nitrocefin_timing_json=TIMING_JSON,
        reader_lid_close_utc=reader_utc,
    )
    RUN2_SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")

    from analysis.plates import analyze_kinetics_run

    reader_utc_txt = READER_LID_CLOSE_TXT.read_text().splitlines()[0].strip()
    analyze_kinetics_run(
        kinetics_csv,
        plate_map_json=PLATE_MAP_R2,
        run=2,
        version=5,
        output_dir=r2_analysis_dir(analysis_version),
        nitrocefin_timing_json=TIMING_JSON,
        reader_lid_close_utc=reader_utc_txt,
        parsed_json=r2_analysis_dir("v1") / "analysis" / "r2_parsed.json",
    )

    decision_report = (
        R2_V2_DIR / "run2_decision_report.md"
        if analysis_version == "v2"
        else R2_POST_RUN_DIR / analysis_version / "run2_decision_report.md"
    )
    write_decision_tree_report(RUN2_SUMMARY, decision_report, compound_list_path=plate_map_v5.parent / "compound_list.json")

    # Keep agent tool path in sync
    agent_kinetics = REPO_ROOT / "data" / "kinetics_r2.csv"
    if not agent_kinetics.exists() or agent_kinetics.stat().st_size != kinetics_csv.stat().st_size:
        shutil.copy2(kinetics_csv, agent_kinetics)

    return {
        "nitrocefin_timing_json": TIMING_JSON,
        "reader_lid_close_utc_txt": READER_LID_CLOSE_TXT,
        "plate_map_r2_json": PLATE_MAP_R2,
        "run_2_summary_json": RUN2_SUMMARY,
        "decision_report_md": decision_report,
        "analysis_dir": r2_analysis_dir(analysis_version),
    }
