# Bench asset photos

- `photos.json`: 20 photos from the bench (Oct 25 2026). Each has its original sha256. 19 are published here, re-encoded without metadata. The Opentrons Flex photo is withheld (people's faces in the enclosure reflection): only its hash is kept.
- `../kg/assets.json` (`python -m baebugs.assets`): 31 objects, each tied to the photos that show it, with role, interfaces and dimensions plus their source (spec / design / ruler-photo / not measured). Version history in `../daisy/assets_mmr.jsonl`.
- `boxes.json` (`python -m baebugs.asset_boxes`): **inferred** boxes from YOLOE text prompts, with model sha, prompt hash and each photo's tier-tree frame root.

Read `boxes.json` honestly: 58 boxes over 19 photos, and most labels are wrong (the 384-well plate called a "hexagonal grid", the Fuse printer a "perforated metal sheet", racks called "microplate"). Two photos got no boxes at all. Treat them as region proposals only. They become training labels for a bench/labware detector only after a person confirms or corrects each one. Until then nothing is trained on them.

Update (12:30): 7 more photos and 2 short videos (`videos/`, audio removed, metadata stripped) of the Fuse Sift depowdering the PA12 toy insects, and of FDM trommel attempt 1. Three new assets: `fuse_sift_drum`, `pa12_toy_insect_batch`, `fdm_trommel_attempt_1` (status FAILED, observed: perforated zones did not print). The split package (`print/packages/trommel_biokea_split`) moves the zones to the Fuse 1+.
