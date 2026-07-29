# TEM-1 Cold-Block Loading (v1)

Cold-block loading for the current `tem1_activity_screen` workflow defaults.

| Hole | UI Label | Total Volume | What To Put There |
|---|---|---:|---|
| `hole_1` | TEM-1 stock | Load at least `4 uL` | Purified TEM-1 stock, `100 ng/uL`. Robot uses `2 uL`; `4 uL` includes a small practical overage. |
| `hole_2` | TEM-1 intermediate | Starts empty; robot prepares `200 uL` | Empty tube/well. Robot makes `1 ng/uL` TEM-1 intermediate here, then transfers `100 uL` onward to `hole_8`. |
| `hole_3` | T1262 intermediate | Starts empty; robot prepares `50 uL` | Empty tube/well. Robot makes the T1262/tazobactam intermediate here for the `1 uM` final condition, then transfers `2.5 uL` to the working plate. |
| `hole_4` | Nitrocefin stock | Load at least `8.25 uL` | `20 mM` nitrocefin stock in DMSO. Robot uses `6.25 uL`; protect from light if practical. |
| `hole_5` | BLB tube 1 | Load at least `554 uL` | BLB buffer for compound/control working-solution dilutions and T1262 intermediate. Robot uses `524 uL`; listed volume includes `30 uL` overage. |
| `hole_6` | No-enzyme prep / BLB tube 2 | Load at least `1283 uL` | BLB buffer. Used for TEM-1 dilution, vehicle prep, and no-TEM-1 control wells. This is physically just BLB, not enzyme. |
| `hole_7` | Nitrocefin BLB | Load at least `1293.75 uL` | BLB buffer used only to dilute nitrocefin just-in-time. Robot uses `1243.75 uL`; listed volume includes `50 uL` overage. |
| `hole_8` | TEM-1 prep | Starts empty; robot prepares `1000 uL` | Empty tube/well at start. Robot prepares final `0.1 ng/uL` TEM-1 working solution here, then dispenses `660 uL` total to assay wells. |
| `hole_9` | DMSO | Load at least `10 uL` | `100% DMSO` for matched vehicle prep. Robot uses `5 uL`; listed volume includes a small practical overage. |
| `hole_10` | 2x nitrocefin | Starts empty; robot prepares `1250 uL` | Empty amber/light-protected tube/well if possible. Robot prepares `100 uM` 2x nitrocefin working solution here, then dispenses `900 uL` total to assay wells. |

## Non-Cold-Block Items

| Item | Location | Notes |
|---|---|---|
| Positive control clavulanic acid stock | `wellplate_pcr_parts_1`, well `H7` | Source for the positive-control working solution. |
| Test compound stocks | Source PCR plates/wells listed in the run setup table | The robot prepares each compound working solution before assay setup. |
| Working plate | `wellplate_pcr_parts_4` | Robot prepares positive control, vehicle, and compound working solutions in row `A`. |

## Notes

- `hole_6` is labeled no-enzyme prep in the UI because it supplies the no-TEM-1 control wells, but physically it should contain BLB buffer.
- `hole_8` and `hole_10` start empty; they are prepared by the robot during the workflow.
- Nitrocefin-containing materials should be protected from light where practical.
- “Load at least” volumes are starting deck volumes. “Robot prepares” volumes are final prepared volumes in holes that start empty.
- Increase starting deck volumes as needed for the tube geometry and pipetting dead volume.
