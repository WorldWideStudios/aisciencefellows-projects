"""Parse Gen5 endpoint PDF exports from platereader_measure into structured data."""

from __future__ import annotations

import json
import re
from pathlib import Path

from gen5_pdf import (
    parse_gen5_endpoint_pdf,
    parse_gen5_pdf,
    write_absorbance_csv,
    write_kinetics_csv,
)

from .modules import ExecutionInfoContext, is_sim_mode, print_log, project_data_dir


def _safe_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(label).strip())
    return cleaned.strip("_") or "read"


def platereader_parse_pdf(
    read_label: str = "read",
    pdf_path: str = "",
    write_csv: bool = True,
    mode: str = "auto",
):
    """Parse a Gen5 PDF into JSON and optional CSV absorbance/kinetics tables.

    Args:
        read_label: Suffix matching the PDF from platereader_measure, e.g.
            "initial" or "endpoint_5min". Ignored when pdf_path is set.
        pdf_path: Explicit path to a Gen5 PDF. When empty, resolves
            ``data/platereader/<execution_id>/{execution_id}_{read_label}.pdf``.
        write_csv: When True, also write a flattened CSV beside the JSON.
        mode: ``auto`` (detect endpoint vs kinetic), ``endpoint``, or ``kinetic``.
    """
    print_log(runlog=True, runlog_type="step_start")
    run_id = ExecutionInfoContext.get().execution_id or "no_execution"
    safe_label = _safe_label(read_label)

    if pdf_path:
        pdf = Path(pdf_path)
    else:
        reader_dir = project_data_dir(f"platereader/{run_id}", create=False)
        if reader_dir is None:
            if is_sim_mode():
                print_log("[SIM] no project bound — skipping PDF parse")
                return {"success": True, "sim": True, "run_id": run_id}
            raise RuntimeError("No project bound; cannot resolve platereader PDF path")
        pdf = reader_dir / f"{run_id}_{safe_label}.pdf"

    print_log(f"platereader_parse_pdf: {pdf}", runlog=True)

    if not pdf.exists():
        if is_sim_mode():
            print_log(f"[SIM] PDF not found — skipping parse: {pdf}")
            return {"success": True, "sim": True, "run_id": run_id, "pdf_path": str(pdf)}
        raise FileNotFoundError(f"Gen5 PDF not found: {pdf}")

    parsed = parse_gen5_pdf(pdf, mode=mode)
    stem = pdf.stem
    json_path = pdf.with_name(f"{stem}_parsed.json")
    json_path.write_text(json.dumps(parsed, indent=2))

    csv_path = None
    export_type = parsed["metadata"].get("export_type", "endpoint")
    if write_csv:
        if export_type == "kinetic":
            csv_path = pdf.with_name(f"{stem}_kinetics.csv")
            write_kinetics_csv(parsed, csv_path, wavelength_nm=490)
        else:
            csv_path = pdf.with_name(f"{stem}_absorbance.csv")
            write_absorbance_csv(parsed, csv_path)

    wavelengths = parsed["metadata"].get("wavelengths_nm", [])
    if export_type == "kinetic":
        timecourses = parsed.get("timecourses", {})
        well_count = len(timecourses)
        a490_values = [
            points[0]["absorbance"]
            for points in (
                tc.get(490, [])
                for tc in timecourses.values()
            )
            if points
        ]
    else:
        wells = parsed["wells"]
        well_count = len(wells)
        a490_values = [wells[w][490] for w in wells if 490 in wells[w]]
    mean_a490 = sum(a490_values) / len(a490_values) if a490_values else None

    print_log(
        f"platereader_parse_pdf completed ({export_type}) — {well_count} wells, "
        f"wavelengths {wavelengths}, mean A490={mean_a490:.4f}"
        if mean_a490 is not None
        else f"platereader_parse_pdf completed ({export_type}) — {well_count} wells",
        runlog=True,
    )

    return {
        "success": True,
        "run_id": run_id,
        "pdf_path": str(pdf),
        "json_path": str(json_path),
        "csv_path": str(csv_path) if csv_path else None,
        "export_type": export_type,
        "well_count": well_count,
        "wavelengths_nm": wavelengths,
        "mean_a490": round(mean_a490, 4) if mean_a490 is not None else None,
        "temperature_c": parsed["metadata"].get("temperature_c"),
    }
