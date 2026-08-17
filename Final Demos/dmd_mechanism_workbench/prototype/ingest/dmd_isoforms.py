"""Emit static reference tables for dystrophin isoforms.

Sources for exon-usage boundaries:
- Muntoni F, Torelli S, Ferlini A. "Dystrophin and mutations: one gene,
  several proteins, multiple phenotypes." Lancet Neurol. 2003;2(12):731-40.
- Doorenweerd N. "Combining genetics, neuropsychology and neuroimaging
  to improve understanding of brain involvement in Duchenne muscular
  dystrophy — a narrative review." Neuromuscul Disord. 2020.
- NCBI RefSeq entries per transcript (accessions below).

Two TSVs land in data/variants/:
  dmd_isoforms.tsv     — 7 rows, one per major isoform
  dmd_exon_usage.tsv   — one row per (isoform, exon) with a boolean

The exon-usage matrix lets us compute per-variant per-isoform effect
locally: a variant affects isoform X iff its cDNA range intersects an
exon that isoform X uses. This is why we do not re-download LOVD per
isoform — LOVD stores each variant once anchored to NM_004006.2
(Dp427m), and the intersection is a local join.

Not tracked in v0:
- Unique 5' exons of alternative-promoter isoforms (1M, 1C, 1P, 1R, 1B3,
  1S, 1G). These live in Dp427m *introns* so are not reachable from
  LOVD c-notation on NM_004006.2. v1 refinement.
- Alt-splicing at Dp71 C-terminus (Dp71a/b/c/d differ at exons 78-79).
  v0 collapses to Dp71.
- UniProt per-isoform suffixes (P11532-N). Base accession P11532 for all;
  suffix-to-isoform mapping is TBD.

Run:
    python -m prototype.ingest.dmd_isoforms
"""

from __future__ import annotations

from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "variants"

# DMD canonical exon count in the reference numbering (NM_004006.2).
DMD_TOTAL_EXONS = 79

# Columns:
#   isoform_id, refseq_transcript, uniprot_base, first_shared_exon,
#   promoter_tissue, primary_expression_tissues, unique_5prime_exon_label
ISOFORMS = [
    ("Dp427m", "NM_004006",  "P11532",  1, "muscle",
        "skeletal_muscle;cardiac_muscle", "1M"),
    ("Dp427c", "NM_000109",  "P11532",  1, "cortical",
        "cortical_neurons;hippocampus", "1C"),
    ("Dp427p", "NM_004009",  "P11532",  1, "Purkinje",
        "cerebellar_Purkinje_cells", "1P"),
    ("Dp260",  "NM_004010",  "P11532", 30, "retinal",
        "retinal_photoreceptors", "1R"),
    ("Dp140",  "NM_004012",  "P11532", 45, "brain_kidney",
        "brain_glia;kidney", "1B3"),
    ("Dp116",  "NM_004014",  "P11532", 56, "Schwann",
        "peripheral_nerve_Schwann_cells", "1S"),
    ("Dp71",   "NM_004015",  "P11532", 63, "ubiquitous",
        "retina;brain;kidney;liver;blood", "1G"),
]

ISOFORM_COLS = [
    "isoform_id",
    "refseq_transcript",
    "uniprot_base",
    "first_shared_exon",
    "promoter_tissue",
    "primary_expression_tissues",
    "unique_5prime_exon_label",
]


def write_isoforms_tsv() -> Path:
    out = OUT_DIR / "dmd_isoforms.tsv"
    with out.open("w") as f:
        f.write("\t".join(ISOFORM_COLS) + "\n")
        for row in ISOFORMS:
            f.write("\t".join(str(x) for x in row) + "\n")
    return out


def write_exon_usage_tsv() -> Path:
    out = OUT_DIR / "dmd_exon_usage.tsv"
    with out.open("w") as f:
        f.write("isoform_id\texon\tused\n")
        for row in ISOFORMS:
            isoform_id = row[0]
            first_exon = row[3]
            for exon in range(1, DMD_TOTAL_EXONS + 1):
                used = 1 if exon >= first_exon else 0
                f.write(f"{isoform_id}\t{exon}\t{used}\n")
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    iso_path = write_isoforms_tsv()
    exon_path = write_exon_usage_tsv()
    print(f"[wrote] {iso_path} ({len(ISOFORMS)} isoforms)")
    print(f"[wrote] {exon_path} ({len(ISOFORMS) * DMD_TOTAL_EXONS} rows)")
    print()
    print("[sanity] exon coverage per isoform:")
    for r in ISOFORMS:
        first = r[3]
        n_exons = DMD_TOTAL_EXONS - first + 1
        pct = 100 * n_exons / DMD_TOTAL_EXONS
        print(
            f"  {r[0]:<7s} {r[1]:<11s}  exons {first:>2d}-{DMD_TOTAL_EXONS} "
            f"({n_exons:>2d}/{DMD_TOTAL_EXONS} = {pct:>3.0f}%)  "
            f"tissue={r[4]}"
        )


if __name__ == "__main__":
    main()
