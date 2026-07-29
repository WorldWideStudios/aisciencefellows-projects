# Data — teammate index

Shared **team contract** for the nitrocefin screen. Small summaries live here in git; large raw files live in [`pvjthomas/local/`](../pvjthomas/local/README.md) (gitignored). Full storage policy: **[STORAGE.md](STORAGE.md)**.

---

## Terminology: rounds vs versions

These are **not** the same thing.

| Term | Meaning | Where it appears |
|------|---------|------------------|
| **Round** | Closed-loop screening iteration (R1 discovery → analyze → R2 dose-response) | Filenames: `plate_map_r**1**.json`, `run_**1**_summary.json`, `round_summary_r**1**.json` |
| **Version** | Plate-design revision *within* a round, before the physical plan is locked | Paths: `data/screens/1/v**2**/plate_map.json` |

**Example (current):**

| Round | Version | Label | Status | What it is |
|-------|---------|-------|--------|------------|
| **1** | v1 | `r1-discovery-v1` | Superseded | 24-compound discovery layout — kept as history only |
| **1** | **v2** | `r1-validation-v2` | **Active** | Minimal validation: clavulanic acid (positive) + DMSO vehicle (negative) @ 50 µM |

When the plate design changes, add `data/screens/{run}/v{N+1}/` — **do not edit** older version folders.

---

## Start here (by role)

| I need… | File |
|---------|------|
| **Active plate for the robot (Round 1)** | [`plate_map_r1.json`](plate_map_r1.json) |
| **Frozen snapshot of that design** | [`screens/1/v2/plate_map.json`](screens/1/v2/plate_map.json) |
| **Why these wells / concentrations** | [`../pvjthomas/runs/1/v2/selection_rationale.md`](../pvjthomas/runs/1/v2/selection_rationale.md) |
| **Assay protocol (volumes, mixing order)** | [`../pvjthomas/NITROCEFIN_ASSAY.md`](../pvjthomas/NITROCEFIN_ASSAY.md) |
| **Compound library + source wells** | [`compounds.csv`](compounds.csv) · [LIBRARY.md](LIBRARY.md) |
| **Per-compound expectations** | [`compound_dossiers.json`](compound_dossiers.json) |
| **Literature-backed assay concentrations** | [`literature_summary.json`](literature_summary.json) · [`compound_literature/refs/T19860.json`](compound_literature/refs/T19860.json) |
| **Results after Round 1 run** | [`assay/run_1_summary.json`](assay/run_1_summary.json) |
| **Git vs local / who writes what** | [STORAGE.md](STORAGE.md) |
| **Compound selection pipeline (Philip)** | [`../ml/workflows/compound_selection/`](../ml/workflows/compound_selection/) |

---

## Active vs frozen plate maps (read this)

```
data/plate_map_r1.json          ← ROBOT: always load this for Round 1
        │
        │  (same wells as)
        ▼
data/screens/1/v2/plate_map.json   ← SNAPSHOT: immutable Round 1 / version 2 design
```

- **`plate_map_r{N}.json`** — symlink-like **active** file for round *N*. Robotics and workflows read this.
- **`screens/{round}/v{version}/plate_map.json`** — **frozen** copy when a design version is approved. Never overwrite; bump version instead.

Older Round 1 designs remain under `screens/1/v1/` for audit only.

---

## Round 1 / version 2 — concentrations & literature

Minimal validation plate before the full compound screen.

| Well role | Compound | ID | Final conc. | Library source | Expected |
|-----------|----------|-----|-------------|----------------|----------|
| **Negative** (vehicle) | DMSO only | — | 0 µM (matched %) | — | Max A490 slope — normalization reference |
| **Positive** (inhibitor) | Clavulanic acid | T19860 | **50 µM** | PHD215176 **h7** | ≥50% inhibition vs vehicle |

**Why 50 µM?** Literature TEM-1 Ki = **0.85 µM** (Radojković et al., J Biol Chem 2025, PMC12274840). At 50 µM we are ~60× above Ki — strong inhibition expected. See [`compound_literature/refs/T19860.json`](compound_literature/refs/T19860.json).

| Field | Value |
|-------|-------|
| Working solution | 500 µM (10× dilution: 5 µL into 50 µL) |
| Pre-incubation | 10 min |
| Read | A490, initial slope |
| Full assay priors | [`literature_summary.json`](literature_summary.json) → `compound_assay_priors.T19860` |

**Literature raw files** (Philip local, not in git): `pvjthomas/local/literature/T19860/` — repository + optional Paperclip search dumps + PMC12274840 full text. Curated summary is git-tracked at [`compound_literature/refs/T19860.json`](compound_literature/refs/T19860.json).

**Pass gate:** vehicle slope high · clavulanic ≥50% inhibition vs vehicle → proceed to Round 1 discovery (future v3+) or Round 2.

---

## Directory map

```
data/
├── README.md                 ← this file
├── STORAGE.md                ← git vs local policy
├── LIBRARY.md                ← compounds.csv columns
├── compounds.csv             ← 105-compound library index
├── compound_dossiers.json    ← per-compound summaries
├── literature_summary.json   ← global + per-compound assay priors
├── plate_map_r1.json         ← active Round 1 plate (→ v2)
├── compound_literature/
│   └── refs/
│       ├── README.md
│       └── T19860.json       ← clavulanic acid evidence
├── assay/
│   ├── README.md
│   └── run_1_summary.json    ← Round 1 results (pending)
└── screens/
    ├── README.md
    └── 1/
        ├── v1/               ← superseded discovery layout
        ├── v2/               ← active validation layout
        └── v3/               ← pending sign-off
```

Philip's ADK compound-selection workspace: [`../ml/workflows/compound_selection/`](../ml/workflows/compound_selection/).

Future rounds add `plate_map_r2.json`, `assay/run_2_summary.json`, `screens/2/v1/`, etc.

---

## Related docs

- [screens/README.md](screens/README.md) — version folder conventions
- [assay/README.md](assay/README.md) — results JSON schema
- [compound_literature/refs/README.md](compound_literature/refs/README.md) — per-compound citation schema
- [../ROLES.md](../ROLES.md) — handoffs (H1: plate map → robotics)
