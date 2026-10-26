# BioKEA sealed replaceable inserts and contained rinse: design contract

STATUS: PROPOSED mechanical design; OpenSCAD/DXF executed; physical fit, leak control, insect recovery NOT_TESTED.
PARENT: Baebugs CAD custody 14-leaf root; append successor records, do not overwrite.

## Concepts rendered (not built)
- Reusable tray/frame nominal 132 x 104 x 14 mm (PHOTO-BASED GUESS); initial 120 x 90 mm Baebugs assumption and separate BugPicker 103 x 140 mm tray geometry are NOT the same part. Measure original.
- Four interchangeable plate profiles: round 3.2 mm; slot 2.4 x ~11.4 mm; hex ~3.0 mm across flats; empty mesh carrier.
- 316L stainless candidate ~0.8 mm thickness (vendor review required).
- Opposed folded stainless grip ears OUTSIDE specimen path, intended for tool/human access when stationary; NOT robot grip during inversion.
- Continuous perimeter gasket retained under uninterrupted solid plate edge; schematic 4.3 mm land and 1.6 mm free thickness; compression NOT established.
- Positive metal bridge retainers (schematic), required to lock insert before moving/inverting full cassette. Mechanical engagement NOT designed/certified.
- Contained upside-down catch position inside splash enclosure with secondary catch screen. Static pose only, not an executed movement. No water pressure or flow simulated.
- The mesh carrier DXF needs a second physical mesh clamp and edge-gap proof; a hole in a plate is not a complete woven mesh.
- CAD drawings are not vendor-ready, robot-ready or print-ready; fabrication without DFM review not authorized.

## Gasket: Parafilm is the wrong permanent choice
Parafilm M is disposable thermoplastic moisture-barrier film, not a qualified repetitive compression seal. The datasheet notes softening ~54-68 C and solvent limitations. Prefer candidate removable silicone O-ring/gasket for aqueous-only conditions; select PTFE, FKM, EPDM or other materials ONLY after verifying preservative compatibility, thermal/cold cycle, cleanability, extractables and deformation. No material qualified yet.
Supplier: https://www.sigmaaldrich.com/deepweb/assets/sigmaaldrich/product/documents/263/242/hs234526c-datasheet.pdf

## Recovery workflow (human-controlled, not simulated)
Register intake bag/photo -> image before sorting -> fraction containers each imaged -> image before inversion -> ensure retaining bridges and closed secondary catch -> gently invert and rinse by approved operator -> image recovered catch and plate underside -> inspect gasket interface -> image nominally empty tray -> register any remainder/debris -> BugPicker accession/well only after evidence review.

Clumps, small appendages and identical-looking insects make single-object identity ambiguous. Even zero detected objects does not establish 100% recovery. Capture high/low count uncertainty and all excluded regions. Never infer organism identity from a hash or a size-class assignment.

## Mandatory hold / VIP fault reasons
UNLATCHED_INSERT; OPEN_CATCH_PATH; EDGE_GAP; GASKET_PINCHED; RINSE_PRESSURE_UNKNOWN; CLUMPED_SAMPLE; DETECTOR_DISAGREEMENT; FRAME_STALE; SPECIMEN_DAMAGED; COUNT_DISCREPANCY; PHYSICAL_CONTAINER_UNTRACKED; CLEANING_NOT_CLEARED.
STOP admission to downstream automation, create human ticket, preserve raw frames and previous breakpoint. Operator approval and physical interlocks are separate from a dashboard button.

## Image custody contract
One image record per camera occurrence: source byte SHA-256, container/sample accession, fraction, tray, insert, gasket lot, camera ID, calibration identity, timestamp, operator, inspection stage and status. Same bytes reused in another context retain unique occurrence IDs. Human annotation is a distinct claim FCO. Capture labels OBSERVED_BYTES, not VERIFIED_ORGANISM_IDENTITY.
Keep source image original bytes in content-addressed store and never overwrite. Keep calibration uncertainty and observation time distinct from ingestion time.

## Fabrication and QA gates
1. Measure real tray ledges, inside dimensions and latch clearances; replace guesses in successor revision.
2. Laser / CNC vendor reviews web width, burrs, stainless material cert, flatness, kerf and folded handle treatment.
3. Assemble dry: verify metal grippers do not contact specimens, clamp engagement and captive seal; verify the seal cannot extrude into processing aperture.
4. Independently test benign particles and leak bypass with an approved rinse protocol; verify primary fraction plus secondary catch and residue, not just main chamber.
5. Test cleaning compatibility with actual chemical agents and contaminants; author cleaning log per insert + gasket lot.
6. Real specimen sorting remains NOT_TESTED until permitted by site procedures.

## Execution evidence
OpenSCAD on magicPRObox built CAD renders and four flat DXF files. Early wrongly labelled assembly STL exports were moved to predecessors, retaining their bytes. No physical actuation or wet sorting was run. Dynamic gasket performance, robotic inversion safety, complete capture and sterilizability are UNKNOWN/NOT_TESTED.
