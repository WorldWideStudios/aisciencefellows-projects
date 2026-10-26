# SO-101 tool swapper — design 2: keyhole coupling

Second design, preserving v1 separately. Units: mm. Robot-side male and tool-side female only; the pin lock, cross-hole, yoke, springs and guide hardware are removed.

## Connection

The male carries a **vertical asymmetric key head** and **three short flared dowels**, equally spaced on a Ø30 circle. The key head is 3 wide × 10 tall, offset vertically so it extends from y=−4 to +6. It occupies z=3.4 to 8, above a Ø3 neck. This breaks the 180° ambiguity of a centered rectangular blade. Each outer dowel has a Ø3.6 stem, a flare from z=5.2 to 6.2, and a Ø6 head from z=6.2 to 8.0. All features turn together.

The female face has **one vertical entry orientation**, with a 3.7 × 10.7 asymmetric slot through a 2.1-deep retaining lip. The central head must pass behind this lip before it can turn. A flared fan-shaped cavity behind the face allows the rotation; the narrow neck stays in the entry opening. The internal head envelope reduces its designed side clearance from 0.35 at entry to 0.06 at 45°. These are cutter-profile clearances: overlapping swept profiles and print tolerances affect actual play. The female face is no longer an open fan-shaped hole.

Align the vertical key and the three enlarged dowel entries. Insert straight until the male face is 0.8 from the receiver face. Turn +45° about the CAD insertion axis (+z), counterclockwise when viewing the female entry face from the robot side. The key progressively approaches the close-fitting end of its internal flared slot while the three headed studs follow ramps with 0.8 nominal axial draw-in. Finish with the faces together; reverse to release. The end walls limit further tightening rotation.

## Main dimensions

| Feature | Value |
|---|---|
| Male flange | Ø40 × 7 |
| Existing horn mount | 4 × Ø3.2 on Ø14 bolt circle |
| Screw head recesses | Ø6.2 × 3 deep |
| Rear horn recess | Ø20 × 1 deep |
| Central rear screw relief | Ø5.4 × 4 deep |
| Preserved screw-bearing web | 3 |
| Female receiver | 44 × 44 × 18 |
| Rear tool blank | 24 × 24 × 18 |
| Dowels | 3, Ø3.6 stem / Ø6 flared head / 8 projection |
| Entry holes | Ø6.6 |
| Curved stem tracks | Nominal Ø4.1 swept cutter |
| General running clearance | 0.25 per side |
| Motion | Straight insertion, then 45° / 0.8 draw-in |

The flange and receiver are larger than v1 to make room for three headed studs while keeping the original wrist mounting holes accessible. The tool blank is solid and has no tool-specific holder yet. V1's rack is not compatible with the larger receiver; no revised rack is included in this two-part design.

## Files

- `cad/male.step`, `cad/female.step`: editable solid exchange geometry.
- `cad/male.stl`, `cad/female.stl`: prototype print meshes.
- `cad/assembled.step`: seated colored assembly.
- `diagrams/design_overview.png`: male, female, exploded and cutaway views.
- `build_design.py`, `render_design.py`, `parameters.json`: reproducible source and dimensions.
- `validation.json`: solid validity and discrete nominal insertion / twist interference checks.

Rebuild from the repository root using the existing isolated CAD environment (CadQuery, Shapely, NumPy, VTK, Matplotlib and trimesh):

```sh
design/tool_swapper_v1/.cad-venv/bin/python design/tool_swapper_v2/build_design.py
design/tool_swapper_v1/.cad-venv/bin/python design/tool_swapper_v2/render_design.py
```

The dowel pockets loft radial profiles along a rising circular path and use rounded end caps. The internal key cavity uses a union of clearance profiles sampled every 0.25°, decreasing clearance along the turn. Validation checks the nominal insertion and turning path, and rejects five wrong entry orientations including 180°. Small angular alignment tolerance is intentional. Geometry validation does not establish strength, preload, cycle life or manufacturing tolerance.

This is a fit-test prototype. The internal slot tightens geometrically toward the end of travel, but running clearances leave some play; face contact alone does not establish a controlled clamp preload. Assess a thin compliant face pad or tune the ramp/head fit after measuring printed parts. With the requested pin removal there is **no positive anti-rotation lock**: reverse tool torque may unwind the coupling. No self-locking or payload rating is claimed. Test capture, insertion, turn, release, screw access and applied loads by hand with a dummy tool before robot use. Inspect internal overhangs and remove support without damaging the retaining lips. No robot or host network configuration was changed.
