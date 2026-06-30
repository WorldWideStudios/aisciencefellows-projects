# Starter protocol — alamarBlue color calibration + closed-loop rehearsal

A first home session for the colorimetric rig, using the real dye with **no cells**. It proves the optics, the red/blue metric, the pump, and the closed loop — and sets the calibration you'll reuse when cells arrive.

**You have:** alamarBlue (resazurin), 25 mL.
**Reductant (cell stand-in):** **ascorbic acid (vitamin C)** — the safe default. Sodium dithionite (sodium hydrosulfite) is an optional faster alternative; see the note at the end.
**The idea:** a reductant chemically converts resazurin (blue) → resorufin (pink), standing in for what live cells do. So you can make the exact blue→pink color change the assay relies on, and calibrate the sensor against it.

---

## Safety

Ascorbic acid is food-grade and low-hazard — basic care only: don't eat lab stock, rinse spills, wear gloves if you like. The real cautions here are minor:

- alamarBlue is **light-sensitive** — keep stock foil-wrapped / refrigerated.
- If you use the optional dithionite instead, that one needs real care (see the end).

---

## Solutions to prepare

1. **alamarBlue working solution.** Dilute stock ~**1:10** in water or PBS (e.g., 1 mL stock + 9 mL water) to a clear, readable blue. Too dark saturates the sensor; too pale gives weak signal — adjust.
2. **Ascorbic acid solution (make fresh).** Dissolve ascorbic acid in water at roughly **10–20 mg/mL** (a crushed vitamin C tablet in a few mL works; pure powder is cleaner). If you have **sodium ascorbate**, use that — it's less acidic and gentler on the color.

---

## Part A — Make the two standards and calibrate the sensor

1. Pipette **2–3 mL** of alamarBlue working solution into a well (or vial) on the taped-down sensor, inside the light-blocking box. This is the **blue / oxidized** standard.
2. With the rig running, read it: `python benchmate_titrator.py read`. Note the `rb` (red/blue) value — your **0% reduced** point.
3. In a **separate** 2–3 mL aliquot, add the ascorbic acid solution and mix. It turns **pink** over a few minutes (gentle warmth — a 37 °C bath or warm water — speeds it). Add a bit more if it's slow; stop once it's a clear pink. This is the **reduced** standard.
   - Ascorbic acid rarely over-reduces, so the pink is stable. If the pink looks weak/muddy, the solution may be too acidic — switch to sodium ascorbate, buffer with a pinch of baking soda, or dilute the alamarBlue in PBS.
4. Read the pink standard. Its `rb` value is your **100% reduced** point.
5. Set the calibration for `read_viability()`:
   ```bash
   export BENCHMATE_LIVE_INDEX=<rb of the pink/reduced standard>   # 100%
   export BENCHMATE_DEAD_INDEX=<rb of the blue/oxidized standard>  # 0%
   ```
   (In the real assay later, "reduced/pink" = live metabolizing cells, "blue" = dead/no cells — same calibration, real biology.)

---

## Part B — Closed-loop rehearsal (the satisfying part)

Drive the blue→pink change *with the pump*, watching the loop find its target.

1. Put **2–3 mL** of fresh alamarBlue working solution in the well (blue).
2. Load the **ascorbic acid solution** into the pump line (this is your "titrant").
3. Pick a target `rb` partway between your two standards, then run:
   ```bash
   python benchmate_titrator.py titrate --target <mid rb> --direction above --approve
   ```
4. Watch it pulse reductant, read the color, slow as it nears pink, and stop. The logged CSV in `data/rig/` is your blue→pink curve.
   - Because ascorbic acid reacts **slowly**, give the color time to develop before each read — increase the loop's settle time (raise `SETTLE_S` in `benchmate_titrator.py`, e.g. to 10–20 s, or warm the sample). If pink develops only after the loop stops, lengthen settle further.

---

## Part C (optional) — Phenolphthalein acid-base titration

A second, independent loop test on classic chemistry:

1. Diluted vinegar (~1:10) + a few drops of phenolphthalein in the well (colorless).
2. Baking-soda solution (~1 tsp/cup) in the pump line.
3. `titrate --target <rb of the pink endpoint> --direction above --approve` → watch colorless snap to pink.

---

## What this gives you

- A **calibrated sensor** on the actual dye and the actual blue→pink axis you'll use with cells — the real value of doing it now.
- A **proven closed loop**: pump → read → decide → stop, logged to `data/rig/` for Benchmate to ingest like the Geneformer cache.
- A clean transition: with cells, the "solution in the well" becomes cells + medium + alamarBlue; you re-read your dead/live controls to refresh the calibration, and the same rig reports viability. Nothing else changes.

## Quick troubleshooting

- **Slow/no color change:** ascorbic acid solution may be stale — make it fresh; add a little more; warm gently.
- **Weak or muddy pink:** too acidic — use sodium ascorbate, buffer slightly, or dilute alamarBlue in PBS.
- **Readings drift:** stray light — close up the box; don't move the sensor mid-run.
- **Weak/over-saturated signal:** re-dilute the alamarBlue working solution.

---

## Optional faster alternative — sodium dithionite (sodium hydrosulfite)

If you want a near-instant reduction, dithionite works in seconds — but it needs real care, so ascorbic acid is the better default:

- **Gloves + eye protection, ventilated area.** Keep the dry powder **sealed, away from moisture and heat** (it can self-heat and release SO₂). **Never mix with acid.** Solutions oxidize within ~1 hour — make small amounts fresh. Dispose per your institution's rules.
- Use a dilute solution (~1 mg/mL) and add **dropwise until pink, then stop** — excess over-reduces the pink resorufin to **colorless** dihydroresorufin. In the closed-loop titration it overshoots easily, so use small pulses (lower `--coarse-ms`).
