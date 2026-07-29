"""Parse Zeon run logs into structured timing reports.

Full documentation: ``RUN_LOG_TIMING.md`` in this directory.

Supports rendered ``run_log.txt`` (from ``save_run_folder``) and raw
``run_log.jsonl`` events.  Workflow node mapping uses workflow JSON
``nodes[].label`` as the join key against log step labels.

Workflow-specific phase buckets for timing reports may be declared in the
workflow JSON under ``timing_phases`` (optional).  Each entry maps a phase
name to label substring needles (case-insensitive, first match wins)::

    "timing_phases": [
      { "phase": "setup", "match": ["prepare dilutions", "pick up pipette"] },
      { "phase": "assay_loading", "match": ["dispense tem-1", "dispense test compound"] }
    ]

When ``timing_phases`` is absent, ``DEFAULT_PHASE_RULES`` (TEM-1 screen
heuristics) is used for backward compatibility.

Typical usage::

    from analysis.run_log_timing import analyze_run_log, format_text_summary

    report = analyze_run_log("run_log.txt", workflow_json="mastermix/workflows/tem1_activity_screen.json")
    print(format_text_summary(report))
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

EventKind = Literal[
    "step_start",
    "step_complete",
    "dispense_serial",
    "dispense_batch",
    "dispense_batch_start",
    "dispense_batch_complete",
    "wait_start",
    "wait_complete",
    "pipette_swap",
    "milestone",
    "nitrocefin_t0",
    "other",
]

PhaseRules = list[tuple[str, tuple[str, ...]]]

# Fallback phase buckets when a workflow JSON has no ``timing_phases`` (TEM-1 screen heuristics).
DEFAULT_PHASE_RULES: PhaseRules = [
    ("setup", ("prepare dilutions", "pick up pipette")),
    ("assay_loading", ("dispense tem-1", "dispense no-enzyme", "dispense vehicle", "dispense positive", "dispense test compound")),
    ("plate_mix", ("mix", "shaker", "grab plate", "return mixed plate", "place pipette for plate mix", "pick pipette after mix")),
    ("preincubation", ("pre-incubate",)),
    ("nitrocefin_prep", ("prepare nitrocefin",)),
    ("nitrocefin_dispense", ("nitrocefin:",)),
    ("teardown", ("place pipette back", "save run folder")),
]

REPO_ROOT = Path(__file__).resolve().parents[2]
TIMING_BASELINES_DIR = Path(__file__).resolve().parent / "timing_baselines"

# --- regexes for rendered .txt logs -------------------------------------------------

HEADER_EXEC = re.compile(r"^Execution ID:\s*(.+)$")
HEADER_WORKFLOW = re.compile(r"^Workflow:\s*(.+)$")
HEADER_STARTED = re.compile(r"^Started:\s*(.+)$")
HEADER_COMPLETED = re.compile(r"^Completed:\s*(.+)$")
HEADER_DURATION = re.compile(r"^Duration:\s*(.+)$")

TS = re.compile(r"\[(\d{2}:\d{2}:\d{2})\]")
TOP_STEP = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\] ▶ (.+?)  STARTING\s*$")
INDENTED = re.compile(r"^\s+\[(\d{2}:\d{2}:\d{2})\]\s+(.*)$")

SERIAL_DISPENSE = re.compile(
    r"(?P<label>.+?):\s*(?:chunk \d+ )?aspirate/dispense\s+(?P<vol>[\d.]+)\s*uL",
    re.I,
)
BATCH_LINE = re.compile(
    r"Batch \d+:\s*aspirate\s+[\d.]+\s*uL.*?dispense\s+[\d.]+\s*uL to\s+(?P<wells>\[[^\]]+\])",
    re.I,
)
BATCH_START = re.compile(r"▶ Batched dispense\s+(?P<detail>.+)$", re.I)
BATCH_COMPLETE = re.compile(r"✓ Batched dispense from\s+(?P<src>.+?) complete:", re.I)
WAIT_START = re.compile(r"(?P<label>.+?):\s*waiting\s+(?P<minutes>[\d.]+)\s*minute", re.I)
WAIT_COMPLETE = re.compile(r"(?P<label>.+?):\s*wait complete", re.I)
MILESTONE = re.compile(r"^✓\s+")
PIPETTE_SWAP = re.compile(r"⇄ Swapping")


def _parse_header_datetime(text: str) -> datetime | None:
    text = text.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S %Z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S PDT",
        "%Y-%m-%d %H:%M:%S PST",
    ):
        try:
            return datetime.strptime(text.replace(" PDT", "").replace(" PST", ""), fmt.replace(" %Z", "").replace(" PDT", "").replace(" PST", ""))
        except ValueError:
            continue
    return None


def _parse_duration_text(text: str) -> float | None:
    text = text.strip().lower()
    m = re.match(r"(\d+)h\s*(\d+)m", text)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60
    m = re.match(r"(\d+)m\s*(\d+)s", text)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.match(r"(\d+)m", text)
    if m:
        return int(m.group(1)) * 60
    m = re.match(r"(\d+)s", text)
    if m:
        return int(m.group(1))
    return None


def _assign_day_offsets(timestamps: list[str]) -> dict[str, int]:
    """Map HH:MM:SS strings to day offset (0 = first day) for overnight runs."""
    offsets: dict[str, int] = {}
    prev: str | None = None
    day = 0
    for ts in timestamps:
        if ts in offsets:
            continue
        if prev is not None:
            ph, pm, _ = map(int, prev.split(":"))
            ch, cm, _ = map(int, ts.split(":"))
            if ch * 60 + cm < ph * 60 + pm - 60:
                day += 1
        offsets[ts] = day
        prev = ts
    return offsets


def _ts_to_datetime(ts: str, day_offset: int, base_date: datetime | None) -> datetime:
    h, m, s = map(int, ts.split(":"))
    if base_date is not None:
        base = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
        return base + timedelta(days=day_offset, hours=h, minutes=m, seconds=s)
    return datetime(2000, 1, 1) + timedelta(days=day_offset, hours=h, minutes=m, seconds=s)


def _seconds_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds()


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m" if m else f"{h}h {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _classify_detail_message(msg: str) -> tuple[EventKind, dict[str, Any]]:
    meta: dict[str, Any] = {"message": msg}
    if PIPETTE_SWAP.search(msg):
        return "pipette_swap", meta
    if m := WAIT_START.search(msg):
        meta["wait_label"] = m.group("label").strip()
        meta["wait_minutes"] = float(m.group("minutes"))
        return "wait_start", meta
    if m := WAIT_COMPLETE.search(msg):
        meta["wait_label"] = m.group("label").strip()
        return "wait_complete", meta
    if m := BATCH_START.search(msg):
        meta["batch_detail"] = m.group("detail").strip()
        return "dispense_batch_start", meta
    if m := BATCH_COMPLETE.search(msg):
        meta["batch_source"] = m.group("src").strip()
        return "dispense_batch_complete", meta
    if m := BATCH_LINE.search(msg):
        meta["wells"] = m.group("wells")
        return "dispense_batch", meta
    if m := SERIAL_DISPENSE.search(msg):
        meta["volume_ul"] = float(m.group("vol"))
        meta["transfer_label"] = m.group("label").strip()
        return "dispense_serial", meta
    if MILESTONE.search(msg):
        return "milestone", meta
    return "other", meta


@dataclass
class RunLogHeader:
    execution_id: str = ""
    workflow: str = ""
    started: datetime | None = None
    completed: datetime | None = None
    duration_seconds: float | None = None
    source_path: str = ""


@dataclass
class LogEvent:
    timestamp: datetime
    kind: EventKind
    step_label: str | None
    message: str
    is_top_level_step: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepSpan:
    label: str
    start: datetime
    end: datetime
    duration_seconds: float
    node_id: str | None = None
    skill_id: str | None = None
    phase: str | None = None
    dispense_event_count: int = 0
    logged_wait_seconds: float = 0.0
    idle_seconds: float = 0.0
    child_events: list[LogEvent] = field(default_factory=list)


@dataclass
class DispenseInterval:
    timestamp: datetime
    step_label: str
    kind: EventKind
    delta_seconds: float | None
    message: str
    volume_ul: float | None = None
    wells: str | None = None


@dataclass
class IdleGap:
    start: datetime
    end: datetime
    duration_seconds: float
    after_step: str | None
    before_step: str | None
    note: str = ""


@dataclass
class PhaseSummary:
    phase: str
    duration_seconds: float
    fraction_of_run: float
    step_labels: list[str] = field(default_factory=list)


@dataclass
class RunTimingReport:
    header: RunLogHeader
    events: list[LogEvent]
    step_spans: list[StepSpan]
    dispense_intervals: list[DispenseInterval]
    idle_gaps: list[IdleGap]
    phase_summaries: list[PhaseSummary]
    workflow_mapping: dict[str, Any] = field(default_factory=dict)

    @property
    def total_seconds(self) -> float:
        if self.header.duration_seconds is not None:
            return self.header.duration_seconds
        if self.header.started and self.header.completed:
            return _seconds_between(self.header.started, self.header.completed)
        if self.step_spans:
            return _seconds_between(self.step_spans[0].start, self.step_spans[-1].end)
        return 0.0


@dataclass
class WorkflowNodeRef:
    node_id: str
    label: str
    skill_id: str | None = None
    description: str = ""
    timing_label: str | None = None
    phase: str | None = None


def load_timing_phases(data: dict[str, Any]) -> PhaseRules:
    """Parse ``timing_phases`` from workflow JSON, or return ``DEFAULT_PHASE_RULES``."""
    raw = data.get("timing_phases")
    if not raw:
        return DEFAULT_PHASE_RULES
    rules: PhaseRules = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        phase = str(entry.get("phase", "")).strip()
        if not phase:
            continue
        match = entry.get("match", [])
        if not isinstance(match, list):
            continue
        needles = tuple(str(m).lower() for m in match if str(m).strip())
        rules.append((phase, needles))
    return rules or DEFAULT_PHASE_RULES


def load_workflow_step_index(
    workflow_json: str | Path,
    phase_rules: PhaseRules | None = None,
) -> tuple[dict[str, WorkflowNodeRef], PhaseRules]:
    """Build ``label -> WorkflowNodeRef`` from a workflow JSON file.

    Returns the index and the phase rules used (from ``timing_phases`` in the
    JSON when present, else ``DEFAULT_PHASE_RULES`` or an explicit override).
    """
    path = Path(workflow_json)
    if not path.is_absolute():
        candidate = REPO_ROOT / path
        if candidate.exists():
            path = candidate
    data = json.loads(path.read_text())
    rules = phase_rules if phase_rules is not None else load_timing_phases(data)
    index: dict[str, WorkflowNodeRef] = {}
    for node in data.get("nodes", []):
        if node.get("type") not in ("skill",):
            continue
        label = str(node.get("label", "")).strip()
        if not label:
            continue
        phase = _infer_phase(label, rules)
        timing_label = None
        params = node.get("parameters") or {}
        if isinstance(params.get("timing_label"), str):
            timing_label = params["timing_label"]
        elif isinstance(params.get("timing_label"), dict):
            pass
        index[label] = WorkflowNodeRef(
            node_id=str(node.get("node_id", "")),
            label=label,
            skill_id=node.get("skill_id"),
            description=str(node.get("description", "")),
            timing_label=timing_label,
            phase=phase,
        )
    return index, rules


def _infer_phase(label: str, rules: PhaseRules) -> str | None:
    lower = label.lower()
    for phase, needles in rules:
        if any(n in lower for n in needles):
            return phase
    return "other"


def map_step_spans_to_workflow(
    spans: list[StepSpan],
    workflow_index: dict[str, WorkflowNodeRef],
    phase_rules: PhaseRules | None = None,
) -> tuple[list[StepSpan], dict[str, Any]]:
    """Attach ``node_id``, ``skill_id``, and ``phase`` from workflow labels."""
    rules = phase_rules or DEFAULT_PHASE_RULES
    mapped = 0
    unmatched: list[str] = []
    for span in spans:
        ref = workflow_index.get(span.label)
        if ref is None:
            unmatched.append(span.label)
            span.phase = _infer_phase(span.label, rules)
            continue
        span.node_id = ref.node_id
        span.skill_id = ref.skill_id
        span.phase = ref.phase
        mapped += 1
    return spans, {
        "mapped_count": mapped,
        "unmatched_labels": sorted(set(unmatched)),
        "workflow_nodes": len(workflow_index),
    }


def _parse_rendered_text(text: str, source_path: str = "") -> tuple[RunLogHeader, list[LogEvent]]:
    header = RunLogHeader(source_path=source_path)
    raw_lines = text.splitlines()

    for line in raw_lines[:12]:
        if m := HEADER_EXEC.match(line):
            header.execution_id = m.group(1).strip()
        elif m := HEADER_WORKFLOW.match(line):
            header.workflow = m.group(1).strip()
        elif m := HEADER_STARTED.match(line):
            header.started = _parse_header_datetime(m.group(1))
        elif m := HEADER_COMPLETED.match(line):
            header.completed = _parse_header_datetime(m.group(1))
        elif m := HEADER_DURATION.match(line):
            header.duration_seconds = _parse_duration_text(m.group(1))

    all_ts: list[str] = []
    for line in raw_lines:
        if m := TOP_STEP.match(line.strip()):
            all_ts.append(m.group(1))
        elif m := INDENTED.match(line):
            all_ts.append(m.group(1))
    day_map = _assign_day_offsets(all_ts)

    events: list[LogEvent] = []
    current_step: str | None = None

    for line in raw_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("─") or stripped == "Run Log":
            continue
        if stripped.startswith("Execution ID:") or stripped.startswith("Workflow:"):
            continue
        if stripped.startswith("Started:") or stripped.startswith("Completed:") or stripped.startswith("Duration:"):
            continue

        if m := TOP_STEP.match(stripped):
            ts = m.group(1)
            label = m.group(2).strip()
            current_step = label
            dt = _ts_to_datetime(ts, day_map[ts], header.started)
            events.append(
                LogEvent(
                    timestamp=dt,
                    kind="step_start",
                    step_label=label,
                    message=f"▶ {label} STARTING",
                    is_top_level_step=True,
                )
            )
            continue

        if m := INDENTED.match(line):
            ts, msg = m.group(1), m.group(2).strip()
            kind, meta = _classify_detail_message(msg)
            dt = _ts_to_datetime(ts, day_map[ts], header.started)
            events.append(
                LogEvent(
                    timestamp=dt,
                    kind=kind,
                    step_label=current_step,
                    message=msg,
                    metadata=meta,
                )
            )

    return header, events


def _parse_jsonl(text: str, source_path: str = "") -> tuple[RunLogHeader, list[LogEvent]]:
    header = RunLogHeader(source_path=source_path)
    events: list[LogEvent] = []
    current_step: str | None = None
    timestamps: list[str] = []
    parsed_rows: list[dict[str, Any]] = []

    for raw in text.splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        parsed_rows.append(row)
        t = str(row.get("t", ""))
        if t:
            timestamps.append(t)

    for row in parsed_rows:
        typ = str(row.get("type", "event"))
        label = str(row.get("label", "")).strip() or None
        msg = str(row.get("msg", "")).strip()
        t_raw = str(row.get("t", ""))

        if typ == "step_start" or (not label and "STARTING" in msg):
            current_step = label or current_step

        kind: EventKind = "other"
        meta: dict[str, Any] = {"type": typ}
        if typ == "step_start":
            kind = "step_start"
        elif typ == "nitrocefin_t0":
            kind = "nitrocefin_t0"
        else:
            kind, meta = _classify_detail_message(msg or label or "")

        dt: datetime | None = None
        if t_raw:
            try:
                dt = datetime.fromisoformat(t_raw.replace("Z", "+00:00"))
            except ValueError:
                if m := TS.search(t_raw):
                    day_map = _assign_day_offsets([m.group(1)])
                    dt = _ts_to_datetime(m.group(1), day_map[m.group(1)], header.started)

        if dt is None:
            continue

        if kind == "step_start":
            current_step = label or (msg.replace("STARTING", "").replace("▶", "").strip() if msg else current_step)

        events.append(
            LogEvent(
                timestamp=dt,
                kind=kind,
                step_label=current_step,
                message=msg or label or typ,
                is_top_level_step=(kind == "step_start"),
                metadata=meta,
            )
        )

    if events:
        header.started = events[0].timestamp
        header.completed = events[-1].timestamp
        header.duration_seconds = _seconds_between(header.started, header.completed)

    return header, events


def _collapse_step_spans(events: list[LogEvent], run_end: datetime | None) -> list[StepSpan]:
    """One span per workflow step label (first start -> next label's first start)."""
    starts: list[tuple[str, datetime]] = []
    seen_transition = False
    prev_label: str | None = None

    for ev in events:
        if not ev.is_top_level_step or ev.kind != "step_start" or not ev.step_label:
            continue
        if ev.step_label != prev_label:
            starts.append((ev.step_label, ev.timestamp))
            prev_label = ev.step_label
            seen_transition = True
        elif not seen_transition:
            starts.append((ev.step_label, ev.timestamp))
            prev_label = ev.step_label

    if not starts:
        return []

    spans: list[StepSpan] = []
    for i, (label, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else (run_end or events[-1].timestamp)
        child = [e for e in events if e.step_label == label and start <= e.timestamp <= end]
        dispense_count = sum(1 for e in child if e.kind in ("dispense_serial", "dispense_batch"))
        wait_seconds = sum(e.metadata.get("wait_minutes", 0) * 60 for e in child if e.kind == "wait_start")
        action_times = [
            e.timestamp
            for e in child
            if e.kind
            not in (
                "step_start",
                "other",
            )
        ]
        idle = _seconds_between(start, end)
        if action_times:
            idle = max(0.0, idle - sum(
                _seconds_between(action_times[j], action_times[j + 1])
                for j in range(len(action_times) - 1)
                if _seconds_between(action_times[j], action_times[j + 1]) < 120
            ))
        spans.append(
            StepSpan(
                label=label,
                start=start,
                end=end,
                duration_seconds=_seconds_between(start, end),
                dispense_event_count=dispense_count,
                logged_wait_seconds=wait_seconds,
                idle_seconds=idle,
                child_events=child,
            )
        )
    return spans


def _build_dispense_intervals(events: list[LogEvent]) -> list[DispenseInterval]:
    intervals: list[DispenseInterval] = []
    prev: datetime | None = None
    for ev in events:
        if ev.kind not in ("dispense_serial", "dispense_batch", "dispense_batch_start", "dispense_batch_complete"):
            continue
        delta = _seconds_between(prev, ev.timestamp) if prev else None
        intervals.append(
            DispenseInterval(
                timestamp=ev.timestamp,
                step_label=ev.step_label or "",
                kind=ev.kind,
                delta_seconds=delta,
                message=ev.message,
                volume_ul=ev.metadata.get("volume_ul"),
                wells=ev.metadata.get("wells"),
            )
        )
        prev = ev.timestamp
    return intervals


def _find_idle_gaps(
    events: list[LogEvent],
    step_spans: list[StepSpan],
    min_seconds: float = 180.0,
) -> list[IdleGap]:
    gaps: list[IdleGap] = []
    actionable = [
        e
        for e in events
        if e.kind
        not in (
            "step_start",
            "other",
        )
    ]
    for i in range(1, len(actionable)):
        a, b = actionable[i - 1], actionable[i]
        gap = _seconds_between(a.timestamp, b.timestamp)
        if gap < min_seconds:
            continue
        after_step = a.step_label
        before_step = b.step_label
        note = "unlogged wait" if a.kind != "wait_start" and b.kind != "wait_complete" else "between actions"
        gaps.append(
            IdleGap(
                start=a.timestamp,
                end=b.timestamp,
                duration_seconds=gap,
                after_step=after_step,
                before_step=before_step,
                note=note,
            )
        )
    return gaps


def _summarize_phases(spans: list[StepSpan], total_seconds: float) -> list[PhaseSummary]:
    by_phase: dict[str, list[StepSpan]] = {}
    for span in spans:
        phase = span.phase or "other"
        by_phase.setdefault(phase, []).append(span)

    summaries: list[PhaseSummary] = []
    for phase, group in sorted(by_phase.items(), key=lambda x: -sum(s.duration_seconds for s in x[1])):
        dur = sum(s.duration_seconds for s in group)
        summaries.append(
            PhaseSummary(
                phase=phase,
                duration_seconds=dur,
                fraction_of_run=(dur / total_seconds if total_seconds else 0.0),
                step_labels=[s.label for s in group],
            )
        )
    return summaries


def build_run_timing_report(
    header: RunLogHeader,
    events: list[LogEvent],
    workflow_index: dict[str, WorkflowNodeRef] | None = None,
    phase_rules: PhaseRules | None = None,
) -> RunTimingReport:
    run_end = header.completed or (events[-1].timestamp if events else None)
    spans = _collapse_step_spans(events, run_end)
    rules = phase_rules or DEFAULT_PHASE_RULES
    mapping: dict[str, Any] = {}
    if workflow_index:
        spans, mapping = map_step_spans_to_workflow(spans, workflow_index, rules)
    else:
        for span in spans:
            span.phase = _infer_phase(span.label, rules)

    total = header.duration_seconds
    if total is None and header.started and run_end:
        total = _seconds_between(header.started, run_end)

    return RunTimingReport(
        header=header,
        events=events,
        step_spans=spans,
        dispense_intervals=_build_dispense_intervals(events),
        idle_gaps=_find_idle_gaps(events, spans),
        phase_summaries=_summarize_phases(spans, total or 0.0),
        workflow_mapping=mapping,
    )


def parse_run_log_path(path: str | Path) -> RunTimingReport:
    path = Path(path)
    text = path.read_text()
    if path.suffix.lower() == ".jsonl":
        header, events = _parse_jsonl(text, str(path))
    else:
        header, events = _parse_rendered_text(text, str(path))
    return build_run_timing_report(header, events)


def analyze_run_log(
    log_path: str | Path,
    workflow_json: str | Path | None = None,
    workflow_id: str | None = None,
) -> RunTimingReport:
    """Parse a run log and optionally map steps to workflow nodes.

    ``workflow_json`` may be a path.  If omitted, ``workflow_id`` (or the
    workflow name from the log header) is used to locate
    ``mastermix/workflows/<id>.json`` under the repo root.
    """
    report = parse_run_log_path(log_path)
    wf_path: Path | None = None
    if workflow_json is not None:
        wf_path = Path(workflow_json)
    else:
        wf_name = workflow_id or report.header.workflow
        if wf_name:
            # Strip common suffixes like _hack_world_22
            base = _normalize_workflow_id(wf_name)
            candidate = REPO_ROOT / "mastermix" / "workflows" / f"{base}.json"
            if candidate.exists():
                wf_path = candidate
    if wf_path is not None and wf_path.exists():
        index, phase_rules = load_workflow_step_index(wf_path)
        report.step_spans, report.workflow_mapping = map_step_spans_to_workflow(
            report.step_spans, index, phase_rules
        )
        report.phase_summaries = _summarize_phases(report.step_spans, report.total_seconds)
    return report


def _normalize_workflow_id(name: str) -> str:
    """Strip execution suffixes like ``_hack_world_22`` from log header workflow names."""
    return re.sub(r"_hack_world_\d+$", "", name.strip())


def baseline_filename(workflow_id: str, workflow_version: str) -> str:
    safe_version = workflow_version.replace("/", "_")
    return f"{workflow_id}_v{safe_version}.json"


def resolve_timing_baseline_path(
    *,
    workflow_json: str | Path | None = None,
    workflow_id: str | None = None,
    workflow_version: str | None = None,
    execution_workflow: str | None = None,
    baselines_dir: str | Path | None = None,
) -> Path | None:
    """Locate a committed timing baseline for a workflow id + version."""
    root = Path(baselines_dir) if baselines_dir is not None else TIMING_BASELINES_DIR
    wf_id = workflow_id
    wf_version = workflow_version

    if workflow_json is not None:
        path = Path(workflow_json)
        if not path.is_absolute():
            candidate = REPO_ROOT / path
            if candidate.exists():
                path = candidate
        if path.exists():
            data = json.loads(path.read_text())
            wf_id = wf_id or str(data.get("workflow_id", "")).strip() or None
            wf_version = wf_version or str(data.get("version", "")).strip() or None

    if not wf_id and execution_workflow:
        wf_id = _normalize_workflow_id(execution_workflow)

    if not wf_id or not wf_version:
        return None

    candidate = root / baseline_filename(wf_id, wf_version)
    return candidate if candidate.exists() else None


def load_timing_baseline(path: str | Path) -> dict[str, Any]:
    """Load a timing baseline JSON file."""
    return json.loads(Path(path).read_text())


def _tolerance_seconds(
    expected: float,
    *,
    relative_pct: float,
    min_absolute_seconds: float,
    phase_spec: dict[str, Any] | None = None,
) -> float:
    """Upper-bound slack: max(relative % of expected, minimum absolute seconds)."""
    spec = phase_spec or {}
    rel = float(spec.get("tolerance_relative_pct", relative_pct))
    abs_min = float(spec.get("tolerance_min_absolute_seconds", min_absolute_seconds))
    return max(expected * rel / 100.0, abs_min)


def check_timing_regression(
    report: RunTimingReport,
    baseline: dict[str, Any],
) -> list[str]:
    """Return human-readable violations when observed durations exceed baseline budgets."""
    defaults = baseline.get("tolerance_defaults") or {}
    rel_default = float(defaults.get("relative_pct", 20.0))
    abs_default = float(defaults.get("min_absolute_seconds", 60.0))

    actual_by_phase = {p.phase: p.duration_seconds for p in report.phase_summaries}
    violations: list[str] = []

    for phase, spec in (baseline.get("phases") or {}).items():
        expected = float(spec["expected_seconds"])
        actual = actual_by_phase.get(phase, 0.0)
        slack = _tolerance_seconds(
            expected,
            relative_pct=rel_default,
            min_absolute_seconds=abs_default,
            phase_spec=spec if isinstance(spec, dict) else None,
        )
        limit = expected + slack
        if actual > limit:
            over_by = actual - expected
            violations.append(
                f"phase '{phase}' took {_format_duration(actual)} ({actual:.0f}s), "
                f"exceeds baseline {_format_duration(expected)} ({expected:.0f}s) "
                f"by {_format_duration(over_by)} ({over_by:.0f}s); "
                f"tolerance {_format_duration(slack)} ({slack:.0f}s), limit {_format_duration(limit)} ({limit:.0f}s)"
            )

    total_spec = baseline.get("total_seconds")
    if total_spec:
        expected_total = float(total_spec["expected_seconds"])
        actual_total = report.total_seconds
        slack = _tolerance_seconds(
            expected_total,
            relative_pct=rel_default,
            min_absolute_seconds=abs_default,
            phase_spec=total_spec if isinstance(total_spec, dict) else None,
        )
        limit = expected_total + slack
        if actual_total > limit:
            over_by = actual_total - expected_total
            violations.append(
                f"total run took {_format_duration(actual_total)} ({actual_total:.0f}s), "
                f"exceeds baseline {_format_duration(expected_total)} ({expected_total:.0f}s) "
                f"by {_format_duration(over_by)} ({over_by:.0f}s); "
                f"tolerance {_format_duration(slack)} ({slack:.0f}s), limit {_format_duration(limit)} ({limit:.0f}s)"
            )

    return violations


def report_to_dict(report: RunTimingReport) -> dict[str, Any]:
    """JSON-serializable summary (omit raw event stream by default)."""

    def _dt(v: datetime | None) -> str | None:
        return v.isoformat(sep=" ") if v else None

    dispense_stats: dict[str, Any] = {}
    deltas = [d.delta_seconds for d in report.dispense_intervals if d.delta_seconds is not None]
    if deltas:
        dispense_stats = {
            "count": len(report.dispense_intervals),
            "mean_delta_s": round(statistics.mean(deltas), 1),
            "median_delta_s": round(statistics.median(deltas), 1),
            "max_delta_s": round(max(deltas), 1),
        }

    return {
        "header": {
            **asdict(report.header),
            "started": _dt(report.header.started),
            "completed": _dt(report.header.completed),
            "duration_human": _format_duration(report.total_seconds),
        },
        "workflow_mapping": report.workflow_mapping,
        "phase_summaries": [
            {
                **asdict(p),
                "duration_human": _format_duration(p.duration_seconds),
                "fraction_pct": round(p.fraction_of_run * 100, 1),
            }
            for p in report.phase_summaries
        ],
        "step_spans": [
            {
                "label": s.label,
                "node_id": s.node_id,
                "skill_id": s.skill_id,
                "phase": s.phase,
                "start": _dt(s.start),
                "end": _dt(s.end),
                "duration_seconds": round(s.duration_seconds, 1),
                "duration_human": _format_duration(s.duration_seconds),
                "dispense_event_count": s.dispense_event_count,
                "logged_wait_seconds": s.logged_wait_seconds,
            }
            for s in report.step_spans
        ],
        "dispense_stats": dispense_stats,
        "idle_gaps": [
            {
                **{k: (v if k not in ("start", "end") else _dt(v)) for k, v in asdict(g).items()},
                "duration_human": _format_duration(g.duration_seconds),
            }
            for g in report.idle_gaps
        ],
    }


def format_text_summary(report: RunTimingReport) -> str:
    """Human-readable timing report."""
    lines = [
        "Run timing summary",
        "==================",
        f"Execution: {report.header.execution_id}",
        f"Workflow:  {report.header.workflow}",
        f"Total:     {_format_duration(report.total_seconds)}",
        "",
        "Phase budget",
        "------------",
    ]
    for p in report.phase_summaries:
        lines.append(
            f"  {p.phase:22s} {_format_duration(p.duration_seconds):>8s}  ({p.fraction_of_run * 100:4.0f}%)"
        )

    lines.extend(["", "Workflow steps (collapsed)", "------------------------"])
    for s in report.step_spans:
        node = f" [{s.node_id}]" if s.node_id else ""
        lines.append(
            f"  {s.label:35s}{node} {_format_duration(s.duration_seconds):>8s}"
            f"  disp={s.dispense_event_count}"
        )

    if report.idle_gaps:
        lines.extend(["", f"Idle gaps (>{_format_duration(180)})", "---------"])
        for g in report.idle_gaps[:15]:
            lines.append(
                f"  {g.start.strftime('%H:%M:%S')} -> {g.end.strftime('%H:%M:%S')}"
                f"  {_format_duration(g.duration_seconds):>8s}  ({g.after_step} -> {g.before_step})"
            )

    if report.workflow_mapping.get("unmatched_labels"):
        lines.extend(["", "Unmapped step labels", "--------------------"])
        for label in report.workflow_mapping["unmatched_labels"]:
            lines.append(f"  - {label}")

    return "\n".join(lines) + "\n"


def write_timing_artifact(report: RunTimingReport, output_path: str | Path) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report_to_dict(report), indent=2) + "\n")
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m analysis.run_log_timing path/to/run_log.txt [--workflow wf.json] [--out timing.json]``"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Parse Zeon run logs into structured timing JSON.")
    parser.add_argument("log_path", help="run_log.txt or run_log.jsonl")
    parser.add_argument("--workflow", help="workflow JSON for node_id mapping")
    parser.add_argument("--baseline", help="timing baseline JSON (default: resolve from workflow)")
    parser.add_argument(
        "--check-baseline",
        action="store_true",
        help="exit 1 when phase durations exceed the baseline budget",
    )
    parser.add_argument("--out", help="write JSON summary to this path")
    parser.add_argument("--text", action="store_true", help="print human-readable summary to stdout")
    args = parser.parse_args(argv)

    report = analyze_run_log(args.log_path, workflow_json=args.workflow)
    if args.out:
        write_timing_artifact(report, args.out)
        print(f"Wrote {args.out}")
    if args.text or not args.out:
        print(format_text_summary(report), end="")

    if args.check_baseline or args.baseline:
        baseline_path = Path(args.baseline) if args.baseline else resolve_timing_baseline_path(
            workflow_json=args.workflow,
            execution_workflow=report.header.workflow,
        )
        if baseline_path is None or not baseline_path.exists():
            print("No timing baseline found for this workflow/version.", file=sys.stderr)
            return 2 if args.check_baseline else 0
        baseline = load_timing_baseline(baseline_path)
        violations = check_timing_regression(report, baseline)
        if violations:
            print("\nTiming regression violations:", file=sys.stderr)
            for v in violations:
                print(f"  - {v}", file=sys.stderr)
            return 1 if args.check_baseline else 0
        if args.check_baseline:
            print(f"Timing within baseline: {baseline_path.name}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
