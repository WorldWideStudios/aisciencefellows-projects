"""
JASPAR transcription-factor motif disruption between human and chimp HAR alleles.

For each HAR we scan the hg38 (human) and panTro5 (chimp) orthologous sequences
against the JASPAR2024 CORE vertebrate PWM collection. A transcription-factor
binding site (TFBS) is called "present" when the best relative PWM score in the
sequence (max over both strands, over all offsets) clears a fixed relative
threshold (default 0.85 of the span between the PWM's min and max attainable
log-odds score). We then compare the two alleles:

  gained  = TFBS present in human but not chimp   (human change created a site)
  lost    = TFBS present in chimp but not human    (human change destroyed a site)
  motif_disruption = gained + lost

This is the direct sequence-to-function signal for a HAR: which TF binding
sites the human-specific substitutions create or destroy. It drives the motif
axis in score.py (previously hard-coded 0).

CAVEAT: presence/absence at a fixed threshold is a coarse call; it does not
model affinity change quantitatively, and JASPAR PWMs are themselves models.
Documented in README caveats.
"""
from __future__ import annotations
import math
import pandas as pd
from pyjaspar import jaspardb

_BG = {"A": 0.25, "C": 0.25, "G": 0.25, "T": 0.25}


def load_pssms(release: str = "JASPAR2024",
               collection: str = "CORE",
               tax_group: str = "vertebrates",
               pseudocount: float = 0.5):
    """Return list of (matrix_id, tf_name, pssm, min_score, max_score)."""
    jdb = jaspardb(release=release)
    motifs = jdb.fetch_motifs(collection=collection, tax_group=tax_group)
    out = []
    for m in motifs:
        m.pseudocounts = pseudocount
        m.background = _BG
        pssm = m.pssm
        out.append((m.matrix_id, m.name, pssm, pssm.min, pssm.max))
    return out


def compute_fpr_thresholds(pssms, fpr: float = 1e-4,
                           precision: int = 10**3) -> dict:
    """
    Per-motif absolute score threshold at a fixed false-positive rate.
    This is the standard FIMO/MOODS-style TFBS call: comparable across motifs
    of different length and information content, unlike a single relative
    cutoff. Short/degenerate motifs whose minimum achievable FPR exceeds `fpr`
    are floored at their max score (require a near-perfect match). Cache the
    returned {matrix_id: threshold} dict — this is the slow one-time step.
    """
    thr = {}
    for mid, name, pssm, mn, mx in pssms:
        d = pssm.distribution(background=_BG, precision=precision)
        thr[mid] = float(d.threshold_fpr(fpr))
    return thr


def _best_score(pssm, seq: str) -> float:
    """Max absolute log-odds score over all offsets and both strands."""
    best = -math.inf
    try:
        for _pos, score in pssm.search(seq, threshold=-1e9, both=True):
            if score > best:
                best = score
    except Exception:
        return -math.inf
    return best


def scan_pair(seq_h: str, seq_c: str, pssms, thresholds: dict) -> dict:
    """Count gained/lost/present TFBS between human and chimp alleles,
    using per-motif FPR thresholds."""
    if not seq_h or not seq_c:
        return {"n_motifs_human": pd.NA, "n_motifs_chimp": pd.NA,
                "n_motif_gained": pd.NA, "n_motif_lost": pd.NA,
                "motif_disruption": pd.NA, "motif_tfs": ""}
    nh = nc = gained = lost = 0
    tfs = []
    for mid, name, pssm, mn, mx in pssms:
        t = thresholds.get(mid, mx)
        ph = _best_score(pssm, seq_h) >= t
        pc = _best_score(pssm, seq_c) >= t
        nh += ph
        nc += pc
        if ph and not pc:
            gained += 1
            tfs.append(f"+{name}")
        elif pc and not ph:
            lost += 1
            tfs.append(f"-{name}")
    return {"n_motifs_human": nh, "n_motifs_chimp": nc,
            "n_motif_gained": gained, "n_motif_lost": lost,
            "motif_disruption": gained + lost,
            "motif_tfs": ";".join(tfs)}


def annotate_motifs(evidence: pd.DataFrame, seqs: pd.DataFrame,
                    pssms=None, thresholds: dict = None,
                    fpr: float = 1e-4, progress_every: int = 50) -> pd.DataFrame:
    """Add motif columns to the evidence spine."""
    if pssms is None:
        pssms = load_pssms()
    if thresholds is None:
        thresholds = compute_fpr_thresholds(pssms, fpr=fpr)
    seqmap = seqs.set_index("har_id")
    recs = []
    ids = list(evidence.har_id)
    for i, har_id in enumerate(ids):
        if har_id in seqmap.index:
            row = seqmap.loc[har_id]
            recs.append({"har_id": har_id,
                         **scan_pair(row.seq_hg38, row.seq_pantro5, pssms, thresholds)})
        else:
            recs.append({"har_id": har_id, "n_motifs_human": pd.NA,
                         "n_motifs_chimp": pd.NA, "n_motif_gained": pd.NA,
                         "n_motif_lost": pd.NA, "motif_disruption": pd.NA,
                         "motif_tfs": ""})
        if progress_every and (i + 1) % progress_every == 0:
            print(f"  scanned {i+1}/{len(ids)}", flush=True)
    mo = pd.DataFrame(recs)
    return evidence.merge(mo, on="har_id", how="left")
