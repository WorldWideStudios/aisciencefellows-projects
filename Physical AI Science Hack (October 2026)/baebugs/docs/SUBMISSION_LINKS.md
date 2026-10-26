# Submission links (BioKEA Track A, 2026-10-25)

One page to click through everything we submit. Status as of 21:35 UTC. **Works** means the file is on `main`. **Pages** links only work once GitHub Pages is on (Settings → Pages → Deploy from a branch → `main` / root).

| # | What | Link | Status |
|---|---|---|---|
| 1 | Repository | https://github.com/biobitworks/baebugs | Works |
| 2 | README Submission table | https://github.com/biobitworks/baebugs#submission-biokea-track-a-physical-ai-for-science-hack-oct-25-2026 | Works |
| 3 | Demo reel, 67 s, 7 steps, original music | https://github.com/biobitworks/baebugs/blob/main/docs/demo/baebugs_reel.mp4 | Works |
| 4 | MVP walkthrough video, 45 s | https://github.com/biobitworks/baebugs/blob/main/docs/demo/baebugs_mvp_demo.mp4 | Works |
| 5 | Sieving robot simulation, 63 s (teammates) | https://github.com/biobitworks/baebugs/blob/main/docs/sieving_robot/sieving_demo.mp4 | Works. Simulation, purity illustrative |
| 6 | Sieving robot deck (teammates' draft .pptx) | https://github.com/biobitworks/baebugs/blob/main/docs/sieving_robot/automated_sieving_robot_deck.pptx | Works. Placeholders on slides 5–8 and 13 |
| 7 | Filtration robot code (SO-101 arm + vision) | https://github.com/biobitworks/baebugs/tree/main/filtration-robot | Works |
| 8 | OpenSCAD workflow animation (BioKEA vs additions) | https://github.com/biobitworks/baebugs/tree/main/docs/workflow_video | Works. Illustrative |
| 9 | End-to-end story page (7 steps, file hashes) | https://biobitworks.github.io/baebugs/site/story/ · source https://github.com/biobitworks/baebugs/blob/main/site/story/index.html | Source works; page needs Pages |
| 10 | MVP graph page (root to leaf, check any hash) | https://biobitworks.github.io/baebugs/site/mvp/ · source https://github.com/biobitworks/baebugs/tree/main/site/mvp | Source works; page needs Pages |
| 11 | Protocol Board | https://biobitworks.github.io/baebugs/site/board/ · source https://github.com/biobitworks/baebugs/tree/main/site/board | Source works; page needs Pages |
| 12 | Training results, wins and nulls | https://github.com/biobitworks/baebugs/blob/main/docs/TRAINING_REVIEW.md | Works |
| 13 | Planned vs built | https://github.com/biobitworks/baebugs/blob/main/docs/ASBUILT_LOMO.md | Works |
| 14 | Custody inventory (25 breaks, 1,195 atoms) | https://github.com/biobitworks/baebugs/blob/main/kg/custody_inventory.json | Works |
| 15 | Interchangeable filters + variable aperture | https://github.com/biobitworks/baebugs/tree/main/print/filters | Works |
| 16 | Toy insects (91, STL + OpenSCAD) | https://github.com/biobitworks/baebugs/tree/main/print/fuse1 | Works |
| 17 | Labware remixes (STL + OpenSCAD + Opentrons) | https://github.com/biobitworks/baebugs/tree/main/print/labware | Works |
| 18 | Vision ladder demo | https://github.com/biobitworks/baebugs/tree/main/docs/ladder_demo | Works |
| 19 | Submission slides, repo copy (12 slides) | https://github.com/biobitworks/baebugs/tree/main/docs/slides | Works. Says 24 breaks; main has 25 |
| 20 | Preprint draft | https://github.com/biobitworks/baebugs/blob/main/docs/preprint/baebugs_preprint.md | Works |
| 21 | Licensing | https://github.com/biobitworks/baebugs/blob/main/NOTICE.md | Works |
| 22 | New slide deck + live demo (team Drive folder) | https://drive.google.com/drive/folders/11-WYJ-ADuBkXb53xUPbTeefuBf64radz | Outside the repo: not reviewed here, not hashed |
| 23 | Full lab stack deck, 14 slides (.pptx for Google Slides, from the team template) | https://github.com/biobitworks/baebugs/blob/main/docs/slides/baebugs_full_lab_stack.pptx | Works. Says 25 breaks |
| 24 | Live: evidence workcell (MVP graph, bench twin, Protocol Board, prove/contest) | https://baebugs-lab-workcell.vercel.app/ | Vercel production alias |
| 25 | Live: evidence lab (AoK/FCG explorer, licences, contest) | https://baebugs-evidence-lab.vercel.app/ | Vercel production alias |
| 26 | Live: CAD custody workcell (OpenSCAD tower, browser-recomputed MMR) | https://baebugs-cad-custody.vercel.app/ | Vercel production alias |
| 27 | Google Slides link submitted on the form | [add after upload] | Pending |
| 28 | YouTube demo video | https://youtu.be/O4Gq-r018cI | Works (hosted on YouTube, outside the repo, not hashed) |
| 29 | Bounding box viewer (YOLOE/OWLv2 recorded PA12 toy predictions) | https://baebugs-lab-workcell.vercel.app/detection/ | Source-linked model predictions, not validated live inference |

Agents read the same graph pack (`site/mvp/mvp.json`):

```
npx github:biobitworks/baebugs get root
baebugs-graph get root
python -m baebugs.graph_mcp   # needs mcp>=1.2,<2
```

Regenerate the story page after any data change: `python site/story/build_story.py`.
