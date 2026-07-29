"""The conversational front end to the TEM1 screening pipeline.

`adk web pipeline/agents` serves this as a chat surface. A coordinator delegates
to one sub-agent per stage of the loop the rest of `pipeline/` already implements:

    planner -> syncer -> simulator -> executor -> analyst
                 |          |            |           |
                 +----------+------------+-----------+
                            all stage transitions go through
                            pipeline/beads_writer (single writer)

So the chat is a *driver*, not a second source of truth: every tool below either
reads beads or writes to it through `beads_writer`, and the round DAG (`bd show`,
`bd graph`) stays the record of what happened. Nothing here invents scientific
logic — the numbers still come from `plan_agent`/`analyze_agent`'s plain
functions.

One thing the chat genuinely cannot do: start a run. The `zeon` CLI has no run
command; physical execution is triggered by a person in the Zeon app. The
executor sub-agent's job is to hand over precise run instructions and then watch
`data/logs/` for the run landing.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from google.adk.agents import Agent

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "agents"))

import analyze_agent as analyze  # noqa: E402
import beads_writer as bw  # noqa: E402
import plan_agent as plan  # noqa: E402
import protocol_docs  # noqa: E402
import simulate as sim  # noqa: E402
import watch_execution as watch  # noqa: E402
import zeon_sync as zs  # noqa: E402

MODEL = os.environ.get("PIPELINE_AGENT_MODEL", "gemini-2.5-flash")
INPUTS_DIR = PROJECT_ROOT / "inputs"
RESULTS_DIR = analyze.RESULTS_DIR  # owned by the module that writes them


# --- shared: reading the beads DAG ---------------------------------------------

def list_rounds_tool(stage: str = None, assay_type: str = None) -> dict:
    """List campaign rounds, newest first, optionally filtered.

    `stage` is one of planned/simulated/approved/running/deviated/decided.
    `assay_type` is one of kinetics/cfps_expression/inhibitor_dose_response.
    Use this whenever the operator refers to a round without giving an id.
    """
    rounds = bw.list_rounds(stage=stage, assay_type=assay_type)
    return {
        "count": len(rounds),
        "rounds": [
            {
                "round_id": r["id"],
                "title": r.get("title"),
                "stage": next((l.split(":", 1)[1] for l in r.get("labels", []) if l.startswith("stage:")), None),
                "assay_type": next((l.split(":", 1)[1] for l in r.get("labels", []) if l.startswith("assay:")), None),
                "status": r.get("status"),
            }
            for r in rounds
        ],
    }


def round_status_tool(round_id: str) -> dict:
    """Full status of one round: its stage, assay type, linked physical
    executions, whether its input preset exists, and whether results have been
    written. This is the tool to call before doing anything to a round."""
    round_ = bw.show_round(round_id)
    children = bw.list_children(round_id)
    preset = INPUTS_DIR / f"{round_id}.json"
    results = RESULTS_DIR / f"{round_id}.json"
    assay_type = round_.get("_assay_type")
    return {
        "round_id": round_id,
        "title": round_.get("title"),
        "stage": round_.get("_stage"),
        "assay_type": assay_type,
        "target_workflow": zs.WORKFLOW_FOR_ASSAY.get(assay_type),
        "executions": [
            {
                "kind": next(
                    (l.split(":", 1)[1] for l in c.get("labels", []) if l.startswith("execution_kind:")), None
                ),
                "execution_id": c.get("metadata", {}).get("execution_id"),
            }
            for c in children
        ],
        "has_input_preset": preset.exists(),
        "has_results": results.exists(),
    }


def show_round_inputs_tool(round_id: str) -> dict:
    """The exact input values a planned round will run with, from
    inputs/<round_id>.json. Read this back to the operator when they ask what a
    round actually does, or before asking them to approve it."""
    path = INPUTS_DIR / f"{round_id}.json"
    if not path.exists():
        return {"error": f"no input preset for {round_id} — it may be a cfps_expression round, "
                         "which is set up by hand in the cfps_mastermix canvas instead"}
    return json.loads(path.read_text())


def note_on_round_tool(round_id: str, text: str) -> dict:
    """Attach a free-text note to a round's bead — operator observations, why a
    range was chosen, anything the numbers don't carry."""
    bw.note(round_id, text)
    return {"round_id": round_id, "noted": text}


DASHBOARD_PATH = PROJECT_ROOT / "pipeline" / "apps" / "dashboard.py"
DASHBOARD_PORT = int(os.environ.get("PIPELINE_DASHBOARD_PORT", "2718"))


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def open_dashboard_tool() -> dict:
    """Launch the marimo campaign-provenance dashboard (pipeline/apps/dashboard.py)
    and open it in the operator's browser.

    Starts it with `marimo run` (the read-only app view, not `marimo edit`) — this
    is the finished dashboard, not a notebook to poke at. If a dashboard is
    already listening on the expected port, this just opens that instead of
    starting a second server. Runs the server as a detached background process —
    it keeps running after this tool call returns, and after this chat session
    ends.
    """
    url = f"http://127.0.0.1:{DASHBOARD_PORT}"
    already_running = _port_open(DASHBOARD_PORT)
    if not already_running:
        subprocess.Popen(
            ["marimo", "run", str(DASHBOARD_PATH), "-p", str(DASHBOARD_PORT), "--no-token", "--headless"],
            cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        for _ in range(20):
            time.sleep(0.5)
            if _port_open(DASHBOARD_PORT):
                break
    opened = webbrowser.open(url)
    return {
        "url": url,
        "already_running": already_running,
        "opened_in_browser": bool(opened),
        "note": "give this URL to the operator regardless of opened_in_browser — a headless "
                "or remote session can't pop a local browser window even though the server is up.",
    }


SHARED_TOOLS = [list_rounds_tool, round_status_tool, open_dashboard_tool]


# --- Plan -----------------------------------------------------------------------

def read_protocol_document_tool(path: str) -> dict:
    """Read a protocol document — a dosing table, dilution scheme, or kit insert —
    and return its text.

    Takes a filesystem path (PDF, txt, md, csv, json, yaml). You have NO other way
    to see a file's contents: a path in the conversation is just a string until
    this tool returns its text. Read the document before planning from it, and
    transcribe its numbers into plan_kinetics_round_by_volume_tool rather than
    stating them as done.
    """
    return protocol_docs.read_document(path)


def list_compound_library_tool() -> dict:
    """The compound library available to screen, from
    pipeline/library/compounds.csv, marked with which ones already have a
    dose-response round in beads."""
    library = plan.load_compound_library()
    screened = {
        r.get("metadata", {}).get("compound_id")
        for r in bw.list_rounds(assay_type="inhibitor_dose_response")
    }
    return {
        "compounds": [{**row, "already_screened": row["compound_id"] in screened} for row in library],
        "count": len(library),
    }


planner = Agent(
    name="planner",
    model=MODEL,
    description="Chooses the conditions for the next round and writes them as an input preset.",
    instruction=(
        "You plan rounds of a TEM1 beta-lactamase screening campaign.\n"
        "Round types:\n"
        "1. kinetics — prerequisite. A purified-TEM1 x nitrocefin grid, read kinetically. Its "
        "fit sets the nitrocefin working concentration everything downstream uses. Two ways "
        "to plan it: plan_kinetics_round_tool takes target concentrations (3 enzyme levels in "
        "nM, 3 nitrocefin levels in uM) and derives volumes from the stock tubes; "
        "plan_kinetics_round_by_volume_tool takes the per-leg volumes directly, which is the "
        "form a protocol document's dosing table is written in. Prefer the by-volume tool "
        "whenever the operator has given you a document or explicit volumes.\n"
        "2. inhibitor_dose_response — one compound dosed across confirmed-expressed wells. "
        "Needs the operator to name which wells on the current CFPS plate came back "
        "confirmed-expressed from a cfps_expression round. Use list_compound_library_tool to "
        "pick the next unscreened compound unless the operator names one, and pass "
        "prior_ic50_um when a previous round fit one, so the series centers on it.\n"
        "3. cfps_expression rounds are NOT planned here — they're set up by hand in the "
        "cfps_mastermix canvas. Say so if asked.\n\n"
        "Before planning a dose-response round, check with list_rounds_tool that a kinetics "
        "round has reached stage 'decided'; if none has, say so and offer to plan the "
        "kinetics round first rather than silently proceeding.\n\n"
        "WORKING FROM A DOCUMENT: when the operator gives you a file path, that path is only "
        "a string to you — you cannot see the contents until read_protocol_document_tool "
        "returns them. Read it, transcribe the dosing table into "
        "plan_kinetics_round_by_volume_tool, and then compare the in-well concentrations that "
        "tool returns against what the document claims. If they disagree, say so — a mismatch "
        "means you misread a row or the document's stocks differ from this bench's.\n\n"
        "NEVER state that a file, workflow, or preset has been changed unless a tool call in "
        "this conversation returned that change. You have no ability to edit files by "
        "describing an edit. Planning writes a preset only; nothing reaches the workflow until "
        "the syncer bakes it, and nothing reaches the Zeon app until it is pushed. Say exactly "
        "which of those has happened.\n"
        "After planning, read the preset back with show_round_inputs_tool, report the "
        "round_id and the key conditions (volumes, concentrations, well count, run_name), and "
        "tell the operator the next step is Sync — nothing has reached the Zeon app yet."
    ),
    tools=[
        plan.plan_kinetics_round_tool,
        plan.plan_kinetics_round_by_volume_tool,
        plan.plan_inhibitor_round_tool,
        read_protocol_document_tool,
        list_compound_library_tool,
        show_round_inputs_tool,
        note_on_round_tool,
        *SHARED_TOOLS,
    ],
)


# --- Sync -----------------------------------------------------------------------

def bake_round_into_workflow_tool(round_id: str, dry_run: bool = True) -> dict:
    """Write a planned round's values into its workflow's input defaults, so the
    Zeon app's run-setup opens pre-filled with exactly this round.

    Call with dry_run=True first and show the operator what would change; only
    call with dry_run=False once they've seen it. This edits the workflow file
    locally — it does not reach the cloud until zeon_push_tool runs.
    """
    round_ = bw.show_round(round_id)
    assay_type = round_.get("_assay_type")
    workflow_id = zs.WORKFLOW_FOR_ASSAY.get(assay_type)
    if workflow_id is None:
        return {"error": f"no workflow mapped for assay_type {assay_type!r}"}
    result = zs.bake_preset_into_workflow(round_id, workflow_id, dry_run=dry_run)
    if not dry_run:
        bw.note(round_id, f"Baked {result['changed_count']} input default(s) into {workflow_id}")
    return result


def set_active_workflow_tool(workflow_id: str) -> dict:
    """Point project.json's active_workflow at a workflow, so it's what the Zeon
    app opens by default. Do this for the workflow the operator is about to run."""
    return zs.set_active_workflow(workflow_id)


def zeon_status_tool() -> dict:
    """What's changed locally versus the Zeon cloud HEAD. Always call this before
    proposing a push, and show the operator the file list."""
    return zs.zeon_status()


def zeon_push_tool(message: str, round_id: str = None) -> dict:
    """Commit the working tree and push it to the Zeon cloud, making these values
    what the app opens.

    OUTWARD-FACING AND SHARED: after this, anyone opening the project sees these
    values. Only call it when the operator has explicitly said to push in this
    conversation — never as an automatic follow-up to baking.
    """
    result = zs.zeon_commit_and_push(message)
    if round_id:
        bw.note(round_id, f"Synced to Zeon cloud: {message}")
    return result


syncer = Agent(
    name="syncer",
    model=MODEL,
    description="Gets a planned round's values into the Zeon app by editing workflow defaults and pushing.",
    instruction=(
        "You move a planned round's numbers from its local preset into the Zeon app.\n"
        "The app fills its run-setup canvas from the workflow's own input defaults, so the "
        "sequence is: bake_round_into_workflow_tool(dry_run=True) -> show the operator the "
        "diff -> bake_round_into_workflow_tool(dry_run=False) -> set_active_workflow_tool -> "
        "zeon_status_tool -> ask the operator whether to push -> zeon_push_tool.\n\n"
        "Pushing is outward-facing and shared: it changes what the cloud project shows "
        "everyone. NEVER call zeon_push_tool without the operator saying to push in this "
        "conversation. Approval to push one round is not approval to push the next.\n"
        "Report only what the tools returned: bake_round_into_workflow_tool's changed_count "
        "and zeon_push_tool's output are your evidence. Never say a workflow was updated, "
        "synced, or pushed without the corresponding tool result in this conversation — if "
        "changed_count is 0, nothing changed, and you say that.\n"
        "If baking raises about preset keys with no matching workflow input, do not work "
        "around it — report it plainly. It means the plan and the workflow graph have drifted "
        "and the operator would otherwise run a different plate than the round claims."
    ),
    tools=[
        bake_round_into_workflow_tool,
        set_active_workflow_tool,
        zeon_status_tool,
        zeon_push_tool,
        show_round_inputs_tool,
        *SHARED_TOOLS,
    ],
)


# --- Simulate -------------------------------------------------------------------

def simulate_round_tool(round_id: str) -> dict:
    """Validate the project as the round would run it: structural checks, node
    parameters against real skill signatures, call sites against the robot API,
    anchors against object models, plus server-side IK/collision verification if
    this zeon build supports it. Moves the round to 'simulated' on a clean pass,
    or to 'deviated' on failure. Run this after syncing, before approval."""
    res = sim.simulate_round(round_id)
    return {
        "ok": res.ok,
        "errors": res.errors,
        "warnings": res.warnings[:20],
        "warning_count": len(res.warnings),
        "zeon_verify_skipped": res.verify_skipped_reason,
        "summary": res.reason(),
    }


simulator = Agent(
    name="simulator",
    model=MODEL,
    description="Runs deterministic validation on a round and records the result.",
    instruction=(
        "You run Simulate for a round: call simulate_round_tool and report what came back.\n"
        "On failure the round is already marked 'deviated' — quote the actual errors, name "
        "the file and node they point at, and hand back to the coordinator so Plan or Sync "
        "can fix them. Do not attempt to fix files yourself.\n"
        "On success, say explicitly whether server-side `zeon verify` ran or was skipped. If "
        "it was skipped, the pass covers structure and parameters only — it is NOT evidence "
        "the arm motion is collision-free, and you should say that rather than implying the "
        "round is physically safe."
    ),
    tools=[simulate_round_tool, *SHARED_TOOLS],
)


# --- Execute (approve + watch; the run itself is human-triggered) ----------------

def approve_round_tool(round_id: str, operator_note: str = "") -> dict:
    """Record the operator's go-ahead: opens a beads human gate on the round,
    resolves it, and moves the round to 'approved'.

    Only call this when the operator has said yes in this conversation, and only
    for a round already at stage 'simulated'.
    """
    round_ = bw.show_round(round_id)
    stage = round_.get("_stage")
    if stage != "simulated":
        return {"error": f"{round_id} is at stage {stage!r}, not 'simulated' — simulate it first"}
    gate_id = bw.create_human_gate(round_id, reason="operator approval via chat")
    bw.resolve_gate(gate_id, reason=operator_note or "approved by operator in chat")
    bw.set_stage(round_id, "approved", reason=operator_note or "approved by operator in chat")
    return {"round_id": round_id, "stage": "approved", "gate_id": gate_id}


def run_instructions_tool(round_id: str) -> dict:
    """Everything the operator needs to start this round's run themselves in the
    Zeon app: which workflow to open, the run_name to use, and the deck items the
    round expects to be loaded."""
    status = round_status_tool(round_id)
    preset_path = INPUTS_DIR / f"{round_id}.json"
    preset = json.loads(preset_path.read_text()) if preset_path.exists() else {}
    deck = {k: v for k, v in preset.items() if isinstance(v, str) and not k.startswith("_")}
    return {
        "round_id": round_id,
        "stage": status["stage"],
        "open_workflow": status["target_workflow"],
        "run_name": preset.get("run_name"),
        "deck_and_labels": deck,
        "how": (
            "Open the project in the Zeon app, select the workflow above (its run-setup "
            "canvas is already pre-filled if this round was synced), confirm the deck, and "
            "start the run. Keep run_name exactly as given — that string is how the pipeline "
            "matches the physical execution back to this round."
        ),
    }


def check_execution_tool(round_id: str, part1_run_name: str = None, part2_run_name: str = None) -> dict:
    """Check whether the operator's run has landed in data/logs yet, link it to
    the round, and report whether the plate-reader export is ready to analyze.

    For a cfps_expression round pass the run names of its two parts; for kinetics
    and inhibitor_dose_response rounds the run_name comes from the preset.
    Returns a status string: waiting_for_execution / running / ready_for_analyze
    / part1_detected_awaiting_gate / already_complete.
    """
    round_ = bw.show_round(round_id)
    if round_.get("_assay_type") == "cfps_expression":
        if not part1_run_name:
            return {"error": "cfps_expression rounds need part1_run_name (and later part2_run_name) "
                             "— ask the operator what they named the runs"}
        return watch.watch_cfps_expression_round(round_id, part1_run_name, part2_run_name)
    return watch.watch_single_execution_round(round_id)


executor = Agent(
    name="executor",
    model=MODEL,
    description="Takes the operator's approval, hands over run instructions, and watches for the run landing.",
    instruction=(
        "You handle the Execute stage. Be clear about what you can and cannot do: the Zeon "
        "CLI has NO run command, so you never start a physical run. A person starts it in the "
        "Zeon app. Never imply otherwise or claim a run has started.\n\n"
        "Sequence: confirm the round is at stage 'simulated' -> if the operator says go, call "
        "approve_round_tool -> call run_instructions_tool and give them the workflow, the exact "
        "run_name, and the deck items -> once they say they've started it (or ask), poll with "
        "check_execution_tool.\n"
        "check_execution_tool returns 'waiting_for_execution' until the run's folder appears in "
        "data/logs. That is normal for a run in progress; say so rather than treating it as an "
        "error. When it returns 'ready_for_analyze', hand back to the coordinator for Analyze.\n"
        "For a cfps_expression round, Part 1 detection opens a timer gate for the incubation "
        "before Part 2's sfGFP read — tell the operator the gate exists and roughly how long."
    ),
    tools=[approve_round_tool, run_instructions_tool, check_execution_tool, show_round_inputs_tool, *SHARED_TOOLS],
)


# --- Analyze ---------------------------------------------------------------------

def read_results_tool(round_id: str) -> dict:
    """The written results of an already-analyzed round, from
    pipeline/results/<round_id>.json — fits, IC50, or go/no-go call."""
    path = RESULTS_DIR / f"{round_id}.json"
    if not path.exists():
        return {"error": f"no results for {round_id} — has it been analyzed?"}
    return json.loads(path.read_text())


analyst = Agent(
    name="analyst",
    model=MODEL,
    description="Fits the plate-reader data for a finished round and states what it decides.",
    instruction=(
        "You analyze a round whose run has landed. Check its assay_type with "
        "round_status_tool, then call the matching tool: analyze_kinetics_round_tool "
        "(Michaelis-Menten fit -> recommended nitrocefin working concentration), "
        "analyze_cfps_expression_round_tool (sfGFP go/no-go gate), or "
        "analyze_inhibitor_round_tool (4-parameter logistic -> IC50). Each moves the round to "
        "'decided'.\n"
        "Report the actual numbers, then say what they imply for the next round: a kinetics fit "
        "sets the substrate level for screening; a no-go means do not spend a screen on that "
        "plate; an IC50 becomes the center of the next dose series for that compound.\n\n"
        "If analyze_kinetics_round_tool raises because the round has no input preset "
        "(typically an 'unplanned' round beads created from a physical run that was never "
        "planned through this chat, or a round stuck at 'deviated' for that reason) do NOT give "
        "up — call round_status_tool to get its linked execution_id, then call "
        "analyze_execution_kinetic_export_tool(execution_id, wells) instead. That tool needs no "
        "preset and reports each well's observed initial rate straight from the Gen5 kinetic PDF "
        "at data/platereader/<execution_id>/. wells is REQUIRED — ask the operator which wells "
        "were actually dosed before calling it. A Gen5 export covers the full 96-well plate, and "
        "most of it is empty-plate background; never pass every well in the export just because "
        "the data exists for it. It also does not fit Michaelis-Menten (no known enzyme/substrate "
        "condition per well without a preset) — say so, and ask the operator which wells "
        "correspond to which conditions if they want that read against a specific layout.\n\n"
        "Both the kinetic and endpoint Gen5 parser paths in parse_gen5_export are real, and read "
        "off data/platereader/<execution_id>/*.pdf when a PDF is present there — the endpoint path "
        "(used by analyze_inhibitor_round_tool and analyze_cfps_expression_round_tool) only falls "
        "back to a synthetic stub for an execution_id that has no export yet. Always check whether "
        "results came from a real export or the stub fallback (round_status_tool won't tell you "
        "this directly — check whether data/platereader/<execution_id>/ has a PDF) and state that "
        "plainly. Never present stub numbers as real measurements.\n"
        "If a fit does not converge, say so and suggest a wider or better-centered range "
        "rather than reporting a meaningless parameter."
    ),
    tools=[
        analyze.analyze_kinetics_round_tool,
        analyze.analyze_cfps_expression_round_tool,
        analyze.analyze_inhibitor_round_tool,
        analyze.analyze_execution_kinetic_export_tool,
        read_results_tool,
        note_on_round_tool,
        *SHARED_TOOLS,
    ],
)


# --- Coordinator -------------------------------------------------------------------

root_agent = Agent(
    name="tem1_pipeline",
    model=MODEL,
    description="Conversational driver for the TEM1 CFPS screening campaign, stage by stage.",
    instruction=(
        "You run a TEM1 beta-lactamase screening campaign on a Zeon lab-automation bench, by "
        "talking to the operator and delegating to your sub-agents. Each round moves through a "
        "fixed loop, and beads (`bd`) is the record of it:\n\n"
        "  Plan -> Sync -> Simulate -> Approve -> Execute -> Analyze\n"
        "  planner  syncer  simulator   executor (approve+watch)  analyst\n\n"
        "Stages map to a round's beads stage label: planned -> simulated -> approved -> "
        "running -> decided, or deviated on any failure. Start almost every request with "
        "list_rounds_tool or round_status_tool so you delegate against the round's real state "
        "rather than the conversation's memory of it.\n\n"
        "Rules that hold across the whole loop:\n"
        "- Do not skip stages. A round is not simulated until simulator says so, not approved "
        "until the operator says so, and not decided until analyst has fit real data.\n"
        "- You cannot start a physical run. There is no run command; the operator starts runs "
        "in the Zeon app. Say this plainly whenever it comes up.\n"
        "- Pushing to the Zeon cloud is shared and outward-facing. Ask first, every time.\n"
        "- Round types: kinetics (prerequisite characterization), cfps_expression (two-part "
        "expression + sfGFP go/no-go gate, set up by hand in the cfps_mastermix canvas), and "
        "inhibitor_dose_response (the actual compound screen, which needs both a decided "
        "kinetics round and a 'go' expression round behind it).\n"
        "- Report what the tools returned, including failures and skipped checks. This drives "
        "real hardware and real reagents; an overstated 'all clear' is the expensive kind of "
        "wrong.\n"
        "- If the operator asks to see, open, or pull up the dashboard, call open_dashboard_tool "
        "yourself — do not say you lack that capability. It starts pipeline/apps/dashboard.py "
        "with `marimo run` and opens it in a browser on this machine."
    ),
    sub_agents=[planner, syncer, simulator, executor, analyst],
    tools=[*SHARED_TOOLS, show_round_inputs_tool, note_on_round_tool],
)
