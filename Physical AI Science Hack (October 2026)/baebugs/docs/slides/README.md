# Submission deck (BioKEA Track A, 2026-10-25)

Source of the Claude Slides deck *BaeBugs: bags in, barcodes out, with custody*. One HTML file per slide in `slides/`, ordered by `deck.json`.
The live deck (private until shared) is a Claude Slides artifact; the demo clip on slide 3 is `docs/demo/baebugs_mvp_demo.mp4`.

Counts and the graph root on slides 1, 4, 9 and 10 are pinned to the pack at mvp-kg@caf982f (root `da9b3edbaa4b484707cca41d562506e5b9a40289830d38c6b627047b046cb855`); the pack regenerates on later commits. Slide 8 counts 24 custody breaks (8 result + 16 withheld bench photo) and slide 11 cites `print/labware/README.md`; both come from PR #12, so merge #12 before this.

Images reference uploaded assets (`/_blob/...`) and render only inside the artifact.

| # | slide | sha256 | sources |
|---|---|---|---|
| 1 | BaeBugs | `5d008def3dfe` | — |
| 2 | Look before you sieve, then prove what happened | `b7f57349544b` | — |
| 3 | Demo: the MVP graph in 45 seconds | `f59f1567ba94` | docs/demo/baebugs_mvp_demo.mp4 |
| 4 | One graph pack, read the same way by people and agents | `128d603ca4dd` | counts from site/mvp/mvp.json at mvp-kg@caf982f |
| 5 | Real California photos beat synthetic-only out of state | `92b3144fc1bf` | exploratory, silver teacher labels · daisy/results/DAISY-BB-002a/v2/DECISION.md |
| 6 | Per-taxon preprocessors route a bug to the model that knows it | `ee9117dd43ba` | exploratory, GBIF taxonomy as labels · daisy/DAISY-BB-004-prereg.md + amendments 1–4 |
| 7 | The order router transfers; the family model does not yet | `46dbf5d88e89` | test = AZ, NV, OR · daisy/results/DAISY-BB-004/v4/DECISION.md |
| 8 | 24 breaks recorded, not hidden. | `64e225aa1a9a` | 24 = 8 result + 16 withheld photo · impact_mmr.jsonl 96–103 · print/labware/merkle/breaks.json |
| 9 | Every file says who owns it and on what terms | `2631f2d72961` | docs/CLAIMS.md, kg/aok.json at mvp-kg@caf982f · not legal advice |
| 10 | Compare two labs top-down and find the one break point | `30c15b9fddcb` | docs/byo_compare_example.json · baebugs/compare.py |
| 11 | The printable bench kit stays well under $200 | `7f6bf1148a31` | print/labware/README.md, filament at 75% fill, 2026 retail estimates |
| 12 | Open science you can verify from your own browser | `fbd52e232237` | — |

## Speaker notes

**1. BaeBugs.** Open on the one-line pitch: a camera looks at a preserved sample before it is sieved, sizes every body in millimetres, plans the sieve stack, checks the plan against a digital twin of the bench, and hands each fraction to BugPicker. Everything it does is a hashed leaf in one graph, so anyone can check it or contest it.

**2. Look before you sieve, then prove what happened.** Six steps, each one logged as a hashed record. The point of step 3 is that nothing reaches the arm unless the twin says the plan is physically valid: the sieve exists and is free, the order is right, and the water stays above reserve. Step 6 plugs straight into BugPicker with no new protocol.

**3. Demo: the MVP graph in 45 seconds.** Captioned walkthrough of site/mvp. Things to point at while it plays: the custody banner at the top (recorded when it listed the 8 result breaks; the page now shows 24 with the withheld bench photos), the leaf search, the claim and licence on every leaf, and the Check this hash button, which recomputes the sha256 in the viewer's own browser and shows match.

**4. One graph pack, read the same way by people and agents.** Tabs on the page: graph, bugs, parts and 3D lab, bench twin, live GBIF California search, claims, prove and contest, agents. Every leaf carries a claim, a licence in context, a status, a file sha256 and a leaf hash. Anyone can contest a leaf through the issue template.

**5. Real California photos beat synthetic-only out of state.** Both runs are OBSERVED_EXPLORATORY: every real-photo label comes from the same YOLOE teacher, so this measures agreement with the teacher across collections, not accuracy against human labels. Arizona transfers almost perfectly (gap minus 0.007 against the CA validation score); Oregon drops 0.139, so Oregon photos are measurably harder. The toy-render flip matters for the physical demo, which uses printed toys. The weights for both runs were not stored, which is a recorded custody break (see custody slide).

**6. Per-taxon preprocessors route a bug to the model that knows it.** The idea: each taxon gets a highly trained small model that preprocesses for lower or local models, so a local model only sees the taxa it is specialised for. Crops are cut from the teacher's polygons with 8 percent padding; labels are the GBIF order and family of the source photo; a photo's crops never span splits. Crop dataset Merkle root 4d5f2831…459e. Source for 0.70: daisy/results/DAISY-BB-004/v4/DECISION.md.

**7. The order router transfers; the family model does not yet.** Decision rule frozen in the prereg: useful if test macro-F1 minus the majority-class macro-F1 is more than 0.10. ORDER clears it easily, with test top-1 accuracy 0.948. The Hymenoptera family model misses by 0.001, so it is NULL, and it is treated as California-only until retrained with out-of-state data. Diptera families cannot be judged because the holdouts contain no Diptera. All gates passed, 15 epochs per run on MPS, and the weights for all three runs are stored and re-verified. Attempts v1 to v3 were invalid and are kept as evidence under amendments 1 to 4.

**8. 24 breaks recorded, not hidden.** Custody here is deterministic: Merkle break points per module, an MMR ledger, LOMO per factor. Variance between runs is fine as long as every step is hashed. The 16 photo breaks are the bench photos behind the labware twin: their sha256 values are pinned, but the bytes stay off the repo because they show vendor marks. The cause of the eight result breaks was a kernel bug: the FINISH step exported weights only for runs marked EXECUTED, but EVAL had already relabelled them OBSERVED_EXPLORATORY, so the weights were deleted before export. Their sha256 values are recorded, but no bytes exist, so the resolvability invariant turned each one into an explicit break. Frozen protocols were never edited; fixes went in as amendments.

**9. Every file says who owns it and on what terms.** Each file is an atom of knowledge with a claim (OWN, OWN plus outside terms, or THIRD), a licence in context, a status and a hash. Outside terms are detected from imports, not mentions. GPL and unlicensed BioKEA and zlite repos are pinned by commit and sha256 root only; the unlicensed ones need the owner's permission before any reuse. On Claude's role: biobitworks directed, reviewed and chose the work.

**10. Compare two labs top-down and find the one break point.** This is the FCO and FCG compare: Claude's graph against a bring-your-own graph. Because every module has its own Merkle root, the comparison stops descending wherever the roots agree. The example file in docs records both graph roots and the full verdict per module.

**11. The printable bench kit stays well under $200.** Numbers come from the labware twin (print/labware), first pass: 19 observed parts and 8 printable remixes, each with a per-part Merkle tree rolled up to one lab root and a hash-linked custody log. Dimensions are estimates from photos against an 18 inch rule, except the SBS footprint and 9 mm pitch, which are standards. Risks to mention if asked: never print parts for cryo at minus 80, rotors, tip racks for robot pickup, or tube substitutes. The remixes are MIT, like everything else written in the repo.

**12. Open science you can verify from your own browser.** Close on the three ways in: the web page for people, npx and the CLI for scripts, the MCP server for agents, all reading the same pack. Check before presenting that GitHub Pages is switched on, otherwise the first link will not open; the repo README links the same page.

