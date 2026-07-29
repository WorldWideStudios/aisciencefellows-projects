# Per-object aspirate / dispense depth

Different labware needs the pipette tip to descend by different amounts below the
well/hole top (a shallow flat-bottom plate vs. a deep cold-block tube). This is a
property of the **object type**, so it lives on the object model as anchors, and the
epipette skills read it at run time.

## The convention: two colinear anchors, take the Z gap

Add two anchors to an object model:

| Anchor | Where |
|--------|-------|
| `depth_top` | at the well/hole **top** |
| `depth_bottom` | directly below it, at the desired **descent depth** |

- Both `parent_link: body`, **same XY** (colinear — they differ only along the
  object's own vertical), same `wxyz`.
- The descent depth is simply the **absolute Z difference** between them.

The pair is dedicated and fixed (not the target hole), so there's no per-hole error,
and the descent below subtracts this same world-Z gap — so it's exact for upright
labware. (A tilted object would shrink the gap by `cos(tilt)`, but the world-Z
descent is upright-only regardless, so that's moot.)

> The colinearity (same XY) is what makes the Z gap == depth.

## How the skill uses it

```python
try:
    top = load_object_anchor(object_id, depth_top_anchor)["xyz"]      # "depth_top"
    bot = load_object_anchor(object_id, depth_bottom_anchor)["xyz"]   # "depth_bottom"
    depth = abs(top[2] - bot[2])                                      # vertical gap
except (KeyError, ValueError):
    depth = aspirate_depth   # fixed fallback param
# ... dip to well_top_z - depth
```

`epipette_aspirate` and `epipette_dispense` both read the same `depth_top` /
`depth_bottom` pair (the depth is the same for aspirate and dispense). The anchor
names are skill parameters (`depth_top_anchor`, `depth_bottom_anchor`), so you can
point a skill at a different pair if aspirate and dispense ever need to differ. The
existing `aspirate_depth` / `dispense_depth` scalars remain the fallback for any
object without the anchors.

## Adding it to a new object

1. Find the well/hole top Z in the object model (e.g. `A1`, `hole_1`).
2. Add `depth_top` at `(any fixed XY, top_z)` and `depth_bottom` at the **same XY**,
   `z = top_z − depth`. Copy a well/hole anchor's `wxyz`.

Example — a plate whose wells top out at `z = 0.014139`, wanting a 1 cm dip:

```yaml
depth_top:
  parent_link: body
  link_T_anchor:
    xyz: [-8.0e-05, -1.0e-06, 0.014139]
    wxyz: [4.32978e-17, 0.707107, -0.707107, -4.32978e-17]
depth_bottom:
  parent_link: body
  link_T_anchor:
    xyz: [-8.0e-05, -1.0e-06, 0.004139]   # 0.014139 - 0.01, SAME XY as depth_top
    wxyz: [4.32978e-17, 0.707107, -0.707107, -4.32978e-17]
```

## Current values

| Object | Top Z | `depth_top` → `depth_bottom` | Depth |
|--------|-------|------------------------------|-------|
| `wellplate_96_flatbottom` | `0.014139` (`A1`) | `0.014139` → `0.004139` | **1 cm** |
| `coldblock_wellplate` | `0.035788` (`hole_1`) | `0.035788` → `0.015788` | **2 cm** |
| `wellplate_pcr` (parts plate) | `0.01549` (all 96 wells) | `0.01549` → `0.00649` | **9 mm** |
| everything else | — | (none) | falls back to the skill param (`aspirate_depth=0.002`, `dispense_depth=0.0125`) |

## Notes / gotchas

- **Only the Z gap matters.** The skill uses `abs(Δz)`, so an XY slip between the two
  anchors is harmless (a 3D distance would instead over-report via the hypotenuse).
  Still, place them at the same XY for clarity — and don't rely on Z alone if you ever
  need tilted labware (see below).
- **Per type, authored once.** The anchors live in the object model, so every
  instance of that type gets the depth for free — unlike `calibration` / `tcp_offset`
  in `live_state.yaml`, which are per-instance.
- **Not a plain field.** `load_object_anchor` only surfaces *anchors* (a fixed dict);
  a custom top-level `depth:` key in the yaml is silently dropped by the model parser.
  That's why this is anchors, not a scalar field.
- **The descent itself is still world −Z.** The skill dips `well_top_z − depth`
  straight down in world. The *depth* is now orientation-proof, but the descent
  direction assumes wells open upward (upright labware). Genuinely sideways labware
  would also need the descent re-aimed along the hole axis — out of scope here.
- **`coldblock_wellplate` holes.** `hole_1..hole_10` now exist (5×2 grid); the depth
  anchors reference `hole_1`'s top Z.
