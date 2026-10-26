# Flex hardware check, Saturday 2026-10-24 about 17:30 PDT

Read-only requests to the Flex's HTTP API plus three camera pictures. No protocol was uploaded or run and nothing on the robot moved. The robot is called "Studio45" in the Opentrons App. Its IP address and serial number are deliberately not written here (public repo), and the camera pictures are not committed because they show the room and people.

## What the robot reports

| Item | Value |
|---|---|
| Model and software | OT-3 Standard (Flex), robot software 10.1.0, firmware 68, board FLEX_B2 |
| Protocol API range | 2.15 to **2.31** (`GET /health`) |
| Left mount | `p1000_multi_flex`: **8-channel, 5 to 1000 µL**, firmware 68, calibration offset recorded 2026-06-27, no tip attached |
| Right mount | **nothing attached** |
| Extension mount | gripper v1.3, firmware 68, calibration offset recorded 2025-12-11 |
| Modules | none attached |
| Deck calibration | status OK (the stored calibration is dated 2022-09-06) |
| Deck fixtures | single slots everywhere, a **trash bin at A3**, no waste chute, no staging-area slots (column 4) configured |
| Camera | enabled, live stream 1280x720 at 30 fps. `POST /camera/capturePreviewImage` with body `{"data": {}}` returned a 1920x1080 JPEG in about 2.7 s. Zoom (1.0 to 2.0), pan, brightness, contrast and saturation are accepted |
| Login | `GET /protocols` and the other reads worked without a token. Writes (upload, create run, play) were not tried |
| Stored on the robot | 32 protocols, 1 run on record, 8.4 GB free on the system partition |

## What the deck looked like (camera, 2x zoom)

A visual read of the picture, not verified against anything the robot knows (the robot does not sense labware).

| Slot | What I could see |
|---|---|
| A1 | teal tip rack with tips, label looks like "1000 µL Filter Tip" |
| A2 | purple tip rack with tips, label looks like "50 µL Filter Tip" |
| A3 | trash bin (black, matches the deck configuration) |
| B1 | 12-trough reservoir (NEST 12 x 15 mL), per `ebrinz`'s notes |
| B2 | 96 deep-well stock plate, per `ebrinz`'s notes |
| B3 | Armadillo 96-well PCR plate on a deep-well plate used as a riser (about 40 mm up), per `ebrinz`'s notes |
| C1 to C3, D1 to D3 | empty |

The labels are blurry even at 2x zoom. A person should read them.

## What this changes

- The 8-channel is on the **left** mount: `("flex_8channel_1000", "left")`. There is no second pipette, so nothing handles 1 to 5 µL and the 5 µL minimum stands.
- The tips on the deck are probably **filter** tips. Their load names are `opentrons_flex_96_filtertiprack_1000ul` and `opentrons_flex_96_filtertiprack_50ul`, not the non-filter names the generator uses today. Check the box labels and use the matching names.
- No staging slots are configured, so do not plan gripper moves to column 4. Moves among A1 to D3 are fine.
- The trash bin in A3 matches `load_trash_bin("A3")`. A waste chute in a protocol would conflict with the robot's deck configuration.
- No modules, so no shaking or temperature control.
- The camera works, so `capture_image` and the snapshot endpoints are real, and a deck picture could be used to check the loaded deck before a run.
- The robot accepts API level 2.31, so `apiLevel` 2.30 is fine.

## Not verified

- The labware in B1 to B3 comes from `ebrinz`'s notes and matches the camera picture, but nothing else checked it. The tip sizes in A1 and A2 come from the labels only.
- Whether writes (upload, create run, play) need a login.
- Whether the stored deck calibration from 2022 is good enough in practice. Its status is OK.
- Image quality for reading small labels.

## Reproduce

```bash
curl -s -H "Opentrons-Version: *" http://<FLEX_IP>:31950/health
curl -s -H "Opentrons-Version: *" http://<FLEX_IP>:31950/instruments
curl -s -H "Opentrons-Version: *" http://<FLEX_IP>:31950/deck_configuration
curl -s -X POST -H "Opentrons-Version: *" -H "Content-Type: application/json" -d '{"data": {}}' http://<FLEX_IP>:31950/camera/capturePreviewImage -o deck.jpg
```

Find the IP on the touchscreen (Settings, Network) or in the Opentrons App.
