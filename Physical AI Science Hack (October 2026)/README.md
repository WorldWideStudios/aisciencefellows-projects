# Physical AI Science Hack — October 2026

Team projects from the Physical AI Science Hack (October 24–25, 2026, Studio 45, San Francisco):
six teams, 24 hours, real lab problems. Tracks included BioKEA's insect-sorting challenge and
lab automation on the Opentrons Flex.

Each folder is a **point-in-time snapshot** of the team's project repository (its `.git`
history is stripped, so these are frozen copies, not live submodules). For the latest version
of any project, follow the repo link. Pitch decks live in [`slides/`](./slides); pitch videos
are on the [Worldwide Studios YouTube channel](https://www.youtube.com/@worldwide-studios-community).

## Teams

| Team | Members | Project | Snapshot | Deck | Video | Repo |
|------|---------|---------|----------|------|-------|------|
| Lab Sentry | Simon Coelho, YM Liaw, Saee Pangarkar, Barmak Modrek, Daniel Betz | A live digital twin of the Opentrons Flex deck that blocks a run until the physical deck matches the protocol, and renders auto-labeled synthetic scenes to train its YOLO models. Judges' shout-out. | — (repo unavailable) | [PDF](./slides/01-lab-sentry.pdf) | [YouTube](https://youtu.be/m9rgV-Us-q0) | [GitHub](https://github.com/simoncoelho/lab-sentry) |
| BaeBugs | Andrew Tran, Wei Wang, Byron P. Lee | A vision-to-sieve insect sorting lane with two independent sizers, a digital-twin check before the arm moves, and a hash-chained provenance log. | [baebugs](./baebugs) | [PDF](./slides/02-bay-bugs.pdf) | [YouTube](https://youtu.be/ZAkk5aXsPaE) | [GitHub](https://github.com/biobitworks/baebugs) |
| BugSorter 2.1 | Aufstin Filiko, Forum Shah | Parametric CadQuery sieves, gates and trays, simulated in MuJoCo before printing — 8,200+ simulations scored 444 sieve designs. | [testSieveSorter](./testSieveSorter) | [PDF](./slides/03-bug-sorter.pdf) | [YouTube](https://youtu.be/6CoNUsIeYcc) | [GitHub](https://github.com/filiko/testSieveSorter) |
| Super Filter | Renaud Renault, Dale Herzog, Mohamed | Size-sorting insects with fluid physics in a variable-cross-section flow channel, plus an optical inspection stage with a vision classifier. Judges' shout-out. | — (no repo) | [PDF](./slides/04-super-filter.pdf) | [YouTube](https://youtu.be/2yJb_9YXpq8) | — |
| Athelas Apothecary (You Shall Not Pipette) | Stefanie Strasser, Erik Brinsmead, Ryan George | Browser plate design → checked plan → generated Flex protocol, run through the official Opentrons simulator before the robot can start. | [Hardwarehack](./Hardwarehack) | [PDF](./slides/05-athelas.pdf) | [YouTube](https://youtu.be/PsPZDdE04U8) | [GitHub](https://github.com/LamaSu/Hardwarehack) |
| RoboSwap | Philip Thomas, Neil Wilson, Apurva Patel, Maya Kanehara, Leo Epstein | A tool changer for benchtop liquid handling: an SO-101 arm locks onto a 3D-printed collar on an electronic pipette, with wrist-camera ChArUco calibration. Overall winner. | [robo_swap_101](./robo_swap_101) | [PDF](./slides/06-roboswap.pdf) | [YouTube](https://youtu.be/4s3JOTNk84c) | [GitHub](https://github.com/RoboDrop/robo_swap_101) |

## Notes on snapshots

- Snapshots were taken on October 26, 2026 from each repo's `main` branch:
  `biobitworks/baebugs@db58465`, `filiko/testSieveSorter@18953e3`,
  `LamaSu/Hardwarehack@fcaf7c0`, `RoboDrop/robo_swap_101@08b7b4c`.
- **Lab Sentry** — `simoncoelho/lab-sentry` returns 404 (private or not yet published), so there
  is no code snapshot for this team. The deck and video are included.
- **Super Filter** — the team did not share a repo. The deck and video are included.
- **BaeBugs** — most of the snapshot's size is `print/`: the STL files for the 91 test insects,
  32 filter hole types and printable labware.
