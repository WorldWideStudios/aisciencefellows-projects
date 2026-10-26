# Thin-wall reinforcement for the fitted v3 male

Print `male_v3_SO101_thin_wall.stl` in millimetres at 100% scale. Use it with the existing `../tool_swapper_v3/pipette_collar_31mm_fitted.stl`; the female does not need to be replaced.

A continuous annular wall now closes the screw-access breakouts across the dowel roots. The wall has outer diameter 20.2 mm, inner diameter 19.6 mm and nominal thickness 0.3 mm, spanning Z=4–11 mm. The dowels span Z=6.5–9.5, so their full root height is backed. This is an additive reinforcement to the previous fitted male. The upper access openings above the reinforced band remain.

The three dowels remain 3 mm in diameter. Their projection from the slightly enlarged body is 2.9 mm. The existing female socket is 20.5 mm inside diameter, leaving nominal radial clearance of 0.15 mm. The 14 mm mounting bolt circle, 3.2 mm shank holes, flange, screw seating depth and overall 14 mm height are retained.

## Screw-head and printing constraints

The added wall makes the access openings slightly D-shaped. Straight screw-head passage was checked at diameter 5.5 mm; minimum clearance at the new wall is approximately 0.05 mm. Diameter 6 mm heads do not pass straight through. Measure the actual heads before printing; the old 6 mm head clearance no longer applies.

The reinforcement is intentionally thin. Confirm the 0.3 mm wall is present in the slicer's layer preview; otherwise it will not reinforce the dowel roots. Printed dimensional accuracy and mechanical strength are not established by the geometry checks. Trial-fit the screws and coupling by hand.

## Validation

`validation.json` records checks on the exported and reimported STL:

- One watertight solid with consistent winding.
- An annular gauge confirms continuous material across the entire dowel-root height.
- All three dowels retain 3 mm section diameters.
- Original surface samples have no loss exceeding 0.00001 mm; the change adds material.
- M3 shank and diameter 5.5 mm head gauges clear their access paths.
- No interference during insertion sampled every 0.25 mm or the 45° turn sampled every 0.25°.
- A diameter 31 mm shaft gauge clears the inserted male throughout the turn.
- Retention interference remains after a 1 mm axial withdrawal in the turned position.

Rebuild from the workspace root with:

```sh
design/tool_swapper_v1/.cad-venv/bin/python design/tool_swapper_v3_thin_wall/build_design.py
design/tool_swapper_v1/.cad-venv/bin/python design/tool_swapper_v3_thin_wall/render_design.py
```

The build reads the previous fitted male and female and writes a new male only. Prior exports remain available.
