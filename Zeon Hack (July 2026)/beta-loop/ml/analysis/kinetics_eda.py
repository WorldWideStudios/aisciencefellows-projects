"""Exploratory pattern detection for nitrocefin kinetic time courses.

Deterministic zone
------------------
``summarize_kinetics_patterns``, ``format_kinetics_summary``, and scoring in
``analysis.kinetics`` — fixed rules, reproducible JSON/CSV/markdown.

LLM zone
--------
``build_kinetics_llm_context`` / ``format_llm_interpretation_prompt`` assemble
*multiple deterministic inputs* into one payload marked ``feed_to_llm: true``.
An agent passes that payload to an LLM for interpretation (QC diagnosis,
surprise hits, next-step recommendations). The LLM must not replace scoring.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

import pandas as pd

from analysis.kinetics import EPS_ABS, classify_slope

ROWS = "ABCDEFGH"
FLAT_RANGE_EPS = 0.005
HIGH_INITIAL_TOP_N = 10
HIGH_INITIAL_MAD_K = 3.0
DEFAULT_EARLY_WINDOW = (30.0, 210.0)
DEFAULT_WAVELENGTHS = (490, 405)
METRICS_PER_WELL = 8  # Gen5 Results: 4 metrics × 2 wavelengths

# ---------------------------------------------------------------------------
# LLM zone — constants (deterministic assembly; interpretation is LLM-side)
# ---------------------------------------------------------------------------
LLM_CONTEXT_MARKER = "LLM_INTERPRETATION_INPUT"
LLM_CONTEXT_VERSION = "1.0"
LLM_CONTEXT_TYPE = "kinetics_interpretation"

DEFAULT_INTERPRETATION_TASKS = [
    "Summarize QC gate pass/fail and plausible root causes (controls, timing, slope window).",
    "Interpret notable pattern buckets (flat rows, high A0, rising, peak-decline, wavelength divergence).",
    "Reconcile compound hit calls with tier/substrate priors; flag surprises and timing suspects.",
    "Recommend follow-up (adjust slope window, re-run controls, dose-response picks) if warranted.",
]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    return df.rename(columns=renamed)


def _pick_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _well_sort_key(well: str) -> tuple[int, int]:
    return (ROWS.index(well[0]), int(well[1:]))


def _load_roles(plate_map_json: str | Path | None) -> dict[str, dict]:
    if not plate_map_json or not Path(plate_map_json).exists():
        return {}
    plate = json.loads(Path(plate_map_json).read_text())
    return dict(plate.get("wells", {}))


def _load_timecourses_from_parsed(
    parsed: dict,
    wavelength_nm: int,
) -> dict[str, pd.DataFrame]:
    """Build per-well DataFrames from gen5 parsed JSON timecourses."""
    series: dict[str, pd.DataFrame] = {}
    wl_key = str(wavelength_nm)
    for well, wl_map in parsed.get("timecourses", {}).items():
        points = wl_map.get(wl_key) or wl_map.get(wavelength_nm)
        if not points:
            continue
        series[well] = pd.DataFrame(points).sort_values("time_s")
    return series


def _load_timecourses_from_csv(
    kinetics_csv: str | Path,
    wavelength_nm: int | None = None,
) -> dict[str, pd.DataFrame]:
    df = _normalize_columns(pd.read_csv(kinetics_csv))
    well_col = _pick_column(df, ["well", "well_id", "well_position"])
    time_col = _pick_column(df, ["time_s", "time", "time_sec", "elapsed_s"])
    signal_col = _pick_column(
        df,
        ["absorbance_a490", "a490", "absorbance", "signal", "od490"],
    )
    if not well_col or not time_col or not signal_col:
        raise ValueError(
            f"CSV must include well, time, and signal columns. Found: {list(df.columns)}"
        )

    wl_col = _pick_column(df, ["wavelength_nm", "wavelength"])
    if wavelength_nm is not None and wl_col:
        df = df[df[wl_col] == wavelength_nm]

    series: dict[str, pd.DataFrame] = {}
    for well, group in df.groupby(well_col):
        g = group.sort_values(time_col).rename(columns={time_col: "time_s", signal_col: "absorbance"})
        series[str(well)] = g[["time_s", "absorbance"]].reset_index(drop=True)
    return series


def _compute_slope(group: pd.DataFrame, window_start: float, window_end: float) -> float | None:
    window = group[(group["time_s"] >= window_start) & (group["time_s"] <= window_end)]
    if len(window) < 2:
        return None
    dt = window["time_s"].diff().mean()
    if dt == 0:
        return None
    return float(window["absorbance"].diff().mean() / dt)


def _well_features(
    group: pd.DataFrame,
    *,
    early_window: tuple[float, float],
    slope_no_tem1_ref: float,
) -> dict[str, Any]:
    g = group.sort_values("time_s")
    times = g["time_s"].tolist()
    values = g["absorbance"].tolist()
    a0 = float(values[0])
    a_end = float(values[-1])
    amax = float(max(values))
    amax_idx = values.index(amax)
    t_peak = float(times[amax_idx])
    t_last = float(times[-1])
    delta = a_end - a0
    value_range = amax - float(min(values))

    early_start, early_end = early_window
    slope_early = _compute_slope(g, early_start, early_end)
    late_start = times[max(0, int(len(times) * 0.67))]
    slope_late = _compute_slope(g, late_start, t_last)

    slope_class = (
        classify_slope(slope_early, slope_no_tem1_ref)
        if slope_early is not None
        else "flat"
    )

    return {
        "A0": round(a0, 4),
        "A_end": round(a_end, 4),
        "Amax": round(amax, 4),
        "t_peak_s": t_peak,
        "delta": round(delta, 4),
        "range": round(value_range, 4),
        "slope_early": round(slope_early, 8) if slope_early is not None else None,
        "slope_late": round(slope_late, 8) if slope_late is not None else None,
        "slope_class_early": slope_class,
        "peak_at_end": abs(t_peak - t_last) < 1.0,
    }


def _mad(values: list[float]) -> float:
    if not values:
        return 0.0
    med = statistics.median(values)
    return float(statistics.median(abs(v - med) for v in values))


def _format_hms(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def summarize_kinetics_patterns(
    kinetics_csv: str | Path,
    plate_map_json: str | Path | None = None,
    *,
    wavelengths: tuple[int, ...] = DEFAULT_WAVELENGTHS,
    parsed_json: str | Path | None = None,
    flat_range_eps: float = FLAT_RANGE_EPS,
    early_window: tuple[float, float] = DEFAULT_EARLY_WINDOW,
    high_initial_top_n: int = HIGH_INITIAL_TOP_N,
    flat_row_labels: tuple[str, ...] = ("A", "H"),
    gen5_results: dict[str, dict[int, dict[str, Any]]] | None = None,
) -> dict:
    """Compute deterministic pattern buckets from kinetic time courses."""
    roles = _load_roles(plate_map_json)
    parsed: dict | None = None
    if parsed_json and Path(parsed_json).exists():
        parsed = json.loads(Path(parsed_json).read_text())

    primary_wl = wavelengths[0]
    if parsed:
        series_by_wl = {wl: _load_timecourses_from_parsed(parsed, wl) for wl in wavelengths}
    else:
        series_by_wl = {primary_wl: _load_timecourses_from_csv(kinetics_csv, primary_wl)}
        for wl in wavelengths[1:]:
            if parsed:
                series_by_wl[wl] = _load_timecourses_from_parsed(parsed, wl)
            elif wl != primary_wl:
                series_by_wl[wl] = {}

    primary_series = series_by_wl.get(primary_wl, {})
    if not primary_series:
        raise ValueError(f"No time courses found for {primary_wl} nm")

    no_tem1_slopes: list[float] = []
    for well, group in primary_series.items():
        if roles.get(well, {}).get("role") == "no_tem1":
            slope = _compute_slope(group, early_window[0], early_window[1])
            if slope is not None:
                no_tem1_slopes.append(slope)
    slope_no_tem1_ref = statistics.median(no_tem1_slopes) if no_tem1_slopes else EPS_ABS / 3

    per_well: dict[str, dict[str, Any]] = {}
    for well, group in primary_series.items():
        spec = roles.get(well, {})
        features = _well_features(
            group,
            early_window=early_window,
            slope_no_tem1_ref=slope_no_tem1_ref,
        )
        per_well[well] = {
            **features,
            "role": spec.get("role"),
            "compound_id": spec.get("compound_id"),
            "concentration_uM": spec.get("concentration_uM"),
        }

    flat_baseline_wells: list[str] = []
    for well, feat in per_well.items():
        if feat["range"] < flat_range_eps:
            flat_baseline_wells.append(well)

    flat_rows: dict[str, list[str]] = {}
    for row in flat_row_labels:
        row_wells = [w for w in flat_baseline_wells if w[0] == row]
        if row_wells:
            flat_rows[row] = sorted(row_wells, key=_well_sort_key)

    a0_values = [(well, feat["A0"]) for well, feat in per_well.items()]
    a0_sorted = sorted(a0_values, key=lambda x: x[1], reverse=True)
    a0_nums = [v for _, v in a0_values]
    a0_median = statistics.median(a0_nums) if a0_nums else 0.0
    a0_mad = _mad(a0_nums)
    high_threshold = a0_median + HIGH_INITIAL_MAD_K * max(a0_mad, 0.01)
    high_initial = [
        {"well": well, "A0": a0, **{k: per_well[well].get(k) for k in ("compound_id", "role")}}
        for well, a0 in a0_sorted[:high_initial_top_n]
    ]
    high_initial_mad = [
        {"well": well, "A0": a0, **{k: per_well[well].get(k) for k in ("compound_id", "role")}}
        for well, a0 in a0_values
        if a0 >= high_threshold
    ]

    rising = [
        {
            "well": well,
            "A0": feat["A0"],
            "A_end": feat["A_end"],
            "slope_early": feat["slope_early"],
            "compound_id": feat.get("compound_id"),
            "role": feat.get("role"),
        }
        for well, feat in per_well.items()
        if feat["delta"] > flat_range_eps
        and (feat["slope_early"] or 0) > max(slope_no_tem1_ref * 3, EPS_ABS / 100)
    ]
    rising.sort(key=lambda x: x["slope_early"] or 0, reverse=True)

    t_last_global = max(
        (float(g["time_s"].max()) for g in primary_series.values()),
        default=900.0,
    )
    peak_decline = [
        {
            "well": well,
            "A0": feat["A0"],
            "Amax": feat["Amax"],
            "A_end": feat["A_end"],
            "t_peak_s": feat["t_peak_s"],
            "t_peak": _format_hms(feat["t_peak_s"]),
            "compound_id": feat.get("compound_id"),
            "role": feat.get("role"),
        }
        for well, feat in per_well.items()
        if not feat["peak_at_end"]
        and feat["t_peak_s"] < 0.8 * t_last_global
        and feat["Amax"] > a0_median + 0.05
        and feat["A_end"] < feat["Amax"] - 0.01
        and feat["range"] > flat_range_eps
    ]
    peak_decline.sort(key=lambda x: x["Amax"] - x["A_end"], reverse=True)

    wavelength_divergence: list[dict] = []
    if len(wavelengths) > 1:
        secondary_wl = wavelengths[1]
        secondary = series_by_wl.get(secondary_wl, {})
        for well in primary_series:
            if well not in secondary:
                continue
            a0_primary = per_well[well]["A0"]
            a0_secondary = float(secondary[well].sort_values("time_s")["absorbance"].iloc[0])
            if abs(a0_primary - a0_secondary) >= 0.05:
                wavelength_divergence.append(
                    {
                        "well": well,
                        f"A0_{primary_wl}": round(a0_primary, 4),
                        f"A0_{secondary_wl}": round(a0_secondary, 4),
                        "compound_id": per_well[well].get("compound_id"),
                        "role": per_well[well].get("role"),
                    }
                )
        wavelength_divergence.sort(
            key=lambda x: abs(x[f"A0_{primary_wl}"] - x[f"A0_{secondary_wl}"]),
            reverse=True,
        )

    negative_slope_wells: list[dict] = []
    if gen5_results:
        for well, wl_map in gen5_results.items():
            for wl, metrics in wl_map.items():
                max_v = metrics.get("max_v")
                if max_v is not None and max_v < 0:
                    negative_slope_wells.append(
                        {
                            "well": well,
                            "wavelength_nm": wl,
                            "max_v": max_v,
                            "source": "gen5_results",
                            "compound_id": per_well.get(well, {}).get("compound_id"),
                        }
                    )
    else:
        for well, feat in per_well.items():
            if (feat["slope_early"] or 0) < 0 and (feat["slope_late"] or 0) < 0:
                negative_slope_wells.append(
                    {
                        "well": well,
                        "wavelength_nm": primary_wl,
                        "slope_early": feat["slope_early"],
                        "slope_late": feat["slope_late"],
                        "source": "computed",
                        "compound_id": feat.get("compound_id"),
                    }
                )

    gen5_max_v_highlights: list[dict] = []
    if gen5_results:
        for well, wl_map in gen5_results.items():
            for wl, metrics in wl_map.items():
                max_v = metrics.get("max_v")
                if max_v is not None and max_v >= 10:
                    gen5_max_v_highlights.append(
                        {
                            "well": well,
                            "wavelength_nm": wl,
                            "max_v": max_v,
                            "lagtime": metrics.get("lagtime"),
                            "compound_id": per_well.get(well, {}).get("compound_id"),
                        }
                    )
        gen5_max_v_highlights.sort(key=lambda x: abs(x["max_v"]), reverse=True)

    return {
        "primary_wavelength_nm": primary_wl,
        "wavelengths": list(wavelengths),
        "early_window_s": list(early_window),
        "flat_range_eps": flat_range_eps,
        "flat_rows": flat_rows,
        "flat_baseline_wells": sorted(flat_baseline_wells, key=_well_sort_key),
        "high_initial": high_initial,
        "high_initial_mad": high_initial_mad,
        "rising": rising,
        "peak_decline": peak_decline,
        "wavelength_divergence": wavelength_divergence,
        "negative_slope_wells": negative_slope_wells,
        "gen5_max_v_highlights": gen5_max_v_highlights,
        "per_well": per_well,
        "slope_no_tem1_ref": slope_no_tem1_ref,
    }


def _well_label(well: str, roles: dict[str, dict]) -> str:
    spec = roles.get(well, {})
    cid = spec.get("compound_id")
    role = spec.get("role")
    if cid:
        return f"{well} ({cid})"
    if role:
        return f"{well} [{role}]"
    return well


def format_kinetics_summary(
    report: dict,
    plate_map_json: str | Path | None = None,
) -> str:
    """Format a deterministic markdown summary (template-based, no LLM)."""
    roles = _load_roles(plate_map_json)
    wl = report["primary_wavelength_nm"]
    lines = [
        "# Kinetics pattern summary",
        "",
        f"Primary wavelength: {wl} nm",
        f"Early slope window: {report['early_window_s'][0]:g}–{report['early_window_s'][1]:g} s",
        "",
        f"## Notable signal patterns ({wl} nm)",
        "",
    ]

    if report["flat_rows"]:
        for row, wells in sorted(report["flat_rows"].items()):
            sample = report["per_well"].get(wells[0], {})
            lines.append(
                f"- **Row {row}** ({', '.join(wells)}): flat baseline "
                f"~{sample.get('A0', '?')} (range < {report['flat_range_eps']})"
            )
        lines.append("")

    if report["high_initial"]:
        lines.append("**High initial signal (t=0):**")
        for item in report["high_initial"][:8]:
            label = _well_label(item["well"], roles)
            lines.append(f"- {label}: A0 = {item['A0']}")
        lines.append("")

    if report["rising"]:
        lines.append("**Rising kinetics (early-window slope above no-TEM-1 baseline):**")
        for item in report["rising"][:10]:
            label = _well_label(item["well"], roles)
            lines.append(
                f"- {label}: {item['A0']} → {item['A_end']} over run "
                f"(slope_early = {item['slope_early']})"
            )
        lines.append("")

    if report["peak_decline"]:
        lines.append("**Peak then decline:**")
        for item in report["peak_decline"][:8]:
            label = _well_label(item["well"], roles)
            lines.append(
                f"- {label}: peak {item['Amax']} at {item['t_peak']}, "
                f"ends {item['A_end']}"
            )
        lines.append("")

    secondary_wl = report["wavelengths"][1] if len(report["wavelengths"]) > 1 else None
    if secondary_wl and report["wavelength_divergence"]:
        lines.append(f"## Wavelength divergence ({wl} vs {secondary_wl} nm)")
        lines.append("")
        for item in report["wavelength_divergence"][:8]:
            label = _well_label(item["well"], roles)
            lines.append(
                f"- {label}: A0 {item[f'A0_{wl}']} vs {item[f'A0_{secondary_wl}']}"
            )
        lines.append("")

    if report["gen5_max_v_highlights"]:
        lines.append(f"## Gen5 Results highlights (Max V, QC cross-check)")
        lines.append("")
        for item in report["gen5_max_v_highlights"][:10]:
            label = _well_label(item["well"], roles)
            lag = item.get("lagtime") or "?"
            lines.append(
                f"- {label} @ {item['wavelength_nm']} nm: Max V = {item['max_v']}, "
                f"lagtime = {lag}"
            )
        lines.append("")

    if report["negative_slope_wells"]:
        lines.append("**Negative slope / Max V:**")
        for item in report["negative_slope_wells"][:8]:
            label = _well_label(item["well"], roles)
            if item.get("source") == "gen5_results":
                lines.append(
                    f"- {label}: Gen5 Max V = {item['max_v']} @ {item['wavelength_nm']} nm"
                )
            else:
                lines.append(f"- {label}: computed early/late slopes negative")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_pattern_summary(
    report: dict,
    json_path: str | Path,
    *,
    markdown_path: str | Path | None = None,
    plate_map_json: str | Path | None = None,
) -> tuple[Path, Path | None]:
    """Write pattern_summary JSON and optional markdown."""
    json_out = Path(json_path)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n")

    md_out = None
    if markdown_path:
        md_out = Path(markdown_path)
        md_out.write_text(format_kinetics_summary(report, plate_map_json))
    return json_out, md_out


# ---------------------------------------------------------------------------
# LLM zone — merge deterministic inputs into one agent-facing payload
# ---------------------------------------------------------------------------


def _condense_compounds(round_summary: dict) -> list[dict[str, Any]]:
    compounds = round_summary.get("compounds") or {}
    rows: list[dict[str, Any]] = []
    if isinstance(compounds, dict):
        for compound_id, info in compounds.items():
            rows.append(
                {
                    "compound_id": compound_id,
                    "median_pct_inhibition": info.get("median_pct_inhibition"),
                    "label": info.get("label"),
                    "timing_suspect_reps": info.get("timing_suspect_reps", 0),
                    "wells": info.get("wells", []),
                }
            )
    rows.sort(key=lambda r: r.get("median_pct_inhibition") or 0, reverse=True)
    return rows


def _condense_pattern_buckets(pattern_report: dict) -> dict[str, Any]:
    """Trim pattern report to LLM-relevant buckets (omit full per_well grid)."""
    return {
        "primary_wavelength_nm": pattern_report.get("primary_wavelength_nm"),
        "wavelengths": pattern_report.get("wavelengths"),
        "early_window_s": pattern_report.get("early_window_s"),
        "flat_rows": pattern_report.get("flat_rows"),
        "flat_baseline_wells": pattern_report.get("flat_baseline_wells"),
        "high_initial": pattern_report.get("high_initial", [])[:12],
        "rising": pattern_report.get("rising", [])[:15],
        "peak_decline": pattern_report.get("peak_decline", [])[:12],
        "wavelength_divergence": pattern_report.get("wavelength_divergence", [])[:12],
        "negative_slope_wells": pattern_report.get("negative_slope_wells", [])[:12],
        "gen5_max_v_highlights": pattern_report.get("gen5_max_v_highlights", [])[:12],
        "slope_no_tem1_ref": pattern_report.get("slope_no_tem1_ref"),
    }


def build_kinetics_llm_context(
    pattern_report: dict,
    round_summary: dict,
    *,
    plate_map: dict | None = None,
    parsed_metadata: dict | None = None,
    artifact_paths: dict[str, str] | None = None,
    include_deterministic_markdown: bool = True,
    plate_map_json: str | Path | None = None,
    interpretation_tasks: list[str] | None = None,
) -> dict[str, Any]:
    """Merge deterministic analysis outputs into a single LLM-facing payload.

    This function does **not** call an LLM. It only packages inputs produced by:

    - ``analyze_kinetics_file`` → ``round_summary`` (hits, QC, compounds)
    - ``summarize_kinetics_patterns`` → ``pattern_report`` (pattern buckets)
    - ``plate_map`` (layout / roles)
    - ``parsed_metadata`` (reader protocol, temperature, kinetic duration)
    - ``artifact_paths`` (paths to CSV/JSON siblings for traceability)

    Returns a dict with ``feed_to_llm: true`` and ``context_marker`` set.
    """
    plate_map = plate_map or {}
    tasks = interpretation_tasks or DEFAULT_INTERPRETATION_TASKS

    run_meta: dict[str, Any] = {
        "round": round_summary.get("round"),
        "run": plate_map.get("run"),
        "version": plate_map.get("version"),
        "assay_type": plate_map.get("assay_type"),
        "layout_notes": plate_map.get("layout_notes"),
        "slope_window_start_s": round_summary.get("slope_window_start_s"),
        "slope_window_end_s": round_summary.get("slope_window_end_s"),
    }
    if parsed_metadata:
        run_meta.update(
            {
                "reader_type": parsed_metadata.get("reader_type"),
                "setpoint_temperature_c": parsed_metadata.get("setpoint_temperature_c"),
                "kinetic_runtime_s": parsed_metadata.get("kinetic_runtime_s"),
                "kinetic_interval_s": parsed_metadata.get("kinetic_interval_s"),
                "kinetic_reads": parsed_metadata.get("kinetic_reads"),
                "experiment_path": parsed_metadata.get("experiment_path"),
                "protocol_path": parsed_metadata.get("protocol_path"),
            }
        )

    deterministic_inputs = {
        "run_metadata": run_meta,
        "qc_gates": round_summary.get("qc_gates"),
        "control_stats": round_summary.get("control_stats"),
        "hits": round_summary.get("hits"),
        "compounds": _condense_compounds(round_summary),
        "failed_wells": round_summary.get("failed_wells"),
        "wells_timing_suspect": round_summary.get("wells_timing_suspect"),
        "pre_read_overage_wells": round_summary.get("pre_read_overage_wells"),
        "timing_stagger_min": round_summary.get("timing_stagger_min"),
        "pattern_buckets": _condense_pattern_buckets(pattern_report),
        "next_plate_design_suggestion": round_summary.get("next_plate_design"),
    }

    context: dict[str, Any] = {
        # --- LLM zone marker (search for this key in artifacts) ---
        "feed_to_llm": True,
        "context_marker": LLM_CONTEXT_MARKER,
        "context_type": LLM_CONTEXT_TYPE,
        "context_version": LLM_CONTEXT_VERSION,
        "interpretation_tasks": tasks,
        "deterministic_input_sources": {
            "round_summary": "analysis.kinetics.analyze_kinetics_file",
            "pattern_report": "analysis.kinetics_eda.summarize_kinetics_patterns",
            "plate_map": "data/screens/.../plate_map.json",
            "parsed_metadata": "gen5_pdf.parse_gen5_kinetic_pdf (optional)",
        },
        "deterministic_inputs": deterministic_inputs,
        "artifact_paths": artifact_paths or {},
    }

    if include_deterministic_markdown:
        context["deterministic_markdown"] = format_kinetics_summary(
            pattern_report, plate_map_json
        )

    return context


def format_llm_interpretation_prompt(context: dict[str, Any]) -> str:
    """Render a ready-to-send user message for an LLM from ``build_kinetics_llm_context``."""
    if not context.get("feed_to_llm"):
        raise ValueError("context missing feed_to_llm marker — not an LLM payload")

    inputs = context.get("deterministic_inputs", {})
    meta = inputs.get("run_metadata", {})
    qc = inputs.get("qc_gates") or {}
    patterns = inputs.get("pattern_buckets") or {}

    lines = [
        "# Kinetics interpretation request",
        "",
        f"Context marker: `{context.get('context_marker')}` v{context.get('context_version')}",
        "",
        "## Your tasks",
    ]
    for task in context.get("interpretation_tasks", []):
        lines.append(f"- {task}")
    lines.append("")
    lines.append("## Run metadata (deterministic)")
    lines.append(f"- Round {meta.get('round')} | slope window {meta.get('slope_window_start_s')}–{meta.get('slope_window_end_s')} s")
    if meta.get("setpoint_temperature_c"):
        lines.append(f"- Incubator setpoint: {meta.get('setpoint_temperature_c')} °C")
    if meta.get("kinetic_runtime_s"):
        lines.append(f"- Kinetic duration: {meta.get('kinetic_runtime_s')} s")
    lines.append("")
    lines.append("## QC gates (deterministic)")
    for key, val in sorted(qc.items()):
        lines.append(f"- {key}: {val}")
    lines.append("")
    lines.append("## Hits (deterministic)")
    for hit in inputs.get("hits") or []:
        lines.append(
            f"- {hit.get('compound_id')}: {hit.get('pct_inhibition')}% "
            f"@ {hit.get('concentration_uM')} µM"
        )
    if not inputs.get("hits"):
        lines.append("- (none)")
    lines.append("")
    lines.append("## Pattern buckets (deterministic)")
    if patterns.get("flat_rows"):
        lines.append(f"- Flat rows: {patterns['flat_rows']}")
    if patterns.get("high_initial"):
        tops = ", ".join(
            f"{w['well']} A0={w['A0']}" for w in patterns["high_initial"][:6]
        )
        lines.append(f"- High initial signal: {tops}")
    if patterns.get("rising"):
        risers = ", ".join(
            f"{w['well']} ({w['A0']}→{w['A_end']})" for w in patterns["rising"][:6]
        )
        lines.append(f"- Rising: {risers}")
    if patterns.get("peak_decline"):
        peaks = ", ".join(
            f"{w['well']} peak@{w.get('t_peak')}" for w in patterns["peak_decline"][:6]
        )
        lines.append(f"- Peak then decline: {peaks}")
    lines.append("")
    lines.append("## Compound scores (deterministic)")
    for compound in (inputs.get("compounds") or [])[:12]:
        lines.append(
            f"- {compound.get('compound_id')}: {compound.get('median_pct_inhibition')}% "
            f"({compound.get('label')})"
        )
    lines.append("")
    if context.get("deterministic_markdown"):
        lines.append("## Full deterministic pattern summary")
        lines.append("")
        lines.append(context["deterministic_markdown"].rstrip())
    lines.append("")
    lines.append("---")
    lines.append(
        "Respond with: (1) QC assessment, (2) notable patterns, "
        "(3) hit confidence, (4) recommended next steps."
    )
    return "\n".join(lines)


def write_kinetics_llm_context(
    context: dict[str, Any],
    json_path: str | Path,
    *,
    prompt_path: str | Path | None = None,
) -> tuple[Path, Path | None]:
    """Write LLM context JSON and optional interpretation prompt markdown."""
    if not context.get("feed_to_llm"):
        raise ValueError("refusing to write: context is not marked feed_to_llm")

    json_out = Path(json_path)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(context, indent=2) + "\n")

    prompt_out = None
    if prompt_path:
        prompt_out = Path(prompt_path)
        prompt_out.write_text(format_llm_interpretation_prompt(context))
    return json_out, prompt_out
