# TEM-1 Cold-Block Loading

Cold-block loading for the current `tem1_activity_screen` Round 3 v1 workflow defaults.

| Hole | UI Label | Total Volume | What To Put There |
|---|---|---:|---|
| `hole_1` | TEM-1 stock | Load at least `4 uL` | Purified TEM-1 stock, `100 ng/uL`. Robot uses `2 uL`; `4 uL` includes a small practical overage. |
| `hole_2` | TEM-1 intermediate | Starts empty; robot prepares `200 uL` | Empty tube/well. Robot makes `1 ng/uL` TEM-1 intermediate here, then transfers `100 uL` onward to `hole_8`. |
| `hole_3` | T1262 intermediate | Starts empty; robot prepares `50 uL` | Empty tube/well. Robot makes the T1262/tazobactam intermediate here for the `1 uM` final condition, then transfers `2.5 uL` to the working plate. |
| `hole_4` | Nitrocefin stock | Load at least `8.25 uL` | `20 mM` nitrocefin stock in DMSO. Robot uses `6.25 uL`; protect from light if practical. |
| `hole_5` | BLB tube 1 | Load at least `506.5 uL` | BLB buffer for compound/control working-solution dilutions and T1262 intermediate. Robot uses `476.5 uL`; listed volume includes `30 uL` overage. |
| `hole_6` | No-enzyme prep / BLB tube 2 | Load at least `1283 uL` | BLB buffer. Used for TEM-1 dilution, vehicle prep, and no-TEM-1 control wells. This is physically just BLB, not enzyme. |
| `hole_7` | Nitrocefin BLB | Load at least `1293.75 uL` | BLB buffer used only to dilute nitrocefin just-in-time. Robot uses `1243.75 uL`; listed volume includes `50 uL` overage. |
| `hole_8` | TEM-1 prep | Starts empty; robot prepares `1000 uL` | Empty tube/well at start. Robot prepares final `0.1 ng/uL` TEM-1 working solution here, then dispenses `540 uL` total to assay wells. |
| `hole_9` | DMSO | Load at least `10 uL` | `100% DMSO` for matched vehicle prep. Robot uses `5 uL`; listed volume includes a small practical overage. |
| `hole_10` | 2x nitrocefin | Starts empty; robot prepares `1250 uL` | Empty amber/light-protected tube/well if possible. Robot prepares `100 uM` 2x nitrocefin working solution here, then dispenses `750 uL` total to assay wells. |

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

## Storage SOP

Hold times below apply to the **TEM-1 activity screen**. Stock plates are library assets; everything the robot dilutes in BLB is **same-run consumable**, not long-term storage.

### Quick reference

| Material | Location | Prep | Max hold | Storage | Before use |
|---|---|---|---|---|---|
| Compound library stock | Source PCR plates | Supplier / cherry-pick | Weeks–months | −20 °C, sealed, minimize freeze-thaw | Thaw RT, vortex, inspect for precipitate |
| Clavulanic acid stock | `wellplate_pcr_parts_1` H7 | 10 mM in DMSO | Same as library stock | −20 °C, sealed | Same as library stock |
| TEM-1 stock | `hole_1` | 100 ng/µL | Same run only | 4 °C on deck during run; aliquot source at −20 °C | Fresh thaw preferred if Q2 enzyme check failed |
| Nitrocefin stock | `hole_4` | 20 mM in DMSO | 2 weeks–2 months (supplier) | −20 °C, **light-protected** | Warm RT, vortex; discard if red before enzyme add |
| BLB | `hole_5`, `hole_6`, `hole_7` | Ready-to-use buffer | Same run | 4 °C until loaded | Check pH ~7; use fresh aliquot if contaminated |
| DMSO | `hole_9` | 100% | Same run | RT sealed; long-term stock −20 °C | Match vehicle DMSO % to compound wells |
| TEM-1 intermediate | `hole_2` | Robot, Phase 0 | **Same run only** | Do not store | Use immediately after prep |
| T1262 intermediate | `hole_3` | Robot, Phase 0 | **Same run only** | Do not store | Use immediately after prep |
| TEM-1 working | `hole_8` | Robot, Phase 0 | **Same run only** | Do not store | Diluted enzyme is unstable; use promptly |
| Compound/control working plate | `wellplate_pcr_parts_4` row A | Robot, Phase 0 | **Same day** (prefer same run) | 4 °C foil-sealed if held briefly | Mix well; reject if cloudy or precipitated |
| Vehicle working | `wellplate_pcr_parts_4` A2 | Robot, Phase 0 | **Same day** | Same as working plate | Must match compound-well DMSO fraction |
| Nitrocefin working | `hole_10` | Robot, Phase IV (JIT) | **Minutes** | Do not store | Prepare after pre-incubation; dose immediately |

### Stock plates (library + controls)

- **10 mM DMSO stocks** are the durable layer. Keep dry, sealed, and cold.
- Limit **freeze-thaw cycles**; water uptake into DMSO drives precipitation and concentration drift.
- **Pass:** clear solution after vortex. **Fail:** cloudiness, particulates, or color shift → do not use for working prep; re-aliquot or re-order.
- Do **not** pipette 10 mM stock directly into assay wells; Phase 0 working plate is required.

### Robot-prepared working solutions (Phase 0)

- Compound/control wells: **2.5 µL stock + 47.5 µL BLB → 500 µM** (50 µM final after 5 µL into 50 µL assay).
- T1262 uses a **200 µM intermediate** in `hole_3` because 1 µM final needs a serial step below reliable single-pipette precision.
- Aqueous working solutions are **less stable than DMSO stocks**. Hydrolysis, evaporation, and precipitation are all possible.
- **Default:** finish the assay run the same day the working plate is built.
- **If held briefly:** foil-seal at 4 °C, ≤24 h absolute max, compounds only (not nitrocefin or diluted enzyme).
- **Pass:** uniform meniscus, no precipitate, vehicle DMSO matched. **Fail:** any well cloudy → exclude that compound from analysis and re-prep.

### Just-in-time reagents (Phase IV)

- **Nitrocefin working** (`hole_10`) is prepared **after** the 10 min pre-incubation, not in Phase 0.
- Nitrocefin autohydrolyzes in aqueous buffer and is light-sensitive. Yellow = intact; red before β-lactamase add = degraded stock or working solution.
- **Rule:** once `hole_10` is filled, proceed to assay dosing without delay.

### Run-day checklist

1. Thaw and inspect **library stock plates** and **TEM-1 / nitrocefin stocks** before deck load.
2. Load cold block per table above; keep **nitrocefin stock light-protected**.
3. Run Phase 0 → confirm working plate row A is clear and mixed.
4. Complete enzyme + compound setup and **10 min pre-incubation** before nitrocefin prep.
5. Prepare nitrocefin working → dose all wells → start plate reader immediately.
6. Do **not** return working plate, `hole_8`, or `hole_10` contents to −20 °C for reuse.
