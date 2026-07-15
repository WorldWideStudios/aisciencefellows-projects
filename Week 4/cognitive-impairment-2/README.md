# cognitive-impairment-2# CVMD — Cognitive Variability Measurement Device

JULY 10th UPDATE
## 🔄 Demo #4 Update — July 11

**This week: the market answered.** Posted the same discovery question ("how do you tell a bad
session from being cooked — and have you ever done something about it?") in the two largest
aim-training communities (KovaaK's, Aimlabs Discords) and r/Archery.

**Findings:**
- **Gamers: acceptance culture.** "There's no such thing as a bad session" · "90% of your PB =
  you're fine." No tracking, no behavior change, no spend. Individuals who can afford a bad rep
  are ruled out as buyers.
- **Archers: vibes + workarounds.** Detection is subjective ("I just vibe it"), diagnosis defaults
  to form — but they showed real workarounds: pre-season baseline logs, "pack it in" rules when
  groups open up, and an escalation path that literally ends in *"ask a coach to look."* One
  admitted the misdiagnosis cost: "the more you try to fix the error, the worse it gets."
- **Conclusion:** readiness is run on feel everywhere; the buyer is the *accountable layer* —
  coaches — not the athlete.

**Built this week (in response):**
- **Team Readiness dashboard** (coach-facing: who scrims, who rests, tonight): (https://ready-ace-dashboard.lovable.app)


**Pipeline:** NYIT Center for Esports Medicine, NYC Collegiate Esports Circuit, program coach
(Lesley), r/Fencing coach thread (in mod queue). Three coach interviews targeted for next week.

DEMO VIDEO: https://www.loom.com/share/004a5d7c0aa94016a839e31b230c94d7


OLDER UPDATES
-------


June 20th Technical Update

# CVMD — Cognitive Variability Measurement Device

A $50 hardware device + companion web app that measures cognitive performance across five validated domains, and checks whether your wearable's readiness score actually predicts how your brain performs.

**Web app:** [brain-track-scan.lovable.app](https://brain-track-scan.lovable.app)
**Substack:** [sameershah770806.substack.com](https://substack.com/@sameershah770806)
**Follow along:** [@MANinREVman](https://x.com/MANinREVman)

---

## The problem

Wearables (Oura, Whoop, Apple Watch) generate a readiness score from sleep and HRV data. That score is a *prediction* about how your brain will perform — but it is never verified against actual cognitive behavior. There's no ground truth layer.

CVMD is that ground truth layer.

## What it measures — five domains

| Domain | Test | Platform | Status |
|---|---|---|---|
| Processing speed + consistency | Reaction time (visual + audio) | Hardware + app | Live |
| Sensory threshold | Critical Flicker Fusion (CFF) | Hardware | Live |
| Motor output | Grip strength | Hardware | Live |
| Motor coordination | Gait (phone accelerometer) | App (beta) | Live |
| Executive inhibition | Stroop interference | App | Live |

Each domain is backed by peer-reviewed literature — see `docs/research.md` for citations.

## Bill of materials (hardware unit)

| Part | Approx. cost | Notes |
|---|---|---|
| ELEGOO UNO R3 (Arduino-compatible) | $12 | Or genuine Arduino Uno |
| Sanwa OBSF-30 arcade buttons x2 | $16 | Green + red |
| LEDs (green, red) x2 | $1 | 5mm standard |
| 220Ω resistors x2 | $1 | For LEDs |
| Passive buzzer | $2 | For audio stimulus trials |
| FSR 402 force-sensitive resistor | $10 | Grip strength sensor |
| 10kΩ resistor | $0.10 | Voltage divider for FSR |
| Breadboard (full size) | $5 | Prototyping |
| Jumper wires (assorted) | $5 | M-M, some M-F |
| USB-A to USB-B cable | $6 | Arduino power/data |
| **Total** | **~$58** | |

Optional / in progress:
- Enclosure box + step-drill bit (~$15) — for a clean, replicable housing
- Custom PCB (via JLCPCB / Flux AI) — removes breadboard entirely, ~$15 for 5 boards

Full wiring diagram: `docs/wiring.md`

## Software

- `firmware/cvmd_combined.ino` — current Arduino sketch: reaction time test (visual + audio, 20 trials) + Critical Flicker Fusion test + grip strength test, all on one device, switchable via button press
- Web app (Lovable-built, source not in this repo): reaction time, gait (beta), Stroop test, cohort/group codes, daily reminder notifications, personal baseline tracking after 3+ sessions

## Data

18 self-test sessions logged across 6 distinct cognitive states (rested, sleep-deprived, jet-lagged, post-impairment, stressed). Full dataset: `data/sessions.csv`

**Headline finding:** standard deviation (consistency) is a more sensitive impairment marker than average reaction time — std dev varied 325% across sessions vs. 120% for average RT. HRV alone explains only ~10% of the variance in cognitive consistency (r = -0.31) — supporting the case for direct behavioral measurement rather than biometric proxies alone.

## Roadmap

- [ ] Finish second hardware unit, distribute to a fellow for n>1 hardware data
- [ ] Custom PCB design (Flux AI / JLCPCB) to remove breadboard dependency
- [ ] Calibrate grip sensor for a wider dynamic range (currently saturates at max reading)
- [ ] Standardize gait test protocol (phone position, surface, step count) with domain expert input
- [ ] Hardware vs. software latency calibration study (current estimated gap: ~124ms)

## Changelog

- **Week 6** — Added grip strength test, added Stroop interference test, app: cohort codes + daily reminders + personal baseline tracking
- **Week 5** — Added Critical Flicker Fusion test, added gait test (beta), web app launched
- **Week 4** — Reaction time hardware (visual + audio), initial self-test data collection began

---

*This repository is updated every two weeks as part of the Worldwide AI for Science Fellowship.*

New this week - June 20 Written Update:


Grip strength test — new hardware modality, FSR 402 sensor, peak + average force readings
Web app: cohort/group codes, daily notification reminders, personal baseline tracking (3+ sessions)
CFF baseline data — 5 readings, stable in 41-43Hz range across different states
4 new self-test sessions logged this week


In progress:


Second hardware unit — components built, finishing assembly before tomorrow's session
Hardware stability — acquired a drill + mat to enclose the device and clean up the breadboard layout
Researched NYC Makerspace as a resource for laser-cutting an enclosure and future PCB work

**Does your wearable's readiness score actually predict how your brain performs?**

CVMD is a $50 hardware device and browser-based app that measures real-time cognitive performance and correlates it with wearable health data.

🌐 **Try the web app (no hardware needed):** [brain-track-scan.lovable.app](https://brain-track-scan.lovable.app)

---

## OLD - MAY / JUNE 2026

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
