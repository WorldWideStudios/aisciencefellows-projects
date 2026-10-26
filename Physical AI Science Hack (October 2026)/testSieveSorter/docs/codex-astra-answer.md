I would build interchangeable sieve inserts and treat gates as an experiment. “Coarse only” is a reasonable hackathon preference, but not a physical limit.

Ranked objections, highest build impact first:

1. Your cut points confuse specimen length with aperture size.

BioKEA advertises a 2–6 mm picking range without defining the dimension. That does not establish 2 mm and 6 mm sieve apertures. A long, narrow fly can pass end-first through a round hole; tall slots admit specimens according to their smallest accessible transverse dimension. Your 7 mm rice can pass a 6 mm opening easily. [BioKEA](https://biokea.ai/)

Likewise, “gap = 1.3 × target width” turns a nominal 2 mm threshold into 2.6 mm: a 30% change, not a harmless allowance. Label outputs by aperture retention until actual specimens establish their relationship to picker success.

2. The missing ingredient is controlled transport across the separator.

EntoSieve deliberately emerges from water and refills through its perforations. Horizontal motion in a shared bath does not reproduce that pumping action. Neither does adding 30–50 mm of water. Stationary jets might provide transport, but their direction, coverage and flow must be observed. [EntoSieve](https://pmc.ncbi.nlm.nih.gov/articles/PMC12225705/)

Reciprocal motion through an open fence also permits backflow. A downstream drop into an isolated collector is more consequential than rounded posts or a collection-pocket angle.

3. Neutral buoyancy undermines your settling and tilt arguments.

Preservation in ethanol does not establish density, wetting or trapped-air behavior after transfer to water. Some specimens sink; others float or snag. If nearly neutrally buoyant, gravity provides little settling or downhill transport.

Crossing 30 mm in a 10 s pause requires 3 mm/s settling speed. Measure it; do not assume it.

For simple submerged sliding, gravity overcomes friction only when tan(angle) exceeds the friction coefficient: 3–5 degrees corresponds to 0.052–0.087. There is no evidence your specimens meet that condition. Suspended specimens do not automatically follow a tilted floor downhill.

4. The opening-area comparison is underspecified.

Fence area is approximately length × open fraction × submerged slot height. A 150 mm fence, 50% open, with 6 mm-high slots gives 450 mm²; 30 mm-high slots give 2,250 mm². Gap width alone cannot establish area.

More importantly, transport depends on normal fluid velocity, specimen encounters, orientation and blockage. A floor has more distributed encounter opportunities, but “line versus area” does not prove gates impossible.

5. Purity alone cannot validate the pitch.

An outlet containing one correctly classified specimen can have 100% purity while recovering almost nothing. Report the full input-class/output-bin count matrix, per-class purity and recovery, total recovery, damage, time and manual interventions.

Your supplied size mix puts roughly 4,480–7,250 specimens below 1.5 mm. A 2 mm fine stage therefore faces thousands of specimens. Sparse cereal demonstrations cannot establish capacity.

Can fine gates work?

Yes, plausibly: use many short parallel channels feeding 2 mm throats, short constrictions widening downstream, directed flow, and a drop into separate collectors. Control slot height if thickness-only passage is unacceptable. These changes increase encounters and prevent return; they also add fabrication and clogging risks.

Smooth posts and downstream relief are sensible. They do not eliminate orientation bias or appendage entanglement. I would prototype a small gate coupon alongside a perforated coupon, rather than commit the entire sorter to either claim.

Firmware and motion:

Taking your firmware description as given, first calibrate travel with a ruler and elapsed time. For a commanded 20 mm move yielding 10 mm, double STEPS_PER_CM. Incorrect calibration corrupts both advertised stroke and speed; it is a credible contributor, not an established diagnosis.

The default 5 mm/s is 6.8 times below EntoSieve’s minimum reported 34 mm/s. The 50 mm/s cap overlaps its operating range but is about half its recommended maximum. More decisively, a vertical 20 mm stroke cannot emerge from 30–50 mm immersion. Raising speed cannot fix that geometry.

The smallest useful behavioral addition is a nonblocking pause after N complete cycles, adjustable from zero to 10 s. Compare equal elapsed time and equal cycle counts separately. It enables a meaningful experiment; it does not guarantee improvement. If abrupt reversals cause missed steps, acceleration ramps take priority.

Your 1.7 Hz slosh estimate is reasonable for an unobstructed 150 mm tank at 30 mm depth. However, “below resonance” is insufficient: sharp reversals excite harmonics and transients. With 20 mm endpoint separation, frequency is 0.125 Hz at default speed and 1.25 Hz at the cap. Observe fluid motion and specimen crossings.

What cereal gets wrong:

Quinoa can traverse a 2 mm slot edge-on because it is about 1 mm thick. Rice similarly demonstrates orientation, not insect body-length classification. Unknown pasta geometry prevents predefined expectations.

Food also absorbs liquid and changes dimensions. It lacks wings, articulated legs, hairs, fragile joints and insect-like wetting. It can expose leaks, jams and return flow; it cannot validate insect recovery, damage or flotation behavior.

My three-hour build:

First 30 minutes: verify actual motion, calibrate stroke/speed, measure openings, and film transport with jets on/off.

Next 75 minutes: reuse the actuator and enclosure; make two removable, thin perforated inserts over a sealed collector, coarse above fine. Prefer available smooth metal screens. Use 5 mm and 1.5 mm as provisional aperture classes, with replaceable inserts. Keep the deck level initially. Allocate at most $100 of the budget to inserts, seals and collectors, retaining $150 for missing hardware.

Final 75 minutes: compare continuous motion against burst/pause operation and a gentle manual drain/refill reference. Use counted, dimensioned feed, three repeats, and at least two loadings. Account for every retained, escaped and misplaced item.

Set provisional demonstration targets of ≥90% purity and recovery per class, ≥99% total recovery, and zero manual clearing during runs. Without preserved insects, the defensible result is “repeatable surrogate separation.” The real-sample, hands-off claim remains unvalidated.