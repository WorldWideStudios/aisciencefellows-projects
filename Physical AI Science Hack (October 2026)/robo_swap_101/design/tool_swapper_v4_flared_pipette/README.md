# Flared-dowel pipette swapper — combined design

This pair combines the **v2 three flared dowels and asymmetric central key** with the **fitted v3 31 mm pipette collar**. It adds a **5 mm spacer between the wrist screw mounting flange and the underside of the dowel plate**. The revised female has a compact round receiver and a tapered base. Units are millimetres; import the printable STLs at 100%.

## Files to print

- `cad/male_SO101_flared_5mm_spacer.stl`
- `cad/female_flared_pipette_collar_31mm.stl`

`diagrams/receiver_comparison.png` compares the former square receiver with this compact revision. `diagrams/design_overview.png` shows the two parts, mounting section, and assembly. `diagrams/exploded.png` shows how they fit together. `cad/male_assembled_DISPLAY_ONLY.stl` is positioned next to the female for inspection; it is not a separate part to print.

The male also has an analytic STEP export. `female_receiver_component.step` contains **only the new socket**. The complete female is supplied as STL because the retained collar source is a mesh; there is no claimed analytic STEP model of the complete holder.

## Male mounting and spacer

| Feature | Dimension / position |
|---|---|
| Standard SO-101 follower horn holes | Four Ø3.2 holes on a Ø14 bolt circle |
| Hole coordinates | X and Y = ±4.949747 |
| Mounting flange | Ø28 × 4 |
| Rear horn recess | Ø20.4 × 1 |
| Central horn screw relief | Ø5.4 through the mounting flange |
| Horn bearing plane | Z = 1 in the male print STL |
| M3 screw head seating plane | Z = 4 |
| Screw-bearing thickness | 3 |
| Spacer | 5 high; Ø27 outside / Ø21 inside |
| Dowel plate underside | Z = 9 |
| Dowel plate | Ø40 × 4; top face Z = 13 |
| Screw head / tool access | Ø6.2 through the upper plate, aligned to the four mounting screws |
| Overall male height | 21 including the 8 mm projecting coupling features |

The spacer is an integral annular bridge. Its open center keeps the screw heads clear; the four access holes through the upper plate let the screws and driver reach the original seats. This provides a **5 mm separation from the screw seating surface to the plate underside**, not 5 mm above the screw heads. A 3 mm-high head occupies part of that space and leaves about 2 mm beneath the plate.

The original 3 mm bearing web is retained. A nominal M3×6 screw seated at Z=4 reaches Z=−2, projecting 3 mm beyond the horn bearing plane at Z=1. The extra spacer does not increase the screw clamp stack or require longer screws. Digital gauges check Ø3 shanks, Ø6 head passage, Ø20 horn clearance, and central screw clearance. The mounting hole centers are independently remeasured from the cached official SO-101 wrist STEP. Actual screw head dimensions and the particular wrist horn still need a hand fit check.

The three dowels retain their v2 geometry: Ø3.6 stems, Ø6 heads, 8 projection, on a Ø30 circle. The asymmetric vertical key, nominal 45° turn, and 0.8 draw-in also remain. There is no pin lock.

## Female holder and receiver replacement

The original `pipette_collar_31mm_fitted.stl` is retained in `inputs/`. Its old receiver is removed above **Z=15.65** in the original collar coordinates. The receiver now has a **Ø41 circular upper body and 12 mm total height**, replacing the 44 × 44 × 18 block. It occupies Z=15.65–27.65, with its entry face at Z=27.65. Its lower 3.5 mm blends into a **34 × 28 rounded rectangular base** with 5 mm corner radii. The three dowel tracks and central key opening retain their existing dimensions. The reduced height leaves a nominal 3.5 mm floor below the deepest cavity; the radial material outside the largest entry hole is nominally 2.2 mm. V2's solid rear tool blank is removed.

This revision removes about **45% of the complete female part’s modeled volume** compared with the square version. The reduced section is a geometry prototype, with no strength or payload rating implied.

The original holder below Z=15.65—including the open Ø31 pipette passage, split ring, and clamp ears—is preserved. The tapered receiver forms the upper attachment above that plane. The shaft bore is recut using the same Ø31.002 cutter as fitted v3 and is verified with a separate Ø31 gauge. The new socket is wider than the old v3 socket to accommodate the three flared heads and their tracks; its width was not scaled to the collar diameter.

Insertion points toward the collar along −Z. In the male's local coupling coordinates the tightening turn is +45°. Viewed into the female opening from the approaching robot, it is clockwise. The female asymmetric entry gate sets the entry orientation. The three ramped head tracks retain the dowels after the turn; the central key rotates behind the entry lip. Follow the included assembly geometry when aligning the wrist.

## Validation

`validation.json` records checks on the exported and reimported STL files:

- Each printable part is one watertight solid with consistent winding.
- The coupling projections match the original v2 male within tessellation tolerance.
- Original holder material below the replacement plane is preserved, checked for both removed and added volume.
- M3 shanks, Ø6 head/driver access, horn recess, and central horn-screw relief clear their gauges.
- Straight insertion is checked at 38 positions; the 45° turn is checked every 0.5°.
- A separate Ø31 pipette gauge clears the female and the male throughout the tested turn.
- Pulling back 1 mm after the turn produces retention interference; 180° reversed entry is blocked.
- Mounting centers match the reference wrist STEP.
- A continuous annular material gauge verifies that trimming has not opened the tracks through the outer wall.
- The male STL is compared to its hash before this female-only revision; its geometry and 5 mm spacer remain compatible.

STL coordinate rounding can collapse tiny seam triangles; the exporter removes collapsed/duplicate faces before the final checks. No holes are patched or geometry guessed. The report records the actual cleanup count and volume change.

These are nominal geometry checks. Actual print clearances, screw fit, clamp preload, strength, pipette load and cycle life are not established. Trial-fit the screws and pair by hand. Reverse torque can release this latch-free design. An internal flared slot may require support or a carefully chosen printing process; inspect the retaining lips in the slicer.

## Rebuild

From the repository root:

```sh
design/tool_swapper_v1/.cad-venv/bin/python design/tool_swapper_v4_flared_pipette/build_design.py
design/tool_swapper_v1/.cad-venv/bin/python design/tool_swapper_v4_flared_pipette/render_design.py
```

Dependencies: CadQuery, NumPy, trimesh, manifold3d, VTK, Matplotlib. `inputs/` contains snapshots of the fitted v3 collar and the v2 STEP pair; `provenance.json` records their SHA-256 hashes. `reference/` contains the previous square female and its measurements for reproducible before/after comparisons; it is not the current printable design. The build also reads the cached official SO-101 reference at `../tool_swapper_v1/reference/Wrist_Roll_Follower_SO101.step`; its provenance and license remain there. Existing v1/v2/v3 designs and robot configuration are not modified.
