# BaeBugs workflow — humans and AI start here

BaeBugs aims to help someone find or choose a bug, assemble suitable lab components, and produce a reviewable protocol with computer vision at each handoff. The current workflow builder is a draft configurator; live inference and physical execution are not connected to this page.

## Try it locally

From the repository root:

```bash
python3 -m http.server 8000
```

Open http://localhost:8000/site/workflow/. Choose a known specimen or a search objective, enter the target, select the sample and components, then click **Build draft protocol** and **Download protocol JSON**. No Python package dependencies are required for this page.

The objective is stored as text; an AI model does not interpret it yet. The seven steps are a fixed inspection template, not an equipment-compatibility calculation.

## What the MVP brings together

| Capability | Evidence / boundary |
|---|---|
| Sizing, sieve planning, twin preflight and fraction verification | Existing Python modules; existence does not prove physical success |
| BugPicker-compatible handoff | Existing adapter code; live end-to-end run remains unverified here |
| Parts, digital twin and evidence graph | Existing review surfaces; geometry concepts require measurements |
| Draft workflow assembly and JSON export | Implemented in site/workflow/index.html; Node assertions passed in turn 01 |
| Bench asset detector comparison | Repository reports OWLv2 F1 0.51 versus YOLOE 0.24 using weak image-level labels; not insect or box-level validation |
| Model/component remix | Selected component names and source links implemented; arbitrary plugins and compatibility solver PROPOSED |

## Workflow and required evidence

| Step | Vision checkpoint | Additional evidence |
|---|---|---|
| Intake | Sample image, scale marker, candidate region | Source, sample ID, preservative |
| Plan | Width estimates and method disagreement | Calibration and aperture measurements |
| Preflight | Slots, stack order and occupancy | Geometry, water reserve, operator review |
| Separate | Every retained fraction before/after | Recovery, loss and damage counts |
| Disperse | Clumping and overlap | Isolated-candidate decision |
| Pick and plate | Source after pick and destination well | Object-to-well identity and action log |
| Downstream | Plate ID, orientation and well map | Dispensing/incubation sensor logs; vision cannot establish chemistry or temperature |

Exported steps start NOT_TESTED with empty evidence. The protocol is PROPOSED, execution NOT_EXECUTED and hardware authorization false. No motion commands are generated.

## Review and next work

Read [the evidence review](REVIEW_20261025.md), [AI review brief](AI_REVIEW.md), [reproduction notebook](reproduce.ipynb), and the append-only turn receipts in this folder. For repository setup see [HOWTO](../HOWTO.md); for source-specific rights see [CLAIMS](../CLAIMS.md). The repository license does not replace third-party terms.

Prioritize actual image inference, deterministic planner/twin adapters, measured compatibility, persistent per-specimen receipts and a specimen-disjoint human-labeled test. Record each real experiment in an executable notebook, preserving failures and negative results.

The previous review could not read the live Notion guide (404) or DataONE record metadata. Saved event slides were reviewed instead. Do not infer successful ingestion, current training completion, deployment, biological accuracy or hardware success from these documents.

Hashes establish identity; graph edges declare relationships; Merkle inclusion establishes custody. None establishes scientific truth.
