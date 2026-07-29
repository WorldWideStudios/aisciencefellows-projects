"""Offline tests for Gen5 endpoint PDF parsing."""

from __future__ import annotations

import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SKILLS_DIR.parent.parent
sys.path.insert(0, str(SKILLS_DIR))

from gen5_pdf import (  # noqa: E402
    is_kinetic_export,
    parse_gen5_endpoint_pdf,
    parse_gen5_kinetic_pdf,
    parse_gen5_pdf,
)

SAMPLE_PDFS = [
    REPO_ROOT / "skill_platereader_measure_20260724_231705.pdf",
    REPO_ROOT
    / "mastermix/data/platereader/skill_platereader_measure_20260725_173839/skill_platereader_measure_20260725_173839.pdf",
    REPO_ROOT
    / "mastermix/data/platereader/skill_platereader_measure_20260725_174147/skill_platereader_measure_20260725_174147.pdf",
]

# Populated plate (7/25 17:41) — high 450 nm signal at B7–B9.
SPOT_CHECK_WELL = Path(SAMPLE_PDFS[2])
SPOT_CHECK = {
    "B7": {450: 0.610, 490: 0.038, 630: 0.042},
    "B8": {450: 0.560, 490: 0.038, 630: 0.044},
    "B9": {450: 0.520, 490: 0.039, 630: 0.039},
}


def _assert_close(actual: float, expected: float, tol: float = 0.001) -> None:
    if abs(actual - expected) > tol:
        raise AssertionError(f"expected {expected}, got {actual}")


def test_all_sample_pdfs() -> None:
    for pdf_path in SAMPLE_PDFS:
        if not pdf_path.exists():
            raise FileNotFoundError(f"Sample PDF missing: {pdf_path}")
        parsed = parse_gen5_endpoint_pdf(pdf_path)
        wells = parsed["wells"]
        assert len(wells) == 96, f"{pdf_path.name}: expected 96 wells, got {len(wells)}"
        for well, wl_map in wells.items():
            assert len(wl_map) == 3, f"{well}: expected 3 wavelengths, got {wl_map}"
        meta = parsed["metadata"]
        assert meta.get("reader_type") == "ELx808", meta
        assert meta.get("wavelengths_nm") == [450, 490, 630], meta
        print(f"OK  {pdf_path.name} — {len(wells)} wells, temp={meta.get('temperature_c')} °C")


def test_spot_check_high_absorbance() -> None:
    parsed = parse_gen5_endpoint_pdf(SPOT_CHECK_WELL)
    for well, expected_wls in SPOT_CHECK.items():
        for wl, expected in expected_wls.items():
            actual = parsed["wells"][well][wl]
            _assert_close(actual, expected)
    print(f"OK  spot check on {SPOT_CHECK_WELL.name}")


def test_empty_plate_near_zero() -> None:
    parsed = parse_gen5_endpoint_pdf(SAMPLE_PDFS[0])
    for well in ("A1", "A2", "H12"):
        for wl in (450, 490, 630):
            assert parsed["wells"][well][wl] == 0.0, (
                f"{well}@{wl}nm expected 0.0, got {parsed['wells'][well][wl]}"
            )
    print(f"OK  empty plate {SAMPLE_PDFS[0].name}")


R2_KINETIC_PDF = REPO_ROOT / "data" / "screens" / "2" / "post-run" / "r2_gen5_export.pdf"


def test_r2_kinetic_pdf() -> None:
    if not R2_KINETIC_PDF.exists():
        raise FileNotFoundError(f"Run 2 kinetic PDF missing: {R2_KINETIC_PDF}")

    text = R2_KINETIC_PDF.read_bytes()
    assert len(text) > 0

    parsed = parse_gen5_kinetic_pdf(R2_KINETIC_PDF)
    meta = parsed["metadata"]
    assert meta.get("export_type") == "kinetic"
    assert meta.get("wavelengths_nm") == [490, 405]
    assert meta.get("kinetic_reads") == 31

    timecourses = parsed["timecourses"]
    assert len(timecourses) == 96
    assert len(timecourses["A1"][490]) == 31
    _assert_close(timecourses["A1"][490][0]["absorbance"], 0.041)
    _assert_close(timecourses["B3"][490][0]["absorbance"], 0.095)
    _assert_close(timecourses["D6"][490][0]["absorbance"], 0.298)

    auto = parse_gen5_pdf(R2_KINETIC_PDF, mode="auto")
    assert "timecourses" in auto
    assert len(auto.get("gen5_results", {})) == 96
    print(f"OK  {R2_KINETIC_PDF.name} — 96 wells × 31 reads @ 490 nm")


def test_detect_kinetic_export() -> None:
    if not R2_KINETIC_PDF.exists():
        return
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(R2_KINETIC_PDF)).pages)
    assert is_kinetic_export(text)


if __name__ == "__main__":
    test_all_sample_pdfs()
    test_spot_check_high_absorbance()
    test_empty_plate_near_zero()
    test_r2_kinetic_pdf()
    print("All Gen5 PDF parser tests passed.")
