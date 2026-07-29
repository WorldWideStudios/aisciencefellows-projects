# Project Requirements

Setup checklist for β-Loop (Track A). Complete **Phase 0** items before Saturday kickoff.

---

## 1. Paperclip — literature search

[Paperclip](https://paperclip.gxl.ai/) indexes 11M+ full-text papers, clinical trials, FDA docs, ChEMBL, PDB, and UniProt. We use it **before Round 1** to ground compound prioritization in known TEM-1 / β-lactamase inhibitor literature.

### Install (choose one)

#### Option A: CLI + agent skill (recommended for ML person)

Run in **your terminal** (not via an agent — sign-in opens a browser):

```bash
curl -fsSL https://paperclip.gxl.ai/install.sh | bash
```

Verify:

```bash
paperclip config
# Server:  https://paperclip.gxl.ai
# Auth:    ✓ you@example.com
# Config:  ~/.paperclip
```

#### Option B: Python SDK (for ADK function tool)

Included in `requirements.txt`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Authenticate with an API key from [paperclip.gxl.ai](https://paperclip.gxl.ai/) (API Keys section):

```bash
export PAPERCLIP_API_KEY="pk_..."
```

Or use credentials saved by `paperclip login` (`~/.paperclip/credentials.json`).

#### Option C: MCP server (for Cursor / Claude Code)

No local install. Add to your MCP client config:

```
https://paperclip.gxl.ai/mcp
```

See [Paperclip docs](https://paperclip.gxl.ai/docs) for Cursor, Claude Code, and other client setup guides.

### Hackathon usage

**Owner:** ML (wrap as ADK function tool `search_literature()`)

Example queries to run in Phase 0:

```bash
paperclip search "TEM-1 beta-lactamase inhibitor clavulanate sulbactam tazobactam" -n 20
paperclip search "nitrocefin beta-lactamase assay IC50" -n 10
paperclip search "beta-lactam antibiotic substrate vs inhibitor TEM-1" -n 10
```

For synthesis across multiple papers:

```bash
paperclip map --from s_<result_id> "What IC50 values and assay conditions were used for TEM-1 inhibitors?"
```

Save outputs to `data/compound_literature/` for the agent to reference when designing Round 1 and Round 2 plates.

### Open literature repositories (no map quota)

The ADK agent also searches **Europe PMC**, **PubMed (NCBI E-utilities)**, **ChEMBL**, **Semantic Scholar**, and **OpenAlex** via `ml/agent/tools/literature_repositories.py` (stdlib `urllib`, no extra pip packages).

Install K-Dense reference skills (optional, for Cursor):

```bash
bash scripts/install-scientific-skills.sh
```

Skills land in `.cursor/skills/scientific-agent-skills/` (paper-lookup, database-lookup, literature-review).

Example agent calls:

```python
from agent.tools.literature import search_literature, search_chembl_activities, list_literature_sources

list_literature_sources()
search_literature("TEM-1 tazobactam Ki nitrocefin", source="europe_pmc", limit=10)
search_chembl_activities("tazobactam", target_query="TEM-1")
```

Optional env vars (rate limits): `NCBI_API_KEY`, `S2_API_KEY`, `OPENALEX_API_KEY`, `OPENALEX_MAILTO`.

Reverse literature check (`reverse_literature_check`) defaults to the five open repositories instead of Paperclip-only search.

### Integration with ADK agent

Literature tools live in [`ml/agent/tools/literature.py`](ml/agent/tools/literature.py):

```python
from agent.tools.literature import (
    search_literature,
    search_chembl_activities,
    map_literature_results,
    load_literature_summary,
    list_literature_sources,
)

list_literature_sources()
search_literature("TEM-1 tazobactam Ki nitrocefin", source="europe_pmc", limit=10)
search_chembl_activities("tazobactam", target_query="TEM-1")

# Paperclip map — only for Paperclip search result ids (s_*)
# map_literature_results("Extract Ki/IC50...", from_results="s_abc123")
```

Per-compound reverse search: `reverse_literature_check()` in [`ml/agent/tools/reverse.py`](ml/agent/tools/reverse.py) — defaults to open repositories, not Paperclip.

Register these as ADK function tools on the `LlmAgent` decision-maker.

---

## 2. Google ADK — agent framework

**Owner:** ML

```bash
pip install google-adk
```

- `LlmAgent` — reads round results, picks compounds, emits plate layout
- `LoopAgent` — Round 1 → Round 2 with session state
- Function tools: `prioritize_compounds`, `analyze_kinetics`, `design_next_plate`, **`search_literature`** (Paperclip)

Docs: [Google Agent Development Kit](https://google.github.io/adk-docs/)

---

## 3. Cheminformatics & analysis

**Owner:** ML

| Package | Purpose |
|---------|---------|
| `rdkit` | β-lactam substructure tags, fingerprints, similarity |
| `numpy`, `pandas`, `scipy` | Kinetics slopes, IC50 fitting |

```bash
pip install -r requirements.txt
```

---

## 4. Docking (optional, Phase 0)

**Owner:** ML

GNINA is not on PyPI — install binary separately if used:

- [GNINA](https://github.com/gnina/gnina) — CNN-scored docking vs TEM-1 (project alias 1JQL → structure 1XPB)
- Batch dock all 105 compounds → scores in `data/compound_dossiers.json` (`docking.gnina_cnn_affinity`)
- Helper: `bash scripts/install-gnina.sh`

### macOS (Philip)

No native macOS binary. Practical options:

1. **Docker + `--no_gpu`** — `docker pull gnina/gnina`; mount repo; see [COMPOUND_SELECTION.md Step R2](pvjthomas/COMPOUND_SELECTION.md#step-r2--docking-gnina)
2. **Remote Linux GPU** — run `run_gnina_batch()` on a Linux box; copy dossiers + `pvjthomas/local/docking/` back
3. **Skip** — pipeline fallback ranking works without scores

Set `GNINA_BIN=/path/to/gnina` when the binary is not on `PATH`.

DiffDock and Boltz-2 are optional stretch goals per hackathon brief.

---

## 5. Zeon robotics

**Owner:** Robotics

- Zeon GitHub repo (TBA at event) — robotic skills and example workflows
- Simulation environment for `cfps`, `gfp_read`, `screen` workflows before hardware

---

## 6. Environment variables

| Variable | Required by | Notes |
|----------|-------------|-------|
| `PAPERCLIP_API_KEY` | Paperclip SDK | Or use `paperclip login` credentials |
| `NCBI_API_KEY` | PubMed E-utilities | Optional; 10 req/s vs 3 without key |
| `S2_API_KEY` | Semantic Scholar | Optional |
| `OPENALEX_API_KEY` | OpenAlex | Optional polite pool |
| `OPENALEX_MAILTO` | OpenAlex | Contact email for polite pool |
| `GOOGLE_API_KEY` | Google ADK | Gemini / ADK backend |

Add a local `.env` (do not commit):

```bash
PAPERCLIP_API_KEY=pk_...
NCBI_API_KEY=...
S2_API_KEY=...
OPENALEX_API_KEY=...
GOOGLE_API_KEY=...
```

---

## Phase 0 install checklist

| Who | Task | Done |
|-----|------|:----:|
| ML | `pip install -r requirements.txt` | ☑ |
| ML | Paperclip CLI or API key configured | ☑ |
| ML | Run TEM-1 literature searches → `data/compound_literature/` | ☐ |
| ML | ADK agent with `search_literature` tool | ☐ |
| ML | GNINA batch dock (optional) | ☐ |
| Robotics | Zeon sim + workflow drafts | ☐ |
| You | `.env` template shared with team (secrets excluded) | ☑ |

### Installed versions (`.venv`, Sat ~14:06)

Verified with `pip install -r requirements.txt` + `scripts/install-paperclip.sh`:

| Package | Version |
|---------|---------|
| `google-adk` | 2.5.0 |
| `gxl-paperclip` | 0.7.11 |
| `numpy` | 2.4.6 |
| `pandas` | 3.0.5 |
| `scipy` | 1.17.1 |
| `rdkit` | 2025.9.3 |

```bash
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/install-paperclip.sh
python -c "import google.adk; from gxl_paperclip import PaperclipClient; import numpy, pandas, scipy; from rdkit import Chem; print('ok')"
```

---

## Quick verify (all tools)

```bash
source .venv/bin/activate
python -c "from gxl_paperclip import PaperclipClient; print('paperclip ok')"
paperclip search "TEM-1 beta-lactamase inhibitor" -n 3
python -c "import google.adk; print('adk ok')"
python -c "from rdkit import Chem; print('rdkit ok')"
```
