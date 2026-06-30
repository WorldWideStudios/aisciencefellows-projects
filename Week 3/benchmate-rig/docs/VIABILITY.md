# Resazurin (alamarBlue) viability rig — spec

A drug-dose + cell-viability node for Benchmate. The pump adds a drug; resazurin reports how many cells stay metabolically alive; Benchmate ingests the viability curve as evidence.

**Verbs:** `set_switch(ch,on)` · `dose(ch,sec)` (ch0 = drug, ch1 = dye) · `read_viability()`
Temperature was removed — cells sit at 37 °C in the incubator, so it's a constant, not a variable.

---

## The readout, in one paragraph

Live, metabolically active cells reduce **resazurin** (blue, absorbs ~600 nm) to **resorufin** (pink, absorbs ~570 nm). So as viability rises, absorbance at 570 nm goes **up** and at 600 nm goes **down**. The rig lights the sample with a 570 nm LED and a 600 nm LED in turn, reads transmitted light on one TSL2591 detector, and reports a ratiometric **index = A570 − A600** that increases with viability and is robust to path length and mild turbidity. Benchmate maps that index to **% viability** using two control readings. This measures *live metabolic activity*, not membrane lysis (that would be trypan blue / PI) — keep that in mind when interpreting a hypothesis test.

---

## What changes from the OD rig (what to order)

| Change | Detail |
|--------|--------|
| **+ Second LED** | Now two narrowband LEDs: **570 nm** (yellow-green) and **600 nm** (orange/amber). ~$1–2. Exact 570/600 is ideal; ±10 nm is workable since the LED is the wavelength selector. |
| **+ Second pump + driver** | Two channels now: ch0 = drug, ch1 = resazurin. Add one more 12 V peristaltic pump and one more MOSFET. ~$18. |
| **− DS18B20** | Dropped. Saves ~$5 and a pin. |
| **+ Reagent (consumable)** | Resazurin sodium salt or ready-to-use **alamarBlue / PrestoBlue** from a life-science supplier (Sigma-Aldrich, Thermo Fisher, Bio-Rad). This is a lab reagent, not an electronics part. |
| Keep | ESP32, TSL2591, relay (stir/aerate), 12 V supply, breadboard, tubing, vessel. |

Net hardware cost is about the same as the OD rig (~$50–70) — you trade the temp probe for a second LED and pump.

### Pins (matches benchmate_rig.ino)

| ESP32 pin | Connects to |
|-----------|-------------|
| GPIO 21 / 22 | TSL2591 SDA / SCL |
| GPIO 13 | 570 nm LED via 220 Ω |
| GPIO 12 | 600 nm LED via 220 Ω |
| GPIO 25 / 33 | MOSFET gate — pump ch0 (drug) / ch1 (dye) |
| GPIO 26 / 27 | Relay IN1 / IN2 (stir / aerate) |
| GND | tie ESP32, MOSFET source, relay, and 12 V supply grounds together |

Mount both LEDs and the detector in fixed geometry around the vessel — the LEDs share the same optical path through the sample. A matte black holder cuts stray light.

---

## Calibrate (once per cell line / assay)

1. **Blank** — fill the vessel with medium + resazurin, no cells (fully oxidized, blue). `POST /set_blank`. This sets A=0 at both wavelengths.
2. **Dead control (0 %)** — a no-cell or killed-cell well. CLI: `python -m benchmate_hardware dead` → stores `DEAD_INDEX`.
3. **Live control (100 %)** — an untreated, healthy well after the same dye-development time. CLI: `python -m benchmate_hardware live` → stores `LIVE_INDEX`.

`viability_percent(index)` then linearly maps any reading between those two points (clamped 0–100 %). Persist the two constants via `BENCHMATE_LIVE_INDEX` / `BENCHMATE_DEAD_INDEX` so they survive restarts.

---

## The assay

`viability_assay()` builds a one-vessel kinetic assay:

```
read_viability        # baseline
dose(drug)            # ch0
wait(incubation_h)    # e.g. 24 h drug exposure
dose(resazurin)       # ch1
loop develop_h:       # e.g. 3 h, every 20 min
    read_viability
```

The **plateau of viability_pct** as the dye develops is your endpoint. Run it from the CLI as a dry run, then for real with approval:

```bash
export BENCHMATE_RIG_URL=http://<rig-ip>
python -m benchmate_hardware assay --drug-sec 5 --incubation-h 24        # dry run
BENCHMATE_RIG_SIMULATE=0 python -m benchmate_hardware assay --drug-sec 5 --incubation-h 24 --approve
```

**One honest limitation:** one vessel measures **one condition**. A full dose-response curve (IC50) means either running the assay at several `drug_sec` values, or building a multi-vessel version (several vials, each with its own LED pair + dye line, multiplexed on the detector). The verb contract doesn't change — `run_experiment()` just gains more channels.

---

## How it feeds Benchmate

Each run writes `data/rig/<run_id>.csv` (`t_s, step, verb, a570, a600, index, viability_pct`). Expose `run_experiment` as a tool in `co_scientist/tools.py` next to `geneformer_neighbors`, and point the Reflection agent at `latest_run()["rows"]`. A hypothesis like *"perturbing gene X sensitizes cells to drug Y"* now gets checked against a real measured viability curve — the wet-lab analogue of the DepMap viability scores already in your stack.

Files: `benchmate_rig.ino` (firmware), `benchmate_hardware.py` (bridge).
