"""Bake per-exon cDNA and protein coordinates for DMD Dp427m.

Fetches ENST00000357033 (MANE canonical, 79 exons, minus strand) from
Ensembl REST and computes for each exon:
  - cDNA start / end   (1-based, relative to full transcript)
  - c-coord start / end (1-based, relative to ATG; c.1 = first base of Met)
  - aa start / end     (approximate 1-based residue span)

Writes: data/variants/dmd_exon_coords.tsv

Powers per-isoform aggregation across the ClinVar pathogenic corpus:
  - parse c.pos from HGVSc → look up exon → apply first_shared_exon rule
    per isoform → nested counts (Dp427* > Dp260 > Dp140 > Dp116 > Dp71)

Run: ~/venv/bin/python -m prototype.ingest.bake_dmd_exon_coords
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
OUT  = REPO / "data" / "variants" / "dmd_exon_coords.tsv"
CACHE = REPO / "cache" / "ensembl_ENST00000357033.json"

# Standard DMD Dp427m NM_004006.3 5'UTR length: 244 nt.
# So c.1 (first base of ATG) = cDNA position 245.
CDS_START_IN_CDNA = 245


def fetch_transcript() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    url = "https://rest.ensembl.org/lookup/id/ENST00000357033?expand=1;utr=1"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    tr = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                tr = json.load(r)
            break
        except Exception as e:
            print(f"[ensembl] attempt {attempt+1} failed: {e}", flush=True)
            time.sleep(2 * (attempt + 1))
    if tr is None:
        raise RuntimeError("Ensembl fetch failed 3x")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(tr))
    return tr


def main() -> int:
    tr = fetch_transcript()
    exons = tr["Exon"]
    if len(exons) != 79:
        print(f"[warn] expected 79 exons, got {len(exons)}")
    print(f"[transcript] {tr['display_name']} · length {tr['length']} nt · "
          f"{len(exons)} exons · strand {tr['strand']}")
    print(f"[cds]        c.1 → cDNA position {CDS_START_IN_CDNA} (5'UTR = 244 nt)")

    # Ensembl returns exons in rank order for the transcript (rank 1 → N).
    # cDNA position accumulates across exons in that order.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        f.write("## Per-exon cDNA + c-coord + aa coordinates for DMD Dp427m.\n")
        f.write("## Source:   Ensembl REST · ENST00000357033 (MANE canonical) · 79 exons\n")
        f.write("## CDS ref:  NM_004006.3 · 5'UTR 244 nt · CDS 11058 nt (3685 aa incl. stop)\n")
        f.write(f"## Baked at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("exon_num\tcdna_start\tcdna_end\texon_length\tc_start\tc_end\taa_start\taa_end\n")

        cdna_pos = 1
        for i, e in enumerate(exons, start=1):
            length = e["end"] - e["start"] + 1
            cdna_start = cdna_pos
            cdna_end   = cdna_pos + length - 1

            # c-coord: 0/negative for 5'UTR, positive for CDS
            c_start = cdna_start - (CDS_START_IN_CDNA - 1)
            c_end   = cdna_end   - (CDS_START_IN_CDNA - 1)

            # aa coord: only defined where c > 0. Clip to CDS.
            if c_end <= 0:
                aa_start = aa_end = ""       # entirely 5'UTR
            elif c_start > 0:
                aa_start = (c_start - 1) // 3 + 1
                aa_end   = (c_end   - 1) // 3 + 1
            else:
                # straddles 5'UTR / CDS boundary
                aa_start = 1
                aa_end   = (c_end - 1) // 3 + 1

            f.write(f"{i}\t{cdna_start}\t{cdna_end}\t{length}\t{c_start}\t{c_end}\t{aa_start}\t{aa_end}\n")
            cdna_pos += length

    n_rows = sum(1 for _ in OUT.read_text().splitlines() if not _.startswith("#") and _.split("\t")[0] != "exon_num")
    print(f"[wrote] {OUT}")
    print(f"[stats] {n_rows} exons written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
