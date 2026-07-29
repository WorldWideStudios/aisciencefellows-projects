"""
Parse Team_3_Data.pdf plate reader output (ELx808 columnar format) into tidy CSVs.

The text-extracted PDF stores data column-by-column within each page chunk:
  Section header (e.g. "490")
  "Time"
  <time values...>
  ""
  "T° 490"
  <temp values...>
  ""
  "A1"
  <A1 values...>
  ""
  "A2"
  ...

Outputs:
  data/490nm_kinetic.csv    - kinetic reads at 490 nm
  data/405nm_kinetic.csv    - kinetic reads at 405 nm
  data/plate_map.csv        - well → condition/compound annotation
"""

import re
import csv
from pathlib import Path

PDF_TXT = "/tmp/team3_data.txt"
OUT_DIR = Path("/Users/huc44/Projects/zeon/data")
OUT_DIR.mkdir(exist_ok=True)

# ── plate map — CORRECTED ACTUAL COMPOUNDS ────────────────────────────────────
# Source plate PHD215176 well contents differed from workflow plan.
# Assay plate well positions are unchanged; only the compound identities below
# reflect what was actually dispensed (verified against PHD215176 well manifest).
#
# Slot | Intended (plan)          | Actual (PHD215176 well)
# -----+--------------------------+----------------------------------
#  +   | T19860 Clavulanic Acid   | T19860 Clavulanic Acid ✓ (correct)
#  1   | T1262  Tazobactam        | T0138  Cefpiramide acid      (A2)
#  2   | T6685  Sulbactam sodium  | T0198  Ceftiofur sodium       (A3)
#  3   | T14081 Enmetazobactam    | T0199  Cephradine             (A4)
#  4   | T1005  Amoxicillin       | T0234  Methicillin sodium salt (A5)
#  5   | T1008  Cephalexin        | T0366  Cefadroxil             (A6)
#  6   | T0224  Meropenem         | T1001  Dicloxacillin Na·H2O   (A7)
#  7   | T0985  Oxacillin Na salt | T1005  Amoxicillin            (A8)
#  8   | T0138  Cefpiramide acid  | T1008  Cephalexin             (A9)
#  9   | T8390  Cefazolin         | T1031  Cloxacillin Na·H2O     (A10)

PLATE_MAP = {
    # Positive control – T19860 Clavulanic Acid, 1 uM  [CORRECT]
    "F3":  "Positive_Control_ClavulanicAcid_1uM",
    "F7":  "Positive_Control_ClavulanicAcid_1uM",
    "G11": "Positive_Control_ClavulanicAcid_1uM",
    # No-enzyme negative control
    "D3":  "Negative_Control_NoEnzyme",
    "D7":  "Negative_Control_NoEnzyme",
    "E11": "Negative_Control_NoEnzyme",
    # Vehicle + TEM-1 control (DMSO vehicle)
    "B3":  "Vehicle_TEM1_Control",
    "B7":  "Vehicle_TEM1_Control",
    "C11": "Vehicle_TEM1_Control",
    # Slot 1 – ACTUAL: T0138 Cefpiramide acid (intended: T1262 Tazobactam)
    "B2":  "T0138_CefpiramideAcid_50uM",
    "D2":  "T0138_CefpiramideAcid_50uM",
    "F2":  "T0138_CefpiramideAcid_50uM",
    # Slot 2 – ACTUAL: T0198 Ceftiofur sodium (intended: T6685 Sulbactam sodium)
    "B4":  "T0198_CeftiofurSodium_50uM",
    "D4":  "T0198_CeftiofurSodium_50uM",
    "F4":  "T0198_CeftiofurSodium_50uM",
    # Slot 3 – ACTUAL: T0199 Cephradine (intended: T14081 Enmetazobactam)
    "B6":  "T0199_Cephradine_50uM",
    "D6":  "T0199_Cephradine_50uM",
    "F6":  "T0199_Cephradine_50uM",
    # Slot 4 – ACTUAL: T0234 Methicillin sodium salt (intended: T1005 Amoxicillin)
    "B8":  "T0234_MethicillinSodium_50uM",
    "D8":  "T0234_MethicillinSodium_50uM",
    "F8":  "T0234_MethicillinSodium_50uM",
    # Slot 5 – ACTUAL: T0366 Cefadroxil (intended: T1008 Cephalexin)
    "B10": "T0366_Cefadroxil_50uM",
    "D10": "T0366_Cefadroxil_50uM",
    "F10": "T0366_Cefadroxil_50uM",
    # Slot 6 – ACTUAL: T1001 Dicloxacillin sodium hydrate (intended: T0224 Meropenem)
    "C5":  "T1001_DicloxacillinSodium_50uM",
    "E5":  "T1001_DicloxacillinSodium_50uM",
    "G5":  "T1001_DicloxacillinSodium_50uM",
    # Slot 7 – ACTUAL: T1005 Amoxicillin (intended: T0985 Oxacillin sodium salt)
    "C9":  "T1005_Amoxicillin_50uM",
    "E9":  "T1005_Amoxicillin_50uM",
    "G9":  "T1005_Amoxicillin_50uM",
    # Slot 8 – ACTUAL: T1008 Cephalexin (intended: T0138 Cefpiramide acid)
    "C3":  "T1008_Cephalexin_50uM",
    "E3":  "T1008_Cephalexin_50uM",
    "G3":  "T1008_Cephalexin_50uM",
    # Slot 9 – ACTUAL: T1031 Cloxacillin sodium monohydrate (intended: T8390 Cefazolin)
    "C7":  "T1031_CloxacillinSodium_50uM",
    "E7":  "T1031_CloxacillinSodium_50uM",
    "G7":  "T1031_CloxacillinSodium_50uM",
}

# ── helpers ────────────────────────────────────────────────────────────────────

WELL_RE = re.compile(r'^[A-H](1[0-2]|[1-9])$')

def is_well(s):
    return bool(WELL_RE.match(s))

def is_time(s):
    return bool(re.match(r'^\d+:\d{2}:\d{2}$', s))

def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def time_to_sec(t):
    h, m, s = t.split(":")
    return int(h)*3600 + int(m)*60 + int(s)

def sec_to_hms(sec):
    return f"{sec//3600}:{(sec%3600)//60:02d}:{sec%60:02d}"

# ── section splitter ───────────────────────────────────────────────────────────

def split_into_column_blocks(lines):
    """
    Split the token stream into column blocks.
    Returns list of (label, [values]) where label is either a well ID, 'Time', or 'T°'.
    Each block is a contiguous run of float/time tokens following a label line.
    """
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        tok = lines[i].strip()
        if not tok or "of 23" in tok or "continued" in tok or tok in ("Results",):
            i += 1
            continue
        # Is this a label? (well, Time, T° xxx, 490, 405, section headers)
        if tok == "Time" or is_well(tok) or tok.startswith("T°"):
            label = "T°" if tok.startswith("T°") else tok
            # collect following values
            j = i + 1
            values = []
            while j < n:
                v = lines[j].strip()
                if not v:
                    j += 1
                    # blank line may separate blocks; if the next real token is also a value, continue
                    # peek ahead
                    k = j
                    while k < n and not lines[k].strip():
                        k += 1
                    if k < n and (is_float(lines[k].strip()) or is_time(lines[k].strip())):
                        continue
                    else:
                        break
                if is_time(v) or is_float(v):
                    values.append(v)
                    j += 1
                else:
                    # hit a new label or section marker
                    break
            blocks.append((label, values))
            i = j
        else:
            i += 1
    return blocks


def parse_wavelength(lines, wavelength):
    """
    Extract all well data for the given wavelength from the token stream.
    Returns {well -> [abs_values]} paired with a shared time list.
    """
    wl_str = str(wavelength)
    wl_cont = f"{wl_str} (continued)"

    # Find all line ranges that belong to this wavelength section
    # A section starts at a line == wl_str or wl_cont
    # and ends at the next top-level section marker
    section_tokens = []
    in_wl = False
    n = len(lines)
    for i, raw in enumerate(lines):
        tok = raw.strip()
        if tok == wl_str or tok == wl_cont:
            in_wl = True
            continue
        # Top-level section changes
        if in_wl and tok in ("405", "490", "Results") and tok != wl_str:
            in_wl = False
            continue
        if in_wl:
            section_tokens.append(raw)

    # Now parse the columnar blocks within this wavelength's lines
    blocks = split_into_column_blocks(section_tokens)

    # Gather time list and well values
    time_list = []
    well_data = {}

    for label, values in blocks:
        if label == "Time":
            # Each page chunk contributes a partial time block; accumulate all
            new_times = [time_to_sec(v) for v in values if is_time(v)]
            # Append only times not already seen (avoid duplicates from page headers)
            existing = set(time_list)
            for t in new_times:
                if t not in existing:
                    time_list.append(t)
                    existing.add(t)
            time_list.sort()
        elif label == "T°":
            pass  # skip temperature
        elif is_well(label):
            floats = [float(v) for v in values if is_float(v)]
            if label not in well_data:
                well_data[label] = floats
            else:
                well_data[label].extend(floats)

    return time_list, well_data


def write_kinetic_csv(time_list, well_data, wavelength, out_path):
    rows_order = "ABCDEFGH"
    all_wells = sorted(well_data.keys(),
                       key=lambda w: (rows_order.index(w[0]), int(w[1:])))

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_sec", "time_hms"] + all_wells)
        n_times = len(time_list)
        for idx, t in enumerate(time_list):
            row = [t, sec_to_hms(t)]
            for w in all_wells:
                vals = well_data[w]
                row.append(vals[idx] if idx < len(vals) else "")
            writer.writerow(row)

    print(f"  {wavelength} nm: {len(time_list)} timepoints × {len(all_wells)} wells → {out_path}")
    return all_wells


def write_plate_map(all_wells, plate_map, out_path):
    rows_order = "ABCDEFGH"
    sorted_wells = sorted(all_wells,
                          key=lambda w: (rows_order.index(w[0]), int(w[1:])))
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["well", "condition", "row", "col"])
        for w in sorted_wells:
            cond = plate_map.get(w, "Unassigned")
            writer.writerow([w, cond, w[0], int(w[1:])])
    print(f"  Plate map: {len(sorted_wells)} wells → {out_path}")


# ── main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Reading PDF text...")
    with open(PDF_TXT) as f:
        lines = f.readlines()

    print("\nParsing 490 nm kinetic data...")
    times_490, data_490 = parse_wavelength(lines, 490)
    wells_490 = write_kinetic_csv(times_490, data_490, 490, OUT_DIR / "490nm_kinetic.csv")

    print("\nParsing 405 nm kinetic data...")
    times_405, data_405 = parse_wavelength(lines, 405)
    wells_405 = write_kinetic_csv(times_405, data_405, 405, OUT_DIR / "405nm_kinetic.csv")

    print("\nWriting plate map...")
    all_wells = sorted(set(wells_490) | set(wells_405))
    write_plate_map(all_wells, PLATE_MAP, OUT_DIR / "plate_map.csv")

    # Sanity check
    print("\n── Sanity (490 nm well values at t=0 and t=900 s) ──")
    key_wells = [("B2", "Tazobactam"), ("B3", "Vehicle_TEM1"), ("D3", "NoEnzyme"),
                 ("F3", "Pos_Ctrl"), ("D6", "Enmetazobactam"), ("F6", "Enmetazobactam")]
    if times_490:
        t0_idx = 0
        tf_idx = len(times_490) - 1
        for w, label in key_wells:
            if w in data_490:
                vals = data_490[w]
                print(f"  {w:4s} ({label:20s}): t=0 {vals[t0_idx]:.3f}  t=15min {vals[tf_idx]:.3f}")

    print("\nDone.")
