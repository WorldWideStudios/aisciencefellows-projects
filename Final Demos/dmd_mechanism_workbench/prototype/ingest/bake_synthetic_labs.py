"""Generate synthetic clinical labs for every patient in patient_phenotype
and write to mechanism.sqlite.patient_labs.

Values are deterministic per patient (seeded on cohort#patient_id), so
the same patient always shows the same labs across bake runs. Ranges
are drawn from published DMD/BMD literature and correlate with
phenotype × age × variant position.

This is the SOURCE OF TRUTH for the labs surfaced in the workbench. If
you want to swap in real longitudinal labs later, replace the generator
with an ingest that reads a CSV/registry — the schema and downstream
consumers stay the same.

Reference sources: Birnkrant 2018 (DMD Care Considerations); Muntoni
2003; Mercuri 2016 (NSAA); Bushby 1993 (BMD trajectories); Ricotti 2016
(Dp140 → IQ); Pillers 1993 (Dp260 → ERG); Haenggi 2006 (Dp71 → kidney).

Idempotent — wipes prior 'synthetic_v1' rows for each patient before
insert. Safe to re-run.

Migration-safe — creates the patient_labs table if it doesn't yet
exist (so this can be applied to an already-built DB without a full
rebuild).

Run:
    python3 -m prototype.ingest.bake_synthetic_labs
"""
from __future__ import annotations

import random
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "mechanism.sqlite"

DATA_SOURCE = "synthetic_v1"

# One row per assay we generate. Order matches the biological hierarchy
# used in the UI (cell → tissue → phenotype), and this list is the only
# place that has to change if you add / rename an assay.
# (key, layer, tissue_or_None, unit, ref_low, ref_high, label)
ASSAYS: list[tuple[str, str, str | None, str, float, float, str]] = [
    # cell-type layer — muscle-membrane damage biomarkers
    ("CK",        "cellType",   "muscle",       "U/L",           40,   200,  "Creatine kinase"),
    ("aldolase",  "cellType",   "muscle",       "U/L",           1.0,  7.5,  "Aldolase"),
    ("LDH",       "cellType",   "muscle",       "U/L",          140,   280,  "Lactate dehydrogenase"),

    # tissue: skeletal muscle
    ("MRI_ff_VL", "tissueType", "skeletal",     "%",              5,    15,  "MRI fat fraction (vastus lateralis)"),

    # tissue: cardiac
    ("LVEF",      "tissueType", "cardiac",      "%",             55,    70,  "Left ventricular ejection fraction"),
    ("NT_proBNP", "tissueType", "cardiac",      "pg/mL",          0,   125,  "NT-proBNP"),
    ("LGE",       "tissueType", "cardiac",      "presence",       0,     0,  "Late gadolinium enhancement (fibrosis)"),

    # tissue: respiratory
    ("FVC_pct",   "tissueType", "respiratory",  "% predicted",   80,   120,  "FVC (% predicted)"),
    ("PCF",       "tissueType", "respiratory",  "L/min",        270,   700,  "Peak cough flow"),

    # tissue: CNS (H04)
    ("IQ",        "tissueType", "CNS",          "FSIQ",          85,   115,  "Full-scale IQ"),

    # tissue: retina (H04)
    ("ERG_bwave", "tissueType", "retina",       "µV",           150,   350,  "ERG b-wave amplitude"),

    # tissue: kidney (H04)
    ("UACR",      "tissueType", "kidney",       "mg/g",           0,    30,  "Urine albumin/creatinine ratio"),

    # phenotype — motor function
    ("m6MWT",     "phenotype",  None,           "meters",       400,   600,  "6-minute walk test"),
    ("NSAA",      "phenotype",  None,           "score/34",      28,    34,  "North Star Ambulatory Assessment"),
    ("TTS",       "phenotype",  None,           "seconds",        0,     5,  "Time to stand from supine"),
]

SCHEMA_MIGRATION = """
CREATE TABLE IF NOT EXISTS patient_labs (
  cohort      TEXT NOT NULL,
  patient_id  TEXT NOT NULL,
  assay_key   TEXT NOT NULL,
  label       TEXT NOT NULL,
  layer       TEXT NOT NULL,
  tissue      TEXT,
  unit        TEXT NOT NULL,
  value       REAL NOT NULL,
  ref_low     REAL NOT NULL,
  ref_high    REAL NOT NULL,
  flag        TEXT NOT NULL,
  data_source TEXT NOT NULL,
  PRIMARY KEY (cohort, patient_id, assay_key)
);
CREATE INDEX IF NOT EXISTS ix_pl_pat   ON patient_labs(cohort, patient_id);
CREATE INDEX IF NOT EXISTS ix_pl_layer ON patient_labs(layer);
"""


def _rng(cohort: str, pid: str) -> random.Random:
    return random.Random(f"{cohort}#{pid}")


def _pheno_bias(phen: str) -> float:
    return {"DMD": 1.0, "IMD": 0.55, "BMD": 0.30, "pending": 0.75}.get(phen, 0.75)


def _age_factor(age: float | None, decline_start: float = 5.0, per_yr: float = 0.06) -> float:
    a = age if age else 8.0
    if a <= decline_start: return 1.0 + 0.02 * (decline_start - a)
    return max(0.15, 1.0 - per_yr * (a - decline_start))


def _round_by_unit(v: float, unit: str) -> float:
    if unit in ("U/L", "pg/mL"):        return int(round(v))
    if unit in ("mg/g", "L/min", "meters"): return int(round(v))
    if unit in ("FSIQ", "µV"):          return int(round(v))
    if unit in ("presence",):           return int(v > 0.5)
    if unit == "score/34":              return int(round(v))
    if unit == "seconds":               return round(v, 1)
    return round(v, 1)


def _parse_exon(s: str | None) -> int | None:
    if not s: return None
    t = s.strip()
    lower = t.lower()
    if lower.startswith("int"):
        t = t[3:]
    try: return int(t)
    except ValueError: return None


def generate_values(cohort: str, pid: str, phen: str, age: float | None,
                     ambulatory: str | None, exon_str: str | None) -> dict[str, float]:
    rng = _rng(cohort, pid)
    sev = _pheno_bias(phen)
    age_val = age or 8.0
    age_mult = _age_factor(age_val)
    exon_n = _parse_exon(exon_str) or 40
    distal_hit = exon_n >= 45   # affects Dp140+
    dp260_hit  = exon_n >= 30   # affects retina
    dp71_hit   = exon_n >= 63

    def jitter(mean: float, cv: float) -> float:
        return mean * rng.uniform(1 - cv, 1 + cv)

    vals: dict[str, float] = {}
    ck_base = {"DMD": 15000, "IMD": 6000, "BMD": 3500, "pending": 8000}.get(phen, 5000)
    vals["CK"]        = jitter(ck_base * (0.8 + 0.4 * (1.0 - age_mult)), 0.35)
    vals["aldolase"]  = jitter(vals["CK"] / 400 + 3.5, 0.20)
    vals["LDH"]       = jitter(vals["CK"] / 45 + 220, 0.15)
    vals["MRI_ff_VL"] = min(95, jitter(8 + sev * 55 * (1 - age_mult) + sev * 10, 0.25))

    lvef_decline = sev * max(0, (age_val - 8)) * 1.8
    vals["LVEF"]      = max(20, jitter(66 - lvef_decline, 0.05))
    vals["NT_proBNP"] = max(30, jitter(80 + max(0, 55 - vals["LVEF"]) * 40, 0.30))
    vals["LGE"]       = 1 if (sev > 0.7 and age_val > 12 and rng.random() > 0.35) else 0

    fvc_decline = sev * max(0, (age_val - 10)) * 6
    vals["FVC_pct"]   = max(15, jitter(95 - fvc_decline, 0.10))
    vals["PCF"]       = max(60, jitter(vals["FVC_pct"] * 5.5, 0.15))

    iq_base = 100 - (12 if distal_hit else 0) - (6 if dp71_hit else 0)
    vals["IQ"]        = max(50, jitter(iq_base, 0.08))

    erg_base = 260 - (100 if dp260_hit else 0)
    vals["ERG_bwave"] = max(30, jitter(erg_base, 0.15))

    uacr_base = 8 + (35 if dp71_hit else 0)
    vals["UACR"]      = max(2, jitter(uacr_base, 0.35))

    amb = (ambulatory or "Yes") == "Yes"
    m6_base = 480 if amb else 0
    vals["m6MWT"]     = max(0, jitter(m6_base * (1 - sev * (1 - age_mult) * 0.7), 0.12)) if amb else 0
    nsaa_base = 32 if amb else 4
    vals["NSAA"]      = max(0, jitter(nsaa_base * (1 - sev * (1 - age_mult) * 0.55), 0.10))
    vals["TTS"]       = max(0.5, jitter(2 + sev * 8 * (1 - age_mult), 0.20)) if amb else 30

    return vals


def flag_for(value: float, unit: str, ref_low: float, ref_high: float) -> str:
    if unit == "presence":
        return "high" if value else "normal"
    if value < ref_low:  return "low"
    if value > ref_high: return "high"
    return "normal"


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA_MIGRATION)  # safe if table already exists

    patients = conn.execute(
        "SELECT cohort, patient_id, phenotype_label, age_years, ambulatory, exon "
        "FROM patient_phenotype "
        "ORDER BY cohort, CAST(patient_id AS INTEGER)"
    ).fetchall()

    # Wipe all prior synthetic_v1 rows in one shot — cheaper than per-patient
    conn.execute("DELETE FROM patient_labs WHERE data_source=?", (DATA_SOURCE,))

    n_rows = 0
    for (cohort, pid, phen, age, amb, exon_str) in patients:
        vals = generate_values(cohort, pid, phen, age, amb, exon_str)
        rows = []
        for (key, layer, tissue, unit, ref_lo, ref_hi, label) in ASSAYS:
            v = _round_by_unit(vals[key], unit)
            flag = flag_for(v, unit, ref_lo, ref_hi)
            rows.append((cohort, pid, key, label, layer, tissue, unit,
                         float(v), float(ref_lo), float(ref_hi), flag, DATA_SOURCE))
        conn.executemany(
            "INSERT INTO patient_labs "
            "(cohort, patient_id, assay_key, label, layer, tissue, unit, "
            " value, ref_low, ref_high, flag, data_source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        n_rows += len(rows)

    conn.commit()
    print(f"[wrote] {n_rows:,} lab rows for {len(patients)} patients "
          f"({len(ASSAYS)} assays × {len(patients)} = {len(ASSAYS) * len(patients):,} expected)")

    # Quick sanity: show a P8-analog (the divergent BMD frameshift case)
    row = conn.execute(
        "SELECT COUNT(*), SUM(CASE WHEN flag='normal' THEN 1 ELSE 0 END), "
        "       SUM(CASE WHEN flag='high' THEN 1 ELSE 0 END), "
        "       SUM(CASE WHEN flag='low' THEN 1 ELSE 0 END) "
        "FROM patient_labs WHERE cohort='S1_novel' AND patient_id='59'"
    ).fetchone()
    print(f"[sanity] Patient S1_novel#59: {row[0]} labs · "
          f"{row[1]} normal · {row[2]} high · {row[3]} low")

    conn.close()


if __name__ == "__main__":
    main()
