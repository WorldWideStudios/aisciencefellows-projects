# Novel-insect test: food analogs that are in no insect database

Photos from the Track A bench, Oct 24 2026. None of these objects are insects, so none should be
triaged **known**: confident-but-out-of-range detections should be **novel (VIP)** and anything the
insect teacher doesn't recognise **unknown**.

| Photo | Scale | Contents |
|---|---|---|
| 01_dishes_ruler.jpg | steel ruler (cm + inch), photographed at an angle → local scale 4.3–6.2 px/mm | 7 dishes, top→bottom: (1) mixed sample: wild rice, red rice, ditalini, white rice, pasta shard; (2) chia; (3) couscous; (4) ditalini; (5) white rice; (6) red rice ×2; (7) brown + red rice |
| 02_dishes_closeup.jpg | none (serrated dish rims are rejected as a ruler) | couscous, chia, ditalini, white rice |
| 03_mixed_dish_ruler.jpg | metric ruler, ~12.8 px/mm | mixed dish: wild rice, white rice, ditalini, lasagna shard, red rice, chia, debris |
| 04_mixed_dish_closeup.jpg | none | same mixed dish, close-up |
| 05_analog_sources.jpg | none | packaging: campanelle, ditalini, farfalle, fideo, rice mix, white rice, chia, couscous |

Run: `python -m baebugs.analog_test --images docs/analog_test/0*.jpg --weights <best.pt> --ref <museum truth> <synthetic truth> --out <dir>`
