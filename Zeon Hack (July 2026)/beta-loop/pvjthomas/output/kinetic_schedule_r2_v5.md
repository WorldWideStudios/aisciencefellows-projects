# Nitrocefin kinetic read schedule — Round 2 v5

**Label:** `r2-discovery-v5` · **Plate map:** [`data/screens/2/v5/plate_map.json`](../../data/screens/2/v5/plate_map.json)

## Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Wavelength | **490 nm** (kinetic) · **450/490 nm** (endpoint fallback) | Score on A490 in both modes |
| `temperature_c` | 25.0 | Literature TEM-1 nitrocefin assays |
| `equilibration_s` | 120.0 | 2 min warm-up at setpoint (ice-cold nitrocefin) |
| `interval_s` | 30 | Gen5 minimum kinetic interval on ELx808 |
| `kinetic_duration_s` | 600.0 | 10 min post-equilibration window |
| `total_plate_time_s` | 720.0 | Equilibration + kinetics (12 min in reader) |
| Slope window | 180.0–480.0 s | Kinetic time; 300.0–600.0 s from lid close |

**Read count:** 21 timepoints (initial + every 30 s to 600 s)

## Gen5 checklist

- Enable incubation at 25 °C; Gen5 waits for setpoint before the first read when the IU incubator is installed.
- Set read mode to kinetic (not endpoint-only).
- Schedule 21 reads: initial, then every 30s until 600s kinetic time.
- Hold at 25 °C for 120s after lid close before the first kinetic read (cold-start warm-up).
- Score slope on kinetic times 180–480s (300–600s from plate close).
- Robot control: temperature is not set by platereader_measure today — bake these values into the saved Gen5 protocol or add AutoGUI steps.

## Read timeline

| # | Kinetic t (s) | Wait before (s) | From lid close (s) | Label |
|---|---------------|-----------------|--------------------|-------|
| 1 | 0 | 0 | 120 | `initial` |
| 2 | 30 | 30 | 150 | `t030s` |
| 3 | 60 | 30 | 180 | `t060s` |
| 4 | 90 | 30 | 210 | `t090s` |
| 5 | 120 | 30 | 240 | `t120s` |
| 6 | 150 | 30 | 270 | `t150s` |
| 7 | 180 | 30 | 300 | `t180s` |
| 8 | 210 | 30 | 330 | `t210s` |
| 9 | 240 | 30 | 360 | `t240s` |
| 10 | 270 | 30 | 390 | `t270s` |
| 11 | 300 | 30 | 420 | `t300s` |
| 12 | 330 | 30 | 450 | `t330s` |
| 13 | 360 | 30 | 480 | `t360s` |
| 14 | 390 | 30 | 510 | `t390s` |
| 15 | 420 | 30 | 540 | `t420s` |
| 16 | 450 | 30 | 570 | `t450s` |
| 17 | 480 | 30 | 600 | `t480s` |
| 18 | 510 | 30 | 630 | `t510s` |
| 19 | 540 | 30 | 660 | `t540s` |
| 20 | 570 | 30 | 690 | `t570s` |
| 21 | 600 | 30 | 720 | `t600s` |

