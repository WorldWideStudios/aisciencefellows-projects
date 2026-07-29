# β-Loop — architecture diagrams

Mermaid views of the ADK agent, compound-selection pipeline, and closed-loop screening flow.

**Code:** [`ml/agent/`](ml/agent/) · **Plans:** [PLAN.md](PLAN.md) · [ml/CLOSED_LOOP.md](ml/CLOSED_LOOP.md) · [pvjthomas/COMPOUND_SELECTION.md](pvjthomas/COMPOUND_SELECTION.md)

---

## Phase naming (two schemes)

| Scheme | Phases | Meaning |
|--------|--------|---------|
| **Compound list** | A → B | A = library inventory · B = ADK forward / reverse / bridge → draft plate |
| **Hackathon timeline** | 0 → 4 | 0 = prep · 1 = Sat AM · 2 = R1 · 3 = R2 · 4 = Sunday demo |

After Phase B, work shifts to **screening rounds** (`round1_planner`, `round2_designer`) and the **robot closed loop**.

---

## 1. End-to-end closed loop

Phase A inventory → Phase B selection → Round 1 → analysis → Round 2 → IC50 / demo.

```mermaid
flowchart TB
  subgraph prep [Phase A + 0]
    A[Phase A: compounds.csv + dossiers]
    L0[Phase 0: literature_summary.json + env]
  end

  subgraph phaseB [Phase B — ADK compound selection]
    F[forward_agent] --> M[selection_merger]
    R[reverse_agent] --> M
    B[bridge_agent] --> M
    M --> DRAFT[plate_map_r2_draft.json]
  DRAFT -->|Philip sign-off| R2MAP[data/plate_map_r2.json]
  end

  subgraph r1 [Phase 2 — Round 1]
    RP[round1_planner] --> R1MAP
    R1MAP --> ROB1[Zeon screen R1]
    ROB1 --> K1[kinetics_r1.csv]
    K1 --> AN1[analyze_kinetics]
    AN1 --> SUM1[round_summary_r1.json]
  end

  subgraph r2 [Phase 3 — Round 2]
    RD[round2_designer] --> R2MAP[plate_map_r2.json]
    SUM1 --> RD
    R2MAP --> ROB2[Zeon screen R2]
    ROB2 --> K2[kinetics_r2.csv]
    K2 --> AN2[analyze_kinetics + IC50]
    AN2 --> SUM2[round_summary_r2.json]
  end

  A --> phaseB
  L0 --> phaseB
  prep --> phaseB
  phaseB --> r1
  r1 --> r2
```

---

## 2. ADK agent tree

Root coordinator and six sub-agents ([`ml/agent/agent.py`](ml/agent/agent.py)).

```mermaid
flowchart TB
  ROOT[beta_loop_coordinator<br/>root_agent]

  subgraph phaseBAgents [Phase B — compound list generation]
    F[forward_agent]
    R[reverse_agent]
    B[bridge_agent]
    M[selection_merger]
  end

  subgraph screeningAgents [Screening rounds]
    R1P[round1_planner]
    R2D[round2_designer]
  end

  ROOT --> F
  ROOT --> R
  ROOT --> B
  ROOT --> M
  ROOT --> R1P
  ROOT --> R2D

  F --> M
  R --> M
  B --> M
  M --> DRAFT[ml/workflows/compound_selection/plate_map_r2_draft.json]
  R1P --> ACTIVE[data/plate_map_r1.json]
  R2D --> R2[data/plate_map_r2.json]
```

**Coordinator tools (also on sub-agents):** `run_compound_selection_pipeline`, `search_literature`, `analyze_kinetics`, `design_next_plate`, …

**Planned (not implemented):** wrap coordinator in ADK `LoopAgent` (max 2 iterations).

---

## 3. Phase B — sub-agent pipeline

From [PLAN.md](PLAN.md) — three deterministic passes into the merger.

```mermaid
flowchart LR
  F[forward_agent<br/>literature → library] --> M[selection_merger]
  R[reverse_agent<br/>RDKit tags + GNINA rank] --> M
  B[bridge_agent<br/>Tanimoto + cluster] --> M
  M --> D[ml/workflows/compound_selection/plate_map_r2_draft.json]
```

With promotion gate ([`ml/workflows/compound_selection/README.md`](ml/workflows/compound_selection/README.md)):

```mermaid
flowchart LR
  F[forward_agent] --> M[selection_merger]
  R[reverse_agent] --> M
  B[bridge_agent] --> M
  M --> D[plate_map_r2_draft.json]
  D -->|"Philip sign-off"| P[data/plate_map_r2.json]
```

| Pass | Agent | Key output |
|------|-------|------------|
| Forward | `forward_agent` | `reference_inhibitors.csv`, `compound_literature/refs/*.json` |
| Reverse | `reverse_agent` | `selection/state.json`, optional `dock_score` |
| Bridge | `bridge_agent` | `similarity/neighbors.json` |
| Merge | `selection_merger` | `plate_map_r2_draft.json` |

---

## 4. Forward / reverse / bridge strategy

Science-level flow from [pvjthomas/COMPOUND_SELECTION.md](pvjthomas/COMPOUND_SELECTION.md) — tiers → Round 1 plate.

```mermaid
flowchart TB
  subgraph forward [Forward — literature first]
    L1[Paperclip / ChEMBL: TEM-1 inhibitors]
    L2[Extract names + SMILES + IC50 priors]
    L3[Match to library by name / InChIKey / SMILES]
    L4{Direct hit in library?}
  end

  subgraph reverse [Reverse — library first]
    R1[Parse all 105 library SMILES from compounds.csv]
    R2[Tag scaffold class: inhibitor vs antibiotic]
    R3[GNINA dock vs TEM-1 1JQL]
    R4[Paperclip: any literature on these compounds?]
  end

  subgraph bridge [Bridge — when no overlap]
    B1[Tanimoto similarity vs literature inhibitors]
    B2[Nearest neighbors in library]
    B3[Cluster by Morgan FP — pick diverse reps]
  end

  L4 -->|yes| T1[Tier 1: must-test]
  L4 -->|no| B1
  B2 --> T2[Tier 2: similarity analogs]
  R2 --> T1
  R3 --> T3[Tier 3: dock score rank]
  R2 --> T4[Tier 4: substrate controls]
  T1 --> PLATE[Round 1 plate map]
  T2 --> PLATE
  T3 --> PLATE
  T4 --> PLATE
```

---

## 5. System architecture (ML ↔ robot ↔ human)

Cross-layer file contract from [PLAN.md](PLAN.md).

```mermaid
flowchart TB
  subgraph ml [ML — Google ADK coordinator]
    TOOLS[prioritize_compounds · analyze_kinetics<br/>design_next_plate · search_literature]
  end

  subgraph robot [Robotics — Zeon protocol runner]
    WF[cfps · gfp_read · screen]
  end

  subgraph human [Human QC]
    QC[gates · sign-off · demo]
  end

  ml -->|plate_map_rN.json| robot
  robot -->|kinetics_rN.csv| ml
  ml -->|round_summary_rN.json| ml
  human --> ml
  human --> robot
  robot --> human
```

---

## 6. Task 1 (robotics) ↔ Task 2 (screening)

How the two hackathon workstreams connect ([PLAN.md](PLAN.md)).

```mermaid
flowchart LR
  subgraph task1 [Task 1 — robotics]
    CFPS[CFPS workflow]
    GFP[GFP workflow]
    SCR[Screen workflow]
  end

  subgraph task2 [Task 2 — screening agent]
    AGENT[ADK agent]
  end

  CFPS --> ENZ[enzyme ready]
  GFP --> ENZ
  ENZ --> R1MAP[plate_map_r1.json]
  R1MAP --> SCR
  AGENT --> R1MAP
  SCR --> K1[kinetics_r1.csv]
  K1 --> AGENT
  AGENT --> R2MAP[plate_map_r2.json]
  R2MAP --> SCR
  SCR --> K2[kinetics_r2.csv]
  K2 --> DEMO[IC50 + demo]
  AGENT --> DEMO
```

---

## Related docs

| Doc | Contents |
|-----|----------|
| [ml/agent/README.md](ml/agent/README.md) | Run commands, tool modules, file contract |
| [ml/CLOSED_LOOP.md](ml/CLOSED_LOOP.md) | Phase 0–4 checklist, R2 design rules |
| [PLAN.md](PLAN.md) | Master timeline, schemas, validation plate |
