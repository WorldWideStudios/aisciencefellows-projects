# Print plan: malaise winners

Built 2026-10-25 13:34 from `sim/opt/winners_malaise.json`, sliced for the P1S (Bambu Studio's default process, PLA). Made by `cad/winners.py`.

**Caveat:** EXPLORATORY: the sim ranks designs; it isn't calibrated against bench counts. The clump is the grain surrogate (insect clumps don't pack yet); bond strengths and the 5 mN damage line are assumed. Winners are verified on fresh clumps, ranked by winner_score = min(robust seed 0, robust over all seeds).

## Winner 1: breaker

- Sim spec: `breaker:open=11.3,bar=1.6,pin_d=3.1,pin_h=8,pitch=8.5,tip=round,under=5mm+2mm,tower=85`
- Stroke to set on the Pi: profile seesaw, deg 7, period_s 1.1, shape constant_speed, vib_mm 0.35, vib_hz 40
- Tower preview: `cad/out/malaise_win1_preview.png`

| Part | Time | Filament | Checks |
|---|---|---|---|
| `malaise_win1_breaker_o11p3_b1p6_d3p1_h8_p8p5_round` | 57 min | 19.6 g | ok |
| **Total, one of each** | **57 min** | **19.6 g** | |

**One plate, ready to print:** 57 min, 19.6 g, all parts arranged on one P1S plate: `cad/out/slice/malaise_win1_plate.gcode.3mf` (local, not committed).

No printability flags.

## Winner 2: breaker

- Sim spec: `breaker:open=8.9,bar=1.2,pin_d=2,pin_h=7.6,pitch=11.8,tip=flat,under=5mm+2mm,tower=85`
- Stroke to set on the Pi: profile seesaw, deg 8, period_s 3.5, shape constant_speed, vib_mm 0.35, vib_hz 40
- Tower preview: `cad/out/malaise_win2_preview.png`

| Part | Time | Filament | Checks |
|---|---|---|---|
| `malaise_win2_breaker_o8p9_b1p2_d2_h7p6_p11p8_flat` | 61 min | 18.5 g | ok |
| **Total, one of each** | **61 min** | **18.5 g** | |

**One plate, ready to print:** 61 min, 18.5 g, all parts arranged on one P1S plate: `cad/out/slice/malaise_win2_plate.gcode.3mf` (local, not committed).

No printability flags.

## Winner 3: breaker

- Sim spec: `breaker:open=11.4,bar=2.3,pin_d=1.4,pin_h=6.8,pitch=8,tip=round,under=5mm+2mm,tower=85`
- Stroke to set on the Pi: profile seesaw, deg 12, period_s 2.5, shape constant_speed, vib_mm 0.35, vib_hz 40
- Tower preview: `cad/out/malaise_win3_preview.png`

| Part | Time | Filament | Checks |
|---|---|---|---|
| `malaise_win3_breaker_o11p4_b2p3_d1p4_h6p8_p8_round` | 48 min | 20.9 g | ok |
| **Total, one of each** | **48 min** | **20.9 g** | |

**One plate, ready to print:** 48 min, 20.9 g, all parts arranged on one P1S plate: `cad/out/slice/malaise_win3_plate.gcode.3mf` (local, not committed).

No printability flags.

Checks: valid single solid, watertight mesh, fits the bed. A tower needs one holder box per level plus the catch pan; the holder (`frame_holder`) isn't repeated here.
