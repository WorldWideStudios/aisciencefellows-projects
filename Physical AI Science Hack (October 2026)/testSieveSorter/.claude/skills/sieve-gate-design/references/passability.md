# Passability rules

What can pass which opening, from geometry alone. `scripts/gatecalc.py` implements every rule on this page; read this page when a result looks odd or when you change a rule.

Status labels: **derived** means it follows from the geometry below; **repo** means it is stated in this repo's docs or code (file named); **assumed** means a placeholder to replace with a measurement.

## Contents
1. Item model
2. Orientation: flat vs rolled
3. Rules per gate type
4. Worked examples
5. Print tolerance and margins
6. Transport, wedging, snagging (not in the calculator)
7. Length
8. Order of levels

## 1. Item model

- Every item has three body dimensions, **L >= W >= T** (length, width, thickness), measured with calipers on 30 random items per type (`sim/BENCH.md` step 3). For insects, measure the body only (head to abdomen tip), and note the **span** separately: the widest extent including legs, antennae and wings.
- Cross-sections are treated as **ellipses** (grains, insect bodies). Box-shaped items pass diagonally less easily than ellipses, so the rules below are slightly optimistic for them.
- Measure in the condition you sort in. Wet quinoa changes thickness (README, pool section). Ethanol-preserved specimens are stiffer than fresh ones.

## 2. Orientation: flat vs rolled

- **Shaking lays items flat**: the thickness T points up and the item rests on its largest face (repo: README, `gated_container.py`).
- **Items pass end-first**, long axis along the flow, so only the W x T cross-section has to fit (repo: gates-verdict.md).
- **An item can roll about its long axis** and arrive on edge, with W up. That is not its resting pose but it happens: neighbours, teeth and the return stroke prop items up. So every gate gives two answers:
  - **flat**: passes lying flat. This is what normally happens.
  - **any**: passes at some roll angle. This is the worst case.
- An item that passes "any" but not "flat" passes with probability **p_roll** (assumed 0.5). `gatecalc.py sim` estimates p_roll from sim runs. The bench is the real answer: count how many of those items end up downstream.

**The exact rule for a rectangular opening** a across x b up, and an elliptical cross-section W x T (derived):
- Rolled by angle θ, the ellipse's horizontal extent h and vertical extent v satisfy h² = W²cos²θ + T²sin²θ and h² + v² = W² + T².
- It fits if h < a and v < b at the same θ. h² ranges over [T², W²], so a suitable θ exists exactly when

  **T < min(a, b)  and  W² + T² < a² + b²**

## 3. Rules per gate type

| Gate (gatecalc token) | Where it exists | Passes flat | Passes at some roll (worst case) | What it really cuts |
|---|---|---|---|---|
| Width gap `w<s>`, H tall (H = 8 today) | `cad/gated_container.py` and `cad/sieve_system.py` STRIPS kind `w` | W < s and T < H | T < min(s, H) and W² + T² < s² + H² | W, if items stay flat. **Only T < s is guaranteed to pass**, because a tall gap is a tall slot to a rolled item. |
| Window `win<s>x<h>`: a w gap with its height capped | proposal | W < s and T < h | T < min(s, h) and W² + T² < s² + h² | W, and also blocks the roll when s² + h² <= W² + T² of the kept items |
| Pillar comb `p<g>`: round posts, clear gap g | proposal (the posts exist in `sieve_system.py` gate_coupon) | same as w | same as w | same as w, but jams less (section 6) |
| Tunnel `t<h>`, Wt wide (Wt = 8 today) | STRIPS kind `t` | T < h and W < Wt | T < min(h, Wt) and W² + T² < h² + Wt² | **T, robustly**: rolling never helps, because thickness is the smallest dimension |
| Square floor hole `sq<a>` | `cad/sieve_insert.py` INSERTS, `round_stack.py` | W < a (aligned with the hole's edges) | min(W, √((W² + T²)/2)) < a (diagonal) | W, but **flat items pass diagonally down to about 0.71 W** |
| Round hole `o<d>` | `sieve_system.py` tray_* (24-well footprint only); proposal for the holder tower | W < d | W < d | **W, exactly.** It is the same test as a round well's mouth. |
| Floor slot or rod gap `slot<g>` | `plinko_layers.py`, `round_stack.py` slot, `sieve_system.py` tray_fine_slot | T < g | T < g | T (items tip in edge-first) |

Notes:
- A square hole's diagonal for an ellipse: rotated 45° in the hole, its bounding box is √((W² + T²)/2) on both sides (derived). The sim's insert rule (`sim/designs_holder.py` ideal_zone) uses the aligned test only, so the sim's "ideal zone" can call a diagonal pass a leak.
- The sim's pool rule (`sim/designs.py` fits) checks two discrete poses, flat and fully on edge. The rule above also allows intermediate roll angles, so it is slightly more permissive.
- Round holes and square windows **both** limit two dimensions; a tall slot limits one (repo: gates-verdict.md). That is why width gates and tunnel gates are different filters.

## 4. Worked examples

Run any of these with `gatecalc.py item LxWxT --gates ...`. Sizes are effective, i.e. as printed.

| Item | Gate | Result | Why |
|---|---|---|---|
| Long-grain rice 6.5 x 2.0 x 1.7 | w1.85 (nominal w2.0, 0.15 undersize) | passes only by rolling | flat W 2.0 > 1.85; on edge T 1.7 < 1.85. **gate_w2p0 does not reliably hold rice back.** |
| Same rice | t1.25 (nominal t1.4) | blocked | T 1.7 > 1.25 |
| Quinoa 2.0 x 2.0 x 1.1 | t1.25 | passes flat, 0.15 mm clearance | near-size: wedging risk |
| Quinoa | sq1.85 | passes only diagonally | √((4 + 1.21)/2) = 1.61 < 1.85 |
| Rice vs quinoa | needs a thickness cut | | Same W, so no width gate or hole separates them. Only t or slot can (repo: gates-verdict.md "Test materials"). |
| Flat beetle 7.0 x 6.8 x 3.0 | w6.0, 8 tall | passes only by rolling | T 3 < 6 and 6.8² + 3² = 55 < 6² + 8² = 100 |
| Same beetle | win6.0x5.8 | still passes at an intermediate roll | 55 < 36 + 33.6 = 69.6. A height cap must satisfy s² + h² <= W² + T²; `plan` computes this and says when no cap works. |
| Same beetle | o6.0 | blocked | W 6.8 > 6.0 |

**Width-then-thickness** separates oblong items from flat ones even when their widths overlap. The w cut removes everything wide; then the t cut keeps the thick ones (rice, 1.7) and passes the flat ones (quinoa, about 1.0).

## 5. Print tolerance and margins

- **Openings print undersize** in FDM. Effective = nominal - undersize. The default 0.15 mm is assumed. Print `cad/hole_gauge.py` (round holes 1.00-12 mm), measure them and put [nominal, measured] pairs in the spec's `[print] gauge`. The hole gauge measures round holes; strip gaps are notches open on one side and may differ, so also measure the printed strips themselves (10 openings per strip, pin gauges or drill shanks) into `sim/bench/openings.csv`.
- **The critical dimension belongs in the XY plane**: strips print flat, so both the gap width and the tunnel height are in XY (repo: README). Pillars must print upright (axis vertical) to come out round.
- **First-layer squish** narrows the openings on the bed side (repo: README pool section). Measure that side.
- **Margins**, in `[rules]`:
  - `pass_clearance_mm` (default 0.15; use 0.25 or more for specimens): room a passer needs beyond its size.
  - `block_margin_mm` (default 0.10): how far a kept item must exceed the opening.
  - `[print] tolerance_mm` (default ±0.10): scatter of a printed opening.
- **The planner scores every size at its worst case**: the opening at +tolerance for kept items, at -tolerance for passers, with the margins applied and p_roll for roll-only items. It then picks the **middle of the run of sizes with the best score** (the "same-score window"). A wide window means the choice is robust; a one-point window means it depends on the margins.
- Round the nominal size to 0.05 mm (gatecalc does). Name parts the repo's way: `gate_w2p45`, `gate_t1p4`.
- **Do not size gaps at 1.3x body width.** That rule turns a 2 mm cut into 2.6 mm; keep it only as a snag guard on the coarse gate (repo: gates-verdict.md "Cut points").

## 6. Transport, wedging, snagging (checked in the sim and on the bench, not by the calculator)

All repo, from gates-verdict.md and the CAD docstrings:
- **One-way drop after each gate.** The gated container drops passers through a 7 mm slot onto the next level, so nothing comes back on the return stroke.
- **Gates need a push.** A level, symmetric stroke only makes items wander. The container's floor slopes 2° toward the gate. Shaking plus spray walks items down to it. Whether a 2° slope is enough under water is unmeasured.
- **Wedging.** A flat-walled gap has a 2 mm long throat (the strip thickness), where near-size items can lock between the teeth. Round or teardrop pillars have a zero-length throat with two-point contact, and the return stroke pops a wedged item back out. Openings that widen downstream (8° relief on inserts, the posts' downstream tail in `gate_coupon`) let near-size items fall free. The calculator's **near-size** count is the number of items within `near_band_mm` (0.15) of the opening.
- **Snagging.** Legs and antennae wider than the gap catch on teeth. The calculator flags passing items whose span exceeds the gap by more than 1 mm. The sim's insect legs are rigid, so it over-predicts snagging of splayed legs.
- **Fragile items** squeezed through a low tunnel can lose legs. Prefer pillars and a larger clearance.
- **Items lying across the gate** have to turn end-first before they pass. That slows them down; the sim's t90 shows it.

## 7. Length

- **Gates and holes never cut length**: items pass end-first (repo: gates-verdict.md "Cut points").
- **Length matters in two places:**
  - whether an item fits the well (see well-fit.md);
  - BugPicker's "2-6 mm" range, which does not say which dimension it means (repo: current-system-vs-our-idea.md).
- **Separating by length needs a different mechanism:**
  - an indented-cylinder grader: pockets lift short items out of a rotating drum;
  - a vision reject at the picker;
  - flagging those items for hand handling.
- `gatecalc plan` reports how many items reach a "fits" level but are too long.

## 8. Order of levels

- Each level keeps what passes every gate above it but not its own gate. The calculator and the sim's `ideal_zone` both use this "first gate it can't pass" rule.
- **Put the coarse cut on top.** Big items block openings.
- **Then the width cut, then the thickness cut.** A tunnel on top would keep everything thick, big items included, on one level.
- **Flip the gated container 180° on every other level**, so a drop lands on the solid end of the container below (repo: `gated_container.py`).
