# β-Loop ADK agent

**Personal / experimental** — Philip's ADK workspace under `ml/` (Task 2). Bio/QC notes stay in `pvjthomas/`.

Closed-loop agent for compound screening experiments. Reads/writes shared `data/` per [STORAGE.md](../../data/STORAGE.md).

## Architecture

```
beta_loop_coordinator (root_agent)          ← adk run / adk web entry point
├── Phase B — compound list generation
│   ├── forward_agent                       ← literature → library matching
│   ├── reverse_agent                       ← RDKit scaffolds, GNINA rank stub
│   ├── bridge_agent                        ← Tanimoto + clustering
│   └── selection_merger                    ← tiers → plate_map_r2_draft.json
├── Screening rounds
│   ├── round1_planner                      ← literature + R1 plate confirmation
│   └── round2_designer                     ← R1 analysis + R2 design
└── Tools (also on coordinator)
    ├── run_compound_selection_pipeline()   ← offline F→R→B→merge
    ├── load_literature_summary() / search_literature() / search_chembl_activities()
    ├── reverse_literature_check()          ← per-compound open-repo search
    ├── classify_scaffolds_rdkit()
    ├── find_tanimoto_neighbors()
    └── analyze_kinetics() / design_next_plate()
```

Human-in-the-loop: draft plates live in `ml/workflows/compound_selection/` until sign-off; then promote to `data/plate_map_r2.json`. Round 1 used the simple validation plate in `data/plate_map_r1.json`.

## Run

From repo root (with `.env` configured for Vertex; optional `PAPERCLIP_API_KEY`, `NCBI_API_KEY`):

```bash
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/install-paperclip.sh

# Interactive CLI
adk run ml/agent

# Web UI
adk web ml/agent --port 8000
```

### Offline pipeline (no live API calls)

```bash
python -c "
import sys
sys.path.insert(0, 'ml')
from agent.tools.selection import run_compound_selection_pipeline
import json
print(json.dumps(run_compound_selection_pipeline(), indent=2))
"
```

### Reverse literature (open repositories)

```bash
cd ml/agent && PYTHONPATH=. python3 -c "
from agent.tools.reverse import reverse_literature_check
print(reverse_literature_check(tiers=[1,2,3,4], use_cache=True))
"
```

Default sources: `europe_pmc`, `pubmed`, `chembl`, `semantic_scholar`, `openalex`. Optional Paperclip: pass `sources=['pmc','biorxiv','proteins']`.

### Example ADK prompts

| Phase | Prompt |
|-------|--------|
| **Phase B full** | "Run compound selection pipeline without live literature searches." |
| **Forward only** | "Delegate to forward_agent: seed references, match literature to library, and finalize v1." |
| **Reverse lit** | "Run reverse_literature_check for all Tier 1–4 compounds; then search_chembl_activities for tazobactam and sulbactam." |
| **Reverse only** | "Delegate to reverse_agent: classify scaffolds with RDKit and rank Tier 3." |
| **Bridge only** | "Delegate to bridge_agent: find Tanimoto neighbors and Tier 2 analogs." |
| **Merge** | "Delegate to selection_merger: merge tiers and write plate draft." |
| **Before R1** | "Load literature summary and confirm Round 1 compound picks." |
| **After R1** | "Analyze Round 1 kinetics and design the Round 2 dose-response plate." |

## Phase B outputs

| Path | Git? | Description |
|------|------|-------------|
| `data/reference_inhibitors.csv` | ✓ | Gold inhibitor list (forward) |
| `ml/workflows/compound_selection/state.json` | ✓ | Pipeline state (forward/reverse/bridge/merge) |
| `ml/workflows/compound_selection/plate_map_r2_draft.json` | ✓ | Round 2 draft plate — not for robot |
| `ml/workflows/compound_selection/neighbors.json` | ✓ | Tanimoto neighbor summary |
| `data/compound_literature/refs/{id}.json` | ✓ | Per-compound lit refs (forward + reverse) |
| `ml/workflows/compound_selection/snapshots/forward/v1/` | ✓ | Frozen forward research agent v1 snapshot + manifest |
| `pvjthomas/local/literature/` | ✗ | Raw search dumps (repos + optional Paperclip) |
| `pvjthomas/local/docking/` | ✗ | GNINA poses (when run) |
| `pvjthomas/local/similarity/` | ✗ | Cluster debug / FP caches |

## Tool modules

| Module | Tools |
|--------|-------|
| `tools/literature.py` | `search_literature`, `search_chembl_activities`, `map_literature_results`, `load_literature_summary`, `list_literature_sources` |
| `tools/literature_repositories.py` | Europe PMC, PubMed, ChEMBL, Semantic Scholar, OpenAlex |
| `tools/forward.py` | `seed_reference_inhibitors`, `match_literature_to_library`, `build_compound_groups`, `search_literature_only_forms`, `finalize_forward_run`, … |

See [`tests/FORWARD_TEST_PLAN.md`](tests/FORWARD_TEST_PLAN.md) for v1 test plan. **Status (2026-07-25):** Tier 1–3 complete (31+ tests); live forward ✓; reverse lit ✓ for v3 plate (open repos). **Philip P0:** curate Tier-1 inhibitor Ki/IC50 and apply concentration rules (T19860 is the template).
| `tools/reverse.py` | `reverse_literature_check`, `classify_scaffolds_rdkit`, `run_gnina_batch`, `rank_by_dock_score`, … |
| `tools/bridge.py` | `find_tanimoto_neighbors`, `cluster_library`, `assign_tier2_analogs` |
| `tools/selection.py` | `run_compound_selection_pipeline`, `generate_round2_plate_draft`, … |
| `tools/chem.py` | RDKit helpers (Tanimoto, SMARTS, name normalize) |

## File contract (screening rounds)

| Tool | Reads | Writes |
|------|-------|--------|
| `run_compound_selection_pipeline` | `compounds.csv`, `literature_summary.json` | `ml/workflows/compound_selection/*`, `reference_inhibitors.csv` |
| `prioritize_compounds` | `plate_map_r1.json`, `compounds.csv` | — |
| `analyze_kinetics` | `kinetics_r{N}.csv`, `plate_map_r{N}.json` | `round_summary_r{N}.json` |
| `design_next_plate` | `round_summary_r1.json` | `plate_map_r2.json` |

Analysis logic lives in [`../analysis/`](../analysis/); agent tools are thin wrappers.

See also [`../COMPOUND_SELECTION.md`](../COMPOUND_SELECTION.md) for the science plan.
