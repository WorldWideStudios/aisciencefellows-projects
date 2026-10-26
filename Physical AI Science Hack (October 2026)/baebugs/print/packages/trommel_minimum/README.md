# baebugs trommel: minimum print package (no bins)

A hand-cranked rotary sieve: 110 mm drum in three swappable 70 mm zones (2, 4, 7 mm holes), 3 degree incline.
Fines fall through each zone onto whatever sits underneath; designed to drop into **BioKEA trays** (bins left out).
Concept geometry, not tested on specimens. Printed holes are not calibrated apertures: measure them.

| File | Qty | Size (mm) | Volume (cm3) | Watertight |
|---|---|---|---|---|
| `trommel_cap_inlet.stl` | 1 | 114.0 x 114.0 x 22.0 | 31.9 | yes |
| `trommel_cap_outlet.stl` | 1 | 114.0 x 114.0 x 22.0 | 36.2 | yes |
| `trommel_crank_hand.stl` | 1 | 78.0 x 22.0 x 47.0 | 15.7 | yes |
| `trommel_stand_inlet.stl` | 1 | 90.0 x 60.0 x 134.1 | 66.5 | yes |
| `trommel_stand_outlet.stl` | 1 | 90.0 x 60.0 x 122.0 | 63.3 | yes |
| `trommel_zone_2mm.stl` | 1 | 110.0 x 110.0 x 76.0 | 48.7 | yes |
| `trommel_zone_4mm.stl` | 1 | 110.0 x 110.0 x 76.0 | 42.1 | yes |
| `trommel_zone_7mm.stl` | 1 | 110.0 x 110.0 x 76.0 | 35.7 | yes |

Package Merkle root: `e4f896a0906736f230727ba5a1af503b028dccb792c661b8c496749da264e081` (per-file sha256 in `manifest.json`; regenerate with `python -m baebugs.print_parts`).

## Hardware (not printed)
- 8 mm steel rod, ~320 mm
- 2 x 608 bearings (22 mm OD) pressed into the stands
- 4 x M3 x 8 set screws (caps and crank to the rod)

## Print
- PLA or PETG (FDM), or PA12 on a Fuse 1+. 3-4 walls, 20-30% infill.
- Print zones upright (holes radial): no supports for 2 and 4 mm; 7 mm holes may need bridging.
- Stands upright, bearing pocket up. Check the 608 press fit and the 8 mm rod fit on a test print first.

## Assembly
1. Press bearings into both stands; set the taller stand at the inlet end (gives the 3 degree slope).
2. Slide caps and zones onto the rod: inlet cap, 2 mm, 4 mm, 7 mm, outlet cap (fine to coarse). Zones key together with spigots.
3. Rod through both bearings, crank on the inlet end, lock with set screws.
4. Feed between the inlet cap spokes; turn slowly. Oversize leaves through the outlet cap.

## Fitting BioKEA trays (check before printing)
- Drum axis is 105 mm above the bench, so the drum bottom is ~50 mm up: tray + handle must be under ~45 mm tall to slide beneath.
- Each zone drops onto a 70 mm strip along the axis. With 120 x 90 mm trays (our unmeasured estimate) three trays side by side
  span 270 mm vs 210 mm of zones, so drops will not centre on each tray. For one zone per tray, regenerate with zone length ~95 mm
  (rod ~400 mm). Send measured tray length / width / height and the files will be regenerated to match.

Licence: MIT (biobitworks/baebugs). https://github.com/biobitworks/baebugs
