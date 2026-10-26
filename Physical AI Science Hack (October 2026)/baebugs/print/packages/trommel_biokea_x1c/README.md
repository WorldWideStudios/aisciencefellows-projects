# baebugs trommel for BioKEA trays: one plate, one print run (Bambu Lab X1 Carbon)

**Print this:** `trommel_plate_x1c.3mf` (8 separate objects already laid out on the 256 x 256 mm plate) or
`trommel_plate_x1c.stl` (same layout as one file; in Bambu Studio use *Split to objects*). Plate used: 246.0 x 234.0 mm, tallest part 125.6 mm.
Individual parts are in `stl/`. Concept geometry: not tested on specimens; printed holes are not calibrated apertures.

## Sized to the BioKEA trays
Tray sizes measured from the BioKEA BugPicker designs: `tray` 103 x 140 x 12.5 mm, `screentray` 113.6 x 149.7 x 10 mm.
- Three trays sit side by side under the drum, short side along the rod. Each drum zone is **119.6 mm** long, so each zone sits over exactly one tray (6 mm gap between trays).
- Only a centred **85.0 mm** band of each zone is perforated, so fines land inside even the narrower 103 mm tray.
- Drum diameter **76 mm** (smaller than the first version so everything fits one X1C plate). Rod axis at **62.5 mm**, drum bottom **24.5 mm** above the bench: trays (12.5 mm) slide underneath with ~12 mm to spare.
- Zones, fine to coarse from the inlet: 2 mm, 4 mm, 7 mm. 3 degree slope from the taller inlet stand. Oversize leaves through the outlet cap.

| Part | Size (mm) |
|---|---|
| `trommel_zone_2mm.stl` | 76.0 x 76.0 x 125.6 |
| `trommel_zone_4mm.stl` | 76.0 x 76.0 x 125.6 |
| `trommel_zone_7mm.stl` | 76.0 x 76.0 x 125.6 |
| `trommel_cap_inlet.stl` | 80.0 x 80.0 x 22.0 |
| `trommel_cap_outlet.stl` | 80.0 x 80.0 x 22.0 |
| `trommel_stand_inlet.stl` | 90.0 x 60.0 x 99.4 |
| `trommel_stand_outlet.stl` | 90.0 x 60.0 x 79.5 |
| `trommel_crank_hand.stl` | 22.0 x 78.0 x 47.0 |

## Hardware (not printed)
- 8 mm steel rod, ~471 mm
- 2 x 608 bearings (22 mm OD), pressed into the stands
- 4 x M3 x 8 set screws (caps and crank), 4 x M3 screws if you bolt the stands down

## Print (X1 Carbon)
- PETG or PLA, 0.4 mm nozzle, 0.2 mm layers, 3 walls, 15-20% infill. No supports needed for 2 and 4 mm holes; 7 mm holes bridge.
- Check the 608 pocket and the 8 mm rod hole fits on the stands before relying on them.

Package Merkle root `d230b0c03130e9086a26ba68005e2ed722966e4dc28c95b122381cf804daea84` (per-file sha256 in `manifest.json`). Regenerate: `python -m baebugs.trommel_plate --printer x1c`.
Licence: MIT, https://github.com/biobitworks/baebugs
