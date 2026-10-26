# SO-101 quarter-turn tool swapper — v1

This design replaces the **follower gripper body** on the existing wrist-roll horn. It includes the male interface, a female receiver with an unfinished rear tool block, a positive locking mechanism, and an open-top rack concept. It implements the user-selected **quarter-turn interrupted screw**, not a continuous M10 machine thread. Dimensions are millimetres.

## Review files

- `diagrams/01_assembly_and_sequence.png`: exploded, cutaway, parked and lifted views.
- `diagrams/02_dimensions_and_mount.png`: component views, mounting pattern and simplified section.
- `cad/assembled.step`: colored assembly including illustrative spring and guide-screw envelopes.
- `cad/male.step` and `.stl`: robot-side replacement.
- `cad/female.step` and `.stl`: receiver plus solid tool blank.
- `cad/latch_yoke.step` and `.stl`: sliding release part.
- `cad/rack_concept.step` and `.stl`: open-top cradle, with axial float and parking magnet pockets.
- `cad/latch_pin_envelope.step`: steel pin envelope; use real steel hardware, not a printed pin.
- `cad/female_cutaway_display_only.stl`: visualization only, **not a part to manufacture**.
- `parameters.json`, `build_design.py`, `render_design.py`, `validation.json`: editable dimensions, CAD generator, drawing generator and geometric checks.

## Requested interface

| Feature | v1 dimension / behavior |
|---|---|
| Male screw maximum diameter | 10.0 |
| Total seated insertion beyond flange | 10.0 |
| Core diameter / pilot | 8.0 core, taper to 6.0 over final 1.5 |
| Interrupted threads | Four helical sectors: two opposed sectors at each of two axial positions |
| Sector geometry | 36° arc, 1.2 axial thickness, 1.0 radial height |
| Axial positions | Sector centers at 3.0 and 7.0 from seating face |
| Screw lead | 8.0 per full revolution, used over only a quarter turn |
| Docking movement | Straight insertion 8.0, then 90° rotation and 2.0 draw-in |
| Female entry | 12.0 diameter funnel, 1.8 deep, tapering to 8.4 core bore |
| Slot openings | Two opposed 60° slots; nominal ±12° rotational capture relative to a 36° male sector |
| Thread clearance | 0.30 radial at crest; 0.30 axial on each flank; core radial clearance 0.20 |
| Female cavity depth | 11.2, so the 10.0 tip does not bottom out |
| Male flange | 28.0 diameter × 7.0 total thickness |
| Female receiver | 32.0 wide × 28.0 high × 22.0 deep |
| Rear tool blank | 24.0 × 24.0 × 18.0; integral to receiver |
| Lock | 2.0 steel pin into a 2.3 cross-hole, 1.5 nominal radial engagement |
| Rack release travel | 3.0 vertically |

The 10 mm specification refers to the **outermost screw sectors**, not the 8 mm core. The 10 mm insertion includes the 1.5 mm pilot. It is not 10 mm of continuous thread engagement.

## SO-101 mounting match

Reference: TheRobotStudio, `SO-ARM100/STEP/SO101/Follower_Specific/Wrist_Roll_Follower_SO101.step`, pinned to commit `a758567c3978dfeefe282ede0500085a48fe8f78`.

Measured from the source STEP's cylindrical surfaces:

- Four 3.2 diameter holes at (±4.949747, ±4.949747) relative to wrist-roll center.
- **14.000 bolt-circle diameter**, equivalent to a **9.899495 square**.
- Original head clearance diameter 6.0; new counterbores use 6.2 for prototype clearance.
- Original screw-bearing web thickness 3.0; preserved in the new flange.
- Rear horn recess: 20.0 diameter × 1.0 deep.
- Central horn-screw clearance: 5.4 diameter; new blind relief extends 4.0 from the back.

The new flange rear is at z = −7; horn bearing plane is −6; M3 screw head seats are at −3; tool-facing seating face is z = 0. Thus the original 3 mm clamp stack is preserved. The four existing M3×6 screws enter from the tool side. The center relief clears the already-installed horn screw; it is not a fifth attachment screw. The hex-key paths at radius 7 clear the 10 mm maximum screw diameter.

This matches the published **standard SO-101 follower** interface. Before printing the full assembly, compare the actual wrist horn against the 14 mm circle and 20 mm recess, because vendor revisions may differ. Reuse the original horn and the four gripper mounting screws if their head dimensions and protrusion agree. The adapter replaces the whole gripper body and gripper motor assembly, rather than only the moving jaw.

Official assembly instructions specify four M3×6 screws for attaching the gripper to motor 5:
https://huggingface.co/docs/lerobot/so101#gripper--handle

Original CAD:
https://github.com/TheRobotStudio/SO-ARM100/blob/a758567c3978dfeefe282ede0500085a48fe8f78/STEP/SO101/Follower_Specific/Wrist_Roll_Follower_SO101.step

## How it docks

1. Keep the screw axis horizontal and coaxial with the receiver in the rack. The release yoke's feet rest on the rack floor; this raises the yoke and lock pin 3 mm. The rack side guides stop receiver rotation. Push the receiver toward its rear stop before engagement to establish the starting position.
2. Align the two slot openings and insert the pilot and screw sectors 8 mm. The two entry orientations are 180° apart; mark and consistently use one for repeatable tool orientation. The cutaway and CAD show the entry orientation with sectors on the left and right.
3. Turn the wrist 90° in the tightening direction: clockwise when looking **from the robot toward the receiver**, equivalent to positive rotation about the model's +z axis. The helical grooves provide 2 mm of axial pull-in. The cradle allows the receiver to move 2 mm toward the robot while the robot holds its axial position. If sliding friction prevents that movement, coordinate a small forward arm movement; do not force the wrist against a jam.
4. The flange contacts the receiver face at the final angle. A thin compliant face gasket supplies preload to reduce looseness. A 21 ID × 24 OD × 0.5 thick soft silicone ring fits the 0.3-deep groove; compression and tightening effort need testing. The end of the helical groove defines the final angle.
5. Lift vertically. As the rack stops supporting the yoke feet, its springs lower the yoke and steel pin into the male cross-hole. The pin is the positive anti-rotation lock. Lift at least 20 mm to clear the cradle before moving away. Confirm the yoke has fully lowered; the pin does not engage if the wrist has stopped short of the final angle.
6. Return the tool to the cradle to release. Lowering raises the yoke and withdraws the pin before reverse rotation. Reverse the 90° twist; the receiver moves back within its rack clearance. Withdraw horizontally. **Do not attempt to unscrew while the pin remains engaged.**

The rack constrains rotation but intentionally provides axial freedom. Its front and rear stops bound that movement. Its open top is the pickup/release direction. The rack is part of the proposed mechanism, not a validated stand-alone docking station.

## Retention and extra hardware

A screw alone can unwind under reverse tool torque. This design therefore includes a separate sliding yoke and steel pin; the complete mechanism requires more than the two printed mating bodies.

Proposed hardware, to fit-check before use:

- Existing 4 × M3×6 gripper-to-horn screws.
- 1 × 2 mm steel pin, approximately 15.5 long, bonded or secured to the yoke. The pin envelope is included in CAD.
- 2 × M3×20 guide screws with retaining heads / washers. Female 2.5 pilot holes provide 6 mm nominal engagement; tap or fit suitable inserts after verifying the chosen fastening method. The model has plain guide holes, not modeled metal threads. A smooth shoulder/sleeve is preferable to sliding repeatedly on screw threads.
- 2 compression springs fitting over the guides: illustrative envelope 6 OD, at least 3.5 ID, 10 working length while locked and 7 while released. Select springs with enough travel before coil bind; the displayed cylinders are **spring envelopes**, not manufactured springs. Start with a combined released force around 1–2 N and test for reliable return without binding; this is a design target, not a verified specification.
- 1 soft silicone face gasket, 21 ID × 24 OD × 0.5 thick, as a preload trial.
- 2 bonded steel target discs, approximately 6 OD × 0.8 thick, in the female underside recesses; 2 magnets approximately 6 OD × 2 thick in the rack pockets. These retain the parked receiver against the release springs. Select and measure the pair so its actual holding force exceeds the springs' upward force across the full 2 mm axial float, yet the robot can lift it. No nominal magnet force is assumed. The tiny central holes in the target recesses are optional retention pilots; flush bonded discs are the initial proposal.
- 2 appropriate fasteners through the rack's 4.4 holes to fasten it to a rigid support.

Magnets are only for parking; the steel pin and screw sectors retain the carried tool. Spring/guide envelopes are in `assembled.step`; some diagrams omit them for clarity. Gasket, target discs and magnets are specified here but are not separate solid models in that assembly.

## Manufacture and first assessment

The exports are **prototype candidates**, not load-rated production parts. The intentionally loose printed-thread clearances assist teleoperation but do not guarantee zero backlash. The face gasket is meant to maintain seating preload; pin clearance still permits some movement if that preload is lost. A future precision version may need a tapered seat and metal lock bushings.

For a fit trial, use a tough, dimensionally stable printing material. Orient the male with the horn side down and the screw upward, and the female with the tool blank down and the socket upward. Inspect support requirements in the slicer: the internal interrupted grooves have overhangs, and trapped support must not remain. The yoke can print on its 6 mm-wide side to keep its U shape in the layer plane. No print orientation or material strength has been validated. At 10 mm outer diameter the sectors are small, so do not infer payload capability from their appearance.

First check by hand: horn fit and screw protrusion; insertion without cross-engagement; full quarter-turn seating; pin insertion and retraction; gasket preload; receiver sliding through the rack; parking retention; lift and return. Test with an inert dummy mass before attaching a pipette. Then establish acceptable axial force, bending moment, torsional load, backlash and cycle life from the actual pipette mass, center of gravity and plunger forces. Those inputs were not provided and no load capacity is claimed.

The tool blank is intentionally solid. It does not yet include a pipette holder, tip ejection or plunger actuation, pneumatic/electrical routing, or spill protection. Those can be added while preserving the receiver interface.

Removing motor 6 may require updating the robot's configured motor list or keeping it electrically connected off the moving tool for an initial test; stock teleoperation can expect a gripper motor response. No robot configuration, calibration, motor state or host network settings were changed during this design task.

## Validation and editable source

`build_design.py` checks valid single solids and nominal interferences at seven twist positions, five straight insertion positions, the seated pin, the released yoke, and three rack float positions. `validation.json` records the results. These are discrete CAD checks, not a tolerance study, structural analysis, real-world collision survey or physical test.

A local isolated `.cad-venv` was used (separate from the robot's existing Python environment). To rebuild from this folder:

```sh
uv venv --python 3.12 .cad-venv
uv pip install --python .cad-venv/bin/python cadquery==2.8.0 matplotlib trimesh vtk
.cad-venv/bin/python build_design.py
.cad-venv/bin/python render_design.py
```

See `reference/LICENSE` for the upstream Apache-2.0 license. The upstream STEP is retained as the dimensional reference; its geometry was measured, and the replacement geometry was built parametrically from scratch.
