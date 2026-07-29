"""Plate map helpers for Round 2 dose-response design and kinetics annotation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from analysis.kinetics import DOSE_RESPONSE_CONCENTRATIONS_UM

CONTROL_WELLS = {
    "A1": {"compound_id": None, "concentration_uM": 0, "role": "vehicle", "bucket": "control"},
    "A2": {"compound_id": None, "concentration_uM": 0, "role": "vehicle", "bucket": "control"},
    "A3": {"compound_id": None, "concentration_uM": 0, "role": "vehicle", "bucket": "control"},
    "A4": {"compound_id": None, "concentration_uM": 0, "role": "no_tem1", "bucket": "control"},
    "A5": {"compound_id": None, "concentration_uM": 0, "role": "no_tem1", "bucket": "control"},
    "A6": {"compound_id": "T19860", "concentration_uM": 50, "role": "pos-ctrl-clavaculin", "bucket": "control"},
}


def load_plate_map(path: str | Path) -> dict:
    """Load a plate map JSON file."""
    return json.loads(Path(path).read_text())


def resolve_plate_map(
    plate_map_json: str | Path | None = None,
    *,
    run: int | None = None,
    version: int | None = None,
    repo_root: str | Path | None = None,
) -> dict | None:
    """Resolve a plate map from an explicit path or ``data/screens/<run>/v<version>/``."""
    if plate_map_json:
        path = Path(plate_map_json)
        if path.exists():
            return load_plate_map(path)
        return None

    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    candidates: list[Path] = []
    if run is not None and version is not None:
        candidates.append(root / f"data/screens/{run}/v{version}/plate_map.json")
    if run is not None:
        screen_dir = root / f"data/screens/{run}"
        if screen_dir.exists():
            candidates.extend(sorted(screen_dir.glob("v*/plate_map.json"), reverse=True))
    candidates.append(root / "data/screens/2/v5/plate_map.json")
    candidates.append(root / "data/screens/1/v3/plate_map.json")

    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            return load_plate_map(path)
    return None


def map_wells_to_plate_layout(
    kinetics_csv: str | Path,
    plate_map_json: str | Path | None = None,
    *,
    run: int | None = 2,
    version: int | None = 5,
) -> pd.DataFrame:
    """Join kinetics CSV rows with plate-map annotations for each well."""
    df = pd.read_csv(kinetics_csv)
    plate_map = resolve_plate_map(plate_map_json, run=run, version=version)
    if plate_map is None:
        raise FileNotFoundError("No plate map found for kinetics annotation")

    well_col = "well" if "well" in df.columns else "well_id"
    layout_rows = []
    for well, spec in plate_map.get("wells", {}).items():
        layout_rows.append({"well": well, **spec})
    layout = pd.DataFrame(layout_rows)

    annotated = df.merge(layout, on="well", how="left")
    annotated.attrs["plate_map_path"] = plate_map.get("versioned_path") or str(plate_map_json)
    annotated.attrs["round"] = plate_map.get("round")
    annotated.attrs["run"] = plate_map.get("run")
    annotated.attrs["version"] = plate_map.get("version")
    return annotated


def write_annotated_kinetics_csv(
    kinetics_csv: str | Path,
    output_csv: str | Path,
    plate_map_json: str | Path | None = None,
    *,
    run: int | None = 2,
    version: int | None = 5,
) -> Path:
    """Write kinetics CSV with plate-layout columns appended."""
    annotated = map_wells_to_plate_layout(
        kinetics_csv,
        plate_map_json,
        run=run,
        version=version,
    )
    out = Path(output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    annotated.to_csv(out, index=False)
    return out


def analyze_kinetics_run(
    kinetics_csv: str | Path,
    *,
    plate_map_json: str | Path | None = None,
    run: int | None = 2,
    version: int | None = 5,
    round_number: int | None = None,
    output_dir: str | Path | None = None,
    analysis_version: str | None = None,
    slope_window_start_s: float | None = 180.0,
    slope_window_end_s: float | None = 480.0,
    parsed_json: str | Path | None = None,
    write_pattern_markdown: bool = True,
    **analyze_kwargs,
) -> dict:
    """Map wells to plate layout, run kinetics analysis, and emit pattern EDA."""
    from analysis.kinetics import analyze_kinetics_file
    from analysis.kinetics_eda import (
        build_kinetics_llm_context,
        summarize_kinetics_patterns,
        write_kinetics_llm_context,
        write_pattern_summary,
    )
    from analysis.run2_paths import (
        R2_ANALYSIS_VERSION,
        R2_DECISION_REPORT,
        R2_KINETICS_ANNOTATED_CSV,
        R2_LLM_CONTEXT_JSON,
        R2_LLM_CONTEXT_MD,
        R2_PARSED_JSON,
        R2_PATTERN_SUMMARY_JSON,
        R2_PATTERN_SUMMARY_MD,
        R2_ROUND_SUMMARY_EDA_JSON,
        r2_analysis_dir,
    )
    from analysis.run3_paths import (
        R3_ANALYSIS_VERSION,
        R3_KINETICS_ANNOTATED_CSV,
        R3_LLM_CONTEXT_JSON,
        R3_LLM_CONTEXT_MD,
        R3_PATTERN_SUMMARY_JSON,
        R3_PATTERN_SUMMARY_MD,
        R3_ROUND_SUMMARY_EDA_JSON,
        r3_analysis_dir,
    )

    plate_map = resolve_plate_map(plate_map_json, run=run, version=version)
    if plate_map is None:
        raise FileNotFoundError("No plate map found for kinetics analysis")

    plate_map_path = plate_map_json or plate_map.get("versioned_path")
    rnd = round_number if round_number is not None else plate_map.get("round", 1)

    kinetics_path = Path(kinetics_csv)
    if output_dir is not None:
        out_dir = Path(output_dir)
    elif run == 2:
        ver = analysis_version or R2_ANALYSIS_VERSION
        out_dir = r2_analysis_dir(ver)
    elif run == 3:
        ver = analysis_version or R3_ANALYSIS_VERSION
        out_dir = r3_analysis_dir(ver)
    else:
        out_dir = kinetics_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = kinetics_path.stem

    if run == 2:
        annotated_path = out_dir / "r2_kinetics_annotated.csv"
        summary_path = out_dir / "r2_round_summary_eda.json"
        pattern_json_path = out_dir / "r2_pattern_summary.json"
        pattern_md_path = (out_dir / "r2_pattern_summary.md") if write_pattern_markdown else None
        llm_context_path = out_dir / "r2_kinetics_llm_context.json"
        llm_prompt_path = out_dir / "r2_kinetics_llm_context.md"
        parsed_path = Path(parsed_json) if parsed_json else (out_dir / "r2_parsed.json")
    elif run == 3:
        annotated_path = R3_KINETICS_ANNOTATED_CSV if out_dir == r3_analysis_dir(analysis_version or R3_ANALYSIS_VERSION) else out_dir / "r3_kinetics_annotated.csv"
        summary_path = R3_ROUND_SUMMARY_EDA_JSON if out_dir == r3_analysis_dir(analysis_version or R3_ANALYSIS_VERSION) else out_dir / "r3_round_summary_eda.json"
        pattern_json_path = R3_PATTERN_SUMMARY_JSON if out_dir == r3_analysis_dir(analysis_version or R3_ANALYSIS_VERSION) else out_dir / "r3_pattern_summary.json"
        pattern_md_path = (R3_PATTERN_SUMMARY_MD if out_dir == r3_analysis_dir(analysis_version or R3_ANALYSIS_VERSION) else out_dir / "r3_pattern_summary.md") if write_pattern_markdown else None
        llm_context_path = R3_LLM_CONTEXT_JSON if out_dir == r3_analysis_dir(analysis_version or R3_ANALYSIS_VERSION) else out_dir / "r3_kinetics_llm_context.json"
        llm_prompt_path = R3_LLM_CONTEXT_MD if out_dir == r3_analysis_dir(analysis_version or R3_ANALYSIS_VERSION) else out_dir / "r3_kinetics_llm_context.md"
        parsed_path = Path(parsed_json) if parsed_json else None
    else:
        annotated_path = out_dir / f"{stem}_annotated.csv"
        summary_path = out_dir / f"round_summary_{stem}.json"
        pattern_json_path = out_dir / f"pattern_summary_{stem}.json"
        pattern_md_path = out_dir / f"pattern_summary_{stem}.md" if write_pattern_markdown else None
        llm_context_path = out_dir / f"kinetics_llm_context_{stem}.json"
        llm_prompt_path = out_dir / f"kinetics_llm_context_{stem}.md"
        parsed_path = Path(parsed_json) if parsed_json else None
        if parsed_path is None:
            base_stem = stem.replace("_kinetics", "")
            candidate = out_dir / f"{base_stem}_parsed.json"
            if candidate.exists():
                parsed_path = candidate

    write_annotated_kinetics_csv(
        kinetics_csv,
        annotated_path,
        plate_map_path,
        run=run,
        version=version,
    )

    summary = analyze_kinetics_file(
        kinetics_csv,
        plate_map_json=plate_map_path,
        round_number=rnd,
        slope_window_start_s=slope_window_start_s,
        slope_window_end_s=slope_window_end_s,
        **analyze_kwargs,
    )
    if run == 2:
        summary["analysis_version"] = analysis_version or R2_ANALYSIS_VERSION
    elif run == 3:
        summary["analysis_version"] = analysis_version or R3_ANALYSIS_VERSION
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    gen5_results = None
    if parsed_path and parsed_path.exists():
        parsed_data = json.loads(parsed_path.read_text())
        gen5_results = parsed_data.get("gen5_results")

    pattern_report = summarize_kinetics_patterns(
        kinetics_csv,
        plate_map_path,
        parsed_json=parsed_path,
        gen5_results=gen5_results,
    )
    write_pattern_summary(
        pattern_report,
        pattern_json_path,
        markdown_path=pattern_md_path,
        plate_map_json=plate_map_path,
    )

    parsed_metadata = None
    if parsed_path and parsed_path.exists():
        parsed_metadata = json.loads(parsed_path.read_text()).get("metadata")

    artifact_paths = {
        "kinetics_csv": str(kinetics_csv),
        "annotated_csv": str(annotated_path),
        "round_summary_json": str(summary_path),
        "pattern_summary_json": str(pattern_json_path),
        "plate_map_json": str(plate_map_path),
    }
    if parsed_path:
        artifact_paths["parsed_json"] = str(parsed_path)
    if pattern_md_path:
        artifact_paths["pattern_summary_md"] = str(pattern_md_path)

    llm_context = build_kinetics_llm_context(
        pattern_report,
        summary,
        plate_map=plate_map,
        parsed_metadata=parsed_metadata,
        artifact_paths=artifact_paths,
        plate_map_json=plate_map_path,
    )
    write_kinetics_llm_context(
        llm_context,
        llm_context_path,
        prompt_path=llm_prompt_path,
    )

    summary["annotated_csv"] = str(annotated_path)
    summary["summary_json"] = str(summary_path)
    summary["plate_map"] = str(plate_map_path)
    summary["pattern_summary_json"] = str(pattern_json_path)
    if pattern_md_path:
        summary["pattern_summary_md"] = str(pattern_md_path)
    summary["kinetics_llm_context_json"] = str(llm_context_path)
    summary["kinetics_llm_context_md"] = str(llm_prompt_path)
    return summary


def design_dose_response_plate(
    hits: list[dict],
    *,
    round_number: int = 2,
    max_compounds: int = 3,
) -> dict:
    """Build an 8-point dose-response plate map for top R1 hits."""
    wells = dict(CONTROL_WELLS)
    row_labels = list("BCDEFGH")
    concentrations = DOSE_RESPONSE_CONCENTRATIONS_UM[:8]
    selected = hits[:max_compounds]

    for row_idx, hit in enumerate(selected):
        if row_idx >= len(row_labels):
            break
        row = row_labels[row_idx]
        compound_id = hit["compound_id"]
        for col_idx, conc in enumerate(concentrations, start=1):
            well = f"{row}{col_idx}"
            wells[well] = {
                "compound_id": compound_id,
                "concentration_uM": conc,
                "role": "sample",
                "bucket": "dose_response",
                "functional_class": "positive",
                "source_hit_pct_inhibition": hit.get("pct_inhibition"),
            }

    return {
        "round": round_number,
        "assay_type": "dose_response",
        "final_volume_ul": 50,
        "compound_concentration_uM": "variable",
        "layout_notes": (
            f"Dose-response on top {len(selected)} R1 hits; "
            f"8-point series {concentrations} µM (one compound per row)."
        ),
        "wells": wells,
    }


def write_plate_map(plate_map: dict, path: str | Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plate_map, indent=2) + "\n")
    return str(path)
