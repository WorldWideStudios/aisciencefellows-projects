# ML — Philip (pvjthomas)

**Primary role:** Task 2 — compound screening closed loop (see [ROLES.md](../ROLES.md))

Philip is both **ML** and **bio/integration** on this team. All Task 2 code lives here — ADK agent, analysis, and compound-selection pipeline. Bio/QC notes and assay docs stay in [pvjthomas/](../pvjthomas/).

**Execution plan:** **[CLOSED_LOOP.md](CLOSED_LOOP.md)** — current checklist with done items marked.

## Layout

```
ml/
├── agent/              # Google ADK coordinator + Phase B sub-agents + tests
├── analysis/           # kinetics scoring, R2 plate design, plate viz
├── workflows/
│   └── compound_selection/   # pipeline state, drafts, forward snapshots
├── README.md           # this file
└── CLOSED_LOOP.md      # plan + checklist
```

Selection science rules: [pvjthomas/COMPOUND_SELECTION.md](../pvjthomas/COMPOUND_SELECTION.md)

## Run the agent

From repo root (`.env` configured for Vertex + Paperclip):

```bash
source .venv/bin/activate
pip install -r requirements.txt

# Interactive CLI
adk run ml/agent

# Web UI
adk web ml/agent --port 8000
```

### Offline compound-selection pipeline

```bash
python -c "
import sys
sys.path.insert(0, 'ml')
from agent.tools.selection import run_compound_selection_pipeline
import json
print(json.dumps(run_compound_selection_pipeline(), indent=2))
"
```

### Tests

```bash
.venv/bin/python -m pytest ml/agent/tests/ -q
```

## Shared data contract

| Path | Role |
|------|------|
| `data/compounds.csv` | Library — consume tier/scaffold tags |
| `data/literature_summary.json` | Structured priors |
| `data/plate_map_r*.json` | **Active** robot plates (sign-off before overwrite) |
| `data/kinetics_r*.csv` | Input from Chang after each screen |
| `data/round_summary_r*.json` | Agent analysis output |
| `ml/workflows/compound_selection/` | Drafts + pipeline state (not robot-active) |

See [PLAN.md](../PLAN.md) and [REQUIREMENTS.md](../REQUIREMENTS.md) for schemas.

## Handoffs

| ID | Direction | Artifact |
|----|-----------|----------|
| H1 | ML → Robotics | `data/plate_map_r{N}.json` |
| H2 | Robotics → ML | `data/kinetics_r{N}.csv` |
| H3 | ML → Team | `round_summary_r1.json` + proposed `plate_map_r2.json` |
| H4 | ML → pitch | IC50 table, heatmaps, agent rationale |

## Not blocking ML work

GFP gate, validation plate sign-off, CFPS/screen hardware, and wet-lab QC are shared with [pvjthomas/](../pvjthomas/) bio role — ship analysis code and R2 design paths in parallel.
