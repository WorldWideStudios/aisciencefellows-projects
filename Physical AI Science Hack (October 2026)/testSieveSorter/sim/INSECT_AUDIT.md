# Audit of `sim/insects.py` against what the BugSorter sorts

Physics session, 2026-10-25, from the agent swarm that also built GRAINS.md. Nothing here is applied: `insects.py` is unchanged, and its three kinds stay frozen for the optimizer's insect leaderboard. My arithmetic and fits are marked as such; every other number links to its source.

## Applied at 12:35: the real Malaise mix (proposal 1, first half)
- **New kinds in `insects.py`**: `insect_malaise` draws body length from a lognormal fitted to EntoSieve's pooled counts (median 1.274 mm, sigma 0.779, truncated to 0.3–20 mm), then picks the body plan given that length. The three old kinds and `PLANS` are byte-identical (checked: 300 specimens per kind, same hash).
- **Shares, 3,000 generated:** 56% under 1.5 mm (data 56–58%), 70 / 28 / 2.1% in the BugPicker classes (fit 71.0 / 26.6 / 2.4%), Diptera 68%, mites 6%, spiders 3%.
- **Stratified kinds** `insect_malaise_lt2` / `_2to6` / `_gt6` draw from the same fit cut to one class. Oversample the rare > 6 mm with them, then weight scores by `insects.MALAISE_SHARES`.
- **Presets:** `insects.MALAISE_MIX` (`insect_malaise=60`) and `insects.MALAISE_MIX_STRATIFIED` (24 / 24 / 12). They work in `--mix` and `--clump`, e.g. `--clump insect_malaise=40,leaf=1,twig=2,dirt=10,bond=medium`.
- **Use the stiff contacts** (`--dt 0.000125 --timeconst 0.00025`, as the seesaw tower runs already do). At dt 0.5 ms, 8 of 40 specimens passed through the trays in 1 s; at 0.125 ms none did (0.2 mm worst overlap).
- **Still ASSUMED:** the plan weights and per-plan sizes (they set shape, not size), the 0.3 mm floor, and legs at the radius floor below about 0.8 mm. Not done: the EntoSieve replication, liquid, per-taxon kinds.

## Summary

- **"We haven't modeled the bugs yet" is half true.** `insects.py` generates detailed rigid specimens in 3 lumped kinds and 8 body plans, with poses and damage. But every number in it is an assumption, nothing in it has been compared with a real specimen, and the sim has no liquid.
- **The size mix doesn't match real Malaise samples.** EntoSieve counted two real Malaise-trap samples ([Ascenzi et al. 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12225705/)). Compared with them, the optimizer's insect mix has too few small specimens and too many large ones:

  | Class | Optimizer's insect mix | EntoSieve's real samples |
  |---|---|---|
  | Under 1.5 mm | 23% | 56–58% |
  | Over 5 mm | 14% | 2.9–5.5% |
  | BugPicker classes: under 2 / 2–6 / over 6 mm | 36 / 55 / 9% | about 69–73 / 25–28 / 1.4–3.7% (my fit) |

  At the real shares, the same sorter would look about 87% pure in the 2–6 mm bin instead of 96% (worked example in 2.1).
- **The biggest open physics question.** The sim and the gate rules assume holes never cut body length, because specimens pass end-first. That assumption is why the optimizer concluded the insect classes are "capped by structure". EntoSieve's real result points the other way: round holes of 1.5, 3 and 5 mm sorted specimens into body-length classes at 92–99% efficiency, in water with a gentle up-and-down stroke. A sim replication of EntoSieve would settle it.
- **No liquid.** Under assumed specimen densities of 1.05–1.15 g/cm³, a specimen in water weighs only about 5–13% of its dry weight, against 31% for rice. At stroke speeds, drag is several times that net weight. A dry sim, or friction calibrated on grains, won't carry over to insects.
- **BENCH.md step 9 leads nowhere.** Insect rows in `bench/grain_dims.csv` are ignored: `grains.load_measured()` keeps only grain kinds, and `insects.py` reads no file.

## 1. What `insects.py` models today

**Contract.** Each specimen is one rigid body with no joints. The head, thorax and abdomen are ellipsoids, each leg is two capsules, antennae are capsules, and wings are thin ellipsoids. `dims` gives length, width and thickness from the body only, and `span` includes the appendages. The optimizer's insect study puts each specimen in a class by `dims["length"]`: under 2, 2–6 or over 6 mm (`optimize.py`).

**Kinds and body plans** (`PLANS`). The numbers in the right-hand columns are from my numpy-only audit, 600 specimens per plan.

| Kind | Plan | Weight in kind | Median L (mm), sigma, range | Under 2 / 2–6 / over 6 mm | Median width | Median span / L | Geoms | Leg capsules at the radius floor |
|---|---|---|---|---|---|---|---|---|
| compact | beetle | 0.65 | 2.8, 0.50, 1–15 | 0.26 / 0.68 / 0.07 | 1.53 | 1.8 | 17 | 22% |
| compact | mite | 0.35 | 0.7, 0.35, 0.3–2 | 1.00 / 0 / 0 | 0.52 | 1.8 | 18 | 85% |
| elongate | fly | 0.65 | 2.3, 0.50, 0.8–15 | 0.37 / 0.59 / 0.04 | 0.88 | 2.0 | 18 | 72% |
| elongate | wasp | 0.15 | 2.5, 0.55, 0.8–18 | 0.34 / 0.60 / 0.06 | 0.69 | 2.4 | 22 | 69% |
| elongate | ant | 0.20 | 3.5, 0.40, 1.5–15 | 0.07 / 0.82 / 0.10 | 0.91 | 1.9 | 19 | 45% |
| longleg | mosquito or midge | 0.30 | 3.5, 0.35, 1.5–9 | 0.04 / 0.91 / 0.05 | 0.76 | 3.7 | 18 | 89% |
| longleg | crane fly | 0.25 | 8.0, 0.35, 4–20 | 0 / 0.19 / 0.81 | 1.37 | 4.6 | 16 | 38% |
| longleg | spider | 0.45 | 2.2, 0.50, 0.8–12 | 0.44 / 0.54 / 0.03 | 1.01 | 2.4 | 20 | 47% |

- **Sizes.** Lengths are truncated lognormals, and the docstring says the medians come from textbook adult lengths, not a fit. The Srivathsan citations in the docstring are correct: 61.7% of specimens per trap fall in ten families, and Cecidomyiidae are about 20% of species per site ([Srivathsan et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10333119/)).
- **Shape.** Segment proportions are fixed fractions of L, with a uniform factor per plan and ±8% jitter. All assumed.
- **Pose.** Drawn once per specimen: splayed, folded (tucked, curled or trailing) or mixed. In the splayed pose the tibiae point 35–75° downward, so the specimen stands on rigid legs.
- **Damage**, drawn once at generation, all assumed:
  - per leg: missing 2–20% depending on the plan, broken at the knee 4%;
  - per antenna: missing 10%;
  - wings: both missing 5%, one side missing 8%;
  - beetles: elytra open 8%.
- **Material.**
  - Body density is `RHO = 1.05e-3` g/mm³, with no source.
  - Wing areal mass is `WING_AREAL = 4e-6` g/mm².
  - Leg and antenna radius is at least `LEG_R_MIN = 0.06` mm, with mass kept at the real value.
  - Wings are `WING_HT = 0.04` mm half-thick, so 0.08 mm thick, about 25 times the ~3 µm the docstring gives for real wings.
- **Stability limits.**
  - From the docstring: legs hitting at more than about 400 mm/s pass through 1 mm bars.
  - From the optimizer's insect round 0 (`sim/opt/LOG.md`): every insect run is flagged, because legs sink 0.4–1.25 mm into rods and gates whose clearance is about 0.05 mm. Insect runs cost about 3 times a grain run per step.
  - Today's glued mesh jams 17 specimens per run.

## 2. What is missing or weak

### 2.1 Size distribution not fitted to data
- **The data exists.** EntoSieve counted every specimen in two Malaise samples by body length, measured from the front of the head to the tip of the last tergite, which is the same definition as `insects.py` ([Ascenzi et al. 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12225705/), Sections 2.3 and 3.1):

  | Sample | Total | Under 1.5 mm | 1.5–3 mm | 3–5 mm | Over 5 mm |
  |---|---|---|---|---|---|
  | 1 | 10,276 | 5,721 | 2,753 | 1,239 | 563 |
  | 2 | 12,482 | 7,242 | 3,853 | 1,028 | 359 |

  Specimens over 30 mm (0.3–0.6%) were removed by hand.
- **One lognormal fits both samples well (my fit).** Median 1.33 mm with sigma 0.84, and median 1.30 mm with sigma 0.70. Caveat: the first bin covers 0–1.5 mm, so the tail below 1 mm is extrapolated. The fit puts 24–27% below 0.8 mm, which is the fly plan's minimum.
- **Why the mix matters for design.** Purity depends on how common each class is. Take 90% recovery of the 2–6 mm class with 5% of the small specimens leaking into its bin:
  - at the sim's 36/55/9 mix, purity is 0.965;
  - at roughly 71/27/2, it is 0.87.

  The sim overstates purity, and understates the load on the fine stage: about 8,000 under 2 mm per sample versus about 23 per run.

### 2.2 Three lumped kinds instead of the real taxa
- **Diptera are under-represented.** They are about 72% of BIOSCAN-5M's order-labelled records (3,675,317 of 5,134,987, my arithmetic from its Tables 2 and A5, [Gharaee et al. 2024](https://arxiv.org/abs/2406.12723)). Those specimens are mostly from Malaise traps ([BIOSCAN-30K card](https://docs.voxel51.com/dataset_zoo/datasets_hf/bioscan_30k.html)). In the study mix, Diptera are about 38%.
- **Mites (13.5%) and spiders (10.4%) are probably over-represented.** Malaise traps intercept flying insects. This is an assumption: check it against BIOSCAN's order counts or a real sample.
- **Missing taxa that EntoSieve names as failure modes:**
  - leafhoppers (Cicadellidae) floated, and were the main intruders in test 2, where the smallest class fell to 78.3%;
  - aphids and butterflies form a water-repellent film;
  - Ichneumonidae "pass through the mesh holes based on their body height rather than their length".

  Also missing (my assumption): thrips, psocids, moths and micro-Hymenoptera smaller than 0.8 mm.

### 2.3 Shape is assumed, and the passage claim contradicts EntoSieve
- **The ceiling comes from the assumptions.** With the generated population, the best single width cut misclassifies 15% at the 2 mm length boundary and 8% at 6 mm. A thickness cut misclassifies 13% and 7%. Those error rates come straight from the assumed proportions (`wf`, `tf`, `JIT`), so the optimizer's "structural ceiling" is assumption-driven.
- **EntoSieve says round holes do cut length.** In test 1, the 1.5 / 3 / 5 mm holes gave 95.6% / 97.6% / 98.4% / 100% per length class. In that gentle, wet, up-and-down regime, specimens apparently lie flat, so their outline as they lie, not their cross-section, decides passage.
- **What this affects.** It contradicts `gates-verdict.md`'s "a long, thin fly passes a 2 mm hole end-first" in practice, and the end-first rule in `passability.md`.
- **Lateral compression** (phorids, ichneumonids) only appears through jitter.

### 2.4 Wet and ethanol state
- **The sim is dry.** `sorter.py` has no buoyancy and no drag, and `spray.py` only models wetting from the jets.
- **Density is uncertain.**
  - Flying insects' overall density is 0.60–0.76 g/cm³, "about half" that of air-free body material ([Drake, Mirkovic & Steinbauer 2024](https://repository.library.noaa.gov/view/noaa/61003)).
  - Storage ethanol at 96% is about 0.81 g/cm³ ([alcoholometric table](https://www.canada.ca/en/revenue-agency/services/tax/technical-information/excise-duty/tables-alcoholometry/canadian-alcoholometric-laboratory-table-1996.html); I didn't re-check the row).
  - Specimens sink in 96% ethanol (Elbrecht sieved there), but some float in water (EntoSieve).
- **My estimates** (an equivalent sphere with Schiller–Naumann drag; real specimens with legs and wings settle slower):
  - At an assumed specimen density of 1.05–1.15, the net weight in water is 4.8–13% of dry weight, and 23–30% in ethanol. For the grains: quinoa 17%, chickpea 23%, rice and pasta 31%.
  - Upper-bound settling speeds in water are 6–64 mm/s, and 21–112 mm/s in 96% ethanol.
  - For a 2.3 mm fly at 50 mm/s relative speed, drag is about 5 times its net weight in water.
- **Clumping and entanglement aren't modelled:**
  - clumping is more common wet, and is reduced by more mesh area, more ethanol and a higher amplitude ([Elbrecht et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8500090));
  - large specimens entangle small ones, and air bubbles make it worse (EntoSieve).

### 2.5 Specimen features the sim can't represent
- **Rigid legs.** They can't fold, so the sim over-predicts snagging. In reality, brittle ethanol-preserved legs break instead (EntoSieve; Elbrecht).
- **Setae and hairs**, which cause Velcro-like tangling.
- **Real wings:** 3 µm membranes that crumple or stick to surfaces.
- **Floating.** There is no free surface and no trapped air.
- **Soft bodies** (aphids).
- **Plumose antennae and ovipositors.**
- **Detached legs, wings and debris.** Elbrecht notes that tissue from large specimens ends up in the small fractions.
- **Clamped legs.** 45–89% of thin capsules are wider than they should be, which would also over-state drag once a liquid is added.

### 2.6 Scale and calibration
- **Too few specimens.** About 65 per run against 8,370–12,482 per real sample, so the sim can't show the fine stage clogging. At 16–22 geoms per specimen, it can't scale up either.
- **No real specimen** has been measured or run. The damage, clumping and float outputs don't exist.

## 3. Proposals, most valuable for the sorter design first

| # | Proposal | Effort | Data needed |
|---|---|---|---|
| 1 | Data-fitted mix: draw L from the EntoSieve fit, then the plan given L; lower the minimum L; weight the scores by real class shares | 2–4 h | Public: EntoSieve counts, Srivathsan, BIOSCAN orders |
| 2 | EntoSieve replication benchmark | about 1 day | Public: EntoSieve hole sizes, 1 mm plates, 34–104 mm/s vertical stroke, Table 3 |
| 3 | Liquid medium, off by default | 0.5–1 day, plus 2 h of bench work | Float/sink density series per taxon; settling-speed video in water and ethanol |
| 4 | Measured-specimen loader plus one counted bench sort | 0.5 day of code, 1–2 days of bench work | 30 specimens per taxon measured in ethanol (L, W, T, span, mass, pose); a count matrix by length class and taxon |
| 5 | Per-taxon kinds (10–12) | 1–2 days | Per-family dimensions (BIOSCAN-5M areas plus own photos); float behaviour |
| 6 | Damage, clumping and load metrics | 0.5–1 day | Bench damage scores, clump counts |

1. **Fit the size mix to data.**
   - Add a new mix or sampler and leave the 3 kinds untouched. Draw L from the fitted lognormal (median 1.3 mm, sigma 0.70–0.84), then pick the plan with P(plan | L) ∝ weight × that plan's lognormal at L. Reweight Diptera to about 70%.
   - Lower the fly and wasp minimum L to about 0.4 mm (an assumption), and add microwasps.
   - Run with stratified counts (oversample the over-6 mm class), but compute purity and recovery weighted by the real class shares.
   - Value: it fixes the class prevalences that purity, contamination and the fine-stage load depend on.

2. **Replicate EntoSieve in the sim.**
   - Build single 1 mm plates with 1.5, 3 and 5 mm holes. Start with square holes of equal area using the existing `inserts`, then convex-mesh round holes.
   - Use a vertical stroke and proposal 1's mix, and compare with Table 3, test 1: 95.6 / 97.6 / 98.4 / 100%.
   - Run it dry first, then with proposal 3.
   - Value: it decides whether the length classes are sortable. If they are, the "insects are capped by structure" finding and the end-first rule in gatecalc have to change.

3. **Add a liquid medium, off by default.**
   - Buoyancy: per particle body, `gravcomp = rho_liquid / rho_specimen`. MuJoCo documents values above 1 as a "buoyancy effect" ([XML reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#body-gravcomp)). `sorter.py:291-292` writes the tray's acceleration into `opt.gravity`, so I expect `gravcomp` to also give the pseudo-buoyancy of a liquid moving with the tray. That's my inference: check it with a 1 s test.
   - Drag: `<option density= viscosity=>` with `fluidshape="ellipsoid"` (added mass, drag and lift; [fluid docs](https://mujoco.readthedocs.io/en/stable/computation/fluid.html)). The model computes forces against still liquid, which here means a bath with no slosh and no drain-through flow.
   - Values in mm, g and s: water 1e-3 g/mm³ and 1e-3 g/(mm·s); 96% ethanol about 0.81e-3 g/mm³, with a viscosity of about 1.2e-3 assumed from handbooks.
   - Bench data: float or sink each taxon in graded ethanol–water mixtures, plus salt solutions above 1.0. Film the settling speed, which `gates-verdict.md` item 7 already asks for.
   - Value: the sorter runs wet, and this is where insects differ most from grains.

4. **Calibrate against real specimens.**
   - Add `insects.load_measured()`, or a new `bench/specimen_dims.csv` with columns for taxon, L, W, T, span, mass, legs and wings state, float/sink, and liquid.
   - From it, fit each plan's lognormal and its W/L and T/L ratios, replacing the assumed `wf` and `tf`.
   - Run one counted sort of a measured subsample of about 200 specimens through the printed trays, then fit `calibrate.py` and check it on a held-out run.
   - The BugPicker's OpenCV camera could log the size of every 2–6 mm specimen it handles. That's my suggestion, not checked against its code.
   - Start the measuring now: it's the slowest part.

5. **Per-taxon kinds.** Keep the old kinds and add new ones:
   - gall midges, fungus gnats and sciarids (small `_mosquito`);
   - chironomids and ceratopogonids;
   - phorids (laterally compressed `_fly`);
   - other flies;
   - micro-Hymenoptera;
   - ichneumonids (slender, ovipositor, pass by height);
   - leafhoppers (wedge-shaped, a floater flag);
   - aphids (sticky);
   - moths (broad wings, floater);
   - beetles, ants, spiders and crane flies as now.

   BIOSCAN-5M has a pixel area for each of 5M specimens. Its stated scale, 0.1554 mm per pixel on 1024×768 images, looks coarse for single-specimen images, so check it against a known specimen first.

6. **Damage, clumping and load metrics.**
   - Damage: tally contact impulses on legs, antennae and wings above a threshold, scored like EntoSieve (broken appendage 0.4, missing 0.6). EntoSieve found no significant effect of sieving on damage (p = 0.869), but a significant taxon effect (p = 0.019).
   - Clumping: count insect–insect contacts that persist.
   - Load: a legless ellipsoid stand-in for the under-1.5 mm fraction, 500–2,000 of them, to see whether the floor blinds.
   - Detached legs and wings as their own particles.

## 4. Suggestions for the frozen kinds (no changes made)
- Leave `rice`, `quinoa`, `chickpea` and `pasta` as they are. In water, their net weight is 2–6 times an insect's, so don't use grain-fitted friction to predict insect transport in liquid.
- For a buoyancy-dominated surrogate, add a new kind, for example polystyrene beads at about 1.05 g/cm³ (an assumption: check the datasheet).
- Also freeze `insect_compact`, `insect_elongate`, `insect_longleg` and `PLANS`, because `sim/opt/leaderboard_insects.md` and `winners_insects.json` depend on them. Add new kinds or mixes instead.

## 5. What was run
- **No MuJoCo runs.** Free memory was 1.01 GB, under the 1.5 GB floor.
- Three small numpy-only scripts: the generator statistics (600 specimens per plan), the lognormal fit to EntoSieve's counts, and the settling estimates. They stayed in the session scratchpad.
- No repo files were edited by the audit.

**Assumptions** (not from the literature): specimen density 1.05–1.15 g/cm³, ethanol viscosity, which taxa Malaise traps rarely catch, the polystyrene density, the lower minimum L, and how `gravcomp` interacts with the tray-frame gravity.

**Sources:**
- [Ascenzi et al. 2025, EntoSieve](https://pmc.ncbi.nlm.nih.gov/articles/PMC12225705/) ([full text](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12225705/fullTextXML))
- [Elbrecht et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8500090)
- [Srivathsan et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10333119/)
- [Gharaee et al. 2024, BIOSCAN-5M](https://arxiv.org/abs/2406.12723)
- [Drake et al. 2024](https://repository.library.noaa.gov/view/noaa/61003)
- [MuJoCo fluid docs](https://mujoco.readthedocs.io/en/stable/computation/fluid.html) and [XML reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#body-gravcomp)
- [Canadian alcoholometric table](https://www.canada.ca/en/revenue-agency/services/tax/technical-information/excise-duty/tables-alcoholometry/canadian-alcoholometric-laboratory-table-1996.html)
