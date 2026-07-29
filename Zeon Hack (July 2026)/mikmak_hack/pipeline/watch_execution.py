"""Execute stage: notices when a human-triggered Zeon run has landed, links it to
the round, and (for cfps_expression rounds) creates the gap-timer gate between
Part 1 and Part 2. Never triggers a run itself — the zeon CLI has no run command;
runs only start from the Zeon app, by a person (per this project's CLAUDE.md).

Matches a round to a physical run by `run_name`: every workflow here declares
`run_name` as an input, so it round-trips into
data/logs/<execution_id>/<run_name>_<timestamp>/run_inputs.json once
save_run_folder (the last node of every workflow) writes it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
import beads_writer as bw  # noqa: E402

DATA_LOGS_DIR = PROJECT_ROOT / "data" / "logs"
DATA_PLATEREADER_DIR = PROJECT_ROOT / "data" / "platereader"
INPUTS_DIR = PROJECT_ROOT / "inputs"

# PLACEHOLDER — minutes between Part 1 starting the shaker and running Part 2's
# sfGFP check (canvas doc: "green signal has appeared as early as ~30 min").
CFPS_EXPRESSION_CONFIRM_DELAY_MINUTES = 30


def discover_executions() -> list[dict]:
    """Every execution present in the project tree, linked to a round or not.

    Keyed off the `data/logs/<execution_id>/` directory rather than a `run_name`
    match, because run_name matching only ever finds runs that finished: it needs
    `run_inputs.json`, which used to be written solely by the final node. A run
    that died partway, or one recovered from an app log export, has a directory
    but may have no run_name at all — and those are precisely the runs worth
    seeing. Anything on disk is reported here; attribution is a separate step.
    """
    out: list[dict] = []
    if not DATA_LOGS_DIR.exists():
        return out
    for exec_dir in sorted(DATA_LOGS_DIR.iterdir()):
        if not exec_dir.is_dir():
            continue
        rec: dict = {
            "execution_id": exec_dir.name,
            "run_name": None,
            "complete": None,
            "last_checkpoint": None,
            "source": None,
            "workflow_id": None,
            "started": None,
            "folders": [],
        }
        for run_dir in sorted(p for p in exec_dir.iterdir() if p.is_dir()):
            rec["folders"].append(run_dir.name)
            status = _read_json(run_dir / "run_status.json")
            meta = _read_json(run_dir / "metadata.json")
            inputs = _read_json(run_dir / "run_inputs.json")
            if status:
                rec["run_name"] = status.get("run_name") or rec["run_name"]
                rec["complete"] = status.get("complete", rec["complete"])
                rec["last_checkpoint"] = status.get("last_checkpoint") or rec["last_checkpoint"]
                rec["source"] = status.get("source") or rec["source"]
            if meta:
                # The app writes `workflow_ref` (workflow id + world id); our own
                # ingest writes `workflow_id`. Fall back through both, then to the
                # execution directory name, which the app builds the same way.
                rec["workflow_id"] = (
                    meta.get("workflow_id")
                    or _resolve_workflow(meta.get("workflow_ref", ""))
                    or rec["workflow_id"]
                )
                rec["started"] = meta.get("started") or meta.get("created_at") or rec["started"]
                rec["name"] = meta.get("name")
        if not rec["workflow_id"]:
            rec["workflow_id"] = _resolve_workflow(exec_dir.name[len("exec_"):]) or None
            if inputs and not rec["run_name"]:
                rec["run_name"] = inputs.get("run_name")
        rec["has_platereader_export"] = platereader_export_ready(exec_dir.name)
        out.append(rec)
    return out


def _resolve_workflow(ref: str) -> str | None:
    """`<workflow_id>_<world_id>` (or a bare id) -> the workflow file it names."""
    if not ref:
        return None
    from ingest_run import resolve_workflow  # same rule, defined once

    return resolve_workflow(ref)


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def execution_to_round() -> dict[str, str]:
    """Map execution_id -> round_id from the beads DAG (the linked-execution children)."""
    mapping: dict[str, str] = {}
    for rnd in bw.list_rounds():
        for child in bw.list_children(rnd["id"]):
            eid = (child.get("metadata") or {}).get("execution_id")
            if eid:
                mapping[eid] = rnd["id"]
    return mapping


def reconcile_executions(create_missing: bool = True) -> list[dict]:
    """Ensure every execution on disk is represented in the beads DAG.

    An unattributed physical run is the thing this pipeline must never have, so an
    execution with no round gets one — labelled `assay:unplanned`, so it is never
    confused with an experiment that came through Plan.
    """
    linked = execution_to_round()
    results = []
    for rec in discover_executions():
        eid = rec["execution_id"]
        round_id = linked.get(eid)
        action = "already-linked"
        if round_id is None and create_missing:
            rnd = bw.create_unplanned_round(
                workflow_id=rec.get("workflow_id") or "unknown",
                execution_id=eid,
                started_at=rec.get("started") or "",
                source=rec.get("source") or "app",
            )
            round_id = rnd.id
            bw.link_execution(round_id, "run", eid)
            bw.record_run_outcome(
                round_id, execution_id=eid,
                complete=bool(rec.get("complete")),
                last_step=rec.get("last_checkpoint") or "",
                detail="discovered in data/logs with no planned round",
            )
            action = "created-unplanned-round"
        elif round_id is None:
            action = "orphan"
        results.append({**rec, "round_id": round_id, "action": action})
    return results


def expected_run_name(round_id: str) -> str | None:
    """The run_name a Plan-generated preset asked the operator to use — only
    exists for kinetics/inhibitor_dose_response rounds (cfps_expression rounds
    are set up by hand via cfps_mastermix's own canvas, no preset)."""
    preset = INPUTS_DIR / f"{round_id}.json"
    if not preset.exists():
        return None
    return json.loads(preset.read_text()).get("run_name")


def find_execution_by_run_name(run_name: str | None) -> str | None:
    if not run_name or not DATA_LOGS_DIR.exists():
        return None
    for exec_dir in DATA_LOGS_DIR.iterdir():
        if not exec_dir.is_dir():
            continue
        for run_dir in exec_dir.iterdir():
            ri = run_dir / "run_inputs.json"
            if not ri.exists():
                continue
            try:
                inputs = json.loads(ri.read_text())
            except json.JSONDecodeError:
                continue
            if inputs.get("run_name") == run_name:
                return exec_dir.name
    return None


def platereader_export_ready(execution_id: str) -> bool:
    d = DATA_PLATEREADER_DIR / execution_id
    return d.exists() and any(d.iterdir())


def watch_single_execution_round(round_id: str, run_name: str | None = None) -> dict:
    """kinetics / inhibitor_dose_response: one execution, one platereader export."""
    round_ = bw.show_round(round_id)
    stage = round_.get("_stage")
    run_name = run_name or expected_run_name(round_id)
    exec_id = find_execution_by_run_name(run_name)

    if exec_id is None:
        return {"status": "waiting_for_execution", "run_name": run_name}

    if stage == "approved":
        bw.set_stage(round_id, "running", reason=f"detected execution {exec_id}")
    if not any(c.get("metadata", {}).get("execution_id") == exec_id for c in bw.list_children(round_id)):
        bw.link_execution(round_id, "run", exec_id)

    if platereader_export_ready(exec_id):
        return {"status": "ready_for_analyze", "execution_id": exec_id}
    return {"status": "running", "execution_id": exec_id}


def _has_kind(children: list[dict], kind: str) -> bool:
    return any(f"execution_kind:{kind}" in c.get("labels", []) for c in children)


def watch_cfps_expression_round(
    round_id: str,
    part1_run_name: str,
    part2_run_name: str | None = None,
) -> dict:
    """cfps_expression: two hand-run executions (the existing cfps_mastermix
    canvas, then cfps_sfgfp_confirmation), bridged by a beads timer gate. Both
    run names are supplied by the operator — Part 1's own canvas already does
    condition planning, so this round type has no Plan-generated input preset.
    """
    round_ = bw.show_round(round_id)
    stage = round_.get("_stage")
    children = bw.list_children(round_id)

    if not _has_kind(children, "part1"):
        exec1 = find_execution_by_run_name(part1_run_name)
        if exec1 is None:
            return {"status": "waiting_for_part1", "run_name": part1_run_name}
        if stage == "approved":
            bw.set_stage(round_id, "running", reason=f"Part 1 execution {exec1} detected")
        bw.link_execution(round_id, "part1", exec1)
        gate_id = bw.create_timer_gate(
            round_id, CFPS_EXPRESSION_CONFIRM_DELAY_MINUTES,
            reason="waiting to run Part 2 (sfGFP confirmation)",
        )
        bw.set_metadata(round_id, pending_gate_id=gate_id)
        return {"status": "part1_detected_awaiting_gate", "execution_id": exec1, "gate_id": gate_id}

    if not _has_kind(children, "part2"):
        if not part2_run_name:
            return {"status": "part1_done_awaiting_part2_run_name"}
        exec2 = find_execution_by_run_name(part2_run_name)
        if exec2 is None:
            return {"status": "waiting_for_part2", "run_name": part2_run_name}
        bw.link_execution(round_id, "part2", exec2)
        return {"status": "ready_for_analyze", "execution_id": exec2}

    return {"status": "already_complete"}


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round_id", nargs="?", help="omit with --reconcile / --list")
    parser.add_argument("--part1-run-name", help="cfps_expression rounds only")
    parser.add_argument("--part2-run-name", help="cfps_expression rounds only")
    parser.add_argument("--poll-seconds", type=int, default=0, help="0 = check once and exit")
    parser.add_argument("--list", action="store_true",
                        help="show every execution in data/logs and whether it's linked")
    parser.add_argument("--reconcile", action="store_true",
                        help="give every unattributed execution an 'unplanned' round")
    args = parser.parse_args()

    if args.list or args.reconcile:
        rows = reconcile_executions(create_missing=args.reconcile)
        for r in rows:
            state = ("complete" if r.get("complete") is True
                     else "STOPPED" if r.get("complete") is False else "unknown")
            print(f"{r['action']:26} {str(r['round_id']):12} {state:8} {r['execution_id']}")
        if not rows:
            print("no executions in data/logs yet")
        raise SystemExit(0)

    if not args.round_id:
        parser.error("round_id is required unless --list or --reconcile is given")

    def check() -> dict:
        round_ = bw.show_round(args.round_id)
        if round_.get("_assay_type") == "cfps_expression":
            return watch_cfps_expression_round(args.round_id, args.part1_run_name, args.part2_run_name)
        return watch_single_execution_round(args.round_id)

    while True:
        result = check()
        print(json.dumps(result))
        if not args.poll_seconds or result["status"] in ("ready_for_analyze", "already_complete"):
            break
        time.sleep(args.poll_seconds)
