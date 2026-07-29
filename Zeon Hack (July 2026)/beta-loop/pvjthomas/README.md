# Philip (pvjthomas)

**Roles:** Bio / hardware / integration **and** ML (Task 2) — same person, two folders by concern.

| Concern | Folder | Docs |
|---------|--------|------|
| **ML — agent, analysis, closed loop** | [ml/](../ml/) | [ml/CLOSED_LOOP.md](../ml/CLOSED_LOOP.md), [ml/agent/](../ml/agent/) |
| **Bio — assay QC, gates, demo, selection science** | this folder | [COMPOUND_SELECTION.md](COMPOUND_SELECTION.md), [NITROCEFIN_ASSAY.md](NITROCEFIN_ASSAY.md) |

Shared deliverables land in `data/` at repo root. Task 2 code lives under **`ml/`** (not a separate root `agent/`).

## Bio lead tasks

- [ ] Sign off **minimal validation plate** before full discovery R1
- [ ] Kickoff organizer questions
- [ ] GFP / activity gate thresholds
- [ ] Demo narrative & pitch
- [ ] QC on CFPS and screen runs
- [ ] Sign off R2 plate map
- [ ] Approve file schemas

## ML lead tasks

See [ml/CLOSED_LOOP.md](../ml/CLOSED_LOOP.md) — agent, analysis, and plate files are tracked there.

**Kinetics / median scoring** (canonical: [runs/2/v5/run2_decision_tree.md](runs/2/v5/run2_decision_tree.md), [PLAN.md](../PLAN.md) § Assay logic):

- [x] Document median scoring — control medians (3/3 vehicle, 3/3 no-TEM-1); compound call = median of 3/3 well scores
- [x] Implement in `ml/analysis/kinetics.py` + unit tests (`ml/agent/tests/unit/test_kinetics.py`)
- [ ] Run `analyze_kinetics_file()` on first real Run 2 CSV; confirm Q1/Q2/Q3 gates match hand read
- [ ] Write `data/assay/run_2_summary.json` with per-compound `median_pct_inhibition` and decision-tree labels
- [ ] Wire ADK `analyze_kinetics()` tool to return compound-level medians (not per-well hits only)

## This folder (`pvjthomas/`)

Use for bio/integration artifacts only:

| Path | Purpose |
|------|---------|
| [`output/`](output/) | Written reports (e.g. Phase A inventory) |
| [`local/`](local/) | Gitignored Paperclip dumps, GNINA poses, debug caches |
| [`runs/`](runs/) | Selection rationale per screen version |
| [`.claude/skills/paperclip/`](.claude/skills/paperclip/SKILL.md) | Paperclip skill for Claude Code |
| `NITROCEFIN_ASSAY.md`, `COMPOUND_SELECTION.md` | Assay + selection science |

Task 2 code moved to **`ml/agent/`**, **`ml/analysis/`**, **`ml/workflows/compound_selection/`**.

## Handoffs

**Receives (ML produces, bio signs off):**
- **H3:** `round_summary_r1.json` + proposed `plate_map_r2.json`
- **H4:** IC50 table, heatmaps, agent rationale → write final pitch

**Sends:**
- Gate pass/fail before screen slots
- Final demo script to team
