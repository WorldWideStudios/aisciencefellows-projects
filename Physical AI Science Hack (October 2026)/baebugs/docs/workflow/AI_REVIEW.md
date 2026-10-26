# AI review brief — BaeBugs workflow

## Frozen starting evidence

Review baseline: commit 02b6ba9697a5dd63957ea043345c7caeab244e40.
Workflow implementation: 5a3b01d0a99487433b4ba129900815529ac3f490.
Merged by PR #19 at 45fb8b3e1559b052a1dedae1635f60aac1426cd4.
Predecessor receipts: turn_20261025_01.json and turn_20261025_02.json.
Recover current HEAD before proposing edits; preserve these predecessor states.

## Task for the reviewing AI

Independently inspect site/workflow/index.html, docs/workflow/README.md, REVIEW_20261025.md and the cited implementation modules. Determine what exists, what actually ran, and which claims are supported. The intended product is an IKEA-style lab-workflow configurator: select a specimen or search objective, compose suitable components, inspect every handoff and export a protocol.

Current implementation is a static draft builder with seven fixed steps. It captures objective text, selected components and source links; it does not perform semantic planning, compatibility solving, inference, persistence or hardware execution.

## Review questions

1. Does the page export the selected inputs and all seven checkpoints without implying execution?
2. Are model tasks separated (bench assets versus insects; detection versus segmentation versus identification)?
3. Are missing calibration, component compatibility and physical observations explicit? Does any text imply a blocker is programmatically enforced when it is only descriptive?
4. Can sample, specimen occurrence, fraction, image, candidate, action and destination well remain individually addressable? What schema is still needed?
5. Are untrusted inputs rendered safely? Check export behavior, accessibility and browser interaction independently.
6. Are source licensing and upstream attribution preserved? Do not treat the root repository license as permission for every dataset/model.
7. Are reported detector metrics weak-label results clearly separated from independent human-labeled accuracy?
8. What is the smallest testable adapter integration using existing planner/twin code?

## Evidence ceiling

- IMPLEMENTED: draft builder, seven checkpoints, protocol JSON export, review documentation and notebook.
- EXECUTED / OBSERVED in turn 01: JavaScript parsing and Node VM assertions passed; exact artifact hashes computed.
- EXECUTED / OBSERVED in turn 02: PR merge and main ref readback succeeded.
- NOT_TESTED: real-browser flow, live inference, hardware, deployment and Python regression suite in this review environment.
- FAILED: pytest invocation (module unavailable); Notion fetch (404); DataONE metadata retrieval unavailable. These are not scientific negative findings.
- UNKNOWN: current R4 training completion and live production state.
- PROPOSED: model adapters, compatibility solver, persisted specimen receipts and independently labeled evaluation.
- MMR NOT_COMPUTED; signatures NOT_SIGNED. Do not invent a new root or signed state.

## Required review output

Return: verdict; findings ordered by severity; exact file/line evidence; reproduction command and observed output; supported wins; unsupported claims; minimal fixes; and NEXT_ACTION. Distinguish PROPOSED, IMPLEMENTED, EXECUTED, OBSERVED and SUPPORTED. Preserve FAILED, NULL, NEGATIVE, DEFERRED, NOT_TESTED, UNKNOWN and NOT_COMPUTED where applicable.

No experiment claim without an executable notebook and bound inputs/outputs. No scientific validity claim from a passing software test. Any correction creates a successor receipt linked to the frozen baseline.
