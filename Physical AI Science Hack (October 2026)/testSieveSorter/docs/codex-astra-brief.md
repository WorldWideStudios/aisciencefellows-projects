# Brief for Codex Astra: red-team our BugSorter "gates" recommendation

You are reviewing a hackathon team's plan for a low-cost insect size sorter. Read-only: do not edit files. Be concrete, use numbers, and disagree wherever the physics or evidence says so. Plain text, no emojis, under ~1,000 words.

## The line we are building into (BioKEA, Berkeley)
Bags of preserved bulk insect samples in, barcoded 96-well plates out. Modules: (1) BugSorter: coarse size sorting; (2) BugDisperser: flotation spreads a size class on a tray; (3) BugPicker: vision-guided vacuum pick-and-place into 96-well plates; (4) enzyme dispenser; (5) incubator. The hack track is only the BugSorter. Track goal: "a sorter that pulls three clean size classes from the mix", working "on real, preserved samples, run after run". Hack budget: $250 BOM, two Bambu printers, a few hours.

Real samples: Malaise traps, mostly small flies, stored in 96% ethanol, 8,000-12,500 specimens per sample. Published size mix (two samples): <1.5 mm 56-58%, 1.5-3 mm 27-31%, 3-5 mm 8-12%, >5 mm 2.9-5.5%.

## Sources on BioKEA's current system
- Deck: BugSorter = "back-and-forth actuation plus water jets", "stacked 3D-printed sieve trays in an acrylic enclosure". Their earlier budget rebuild of EntoSieve "never sieved reliably enough for real samples". https://docs.google.com/presentation/d/1SxKytbrSBqIaxMuh4jCn2J_zIUmfZpnH/preview
- Firmware, https://github.com/BioKEA/BugSorter (fork of zlite/entosieve): M5Stack Core ESP32 + M5Stack stepper module (HR8825). Web app sets homing, top and bottom position, speed, run duration. One axis between "top" and "bottom" limit switches at constant speed (no acceleration profile, no dwell). Default 2 cm stroke at 0.5 cm/s, speed capped at 5 cm/s, run 15 s to 30 min, STEPS_PER_CM = 100 marked "Calibrate this". No jet/pump/valve control in firmware.
- The team was told today that the bench unit's motion is horizontal and the jets are stationary. This conflicts with the public firmware's vertical top/bottom design; unresolved.
- BugPicker, https://github.com/BioKEA/BugPicker: Opulo LumenPnP conversion, OpenPnP + OpenCV, single vacuum nozzle with pressure-confirmed pickup, 96-well at 9 mm pitch, tray.stl and screentray.stl. biokea.ai states a 2-6 mm picking range.
- EntoSieve paper, https://pmc.ncbi.nlm.nih.gov/articles/PMC12225705/ : vertical stroke in water, container fully emerges each oscillation (water drains down through holes, flushes back up on descent), 30-50 mm water over aluminium perforated plates (1.5/3/5 mm holes), 34-104 mm/s with max recommended, 92-99% efficiency, worst class 78% (floating leafhoppers; doubling time did not help), large specimens obstruct holes and entangle small ones, all transfers between meshes manual. The authors abandoned earlier "shakers and a rotating sieve" for a "much gentler" up-down stroke (no details).
- Elbrecht et al. 2021, PeerJ 9:e12177, https://pmc.ncbi.nlm.nih.gov/articles/PMC8500090 : 4 mm metal mesh fully immersed in 96% ethanol, "repeated light shaking and pauses of 10 s", about 15 min, clear two-fraction split, gentler than dry. Clumping was more common wet and was reduced by more mesh area, more ethanol and higher amplitude. Dry sieving broke legs and needed 2-3 h of electrostatic cleanup.

## The team's idea ("gates")
A tray with a large open holding area for big items and fixed-width openings ("gates") that small items pass as the tray moves back and forth horizontally. Cascaded coarse to fine, each chamber one size class. Reuses the existing horizontal motion with minimal BOM change.

## Our current recommendation (please attack it)
1. Gates are viable for the coarse cut only. They are not viable as the fine-cut mechanism: a fence is a line a specimen must be carried across, while a floor hole is an area it can settle into. A 150 mm fence with 1.5 mm gaps has about 450 mm2 of opening vs about 4,500 mm2 for a perforated plate, with no gravity assist.
2. Cut points come from the BugPicker's 2-6 mm range: classes <2 mm, 2-6 mm, >6 mm. Gates (~6 mm) on a tilted coarse deck; perforated floor at ~2 mm below it.
3. Run wet, 30-50 mm of liquid. In water a preserved fly is nearly neutrally buoyant, so it follows the water and floor friction barely matters.
4. Add a shake-pause duty cycle (a few gentle strokes, then ~10 s still so small specimens sink through the floor holes). This needs a dwell parameter in the firmware.
5. Tilt the deck 3-5 degrees so oversize migrates to a downhill pocket; a level cascade random-walks. Bias also packs oversize onto fences, so angle the fences so the cake slides to the pocket.
6. Gate geometry: smooth rounded vertical posts, no undercuts, wider on the exit side, gaps at least 1.3x target body width. Tall slots gate on one dimension, so they are more permissive than round holes.
7. Stay below the tray's slosh resonance (about 1.7-1.8 Hz for 150 mm long, 30 mm deep).
8. Benchmark: run the published EntoSieve settings on the same mix and score both with the paper's efficiency formula (100 - intruders x 100 / class count).
9. Value pitch: all three classes separated in one hands-off run with no manual mesh-to-mesh transfer, into removable chambers sized as the disperser's input.

## Test materials today
Rice, pasta and quinoa (no real insects). Quinoa is lens-shaped, about 2 mm across and 1 mm thick. Long-grain rice is about 7 x 2 x 1.7 mm. Pasta shape is unknown.

## Questions
1. Where is this recommendation wrong or overconfident? Rank your objections by how much they would change what the team builds today.
2. Is "gates only for the coarse cut" right, or is there a gate geometry or motion that makes gates work at ~2 mm?
3. Given the public firmware (constant speed, top/bottom positions, 5 cm/s cap), what is the smallest firmware change that most improves sorting? Is the 5 cm/s cap or the uncalibrated STEPS_PER_CM a likely cause of the "never sieved reliably" result?
4. What will rice, pasta and quinoa mislead the team about, compared with real flies?
5. If you had three hours and this kit, what would you build and how would you know it works?
