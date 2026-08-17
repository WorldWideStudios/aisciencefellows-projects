"""Parse data/raw/clinvar_dmd.tsv → populate clinvar_phenotype in mechanism.sqlite.

Reads the DMD-only slice of ClinVar's variant_summary.txt (produced by
scripts/fetch_clinvar_dmd.sh, which streams the FTP file and awk-filters
on GeneSymbol=='DMD'). Deduplicates on VariationID (rows appear once per
assembly), classifies each variant by PhenotypeList substring match into
one of: DMD, BMD, IMD, DCM, other, and writes a row per variant.

Schema:
    clinvar_phenotype(
      variation_id     INTEGER PRIMARY KEY,
      allele_id        INTEGER,
      variant_name     TEXT,       -- ClinVar 'Name' column
      clin_sig         TEXT,       -- raw ClinicalSignificance
      clin_sig_simple  INTEGER,    -- 0/1/-1
      review_status    TEXT,
      phenotype_list   TEXT,       -- raw joined phenotype list
      phenotype_label  TEXT,       -- DMD / BMD / IMD / DCM / other
      data_source      TEXT        -- 'clinvar'
    )

Run:
    python3 -m prototype.ingest.bake_clinvar
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "data" / "raw" / "clinvar_dmd.tsv"
DB = REPO / "data" / "mechanism.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS clinvar_phenotype (
  variation_id     INTEGER PRIMARY KEY,
  allele_id        INTEGER,
  variant_name     TEXT,
  clin_sig         TEXT,
  clin_sig_simple  INTEGER,
  review_status    TEXT,
  phenotype_list   TEXT,
  phenotype_label  TEXT,
  data_source      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_clinvar_label ON clinvar_phenotype(phenotype_label);
CREATE INDEX IF NOT EXISTS ix_clinvar_sig   ON clinvar_phenotype(clin_sig_simple);
"""


def classify(phenotype_list: str) -> str:
    """Map ClinVar PhenotypeList string → dashboard label.

    ClinVar PhenotypeList is a `;`-joined list of MedGen terms. We take
    the first matching label in priority order (DMD > BMD > IMD > DCM >
    other) — a variant classified as both Duchenne AND cardiomyopathy
    goes under DMD because that's the primary phenotype.
    """
    if not phenotype_list:
        return "other"
    p = phenotype_list.lower()
    if "duchenne" in p:
        return "DMD"
    if "becker" in p:
        return "BMD"
    if "intermediate muscular dystrophy" in p or "intermediate dmd" in p:
        return "IMD"
    if "cardiomyopathy" in p or "cmd3b" in p:
        return "DCM"
    if "muscular dystrophy" in p:
        # Unqualified — treat as other so we don't over-assign to DMD
        return "other"
    return "other"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"missing {SRC} — run scripts/fetch_clinvar_dmd.sh first")

    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    # Drop any prior load so re-runs are idempotent (not a migration).
    conn.execute("DELETE FROM clinvar_phenotype")

    seen: dict[int, dict] = {}   # variation_id → best row (prefer GRCh38)
    with SRC.open() as f:
        r = csv.DictReader(f, delimiter="\t")
        for row in r:
            try:
                vid = int(row["VariationID"])
            except (KeyError, ValueError):
                continue
            assembly = row.get("Assembly", "")
            prior = seen.get(vid)
            if prior is not None and prior["Assembly"] == "GRCh38":
                continue   # GRCh38 already recorded; skip GRCh37 dup
            if prior is not None and assembly != "GRCh38":
                continue
            seen[vid] = row

    rows = []
    for vid, row in seen.items():
        try:
            aid = int(row.get("#AlleleID") or 0)
        except ValueError:
            aid = 0
        try:
            css = int(row.get("ClinSigSimple") or 0)
        except ValueError:
            css = 0
        plist = row.get("PhenotypeList", "")
        rows.append((
            vid,
            aid,
            row.get("Name", ""),
            row.get("ClinicalSignificance", ""),
            css,
            row.get("ReviewStatus", ""),
            plist,
            classify(plist),
            "clinvar",
        ))

    conn.executemany(
        "INSERT INTO clinvar_phenotype VALUES (?,?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()

    print(f"[loaded] {len(rows)} unique DMD variants from ClinVar")
    print("[label distribution]")
    for label, n in conn.execute(
        "SELECT phenotype_label, COUNT(*) FROM clinvar_phenotype "
        "GROUP BY phenotype_label ORDER BY 2 DESC"
    ):
        print(f"  {label:8}  {n}")
    print("[clin sig distribution]")
    for sig, n in conn.execute(
        "SELECT clin_sig, COUNT(*) FROM clinvar_phenotype "
        "GROUP BY clin_sig ORDER BY 2 DESC LIMIT 10"
    ):
        print(f"  {sig[:50]:50}  {n}")
    conn.close()


if __name__ == "__main__":
    main()
