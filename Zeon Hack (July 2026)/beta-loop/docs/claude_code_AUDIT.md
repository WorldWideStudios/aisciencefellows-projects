# Mastermix TEM-1 Protocol Audit

> Scope: `mastermix/` only — skills, workflows, canvas, and any transitive Python imports.  
> Reference: `hackathon-track-1-cfps-main/` is the authoritative example.  
> Date: 2026-07-26

---

## Part 1 — Scripts Not Reachable from `tem1_activity_screen.json`

### How reachability is defined

A skill is **reachable** if it appears in the workflow's `nodes` (direct), or is imported in the
`robotic_code.py` of a reachable skill (transitive). Stand-alone `.py` files in `skills/` are
reachable only if imported by a reachable skill.

### Reachable from `tem1_activity_screen`

**Directly referenced as `skill_id`:**
```
batched_dispense_mastermix
epipette_grab
place_current_pipette
prepare_nitrocefin_working_solution
prepare_tem1_dilution_plate
save_run_folder
wait_minutes
wellplate_drop
wellplate_grab
wellplate_shaker_close
wellplate_shaker_load
wellplate_shaker_open
wellplate_shaker_run
wellplate_shaker_unload
```

**Transitively imported by the above:**
```
epipette_aspirate          ← batched_dispense_mastermix, prepare_tem1_dilution_plate,
                              prepare_nitrocefin_working_solution
epipette_dispense          ← same three
epipette_eject             ← same three
epipette_place             ← place_current_pipette → utils.ensure_pipette
epipette_attach            ← utils.attach_next_tip (called by all aspirate paths)
```

**Shared support files:**
```
utils.py                   ← all skills
```

---

### ❌ Skills NOT reachable from `tem1_activity_screen` (candidates for deletion)

These are split into three categories for clarity.

#### Category A — TEM-1 project additions (our code, not in cfps example)

These exist **only in our mastermix** and are not reachable from `tem1_activity_screen`:

| Path | Why it exists | Status |
|---|---|---|
| `skills/gen5_pdf.py` | Parse Gen5 PDF output files | Only imported by `platereader_parse_pdf` — see below |
| `skills/platereader_parse_pdf/` | Parse plate-reader PDF via Gen5 | Not in any active workflow |
| `skills/platereader_run_kinetic_schedule/` | Kinetic read scheduling | Used by `platereader_kinetic_test` and `test_platereader_kinetic_schedule` workflows — **not** by `tem1_activity_screen` |
| `skills/read_schedule.py` | Build kinetic read schedules | Only imported by `platereader_run_kinetic_schedule` |
| `skills/test_gen5_pdf.py` | Dev test script for PDF parsing | Standalone test script, not a skill folder |
| `skills/batched_dispense_mastermix/` | **IS reachable** | ✅ Keep |

The three skills `platereader_parse_pdf`, `platereader_run_kinetic_schedule`, and the supporting
`gen5_pdf.py` / `read_schedule.py` are part of the **kinetic readout sub-system** that was
built in anticipation of a kinetic platereader step. They are not in the cfps example and are
not called by `tem1_activity_screen`. These are **candidates for deletion** if you've decided the
manual endpoint readout workflow is final.

#### Category B — cfps example skills that we copied but don't use in the TEM-1 screen

| Path | Used by cfps_mastermix? | Used by tem1_activity_screen? |
|---|---|---|
| `skills/cfps_dispense_mastermix/` | Yes | No |
| `skills/cfps_make_mastermix/` | Yes | No |
| `skills/cfps_log_platemap/` | Yes | No |
| `skills/seal_plate/` | Yes (cfps) | No |
| `skills/wellplate_shaker_set_state/` | Yes (cfps) | No |
| `skills/platereader_closed/` | cfps-derived platereader test | No |
| `skills/platereader_load/` | cfps-derived platereader test | No |
| `skills/platereader_open/` | cfps-derived platereader test | No |
| `skills/platereader_unload/` | cfps-derived platereader test | No |
| `skills/platesealer_pick_seal/` | via `seal_plate` | No |
| `skills/platesealer_platemax_door/` | via `seal_plate` | No |
| `skills/platesealer_platemax_load/` | via `seal_plate` | No |
| `skills/platesealer_platemax_place_seal/` | via `seal_plate` | No |
| `skills/platesealer_platemax_seal/` | via `seal_plate` | No |
| `skills/platesealer_platemax_unload/` | via `seal_plate` | No |
| `skills/plate_unseal/` | cfps only | No |
| `skills/epipette_mix/` | via `cfps_make_mastermix` | No |

These all come from the cfps example. They are not removable from the cfps workflow, but they
are **dead weight** for your TEM-1 screen.

#### Category C — Test/development skills not used by anything

| Path | Note |
|---|---|
| `skills/arms_home/` | Utility, not in any workflow node |
| `skills/epipette_aspirate_test/` | Development test skill |
| `skills/epipette_attach_test/` | Development test skill |
| `skills/epipette_dispense_test/` | Development test skill |
| `skills/epipette_tip_check/` | Tip verification utility |

#### Canvases and workflows not reachable from `tem1_activity_screen`

| File | Used by |
|---|---|
| `canvas/cfps_mastermix_screen.tsx` | `cfps_mastermix.json` only |
| `canvas/platereader_kinetic_test_screen.tsx` | `platereader_kinetic_test.json` only |
| `canvas/tem1_dilution_plate.tsx` | `tem1_dilution_plate.json` only |
| `workflows/cfps_mastermix.json` | Not active |
| `workflows/platereader_kinetic_test.json` | Not active |
| `workflows/tem1_dilution_plate.json` | Not active (standalone dilution-prep only) |
| `workflows/test_platereader_kinetic_schedule.json` | Not active |

**`tem1_dilution_plate.json` is a standalone workflow** that calls just `prepare_tem1_dilution_plate`.
It was likely used for early testing. It is superseded by the full `tem1_activity_screen` which
includes that step.

### Summary: what you can safely delete (our additions only, per your constraint)

Awaiting your approval before deleting anything. Recommended removal list (our additions, not
from cfps example):

```
mastermix/skills/gen5_pdf.py
mastermix/skills/platereader_parse_pdf/
mastermix/skills/read_schedule.py
mastermix/skills/test_gen5_pdf.py
mastermix/skills/platereader_run_kinetic_schedule/   (our additions to cfps platereader skills)
mastermix/workflows/platereader_kinetic_test.json
mastermix/workflows/test_platereader_kinetic_schedule.json
mastermix/workflows/tem1_dilution_plate.json         (superseded by tem1_activity_screen)
mastermix/canvas/platereader_kinetic_test_screen.tsx
mastermix/canvas/tem1_dilution_plate.tsx
```

The `platereader_open`, `platereader_load`, `platereader_closed`, `platereader_unload` skills are
verbatim cfps copies — do not delete those (they're not your additions), but they're unused by the
TEM-1 screen.

---

## Part 2 — Code We Added vs the cfps Example

### 2.1 New skills (entirely our additions, no cfps equivalent)

| Skill | Purpose |
|---|---|
| `batched_dispense_mastermix` | Aspirate enough for N wells, dispense one-by-one; designed for homogeneous assay liquids that can share a tip. Records nitrocefin timing events per-well. |
| `prepare_tem1_dilution_plate` | Serial dilution of TEM-1 (100 → 1 → 0.1 ng/uL) plus compound/control and vehicle working solutions including a two-step T1262/tazobactam intermediate. |
| `prepare_nitrocefin_working_solution` | Just-in-time 100 uM (2×) nitrocefin working solution from 20 mM stock. |
| `platereader_run_kinetic_schedule` | Orchestrates timed kinetic reads against a JSON schedule. Calls `platereader_measure` in a loop. |
| `platereader_parse_pdf` | Post-run PDF parsing using `gen5_pdf.py`. |

Stand-alone helper modules added:

| File | Purpose |
|---|---|
| `skills/gen5_pdf.py` | Parse Gen5 endpoint PDF output into absorbance data |
| `skills/read_schedule.py` | Build kinetic read schedules (time-series of well-read events) |
| `skills/test_gen5_pdf.py` | Manual dev test for the PDF parser |

### 2.2 Modified copies of cfps skills

#### `batched_dispense_mastermix` vs `cfps_dispense_mastermix`

`cfps_dispense_mastermix` (cfps) dispenses once per well, one tip per well.  
`batched_dispense_mastermix` (ours) **groups wells per aspirate**: computes `wells_per_batch = floor(pipette_max / per_well)` and aspirates the total for a batch before dispensing individually. One tip per batch, not per well — correct for homogeneous reagents.

Key additions vs cfps:
- `_preferred_pipette_name()` — chooses 10 uL vs 120 uL by volume threshold (< 10 uL → 10 uL pipette)
- `_record_timing()` — writes per-event JSON to `project_data_dir("timing/{run_id}/nitrocefin_timing.json")` for any call with `timing_label` set. This fires during nitrocefin dispense.
- `num_reactions` guard — exits early with `{"success": True, "skipped": True}` if 0 (safe but **silent** — see inconsistency issues).
- Returns a dict; cfps also returns a dict. Both return `{"success": True}`.

#### `utils.py`

Identical between mastermix and cfps — no diff. Both are the canonical shared module.

### 2.3 New workflow: `tem1_activity_screen.json`

Not present in cfps at all. Orchestrates 14 direct skill calls (plus transitive sub-calls):

1. `prepare_tem1_dilution_plate` — serial dilution plate prep
2. `epipette_grab` — pick up pipette
3. `batched_dispense_mastermix` ×2 — TEM-1 enzyme prep and no-enzyme BLB
4. `batched_dispense_mastermix` ×2 — vehicle and positive-control
5. `batched_dispense_mastermix` ×9 — compounds 1–9
6. `place_current_pipette` + shaker sequence (open/load/close/run/wait/stop/open/unload/close) + `wellplate_drop`
7. `epipette_grab` → `wait_minutes` (pre-incubation) → `prepare_nitrocefin_working_solution`
8. `batched_dispense_mastermix` ×13 — nitrocefin to all conditions
9. `place_current_pipette` → `save_run_folder`

### 2.4 New canvas: `tem1_activity_screen.tsx`

Hardcodes all plate-layout constants as TypeScript literals (`POSITIVE_WELLS`, `NEGATIVE_WELLS`,
`VEHICLE_WELLS`, `COMPOUND_WELLS`). Builds and submits the full workflow input map including all
volumes, well assignments, and object bindings. Contains an inline deck-loading volume table.

---

## Part 3 — Logical Inconsistencies

These are prioritized: our-implementation-only issues first, then issues shared with cfps.

---

### 🔴 HIGH — Our implementation only

#### I-1: `tazobactam_intermediate_anchor` / `tazobactam_stock_volume_ul` / `tazobactam_intermediate_blb_volume_ul` not exposed in workflow or canvas

**Where:** `prepare_tem1_dilution_plate/robotic_code.py` lines 94, 126–128 vs `tem1_activity_screen.json` inputs vs `tem1_activity_screen.tsx`

The skill has three parameters for the T1262/tazobactam two-step dilution:
```python
tazobactam_intermediate_anchor: str = "hole_3"    # default
tazobactam_stock_volume_ul: float = 1.0           # default
tazobactam_intermediate_blb_volume_ul: float = 49.0  # default
```

None of these are declared in the workflow's `inputs` array, and none are in the canvas `values`
object. This means:
- They always use the **Python defaults** regardless of what the operator configures.
- `hole_3` is used for the T1262 intermediate but is **not tracked in the canvas collision check**
  (`usedHoles` at line 190 of the canvas does not include `hole_3`).

**Risk:** If an operator places something in `hole_3`, the T1262 intermediate liquid will be
pipetted into the wrong tube. No warning is shown. The collision guard in the canvas is incomplete.

**Fix needed:**
1. Add `tazobactam_intermediate_anchor`, `tazobactam_stock_volume_ul`, and
   `tazobactam_intermediate_blb_volume_ul` to the workflow `inputs` (or hardcode them as literal
   constants in the workflow node, not `$input` references).
2. Add `"hole_3"` (or the tazobactam anchor) to `usedHoles` in the canvas validation.

---

#### I-2: `compound_1_source_well` default mismatch between skill and workflow

**Where:** `prepare_tem1_dilution_plate/robotic_code.py` line 99 vs `tem1_activity_screen.json` line 41

The **skill's Python default** for `compound_1_source_well` is `"G6"`.  
The **workflow input default** is `"B10"`.  
The **canvas** default (`DEFAULT_SOURCE_WELLS[0]`) is `"B10"`.

Since the workflow/canvas value overrides the skill default at runtime, `B10` wins — the Python
default `G6` is dead code. But it creates confusion: if the workflow is called without the canvas
(e.g., programmatically with defaults), the wrong well would be picked.

Additionally, many other compound source well defaults in the skill differ from what the workflow
declares. Spot-check:

| Param | Skill default | Workflow default |
|---|---|---|
| `compound_1_source_well` | `G6` | `B10` |
| `compound_3_source_well` | `B10` | `F7` |
| `compound_4_source_well` | `F7` | `A8` |
| `compound_5_source_well` | `A10` | `A9` |
| `compound_6_source_well` | `B10` | `A3` |
| `compound_7_source_well` | `B4` | `A4` |
| `compound_8_source_well` | `H8` | `A2` |
| `compound_9_source_well` | `A3` | `F3` |

The workflow defaults are the authoritative R2 v5 layout and match the canvas — so they are the
correct values. The skill defaults are **stale from an earlier layout version** and should be
updated to match, or at minimum documented as historical artifacts.

---

#### I-3: `dispense_tem1` node reads `tem1_working_anchor` from `source_block`, not from `working_plate`

**Where:** `tem1_activity_screen.json` node `dispense_tem1` vs the actual TEM-1 prep location

The `prepare_tem1_dilution_plate` skill deposits the 0.1 ng/uL TEM-1 working solution into
`tem1_working_anchor` (default `hole_8`) on the **`blb_source` / cold block object**.

The `dispense_tem1` node then retrieves from `reagent_block` = `source_block` (the cold block) at
`mm_anchor` = `tem1_working_anchor` (`hole_8`). This is correct — both objects map to the same
physical cold block (`coldblock_wellplate`).

However, this means `blb_source` and `source_block` in the workflow inputs must always refer to
**the same physical object**. In the canvas (line 156) both are set to `sourceBlock`, so this is
consistent. But the workflow exposes them as two separate inputs with the same default — if an
operator were to set them differently, TEM-1 would be dispensed from a hole on a different object
than where it was prepared. There's no validation guard for this.

**Risk:** Low in practice (canvas enforces same object), but the workflow input design allows an
inconsistent configuration that would silently pipette from an empty or wrong tube.

---

#### I-4: Nitrocefin working solution volume — sufficient but no operator warning when overage is consumed

**Volumes verified correct:**
- Prepared: 1250 uL (6.25 + 1243.75)
- Needed: 36 wells × 25 uL = 900 uL
- Buffer: 350 uL (28%)

This is fine. However, the canvas deck table at line 145 shows `needed = allWells.length * nitrocefinVolume`
(= 900 uL) plus a configurable `nitrocefinOverage` (default 50). So the operator loads `950 uL`
minimum into the final working-solution hole — but **the skill actually prepares 1250 uL in that
very hole**. The deck table conflates the pre-prepared working solution with the amount to load for
dispensing. The `2x nitrocefin working` row in the deck table tells the operator to load 950 uL,
but the robot will pipette 1250 uL into `hole_10` during prep, so the operator must pre-load
at least 0 uL there (it's robot-prepared). This row is **misleading** — it implies the operator
should manually load it.

---

#### I-5: Nitrocefin addition order in workflow vs canvas description

**Canvas description (line 233):**  
> "Nitrocefin is added in a stagger-aware order: no-TEM-1 controls first, then clavulanate and
> inhibitor-class compounds, then substrate-control compounds, with the vehicle + TEM-1 max-activity
> wells last."

**Actual workflow edge order (lines 189–201):**
```
prepare_nitrocefin → nitro_negative → nitro_positive → nitro_compound_1..9 → nitro_vehicle
```

The vehicle wells are **last**, which matches "vehicle + TEM-1 max-activity wells last." But the
canvas says "clavulanate and inhibitor-class compounds" come before "substrate-control compounds"
— the actual order is positive control → compounds 1–9, which mixes inhibitors and substrates in
compound-number order (not by inhibitor type). The order of compounds 1–9 as dispensed is:
T1262 (true inhibitor), T6685, T14081, T1005 (amoxicillin, substrate), T1008 (cephalexin, substrate),
T0224 (meropenem), T0985 (oxacillin), T0138 (cefpiramide), T8390 (cefazolin).

The canvas description implies a pharmacology-aware staggering that isn't implemented — compounds
are dispensed in slot-number order. This is a documentation inconsistency; whether it matters for
the experiment depends on your kinetic read timing tolerance.

---

#### I-6: `tem1_well_count` = 33 hardcoded in workflow; computed as 33 in canvas — but both could drift

The `tem1_wells` list in the workflow has a `defaultValue` of a comma-separated string with 33
wells. `tem1_well_count` defaults to `33`. The canvas computes `tem1Wells.length` dynamically.
If the well-list constants (`POSITIVE_WELLS`, `VEHICLE_WELLS`, `COMPOUND_WELLS`) are ever changed
in the canvas but the workflow defaults are not updated, the `num_reactions` guard in
`batched_dispense_mastermix` could silently truncate the dispense without error. This is a
soft multiple-source-of-truth issue since the canvas always overrides the workflow defaults.

---

### 🟡 MEDIUM — Shared with cfps example (brief)

These exist in both projects; fixing ours first isn't necessary, but be aware:

- **Silent skip on empty wells:** `batched_dispense_mastermix` returns `{"success": True, "skipped": True}` when `num_reactions=0` or `wells=""`. Workflow nodes treat any return without raising as success — a silently skipped dispense doesn't fail the run.

- **`epipette_10ul` fallback in `PIPETTES`:** `pipette_limits()` falls back to `epipette_10ul` limits (0.5–10 uL) for any unrecognized pipette name. If a pipette is mis-named in the world, its limits silently become the 10 uL range, potentially causing over-aspiration.

- **`_tipbox_capacity` defaults to 96:** If a tip box has no calibration for a given pipette, it is assumed to have 96 tips. An empty calibration entry silently causes overrun.

---

## Summary Table

| # | Severity | Scope | Finding |
|---|---|---|---|
| I-1 | 🔴 HIGH | Ours only | `tazobactam_intermediate_anchor` not exposed; `hole_3` missing from canvas collision guard |
| I-2 | 🔴 HIGH | Ours only | Compound source-well defaults in skill are stale vs workflow/canvas (up to 8 mismatches) |
| I-3 | 🟡 MED | Ours only | `blb_source` and `source_block` silently required to be the same object; no guard |
| I-4 | 🟡 MED | Ours only | Deck-loading table misleads operator on the `2x nitrocefin working` row |
| I-5 | 🟡 MED | Ours only | Canvas documents a pharmacology-aware nitrocefin addition order that isn't implemented |
| I-6 | 🟡 MED | Ours only | `tem1_well_count` has two sources of truth (workflow default vs canvas computed) |
| — | 🟢 LOW | Both | Silent-skip on empty dispense, pipette-name fallback, tipbox capacity default |
