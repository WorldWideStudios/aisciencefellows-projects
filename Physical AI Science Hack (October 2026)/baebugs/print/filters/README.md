# Novel filters: craft-store punches, plastic canvas, tulle (+ passage twin)

`filters.json` lists 20 hole types at **nominal** sizes (inch punches converted to mm; canvas opening =
pitch − ~0.9 mm bar; tulle ~1.2 mm). Punch dies vary by brand: measure one punched hole before trusting a
cut. `stl/` holds 50 × 50 × 1.6 mm Fuse 1+ plates (19 printable; 14-count canvas is below the 1 mm hole
minimum, buy it instead). Realisations: **punched** (PET / acetate / craft-foam sheet), **bought**
(canvas, tulle), or **printed** (STL).

## Passage twin (`passage/<mode>/`)
For each of the 91 TOY insects × 24 holes (kit sieves at their estimated apertures + this library):
convex-hull projection over 64 orientations × in-plane rotations → `pass_flat`, `pass_tumbled`,
`end_on_only`, `retained`, plus a passage score (fraction of orientations that fit).
- `toy_rigid`: the printed toy (legs/wings fixed) — exact for the physical toys.
- `body_folded`: body segments only — approximation of a real insect with appendages folded.

Findings (body_folded): on round / square / hex holes a body lying flat passes only if its width is
~0.6–0.7 × the inscribed diameter; most other passage is **end-on only**, so the kit's
"width governs passage" assumption needs flow to stand insects upright. **Slots** cut at 1.0 ×
slot width lying flat (long bodies lie along the slot), and they are where a width-only rule fails
leave-one-plate-out (0.83–0.85 accuracy): hole **shape** carries information.
`python -m baebugs.punch_filters` / `python -m baebugs.passage_twin` rebuild everything; each hole has a
spec hash and each (toy, hole) test is a Merkle leaf (`passage_root` in `summary.json`).

## OpenSCAD
`scad/<filter>.scad` = exact hole outline + centres of each plate; `scad/filter_plate.scad` = hand-editable parametric plate (shape circle/square/hexagon/slot/star, size, slot length, pitch via web, border, thickness, hex stagger). Sizes nominal.
