"""Bake per-variant ESM3 protein-impact scores for the Zhang cohort.

For each of the 10 curated patients:
  1. Read the variant HGVSp → extract 1-based residue index r
  2. Fold a WT window of dystrophin ±128 AA around r via ESM3 Forge
  3. Extract mean pLDDT in that window
  4. Compute impact_score = (1 − r/L) × mean_pLDDT / 100
     — the fraction of protein truncated, weighted by how well-folded
       the cut region is

Every variant in this cohort is a Frameshift, Nonsense, or Splice-site
(no missense), so the score is a truncation-severity index, not a residue-
level LLR. That's the honest scoring for this cohort.

Output: data/variants/protein_impact.tsv  (one row per patient)
  patient_id, cohort, hgvsc, hgvsp, consequence, residue, window_start,
  window_end, mean_wt_plddt, truncation_fraction, impact_score, uniprot,
  status, notes

Run (needs ESM3_API_KEY):
    ~/venv/bin/python -m prototype.ingest.bake_esm3_impact
Or first source:
    source /home/ubuntu/alms_inference_env/.env
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DB   = REPO / "data" / "mechanism.sqlite"
OUT  = REPO / "data" / "variants" / "protein_impact.tsv"

WINDOW = 128                        # ± AA around variant residue
UNIPROT_ID = "P11532"               # Dp427m canonical
DYSTROPHIN_LEN = 3685               # full-length aa count (canonical)
MODEL = "esm3-open-2024-03"


# HGVSp → residue index. Handles:
#   p.(Leu2181Tyrfs*8)   → 2181
#   p.(Trp3083*)         → 3083
#   p.(Gln2193*)         → 2193
_HGVSP_RE = re.compile(r"p\.\(?[A-Za-z]{3}(\d+)")


def parse_residue(hgvsp: str | None) -> int | None:
    if not hgvsp: return None
    m = _HGVSP_RE.search(hgvsp)
    return int(m.group(1)) if m else None


def fetch_dystrophin_sequence() -> str:
    """Pull P11532 canonical sequence from UniProt REST."""
    import urllib.request
    url = f"https://rest.uniprot.org/uniprotkb/{UNIPROT_ID}.fasta"
    with urllib.request.urlopen(url, timeout=30) as r:
        text = r.read().decode()
    seq = "".join(line.strip() for line in text.splitlines() if not line.startswith(">"))
    if len(seq) != DYSTROPHIN_LEN:
        print(f"[warn] UniProt returned {len(seq)} aa, expected {DYSTROPHIN_LEN}")
    return seq


def load_patients() -> list[dict]:
    """Fetch the 10 Zhang cohort patients + their variants from the DB."""
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT cohort, patient_id, aa_change, nucleotide, consequence "
            "FROM patient_phenotype "
            "WHERE (cohort, patient_id) IN (VALUES "
            "  ('S1_novel','2'),('S1_novel','30'),('S2_reported','258'),"
            "  ('S1_novel','57'),('S1_novel','5'),('S1_novel','11'),"
            "  ('S2_reported','202'),('S2_reported','225'),('S1_novel','49'),"
            "  ('S2_reported','266'))"
        ).fetchall()
    import html as _html
    return [{
        "cohort":      cohort,
        "patient_id":  pid,
        "hgvsp":       _html.unescape(aa or ""),
        "hgvsc":       _html.unescape(nuc or ""),
        "consequence": cons,
    } for (cohort, pid, aa, nuc, cons) in rows]


def esm3_fold_window(seq: str) -> tuple[list[float], float]:
    """Fold a sequence via ESM3 Forge. Returns (plddt_array, pTM)."""
    from esm.sdk import client as make_client
    from esm.sdk.api import ESMProtein, GenerationConfig
    api_key = os.environ.get("ESM3_API_KEY") or os.environ.get("ESM_API_KEY")
    if not api_key:
        raise RuntimeError("ESM3_API_KEY not set")
    cli = make_client(model=MODEL, token=api_key)
    folded = cli.generate(
        ESMProtein(sequence=seq),
        GenerationConfig(track="structure"),
    )
    if hasattr(folded, "error_code"):
        raise RuntimeError(f"fold error: {getattr(folded, 'error_msg', folded)}")
    plddt = folded.plddt
    if hasattr(plddt, "detach"):
        plddt = plddt.detach().cpu().numpy().tolist()
    elif hasattr(plddt, "tolist"):
        plddt = plddt.tolist()
    ptm = float(folded.ptm) if folded.ptm is not None else 0.0
    return plddt, ptm


def compute_impact(patient: dict, dystrophin_seq: str) -> dict:
    r = parse_residue(patient["hgvsp"])
    cons = (patient["consequence"] or "").lower()

    # Splice-site variants without a residue map — skip the fold, mark N/A.
    if r is None:
        return {
            **patient,
            "residue": None,
            "window_start": None, "window_end": None,
            "mean_wt_plddt": None,
            "truncation_fraction": None,
            "impact_score": None,
            "status": "skipped_no_residue",
            "notes": f"consequence={cons}; no residue parsed from HGVSp",
        }

    # Build window around variant residue (1-based → 0-based slicing)
    r0 = r - 1
    start0 = max(0, r0 - WINDOW)
    end0   = min(len(dystrophin_seq), r0 + WINDOW + 1)
    window_seq = dystrophin_seq[start0:end0]
    if len(window_seq) < 20:
        return {
            **patient, "residue": r,
            "window_start": start0 + 1, "window_end": end0,
            "mean_wt_plddt": None, "truncation_fraction": None,
            "impact_score": None, "status": "skipped_tiny_window",
            "notes": f"window len {len(window_seq)} too small",
        }

    print(f"  [{patient['patient_id']}] fold WT window {start0+1}-{end0} "
          f"({len(window_seq)} aa) around r={r} ({cons})…", flush=True)
    t0 = time.time()
    plddt, ptm = esm3_fold_window(window_seq)
    dt = time.time() - t0
    # The ESM3 SDK returns pLDDT on a 0-1 scale. Rescale to the classical
    # 0-100 semantics used elsewhere in the workbench (matches the JARVIS
    # convention and what users expect to read).
    mean_plddt_raw = sum(plddt) / len(plddt) if plddt else 0.0
    mean_plddt = mean_plddt_raw * 100.0 if mean_plddt_raw <= 1.0 else mean_plddt_raw
    trunc_frac = (DYSTROPHIN_LEN - r) / DYSTROPHIN_LEN
    impact = trunc_frac * (mean_plddt / 100.0)   # 0-1 index: 1 = catastrophic
    print(f"    plddt μ={mean_plddt:.1f} · pTM={ptm:.2f} · "
          f"trunc={trunc_frac*100:.1f}% · impact={impact:.3f} "
          f"({dt:.1f}s)", flush=True)
    return {
        **patient, "residue": r,
        "window_start": start0 + 1, "window_end": end0,
        "mean_wt_plddt": round(mean_plddt, 2),
        "wt_ptm": round(ptm, 3),
        "truncation_fraction": round(trunc_frac, 4),
        "impact_score": round(impact, 4),
        "status": "ok",
        "notes": f"window ±{WINDOW}aa · fold {dt:.1f}s",
    }


def main() -> int:
    print(f"[bake_esm3_impact] model={MODEL} window=±{WINDOW}aa uniprot={UNIPROT_ID}")
    if not (os.environ.get("ESM3_API_KEY") or os.environ.get("ESM_API_KEY")):
        print("ERROR: ESM3_API_KEY not set. Try:")
        print("  source /home/ubuntu/alms_inference_env/.env")
        return 1

    seq = fetch_dystrophin_sequence()
    print(f"[dystrophin] fetched {len(seq)} aa from UniProt {UNIPROT_ID}")

    patients = load_patients()
    print(f"[cohort]     {len(patients)} patients loaded from patient_phenotype")

    results = []
    for pat in patients:
        try:
            results.append(compute_impact(pat, seq))
        except Exception as e:
            print(f"  [{pat['patient_id']}] FAILED: {e}", flush=True)
            results.append({
                **pat, "residue": parse_residue(pat["hgvsp"]),
                "window_start": None, "window_end": None,
                "mean_wt_plddt": None, "wt_ptm": None,
                "truncation_fraction": None, "impact_score": None,
                "status": "error", "notes": str(e)[:200],
            })

    # Write TSV
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["patient_id", "cohort", "hgvsc", "hgvsp", "consequence",
            "residue", "window_start", "window_end",
            "mean_wt_plddt", "wt_ptm",
            "truncation_fraction", "impact_score",
            "uniprot", "status", "notes"]
    with OUT.open("w") as f:
        f.write("## Per-variant ESM3 protein-impact scores for the Zhang cohort.\n")
        f.write("## Source model:  esm3-open-2024-03 via Forge / biohub.ai\n")
        f.write(f"## Baked at:      {time.strftime('%Y-%m-%d %H:%M:%S')} · window ±{WINDOW}aa\n")
        f.write("## Metric:        impact = (1 - residue/{}) * mean_pLDDT/100\n".format(DYSTROPHIN_LEN))
        f.write("##                fraction of dystrophin truncated × structural quality of cut region\n")
        f.write("\t".join(cols) + "\n")
        for r in results:
            r["uniprot"] = UNIPROT_ID
            f.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")

    n_ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n[wrote] {OUT}")
    print(f"[stats] {n_ok}/{len(results)} folds OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
