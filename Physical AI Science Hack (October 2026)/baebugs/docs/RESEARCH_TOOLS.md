# Prebuilt tools checked before building (bench assets, Oct 25 2026)

Rule: look for an existing open package first, integrate it, and build only the glue. What was checked and what was used:

| Need | Checked | Used | Why |
|---|---|---|---|
| Labware dimensions | PyLabRobot resource library (0.2.2: Revvity/PerkinElmer, Greiner, Corning Falcon, VWR, Eppendorf, Opentrons...), Opentrons shared-data labware definitions | **both** (`baebugs/assets.py`) | Opentrons definitions give exact specs for the Flex 50 uL filter tip racks in the photos; PyLabRobot gives near matches (384 plate, 50 mL conical), recorded as *library candidates* with the reason they are not exact, never as measurements |
| Box confirmation (human in the loop) | Label Studio, CVAT, labelme, X-AnyLabeling | **Label Studio** (Apache-2.0; `baebugs/label_studio.py`) | imports model boxes as pre-annotations, exports human annotations as JSON; our import keeps only human annotations and hashes them into the asset MMR |
| Open-vocabulary detection | YOLOE (Ultralytics, AGPL-3.0), OWLv2 (Google, Apache-2.0), Grounding DINO 1.0 (Apache-2.0), Florence-2 (MIT, no per-box scores) | **YOLOE + OWLv2** (`baebugs/asset_boxes.py`) | OWLv2 runs from Hugging Face transformers with a permissive licence and gives per-box scores; both are compared on the same photos |
| Lab inventory / LIMS | eLabFTW, openBIS, other open-source LIMS listings | not integrated yet | our asset records are plain JSON with hashes; any of these can import them later |

How the detectors are compared without box labels: an image-level check against the asset registry. For each photo, the registry says which kinds of objects it shows (rack, tip box, plate, tray...). A detector is scored on whether it finds those kinds (precision / recall / F1). This is weak evidence and a stand-in until boxes are confirmed in Label Studio.

Sources: [PyLabRobot resources](https://cdn.jsdelivr.net/npm/@saibolla/ada@0.1.3/skills/pylabrobot/references/resources.md), [Label Studio pre-annotations](https://labelstud.io/guide/predictions), [open-vocabulary detector comparison (Fora Soft, 2026)](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/open-vocabulary-detection-grounding-dino-florence-2-rtdetr-rfdetr), [Grounding DINO vs OWLv2 (Roboflow)](https://roboflow.com/compare/grounding-dino-vs-owlv2), [open-source LIMS guide](https://intuitionlabs.ai/articles/open-source-lims-guide).
