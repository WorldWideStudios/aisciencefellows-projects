"""Analyze stage: turns a plate-reader export into a fit and a decision, for all
three round types.

`parse_gen5_export`'s "kinetic" branch parses a real BioTek Gen5 ELx808 kinetic
export (data/platereader/<execution_id>/*.pdf) — verified against an actual
hardware run's PDF on 2026-07-26. The export is a per-wavelength, per-timepoint
table in 10-well-wide chunks ("Time  T° <wavelength>  A1 A2 ... A10", repeating
across the full 96-well plate for 490 then 405 nm), followed by a "Results"
section of the reader's own per-well curve stats which this parser does not use
(the initial-rate fit is redone here from the raw trace instead, matching what
the rest of the pipeline expects).

`parse_gen5_export`'s "endpoint" branch parses a real export too, reusing the
kinetic parser on the assumption the endpoint report shares the same Gen5/ELx808
table layout (per the wet-lab side, the two exports are expected to largely
match) and takes each well's last reported value as its endpoint reading. When
no PDF exists yet at data/platereader/<execution_id>/ for a given execution, it
falls back to synthetic data seeded from the execution_id, so
inhibitor_dose_response and cfps_expression analysis keep working end to end
until that execution's real export lands.

Like plan_agent.py, the real work lives in plain functions; the ADK `Agent` at the
bottom just wraps them as tools for a human steering Analyze conversationally.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import numpy as np
from google.adk.agents import Agent
from pypdf import PdfReader
from scipy.optimize import curve_fit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
import beads_writer as bw  # noqa: E402
from watch_execution import DATA_LOGS_DIR, DATA_PLATEREADER_DIR  # noqa: E402

RESULTS_DIR = PROJECT_ROOT / "pipeline" / "results"
INPUTS_DIR = PROJECT_ROOT / "inputs"

KINETIC_WAVELENGTH = "490"  # nitrocefin's colorimetric readout


def _find_platereader_pdf(execution_id: str) -> Path:
    export_dir = DATA_PLATEREADER_DIR / execution_id
    if not export_dir.exists():
        raise FileNotFoundError(
            f"no plate-reader export at {export_dir} — drop the Gen5 PDF there "
            f"(data/platereader/{execution_id}/<name>.pdf) before analyzing"
        )
    pdfs = sorted(export_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"{export_dir} exists but has no .pdf in it")
    return pdfs[0]


_HEADER_RE = re.compile(r"^Time\s+T°\s*(\d+)\s+(.+)$")
_ROW_RE = re.compile(r"^(\d+):(\d{2}):(\d{2})\s+[\d.]+\s+(.+)$")


def _parse_kinetic_pdf(pdf_path: Path) -> dict[str, dict[str, dict[str, list]]]:
    """Every wavelength's per-well kinetic trace out of a Gen5 kinetic export.
    Returns {wavelength: {well: {"timepoints_min": [...], "values": [...]}}}.
    Stops at the "Results" section (the reader's own per-well fit stats, which
    this pipeline recomputes itself rather than trusting Gen5's).
    """
    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages)
    traces: dict[str, dict[str, dict[str, list]]] = {}
    current_wavelength: str | None = None
    current_wells: list[str] = []

    for line in text.splitlines():
        if line.strip() == "Results":
            break
        header = _HEADER_RE.match(line)
        if header:
            current_wavelength, wells_str = header.groups()
            current_wells = wells_str.split()
            traces.setdefault(current_wavelength, {})
            for w in current_wells:
                traces[current_wavelength].setdefault(w, {"timepoints_min": [], "values": []})
            continue
        row = _ROW_RE.match(line)
        if row and current_wavelength:
            hh, mm, ss, rest = row.groups()
            t_min = int(hh) * 60 + int(mm) + int(ss) / 60
            values = rest.split()
            n = len(current_wells)
            if len(values) != n:
                # The last row before a page break often has the page footer
                # ("<n> of 23") glued onto its final value with no separating
                # space, e.g. "0.040" + "2 of 23" -> "0.0402 of 23". Recover the
                # real value if that's exactly what happened; otherwise this
                # isn't a data row for the current well block (e.g. a Results row).
                if len(values) == n + 2 and values[n] == "of":
                    m = re.match(r"^\d+\.\d{3}", values[n - 1])
                    if not m:
                        continue
                    values = values[: n - 1] + [m.group(0)]
                else:
                    continue
            for w, v in zip(current_wells, values):
                traces[current_wavelength][w]["timepoints_min"].append(t_min)
                traces[current_wavelength][w]["values"].append(float(v))
    return traces


def _parse_gen5_kinetic_export(execution_id: str, wells: list[str] | None) -> dict:
    pdf_path = _find_platereader_pdf(execution_id)
    traces = _parse_kinetic_pdf(pdf_path)
    if KINETIC_WAVELENGTH not in traces:
        raise RuntimeError(
            f"{pdf_path} has no {KINETIC_WAVELENGTH} nm table — wavelengths found: "
            f"{sorted(traces)}"
        )
    by_well = traces[KINETIC_WAVELENGTH]
    if wells is None:
        wells = sorted(by_well)
    missing = [w for w in wells if w not in by_well]
    if missing:
        raise RuntimeError(
            f"{pdf_path} has no {KINETIC_WAVELENGTH} nm data for well(s) {missing} — "
            f"plate had wells {sorted(by_well)}"
        )
    return {
        w: {"timepoints_min": by_well[w]["timepoints_min"], "a490": by_well[w]["values"]}
        for w in wells
    }


# --- Gen5 endpoint export parsing -------------------------------------------------

def _parse_gen5_endpoint_export(execution_id: str, wells: list[str] | None) -> dict:
    """Real parsing if a PDF is already sitting at data/platereader/<execution_id>/,
    else the synthetic stub (seeded from execution_id, so repeat calls agree).

    The endpoint export is expected to share the kinetic export's table layout
    (same Gen5/ELx808 report format, just fewer — possibly one — timepoints), so
    this reuses `_parse_kinetic_pdf` and takes each well's LAST reported value as
    its endpoint reading rather than assuming a different table shape. If that
    assumption turns out wrong once a real endpoint sample is in hand, only this
    function needs to change.
    """
    if wells is None:
        raise ValueError(
            "wells is required — name the wells that were actually dosed; a Gen5 export "
            "covers the whole plate and most of it is empty background, not worth analyzing"
        )
    export_dir = DATA_PLATEREADER_DIR / execution_id
    if export_dir.exists() and any(export_dir.glob("*.pdf")):
        pdf_path = _find_platereader_pdf(execution_id)
        traces = _parse_kinetic_pdf(pdf_path)
        wavelength = KINETIC_WAVELENGTH if KINETIC_WAVELENGTH in traces else next(iter(traces), None)
        if wavelength is None:
            raise RuntimeError(f"{pdf_path} has no wavelength tables at all")
        by_well = traces[wavelength]
        missing = [w for w in wells if w not in by_well]
        if missing:
            raise RuntimeError(f"{pdf_path} has no data for well(s) {missing} — plate had wells {sorted(by_well)}")
        return {w: by_well[w]["values"][-1] for w in wells}
    # STUB fallback — no real export for this execution yet.
    rng = random.Random(execution_id)
    return {w: round(rng.uniform(0.05, 1.2), 4) for w in wells}


def parse_gen5_export(execution_id: str, kind: str, wells: list[str] | None = None) -> dict:
    """`kind` is "endpoint" (one value per well) or "kinetic" (a value per well
    per timepoint) — both parse real Gen5 PDFs at
    data/platereader/<execution_id>/*.pdf when one exists. `wells=None` is
    allowed only for "kinetic" (means every well found in the export); "endpoint"
    always requires an explicit well list. Endpoint export parsing falls back to
    a synthetic stub when no PDF is present yet for that execution_id.
    """
    if kind == "kinetic":
        return _parse_gen5_kinetic_export(execution_id, wells)
    if kind == "endpoint":
        return _parse_gen5_endpoint_export(execution_id, wells)
    raise ValueError(f"unknown export kind: {kind!r}")


def _run_inputs_for_execution(execution_id: str) -> dict:
    for exec_dir in DATA_LOGS_DIR.glob(f"{execution_id}"):
        for run_dir in exec_dir.iterdir():
            ri = run_dir / "run_inputs.json"
            if ri.exists():
                return json.loads(ri.read_text())
    return {}


def _execution_id_for_kind(round_id: str, kind: str) -> str | None:
    for child in bw.list_children(round_id):
        if f"execution_kind:{kind}" in child.get("labels", []):
            return child.get("metadata", {}).get("execution_id")
    return None


def _write_results(round_id: str, results: dict) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{round_id}.json"
    out.write_text(json.dumps(results, indent=2) + "\n")
    return out


# --- kinetics round: Michaelis-Menten over the E x S grid ----------------------

def _initial_rate(timepoints_min: list[float], a490: list[float]) -> float:
    """Slope of the first few points — a quick, honest stand-in for a proper
    linear-region fit over the true linear phase of the curve."""
    n = min(4, len(timepoints_min))
    t = np.array(timepoints_min[:n])
    y = np.array(a490[:n])
    if n < 2 or np.allclose(t, t[0]):
        return 0.0
    slope, _ = np.polyfit(t, y, 1)
    return float(slope)


def _michaelis_menten(s, vmax, km):
    return vmax * s / (km + s)


def analyze_kinetics_round(round_id: str) -> dict:
    preset_path = INPUTS_DIR / f"{round_id}.json"
    if not preset_path.exists():
        raise FileNotFoundError(f"no input preset for {round_id} — was it planned via plan_agent?")
    inputs = json.loads(preset_path.read_text())

    exec_id = _execution_id_for_kind(round_id, "run")
    if not exec_id:
        raise RuntimeError(f"{round_id} has no linked execution yet — run watch_execution first")

    # Recover the 3x3 grid + concentrations from the preset (see plan_agent.plan_kinetics_round).
    points = []
    for i in range(1, 4):
        for j in range(1, 4):
            pos = f"pt_e{i}s{j}"
            well = inputs.get(f"{pos}_well")
            if well:
                points.append({"well": well, "e_level": i, "s_level": j})
    wells = [p["well"] for p in points]

    traces = parse_gen5_export(exec_id, "kinetic", wells)
    for p in points:
        trace = traces[p["well"]]
        p["initial_rate"] = _initial_rate(trace["timepoints_min"], trace["a490"])

    # One Michaelis-Menten fit per enzyme level, rate vs substrate "level" (1..3)
    # standing in for concentration — real units come from the preset's *_vol_ul
    # once the real stock concentrations are known.
    fits = {}
    for i in range(1, 4):
        level_points = [p for p in points if p["e_level"] == i]
        s = np.array([p["s_level"] for p in level_points], dtype=float)
        v = np.array([p["initial_rate"] for p in level_points], dtype=float)
        try:
            (vmax, km), _ = curve_fit(_michaelis_menten, s, v, p0=[max(v.max(), 1e-6), 1.0], maxfev=2000)
            fits[f"enzyme_level_{i}"] = {"vmax": float(vmax), "km": float(km)}
        except RuntimeError:
            fits[f"enzyme_level_{i}"] = {"vmax": None, "km": None, "note": "fit did not converge"}

    # Decision: pick the enzyme level with the best-converged fit, recommend the
    # substrate level nearest 4x its Km (~80% Vmax) as the working concentration,
    # and the run's own read cadence as the recommended endpoint timing.
    converged = {k: f for k, f in fits.items() if f.get("km") is not None}
    if converged:
        best_level_key = max(converged, key=lambda k: converged[k]["vmax"] or 0)
        best_km = converged[best_level_key]["km"]
        recommended_s_level = min(3, max(1, round(best_km))) if best_km else 2
    else:
        best_level_key, recommended_s_level = None, 2

    results = {
        "round_id": round_id, "execution_id": exec_id, "points": points, "fits": fits,
        "recommended_nitrocefin_level": recommended_s_level,
        "recommended_endpoint_minutes": 120,  # PLACEHOLDER, matches the CFPS kit's stated ~2h window
        "best_fit": best_level_key,
    }
    _write_results(round_id, results)
    bw.note(round_id, f"Kinetics fit: {json.dumps(fits)}")
    bw.set_stage(round_id, "decided", reason=f"recommend nitrocefin level {recommended_s_level} (fit: {best_level_key})")
    return results


# --- ad-hoc kinetic export: no beads preset needed ------------------------------

def analyze_execution_kinetic_export(execution_id: str, wells: list[str], round_id: str | None = None) -> dict:
    """Fit per-well initial rates straight from a Gen5 kinetic PDF, for a run that
    has no input preset to recover a plate layout from — e.g. a run recovered from
    an app log export, or an unplanned/deviated round.

    Unlike analyze_kinetics_round, this does NOT assume a 3x3 enzyme x substrate
    grid or fit Michaelis-Menten (there is no known condition per well without a
    preset) — it reports the observed initial rate for each well so the operator
    can read it against whatever they know the plate layout was.

    `wells` is required and must name only the wells that actually got reagent —
    a Gen5 export covers the full 96-well plate, and most of that is empty plate
    background, not data worth fitting or showing. There's no reliable way to
    infer "processed" from the trace alone (an unused well and a near-zero-rate
    used well both read as flat noise), so the operator must say which wells were
    dosed. If round_id is given (e.g. an unplanned round beads created for this
    execution), results are also written to pipeline/results/<round_id>.json and
    noted on that round; results are always written to
    pipeline/results/<execution_id>.json too.
    """
    if not wells:
        raise ValueError(
            "wells is required — name the wells that were actually dosed (ask the operator "
            "if you don't know); a Gen5 export covers the whole plate and most of it is "
            "empty background, not worth analyzing or showing"
        )
    traces = parse_gen5_export(execution_id, "kinetic", wells)
    well_rates = {
        w: {"initial_rate": _initial_rate(t["timepoints_min"], t["a490"]),
            "n_timepoints": len(t["timepoints_min"])}
        for w, t in traces.items()
    }
    results = {
        "kind": "raw_kinetic_export",
        "execution_id": execution_id,
        "round_id": round_id,
        "well_rates": well_rates,
    }
    _write_results(execution_id, results)
    if round_id:
        _write_results(round_id, results)
        bw.note(round_id, f"Raw kinetic export analyzed ({len(well_rates)} well(s)): {json.dumps(well_rates)}")
    return results


# --- inhibitor_dose_response round: 4-parameter logistic -> IC50 ---------------

def _four_pl(x, bottom, top, ic50, hill):
    return bottom + (top - bottom) / (1 + (x / ic50) ** hill)


def _export_data_source(execution_id: str) -> str:
    """Whether an endpoint analysis is about to read a real Gen5 PDF or fall back
    to the synthetic stub — for results to carry honestly rather than the caller
    having to guess from the numbers."""
    export_dir = DATA_PLATEREADER_DIR / execution_id
    if export_dir.exists() and any(export_dir.glob("*.pdf")):
        return "real_export"
    return "synthetic_stub"


def analyze_inhibitor_round(round_id: str) -> dict:
    preset_path = INPUTS_DIR / f"{round_id}.json"
    if not preset_path.exists():
        raise FileNotFoundError(f"no input preset for {round_id} — was it planned via plan_agent?")
    inputs = json.loads(preset_path.read_text())

    exec_id = _execution_id_for_kind(round_id, "run")
    if not exec_id:
        raise RuntimeError(f"{round_id} has no linked execution yet — run watch_execution first")

    n = int(inputs["dose_n"])
    wells = [inputs[f"dose{i}_well"] for i in range(1, n + 1)]
    doses_ul = [inputs[f"dose{i}_compound_vol_ul"] for i in range(1, n + 1)]  # proxy for concentration

    values = parse_gen5_export(exec_id, "endpoint", wells)
    response = np.array([values[w] for w in wells])
    dose = np.array(doses_ul, dtype=float)
    dose = np.where(dose <= 0, 1e-6, dose)  # avoid log(0) in the 4PL

    try:
        (bottom, top, ic50, hill), _ = curve_fit(
            _four_pl, dose, response,
            p0=[response.min(), response.max(), np.median(dose), 1.0],
            maxfev=5000,
        )
        predicted = _four_pl(dose, bottom, top, ic50, hill)
        ss_res = float(np.sum((response - predicted) ** 2))
        ss_tot = float(np.sum((response - response.mean()) ** 2))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
        fit = {
            "bottom": float(bottom), "top": float(top), "ic50": float(ic50), "hill_slope": float(hill),
            "r_squared": r_squared,
        }
    except RuntimeError:
        fit = {"note": "fit did not converge — try a wider or better-centered dose range"}

    results = {
        "round_id": round_id, "execution_id": exec_id, "compound_id": inputs.get("compound_id"),
        "wells": wells, "doses_ul": doses_ul, "response": response.tolist(), "fit": fit,
        "data_source": _export_data_source(exec_id),
    }
    _write_results(round_id, results)
    bw.note(round_id, f"Dose-response fit for {inputs.get('compound_id')}: {json.dumps(fit)}")
    bw.set_stage(round_id, "decided", reason=f"IC50={fit.get('ic50', 'n/a')}")
    return results


# --- cfps_expression round: sfGFP go/no-go --------------------------------------

def analyze_cfps_expression_round(round_id: str, go_threshold_ratio: float = 0.5) -> dict:
    """Compares mean sfGFP signal in sample wells against positive/negative
    controls (well roles recovered from Part 1's own run_inputs, since Part 2
    reads the whole plate with no layout of its own). Go if the sample signal
    clears `go_threshold_ratio` of the positive control, above the negative.
    """
    part1_exec = _execution_id_for_kind(round_id, "part1")
    part2_exec = _execution_id_for_kind(round_id, "part2")
    if not part1_exec or not part2_exec:
        raise RuntimeError(f"{round_id} needs both part1 and part2 executions linked before analyzing")

    part1_inputs = _run_inputs_for_execution(part1_exec)
    pos_wells = [w.strip() for w in part1_inputs.get("pos_wells", "").split(",") if w.strip()]
    neg_wells = [w.strip() for w in part1_inputs.get("neg_wells", "").split(",") if w.strip()]
    sample_wells = [w.strip() for w in part1_inputs.get("sample_wells", "").split(",") if w.strip()]
    all_wells = pos_wells + neg_wells + sample_wells

    values = parse_gen5_export(part2_exec, "endpoint", all_wells)
    mean = lambda ws: float(np.mean([values[w] for w in ws])) if ws else None  # noqa: E731
    pos_mean, neg_mean, sample_mean = mean(pos_wells), mean(neg_wells), mean(sample_wells)

    go = bool(
        sample_mean is not None and pos_mean is not None and neg_mean is not None
        and sample_mean > neg_mean and sample_mean > go_threshold_ratio * pos_mean
    )

    results = {
        "round_id": round_id, "part1_execution_id": part1_exec, "part2_execution_id": part2_exec,
        "pos_mean": pos_mean, "neg_mean": neg_mean, "sample_mean": sample_mean, "go": go,
        "data_source": _export_data_source(part2_exec),
    }
    _write_results(round_id, results)
    bw.note(round_id, f"sfGFP go/no-go: pos={pos_mean} neg={neg_mean} sample={sample_mean} -> {'GO' if go else 'NO-GO'}")
    bw.set_stage(round_id, "decided", reason=f"{'go' if go else 'no-go'} (sample={sample_mean}, pos={pos_mean}, neg={neg_mean})")
    return results


# --- ADK agent wrapper -----------------------------------------------------------

def analyze_kinetics_round_tool(round_id: str) -> dict:
    """Analyze a kinetics round: fits Michaelis-Menten per enzyme level from the
    kinetic plate-reader export, and recommends a nitrocefin working
    concentration + endpoint timing for the inhibitor screen. Sets the round to
    'decided'."""
    return analyze_kinetics_round(round_id)


def analyze_inhibitor_round_tool(round_id: str) -> dict:
    """Analyze an inhibitor_dose_response round: fits a 4-parameter logistic to
    the endpoint plate-reader export and reports IC50. Sets the round to
    'decided'."""
    return analyze_inhibitor_round(round_id)


def analyze_cfps_expression_round_tool(round_id: str) -> dict:
    """Analyze a cfps_expression round: compares Part 2's sfGFP read across
    positive/negative/sample wells (recovered from Part 1's own inputs) and
    decides go/no-go for spending an inhibitor screen on this plate. Sets the
    round to 'decided'."""
    return analyze_cfps_expression_round(round_id)


def analyze_execution_kinetic_export_tool(execution_id: str, wells: list[str], round_id: str = None) -> dict:
    """Analyze a kinetic Gen5 PDF directly by execution_id, with no beads input
    preset required — use this instead of analyze_kinetics_round_tool when the
    round has no preset to recover a plate layout from (an 'unplanned' round from
    an app log export, or any round stuck at 'deviated' for that reason).

    `wells` (e.g. ["A1","A2",...]) is REQUIRED — ask the operator which wells were
    actually dosed if you don't already know. A Gen5 export covers the full
    96-well plate, and reporting all of it would mostly be empty-plate background
    noise, not real data — do not pass every well just because the export has
    data for every well. Pass `round_id` to also attach the results and a note to
    that round's bead. Does NOT fit Michaelis-Menten or recommend a working
    concentration — with no preset there is no known enzyme/substrate condition
    per well, so this reports each well's observed initial rate only; read it
    against whatever the operator knows the plate layout was."""
    return analyze_execution_kinetic_export(execution_id, wells=wells, round_id=round_id)


root_agent = Agent(
    name="analyze_agent",
    model="gemini-2.5-flash",
    description="Fits plate-reader data and decides the next step for a TEM1 CFPS screening round.",
    instruction=(
        "You analyze completed rounds of a TEM1 beta-lactamase screening campaign. Given a "
        "round_id, first check what assay_type it is (the operator will usually tell you, or "
        "you can infer from context) and call the matching tool: "
        "analyze_kinetics_round_tool for a kinetics round, analyze_cfps_expression_round_tool "
        "for a cfps_expression (go/no-go) round, or analyze_inhibitor_round_tool for an "
        "inhibitor_dose_response round. Report the key numbers back plainly — the fit "
        "parameters or IC50 or go/no-go call — since that's what decides the next Plan call.\n\n"
        "If the round has no input preset (analyze_kinetics_round_tool raises "
        "FileNotFoundError saying so) — typically an 'unplanned' round recovered from an app "
        "log export — fall back to analyze_execution_kinetic_export_tool with the round's "
        "linked execution_id instead of giving up."
    ),
    tools=[
        analyze_kinetics_round_tool, analyze_cfps_expression_round_tool,
        analyze_inhibitor_round_tool, analyze_execution_kinetic_export_tool,
    ],
)
