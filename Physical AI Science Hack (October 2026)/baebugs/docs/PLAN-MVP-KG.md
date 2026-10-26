# MVP plan: knowledge graph you can contest, modular lab, agent access (deadline 2026-10-25 14:30 PDT)

Each milestone is a Merkle break point: it ends in a commit, a push, a check-in, and an MMR event;
major ones merge branch `mvp-kg` into `main` through a PR. Nothing below is claimed until its check passes.

| BP | Milestone | Check that closes it | Merge? |
|---|---|---|---|
| BP0 | This plan | committed | - |
| BP1 | **Atoms of knowledge (AoK) + licensing review**: every component (code, data, prints, models, results, docs) is an atom with claim, author/role (what Byron developed, what BioKEA/zlite/GBIF/Opentrons/Claude contributed), licence *in the atom's context*, status, leaf hash; atoms roll up to a root per level (repo -> module -> part/dataset/result -> file) | every atom resolves (resolvability invariant), licence present for 100% of atoms, no claim above its evidence status | yes |
| BP2 | **MVP page** (GitHub Pages, one link from README and site): root -> leaf knowledge graph browser, simple search filters (bug / species / order, print, part, module, licence, status), modular BioKEA lab rendered in WebGL (three.js, STL/GLB from the repo), California research tools (live GBIF occurrence search for CA, links to Essig/Calbug), toy and printed-part versions per bug | page builds, every node shows its address (root or leaf hash), axe-core accessibility pass, works at phone width | yes |
| BP3 | **Contest -> prove flow**: a "Contest this atom" action opens a GitHub issue / PR template that carries the atom address; a contester submits their own FCO/FCG JSON; a check verifies it against the graph (resolves, hashes recompute) and records the outcome as an attestation | template + verifier + test | with BP2 |
| BP4 | **Agent access** to the same graph: Python package + CLI (`baebugs-kg root|leaf|search|verify`), MCP server (stdio), Claude skill + plugin manifest, `npx github:biobitworks/baebugs` CLI | each entry point returns the same root hash | yes |
| BP5 | **Stress test** (`doctor`): pytest, ruff, pip check, npm doctor, html-validate, axe-core/Playwright a11y, broken-link + resolvability check, `brew doctor`/`gum` if present on the Mac, bring-your-own check hooks | doctor report committed; failures listed, not hidden | - |
| BP6 | **Training in parallel**: DAISY-BB-004 per-taxon preprocessors (one small model per order, later family/species) trained on specimen crops labelled from GBIF taxonomy, weights + values tracked per epoch (tensor hashes), exported and resolvable; local/smaller models consume them as preprocessors | preregistered before data; per-run custody INTACT; results vs DAISY-BB-002a | merge results |
| BP7 | **Claude vs bring-your-own comparison**: same graph, same queries; any other agent or person reproduces the root and the per-atom answers | comparison table committed | final |

Delegation: scaffolding, doctor checks and page polish go to smaller Claude models; custody, licensing claims
and training design stay here. Local Ollarma models: optional consumers via the CLI/MCP (they get the same root).
Continuous commits: each BP pushes; the custody watcher (magicstudio :8790) flags unpushed commits as WARN.
Not in scope today: hardware runs, calibrated apertures, publishing to npm/PyPI registries (installs from GitHub).
