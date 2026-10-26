# Baebugs public rights audit — 2026-10-25

This is a source/rights inventory, **not a legal opinion, patent search or inventorship determination**. Each item in the graph carries license context and a source hash; the graph does not issue licenses.

## Source and contribution boundaries

| Scope | Source-backed finding | Safe public description | Not established |
|---|---|---|---|
| Baebugs original code | Root \`LICENSE\` declares MIT, Copyright (c) 2026 biobitworks | MIT-declared Baebugs implementation and prototype generators | Every contributor's assignment, exclusive IP, novelty |
| Baebugs STL parts, DXF/filter suggestions, Opentrons adapters | Exact bytes in \`print/parts/parts.json\`, \`opentrons/parts.json\`, and original generators | Baebugs-generated **prototype concepts** under repository MIT context, subject to contributor ownership and reused-design review | Manufacturing fit, biological safety, certified robotics, new patent claims |
| BioKEA BugPicker and BugPicker-arm-demo | Each checked repo contains GPL-3.0 license text | Upstream BioKEA tooling used as protocol and interface reference | Ownership by Baebugs or automatic MIT relicensing; derivative distribution obligations require review |
| BioKEA BugSorter | Checked source repository has **no LICENSE file** | Reference to named upstream concept only | Reuse, modification or redistribution permission; GitHub visibility is not a license |
| zlite EntoSieve | Checked source repository has **no LICENSE file** | Historical source and concept reference only | Reuse/redistribution permission |
| GBIF / Essig / Calbug | GBIF occurrence license and multimedia rights can differ; attribution and DOI matter | Only permitted metadata, source identifiers and links in public catalog | Automatic right to redistribute photographs or complete datasets |
| California Academy of Sciences (separate institution) | Its entomology page restricts commercial use and redistribution without consent | Contextual *example* of source-specific terms | Those particular terms governing every Berkeley/Essig image |
| Training model weights | Experiment receipts preserve hashes, but 002a best.pt exports were lost | Reported exploratory comparison and checkpoint hashes | Deployable model, independent accuracy, redistributable weights |
| FCO/FCG and MMR | Generated verified hashes, ordered leaves, exact sources | Publicly recomputable declared provenance and snapshot integrity | Scientific truth, causal attribution, author signature, patent priority |

### What the user may claim at each abstraction level

- **L0 source/document:** a source was inspected; publication/license must be cited verbatim and tied to exact file/URL and access scope.
- **L1 AoK:** a discrete assertion was extracted, with source link, original wording, and context constraints.
- **L2 FCO:** specific content bytes and context identities recompute exactly. The FCO does not verify the assertion's truth.
- **L3 FCG:** named relationship between FCOs; edge type does not infer physical causality.
- **L4 derived evidence:** algorithm, version, parameters, inputs and actual outputs observed; missing original media or weights stays unavailable.
- **L5 claim:** bound to experiments, counterevidence, licensing and confidence. Teacher-label agreement is not independent species accuracy.
- **L6 artifact/publication:** attributed screenshots, source code, patents, prints, videos and raw datasets are *different rights categories*. A published graph does not award inventorship.

## Public-page admission criteria

- Do not expose restricted images, private lab data, personally identifiable collection records or secrets.
- Do not mix third-party GPL designs into MIT release materials without compatible rights analysis.
- Do not label scientific model outcomes SUPPORTED when the only ground truth is the same teacher.
- Do not show a real insect as "discovered new species" without voucher, taxonomist and independent evidence.
- Treat requests for corrections as **counterevidence candidates**. GitHub issue acceptance triggers a new successor snapshot, never mutation of frozen predecessors.
- User-owned research may have CC BY-NC-ND 4.0 designations in other lanes. That **does not retroactively replace MIT** on this repository or cure third-party obligations.
- ILEA is an unresolved user-mentioned dataset name. No URL, permission, bytes or accession is invented.

## Sources and inspection anchors

- https://github.com/biobitworks/baebugs/blob/main/LICENSE
- https://github.com/BioKEA/BugPicker/blob/main/LICENSE
- https://github.com/BioKEA/BugPicker-arm-demo/blob/main/LICENSE
- https://github.com/BioKEA/BugSorter
- https://github.com/zlite/entosieve
- https://www.gbif.org/citation-guidelines
- https://techdocs.gbif.org/en/data-publishing/multimedia-publishing
- https://www.calacademy.org/scientists/entomology-information-page

**NOT_SIGNED**. License-rights and inventor-attribution decisions require human review.
