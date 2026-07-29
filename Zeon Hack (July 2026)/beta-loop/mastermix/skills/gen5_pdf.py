"""Parse Gen5 absorbance PDF exports from BioTek ELx808 plate readers.

Supports endpoint reads (single absorbance per well) and kinetic reads
(time course per well at one or more wavelengths).
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from pypdf import PdfReader

ROWS = "ABCDEFGH"
COLS = range(1, 13)
WAVELENGTHS_NM = (450, 490, 630)
WELLS_PER_PLATE = 96
VALUES_PER_PLATE = WELLS_PER_PLATE * len(WAVELENGTHS_NM)
WELL_RE = re.compile(r"^[A-H](?:1[0-2]|[1-9])$")
TIME_ROW_RE = re.compile(r"^0:\d{2}:\d{2}$")
KINETIC_HEADER_RE = re.compile(r"^Time T° (\d+) ((?:[A-H](?:1[0-2]|[1-9])\s*)+)$")
METRICS_PER_WELL = 8  # Gen5 Results: 4 metrics × 2 wavelengths per well


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_time_hms(value: str) -> float:
    hours, minutes, seconds = (int(part) for part in value.split(":"))
    return float(hours * 3600 + minutes * 60 + seconds)


def _parse_metadata(text: str) -> dict:
    meta: dict = {}

    if m := re.search(r"Software Version\s+([\d.]+)", text):
        meta["software_version"] = m.group(1)
    if m := re.search(r"Protocol File Path:\s*(.+)", text):
        meta["protocol_path"] = m.group(1).strip()
    if m := re.search(r"Experiment File Path:\s*(.+)", text):
        meta["experiment_path"] = m.group(1).strip()
    if m := re.search(r"Plate Number\s+(.+)", text):
        meta["plate_number"] = m.group(1).strip()
    if m := re.search(r"Date\s+(.+)", text):
        meta["date"] = m.group(1).strip()
    if m := re.search(r"^Time\s+(.+)", text, re.MULTILINE):
        meta["time"] = m.group(1).strip()
    if m := re.search(r"Reader Type:\s*(.+)", text):
        meta["reader_type"] = m.group(1).strip()
    if m := re.search(r"Read\s+(.+)", text):
        meta["read_type"] = m.group(1).strip()
    if m := re.search(r"Wavelengths:\s*([\d,\s]+)", text):
        meta["wavelengths_nm"] = [int(w.strip()) for w in m.group(1).split(",") if w.strip()]
    if m := re.search(r"Actual Temperature:\s*([\d.]+)", text):
        meta["temperature_c"] = float(m.group(1))
    if m := re.search(
        r"Start Kinetic\s+Runtime (0:\d{2}:\d{2}).*?Interval (0:\d{2}:\d{2}),\s*(\d+) Reads",
        text,
    ):
        meta["kinetic_runtime_s"] = _parse_time_hms(m.group(1))
        meta["kinetic_interval_s"] = _parse_time_hms(m.group(2))
        meta["kinetic_reads"] = int(m.group(3))
    if m := re.search(r"Set Temperature\s+Setpoint\s*([\d.]+)", text):
        meta["setpoint_temperature_c"] = float(m.group(1))

    return meta


def is_kinetic_export(text: str) -> bool:
    return "Start Kinetic" in text


def _well_id(row: str, col: int) -> str:
    return f"{row}{col}"


def _parse_absorbance_values(text: str, wavelengths_nm: list[int]) -> dict[str, dict[int, float]]:
    results_idx = text.find("Results")
    if results_idx < 0:
        raise ValueError("Gen5 PDF missing 'Results' section")

    after_results = text[results_idx:]
    values = [float(v) for v in re.findall(r"\d+\.\d+", after_results)]
    if len(values) != VALUES_PER_PLATE:
        raise ValueError(
            f"Expected {VALUES_PER_PLATE} absorbance values, found {len(values)}"
        )

    wells: dict[str, dict[int, float]] = {}
    for wl_idx, wl in enumerate(wavelengths_nm):
        block = values[wl_idx * WELLS_PER_PLATE : (wl_idx + 1) * WELLS_PER_PLATE]
        for row_idx, row in enumerate(ROWS):
            row_vals = block[row_idx * 12 : (row_idx + 1) * 12]
            for col_idx, absorbance in enumerate(row_vals, start=1):
                well = _well_id(row, col_idx)
                wells.setdefault(well, {})[wl] = absorbance

    return wells


def _section_for_wavelength(text: str, wavelength_nm: int) -> str:
    marker = f"\n{wavelength_nm}\n"
    start = text.find(marker)
    if start < 0:
        if text.startswith(f"{wavelength_nm}\n"):
            start = 0
        else:
            return ""
    else:
        start += 1

    next_markers = [text.find(f"\n{wl}\n", start + 1) for wl in (490, 405, 450, 630) if wl != wavelength_nm]
    next_markers.append(text.find("\nResults\n", start + 1))
    end_candidates = [idx for idx in next_markers if idx >= 0]
    end = min(end_candidates) if end_candidates else len(text)
    return text[start:end]


def _parse_kinetic_wavelength_section(section: str, wavelength_nm: int) -> dict[str, list[dict[str, float]]]:
    """Parse one wavelength block into per-well time courses."""
    series: dict[str, list[dict[str, float]]] = {}
    active_wells: list[str] = []

    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line or line.endswith("of 23") or line.startswith("--"):
            continue

        header = KINETIC_HEADER_RE.match(line.replace("\t", " "))
        if header:
            header_wl = int(header.group(1))
            if header_wl != wavelength_nm:
                continue
            active_wells = header.group(2).split()
            continue

        if not active_wells:
            continue

        parts = line.replace("\t", " ").split()
        if len(parts) < 3 or not TIME_ROW_RE.match(parts[0]):
            continue

        time_s = _parse_time_hms(parts[0])
        try:
            temperature_c = float(parts[1])
            values = [float(v) for v in parts[2:]]
        except ValueError:
            continue

        if len(values) != len(active_wells):
            continue

        for well, absorbance in zip(active_wells, values):
            if not WELL_RE.match(well):
                continue
            series.setdefault(well, []).append(
                {
                    "time_s": time_s,
                    "temperature_c": temperature_c,
                    "absorbance": absorbance,
                }
            )

    return series


def _parse_kinetic_timecourses(text: str, wavelengths_nm: list[int]) -> dict[str, dict[int, list[dict[str, float]]]]:
    wells: dict[str, dict[int, list[dict[str, float]]]] = {}
    for wavelength_nm in wavelengths_nm:
        section = _section_for_wavelength(text, wavelength_nm)
        if not section:
            continue
        for well, points in _parse_kinetic_wavelength_section(section, wavelength_nm).items():
            wells.setdefault(well, {})[wavelength_nm] = points
    return wells


def _parse_gen5_kinetic_results(
    text: str,
    wavelengths_nm: list[int],
) -> dict[str, dict[int, dict[str, float | str | None]]]:
    """Parse Gen5 kinetic Results section (Max V, Lagtime) for QC cross-check."""
    idx = text.find("Results")
    if idx < 0:
        return {}

    section = text[idx:]
    tokens = re.findall(r"-?\d+\.\d+|\d+:\d+:\d+|\?\?\?\?\?", section)
    expected = WELLS_PER_PLATE * METRICS_PER_WELL
    if len(tokens) != expected:
        return {}

    wl_primary = wavelengths_nm[0] if wavelengths_nm else 490
    wl_secondary = wavelengths_nm[1] if len(wavelengths_nm) > 1 else wl_primary

    results: dict[str, dict[int, dict[str, float | str | None]]] = {}
    well_idx = 0
    for row in ROWS:
        for col in COLS:
            well = _well_id(row, col)
            chunk = tokens[well_idx * METRICS_PER_WELL : (well_idx + 1) * METRICS_PER_WELL]
            if len(chunk) != METRICS_PER_WELL:
                well_idx += 1
                continue
            results[well] = {
                wl_primary: {
                    "max_v": float(chunk[0]),
                    "r_squared": float(chunk[1]),
                    "t_at_max_v": chunk[2],
                    "lagtime": None if chunk[3] == "?????" else chunk[3],
                },
                wl_secondary: {
                    "max_v": float(chunk[4]),
                    "r_squared": float(chunk[5]),
                    "t_at_max_v": chunk[6],
                    "lagtime": None if chunk[7] == "?????" else chunk[7],
                },
            }
            well_idx += 1
    return results


def parse_gen5_kinetic_pdf(pdf_path: str | Path) -> dict:
    """Parse a Gen5 kinetic PDF into metadata and per-well time courses."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Gen5 PDF not found: {path}")

    text = _extract_text(path)
    metadata = _parse_metadata(text)
    metadata["export_type"] = "kinetic"
    wavelengths_nm = metadata.get("wavelengths_nm") or [490]
    timecourses = _parse_kinetic_timecourses(text, wavelengths_nm)
    if not timecourses:
        raise ValueError(f"No kinetic time courses found in {path.name}")

    gen5_results = _parse_gen5_kinetic_results(text, wavelengths_nm)

    return {"metadata": metadata, "timecourses": timecourses, "gen5_results": gen5_results}


def parse_gen5_pdf(pdf_path: str | Path, mode: str = "auto") -> dict:
    """Parse a Gen5 PDF in endpoint or kinetic mode."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Gen5 PDF not found: {path}")

    if mode not in {"auto", "endpoint", "kinetic"}:
        raise ValueError(f"Unsupported mode: {mode}")

    text = _extract_text(path)
    use_kinetic = mode == "kinetic" or (mode == "auto" and is_kinetic_export(text))
    if use_kinetic:
        return parse_gen5_kinetic_pdf(path)
    return parse_gen5_endpoint_pdf(path)


def parse_gen5_endpoint_pdf(pdf_path: str | Path) -> dict:
    """Parse a Gen5 endpoint PDF into metadata and per-well absorbance.

    Returns:
        dict with ``metadata`` and ``wells`` keys. Each well maps wavelength (nm)
        to absorbance, e.g. ``wells["A1"][450] == 0.040``.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Gen5 PDF not found: {path}")

    text = _extract_text(path)
    metadata = _parse_metadata(text)
    wavelengths_nm = metadata.get("wavelengths_nm") or list(WAVELENGTHS_NM)
    wells = _parse_absorbance_values(text, wavelengths_nm)

    metadata["export_type"] = "endpoint"
    return {"metadata": metadata, "wells": wells}


def kinetics_to_csv_rows(
    parsed: dict,
    *,
    wavelength_nm: int = 490,
) -> list[dict[str, str | int | float]]:
    """Flatten kinetic time courses to CSV-ready rows."""
    rows: list[dict[str, str | int | float]] = []
    timecourses = parsed.get("timecourses", {})
    for well in sorted(timecourses, key=_well_sort_key):
        wl_points = timecourses[well].get(wavelength_nm)
        if not wl_points:
            continue
        for point in sorted(wl_points, key=lambda p: p["time_s"]):
            rows.append(
                {
                    "well": well,
                    "time_s": point["time_s"],
                    "temperature_c": point["temperature_c"],
                    "wavelength_nm": wavelength_nm,
                    "absorbance_a490": point["absorbance"],
                }
            )
    return rows


def write_kinetics_csv(
    parsed: dict,
    csv_path: str | Path,
    *,
    wavelength_nm: int = 490,
) -> Path:
    """Write kinetic time courses for one wavelength to CSV."""
    path = Path(csv_path)
    rows = kinetics_to_csv_rows(parsed, wavelength_nm=wavelength_nm)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["well", "time_s", "temperature_c", "wavelength_nm", "absorbance_a490"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def wells_to_csv_rows(parsed: dict) -> list[dict[str, str | int | float]]:
    """Flatten parsed wells to CSV-ready rows."""
    rows: list[dict[str, str | int | float]] = []
    for well in sorted(parsed["wells"], key=_well_sort_key):
        for wl in sorted(parsed["wells"][well]):
            rows.append(
                {
                    "well": well,
                    "wavelength_nm": wl,
                    "absorbance": parsed["wells"][well][wl],
                }
            )
    return rows


def _well_sort_key(well: str) -> tuple[int, int]:
    row = well[0]
    col = int(well[1:])
    return (ROWS.index(row), col)


def write_absorbance_csv(parsed: dict, csv_path: str | Path) -> Path:
    """Write flattened absorbance rows to CSV."""
    path = Path(csv_path)
    rows = wells_to_csv_rows(parsed)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["well", "wavelength_nm", "absorbance"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def absorbance_csv_string(parsed: dict) -> str:
    """Return CSV content as a string."""
    buf = io.StringIO()
    rows = wells_to_csv_rows(parsed)
    writer = csv.DictWriter(buf, fieldnames=["well", "wavelength_nm", "absorbance"])
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
