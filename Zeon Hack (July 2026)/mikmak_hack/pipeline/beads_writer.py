"""The single writer to beads (`bd`) for this pipeline.

Every stage transition the Plan/Simulate/Approve/Execute/Analyze loop makes gets
serialized here, and only here — no other module in `pipeline/` shells out to `bd`.
That's what keeps the audit trail linear and trustworthy: one dumb committer,
many callers.

Round lifecycle (`stage` label on the round bead, via `bd set-state`):
    planned -> simulated -> approved -> running -> decided
                                              \\-> deviated (on failure, any stage)

Each round bead carries an `assay:<kinetics|cfps_expression|inhibitor_dose_response>`
label so the three round types are distinguishable in `bd list`/`bd graph` without a
separate table:
  - kinetics              — standalone purified-TEM1 x nitrocefin characterization.
                             One physical execution (kind="run").
  - cfps_expression        — Part 1 (cfps_mastermix) + Part 2 (cfps_sfgfp_confirmation,
                             the go/no-go gate). Two executions (kind="part1", "part2").
  - inhibitor_dose_response — Part 3 (cfps_inhibitor_dose_response). One execution
                             (kind="run"), blocked on a cfps_expression round deciding
                             "go" and informed by a kinetics round's fit.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


class BeadsError(RuntimeError):
    """A `bd` invocation failed. Raised, never swallowed — same convention as
    Zeon skill code: failure is exception-driven, not a returned success=False."""


@dataclass(frozen=True)
class Round:
    id: str
    assay_type: str


def _run(*args: str) -> dict | list | None:
    proc = subprocess.run(
        ["bd", *args, "--json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise BeadsError(f"bd {' '.join(args)!r} failed: {proc.stderr.strip()}")
    out = proc.stdout.strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        # A few subcommands (e.g. `gate resolve`) print human text even with --json.
        # Exit code is the real success signal for those; callers that need
        # structured data back use commands confirmed to emit it (create, set-state,
        # gate create, show, list).
        return None


ASSAY_TYPES = (
    "kinetics",
    "cfps_expression",
    "inhibitor_dose_response",
    # A run that reached hardware without coming through Plan — started straight
    # from the Zeon app, or recovered after the fact from an app log export. It
    # gets a round bead like anything else, because the alternative is a physical
    # run that the audit trail cannot see. Distinguishable by label, so it never
    # gets mistaken for a planned experiment.
    "unplanned",
)


def create_round(assay_type: str, objective: str = "", compound_id: str | None = None) -> Round:
    """Create the round bead. `assay_type` is one of ASSAY_TYPES."""
    if assay_type not in ASSAY_TYPES:
        raise ValueError(f"unknown assay_type: {assay_type!r} (expected one of {ASSAY_TYPES})")
    title = objective or f"{assay_type} round"
    args = ["create", title, "--type", "task", "--labels", f"assay:{assay_type}"]
    if compound_id:
        args += ["--metadata", json.dumps({"compound_id": compound_id})]
    result = _run(*args)
    round_id = result["id"]
    set_stage(round_id, "planned", reason="round created")
    return Round(id=round_id, assay_type=assay_type)


def set_stage(round_id: str, stage: str, reason: str = "") -> None:
    valid = {"planned", "simulated", "approved", "running", "deviated", "decided"}
    if stage not in valid:
        raise ValueError(f"unknown stage: {stage!r} (expected one of {sorted(valid)})")
    _run("set-state", round_id, f"stage={stage}", "--reason", reason or stage)


def create_human_gate(round_id: str, reason: str = "awaiting operator approval") -> str:
    result = _run("gate", "create", "--type", "human", "--blocks", round_id, "--reason", reason)
    return result["id"]


def resolve_gate(gate_id: str, reason: str = "") -> None:
    _run("gate", "resolve", gate_id, "--reason", reason or "resolved")


def create_timer_gate(round_id: str, minutes: int, reason: str = "") -> str:
    result = _run(
        "gate", "create",
        "--type", "timer",
        "--blocks", round_id,
        "--timeout", f"{minutes}m",
        "--reason", reason or f"{minutes}-minute incubation",
    )
    return result["id"]


def link_execution(round_id: str, kind: str, execution_id: str) -> str:
    """Record a physical run (Zeon `execution_id`) as a child bead of the round.

    `kind` is a short free-form label for which physical run this is within the
    round — 'run' for a kinetics or inhibitor_dose_response round's single
    execution, 'part1'/'part2' for a cfps_expression round's two executions
    (cfps_mastermix, then cfps_sfgfp_confirmation). Not an enum: round shapes vary
    by assay_type, so this only needs to be a stable, readable label per round.
    """
    result = _run(
        "create", f"{kind} execution {execution_id}",
        "--type", "task",
        "--parent", round_id,
        "--labels", f"execution_kind:{kind}",
        "--metadata", json.dumps({"execution_id": execution_id}),
    )
    return result["id"]


def create_unplanned_round(
    workflow_id: str,
    execution_id: str,
    started_at: str = "",
    source: str = "app",
) -> Round:
    """Round bead for a run that reached hardware without a Plan stage.

    `source` says how we learned about it — "app" for one detected in the project
    tree, "log_export" for one recovered from a downloaded app log. Both are real
    physical runs; neither has a planned round to attach to.
    """
    title = f"Unplanned run — {workflow_id} ({execution_id[:32]})"
    args = [
        "create", title,
        "--type", "task",
        "--labels", "assay:unplanned",
        "--metadata", json.dumps({
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "started_at": started_at,
            "provenance_source": source,
        }),
    ]
    round_id = _run(*args)["id"]
    set_stage(round_id, "planned", reason=f"unplanned run recorded from {source}")
    return Round(id=round_id, assay_type="unplanned")


def record_run_outcome(
    round_id: str,
    execution_id: str,
    complete: bool,
    last_step: str = "",
    steps_seen: int = 0,
    detail: str = "",
) -> None:
    """Write what a physical run actually did, finished or not.

    A run that stopped partway is recorded as `deviated` with the step it reached
    — not left silent. That is the whole point of tracking: a failed run is
    evidence, and the audit trail should show it happened and where it stopped.
    """
    where = f" at {last_step!r}" if last_step else ""
    summary = (
        f"execution {execution_id}: {'completed' if complete else 'stopped'}{where}"
        f" after {steps_seen} step(s)" + (f" — {detail}" if detail else "")
    )
    note(round_id, summary)
    set_stage(round_id, "running" if complete else "deviated", reason=summary)


def block_on(blocked_round_id: str, blocker_round_id: str) -> None:
    """`blocked_round_id` cannot be planned/surfaced until `blocker_round_id` closes.

    Used to gate the first inhibitor_dose_response round behind the first
    kinetics round reaching `decided`.
    """
    _run("dep", "add", blocked_round_id, "--blocked-by", blocker_round_id)


def note(round_id: str, text: str) -> None:
    _run("note", round_id, text)


def get_stage(round_id: str) -> str | None:
    return show_round(round_id).get("_stage")


def show_round(round_id: str) -> dict:
    result = _run("show", round_id)[0]
    for label in result.get("labels", []):
        if label.startswith("stage:"):
            result["_stage"] = label.split(":", 1)[1]
        elif label.startswith("assay:"):
            result["_assay_type"] = label.split(":", 1)[1]
    return result


def list_children(round_id: str) -> list[dict]:
    """Execution-linked child beads of a round (excludes the state-change event
    beads that set-state also creates as children)."""
    result = _run("show", round_id, "--children") or {}
    children = result.get(round_id, [])
    return [c for c in children if c.get("issue_type") == "task"]


def set_metadata(round_id: str, **kv) -> None:
    """Persist small key/value state on the round bead itself (e.g. which gate
    it's currently waiting on) — cheap scratch space for a stateless poller."""
    args = []
    for k, v in kv.items():
        args += ["--set-metadata", f"{k}={v}"]
    _run("update", round_id, *args)


def list_rounds(stage: str | None = None, assay_type: str | None = None) -> list[dict]:
    """Round beads only (excludes gates/execution children) — top-level task
    issues with no parent, optionally filtered by stage/assay_type label."""
    labels = []
    if stage:
        labels += ["--label", f"stage:{stage}"]
    if assay_type:
        labels += ["--label", f"assay:{assay_type}"]
    result = _run("list", "--type", "task", *labels) or []
    return [r for r in result if "." not in r["id"]]
