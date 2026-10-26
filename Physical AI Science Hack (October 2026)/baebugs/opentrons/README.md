# BioKEA line on an Opentrons Flex (lab in a box, deck edition)

| BioKEA module | Flex translation | Part / labware |
|---|---|---|
| 1 BugSorter | mini trommel on deck (external motor) + sieve stack on Heater-Shaker | `ot_mini_trommel_base` + `_drum` / `baebugs_mini_trommel_4bin`; `ot_sieve_adapter` / `baebugs_sieve_adapter_50mm` (uses the vortex-kit mini sieve rings) |
| 2 BugDisperser | Heater-Shaker D1, gentle shake on the flat adapter | `baebugs_sieve_adapter_50mm` |
| 3 BugPicker | external arm or suction picker via a hand-off carrier | `ot_handoff_plate` / `baebugs_handoff_plate` (grip handle, 20 mm suction pad, tag pocket) |
| 4 Enzyme dispenser | Flex 1-channel 1000 uL pipette | stock tips + reservoir |
| 5 Turnstile incubator | Heater-Shaker D3 at 56 C, 300 rpm | stock deep-well plate + adapter |

`protocols/baebugs_flex_line.py` passes `opentrons_simulate -L opentrons/labware` (output in
`protocols/baebugs_flex_line.sim.txt`). Not run on hardware. Before a real run: check gripper grip height
on the printed parts, skirt fit in the deck slot and on the Heater-Shaker flat adapter (4 mm stacking offset
declared), and latch clearance. Print in PLA/PETG for fit, PA12 powder or post-cured tough resin for wet use.
