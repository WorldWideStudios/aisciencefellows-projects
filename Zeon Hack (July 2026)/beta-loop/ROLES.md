# Team Roles & Handoffs

| Member | Folder | Role |
|--------|--------|------|
| pvjthomas | [pvjthomas/](pvjthomas/) | Philip — bio / hardware / integration |
| ML | [ml/](ml/) | Philip — ADK agent, Paperclip, kinetics analysis, plate maps |
| learsch (Rob) | [learsch/](learsch/) | Automation — expression pipeline (proposed) |
| changhu (Chang) | [changhu/](changhu/) | Automation — screening pipeline (proposed) |

Quick reference for who does what during the hackathon.

## Two main tasks

| Task | Lead | Support | Folder / path |
|------|------|---------|---------------|
| **1. Program assay on robotics** | Rob + Chang (see folder plans) | pvjthomas (QC) | `workflows/` |
| **2. Compound screening (closed loop)** | ML (Philip) | Chang (robot) | `ml/agent/`, `ml/analysis/`, `data/` |

**ML plan:** [ml/CLOSED_LOOP.md](ml/CLOSED_LOOP.md)  
**Philip's selection science:** [pvjthomas/COMPOUND_SELECTION.md](pvjthomas/COMPOUND_SELECTION.md)

**Proposed automation split:** Rob = CFPS + GFP gate · Chang = screen + kinetics export.  
**TODO — Rob & Chang:** Modify and agree on split in [learsch/README.md](learsch/README.md) and [changhu/README.md](changhu/README.md).

Zeon **skills library** = provided primitives. **Task 1** = compose them into CFPS / GFP / screen workflows. **Task 2** = agent + analysis that drives which compounds go on each plate.

Assign Task 1 vs Task 2 to learsch and changhu at kickoff; Philip spans both roles (ML code in `ml/`, bio QC in `pvjthomas/`).

**Update:** Rob and Chang collaborate on Task 1 automation with a proposed upstream/downstream split — they must review and agree (TODO in their folder READMEs).

## Ownership matrix

| Task | Robotics | You | ML |
|------|:--------:|:---:|:--:|
| Zeon workflow authoring | **lead** | review | — |
| Hardware booking | **lead** | assist | — |
| CFPS / screen execution | **lead** | QC | — |
| Plate reader export → CSV | **lead** | — | consume |
| Kickoff organizer questions | — | **lead** | — |
| GFP / activity gate thresholds | — | **lead** | — |
| Minimal validation plate sign-off | — | **lead** | — |
| Hit threshold (analysis code) | — | define | **implement** |
| Demo narrative & pitch | assist | **lead** | assist |
| ADK agent & LoopAgent | — | review | **lead** |
| Kinetics analysis & IC50 | — | review | **lead** |
| Literature search (repos + optional Paperclip) | — | — | **lead** |
| GNINA / compound priors | — | — | **lead** |
| File schemas | review | **approve** | **lead** |
| R2 plate map sign-off | review | **approve** | **lead** |

## Handoff points

### H0: Literature → ML (Phase 0, before hackathon)
- **Artifact:** `data/compound_literature/*.txt` + `data/literature_summary.json` + `data/compound_literature/refs/`
- **Verify:** known inhibitors listed, assay conc/timing documented, concentration source tagged (`literature` / `10x_ki` / `project_default`)

### H1: ML → Robotics (before each screen)
- **Artifact:** `data/plate_map_r{N}.json`
- **Verify:** well count ≤ 96, controls present, no nitrocefin, DMSO matched

### H2: Robotics → ML (after each screen)
- **Artifact:** `data/kinetics_r{N}.csv`
- **SLA:** ML starts analysis within 5 min of file landing

### H3: ML → Team (after R1 analysis)
- **Artifact:** `data/round_summary_r1.json` + proposed `plate_map_r2.json`
- **SLA:** 30-min team sync before R2 reagents touched

### H4: ML → You (before demo)
- **Artifact:** IC50 table, R1/R2 heatmaps, agent rationale text
- **You** writes final pitch from these

## When blocked

| Blocker | Robotics does | ML does | You do |
|---------|---------------|---------|--------|
| Incubator wait | Polish screen workflow | Test on fake data | Compound QA |
| GFP gate fail | Debug seal/temp/pipetting | Keep building R1 map + analysis on synthetic data | Escalate to organizers |
| Validation plate fail | Debug assay with pvjthomas | — | Fix protocol / escalate |
| Reader queue | Prep next workflow | Dashboard | Slides |
| R1 flat curves | — | Check normalization code | Debug assay conditions |

## Sync schedule

- **11:00** — Kickoff (all)
- **Every 2h** — 5-min standup (all)
- **~16:20** — R1 review + R2 lock (all, mandatory)
- **21:00** — Demo prep check (all)
- **Sunday 12:00** — Final demo rehearsal (all)
