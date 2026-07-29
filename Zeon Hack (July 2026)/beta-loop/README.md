# β-Loop

Closed-loop TEM-1 β-lactamase inhibitor discovery for the [Zeon Systems AI for Science hackathon](https://luma.com/avi3l01q) (Track A).

An ADK agent prioritizes compounds (open literature repositories + optional Paperclip + GNINA docking), a Zeon robot runs the nitrocefin assay, and results feed back into the next plate design — two rounds, real wet lab.

## Two main tasks

Zeon provides a **skills library** (robotic primitives + examples). We have two jobs:

| Task | Focus | Status |
|------|-------|--------|
| **1. Program the assay on robotics** | CFPS → GFP gate → nitrocefin screen workflows | TODO |
| **2. Compound screening** | ADK agent closed loop: prioritize → R1 → analyze → R2 | TODO |

See **[PLAN.md](PLAN.md#two-main-tasks)** for details, owners, and how they connect.

## Team

| Folder | Member | Role |
|--------|--------|------|
| [pvjthomas/](pvjthomas/) | Philip | Bio / hardware / integration, assay QC, demo |
| [ml/](ml/) | Philip | ADK agent, literature search, kinetics analysis |
| [learsch/](learsch/) | Rob (learsch) | Automation — expression (CFPS, GFP) |
| [changhu/](changhu/) | Chang (changhu) | Automation — screening (assay, reader) |

## Docs

- **[ASSAY_WORKFLOW.md](ASSAY_WORKFLOW.md)** — three-assay pipeline (CFPS → GFP gate → nitrocefin screen)
- **[PLAN.md](PLAN.md)** — full project plan, timeline, plate designs
- **[ROLES.md](ROLES.md)** — ownership and handoffs
- **[REQUIREMENTS.md](REQUIREMENTS.md)** — literature backends, ADK, Python deps

## Quick start

```bash
git clone https://github.com/pvjthomas/beta-loop.git
cd beta-loop

# Use GitHub noreply email for commits (avoids GH007 push errors)
git config user.email "pvjthomas@users.noreply.github.com"
git config user.name "pvjthomas"

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add PAPERCLIP_API_KEY, GOOGLE_API_KEY
```

Paperclip CLI (run in your terminal):

```bash
curl -fsSL https://paperclip.gxl.ai/install.sh | bash
```

## Repo layout

```
pvjthomas/      # Philip — bio QC, assay docs, local caches
ml/             # Philip — ADK agent, analysis, compound-selection pipeline
learsch/        # Rob — personal workspace
changhu/        # Chang — personal workspace
data/           # compounds, plate maps, kinetics, literature (shared)
workflows/      # Zeon robot workflows — Task 1 (TODO, shared)
```

## Zeon skills library

Low-level robotic skills (pipetting, sealing, shaking, etc.) are **provided by Zeon** — we compose them into assay workflows rather than building primitives from scratch. Example skills from the brief: `plateshaker_open`, `epipette_aspirate`, `platesealer_run`. Full library in the Zeon GitHub repo (TBA at kickoff).

## Scientific goal

> Which compounds meaningfully reduce TEM-1 β-lactamase activity, and what dose-response patterns do they show?

TargetMol β-lactam library (**105 compounds**, [`data/compounds.csv`](data/compounds.csv)) · nitrocefin kinetic read @ A490 · two closed-loop screening rounds.
