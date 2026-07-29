# TEM-1 mastermix end-to-end audit

Date: 2026-07-26

Scope: `beta-loop-main/mastermix`, compared byte-for-byte and semantically
against `hackathon-track-1-cfps-main`.

No deletion or implementation change was made as part of this audit.

## Scope boundary

The cleanup boundary is narrower than "everything TEM-1 cannot reach":

- Files copied unchanged from CFPS are not cleanup candidates.
- Only code, workflows, canvases, and modifications added in `mastermix` are
  considered for cleanup.
- For a modified CFPS file, cleanup means reverting the custom delta, not
  deleting the original file.
- `.zeon/` is Zeon version-control metadata and is out of scope.
- `objects copy/` and generated PDFs are noted separately because they are not
  scripts or functions.

The audit followed imports transitively, including the dynamic
`epipette_attach` import in `skills/utils.py`.

---

# 1. Cleanup: mastermix-only code not reachable from TEM-1

## 1.1 Safe code deletion candidates

These paths are additions in `mastermix`, do not exist in CFPS, and cannot be
reached from `workflows/tem1_activity_screen.json`, its canvas, or any imported
skill.

### Plate-reader experiment stack

- `skills/platereader_parse_pdf/`
- `skills/platereader_run_kinetic_schedule/`
- `skills/gen5_pdf.py`
- `skills/read_schedule.py`
- `skills/test_gen5_pdf.py`
- `workflows/platereader_kinetic_test.json`
- `workflows/test_platereader_kinetic_schedule.json`
- `canvas/platereader_kinetic_test_screen.tsx`

This group is isolated from TEM-1. Its only workflow callers are the two
plate-reader workflows above.

There is also affirmative evidence that it is stale:

- `platereader_kinetic_test.json` passes `export_extension` to
  `platereader_run_kinetic_schedule`, but the Python function has no such
  parameter. Zeon derives parameters from the function signature, so this
  workflow is invalid.
- The workflow says it triggers one Gen5 kinetic method, while the skill calls
  `platereader_measure` separately at every time point.
- Nominal time points omit the duration of each preceding read/export. Waiting
  starts after each read finishes, so actual times drift later than the
  recorded `kinetic_time_s`.
- Incubator temperature is recorded but not programmed.
- `platereader_parse_pdf` is not called by either custom plate-reader workflow.

### Standalone TEM dilution test surface

- `workflows/tem1_dilution_plate.json`
- `canvas/tem1_dilution_plate.tsx`

The activity workflow calls `prepare_tem1_dilution_plate` directly; workflows
cannot call other workflows. Deleting this standalone test surface does not
remove the dilution skill used by the activity screen.

## 1.2 Revert candidate, not deletion candidate

- `skills/platereader_measure/robotic_code.py`

This is a CFPS file modified in `mastermix` for labeled exports and a changed
AutoGUI sequence. TEM-1 does not call it. Cleanup should replace it with the
CFPS version rather than delete the skill.

## 1.3 Mastermix additions that TEM-1 needs

Do not delete:

- `workflows/tem1_activity_screen.json`
- `canvas/tem1_activity_screen.tsx`
- `skills/batched_dispense_mastermix/`
- `skills/prepare_tem1_dilution_plate/`
- `skills/prepare_nitrocefin_working_solution/`
- `skills/wait_minutes/`
- `TEM1_COLD_BLOCK_LOADING.md`

These CFPS files contain mastermix changes required by the current design:

- `skills/save_run_folder/robotic_code.py`
  - copies nitrocefin timing JSON into the final run folder.
- `skills/wellplate_shaker_run/robotic_code.py`
  - attempts a second press to stop the shaker.
  - it needs correction, but reverting it would leave TEM-1 mixing running.
- `project.json`
  - selects `tem1_activity_screen` and `hack_world_22`.

## 1.4 Explicit exclusions

Original CFPS skill directories remain out of cleanup scope even if TEM-1 does
not call them. That includes all `cfps_*`, plate-sealer, plate-reader, unseal,
and CFPS test skills that are unchanged from the example.

Non-code additions for separate review:

- `objects copy/` is byte-identical to `objects/`, but it is outside the
  requested scripts/functions cleanup.
- The two `data/platereader/...pdf` files support the unused PDF parser tests,
  but are test data rather than code.

---

# 2. What mastermix added or changed relative to CFPS

## 2.1 Exact implementation delta

Ignoring `.zeon/`, caches, duplicated objects, and generated PDFs:

| Change | TEM-1 reachable? | Purpose |
|---|---:|---|
| `tem1_activity_screen.json` | Yes | Full 46-node assay workflow |
| `tem1_activity_screen.tsx` | Yes | Setup, plate map, and load calculations |
| `prepare_tem1_dilution_plate` | Yes | Enzyme, compound, control, and vehicle prep |
| `batched_dispense_mastermix` | Yes | Multi-well dispense from one aspiration |
| `prepare_nitrocefin_working_solution` | Yes | Just-in-time 100 µM nitrocefin |
| `wait_minutes` | Yes | Mixing and pre-incubation timers |
| Modified `save_run_folder` | Yes | Preserve nitrocefin timing JSON |
| Modified `wellplate_shaker_run` | Yes | Attempt start/stop toggling |
| `TEM1_COLD_BLOCK_LOADING.md` | Operationally related | Deck instructions |
| TEM dilution standalone workflow/canvas | No | Dilution test surface |
| Plate-reader parser/scheduler stack | No | Abandoned readout experiment |
| Modified `platereader_measure` | No | Labeled repeated PDF exports |

All generic pipetting, gripping, plate-motion, object-model, and live-state
files are otherwise byte-identical to CFPS.

The active `world_state.json` and `live_state.yaml` are also byte-identical.
The significant world difference is that `mastermix` omits two sidecars present
in CFPS:

- `worlds/hack_world_22/blox_tsdf.npz`
- `worlds/hack_world_22/blox_voxels.npz`

## 2.2 TEM-1 execution path

The workflow executes:

1. prepare TEM-1, T1262, compound/control, and vehicle solutions
2. redundantly grab the pipette
3. dispense enzyme/no-enzyme preparations
4. dispense vehicle, control, and compounds 1–9
5. return the pipette
6. move the plate into the shaker
7. start, wait, and stop the shaker
8. return the plate home
9. re-grab a pipette
10. pre-incubate
11. prepare nitrocefin
12. add nitrocefin condition-by-condition
13. return the pipette and save the run

### Custom call graph

```text
tem1_activity_screen
├── prepare_tem1_dilution_plate                 [added]
│   ├── batched_dispense_mastermix              [added]
│   └── CFPS aspirate/dispense/eject + utils
├── batched_dispense_mastermix                  [added]
│   └── CFPS aspirate/dispense/eject + utils
├── wait_minutes                                [added]
├── prepare_nitrocefin_working_solution         [added]
│   └── CFPS aspirate/dispense/eject + utils
├── wellplate_shaker_run                        [modified]
├── save_run_folder                             [modified]
└── original CFPS motion skills
```

`epipette_attach` is dynamically reached through `utils.attach_next_tip`, so
that original CFPS skill remains required.

## 2.3 TEM-specific behavior

### `prepare_tem1_dilution_plate`

It prepares:

- TEM-1: 100 ng/µL stock → 1 ng/µL intermediate → 0.1 ng/µL working.
- T1262: 10 mM stock → 200 µM intermediate → 10 µM working well.
- Positive control and compounds 2–9: nominal 10 mM stock → 500 µM working.
- Vehicle: 5% DMSO working solution.

It composes the CFPS atomic pipetting functions in Python rather than exposing
each transfer as a workflow node.

### `batched_dispense_mastermix`

This is the major behavioral departure from CFPS:

- CFPS uses one fresh tip and aspiration per destination well.
- The new function aspirates for several wells and sequentially dispenses into
  them using one tip.
- It chooses the 10 µL pipette below 10 µL per well and the 120 µL pipette at
  10 µL or above.
- With `timing_label`, it records a timestamp after each destination dispense.

### `prepare_nitrocefin_working_solution`

It makes 1,250 µL of 100 µM nitrocefin from 6.25 µL of 20 mM stock plus
1,243.75 µL BLB, then mixes 100 µL for five cycles.

### `wait_minutes`

It validates non-negative time and uses pause-aware sleep. Simulation shortens
the wait to at most two seconds.

### Modified `wellplate_shaker_run`

CFPS ignores `ensure_state="off"` and intentionally leaves the shaker running.
The mastermix version presses for both `"on"` and `"off"` calls. It does not
verify the physical shaker state.

### Modified `save_run_folder`

It retains CFPS behavior, then copies JSON from
`data/timing/<execution_id>/` into the final run folder's `timing/` directory.

## 2.4 Static and mathematical validation

Passed:

- Every Python file parses.
- Every workflow/world JSON parses.
- `tem1_activity_screen` has no unknown skill parameters.
- Every required parameter and `$input` is bound.
- Every declared TEM-1 input is used.
- The graph is connected from one start to one end.
- All 36 assay wells are unique across conditions.
- `tem1_wells` equals positive + vehicle + all compounds: 33 wells.
- `vehicle_addition_wells` equals negative + vehicle: 6 wells.
- Current count inputs match their CSV lists.

Current concentration math:

| Material | Preparation | Final assay value |
|---|---|---|
| TEM-1 | 2 µL × 100 ng/µL into 200 µL; 100 µL into 1,000 µL | 0.1 ng/µL working; 2 ng/well |
| T1262 | 1 µL × 10 mM into 50 µL; 2.5 µL into 50 µL | 10 µM working; 1 µM final |
| Other compounds/control | 2.5 µL × 10 mM into 50 µL | 500 µM working; 50 µM final |
| Vehicle | 5 µL DMSO into 100 µL | 5% working; 0.5% final |
| Nitrocefin | 6.25 µL × 20 mM into 1,250 µL | 100 µM working; 50 µM final |

Source consumption agrees with the canvas:

- BLB tube 1: 524 µL before overage.
- BLB tube 2: 1,253 µL before overage.
- Nitrocefin BLB: 1,243.75 µL.
- TEM-1 working produced/consumed: 1,000/660 µL.
- Nitrocefin working produced/consumed: 1,250/900 µL.

Estimated current tip use with both pipettes available:

- 48 × 10 µL tips
- 52 × 120 µL tips
- 100 tips total

---

# 3. Logical inconsistencies and reliability findings

Mastermix-specific findings come first. Shared CFPS issues are briefly listed
at the end.

## 3.1 Mastermix-specific findings

### Critical: dilution prep is followed by a second physical grab

`prepare_tem1_dilution_plate` uses `ensure_pipette` and leaves a pipette in the
gripper. The next node calls `epipette_grab` unconditionally.

Consequences:

- It can pick an object already attached to the arm.
- It overwrites shared grab-home waypoints used by later placement.
- The dilution step accepts possibly stale `live_state.in_hand` as physical
  truth.

CFPS instead grabs before liquid handling.

Recommended fix:

- Put one explicit grab before `prepare_dilutions`.
- Remove the grab immediately after dilution prep.
- Verify/initialize `in_hand` at workflow start.

### Critical: hidden, collision-prone T1262 parameters

Only the Python signature defines:

- `tazobactam_intermediate_anchor="hole_3"`
- `tazobactam_stock_volume_ul=1.0`
- `tazobactam_intermediate_blb_volume_ul=49.0`

They are absent from the workflow and canvas. The canvas's hole uniqueness
check also omits fixed `hole_3`, so another reagent may be assigned there.

Recommended fix: expose all three as workflow inputs, seed them through the
canvas, and include `hole_3` in collision validation.

### High: the canvas is a second executable protocol definition

It hardcodes and submits the well map, working plate, destination wells,
volumes, fixed anchors, counts, and compound defaults. Changing workflow
defaults alone does not change a canvas-confirmed run.

Examples:

- Changing workflow `enzyme_volume_ul` has no effect: the canvas submits 20.
- Changing `compound_1_dest_well` has no effect: the canvas submits `A3`.
- Changing workflow well lists has no effect: the canvas recreates its own.

Recommended design:

1. Put protocol constants in one structured workflow input/preset.
2. Make the canvas visualize that structure.
3. Derive counts/unions; do not accept them independently.
4. Keep skill defaults generic rather than embedding another plate map.

### High: eight skill source defaults disagree with the workflow

| Parameter | Skill | Workflow |
|---|---|---|
| compound 1 | G6 | B10 |
| compound 3 | B10 | F7 |
| compound 4 | F7 | A8 |
| compound 5 | A10 | A9 |
| compound 6 | B10 | A3 |
| compound 7 | B4 | A4 |
| compound 8 | H8 | A2 |
| compound 9 | A3 | F3 |

The main workflow overrides them, but direct skill execution or a future
partial binding silently draws from different wells.

Recommended fix: require source wells explicitly or make one preset
authoritative.

### High: well lists and counts can silently diverge

Examples include `tem1_wells`/`tem1_well_count`, every compound list/shared
`replicate_count`, and `vehicle_addition_wells`/its count.

`batched_dispense_mastermix` truncates the list when the count is smaller and
only warns/partially fills when the count is larger.

Recommended fix: derive the count from the parsed list and raise on any
explicit mismatch.

### High: batching contradicts its comments and canvas

The canvas says five enzyme wells per 100 µL aspiration. The code computes:

```python
wells_per_batch = floor(120 / 20) = 6
```

Its own comment mentions 100 µL/five wells while using the 120 µL limit.

It also uses exact-capacity 120, 100, and 10 µL batches with no liquid
headroom. Retained liquid or pipette inaccuracy can under-deliver later wells.

Recommended fix: define one usable capacity/disposal volume, derive batch size
from it, and render the same value in the canvas.

### High: shaker `"on"` and `"off"` are not enforced states

The code presses once for either request, with no running sensor or trusted
logical state:

- If already on, `"on"` turns it off.
- If the first press fails, `"off"` may start it.
- Retrying a node reverses the intended state.
- The `shaker` object parameter is unused.

The metadata's state-aware description does not match the code.

Recommended fix: use explicit state seeding/operator confirmation and
idempotent command tracking. If state cannot be known, call the operation
`toggle` rather than `ensure_state`.

### High: nitrocefin order contradicts the canvas

The canvas claims inhibitor-class compounds precede substrate controls. The
graph is simply:

```text
negative → positive → compound_1 → ... → compound_9 → vehicle
```

Compounds 4 and 5 are substrate controls but occur before compounds 6–9.

Recommended fix: reorder the graph to the scientific grouping or remove the
claim and analyze strictly per-well timing.

### High: pre-incubation differs by condition

Vehicle, positive control, and compounds 1–9 are added sequentially. Only after
all dispensing, pipette return, plate motion, and shaker mixing does the
nominal ten-minute timer begin. Early conditions therefore incubate longer
than later conditions, and that stagger is not logged.

Recommended fix: record per-condition addition completion and compensate, or
define the common plate-mix event as the justified incubation start.

### Medium: nitrocefin t0 has conflicting definitions

The canvas says condition/batch completion is t0. The code records one
timestamp per well after the atomic dispense routine returns. That is later
than reagent contact because post-dispense motion and sleeps occur first.

Recommended fix: choose plunger actuation, per-well completion, or batch
completion as t0 and implement the same definition in code, UI, and analysis.

### Medium: canvas object options violate fixed anchor requirements

The canvas offers `wellplate_holder_fixture_plate` and `plate_stand_holder` as
plate homes, but the workflow always requests anchor `home`. Those object
models define no `home`.

It also advertises `coldblock_large`, which has only holes 1–4 while the
protocol uses holes through 10.

Recommended fix: restrict choices to compatible object types or validate the
required anchors for the chosen type.

### Medium: object selectors may submit `displayName`

`objName` prefers `displayName` and uses it as the option value. Zeon's canvas
docs specify object `name` or UUID for submission.

Recommended fix: use UUID as value and `displayName || name` only as label.

### Medium: separate source inputs are forcibly collapsed

The workflow separately declares `source_block`, `blb_source`, `dmso_source`,
and `tem1_stock_source`; the canvas submits the same selected object for all.

Recommended fix: expose separate selectors or replace them with one explicit
cold-block input.

### Medium: greedy chunking can create a below-minimum remainder

For a hypothetical 121 µL transfer, custom `_transfer_chunked` produces
120 + 1 µL on the 120 µL pipette, below its 10 µL minimum. Current defaults do
not trigger it. CFPS's equal-chunk approach avoids this.

Recommended fix: reuse equal valid chunks and validate each stroke.

### Low: metadata overstates compound count

The dilution metadata says ten compound solutions plus one known-active
control. The implementation prepares nine test compounds plus one control:
ten compound/control wells total.

## 3.2 Unreachable plate-reader inconsistencies

These do not affect TEM-1 and reinforce deletion:

- Invalid `export_extension` workflow parameter.
- "One kinetic method" documentation versus repeated endpoint calls.
- Read timing ignores each read/export duration.
- Incubator value is recorded but not controlled.
- PDF parser is not called by the plate-reader workflows.

## 3.3 Mastermix world difference

The world retains:

```json
"enable_blox": true,
"map_saved": true,
"tsdf_saved": true
```

but omits the Blox files present in CFPS. Zeon's
[world-state documentation](https://readme.zeonsystems.app/docs/worlds-world-state-json)
says these sidecars are loaded when Blox is enabled.

Recommended fix: restore the CFPS sidecars if this remains the same world, or
rebuild/export the world and update its flags.

## 3.4 Brief inherited CFPS issues

These are not mastermix cleanup candidates, but custom TEM skills call them:

1. Both worlds reference missing local `tipbox_10ul` and `tipbox_120ul` object
   models.
2. Shared aspirate, dispense, and eject wrappers ignore a low-level
   `{"success": false}` and return success.
3. Shared pipette hardware calls lack `is_sim_mode()` guards, contrary to
   current Zeon [pipetting guidance](https://readme.zeonsystems.app/docs/pipetting).
4. Shared `epipette_attach` uses absolute world Z and a hardcoded temporary
   orientation rather than an anchor-derived pose.

Handle these in a separate upstream/reference-hardening pass.

---

# Recommended order of work

1. Approve and perform section 1's custom-only cleanup.
2. Restore/rebuild the missing Blox sidecars.
3. Fix initial pipette acquisition and remove the redundant grab.
4. Make T1262 intermediate parameters explicit and collision-validated.
5. Consolidate configuration into one source of truth.
6. Remove redundant counts and require exact well-list validation.
7. Make shaker control idempotent or operator-confirmed.
8. Define one nitrocefin t0 convention.
9. Correct or record pre-incubation stagger.
10. Fix batch capacity/headroom and canvas documentation.
11. Address inherited CFPS hardware-return/simulation issues separately.

## Official Zeon references

- [Skills and signature-derived parameters](https://readme.zeonsystems.app/docs/skills)
- [Workflow JSON and input binding](https://readme.zeonsystems.app/docs/workflows-json)
- [Creating a canvas](https://readme.zeonsystems.app/docs/creating-a-canvas)
- [Pipetting runtime behavior](https://readme.zeonsystems.app/docs/pipetting)
- [World state and sidecars](https://readme.zeonsystems.app/docs/worlds-world-state-json)
- [Skill state and artifacts](https://readme.zeonsystems.app/docs/skill-state-and-logging)
