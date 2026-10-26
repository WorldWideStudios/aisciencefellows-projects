# Trommel for BioKEA trays, split after FDM attempt 1

FDM attempt 1 (photo `assets/photos/fdm_trommel_attempt1.jpg`): the caps, crank and stand feet printed; the perforated drum
zones did not (loose loops / spaghetti, heavy stringing). Thin tall walls full of radial holes are hard on FDM.

So the same geometry (same tray fit, same rod) is split by printer:

| Folder | Printer | What | Fits |
|---|---|---|---|
| `fuse1_zones/` | Formlabs Fuse 1+ (PA12) | 3 perforated drum zones (2, 4, 7 mm holes), 76 x 76 x 125.6 mm each, laid out in `fuse1_zones_build.stl` (2 x 2, 4 mm gaps) | 160 x 160 x 126 mm in a 165 x 165 x 300 mm build |
| `x1c_rest/` | Bambu X1 Carbon | inlet/outlet caps, two stands, hand crank in `x1c_rest_plate.stl` | 206 x 156 mm on the 256 x 256 mm plate |

Powder printing needs no supports, so the radial holes come out clean, and the Fuse Sift (the rotating perforated
drum you just used) depowders them. Drum zone length 119.6 mm (one per tray), 85 mm perforated band, axis 62.5 mm.
Hardware unchanged: 8 mm rod ~470 mm, 2 x 608 bearings, 4 x M3 set screws.

If you retry the zones on FDM anyway: dry the filament, print slower (outer walls 40-60 mm/s), use a brim, raise
retraction a little for the stringing, and print one zone alone first.

Per-file sha256 and Merkle root in `manifest.json`. Regenerate: `python -c "from baebugs import trommel_plate as t; t.build_split()"`.
