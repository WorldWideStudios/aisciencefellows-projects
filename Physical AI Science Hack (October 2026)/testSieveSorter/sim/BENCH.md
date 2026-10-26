# Bench protocol for tonight

The sim gets tuned on what you measure tonight, then has to predict a run it never saw. Every number goes in a CSV in `sim\bench\`. Copy the template and keep its header row. Rows starting with `#` are examples and are ignored. Units are mm, g and s.

## Kit

- Steel ruler and calipers.
- A phone that films slow motion (240 fps, or 120), plus a clamp or tripod.
- A kitchen scale (0.01 g), a measuring cup with ml marks, and a stopwatch.
- White paper and a phone inclinometer app.
- Tape and a marker.

## Zone names

The counting sheets use the sim's zone names. Print them for a design from `sim\`:

```
python calibrate.py --zones "inserts:mesh5,mesh2"
```

- `inserts:mesh5,mesh2` (current mesh inserts): `on_mesh5, on_mesh2, catch, between, lost`
- `inserts:5mm,2mm` (future printed inserts): `on_5mm, on_2mm, catch, between, lost`
- `between` means stuck in a hole or wedged between parts (a jam). `lost` means it left the unit.

Before counting, agree which physical place each name means.

## 1. Stroke (the most important measurement)

Goes into `stroke_<name>.csv`; copy `stroke_example.csv`, which holds `t_s,x_mm` rows.

1. Tape a ruler to the bench along the stroke, next to the tray. Put a bright dot on the tray edge.
2. Film the dot and the ruler square-on at 120 to 240 fps, for at least 5 full strokes. Film once at 50 mm/s and once at the firmware default of 5 mm/s.
3. With Tracker (free, physlets.org/tracker):
   - open the video;
   - set the calibration stick on two ruler marks and type the distance in mm;
   - put the x axis along the stroke;
   - add a point-mass track and click the dot on each frame (or use Autotracker);
   - copy the t and x columns into the CSV.
4. Without Tracker, step through the video frame by frame and read the dot against the ruler. `t_s` = frame number / fps.
5. **Reversal sharpness (`ramp_s`, the key unknown).** Zoom in on 3 reversals. Count the frames from the moment the tray starts slowing until it is at full speed the other way: `ramp_s` = frames / fps. The sim assumes 0.01 s. This number decides whether dry grains move at all at 5 mm/s, because the jolt at each reversal is about 2 x speed / `ramp_s`.
6. Note any up-and-down motion of the tray.

How the sim uses it:
- In `bench_counts.csv`, set `stroke_profile` to `csv` and `stroke_csv` to the file name. The sim then replays the measured motion.
- The measured `ramp_s` replaces the 0.01 s guess in the firmware stroke used by `sweep.py`.

## 2. Openings

Goes into `openings.csv`, one row per part.

- **Printed inserts and gates:** measure 10 holes, plus the bar width and the screen thickness.
- **Glued wire mesh:** measure the aperture (the gap between wires) in 10 places and the wire diameter in 5. Note which side the mesh is glued on.

How the sim uses it: the designs are built from the CAD numbers. If a measured opening differs by more than 0.1 mm, the design should use the measured value. Mesh aperture and wire diameter set the mesh model in `designs_holder.py`. Open area = aperture² / (aperture + wire)². That is about 29-37% for the printed screens and 50-65% for wire mesh, which is why throughput gets checked in step 6.

## 3. Grains

Goes into `grain_dims.csv`, one row per grain.

1. Take 30 of each kind at random, not the prettiest ones.
2. With calipers, measure length (longest), width and thickness (shortest).
3. Weigh all 30 together and put total / 30 in `mass_mg` on each row.

How the sim uses it: the mean size, the spread and the density (mass / volume) of each kind in `grains.py`.

## 4. Counted runs (the calibration data)

Goes into `bench_counts.csv`, `split` = `fit`.

1. Count out a known mix exactly, the same every run. The sim default is rice 30, quinoa 30, chickpea 8, pasta 8.
2. Pour it the same way each time, spread over the top screen.
3. Run for a fixed 30 to 60 s, timed, then stop.
4. Count every particle of every kind in every zone, including `between` (jams) and `lost`. Each kind's counts must add up to what went in.
5. Do 3 repeats per configuration. Write one row per run, kind and zone; zones with 0 can be left out.
6. Write the stroke the way the firmware sets it:
   - `stroke_profile` = `constant_speed`;
   - `amp_mm` = half the stroke length (a 2 cm stroke is 10);
   - `speed_mm_s` and `ramp_s`.

   For a filmed stroke, use `csv` and `stroke_csv` instead.

How the sim uses it: `calibrate.py` tunes friction and bounce until the simulated fraction of each kind in each zone matches these runs.

## 5. Hold one configuration out

Goes into `bench_counts.csv`, `split` = `holdout`.

1. Before running anything, pick a second configuration that changes one thing: the other inserts (mesh vs printed), or the other speed.
2. Run it 3 times, exactly like step 4. Don't use it for tuning. Ideally a different person counts it, and nobody looks at the sim's prediction first.

How the sim uses it: `calibrate.py` predicts these counts with the tuned parameters and shows predicted vs observed. It calls the fit "validated" only when holdout rows exist, they differ from every fit configuration, and the error is small.

## 6. Clear-out timing (throughput)

Goes into `clear_times.csv`.

1. Use the same known mix. Film the unit from above (normal frame rate is fine) and start a stopwatch with the stroke.
2. For each screen and each kind that should pass it, write down when the last one leaves: a row with `n_remaining` = 0.
3. If you can, also count from the video how many are still on that screen at 10 s, 30 s and 60 s.
4. Write `n_loaded` (how many of that kind went in) on every row.

How the sim uses it: `calibrate.py --clear bench\clear_times.csv` predicts how many are still on each screen at those times, and when each screen clears.

## 7. Spray

Goes into `jets.csv`, one row per nozzle.

- **Liquid:** water or ethanol.
- **Flow:** run the nozzle into the measuring cup for a timed 30 s. Record `collected_ml` and `collect_s`.
- **Nozzle diameter:** calipers or a drill bit.
- **Position:** x, y, z of the nozzle tip relative to the tray centre at rest. x runs along the stroke; z is measured up from under the tray.
- **Angle:** tilt from straight down, and the direction it points (azimuth: 0 = +x, 90 = +y).
- **Footprint:** hold white paper at tray height, give a 1 s burst, and measure the wet spot's diameter and the nozzle's height above the paper.
- **Pulse timing:** on and off times in s; leave blank if it is continuous.

How the sim uses it: `spray.py` builds one jet per row, fixed in the lab while the tray moves:
- `pos_lab` = (x, y, z);
- `dir` from the tilt and azimuth;
- `flow_ml_s` = collected_ml / collect_s;
- `half_angle_deg` = atan(footprint_d / 2 / footprint_height) in degrees;
- `pulse` = (on, off).

## 8. Wet vs dry tilt

Goes into `tilt.csv`.

1. Put 5 grains of one kind on a printed screen.
2. Tilt it slowly and read the angle when they start to slide.
3. Do 5 trials dry, then 5 sprayed wet.
4. Repeat on the wire mesh.

How the sim uses it: friction = tan(angle). The dry value centres the fit grid; the wet value sets the spray's wet friction.

## 9. Real specimens

1. Get a few preserved specimens: compact (beetle, mite), elongate (fly, ant) and long-legged (mosquito, spider).
2. Measure them like grains into `grain_dims.csv`, with `kind` = `insect_compact`, `insect_elongate` or `insect_longleg`, and the species in `note`. Photograph each on mm paper.
3. Run a few through the unit and count them as in step 4. Note any snagging and damage.

How the sim uses it: the sizes in `insects.py`. Without real specimens, insect results are labelled exploratory.

## Then

From `sim\`:

```
python calibrate.py bench\bench_counts.csv --clear bench\clear_times.csv
python sweep.py compare
```

`calibrate.py` writes `out\calibration\calibration.json`. `sweep.py compare` then uses the fitted parameter sets (low, best and high friction) instead of the default 0.3 / 0.4 / 0.5.
