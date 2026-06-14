# cognitive-impairment-2# CVMD — Cognitive Variability Measurement Device

**Does your wearable's readiness score actually predict how your brain performs?**

CVMD is a $50 hardware device and browser-based app that measures real-time cognitive performance and correlates it with wearable health data.

🌐 **Try the web app (no hardware needed):** [brain-track-scan.lovable.app](https://brain-track-scan.lovable.app)

---

## The Problem

Every morning wearables give you a readiness score. But nobody has validated whether that score predicts how your brain actually performs. CVMD is the ground truth instrument.

---

## Two Ways to Test

**Option 1 — Web App**
No hardware required. Works on any phone or laptop. Takes 3-4 minutes. Visual and audio stimulus trials. Reports average reaction time, standard deviation, and visual vs audio breakdown.

👉 [brain-track-scan.lovable.app](https://brain-track-scan.lovable.app)

**Option 2 — Hardware Device**
Arduino microcontroller, two arcade buttons, two LEDs, a passive buzzer, breadboard, jumper wires. No soldering required. ~$50 total. Microsecond precision with no browser latency.

---

## Key Findings So Far

- **Std dev > average speed.** Variability spread 242% across impairment states vs 76% for average RT. A tired brain doesn't just get slower — it gets unpredictable.
- **Visual faster than audio.** Consistent across all 5 subjects tested. ~380ms visual vs ~560ms audio on average.
- **Wearables miss intraday decline.** Same morning Oura scores, meaningfully different evening performance.
- **High readiness ≠ fast reactions.** Best biometric session of the week didn't produce best reaction times.

---

## Data

| Date | State | Readiness | HRV | Avg RT | Std Dev | Score |
|------|-------|-----------|-----|--------|---------|-------|
| May 29, 11:45pm | Midnight, sleep deprived | 65 | 89 | 323ms | 86ms | 19/20 |
| May 30, 9:43am | Morning, rested | 78 | 97 | 335ms | 124ms | 20/20 |
| May 30, 10:20am | First multimodal test | 78 | 97 | 568ms | 294ms | 20/20 |
| May 31, 9:04am | Low recovery state | — | — | 518ms | 233ms | 20/20 |
| Jun 2, 1:43pm | Disrupted sleep | 65 | 81 | 464ms | 138ms | 20/20 |
| Jun 2, 9:58pm | Evening, tired | 65 | 81 | 498ms | 196ms | 20/20 |
| Jun 4, 9:04am | Best biometrics | 84 | 103 | 449ms | 148ms | 20/20 |

---

## Hardware Wiring

| Component | Arduino Pin |
|-----------|------------|
| Green LED | Pin 8 |
| Red LED | Pin 4 |
| Buzzer | Pin 9 |
| Green button | Pin 7 |
| Red button | Pin 6 |
| All grounds | GND via breadboard rail |

---

## Parts List (~$50)

| Part | Cost |
|------|------|
| ELEGOO UNO R3 | ~$12 |
| Sanwa arcade buttons x2 | ~$16 |
| LEDs x2 | ~$1 |
| 220 ohm resistors x2 | ~$1 |
| Passive buzzer | ~$
