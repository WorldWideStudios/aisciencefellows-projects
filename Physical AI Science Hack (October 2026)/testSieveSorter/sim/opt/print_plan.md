# Print plan: demo winners

Built 2026-10-25 09:52 from `sim/opt/winners.json`, sliced for the P1S (Bambu Studio's default process, PLA). Made by `cad/winners.py`.

**Caveat:** sim ranking only; uncalibrated; openings simulated at nominal - 0.15 mm (ASSUMED undersize). The CAD is drawn at the nominal sizes; the sim assumed openings print 0.15 mm small. Check that against `hole_gauge` before trusting a gate size to 0.1 mm.

## Winner 1: plinko

- Sim spec: `plinko`, robust score 0.999
- Stroke to set on the Pi: tool sine 48 Hz, 2.2 g (0.24 mm), 20 deg up (profile sine, amp_mm 0.2373, freq_hz 48, angle_deg 20)
- Tower preview: `cad/out/win1_tower.png`

| Part | Time | Filament | Checks |
|---|---|---|---|
| `win1_layer_1_rods_3p7` | 37 min | 22.3 g | ok |
| `win1_layer_2_rods_1p5` | 47 min | 25.0 g | ok |
| `win1_layer_3_catch` | 47 min | 33.3 g | ok |
| **Total, one of each** | **130 min** | **80.6 g** | |

**One plate, ready to print:** 124 min, 80.5 g, all parts arranged on one P1S plate: `cad/out/slice/win1_plate.gcode.3mf` (local, not committed).

No printability flags.

## Winner 2: plinko

- Sim spec: `plinko`, robust score 1.000
- Stroke to set on the Pi: tool sine 37 Hz, 2.1 g (0.38 mm), 25 deg up (profile sine, amp_mm 0.3812, freq_hz 37, angle_deg 25)
- Tower preview: `cad/out/win2_tower.png`

| Part | Time | Filament | Checks |
|---|---|---|---|
| `win2_layer_1_rods_4p7` | 39 min | 24.1 g | ok |
| `win2_layer_2_rods_1p6` | 54 min | 31.4 g | ok |
| `win2_layer_3_catch` | 47 min | 33.3 g | ok |
| **Total, one of each** | **139 min** | **88.9 g** | |

**One plate, ready to print:** 133 min, 88.7 g, all parts arranged on one P1S plate: `cad/out/slice/win2_plate.gcode.3mf` (local, not committed).

No printability flags.

## Winner 3: gated_mid

- Sim spec: `gated:2.7,t3p35,t1p45,tw=4.85,tooth=0.95,slot=8.1/7,gx=22.2/53,flip=0`, robust score 0.985
- Stroke to set on the Pi: tool sine 48 Hz, 3.7 g (0.40 mm), 30 deg up (profile sine, amp_mm 0.3991, freq_hz 48, angle_deg 30)
- Tower preview: `cad/out/win3_tower.png`
- Assembly, top first:
  - L1 (top): gate_t3p5 at x 22.2, drop slot 8.1 mm, wedge beyond
  - L2 (NOT flipped): gate_t1p6 at x 53, standard slot and ramp
  - catch pan under L2

| Part | Time | Filament | Checks |
|---|---|---|---|
| `win3_gated_container_L1` | 70 min | 48.6 g | ok |
| `win3_gated_container_L2` | 72 min | 48.9 g | ok |
| `win3_gate_t3p5` | 6 min | 3.2 g | ok |
| `win3_gate_t1p6` | 6 min | 3.5 g | ok |
| **Total, one of each** | **154 min** | **104.1 g** | |

**One plate, ready to print:** 152 min, 103.8 g, all parts arranged on one P1S plate: `cad/out/slice/win3_plate.gcode.3mf` (local, not committed).

No printability flags.

## Breaker layer (prints after the winner plate)

The clump breaker for the top of the stack (`docs/sessions/clump-breakup.md`): `breaker:open=8,bar=1.6,pin_d=2.5,pin_h=12,pitch=10,tip=round`, built by `cad/breaker_layer.py`. These sizes are a sensible default, not an optimizer result; the optimizer's `malaise` study searches the same parameters, and a winner from it builds the same way.

| Part | Time | Filament | Checks |
|---|---|---|---|
| `breaker_o8_b1p6_d2p5_h12_p10_round` | 89 min | 24.0 g | ok |

- 12 x 8 openings (61.4% of the box's open bottom), 77 pins 9.6 mm apart, tops 17.4 mm up the box.
- Preview: `cad/out/breaker_o8_b1p6_d2p5_h12_p10_round_preview.png`. Sliced file: `cad/out/slice/breaker_o8_b1p6_d2p5_h12_p10_round.gcode.3mf` (local, not committed).
- No printability flags.

**Bench demo clump (a suggestion to the team).** Stir rice, quinoa and a few pasta tubes with a little sugar water (a water-soluble binder) and some torn leaf bits, press it into a ball about 30 mm across and let it set for a few minutes. Put it on the breaker layer, run the shake with the spray on, and film it side-on: it should come apart on the pins, the leaf bits should stay on the breaker, and the grains should sort on the trays below. The binder dissolves in the spray, standing in for the ethanol film. How strong it is next to a real Malaise clump is an assumption.

Checks: valid single solid, watertight mesh, fits the bed. A tower needs one holder box per level plus the catch pan; the holder (`frame_holder`) isn't repeated here.

<!-- hand-written from here on: winners.py keeps it -->
## Print queue (13:35, Oct 25)

One P1S. **What's on the printer now isn't known to this session.** It's on the main session's list of questions for the user (PLAN.md, decision 2). Update this table when someone says.

| Order | Part | Time | Status | Why |
|---|---|---|---|---|
| 1 | `breaker_o11p3_b1p6_d3p1_h8_p8p5_round` | 57 min, 19.6 g | sliced; **send by 13:50** (PLAN.md, 13:30) | the optimizer's **verified** malaise #1, B-164f355a (robust 0.630 over all seeds, 94% of fresh clumps freed) |
| 2 | `sieve_insert_5mm_across` | 47 min | ready to print, sliced | the fix for quinoa and chia stuck on the 5 mm tray; drops into today's holder boxes |
| 3 | `breaker_o8_b1p6_d2p5_h12_p10_round` | 89 min | ready to print, sliced | the CAD default breaker: 34% freed without the buzz, 84% with it |
| 4 | `sieve_insert_2mm_across` | 65 min | ready to print, sliced | the same fix on 2 mm |
| 5 | `seesaw_holder`, one per level | 60 min each | ready to print, sliced | centre pivot pins, no tab: levels hang about 55 mm apart at ±10° instead of 85–110 |
| 6 | `seesaw_catch_pan` | 125 min | ready to print, sliced | deeper pan with an inward lip: grains bounced out over the ends |
| - | winner plates 1–3 (above) | 124–152 min | sliced | translation-stroke winners from before the seesaw; superseded |

**Don't print** B-31c4ea6d (`breaker_o12_b1p9_d2p8_h6_p9_round`). It led round 2 on one lucky seed and scores 0.42 on fresh clumps. B-32a7c82c (`breaker_o11p4_...`, built at 13:10) was the round-0 leader and is superseded too.

Item 1 sent at 13:50 is done by about 14:50. Item 2 right after it finishes by about 15:40, after the live demos start (15:30). Items 3–6 come after the demo.

## Optimizer's breaker (malaise study, EXPLORATORY): B-164f355a

The verified #1 in `sim/opt/LOG.md` (13:30): `breaker:open=11.3,bar=1.6,pin_d=3.1,pin_h=8,pitch=8.5,tip=round`, built by `cad/breaker_layer.py` with the same keys. The sim ranks designs; it isn't calibrated against bench counts, and the bond strengths and insect bodies are assumed.

| Part | Time | Filament | Checks |
|---|---|---|---|
| `breaker_o11p3_b1p6_d3p1_h8_p8p5_round` | 57 min | 19.6 g | ok |

- 40 round pins, 3.1 mm across and 8 mm tall; 11.3 mm openings, 68.9% open. No printability flags.
- **Stroke to set on the bench:** seesaw ±7°, 1.1 s per cycle, constant angular speed, with a 0.35 mm, 40 Hz buzz on top.
- **Why this one** (LOG.md verify table, robust score over all seeds):

  | Design | Robust score | Freed on fresh clumps |
  |---|---|---|
  | B-164f355a (this breaker) | 0.630 | 94% |
  | CAD default with the buzz | 0.452 | 84% |
  | no breaker | 0.229 | 48% |

  The cost is harder hits: peak-force p90 is about 250 mN against 34 mN with no breaker.
- **Sliced files** (local, not committed). Open either one in Bambu Studio and send it to the P1S from there:
  - `cad/out/slice/breaker_o11p3_b1p6_d3p1_h8_p8p5_round.gcode.3mf` in the main checkout;
  - the same part in this worktree as `cad/out/slice/malaise_win3_plate.gcode.3mf`.

## Seesaw parts (cad/seesaw_holder.py, cad/sieve_insert.py)

Built 12:30–12:40 for the per-level seesaw (docs/SYSTEM.md §3), sliced for the P1S with the default PLA process. All four are valid single solids, watertight, fit the bed, and print flat with no supports.

| Part | Time | Filament | What changed and why |
|---|---|---|---|
| `seesaw_holder` | 60 min | 41.6 g | The holder box with no +X tab and no finger notches. It has a pivot lug in the middle of each long wall, with a blind 6.2 mm hole at mid-height for a 6 mm pin from each post. With the tab gone, levels clear each other at about half the pitch, so **specimens drop about half as far** between levels. The clump session found those drops give the largest impact force. |
| `seesaw_catch_pan` | 125 min | 97.2 g | The bottom level. Its rim and pivot are the same as a box's, but the floor is 20 mm deeper (42 mm under the rim), and the rim has an inward lip (2 mm, 45° underside) that leaves exactly the 122 × 82 open bottom of the box above. Grains bounced out over the ends at 25°. |
| `sieve_insert_5mm_across` | 47 min | 21.2 g | 216 holes of 5 mm (was 150), 54% of the box's open bottom. The screen reaches the ledge, the border is a 45° ramp down to the screen, and the only ribs are two 45° ridges along Y (across the slide). There's no flat top for a grain to rest on, and nothing solid runs along X for it to ride. The label on the tab reads "5X". |
| `sieve_insert_2mm_across` | 65 min | 22.5 g | The same layout with 2 mm holes: 936 holes (was 726). |

The inserts drop into the old `frame_holder` too, so items 2 and 3 can be tested on today's rig before any new box is printed.

**Pitch (pivot to pivot) the seesaw holder needs:** about 42 mm at ±5°, 54 mm at ±10° and 65 mm at ±15°, with 5 mm left between neighbours (sim `rocking.py`, the same within 0.1 mm as the closed form). The 11:20 renders hung the levels 85 mm apart.

**Softer landings (the clump session's finding) beyond a shorter drop:**
- the 45° ramps and ridges turn a straight drop onto a solid strip into a glancing one;
- a TPU 95A copy of the inserts would be the soft landing. The P1S prints TPU without the AMS, but it needs the filament on hand and prints slower (an estimate: about twice as long). Not sliced.

In the sim: `inserts:5mm_across,2mm_across,pitch=55,holder=seesaw` (`sim/designs_holder.py` reads all of this from the CAD modules).

### Sim check: the old parts against the new (one seed, uncalibrated)

Both towers ran ±10°, 2 s per cycle, constant angular speed, neighbours in opposite phase. Each got the same 71 grains of all 10 kinds, 10 s after a 1 s settle, seed 1. Old: `inserts:5mm,2mm,pitch=85`. New: `inserts:5mm_across,2mm_across,pitch=55,holder=seesaw`. Grain counts left on the 5 mm tray:

| Grain (count) | Old: on 5 mm | New: on 5 mm | Old: in the catch | New: in the catch |
|---|---|---|---|---|
| quinoa (12) | **7** | **1** | 3 | 10 |
| chia (12) | 6 | 4 | 5 | 7 |
| couscous (10) | 0 | 1 | 8 | 8 |
| the 5 rice kinds (30) | 7 | 8 | 2 | 1 |
| pasta (4), chickpea (3) | 7 | 7 | 0 | 0 |

- **Small grains stuck on the 5 mm tray, all kinds but pasta and chickpea:** 20 of 64 on the old parts, 14 of 64 on the new. Most of the gain is quinoa. Chia still sticks (4 of 12): at ±10° it doesn't slide on plastic, ramps or not.
- **Gentler:** the largest contact overlap fell from 0.16 to 0.10 mm on the trays and from 0.054 to 0.016 mm between particles, a crude proxy for impact. The drop is 55 mm instead of 85, so the free-fall impact speed is about 1.0 m/s instead of 1.3 (√(2gh), in air), and the energy about 35% lower.
- **One seed only.** Seeds 2 and 3 were started and then stopped when the laptop ran low on memory. Treat this as a direction, not a number. Replays: `sim/out/runs/ab_old/view.html` and `ab_new/view.html` (local, `--rig bugsorter`).
