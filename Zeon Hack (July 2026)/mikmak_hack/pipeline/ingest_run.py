"""Ingest stage: get a hardware run into the tracker even when it left nothing behind.

The project tree only learns about a run when a `save_run_folder` node executes.
A run that dies before its first checkpoint — or one from before checkpoints
existed — is invisible to `data/logs/`, even though the Zeon app has the log all
along. This module closes that hole: drop the app's exported run log into
`data/inbox/` and it becomes a first-class, inspectable record.

What it does NOT do is invent data. An app log export carries step boundaries and
timing, not volumes or wells, so the normalized folder it writes contains exactly
what the export contained plus what can be derived from it, and marks itself
`source: "log_export"`. Anything absent stays absent — a run whose inputs were
never recorded is shown as a run whose inputs are unknown, not as a run with
guessed inputs.

Usage:
    python pipeline/ingest_run.py                 # ingest everything in data/inbox/
    python pipeline/ingest_run.py <path> [...]    # ingest specific files
    python pipeline/ingest_run.py --round <id> <path>   # attach to a known round
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
import beads_writer as bw  # noqa: E402

INBOX = PROJECT_ROOT / "data" / "inbox"
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
WORKFLOWS_DIR = PROJECT_ROOT / "workflows"

# "[21:33:28] ▶ Attach tip (pt_e1s1_enz)  STARTING" — the app's export format.
STEP_RE = re.compile(r"\[(\d{2}:\d{2}:\d{2})\]\s*▶\s*(.+?)\s+STARTING\s*$")
HEADER_RE = re.compile(r"^([A-Za-z ]+):\s+(.*)$")


class IngestError(RuntimeError):
    """The file isn't a run log we can read. Raised, not returned."""


# --- parsing -------------------------------------------------------------------

def parse_log_export(text: str) -> dict:
    """Pull the header fields and the ordered step list out of an app log export."""
    header: dict[str, str] = {}
    steps: list[tuple[str, str]] = []
    for line in text.splitlines():
        m = STEP_RE.search(line)
        if m:
            # Indented sub-events ("▶ Returning epipette_10ul to its stand") are
            # detail under the step above, not steps in the graph.
            if not line.startswith(" "):
                steps.append((m.group(1), m.group(2).strip()))
            continue
        h = HEADER_RE.match(line.strip())
        if h and not line.startswith("["):
            header[h.group(1).strip().lower()] = h.group(2).strip()

    if "execution id" not in header:
        raise IngestError("no 'Execution ID:' header — is this a Zeon run log export?")
    return {"header": header, "steps": steps}


def resolve_workflow(workflow_ref: str) -> str | None:
    """Map the export's workflow label back to a file in workflows/.

    The app labels runs `<workflow_id>_<world_id>`, so an exact match usually
    fails and the longest matching filename prefix is the right answer.
    """
    if not workflow_ref:
        return None
    candidates = sorted((p.stem for p in WORKFLOWS_DIR.glob("*.json")), key=len, reverse=True)
    for stem in candidates:
        if workflow_ref == stem or workflow_ref.startswith(stem + "_"):
            return stem
    return None


def terminal_labels(workflow_id: str) -> tuple[list[str], str | None]:
    """Every step label in the workflow, plus the label of its last real node —
    what a complete run should have reached."""
    path = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not path.exists():
        return [], None
    wf = json.loads(path.read_text())
    nodes = {n["node_id"]: n for n in wf["nodes"]}
    nxt = {e["from_node"]: e["to_node"] for e in wf["edges"]}
    pv = {e["to_node"] for e in wf["edges"]}
    start = next((n for n in nodes if n not in pv), None)
    chain, cur = [], start
    while cur:
        chain.append(cur)
        cur = nxt.get(cur)
    labels = [nodes[n].get("label", n) for n in chain if nodes[n].get("type") == "skill"]
    return labels, (labels[-1] if labels else None)


def assess(parsed: dict) -> dict:
    """Turn a parsed export into a verdict: which workflow, how far it got, done or not."""
    h, steps = parsed["header"], parsed["steps"]
    eid = h.get("execution id", "")
    workflow_id = resolve_workflow(h.get("workflow", ""))
    labels, terminal = terminal_labels(workflow_id) if workflow_id else ([], None)

    last_step = steps[-1][1] if steps else ""
    # Compare on the base label ("Attach tip (pt_e1s1_enz)" -> "Attach tip") so a
    # graph edit that renamed instances doesn't read as an incomplete run.
    def base(s: str) -> str:
        return re.sub(r"\s*\(.*?\)\s*$", "", s).strip()

    reached_terminal = bool(terminal) and base(last_step) == base(terminal)
    # The app reports "Completed:" even for a run stopped early, so it is evidence
    # the execution ended — not evidence the graph finished.
    return {
        "execution_id": eid,
        "workflow_id": workflow_id,
        "workflow_ref": h.get("workflow", ""),
        "started": h.get("started", ""),
        "completed": h.get("completed", ""),
        "duration": h.get("duration", ""),
        "steps_seen": len(steps),
        "steps_in_workflow": len(labels),
        "first_step": steps[0][1] if steps else "",
        "last_step": last_step,
        "terminal_step": terminal,
        "reached_terminal": reached_terminal,
    }


# --- writing -------------------------------------------------------------------

def write_run_folder(verdict: dict, log_text: str, source_name: str) -> Path:
    """Normalize into data/logs/<execution_id>/<folder>/ so every reader — the
    dashboard, watch_execution, a human with `ls` — finds it where it expects."""
    eid = verdict["execution_id"]
    out = LOGS_DIR / eid / "ingested_from_app_export"
    (out / "logs").mkdir(parents=True, exist_ok=True)
    (out / "logs" / "run_log.txt").write_text(log_text)

    (out / "run_status.json").write_text(json.dumps({
        "execution_id": eid,
        "run_name": None,  # the export does not carry it
        "checkpoints": [],
        "last_checkpoint": verdict["last_step"],
        "complete": verdict["reached_terminal"],
        "source": "log_export",
        "ingested_at": datetime.now().astimezone().isoformat(),
        "ingested_from": source_name,
        "steps_seen": verdict["steps_seen"],
        "steps_in_workflow": verdict["steps_in_workflow"],
        "terminal_step": verdict["terminal_step"],
        "note": "Recovered from a Zeon app log export. Step boundaries and timing "
                "only — this export carries no volumes, wells, or input values, so "
                "run_inputs.json is deliberately absent rather than reconstructed. "
                "steps_seen and steps_in_workflow are NOT comparable: the export "
                "emits a STARTING line for only some node types, so steps_seen is "
                "not a progress fraction. Completion is judged solely on whether "
                "the last logged step is the workflow's terminal step.",
    }, indent=2) + "\n")

    (out / "metadata.json").write_text(json.dumps({
        "execution_id": eid,
        "workflow_ref": verdict["workflow_ref"],
        "workflow_id": verdict["workflow_id"],
        "started": verdict["started"],
        "completed": verdict["completed"],
        "duration": verdict["duration"],
        "status": "completed" if verdict["reached_terminal"] else "stopped_early",
        "source": "log_export",
    }, indent=2) + "\n")
    return out


def already_ingested(eid: str) -> bool:
    return (LOGS_DIR / eid / "ingested_from_app_export").exists()


def ingest_file(path: Path, round_id: str | None = None) -> dict:
    """Ingest one exported log: normalize it on disk, then record it in beads."""
    text = path.read_text(errors="replace")
    verdict = assess(parse_log_export(text))
    eid = verdict["execution_id"]
    if already_ingested(eid):
        return {**verdict, "skipped": "already ingested"}

    folder = write_run_folder(verdict, text, path.name)

    # Attach to the round that planned it, or give it one of its own. A physical
    # run with no round is a run the audit trail cannot see, which is the failure
    # this whole module exists to prevent.
    if round_id is None:
        rnd = bw.create_unplanned_round(
            workflow_id=verdict["workflow_id"] or verdict["workflow_ref"] or "unknown",
            execution_id=eid,
            started_at=verdict["started"],
            source="log_export",
        )
        round_id = rnd.id
    bw.link_execution(round_id, "run", eid)

    detail = f"{verdict['duration']}, recovered from app log export"
    if not verdict["reached_terminal"] and verdict["terminal_step"]:
        detail += f"; workflow's last step is {verdict['terminal_step']!r}"
    bw.record_run_outcome(
        round_id,
        execution_id=eid,
        complete=verdict["reached_terminal"],
        last_step=verdict["last_step"],
        steps_seen=verdict["steps_seen"],
        detail=detail,
    )
    return {**verdict, "round_id": round_id, "folder": str(folder)}


def main(argv: list[str]) -> int:
    round_id = None
    args = list(argv)
    if "--round" in args:
        i = args.index("--round")
        round_id = args[i + 1]
        del args[i:i + 2]

    paths = [Path(a) for a in args] if args else sorted(INBOX.glob("*.txt"))
    if not paths:
        print(f"nothing to ingest — drop app log exports into {INBOX}/")
        return 0

    for p in paths:
        if not p.is_file():
            print(f"skip (not a file): {p}")
            continue
        try:
            r = ingest_file(p, round_id)
        except IngestError as e:
            print(f"skip {p.name}: {e}")
            continue
        if r.get("skipped"):
            print(f"{p.name}: {r['skipped']} ({r['execution_id']})")
            continue
        state = "complete" if r["reached_terminal"] else f"STOPPED at {r['last_step']!r}"
        print(f"{p.name}\n   execution : {r['execution_id']}\n   workflow  : {r['workflow_id']}"
              f"\n   logged    : {r['steps_seen']} step-starts (not a progress fraction)"
              f"\n   outcome   : {state}"
              f"\n   expected  : {r['terminal_step']!r}"
              f"\n   round     : {r['round_id']}\n   folder    : {r['folder']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
