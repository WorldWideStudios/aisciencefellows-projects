# Kinetic Plate-Reader Handoff

## Summary

We are building Zeon workflows in `mastermix` for a TEM-1 nitrocefin inhibition assay.

The current problem is that `pvjthomas/output/kinetic_schedule_r2_v5.json` describes a true kinetic A490 read schedule, but the current plate-reader automation cannot faithfully execute it by repeatedly calling `platereader_measure()`.

The requested schedule is:

- Temperature: `25 C`
- Equilibration after plate close: `120 s`
- Kinetic duration: `600 s`
- Read interval: `30 s`
- Read points: `21` total, initial plus every `30 s` through `600 s`
- Slope window: `180-480 s` kinetic time

The current `platereader_measure()` skill triggers one full Gen5 GUI read/export cycle via AutoGUI. That cycle includes GUI waits and PDF export steps, so it is too slow to run once every `30 s`. Repeating `platereader_measure()` for each timepoint will distort the kinetics.

## Core Conclusion

To implement `kinetic_schedule_r2_v5.json` correctly, Gen5 must run one saved kinetic method internally.

The robot workflow should trigger that one saved Gen5 kinetic protocol once, wait for it to complete, and export/download the resulting kinetic data once.

Do not emulate kinetic acquisition by looping `platereader_measure()` every `30 s`.

## Current State

- `tem1_activity_screen` currently references `platereader_run_kinetic_schedule`.
- `platereader_run_kinetic_schedule` builds/saves schedule metadata from `read_schedule.py`.
- `platereader_measure(read_label=...)` triggers one Gen5 read/export via AutoGUI and saves a PDF.
- Nitrocefin per-well timing is recorded by `batched_dispense_mastermix` into:
  - `data/timing/<execution_id>/nitrocefin_timing.json`
  - copied into final run folders by `save_run_folder`
- The R2 v5 activity screen layout has been applied.
- The activity workflow performs reagent dilution prep up front.
- Nitrocefin is prepared just-in-time before assay initiation.

## Relevant Files

- `pvjthomas/output/kinetic_schedule_r2_v5.json`
- `mastermix/workflows/tem1_activity_screen.json`
- `mastermix/skills/platereader_run_kinetic_schedule/robotic_code.py`
- `mastermix/skills/read_schedule.py`
- `mastermix/skills/platereader_measure/robotic_code.py`
- `mastermix/skills/batched_dispense_mastermix/robotic_code.py`
- `mastermix/skills/save_run_folder/robotic_code.py`

## Required Gen5 Setup

Create or verify a saved Gen5 method on the plate-reader PC for the TEM-1 nitrocefin kinetic assay.

Required method settings:

- Absorbance read at `490 nm`
- Incubation enabled at `25 C`
- Equilibration or delay of `120 s` after lid close / plate load
- Kinetic read mode, not endpoint-only
- `21` reads total:
  - first read at kinetic `t=0`
  - then every `30 s`
  - final read at kinetic `t=600 s`
- Export raw kinetic data, preferably CSV or XLSX, not only PDF

## Required AutoGUI Setup

Confirm or create AutoGUI press actions for the plate-reader PC.

Needed actions:

- Start the saved TEM-1 A490 kinetic method.
- Confirm/run the method.
- Export the kinetic data file.
- Save/download the exported file from the known Windows directory.

Example action names are placeholders only:

- `Experiment_TEM1_Kinetic_A490`
- `Experiment_ReadPlate`
- `Experiment_ExportKineticCSV`

The actual action names must match the AutoGUI server on the Windows plate-reader machine.

## Implementation To Do

1. Confirm the saved Gen5 kinetic method exists.

2. Confirm the AutoGUI press-action names for:
   - opening/choosing the kinetic method
   - starting the read
   - exporting raw kinetic data
   - saving the output file

3. Replace the repeated-read behavior.

   Modify or replace `platereader_run_kinetic_schedule` so it:

   - Saves schedule metadata JSON.
   - Triggers the saved Gen5 kinetic method once.
   - Waits for the kinetic method to complete.
   - Downloads the resulting kinetic file once.
   - Returns the file path in the skill result.

4. Keep nitrocefin timing metadata.

   Preserve the existing per-well `t0` timing from `batched_dispense_mastermix`:

   - `condition`
   - `well`
   - `t0_utc`
   - `source_anchor`
   - `volume_ul`

5. Make sure final run output includes:

   - `nitrocefin_timing.json`
   - kinetic schedule JSON
   - plate-reader kinetic export file
   - run inputs
   - run log

6. Update `tem1_activity_screen` only if needed.

   The workflow should call a single kinetic reader skill after:

   - nitrocefin additions
   - pipette placement
   - plate loading
   - reader close

7. Validate before syncing.

   Suggested checks:

   ```bash
   python3 -m py_compile mastermix/skills/platereader_run_kinetic_schedule/robotic_code.py
   python3 -m json.tool mastermix/workflows/tem1_activity_screen.json >/dev/null
   zeon status
   ```

   Also run a workflow-reference check for:

   - missing skills
   - missing inputs
   - bad edges
   - unreachable nodes

## Open Question

Is the Gen5 kinetic method already created on the plate-reader PC?

If yes, what are the exact AutoGUI press-action names to start it and export the kinetic data?
