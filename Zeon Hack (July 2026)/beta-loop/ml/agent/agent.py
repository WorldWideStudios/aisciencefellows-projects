"""β-Loop ADK agent — closed-loop TEM-1 inhibitor screening."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import Agent

from agent.prompts import (
    BRIDGE_INSTRUCTION,
    COORDINATOR_INSTRUCTION,
    FORWARD_INSTRUCTION,
    MERGE_INSTRUCTION,
    REVERSE_INSTRUCTION,
    ROUND1_INSTRUCTION,
    ROUND2_INSTRUCTION,
)
from agent.tools.bridge import assign_tier2_analogs, cluster_library, find_tanimoto_neighbors
from agent.tools.compounds import load_compounds, prioritize_compounds
from agent.tools.forward import (
    finalize_forward_run,
    load_reference_inhibitors,
    match_literature_to_library,
    run_forward_literature_searches,
    search_literature_only_forms,
    seed_reference_inhibitors,
    write_literature_summary_from_forward,
)
from agent.tools.kinetics_tool import analyze_kinetics, load_round_summary
from agent.tools.run2_artifacts import generate_run2_artifacts
from agent.tools.run2_data_audit import audit_run2_data_tool
from agent.tools.literature import (
    list_literature_sources,
    load_literature_summary,
    save_literature_search,
    search_chembl_activities,
    search_literature,
)
from agent.tools.plates import design_next_plate, load_plate_map
from agent.tools.reverse import (
    classify_scaffolds_rdkit,
    load_dock_scores,
    rank_by_dock_score,
    reverse_literature_check,
    run_gnina_batch,
)
from agent.tools.selection import (
    generate_round2_plate_draft,
    load_selection_state,
    merge_tier_assignments,
    run_compound_selection_pipeline,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(Path(__file__).parent / ".env")
load_dotenv(REPO_ROOT / ".env")

MODEL = "gemini-2.5-flash"

LITERATURE_TOOLS = [
    load_literature_summary,
    list_literature_sources,
    search_literature,
    search_chembl_activities,
    save_literature_search,
]
FORWARD_TOOLS = [
    seed_reference_inhibitors,
    load_reference_inhibitors,
    run_forward_literature_searches,
    search_literature_only_forms,
    match_literature_to_library,
    write_literature_summary_from_forward,
    finalize_forward_run,
]
REVERSE_TOOLS = [
    classify_scaffolds_rdkit,
    run_gnina_batch,
    load_dock_scores,
    rank_by_dock_score,
    reverse_literature_check,
]
BRIDGE_TOOLS = [
    find_tanimoto_neighbors,
    assign_tier2_analogs,
    cluster_library,
]
MERGE_TOOLS = [
    load_selection_state,
    merge_tier_assignments,
    generate_round2_plate_draft,
    run_compound_selection_pipeline,
]
COMPOUND_TOOLS = [load_compounds, prioritize_compounds]
ANALYSIS_TOOLS = [analyze_kinetics, load_round_summary, audit_run2_data_tool, generate_run2_artifacts]
PLATE_TOOLS = [load_plate_map, design_next_plate]

forward_agent = Agent(
    model=MODEL,
    name="forward_agent",
    description="Phase B forward research pass: Paperclip literature → library inhibitor matching.",
    instruction=FORWARD_INSTRUCTION,
    tools=[*LITERATURE_TOOLS, *FORWARD_TOOLS],
)

reverse_agent = Agent(
    model=MODEL,
    name="reverse_agent",
    description="Phase B reverse pass: RDKit scaffold tags, GNINA rank, per-compound literature.",
    instruction=REVERSE_INSTRUCTION,
    tools=[*REVERSE_TOOLS, load_compounds],
)

bridge_agent = Agent(
    model=MODEL,
    name="bridge_agent",
    description="Phase B bridge: Tanimoto analogs and library clustering when literature ≠ library.",
    instruction=BRIDGE_INSTRUCTION,
    tools=[*BRIDGE_TOOLS, load_reference_inhibitors, load_compounds],
)

selection_merger = Agent(
    model=MODEL,
    name="selection_merger",
    description="Merge forward/reverse/bridge into tiers and Round 2 plate draft.",
    instruction=MERGE_INSTRUCTION,
    tools=[*MERGE_TOOLS, load_compounds],
)

round1_agent = Agent(
    model=MODEL,
    name="round1_planner",
    description="Plans Round 1 using literature priors and the signed-off or draft plate map.",
    instruction=ROUND1_INSTRUCTION,
    tools=[*LITERATURE_TOOLS, *COMPOUND_TOOLS, load_plate_map, load_selection_state],
)

round2_agent = Agent(
    model=MODEL,
    name="round2_designer",
    description="Analyzes Round 1 kinetics and designs the Round 2 dose-response plate.",
    instruction=ROUND2_INSTRUCTION,
    tools=[*LITERATURE_TOOLS, *ANALYSIS_TOOLS, *PLATE_TOOLS],
)

root_agent = Agent(
    model=MODEL,
    name="beta_loop_coordinator",
    description=(
        "Coordinates TEM-1 inhibitor screening: compound selection (forward/reverse/bridge), "
        "Round 1 plate, kinetics analysis, Round 2 design."
    ),
    instruction=COORDINATOR_INSTRUCTION,
    tools=[
        *LITERATURE_TOOLS,
        *FORWARD_TOOLS,
        *REVERSE_TOOLS,
        *BRIDGE_TOOLS,
        *MERGE_TOOLS,
        *COMPOUND_TOOLS,
        *ANALYSIS_TOOLS,
        *PLATE_TOOLS,
    ],
    sub_agents=[
        forward_agent,
        reverse_agent,
        bridge_agent,
        selection_merger,
        round1_agent,
        round2_agent,
    ],
)
