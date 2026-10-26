# Escalation ladder demo (printed toys, real deciders)

`python -m baebugs.ladder_demo` on magicstudio. 12 toys (6 California, 4 from outside California, 2 tiny fill-ins), steps sort → image → pick; a specimen stops at the first step that is not APPROVE. 18 step records in `ladder_mmr.jsonl` (MMR root `f088ee7b…`), statistics in `markov.json` (`stats_sha256` `310a7854…`, recomputed from the chain in `notebooks/tiers_ladder_markov.ipynb`), per-step snapshots with tier grids, object boxes and break boxes in `snapshots/`.

Ladder: FAMILY_Hymenoptera (CA only) → ORDER router (DAISY-BB-004 v4 weights) → local VLM qwen2.5vl:3b → Claude (no API key on this machine: reported UNAVAILABLE, escalated) → human (nobody at the bench: HOLD, queued).

What it showed, read honestly:
- **Novelty routing works.** The two most unusual specimens (aphid-like 1.5 mm, novelty 1.0; damselfly 29.9 mm, 0.985) skipped the taxon models; the aphid went straight to the human queue.
- **Pick verification by Merkle diff works.** After each pick the frame diff had exactly one break box where the toy was and no object left: APPROVE with no model involved.
- **Confidence alone is not a safe gate.** The ORDER router, trained on museum photos, was confidently wrong on toy renders: Bombyliidae → Hymenoptera (0.97), Largidae → Coleoptera, *Andrena* → Coleoptera, and those were approved. Toy renders are outside its training domain; rung 1 needs a domain check on the input (photo vs render) and calibrated confidence before it may decide.
- **The local VLM is not a usable decider yet.** qwen2.5vl:3b answered confidence 0.9 every time, mostly HOLD, sometimes echoing the prompt's placeholder as the label. It should advise, not decide, until it is calibrated.
- The FAMILY_Hymenoptera rung (NULL out of state) correctly never decided outside California.
