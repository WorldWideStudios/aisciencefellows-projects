# Bench Boards (design draft)

A Pinterest-style feed for protocols, printable parts, labware, insect prints and models, built as a view over
the BaeBugs graph: every card carries its leaf hashes, licence, status, cost and a "Check in twin" preflight.

Open [`index.html`](index.html) in a browser for the design memo and a static, clickable mockup. Nothing is
implemented yet; card facts in the mockup come from `kg/aok.json`, `opentrons/`, `print/` and the bench-twin
files, and the graph and card roots shown are placeholders.

Open questions for review:

1. First domain: insect sample prep plus printable lab hardware (proposed)?
2. Keep it inside this repo (`site/cards/`) until v2, or split it out?
3. Boards as JSON in git (custody by PR) or a database with its own MMR log?
4. Cost basis: filament only (~$8 for the remix set) or the full kit?
5. Remix licence: the bench-twin README says CERN-OHL-W/S-2.0, the labware PR relicensed them MIT. Pick one.
