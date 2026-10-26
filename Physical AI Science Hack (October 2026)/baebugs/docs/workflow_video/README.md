# Original workflow versus BaeBugs additions — animated MVP

## Do we have an end-to-end arm video?

No verified end-to-end hardware recording was recovered in this review. The repository includes a 44.64-second website tour (`docs/demo/baebugs_mvp_demo.mp4`) and two short physical Sift tumble clips (`assets/videos/`); those do not establish the complete BioKEA arm workflow with our additions. One sampled Sift frame shows a perforated drum; no arm or specimen-to-well lineage is established by that sample.

`biokea_vs_baebugs.mp4` is a new 30-second OpenSCAD-derived, captioned keyframe animation. Both views are illustrative. It is not footage of an executed robot, a calibrated digital twin, a collision simulation or a measured performance comparison.

## Attribution and comparison

BioKEA baseline: BugSorter → BugDisperser → BugPicker → dispenser → incubator, described in the saved event slides. The separate upstream arm project documents an xArm 7 moving a plate from BugPicker to an imager, invoking a scan, then returning it. We do not claim that upstream mechanism as ours.

Source: https://github.com/BioKEA/BugPicker-arm-demo/blob/bfd3be6ac8b5092f63824ccc656a3abb008a4f4a/README.md

Our addition: visual intake/calibration, multi-method candidate review, sieve/twin planning, per-fraction verification, specimen-to-well trace, human review and draft protocol export. Code exists for portions; physical integration is PROPOSED / NOT_TESTED. Cameras in the animation are proposed conceptual placements. Novelty is not established by this comparison.

Scene geometry was authored here, not copied from upstream CAD. The generic arm is not an accurate xArm 7 model. Dimensions, poses, clearances, grasping and specimen dynamics are unmeasured. The dispenser/incubator are contextual stations; the animated plate shuttle does not traverse them.

## Reproduce

Install OpenSCAD, FFmpeg, Python with numpy, matplotlib and Pillow. Run from repository root:

```bash
python docs/workflow_video/render.py
```

The script exports OpenSCAD STL meshes, renders them offscreen through Matplotlib, and encodes MP4 with FFmpeg. No device is contacted. Direct OpenSCAD PNG rendering failed because this environment lacked an X server; mesh export succeeded. The notebook reproduces the same process. Generated frames are intermediates and are not committed.

## Hardware evidence still needed

Record a continuous wide view plus synchronized station images for a known plate/sample ID: intake → sorting fractions → dispersion → pick/well placement → arm-to-imager → scan → return → downstream handoff. Bind frame times, model IDs, human decisions, commands and instrument logs; retain failures. Compare baseline and additions with matched samples and measured recovery, damage, pick success and time. Do not convert illustrative rendering into OBSERVED hardware evidence.
