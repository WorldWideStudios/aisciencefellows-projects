---
name: baebugs-aok
description: Retrieve source-bound BioKEA/Baebugs evidence, verify exact FCO identities and Merkle inclusion, inspect individual rights, and propose counterevidence without mutating frozen history.
---
# Baebugs AoK verifier (skill)

Use the public read-only `site/aok/data/graph.json` and `root.json`.
Given an ID (for example `part:trommel_zone_2mm`), use direct key lookup; do not search semantically again.

1. Verify `python3 tools/aok_build.py verify` or `node packages/baebugs-aok/bin/baebugs-aok.mjs verify`.
2. Retrieve the `fco_id` (content identity), `occurrence_id` (context), leaf `sha256`, source path/exact bytes hash, license, attribution, status and inclusion proof. Preserve negative and unknown states.
3. Distinguish the AoK snapshot root from historical CAD14 and DAISY002a roots. They are declared graph references **not one cryptographic commitment**.
4. For disagreement, generate candidate JSON with reference leaf, evidence URI and typed proposed FCG edge; send to GitHub for human review. No in-place mutation, no claim of verified signature.
5. Never claim real specimen recovery, new taxon, measured aperture, model accuracy or IP ownership from a mere hash.
6. Respect BugPicker GPL, BioKEA BugSorter and EntoSieve license UNKNOWN, GBIF media-specific rights, and missing ILEA identity.
7. No tool call may actuate hardware, write restricted images or publish private specimen data from this skill.

**Existing interfaces:** Python CLI `tools/aok_build.py`, optional MCP `tools/aok_mcp.py`, Node CLI `packages/baebugs-aok/bin/baebugs-aok.mjs` and public JSON.

## Expected response
`SOURCE → AoK → FCO → FCG → DERIVED → CLAIM → ARTIFACT`;
each node's status plus source permission, actual executed evidence and requested next action.
