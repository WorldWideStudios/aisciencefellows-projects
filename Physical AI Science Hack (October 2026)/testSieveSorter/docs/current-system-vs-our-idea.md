# BioKEA's current BugSorter vs. our gates idea

Every claim about BioKEA's current system links to where it comes from. Where sources disagree, both are shown and the conflict is listed under [Check on the bench](#check-on-the-bench).

## Sources

| Source | Link | What it tells us |
|---|---|---|
| Track A deck and speaker notes | [Google Slides](https://docs.google.com/presentation/d/1SxKytbrSBqIaxMuh4jCn2J_zIUmfZpnH/preview) | The BugSorter is "back-and-forth actuation plus water jets" and a "size-sorting tower: stacked 3D-printed sieve trays in an acrylic enclosure". The earlier EntoSieve rebuild "never sieved reliably enough for real samples". Also the kit list and the open questions. |
| BugSorter firmware | [github.com/BioKEA/BugSorter](https://github.com/BioKEA/BugSorter), a fork of `zlite/entosieve`, last push 2026-08-13 | Electronics and control: see the table below. |
| BugPicker repo | [github.com/BioKEA/BugPicker](https://github.com/BioKEA/BugPicker) | The picker is a converted Opulo LumenPnP running OpenPnP, with OpenCV detection and one vacuum nozzle whose pickup is confirmed by a pressure sensor. It fills 96-well plates (9 mm pitch) and its designs include `Designs/tray.stl` and `Designs/screentray.stl`. |
| BioKEA website | [biokea.ai](https://biokea.ai) | BugPicker picking range: "2–6 mm". |
| Team meeting, 2026-10-24 | transcript (not published) | Bench unit's motion is "already horizontal", the jets can't be re-aimed, "the sample plate is up to us". |
| EntoSieve paper | [Ascenzi et al. 2025, PMC12225705](https://pmc.ncbi.nlm.nih.gov/articles/PMC12225705/) · [build files, OSF](https://osf.io/6t25n/) | The original published design and its numbers. This is not BioKEA's version. |
| Wet sieving precedent | [Elbrecht et al. 2021, PeerJ 9:e12177](https://pmc.ncbi.nlm.nih.gov/articles/PMC8500090) | Gentle shaking alternated with 10 s pauses, mesh fully immersed in 96% ethanol. |
| Picker precedent | [DiversityScanner, Wührl et al. 2022](https://www.biorxiv.org/content/10.1101/2021.05.17.444523v3.full) | A published picker robot. It takes specimens under 3 mm only and skips touching objects. |

## Side by side

| Aspect | Current BugSorter | Source | Our idea, built on top |
|---|---|---|---|
| Lineage | An upgrade of EntoSieve's electronics. The original used an Arduino and analog knobs. | [BugSorter README](https://github.com/BioKEA/BugSorter) | Keep the electronics and change the tray. |
| Controller | M5Stack Core ESP32 with an M5Stack stepper module (HR8825). It has a screen and buttons, plus a web app over WiFi. | [README](https://github.com/BioKEA/BugSorter) | Same hardware. |
| Web app controls | Homing, top and bottom position, speed, run duration, saving settings. A status JSON reports both limit switches, the positions and the completed cycles. | [README](https://github.com/BioKEA/BugSorter), [`src/main.cpp`](https://github.com/BioKEA/BugSorter/blob/main/src/main.cpp) | Add a **dwell** setting (strokes per burst, then a pause) for shake–pause. |
| Motion | One axis between "top" and "bottom" limit switches at **constant speed**: no acceleration ramp and no dwell. Default stroke 2 cm at 0.5 cm/s, speed capped at **5 cm/s**, runs 15 s to 30 min. `STEPS_PER_CM = 100` is a placeholder marked "Calibrate this". | [`src/main.cpp`](https://github.com/BioKEA/BugSorter/blob/main/src/main.cpp) | Stroke horizontally, with shake–pause, and tilt the deck 3–5°. |
| Motion, as described | "Back-and-forth actuation" | [deck](https://docs.google.com/presentation/d/1SxKytbrSBqIaxMuh4jCn2J_zIUmfZpnH/preview) | — |
| Motion, as told to the team | Horizontal | transcript | — |
| Water jets | In the deck. **No jet, pump or valve control in the public firmware.** The team says the jets are stationary. | [deck](https://docs.google.com/presentation/d/1SxKytbrSBqIaxMuh4jCn2J_zIUmfZpnH/preview), [`src/main.cpp`](https://github.com/BioKEA/BugSorter/blob/main/src/main.cpp), transcript | Fix the jets at build time, aimed at the gate fence and the oversize pocket. Pulse them. |
| Screens | Stacked 3D-printed sieve trays. Kit: woven mesh in 3 apertures, perforated plastic, hex-perforated steel, perforated steel in 2 hole sizes, a printed honeycomb. | [deck](https://docs.google.com/presentation/d/1SxKytbrSBqIaxMuh4jCn2J_zIUmfZpnH/preview) | A coarse **gate deck (~6 mm)** on top, with a **perforated floor (~2 mm)** below it. |
| Liquid | EntoSieve sorts in water. BugSorter has water jets. | [paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12225705/), [deck](https://docs.google.com/presentation/d/1SxKytbrSBqIaxMuh4jCn2J_zIUmfZpnH/preview) | Wet sort with 30–50 mm of liquid, one bath for the whole sorter. |
| Unloading | EntoSieve: every step is manual (lift out, tap the filter, rinse, flip sieves with clamps), taking 7–16 min per sample. | [paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12225705/) | Removable chambers: an oversize pocket, a 2–6 mm tray sized as the disperser's input, and a collector for under 2 mm. |
| Downstream size limit | BugPicker picks 2–6 mm. | [biokea.ai](https://biokea.ai) | The cut points are **2 mm and 6 mm**, which gives the deck's three classes: under 2 mm, 2–6 mm, over 6 mm. |
| Picker input | Specimens on a printed tray or screen tray. Pickup is confirmed by vacuum pressure, so the specimens are probably drained, not floating (our inference). | [BugPicker](https://github.com/BioKEA/BugPicker) | The 2–6 mm chamber should drain cleanly onto, or become, the picker's tray. |

## What the firmware tells us about "never sieved reliably"

This is our reading of the code, not something BioKEA has confirmed.

- **Speed cap:** the firmware stops at 5 cm/s. The EntoSieve authors run 3.4–10.4 cm/s and recommend the maximum, so BioKEA's rebuild may never reach the speed the original design depends on.
- **Steps-per-cm placeholder:** if `STEPS_PER_CM` was never calibrated for the lead screw and microstepping, the stroke and speed shown in the web app aren't what the machine actually does.
- **Speed profile:** constant speed with hard reversals is a square-wave velocity, with no ramp in either direction. EntoSieve's stroke also lifts the container fully out of the water every cycle, which is what drives water down through the holes and back up again. A short stroke (default 2 cm) may never do that.

## Check on the bench

1. Which firmware runs on the bench unit: this repo, or a newer version with jet control?
2. Which way does it stroke, vertical or horizontal? The public firmware's "top/bottom" naming and limit switches match the vertical EntoSieve.
3. Was `STEPS_PER_CM` calibrated? Measure: command a 2 cm stroke and check it with calipers.
4. What failed in the rebuild: sorting accuracy, clogging, damage, or the manual steps around it?
5. What does the BugDisperser accept, and does the picker take specimens drained or in liquid?
6. Is 2–6 mm the picker's real range today? What happens to the under-2 mm fraction, which is most of a Malaise sample?
