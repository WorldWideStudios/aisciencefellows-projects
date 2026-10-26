---
name: baebugs-graph
description: Look up any node of the baebugs knowledge graph (root, module:<name>, leaf:<path>, or a hash), what is claimed under which licence, and compare a user's own files or FCO/FCG against it. Use when someone asks about baebugs files, prints, parts, results, custody or licensing.
---

# baebugs graph

Every surface reads the same pack (`site/mvp/mvp.json`), so all of them give the same root.

1. Get the root first and quote it with any answer: `baebugs-graph get root` (or `npx github:biobitworks/baebugs get root`, or the MCP tool `root`).
2. Resolve what was asked: `baebugs-graph get leaf:<path>`, `module:<name>`, a sha256, or free text (returns hits).
3. Licensing: answer from the node's `claim` and `licence` fields; `OWN` = written here, MIT; `OWN+TERMS` = MIT plus the listed outside terms (Ultralytics AGPL-3.0 for weights, GBIF CC BY attribution, Opentrons Apache-2.0); `THIRD` = not ours. Say it records licences, not legal advice.
4. To check someone's copy: `baebugs-graph fco <files...> > mine.json`, then `baebugs-graph prove mine.json`. Report MATCH / DIFFERS / NOT IN GRAPH per file and the graph root compared against.
5. Custody: if `custody.breaks > 0`, name the affected runs; results whose weights were not stored are exploratory only.
6. To contest: open an issue with the address, the graph root and the attestation (template "Contest an atom").
