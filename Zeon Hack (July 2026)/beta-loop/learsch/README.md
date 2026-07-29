# Rob (learsch) — Automation plan

**Primary role:** Expression pipeline (Task 1, upstream)  
**Partner:** [Chang (changhu)](../changhu/README.md) — screening pipeline  
**Support / QC:** [pvjthomas](../pvjthomas/README.md)

> **TODO — Rob & Chang:** Review this proposed split together, edit anything that doesn’t fit your skills or kickoff constraints, and **agree on final ownership** (check both READMEs, note changes in a comment or quick sync). Default assumption below until you change it.

Personal workspace for WIP. Promote finished workflows to shared `workflows/`.

---

## Proposed split (Task 1 — robotics)

| | Rob (you) | Chang |
|---|-----------|-------|
| **Track** | Make & confirm enzyme | Screen & export data |
| **Workflows** | `cfps`, `gfp_read` | `screen` |
| **Hardware blocks** | CFPS + GFP gate (first) | Screen R1 + R2 |
| **Handoff** | “GFP gate passed — enzyme ready” | Consumes enzyme → runs assay |

---

## Your deliverables

- [ ] `workflows/cfps.json` — cell-free TEM-1 expression (+ controls)
- [ ] `workflows/gfp_read.json` — sfGFP gate readout
- [ ] GFP pass/fail logic documented (thresholds with pvjthomas)
- [ ] Run CFPS on hardware; book expression blocks
- [ ] GFP gate read → explicit go/no-go before Chang screens

## Your checklist

- [ ] Zeon sim: CFPS + GFP workflows validated
- [ ] Skills: pipetting, sealing, shaker, incubator
- [ ] Three CFPS conditions: sfGFP+, no template, TEM-1 fusion
- [ ] Re-run CFPS if GFP gate fails (coordinate with Chang)

## Handoff to Chang

When GFP gate **passes**, notify Chang with:

- Which plate / wells contain usable enzyme prep
- Any timing notes (incubation length, cool-down)
- Gate read values (for lab notebook / demo)

Chang cannot book screen slots until you sign off gate pass.

---

## Do together (first ~2 h at hack)

- [ ] Zeon skills library tour + sim setup
- [ ] Agree pipette volumes, DMSO matching, timing
- [ ] Freeze `plate_map.json` schema (Chang needs this for screen workflow)
- [ ] Dry-run screen in sim with fake plate map

---

## Sat timeline (draft)

| Time | Rob |
|------|-----|
| AM | CFPS on hardware |
| Midday | GFP gate read |
| PM | Support / re-run CFPS if needed |
| Eve | Backup if expression fails |

---

## Shared paths

| Path | Your files |
|------|------------|
| `workflows/cfps.json` | lead |
| `workflows/gfp_read.json` | lead |
| `workflows/screen.json` | Chang leads — you review |

See [PLAN.md](../PLAN.md#two-main-tasks) for full project context.
