# Pipette swapper v3 — SO-101 fitted pair

Use **male_v3_SO101_fitted.stl** and **pipette_collar_31mm_fitted.stl** together. STL units are millimetres; import at 100%. Original supplied meshes are preserved in `inputs/`.

## Changes

The supplied male had four Ø3.2 holes on a 28 mm bolt circle (19.799 mm square). The standard SO-101 follower horn interface uses a 14 mm bolt circle (9.899495 mm square). The revised hole centers are (±4.949747, ±4.949747). The flange remains Ø36; the coupling core remains Ø20. Scaling the whole model would have spoiled the coupling dimensions.

The mounting flange has a Ø20.4 × 1 mm rear horn recess and Ø5.4 central horn-screw relief. The four screw head seats are at Z=4, leaving the reference 3 mm bearing web above the horn recess. Ø6.2 access bores extend through the coupling so four M3 screws can be installed from the tool side. These bores open locally through the coupling wall. Screw access was checked with Ø6 mm head gauges; measure the actual screw heads and horn before printing.

The male's plain cylindrical stem is shortened by 8 mm, reducing overall height from 22 to 14 mm while retaining the three tabs and original tapered nose. This prevents the assembled male from occupying the shaft bore. The collar has corresponding new 45° internal tracks; use the revised pair together. The tracks have a 13.4 mm outer radius, Z=19.45–23.85 and a 1.8 mm top retaining lip. The core cavity radius is 10.25 mm, giving nominal 0.25 mm radial clearance. Original entry slots and lower cavities remain. This revision uses constant-depth tracks; it does not establish controlled ramp preload.

The marked obstruction is removed by recutting the nominal Ø31 mm shaft passage along X across the entire collar. The cutter is Ø31.002 mm to avoid coincident mesh faces. A separate Ø31 mm gauge verifies the open passage with the male inserted and throughout the tested turn. The collar exterior and clamp ears are retained.

Small disconnected, defective internal fragments in the supplied male STL were excluded; both revised exports are each a single closed solid.

## Reference and validation

Mounting dimensions were remeasured from the repository's cached official [TheRobotStudio SO-101 follower wrist STEP](https://github.com/TheRobotStudio/SO-ARM100/blob/a758567c3978dfeefe282ede0500085a48fe8f78/STEP/SO101/Follower_Specific/Wrist_Roll_Follower_SO101.step). The hole centers agree to numerical precision; see `wrist_reference_check.json`. This establishes agreement with the standard reference, not a measurement of the user's particular wrist.

`validation.json` records checks on the exported, reimported STL files:

- Each part is watertight, has consistent winding and contains one solid.
- No volumetric interference during 18 mm of aligned insertion, sampled every 0.25 mm.
- No volumetric interference through a 45° turn, sampled every 0.25°.
- A Ø31 shaft gauge clears the female and assembled male throughout the turn, sampled every 1°.
- Four Ø3 mm screw shank gauges, Ø6 mm head/access gauges and a Ø20 mm horn gauge clear their respective mounting features.
- A 1 mm axial withdrawal after turning produces interference with the retaining lip, verifying geometric capture. Insertion at 45° also encounters interference.

For assembly visualization, rotate the male 180° about X, then 0–45° about female Z, and translate by (0,0,29.65). From the receiver opening looking toward the collar, the locking turn is counterclockwise. The three equivalent entry positions are 120° apart. `male_locked_display_only.stl` is positioned for inspection alongside the female; **do not print it**.

The digital checks establish nominal geometry only. Print a fit prototype and check mounting, screw access, insertion, turning, shaft clearance and retention by hand before using the robot. Printer shrinkage, fastener variations and strength are not validated. There is no positive anti-rotation latch; reverse rotation can release the coupling.

## Rebuild

From the workspace root:

```sh
design/tool_swapper_v1/.cad-venv/bin/python design/tool_swapper_v3/build_design.py
design/tool_swapper_v1/.cad-venv/bin/python design/tool_swapper_v3/render_design.py
```

Build dependencies: Python 3.12, numpy, trimesh, manifold3d, networkx. The preview additionally uses matplotlib. Inputs are the preserved supplied STLs. No host network or robot configuration is changed.
