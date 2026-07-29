# Kinetics interpretation request

Context marker: `LLM_INTERPRETATION_INPUT` v1.0

## Your tasks
- Summarize QC gate pass/fail and plausible root causes (controls, timing, slope window).
- Interpret notable pattern buckets (flat rows, high A0, rising, peak-decline, wavelength divergence).
- Reconcile compound hit calls with tier/substrate priors; flag surprises and timing suspects.
- Recommend follow-up (adjust slope window, re-run controls, dose-response picks) if warranted.

## Run metadata (deterministic)
- Round 3 | slope window 180.0–480.0 s
- Incubator setpoint: 37.0 °C
- Kinetic duration: 900.0 s

## QC gates (deterministic)
- pos_ctrl_median_pct: 99.4
- q1_pass: True
- q1t_timing_stagger: False
- q1t_timing_unknown: False
- q2_endpoint_pass: True
- q2_pass: False
- q3_pass: True

## Hits (deterministic)
- T1262: 100.0% @ 1.0 µM
- T14081: 98.1% @ 50 µM
- T0224: 98.1% @ 50 µM
- T6685: 91.8% @ 50 µM

## Pattern buckets (deterministic)
- Flat rows: {'A': ['A3', 'A4', 'A6', 'A9', 'A10', 'A11'], 'H': ['H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'H9', 'H10', 'H11', 'H12']}
- High initial signal: B10 A0=0.152, D10 A0=0.141, B11 A0=0.131, C3 A0=0.12, C7 A0=0.116, C9 A0=0.115
- Rising: G9 (0.094→0.215), E9 (0.115→0.23), G3 (0.083→0.2), E7 (0.1→0.224), G7 (0.083→0.208), E3 (0.112→0.22)
- Peak then decline: B11 peak@0:00:00

## Compound scores (deterministic)
- T1262: 100.0% (confirmed_hit)
- T14081: 98.1% (confirmed_hit)
- T0224: 98.1% (surprise_hit)
- T6685: 91.8% (confirmed_hit)
- T0985: 13.3% (confirmed_substrate)
- T0138: 8.2% (inactive)
- T8390: 4.4% (inactive)

## Full deterministic pattern summary

# Kinetics pattern summary

Primary wavelength: 490 nm
Early slope window: 30–210 s

## Notable signal patterns (490 nm)

- **Row A** (A3, A4, A6, A9, A10, A11): flat baseline ~0.039 (range < 0.005)
- **Row H** (H2, H3, H4, H5, H6, H7, H8, H9, H10, H11, H12): flat baseline ~0.041 (range < 0.005)

**High initial signal (t=0):**
- B10 (T1008): A0 = 0.152
- D10 (T1008): A0 = 0.141
- B11: A0 = 0.131
- C3 (T0138): A0 = 0.12
- C7 (T8390): A0 = 0.116
- C9 (T0985): A0 = 0.115
- E9 (T0985): A0 = 0.115
- F10 (T1008): A0 = 0.113

**Rising kinetics (early-window slope above no-TEM-1 baseline):**
- G9 (T0985): 0.094 → 0.215 over run (slope_early = 0.00043333)
- E9 (T0985): 0.115 → 0.23 over run (slope_early = 0.00042222)
- G3 (T0138): 0.083 → 0.2 over run (slope_early = 0.00042222)
- E7 (T8390): 0.1 → 0.224 over run (slope_early = 0.00041667)
- G7 (T8390): 0.083 → 0.208 over run (slope_early = 0.00041667)
- E3 (T0138): 0.112 → 0.22 over run (slope_early = 0.00040556)
- D10 (T1008): 0.141 → 0.238 over run (slope_early = 0.00036111)
- F10 (T1008): 0.113 → 0.214 over run (slope_early = 0.00036111)
- C7 (T8390): 0.116 → 0.225 over run (slope_early = 0.00035)
- C3 (T0138): 0.12 → 0.219 over run (slope_early = 0.00034444)

**Peak then decline:**
- B11: peak 0.131 at 0:00:00, ends 0.121

## Wavelength divergence (490 vs 405 nm)

- D6 (T14081): A0 0.054 vs 0.235
- F6 (T14081): A0 0.058 vs 0.235
- D4 (T6685): A0 0.058 vs 0.234
- D3 [no_tem1]: A0 0.054 vs 0.229
- D7 [no_tem1]: A0 0.053 vs 0.227
- E11 [no_tem1]: A0 0.053 vs 0.225
- F4 (T6685): A0 0.053 vs 0.223
- B6 (T14081): A0 0.053 vs 0.214

## Gen5 Results highlights (Max V, QC cross-check)

- H3 @ 490 nm: Max V = 46.0, lagtime = 0:00:00
- C3 (T0138) @ 490 nm: Max V = 42.0, lagtime = 0:00:00
- D3 [no_tem1] @ 490 nm: Max V = 42.0, lagtime = 0:00:00
- G3 (T0138) @ 490 nm: Max V = 42.0, lagtime = 0:00:00
- H1 @ 490 nm: Max V = 42.0, lagtime = 0:00:00
- G10 @ 490 nm: Max V = 40.0, lagtime = 0:00:00
- F10 (T1008) @ 490 nm: Max V = 38.0, lagtime = 0:00:00
- G1 @ 490 nm: Max V = 36.0, lagtime = 0:00:00
- B3 @ 490 nm: Max V = 34.0, lagtime = 0:00:00
- F1 @ 490 nm: Max V = 32.0, lagtime = 0:00:00

**Negative slope / Max V:**
- A2: Gen5 Max V = -8.0 @ 490 nm
- A3: Gen5 Max V = -8.0 @ 490 nm
- A4: Gen5 Max V = -8.0 @ 405 nm
- A7: Gen5 Max V = -10.0 @ 490 nm
- A7: Gen5 Max V = -8.0 @ 405 nm
- A8: Gen5 Max V = -18.0 @ 405 nm
- A9: Gen5 Max V = -8.0 @ 405 nm
- A10: Gen5 Max V = -16.0 @ 405 nm

---
Respond with: (1) QC assessment, (2) notable patterns, (3) hit confidence, (4) recommended next steps.