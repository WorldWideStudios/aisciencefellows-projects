# Working dimensions

Adopted 2026-10-24 as the team's working numbers. All values are in mm.

- **Source of truth:** `frame_holder.py` and `sieve_insert.py`. This page mirrors them; if you change a number, change it in the script, rebuild, then update this page.
- **Inserts follow the holder:** if a measured part disagrees, fix the holder first. The inserts take their outside size from the holder pocket.

## Holder box (`frame_holder.py`)

| What | Value |
|---|---|
| Body | 140 × 104 × 25 |
| Overall with tab | 162 × 104 × 25 |
| Side wall | 4.0 |
| Ledge thickness (bottom) | 3.0 |
| Pocket above the ledge | 132 × 96 |
| Open centre through the bottom | 122 × 82 |
| Ledge width | 5 at the ends, 7 along the sides |
| Finger notches | one U in the middle of each long wall, 34 wide × 21.5 deep from the top (round bottom, radius 17) |
| Mounting tab (+X end) | 22 long × 4.5 thick × 25 tall |
| Mounting hole | 6 diameter, centre 6.5 from the tab's end, at mid-height |

### Level spacing for the seesaw (`seesaw_tower.py`)

Each box tips about its own pivot across its middle (at the body's centre, mid-height: where `seesaw_holder.py` puts its pins), and neighbours tip opposite ways (docs/SYSTEM.md §3). The minimum pitch (pivot to pivot) that leaves 3 mm between neighbours at full tilt, from the real solids over both half-cycles, is in `out/seesaw_tower_checks.json`. The closed form is 2 (a sin θ + (H/2) cos θ) + 3, with a = 92 with the tab and 70 without, and H = 25:

| Tilt | `frame_holder` (with the +X tab) | `seesaw_holder` (no tab) |
|---|---|---|
| ±5° | 43.9 | 40.1 |
| ±10° | 59.6 | 51.9 |
| ±15° | 74.7 | 63.4 |
| ±20° | 89.5 | 74.4 |
| ±25° | 103.6 | 84.9 |

The pitch is about how far a specimen drops from one screen to the next, so the smallest pitch that clears is the gentlest. Use **55 mm at ±10°** and **65 mm at ±15°** with the seesaw holder (5 mm clear in the sim's `rocking.py`). Preview: `out/seesaw_tower.png` is still the 11:06 one (frame_holder boxes at ±25°, 105 mm). The ±10° re-render with the seesaw parts was stopped when the laptop ran low on memory.

## Seesaw holder and catch pan (`seesaw_holder.py`)

Same body, pocket, ledge and open bottom as `frame_holder.py`, so every insert and layer drops in.

| What | Value |
|---|---|
| Mounting tab | none |
| Finger notches | none (the lugs sit there); lift the box off its pins to swap inserts |
| Pivot lugs | one in the middle of each long wall: 16 wide, 6 out from the wall, from the bed up to a half-round top |
| Pivot hole | 6.2 diameter, blind, 8 deep from the lug face, centre at mid-height (12.5); coaxial on both sides |
| Overall | 140 × 116 × 25 |
| Catch pan | the same walls carried 20 further down: 45 tall, 3 thick solid floor (42 under the rim), pivot 12.5 under the rim as on a box |
| Catch-pan lip | 2 thick at the rim with a 45° underside, in 5 at the ends and 7 along the sides: leaves the 122 × 82 open bottom of the box above |

## Sieve inserts (`sieve_insert.py`)

| What | Value |
|---|---|
| Outside | 131.4 × 95.4 × 3.0 (the pocket less 0.6 total clearance); rests on the 3 mm ledge |
| Border | 10 |
| Ribs | 3 |
| Windows | 3 × 2, each 35.1 × 36.2 |
| Pull tabs | 2, centred on the long edges, flush with the outside: 20 along the edge × 6 thick × 18 above the frame |
| Hole taper | holes widen 8° downward |
| Label | hole size debossed on top of the +Y tab |

| Insert | Square hole | Bar | Screen thickness | Holes |
|---|---|---|---|---|
| `sieve_insert_5mm` | 5.0 | 1.2 | 1.6 | 150 |
| `sieve_insert_2mm` | 2.0 | 1.0 | 1.4 | 726 |

The plinko layers (`plinko_layers.py`) use the same 131.4 × 95.4 outside size. Under each pull tab, a foot at rod height reaches out to the nearest rod centres, so a tab face never lands on a rod's edge (that line contact leaves the mesh open).

## Gated container (`gated_container.py`), the final design

Same footprint as the sieve inserts, shaken longways (X).

| What | Value |
|---|---|
| Outside | 131.4 × 95.4; walls 2 thick, 16 tall |
| Pull tabs | 20 × 6, top at 21 above the container's bottom: 1 below the box rim, so boxes stack rim on rim; grip them through the box's finger notches |
| Floor | solid, 2 thick at the gate end; slopes 2° up away from the gate (rises 4.06 over the length) |
| Gate strip position | centre at x = 53, held by two rails per side with a 2.3 groove |
| Drop slot | x 54 to 61 (7 long), y ±40, over the box's open bottom; 45° ramp from 61 to the end wall |
| Tower | flip the container 180° on every other level |
| Mid-slot variant | `container(gate_x, slot)`: the strip anywhere with \|x\| ≥ 13.15 (rails clear the tabs), the drop slot `slot` long from the strip's downstream face, then a 30° wedge back into the slot from a 0.4 lip, capped 14 tall (2 under the wall top). Optimizer winner 3's L1: x 22.2, slot 8.1; its tower isn't flipped |

| Gate strip | Openings | Count |
|---|---|---|
| Size of every strip | 91.0 × 18 × 2, printed flat | — |
| `gate_w5p0`, `gate_w3p0`, `gate_w2p0` | width gaps 5.0 / 3.0 / 2.0, 8 tall | 11 / 15 / 19 |
| `gate_t1p2`, `gate_t1p4`, `gate_t1p6` | tunnels 8 wide, 1.2 / 1.4 / 1.6 tall | 7 each |

Teeth between openings are 2 wide.

## Ribs-across inserts for the seesaw (`sieve_insert.py` ACROSS)

The grains slide along X on the seesaw, so these have nothing solid running along X and no flat top a grain can rest on. Same outside, pull tabs and hole sizes as the inserts above.

| What | Value |
|---|---|
| Screen | 121.4 × 81.4 at the bottom, the whole area over the box's open bottom (border 5 at the ends, 7 along the sides: just the ledge) |
| Border | a 45° ramp from the screen's edge up to a 0.6 flat at the outer edge: 6.0 tall at the ends, 8.0 along the sides |
| Ribs | 2, along Y only, at x = ±20.73: 45° ridges 3 wide at the screen, 1.5 tall |
| Windows | 3 × 1, each 38.47 × 81.4 |
| Label | "5X" / "2X" on the +Y tab |

| Insert | Square hole | Bar | Screen | Holes | Open, % of the box's open bottom |
|---|---|---|---|---|---|
| `sieve_insert_5mm_across` | 5.0 | 1.2 | 1.6 | 216 | 54.0 |
| `sieve_insert_2mm_across` | 2.0 | 1.0 | 1.4 | 936 | 37.4 |

In the sim: `inserts:5mm_across,2mm_across,pitch=55,holder=seesaw`.
