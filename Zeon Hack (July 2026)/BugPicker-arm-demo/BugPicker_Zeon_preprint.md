# Toward Low-Cost Robotic Biodiversity Discovery Using Bug Picking, Plate Shuttling, and Automated Plate Scanning

**Sean Jungbluth<sup>1</sup>, Austin Baker<sup>1</sup>, Jeremy Garibay<sup>2</sup>, Chris Anderson<sup>3</sup>**

<sup>1</sup> BioKEA  
<sup>2</sup> Independent / Zeon Systems hackathon team  
<sup>3</sup> Independent

## Abstract

Large-scale biodiversity discovery remains constrained by manual handling: small hard-bodied invertebrates, especially insects, must be detected, picked, transferred into plates, imaged, and prepared for downstream molecular assays. We describe an integrated prototype workflow that combines BugPicker, an automated organism pick-and-place system derived from an Opulo LumenPnP/OpenPnP platform, with an xArm 7 robotic plate shuttle and a GRBL-controlled plate-reader/scanning stage. The system detects small organisms from tray images, places them into 96-well plates, transfers plates between stations, executes a scan routine, and returns plates to the BugPicker. Developed during the AI Science World Model Hack Hub Zeon Systems hackathon, this work demonstrates how AI-assisted software development and commodity robotics can rapidly connect previously separate laboratory automation modules. We propose that such integrated workflows can reduce the cost of sequencing and imaging small organisms toward $0.25 per individual, enabling larger-scale biodiversity monitoring, reference-library generation, and ground-truthing of environmental surveys.

## Introduction

Biological discovery at environmental scale is limited not only by sequencing chemistry or imaging hardware, but by the physical labor required to move individual organisms through a workflow. In many biodiversity pipelines, humans still sort samples, pick specimens, place individuals into wells, move plates between instruments, verify sample transfer, and maintain metadata. These steps are repetitive, error-prone, and difficult to scale.

The core idea of this project is to automate the bottlenecks between organism discovery and downstream characterization. BugPicker addresses the first bottleneck: converting unstructured trays of small organisms into organized 96-well plates. The plate-shuttle system addresses the next bottleneck: moving those plates between stations without manual handling. The PlateReader module provides a controllable scanning/readout stage that can be invoked programmatically as part of the same cycle.

Our hypothesis is that integrated robotics can lower the effective cost of sequencing and imaging small organisms to approximately $0.25 per individual by reducing manual handling, increasing throughput, and enabling unattended or semi-attended operation.

## System Overview

The combined prototype has three major subsystems.

**BugPicker** repurposes an Opulo LumenPnP, normally used for PCB pick-and-place work, into an organism handling platform. A top camera rasters over a tray, Python/OpenCV segmentation detects dark organism silhouettes, and OpenPnP scripts convert detections into machine coordinates. A vacuum nozzle picks individual organisms, verifies pickup using a pressure signal and bottom-camera QA, and places each organism into the next well of a 96-well plate.

**Plate shuttle** uses a uFactory xArm 7 and xArm gripper to move 96-well plates between the BugPicker and an imager/plate-reader station. The current Python workflow, `Plate_shuttle_cycle.py`, performs pickup, safe transit, imager placement, scan invocation, imager pickup, BugPicker return, and final retract. Cartesian poses are used for plate approach and placement, with 50 mm approach offsets above grip/drop positions. The script includes dwell times before and after release, slower gripper opening, and one-time recovery from intermittent xArm stop-state motion failures.

**PlateReader** is a GRBL-controlled plate-reader/scan-stage prototype driven through a Python serial interface. The current `scan96.py` routine opens `/dev/ttyUSB0`, initializes GRBL, raises the pen/actuator, performs a reproducible X-axis jog sequence, verifies the machine position before and after motion, and returns control to the plate-shuttle script. In the integrated cycle, the arm waits for this subprocess to complete before retrieving the plate.

## Methods

### Bug detection and picking

BugPicker uses a file-coordinated OpenPnP/Python pipeline. The OpenPnP layer controls camera rastering, nozzle motion, vacuum actuation, and plate placement. Python tools process scan images, segment candidate organisms, deduplicate detections across overlapping frames, and emit pick coordinates as `objects.jsonl`. A QA script inspects bottom-camera and well images to determine whether an organism was picked, stuck to the nozzle, or successfully deposited.

### Plate transfer automation

The plate shuttle is implemented in Python using the xArm SDK. The workflow uses taught Cartesian poses of the form:

```python
[x, y, z, roll, pitch, yaw]
```

The current cycle includes separate poses for BugPicker pickup, BugPicker return placement, imager placement, and imager pickup. This separation proved important because the best pose for gripping a plate was not identical to the best pose for placing it back down. The gripper is opened to `850`, closed to `755`, and opened at reduced speed to avoid displacing plates during release.

The main sequence is:

1. Move to BugPicker pickup approach.
2. Descend to pickup pose and grip the plate.
3. Move through a safe transit pose.
4. Place the plate on the imager.
5. Hold before and after release.
6. Move to an imaging wait pose.
7. Run the PlateReader scan subprocess.
8. Pick the plate back up from the imager.
9. Return the plate to the BugPicker.
10. Release, retract, and return to home travel.

### Plate-reader integration

The plate-reader step is invoked from the arm-control script using `subprocess.run`, which blocks until the scan routine exits. If the scan returns a nonzero exit code, the plate shuttle stops rather than proceeding to retrieve the plate. This makes downstream station failure visible to the orchestration layer.

### Recovery behavior

During repeated demonstrations, the xArm occasionally entered stop state `4` with motion return code `-9` during a carried transit move. The current script handles this by clearing warnings/errors, re-enabling motion, setting the arm ready, and retrying the same motion once. The retry does not change gripper state, avoiding unsafe release while a plate may be suspended. If the retry fails, the script stops.

## Results

We built a prototype end-to-end pipeline in which the arm picks a plate from the BugPicker, places it on the imager, invokes the PlateReader scan routine, retrieves the plate, and returns it to the BugPicker. The integrated script successfully waited for the PlateReader process to complete before resuming the return leg. After tuning, the release sequence included a pre-release dwell, slow gripper opening, and post-release dwell, which improved plate placement stability.

The prototype also surfaced practical engineering requirements for robust biological robotics: separate pickup and placement poses, conservative approach heights, slow release dynamics, visible safety prompts, and explicit handling of controller stop states. These are small details, but they are central to moving from a visual demo to a repeatable laboratory workflow.

## Discussion

This prototype shows that relatively accessible robotics platforms can be composed into a larger biodiversity automation workflow. BugPicker converts a tray of organisms into organized plate positions. The xArm shuttle connects that plate workflow to another instrument. The PlateReader interface demonstrates that downstream devices can be inserted into the sequence as blocking subprocesses, allowing each station to complete before the plate is moved again.

The broader implication is that biodiversity workflows can be treated as programmable pipelines. Once organisms are physically organized in plates, imaging, sequencing preparation, and metadata generation become easier to automate. This could support large-scale DNA barcoding, reference image libraries, organism-level trait extraction, and ground-truth datasets for environmental DNA or image-based surveys. Although the current focus is small hard-bodied invertebrates, especially insects, the workflow is intended to expand to other metazoans.

The $0.25 per individual cost target is a hypothesis based on amortized low-cost robotics, 96-well batch handling, reduced labor per specimen, and high-utilization downstream sequencing and imaging workflows. The target is ambitious but useful because it focuses attention on throughput, consumables, labor displacement, and failure recovery. Achieving that target will require not only faster robotics, but robust coordination across picking, imaging, liquid handling, sequencing preparation, and data interpretation.

## Impact

Low-cost, high-throughput organism handling could help governments, nonprofits, and researchers monitor biodiversity with greater spatial and temporal resolution. Automated ground-truth generation would make environmental surveys more reliable by linking molecular signals, images, and physical voucher-like sample records. At scale, these systems could help detect changes in species composition, identify invasive or threatened taxa, and accelerate discovery of undescribed biodiversity.

## Next Steps

Near-term engineering work should focus on downstream automation beyond plate transfer. Priorities include liquid handling, lysis and DNA extraction, sequencing-library preparation, more formal metadata tracking, and expanded QA checks after each physical transfer.

A second direction is an agentified feedback loop for discovery. Such a system would monitor images, sequencing results, taxonomic novelty signals, and sampling metadata, then suggest useful next actions: which organisms to prioritize, which samples to re-image, which wells need rework, and which field collections might reveal new species. This closes the loop between robotic execution and scientific decision-making.

## Limitations

The current prototype is a hackathon-stage system and should not yet be interpreted as a production automation platform. Payload parameters remain placeholders, and throughput/cost have not yet been formally measured. The PlateReader routine currently demonstrates programmable plate-reader/scan-stage control and integration; additional work is needed to connect it to final biological readout requirements. Safety supervision remains necessary during operation.

## Conclusion

We integrated organism picking, robotic plate transfer, and automated plate-reader actuation into a single repeatable workflow for 96-well biodiversity processing. The system demonstrates a path from manual organism handling toward scalable, low-cost biodiversity discovery infrastructure. With downstream liquid handling, sequencing integration, and agent-guided feedback, this approach could enable large-scale imaging and DNA sequencing of small organisms at costs compatible with routine environmental monitoring.

## Remaining Questions Before Submission

- What measured cycle time per plate should be reported once benchmarking is complete?
- Which downstream biological readout should be used for the first formal validation: imaging, DNA extraction, sequencing-library preparation, or full sequencing?
