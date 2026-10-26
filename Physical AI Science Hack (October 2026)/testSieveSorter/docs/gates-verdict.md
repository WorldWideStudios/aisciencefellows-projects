# Is the "gates" sieve viable? Verdict and plan

Prepared 2026-10-24 for the BioKEA Track A hack. Three independent reads went into it:

- **Claude** (me)
- **Fable 5.1**, run at high effort and briefed with facts only
- **Codex Astra** (`gpt-6-astra`), asked to attack the combined recommendation. Its shell tool failed to start, so it worked from the brief only, without opening the local files.

Sources for every claim about BioKEA's current system are in [current-system-vs-our-idea.md](current-system-vs-our-idea.md). Codex's full answer is in [codex-astra-answer.md](codex-astra-answer.md).

## Verdict

**Gates are a reasonable experiment, not the backbone.** All three reviewers agree on that. The safest build reuses BioKEA's actuator with removable perforated inserts over sealed collectors, and adds a small gate coupon beside it for comparison.

- **Gates are most useful for the coarse cut**, where they stop big items from blocking the holes.
- **At the fine cut they are unproven and harder, but not ruled out.** Fable and I called them non-viable there; Codex showed that claim was overstated (see below).

### The one thing that decides whether horizontal motion works
**Water has to move through the openings in one direction.** EntoSieve gets this by lifting the sieve fully out of the water on every stroke: water drains down through the holes, carrying small specimens with it, then flushes back up on the way down ([paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12225705/)). Sliding a tray sideways in a shared bath doesn't do that. It just pushes water back and forth, and anything carried through an opening can be carried back on the return stroke.

**The fix is a drop into an isolated collector after every separator.** Once an item falls through, it can't come back. Codex ranked this above post shape or pocket angle, and it was my original "step down after each gate" idea.

### Physics that holds up
- **Slots let more through than holes.** A tall slot only limits one dimension; a round hole limits two. A fly lying flat passes a slot sideways, and so does quinoa (about 1 mm thick). The mentor's "with holes, both things go through" is backwards.
- **Opening area depends on slot height.** Area = fence length × open fraction × submerged slot height. A 150 mm fence that's 50% open has about 450 mm² with 6 mm tall slots and about 2,250 mm² with 30 mm tall slots (Codex). Taller slots give more area but sort by thickness only. Gap width alone doesn't settle the comparison with a perforated floor.
- **A level stroke doesn't transport anything.** Back-and-forth motion on a level tray just makes items wander. Something has to move them toward the openings: a one-way drop, directed jet flow, or an asymmetric stroke.
- **Sloshing frequency.** A 150 mm tray with 30 mm of water sloshes at about 1.7 Hz. Sharp reversals also excite higher harmonics, so watch the water rather than trusting the number.

### Claims that got weaker under review
- **Tilting.** Fable said to tilt the deck 3–5° so oversize moves downhill. Codex pointed out that sliding underwater only starts when tan(angle) exceeds the friction coefficient (0.05–0.09 at 3–5°), and nobody has measured that. Fable's own argument that specimens are nearly neutrally buoyant also means gravity barely pulls them downhill. Treat tilt as something to test, not a fix.
- **Shake, then pause.** Elbrecht et al. 2021 ([PeerJ 9:e12177](https://pmc.ncbi.nlm.nih.gov/articles/PMC8500090)) got a clear two-fraction split with "repeated light shaking and pauses of 10 s", but they did it in **96% ethanol** (density about 0.79), where insects sink readily. In water they sink slowly. Clearing 30 mm of water in a 10 s pause needs a settling speed of 3 mm/s, so **measure the settling speed** in your actual bath before relying on pauses.
- **Cut points.** BioKEA's "2–6 mm" picking range ([biokea.ai](https://biokea.ai)) doesn't say which dimension it means. A long, thin fly passes a 2 mm hole end-first, and 7 mm rice passes a 6 mm gate by its width. So **label outputs by the aperture that retained them** (for example "retained on 5 mm", "passed 1.5 mm"). Fix the real cut points once you know which specimens the picker actually handles. Drop the "gaps at least 1.3× body width" rule for sizing: it turns a 2 mm cut into 2.6 mm. Keep it only as a snag guard on the coarse gate.

## How to make the back-and-forth work, in priority order

1. **Check what's on the bench.** The public firmware ([BioKEA/BugSorter](https://github.com/BioKEA/BugSorter/blob/main/src/main.cpp)) runs one axis between "top" and "bottom" limit switches at constant speed, with no pause and a 5 cm/s cap. The team was told the motion is horizontal with water jets. Find out which firmware and which stroke direction the bench unit actually has.
2. **Calibrate the stroke.** Command a 20 mm move and measure it. If it moves 10 mm, double `STEPS_PER_CM`. A wrong value corrupts both the stroke and the speed shown in the web app.
3. **Check the stroke against the water depth, if the unit is vertical.** A 20 mm stroke can't lift the sieve out of 30–50 mm of water, and going faster won't fix that. The stroke has to exceed the water depth, as in the original EntoSieve.
4. **Add a one-way drop into an isolated collector** below every separator.
5. **Film the transport with the jets on and off.** The jets can't be re-aimed, so see what they actually move before building around them.
6. **Add a pause setting to the firmware.** The smallest useful change is a pause after N complete cycles, adjustable from 0 to 10 s, that doesn't freeze the web app (Codex). Compare against continuous motion at equal elapsed time and at equal cycle counts. If sharp reversals cause missed steps, add acceleration ramps first.
7. **Measure settling speed** in water (and in ethanol, if allowed) before tuning pause length.
8. **Gate coupon geometry:** many short parallel channels feeding the throat, short constrictions that widen downstream, smooth rounded posts with no undercuts, flow directed toward the throats, and a drop into a separate collector. Limit slot height if you don't want thickness-only sorting.

**Speed context:** at the default 5 mm/s over a 20 mm stroke the machine cycles at 0.125 Hz, and at the 50 mm/s cap at 1.25 Hz. The default is 6.8× slower than EntoSieve's minimum of 34 mm/s, and the cap is about half its recommended maximum of 104 mm/s.

### A third motion option already on the bench
Another session wired a Dayton TT25 tactile transducer ("puck", resonant at 40 Hz) to a Raspberry Pi to vibrate sieve trays. That's small-amplitude, high-frequency vibration, the regime of lab sieve shakers. It's good for keeping a perforated floor clear and breaking up clumps. It doesn't move items across gates. As of today it had no amplifier, so nothing could be felt. Note that Elbrecht found dry vibratory sieving broke legs off; whether wet vibration is gentle enough is untested.

## Three-hour build (Codex's plan, which I endorse)

1. **First 30 min:** verify the real motion, calibrate stroke and speed, measure the actual openings, and film transport with the jets on and off.
2. **Next 75 min:** reuse the actuator and enclosure. Make two removable, thin perforated inserts over a sealed collector, coarse above fine. Prefer the smooth metal screens from the kit. Use provisional apertures of 5 mm and 1.5 mm, replaceable. Keep the deck level at first. Spend at most $100 on inserts, seals and collectors, keeping $150 for missing hardware. Print a small gate coupon to run beside the perforated insert.
3. **Final 75 min:** compare continuous motion, shake–pause, and a gentle manual drain-and-refill as a reference. Use a counted, measured feed: three repeats and at least two loadings. Account for every item: retained, escaped and misplaced.

## Test materials: rice, pasta, quinoa

Measure 10 of each with calipers (width, thickness, length) before setting any cut point.
- **Quinoa vs. long-grain rice:** quinoa is lens-shaped, about 2 mm across and 1 mm thick. Long-grain rice is about 7 × 2 × 1.7 mm. They're the same width, so holes and square gates can't separate them. Slots sort by thickness, but quinoa also passes a 2 mm slot edge-on. Short-grain rice (about 2.5–3 mm wide) does separate from quinoa with a 2.3–2.5 mm hole. If quinoa and rice end up in the same bin, that comes from the materials, not the machine.
- **Pasta** behaves according to its shape. Tubes stay on top cleanly, spaghetti pieces slip through end-on, and orzo acts like rice.
- **In water,** rice and pasta release starch and soften, and quinoa can foam. Keep wet runs under 10–15 min and change the water each run, or test geometry dry.
- **What food can't tell you:** it has no wings, articulated legs or hairs, and it doesn't wet like an insect. It can expose leaks, jams and water flowing back; it can't validate insect recovery, damage or flotation. The honest claim from a food demo is **"repeatable surrogate separation."**

## Scoring and targets

- **Report the full count matrix:** what each input class was, and how many ended up in each output bin. Then give per-class purity, per-class recovery, total recovery, damage, time and manual interventions. Purity alone can mislead: a bin holding one correct item is 100% pure while recovering almost nothing.
- **Note on the paper's formula:** EntoSieve's "efficiency" (100 − intruders × 100 ÷ specimens in the class) is the share of each class that lands in the right bin. Report it alongside purity.
- **Targets for the demo (Codex):** at least 90% purity and 90% recovery per class, at least 99% total recovery, and no manual clearing during runs.
- **Capacity is a separate question.** A real Malaise sample puts about 4,500–7,250 specimens under 1.5 mm onto the fine stage. A few hundred food grains can't show that a stage handles that load.

## Failures and how to prevent them

| Failure | Prevention |
|---|---|
| Items carried back through an opening | Drop into an isolated collector after every separator |
| Legs and wings snag on posts | Smooth, rounded posts with no undercuts; never use woven mesh as a fence |
| Near-size items wedge | Constrictions that widen downstream; periodic reverse flush |
| Floaters (the paper's worst class) | Skim lip or surface weir |
| Clumps, and big specimens tangling small ones | Coarse insert first; pulse the jets; vibration on the fine floor (untested) |
| Material piles at the end walls or spills | Lower the water or move off the sloshing frequency; high walls |
| Specimens left in the machine between samples | Smooth inserts, rinse path, camera check that every bin is empty |

## Where the three reviewers agreed and disagreed

| Point | Claude | Fable 5.1 | Codex Astra |
|---|---|---|---|
| Gates for the coarse cut | yes | yes | reasonable, but treat as an experiment |
| Gates at the fine cut | not viable | not viable, about 10× slower | plausible with parallel channels and directed flow; prototype a coupon |
| Slots let more through than holes | yes | yes | yes |
| One-way drop after each separator | yes (first idea) | not raised | the most important change |
| Tilt 3–5° | adopted from Fable | required | unproven; specimens may not slide; start level |
| Specimens nearly neutrally buoyant in water | adopted from Fable | yes | not established; measure |
| Shake–pause | yes (Elbrecht) | yes | useful experiment; measure settling speed first |
| Cut points from picker's 2–6 mm range | yes | n/a | the range doesn't say which dimension; label outputs by aperture |
| Gaps at least 1.3× body width | Fable's rule | proposed | distorts sizing (2 mm becomes 2.6 mm) |
| Firmware | 5 cm/s cap; uncalibrated steps per cm | n/a | calibrate first; a 20 mm stroke can't clear 30–50 mm of water; add a non-freezing pause |
| Score with purity only | proposed | proposed | insufficient; report the full count matrix |
| "The horizontal setup never sieved reliably" | no: the deck says that of the EntoSieve rebuild | yes | n/a |
