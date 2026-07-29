# Kinetics interpretation request

Context marker: `LLM_INTERPRETATION_INPUT` v1.0

## Your tasks
- Summarize QC gate pass/fail and plausible root causes (controls, timing, slope window).
- Interpret notable pattern buckets (flat rows, high A0, rising, peak-decline, wavelength divergence).
- Reconcile compound hit calls with tier/substrate priors; flag surprises and timing suspects.
- Recommend follow-up (adjust slope window, re-run controls, dose-response picks) if warranted.

## Run metadata (deterministic)
- Round 2 | slope window 180.0–480.0 s
- Incubator setpoint: 37.0 °C
- Kinetic duration: 900.0 s

## QC gates (deterministic)
- pos_ctrl_median_pct: 83.3
- q1_pass: True
- q1t_timing_stagger: True
- q1t_timing_unknown: False
- q2_endpoint_pass: True
- q2_pass: False
- q3_pass: True

## Hits (deterministic)
- T0224: 97.0% @ 50 µM
- T1005: 68.2% @ 50 µM

## Pattern buckets (deterministic)
- Flat rows: {'A': ['A1', 'A2', 'A3', 'A5', 'A7', 'A8'], 'H': ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'H9', 'H10', 'H11', 'H12']}
- High initial signal: F6 A0=0.325, D6 A0=0.298, G5 A0=0.28, B6 A0=0.278, D4 A0=0.266, B4 A0=0.257
- Rising: D10 (0.2→0.278), E9 (0.068→0.179), G3 (0.071→0.126), E5 (0.195→0.233), B7 (0.095→0.135), C7 (0.114→0.139)
- Peak then decline: G5 peak@0:00:00, D10 peak@0:05:30, G9 peak@0:05:30, C7 peak@0:07:00, E5 peak@0:06:30, B10 peak@0:05:00

## Compound scores (deterministic)
- T0224: 97.0% (surprise_hit)
- T1005: 68.2% (surprise_hit)
- T6685: 27.3% (surprise_miss)

## Full deterministic pattern summary

# Kinetics pattern summary

Primary wavelength: 490 nm
Early slope window: 30–210 s

## Notable signal patterns (490 nm)

- **Row A** (A1, A2, A3, A5, A7, A8): flat baseline ~0.041 (range < 0.005)
- **Row H** (H1, H2, H3, H4, H5, H6, H7, H8, H9, H10, H11, H12): flat baseline ~0.04 (range < 0.005)

**High initial signal (t=0):**
- F6 (T14081): A0 = 0.325
- D6 (T14081): A0 = 0.298
- G5 (T0224): A0 = 0.28
- B6 (T14081): A0 = 0.278
- D4 (T6685): A0 = 0.266
- B4 (T6685): A0 = 0.257
- D2 (T1262): A0 = 0.243
- C3 (T0138): A0 = 0.22

**Rising kinetics (early-window slope above no-TEM-1 baseline):**
- D10 (T1008): 0.2 → 0.278 over run (slope_early = 0.00041111)
- E9 (T0985): 0.068 → 0.179 over run (slope_early = 0.00039444)
- G3 (T0138): 0.071 → 0.126 over run (slope_early = 0.00020556)
- E5 (T0224): 0.195 → 0.233 over run (slope_early = 0.00017222)
- B7 [vehicle]: 0.095 → 0.135 over run (slope_early = 0.00016667)
- C7 (T8390): 0.114 → 0.139 over run (slope_early = 0.00013333)
- B10 (T1008): 0.197 → 0.209 over run (slope_early = 0.00010556)
- E7 (T8390): 0.139 → 0.158 over run (slope_early = 8.889e-05)
- B3 [vehicle]: 0.095 → 0.12 over run (slope_early = 8.333e-05)
- E3 (T0138): 0.139 → 0.158 over run (slope_early = 6.667e-05)

**Peak then decline:**
- G5 (T0224): peak 0.28 at 0:00:00, ends 0.218
- D10 (T1008): peak 0.309 at 0:05:30, ends 0.278
- G9 (T0985): peak 0.182 at 0:05:30, ends 0.154
- C7 (T8390): peak 0.159 at 0:07:00, ends 0.139
- E5 (T0224): peak 0.248 at 0:06:30, ends 0.233
- B10 (T1008): peak 0.223 at 0:05:00, ends 0.209
- C3 (T0138): peak 0.226 at 0:08:00, ends 0.213
- C9 (T0985): peak 0.164 at 0:05:30, ends 0.151

## Wavelength divergence (490 vs 405 nm)

- D8 (T1005): A0 0.102 vs 0.414
- F8 (T1005): A0 0.071 vs 0.352
- F4 (T6685): A0 0.105 vs 0.367
- F7 (T19860): A0 0.068 vs 0.298
- F3 (T19860): A0 0.059 vs 0.252
- D7 [no_tem1]: A0 0.056 vs 0.248
- D3 [no_tem1]: A0 0.062 vs 0.25
- E11 [no_tem1]: A0 0.057 vs 0.23

## Gen5 Results highlights (Max V, QC cross-check)

- F3 (T19860) @ 405 nm: Max V = 32.0, lagtime = 0:09:11
- F4 (T6685) @ 405 nm: Max V = 32.0, lagtime = 0:09:15
- G3 (T0138) @ 490 nm: Max V = 30.0, lagtime = 0:00:04
- B2 (T1262) @ 405 nm: Max V = 26.0, lagtime = 0:06:16
- B6 (T14081) @ 405 nm: Max V = 26.0, lagtime = 0:09:12
- F1 @ 405 nm: Max V = 26.0, lagtime = 0:06:09
- F10 (T1008) @ 490 nm: Max V = 26.0, lagtime = 0:00:02
- B1 @ 405 nm: Max V = 24.0, lagtime = 0:06:15
- B5 @ 405 nm: Max V = 22.0, lagtime = 0:09:08
- B4 (T6685) @ 405 nm: Max V = 20.0, lagtime = 0:06:09

**Negative slope / Max V:**
- A1: Gen5 Max V = -2.0 @ 490 nm
- A1: Gen5 Max V = -6.0 @ 405 nm
- A3: Gen5 Max V = -4.0 @ 490 nm
- A3: Gen5 Max V = -8.0 @ 405 nm
- A4: Gen5 Max V = -10.0 @ 405 nm
- A5: Gen5 Max V = -8.0 @ 405 nm
- A6: Gen5 Max V = -6.0 @ 490 nm
- A6: Gen5 Max V = -6.0 @ 405 nm

---
Respond with: (1) QC assessment, (2) notable patterns, (3) hit confidence, (4) recommended next steps.