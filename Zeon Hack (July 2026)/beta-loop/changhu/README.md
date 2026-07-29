# Chang (changhu) — Automation plan

**Primary role:** Screening pipeline (Task 1, downstream)  
**Partner:** [Rob (learsch)](../learsch/README.md) — expression pipeline  
**Support / QC:** [pvjthomas](../pvjthomas/README.md)

> **TODO — Rob & Chang:** Review this proposed split together, edit anything that doesn’t fit your skills or kickoff constraints, and **agree on final ownership** (check both READMEs, note changes in a comment or quick sync). Default assumption below until you change it.

Personal workspace for WIP. Promote finished workflows to shared `workflows/`.

---

## Proposed split (Task 1 — robotics)

| | Chang (you) | Rob |
|---|-------------|-----|
| **Track** | Screen & export data | Make & confirm enzyme |
| **Workflows** | `screen` | `cfps`, `gfp_read` |
| **Hardware blocks** | Screen R1 + R2 | CFPS + GFP gate (first) |
| **Handoff** | Waits for GFP gate pass | “Enzyme ready” → you run assay |

---

## Your deliverables

- [ ] `workflows/screen.json` — nitrocefin kinetic assay end-to-end
- [ ] Read `data/plate_map_r{N}.json` → robot well assignments
- [ ] Export `data/kinetics_r1.csv`, `data/kinetics_r2.csv` from plate reader
- [ ] Vehicle + no-TEM-1 controls on every screen plate
- [ ] Book and run **Round 1 & Round 2** screen blocks

## Screen workflow steps

1. Assay buffer
2. Enzyme (skip no-TEM-1 wells)
3. Compound per well (from source plate)
4. Pre-incubate RT
5. Nitrocefin — track time
6. A490 kinetics (30 s intervals)

## Your checklist

- [ ] Build screen workflow in sim **while Rob runs CFPS**
- [ ] Validate workflow accepts `plate_map_r1.json` / `plate_map_r2.json`
- [ ] Confirm DMSO matched in vehicle vs compound wells
- [ ] Plate reader export → CSV format agreed with analysis owner
- [ ] **No screen slot until Rob confirms GFP gate pass**

## Handoff from Rob

Block on:

- GFP gate pass message from Rob
- Enzyme prep location / plate map for enzyme source wells

Then execute plate maps from agent (Task 2) — review format **before** R1 hardware.

---

## Do together (first ~2 h at hack)

- [ ] Zeon skills library tour + sim setup
- [ ] Agree pipette volumes, DMSO matching, timing
- [ ] Freeze `plate_map.json` schema (you implement consumer)
- [ ] Dry-run screen in sim with fake plate map

---

## Sat timeline (draft)

| Time | Chang |
|------|-------|
| AM | Build screen workflow in sim |
| Midday | Finalize screen; review `plate_map_r1.json` |
| PM | **Run Screen R1** |
| Eve | **Run Screen R2** |
| Sun | Reader export fixes for demo |

---

## Task 2 interface (with pvjthomas)

You own the **robot side** of the closed loop:

- Consume `plate_map_r*.json` from agent
- Produce `kinetics_r*.csv` for analysis

Agent / IC50 / Paperclip / plate maps → [ml/](../ml/README.md). Validation sign-off → [pvjthomas/](../pvjthomas/).

---

## Shared paths

| Path | Your files |
|------|------------|
| `workflows/screen.json` | lead |
| `data/kinetics_r*.csv` | generate |
| `data/plate_map_r*.json` | consume |

See [PLAN.md](../PLAN.md#two-main-tasks) for full project context.
