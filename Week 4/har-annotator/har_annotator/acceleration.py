"""
Real human-chimp substitution burden for the acceleration axis.

Replaces the earlier HAR-width proxy. For each HAR we have hg38 and panTro5
(chimpanzee) coordinates from Cui et al. 2025 Supplemental Table 2, Table-a.
We fetch both orthologous sequences from the UCSC REST sequence API, align
them, and count human-chimp substitutions and indels. The per-base
substitution rate (subst_rate) is the real measure of sequence divergence in
the HAR and drives the acceleration score in score.py.

CAVEAT (documented, not hidden): human-chimp divergence is a first-order
measure of acceleration. Strict *human-specific* acceleration requires an
outgroup (e.g. macaque) or a branch model (phyloP) to confirm the change
occurred on the human lineage rather than the chimp lineage. This is a large
improvement over width but is not lineage-polarized; see README caveats.
"""
from __future__ import annotations
import time
import pandas as pd
import requests
from Bio.Align import PairwiseAligner

UCSC_SEQ_API = "https://api.genome.ucsc.edu/getData/sequence"
SUPP_SHEET = "HARs information"   # Table-a, header on row 3 (skiprows=2)


def load_ortholog_coords(supp_xlsx: str) -> pd.DataFrame:
    """Read Table-a: HAR names + hg38 and panTro5 coordinates."""
    ta = pd.read_excel(supp_xlsx, sheet_name=SUPP_SHEET, skiprows=2)
    keep = ["Names", "chr_hg38", "start_hg38", "end_hg38",
            "chr_pantro5", "start_pantro5", "end_pantro5"]
    ta = ta[keep].rename(columns={"Names": "har_id"})
    for c in ["start_hg38", "end_hg38", "start_pantro5", "end_pantro5"]:
        ta[c] = ta[c].astype("Int64")
    return ta


def _fetch_seq(genome: str, chrom: str, start: int, end: int,
               session: requests.Session, retries: int = 3) -> str:
    """One UCSC REST sequence call (0-based, half-open — matches BED/HAR coords)."""
    params = {"genome": genome, "chrom": chrom, "start": int(start), "end": int(end)}
    for attempt in range(retries):
        try:
            r = session.get(UCSC_SEQ_API, params=params, timeout=30)
            if r.ok:
                dna = r.json().get("dna", "")
                if dna:
                    return dna.upper()
            time.sleep(1.0 + attempt)
        except requests.RequestException:
            time.sleep(1.0 + attempt)
    return ""


def fetch_ortholog_sequences(coords: pd.DataFrame,
                             har_ids: list[str] | None = None,
                             cache_path: str | None = None,
                             progress_every: int = 50) -> pd.DataFrame:
    """
    Fetch hg38 + panTro5 sequence for each requested HAR.
    Returns columns: har_id, seq_hg38, seq_pantro5, len_hg38, len_pantro5.
    Cached to `cache_path` (parquet) so reruns don't refetch.
    """
    import os
    if cache_path and os.path.exists(cache_path):
        cached = pd.read_parquet(cache_path)
    else:
        cached = pd.DataFrame(columns=["har_id", "seq_hg38", "seq_pantro5"])

    sub = coords if har_ids is None else coords[coords.har_id.isin(har_ids)]
    have = set(cached.har_id)
    todo = sub[~sub.har_id.isin(have)]

    rows = []
    with requests.Session() as s:
        for i, r in enumerate(todo.itertuples(index=False)):
            hseq = _fetch_seq("hg38", r.chr_hg38, r.start_hg38, r.end_hg38, s)
            cseq = _fetch_seq("panTro5", r.chr_pantro5, r.start_pantro5, r.end_pantro5, s)
            rows.append({"har_id": r.har_id, "seq_hg38": hseq, "seq_pantro5": cseq})
            if progress_every and (i + 1) % progress_every == 0:
                print(f"  fetched {i+1}/{len(todo)}", flush=True)

    fetched = pd.DataFrame(rows)
    out = pd.concat([cached, fetched], ignore_index=True) if len(fetched) else cached
    out["len_hg38"] = out.seq_hg38.str.len()
    out["len_pantro5"] = out.seq_pantro5.str.len()
    if cache_path:
        out.to_parquet(cache_path, index=False)
    return out


def _aligner() -> PairwiseAligner:
    a = PairwiseAligner()
    a.mode = "global"
    a.match_score = 2.0
    a.mismatch_score = -1.0
    a.open_gap_score = -5.0
    a.extend_gap_score = -0.5
    return a


def align_and_count(seq_h: str, seq_c: str) -> dict:
    """
    Global-align human vs chimp; count substitutions, indels, aligned length.
    subst_rate = substitutions / aligned_length (columns where both non-gap).
    """
    if not seq_h or not seq_c:
        return {"n_substitutions": pd.NA, "n_indels": pd.NA,
                "aln_length": pd.NA, "subst_rate": pd.NA}
    aln = _aligner().align(seq_h, seq_c)[0]
    a_h, a_c = str(aln[0]), str(aln[1])
    subs = indels = matched_cols = 0
    for bh, bc in zip(a_h, a_c):
        if bh == "-" or bc == "-":
            indels += 1
        else:
            matched_cols += 1
            if bh != bc:
                subs += 1
    rate = subs / matched_cols if matched_cols else pd.NA
    return {"n_substitutions": subs, "n_indels": indels,
            "aln_length": len(a_h), "subst_rate": rate}


def annotate_acceleration(evidence: pd.DataFrame, seqs: pd.DataFrame) -> pd.DataFrame:
    """Add n_substitutions, n_indels, aln_length, subst_rate to the evidence spine."""
    seqmap = seqs.set_index("har_id")
    recs = []
    for har_id in evidence.har_id:
        if har_id in seqmap.index:
            row = seqmap.loc[har_id]
            recs.append({"har_id": har_id,
                         **align_and_count(row.seq_hg38, row.seq_pantro5)})
        else:
            recs.append({"har_id": har_id, "n_substitutions": pd.NA,
                         "n_indels": pd.NA, "aln_length": pd.NA, "subst_rate": pd.NA})
    acc = pd.DataFrame(recs)
    return evidence.merge(acc, on="har_id", how="left")
