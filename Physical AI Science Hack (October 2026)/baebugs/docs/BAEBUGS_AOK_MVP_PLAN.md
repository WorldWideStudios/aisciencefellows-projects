# Baebugs AoK/FCO–FCG evidence lab: implementable plan

Source baseline: \`biobitworks/baebugs\` main at \`3a1806000ec4ca38e25f2749712d54b82ef612af\` as observed at branch creation. This is a distinct feature branch; preserves predecessor CAD and DAISY roots.

## Audience and simplest SPC-style flow

**Search → Select object → Read claim and rights → Inspect evidence and neighbor FCOs → Verify leaf against root → Contest with own source.**

Visible defaults: searchable indexed records; a focused neighborhood (not a wall of 112 nodes); modular workcell station selectors; exactly one rights line and one evidence state per selected object; progressive disclosure for long hashes and raw JSON. Provenance-led evidence funnel from SPC without copying restricted SPC datasets.

## Logical pipeline

source/exact bytes → AoK/content FCO → occurrence/context FCO → typed FCG → experiment/method → derived evidence → bounded claim → public artifact.

A \`source_path\` and its SHA-256 identify actual local input bytes. FCO id hashes canonical semantic content. Occurrence id hashes its independent graph context. Graph \`id\` is a human-friendly key; **never substitute it for the content address**.

Build \`tools/aok_build.py\`:
- read manifests for 20 trommel/vortex/arm STLs, 4 Opentrons STL adapters, filter registry, DAISY inventory, and source rules;
- fail closed if any claimed part bytes do not equal recorded manifest SHA-256;
- hash 112 content objects plus 135 distinct typed relationship atoms with canonical JSON + domain-separated SHA-256;
- sort leaves by stable node ID and compute binary Merkle root, duplicate odd-final leaf, carry per-leaf sibling inclusion proof;
- output root, graph, source manifest and machine-readable access interfaces;
- **do not** treat this tree as an extension of the historical CAD14 MMR or DAISY experiment tree.

## Model of evidence claims

Every object must have type, source, status, rights, source SHA, content FCO, occurrence ID and leaf inclusion. Statuses remain separate: PROPOSED, IMPLEMENTED, EXECUTED, OBSERVED, SUPPORTED, FAILED, UNKNOWN, NOT_TESTED, NOT_COMPUTED. Rights are recorded per occurrence; global root MIT is not a substitution for asset-specific rights.

## Modular lab

Modules: sorter/EntoSieve, disperser, picker, enzyme dispenser, incubator, camera, arm, Opentrons adapter, flow-through/eDNA. Display rendered part previews from source. Use JavaScript SVG and keyboard-operable selection. Later optional WebGL (Three.js) viewer can use GLB, but no remote package needed for this snapshot.

## Adoption channels

- Browser: \`site/aok/index.html\`, \`data/graph.json\`, \`data/root.json\`, \`data/manifest.json\`.
- Python: \`tools/aok_build.py {list,get,search,proof,verify,doctor}\`.
- Node: \`packages/baebugs-aok/bin/baebugs-aok.mjs\`; local \`npm pack\`. **NOT_PUBLISHED to npm.**
- Optional MCP: \`tools/aok_mcp.py\` read-only stdio server for connected agents.
- Claude/agents: \`skills/baebugs-aok/SKILL.md\` task schema and claim-admission boundaries.
- User challenge: browser generates candidate FCO and FCG edge; submits through GitHub Issue for human review. Not a direct canonical write API.

## Merkle breakpoints, gates and expected receipts

| Gate | Test | Admission |
|---|---|---|
| G0 source | Repository pin and rights inventory, no private material | Source status declared |
| G1 content | source-file hashes, part manifest exact matches | FAIL_CLOSED on mismatch |
| G2 graph | no missing endpoints, no duplicate IDs; FCO/occurrence identities | PASS required |
| G3 roots | ordered leaves, proof generation, independent recomputation | PASS required |
| G4 browser | JS/browser exact UTF-8, inclusion, keyboard graph, responsive | PASS required |
| G5 adversarial | source drift, leaf tamper, root tamper, bad license, negative records | FAIL detected |
| G6 CLI/interop | Python, Node, optional MCP, skill, JSON receipt | PASS or NOT_TESTED |
| G7 publication | GitHub push, Vercel deployment and remote readback hash | PASS or BLOCKED |
| G8 science | expert ID / three-bug physical recovery / operational rights | NOT_TESTED |

### Competitive experiments and higher-order LOMO

A future measurement layer can compare leave-one-module-out and leave-one-mode-out tests: discard robot, vision, mesh, density, or elutriation lane; recompute actual supported metrics **only if measured outcomes exist**. Until real baselines and denominators are available, show \`NOT_COMPUTED\`, not a fictitious benefit.

### Public API considerations

Catalog snapshots can be cached immutably with versioned names and canonical root links. For higher traffic use an S3/SQLite/DuckDB identity index and REST endpoints, but do not replace cryptographic leaf recomputation with a semantic-search vector. Search may propose node IDs; retrieval after knowing an ID is direct lookup.

### Safe Next Action

Expert review of claims and licenses → obtain physical calibration and specimen recovery evidence → successor graph snapshot under documented new root. Do not rewrite predecessor.

## FCG relationship-atom successor
The initial 112-node root was superseded by an append-only successor: 135 declared relationships have independent content FCOs and ordered Merkle leaves, yielding 247 leaf identities. The predecessor root and bytes remain archived under docs/aok-predecessor-20261025/v2-nodes-only. This is not an MMR append to the predecessor tree; it is a new deterministic snapshot rooted in expanded source declarations.
