# Closed-loop colorimetric titrator — cheap home build

An automated titrator: a peristaltic pump adds titrant in small pulses, an RGB color sensor watches an indicator, and the host stops dosing the instant the color crosses your endpoint. ~$30, no cells, kitchen chemicals, and it's a true closed feedback loop you can watch run itself.

**Why this is the right first build:** the RGB sensor and the red/blue color metric are *exactly* what alamarBlue needs later (blue resazurin → pink resorufin). Once this loop works on vinegar and cabbage juice, `read_viability()` reuses the same `read_color()` with only a calibration change. The titrator is the dress rehearsal for the cell assay.

Files: `pico_titrator.py` (Pico firmware), `benchmate_titrator.py` (host loop + Benchmate bridge).

---

## What to buy (~$30 single-well; ~$110 for the full 6-well plate — see the purchasing list)

| Item | Pick | ~Price | Have it? |
|------|------|-------:|----------|
| Microcontroller | **Raspberry Pi Pico** (not an ESP32 — no WiFi needed, USB is fine) | $4 | Maybe |
| RGB color sensor | **TCS34725 breakout** — ×1 for a single-well test, **×6 for the 6-well plate** | $5 ea | No |
| I2C multiplexer | **TCA9548A** — only for the 6-well version (the 6 sensors share address 0x29) | $7 | No |
| Peristaltic pump | 12 V peristaltic pump + silicone tubing | $15 | From the earlier build |
| Pump driver | Logic-level N-MOSFET module (IRLZ44N) | $3 | Maybe |
| Power supply | 12 V 1–2 A adapter | $9 | Reuse a router/laptop brick |
| Breadboard + wires | small breadboard + jumpers | $5 | Yes |
| Vessel | **6-well culture plate** (or a clear vial for a quick 1-well test) | $0–12 | Bring from work |
| Mounting | tape + an optional foam-board jig + a cardboard box (no 3D printer) | $0–2 | Household |

**Why not the ESP32:** you only needed it for WiFi and pump pins. Here the laptop is right next to the rig over USB, so a $4 Pico does the job. (If you'd rather keep the ESP32 you already have, it works too — same logic, just over WiFi instead of serial.)

### Kitchen chemistry (all safe)
- **Acid:** white vinegar (acetic acid).
- **Base / titrant:** baking-soda or washing-soda solution.
- **Indicator:** red cabbage juice (boil chopped cabbage, keep the purple water — it sweeps pink→purple→blue/green with pH), or phenolphthalein from work (colorless→pink).
- Avoid household ammonia/bleach — the baking-soda route is gentler and just as good a demo.

---

## Wiring

The Pico runs on USB. The pump runs on 12 V through the MOSFET. **Tie all grounds together** (Pico GND, MOSFET source, 12 V supply ground).

| Pico pin | Connects to |
|----------|-------------|
| GP0 / GP1 | TCS34725 SDA / SCL  (VIN → 3V3, GND → GND) |
| GP15 | MOSFET gate (pump on 12 V through the MOSFET) |
| GP14 | TCS34725 LED pin (optional control; or tie the LED to 3V3) |
| GND | MOSFET source + 12 V supply ground |

A small magnetic stirrer (or a gentle manual swirl between pulses) helps the titrant mix before each reading.

---

## Mounting the sensors (no 3D printer needed)

Tape works fine — the only job of a mount is to hold each sensor still relative to its well.

- **Tape to the BOTTOM of the plate, not the lid.** The TCS34725's onboard LED then lights the liquid from below and you read the color reflected back (reflectance mode). Avoid the lid — in the real assay it collects condensation that ruins the optical path.
- **Block room light** — this matters more than perfect alignment. Put the whole plate-on-sensors assembly in a cardboard box (or wrap it). Bare taped sensors drift with ambient light; the onboard LED should dominate.
- **Use opaque tape** (black electrical/gaffer) around the *edges* of each breakout — never over the optical window or LED.
- **Don't move a sensor mid-run.** Per-well control calibration absorbs position differences, but not movement between the baseline read and the measurement. Tape it down and leave it.
- **Optional zero-cost jig:** cut 6 holes at ~39 mm spacing (the 2×3 well grid) in foam board or a box lid, drop the sensors in, set the plate on top — slightly more repeatable than bare tape.

## Scaling to the 6-well plate

One sensor per well, all taped to the bottom, wired to a **TCA9548A multiplexer** (all TCS34725s share I2C address 0x29, so the mux is what lets the Pico read each well in turn). Six wells = six conditions = a dose-response curve in one run. Reflectance from the bottom gives a relative red/blue ratio per well, which you calibrate against controls exactly as in the single-well case.

> Note: the current `pico_titrator.py` / `benchmate_titrator.py` read **one** sensor. Reading all six is a small addition — select the mux channel (write 1<<channel to address 0x70) before each `READ`. Ask and I'll add it.

---

## Set up in order

1. **Flash the Pico.** Install MicroPython (drag the UF2 onto the Pico in bootloader mode), open Thonny, save `pico_titrator.py` to the Pico **as `main.py`**. It runs on power-up.
2. **Talk to it.** `pip install pyserial`, set `BENCHMATE_TITRATOR_PORT` (e.g. `/dev/ttyACM0` or `COMx`), then `python benchmate_titrator.py read` — you should get live r,g,b,c numbers.
3. **Calibrate the pump.** Pulse a known amount into a measuring container and compute microliters per millisecond; set `BENCHMATE_UL_PER_MS`. (Default 1.5 is a placeholder.)
4. **Set the endpoint.** Put indicator + acid in the vessel, read the color, add a known excess of base by hand, read again — the two `rb` (red/blue ratio) values bracket your endpoint. Pick a target between them.
5. **Dry run first.** `BENCHMATE_TITRATOR_SIMULATE=1 python benchmate_titrator.py titrate --target 1.8` runs the whole loop against a modeled titration curve, no hardware.
6. **Real run.** `python benchmate_titrator.py titrate --target 1.8 --direction above --approve`. Watch it pulse, slow down near the endpoint, and stop. The dispensed volume is your result.

---

## How the loop works

`titrate()` runs: read color → if not past target, pulse titrant → wait to mix → read again. Far from the target it uses **coarse** pulses; once the metric is within `fine_band` of the target it switches to **fine** pulses, so it slows down and doesn't blow past the endpoint. It stops at the first crossing and reports the total dispensed volume. Every step is logged to `data/rig/titration-*.csv` (step, total_ms, volume_uL, metric) — a full titration curve.

**Tuning matters.** In simulation, coarse pulses that are large relative to the indicator's transition will overshoot; shrinking `--coarse-ms` / widening `fine_band` gives a clean approach (the tuned defaults land within ~3% of the true equivalence point in the model). Tune these to your pump and indicator on the first real run.

**Safety:** every pump pulse is self-terminating and capped in firmware; the host aborts if it dispenses past `MAX_TOTAL_MS` without finding an endpoint; and a real run requires `approve=True`.

---

## The bridge to alamarBlue (the end goal)

The titrator and the viability assay are the **same instrument**. `read_color()` returns a red/blue ratio; in titration it crosses a threshold, in alamarBlue it rises as live cells reduce the dye. `read_viability(live_rb, dead_rb)` (already in `benchmate_titrator.py`) maps the current ratio between a dead control (0%) and a live control (100%). So your path is:

1. Build and tune this titrator on kitchen chemistry — prove the pump, the sensor, the loop, and the Benchmate hookup with zero biology risk.
2. When you're back at the bench with cells, swap the chemistry for a drug + alamarBlue, recalibrate the two control readings, and the same rig reports viability.

Expose `titrate()` (and later `read_viability()`) as a tool in `co_scientist/tools.py`; the CSV in `data/rig/` is read by the agents like the Geneformer cache. A titration is the cleanest possible safe demonstration of Benchmate's design→act→measure loop.
