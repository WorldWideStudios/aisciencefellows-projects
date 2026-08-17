"""Bake WT + mutant protein folds and PyMOL renders per Zhang cohort variant.

For each variant:
  1. Fetch DMD (P11532) canonical sequence
  2. Fold a WT window ±256aa around the variant residue → save PDB
  3. Fold the truncated mutant sequence (WT[1..residue-1]) as its own
     window, focused on the last ±256aa before the cut → save PDB
  4. PyMOL headless: render two PNGs
     - wt_context.png   — WT window, variant residue as red sphere + label
     - mutant_full.png  — truncated protein colored orange, C-terminal
                          fragment shown as a stub with a red "cut" marker

Outputs to:
  cache/esm3/P11532/variants/<slug>/wt_window.pdb
  cache/esm3/P11532/variants/<slug>/mutant_window.pdb
  cache/esm3/P11532/variants/<slug>/wt_context.png
  cache/esm3/P11532/variants/<slug>/mutant_full.png

Slug convention: `_` for any non-alphanumeric char in HGVSc (matches
hydrate_patient_view and workbench conventions).

Run:
    source /home/ubuntu/alms_inference_env/.env    # ESM3_API_KEY
    ~/venv/bin/python -m prototype.ingest.bake_protein_renders --variant c.6540del
    ~/venv/bin/python -m prototype.ingest.bake_protein_renders --all
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "mechanism.sqlite"
CACHE = REPO / "cache" / "esm3" / "P11532" / "variants"
UNIPROT_FASTA = REPO / "cache" / "uniprot_P11532.fasta"

UNIPROT_ID = "P11532"
DYSTROPHIN_LEN = 3685
MODEL = "esm3-open-2024-03"
WINDOW = 256          # ± AA around variant residue

_HGVSP_RE = re.compile(r"p\.\(?[A-Za-z]{3}(\d+)")
_SLUG_RE = re.compile(r"[^A-Za-z0-9]+")


def slugify(s: str) -> str:
    return _SLUG_RE.sub("_", s or "").strip("_")


def parse_residue(hgvsp: str | None) -> int | None:
    if not hgvsp: return None
    m = _HGVSP_RE.search(hgvsp)
    return int(m.group(1)) if m else None


def load_dystrophin_sequence() -> str:
    """Use cached FASTA if present; otherwise fetch from UniProt REST."""
    if UNIPROT_FASTA.exists():
        text = UNIPROT_FASTA.read_text()
    else:
        import urllib.request
        url = f"https://rest.uniprot.org/uniprotkb/{UNIPROT_ID}.fasta"
        with urllib.request.urlopen(url, timeout=30) as r:
            text = r.read().decode()
        UNIPROT_FASTA.write_text(text)
    return "".join(line.strip() for line in text.splitlines() if not line.startswith(">"))


def load_variants(specific: str | None = None) -> list[dict]:
    """Load Zhang cohort variants. If `specific` is set, filter to that HGVSc."""
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
    out = []
    for (cohort, pid, aa, nuc, cons) in rows:
        nuc_u = html.unescape(nuc or "")
        aa_u  = html.unescape(aa or "")
        if specific and nuc_u != specific: continue
        out.append({
            "cohort": cohort, "patient_id": pid,
            "hgvsc": nuc_u, "hgvsp": aa_u, "consequence": cons,
        })
    return out


def esm3_fold(seq: str) -> tuple[list[float], float, str]:
    """Fold via ESM3 Forge. Returns (plddt_array, pTM, pdb_string)."""
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
    pdb = folded.to_pdb_string() if hasattr(folded, "to_pdb_string") else folded.to_pdb()
    return plddt, ptm, pdb


def fold_and_save(seq: str, out_pdb: Path, label: str) -> tuple[float, float]:
    """Fold seq via Forge, save PDB, return (mean_plddt, pTM)."""
    out_pdb.parent.mkdir(parents=True, exist_ok=True)
    if out_pdb.exists() and out_pdb.stat().st_size > 100:
        print(f"    [{label}] PDB exists, skipping fold ({out_pdb.name})", flush=True)
        # We can't recover pLDDT from a cached PDB without re-parsing; return 0s.
        return 0.0, 0.0
    print(f"    [{label}] fold {len(seq)} aa …", end=" ", flush=True)
    t0 = time.time()
    plddt, ptm, pdb = esm3_fold(seq)
    dt = time.time() - t0
    mean_p = (sum(plddt) / len(plddt) if plddt else 0.0)
    if mean_p <= 1.0: mean_p *= 100
    out_pdb.write_text(pdb)
    print(f"pLDDT μ={mean_p:.1f} pTM={ptm:.2f} ({dt:.1f}s) → {out_pdb.name}", flush=True)
    return mean_p, ptm


def render_pymol(wt_pdb: Path, mut_pdb: Path, variant_residue: int,
                 variant_residue_in_window: int, hgvsp: str,
                 out_dir: Path) -> None:
    """PyMOL headless render of WT (context) and mutant (truncated) PNGs.

    wt_context.png:  WT window colored lightblue; variant residue as
                     a red sphere + labelled 'p.XyzN'
    mutant_full.png: Truncated sequence colored orange; C-terminal
                     end marked with a red 'cut' sphere
    """
    import pymol
    pymol.finish_launching(["pymol", "-cq"])
    from pymol import cmd
    cmd.reinitialize()

    label = hgvsp.replace("p.", "").replace("(", "").replace(")", "")
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- WT context ---
    cmd.load(str(wt_pdb), "wt")
    cmd.hide("everything", "wt")
    cmd.show("cartoon", "wt")
    cmd.color("lightblue", "wt")
    # Mark the variant residue (in WINDOW-relative coordinates) with a
    # red sphere on its Cα atom + label.
    sel = f"wt and resi {variant_residue_in_window} and name CA"
    cmd.show("spheres", sel)
    cmd.color("red", sel)
    cmd.set("sphere_scale", 2.5, sel)
    cmd.label(sel, f'"{label}"')
    cmd.set("label_size", 20)
    cmd.set("label_color", "black")
    cmd.set("label_font_id", 7)
    cmd.set("label_position", (0, 4, 0))
    cmd.bg_color("white")
    cmd.orient("wt")
    cmd.zoom("wt", buffer=3)
    cmd.set("ray_opaque_background", 1)
    cmd.set("ray_shadows", 0)
    cmd.png(str(out_dir / "wt_context.png"), width=800, height=600,
            dpi=150, ray=1)
    cmd.delete("all")

    # --- Mutant full (truncated) ---
    cmd.load(str(mut_pdb), "mut")
    cmd.hide("everything", "mut")
    cmd.show("cartoon", "mut")
    cmd.color("orange", "mut")
    # Mark the truncation point (C-terminus of the mutant window) with
    # a red sphere.
    n_res = cmd.count_atoms("mut and name CA")
    cut_sel = f"mut and resi {n_res} and name CA"
    cmd.show("spheres", cut_sel)
    cmd.color("red", cut_sel)
    cmd.set("sphere_scale", 2.8, cut_sel)
    cmd.label(cut_sel, '"CUT"')
    cmd.set("label_size", 22)
    cmd.set("label_color", "red")
    cmd.set("label_position", (0, 4, 0))
    cmd.bg_color("white")
    cmd.orient("mut")
    cmd.zoom("mut", buffer=3)
    cmd.png(str(out_dir / "mutant_full.png"), width=800, height=600,
            dpi=150, ray=1)
    cmd.delete("all")


def bake_one(variant: dict, dystrophin_seq: str) -> dict:
    """Fold + render for one variant. Returns per-variant status dict."""
    hgvsc = variant["hgvsc"]
    hgvsp = variant["hgvsp"]
    cons  = (variant["consequence"] or "").lower()
    residue = parse_residue(hgvsp)
    slug = slugify(hgvsc)
    out_dir = CACHE / slug

    print(f"[{variant['cohort']}#{variant['patient_id']}] {hgvsc} {hgvsp} ({cons})",
          flush=True)
    if residue is None:
        print(f"    skipped: no residue (consequence={cons})", flush=True)
        return {"variant": hgvsc, "status": "skipped_no_residue"}

    # WT window ±WINDOW around variant residue.
    r0 = residue - 1
    start0 = max(0, r0 - WINDOW)
    end0   = min(len(dystrophin_seq), r0 + WINDOW + 1)
    wt_window_seq = dystrophin_seq[start0:end0]
    var_in_window = residue - start0   # 1-based within window
    wt_pdb = out_dir / "wt_window.pdb"

    # Mutant window: last WINDOW aa BEFORE the cut. For a truncation at
    # residue r, the mutant protein is dystrophin_seq[0:r-1]. We fold
    # the terminal segment [max(0, r-1-WINDOW) : r-1] so the render
    # shows the C-terminus of the mutant, where the truncation happens.
    mut_start0 = max(0, r0 - WINDOW)
    mut_end0 = r0                      # exclusive
    mut_window_seq = dystrophin_seq[mut_start0:mut_end0]
    mut_pdb = out_dir / "mutant_window.pdb"

    try:
        fold_and_save(wt_window_seq, wt_pdb, "WT")
        fold_and_save(mut_window_seq, mut_pdb, "MUT")
    except Exception as e:
        print(f"    FOLD FAILED: {e}", flush=True)
        return {"variant": hgvsc, "status": "fold_error", "error": str(e)[:200]}

    try:
        render_pymol(wt_pdb, mut_pdb, residue, var_in_window, hgvsp, out_dir)
        print(f"    rendered → {out_dir.relative_to(REPO)}/", flush=True)
    except Exception as e:
        print(f"    RENDER FAILED: {e}", flush=True)
        return {"variant": hgvsc, "status": "render_error", "error": str(e)[:200]}

    return {"variant": hgvsc, "slug": slug, "status": "ok",
            "wt_pdb": str(wt_pdb.relative_to(REPO)),
            "mut_pdb": str(mut_pdb.relative_to(REPO))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", help="Bake only this HGVSc (e.g. c.6540del)")
    ap.add_argument("--all", action="store_true", help="Bake every cohort variant")
    args = ap.parse_args()

    if not (args.variant or args.all):
        ap.error("pass --variant HGVSc or --all")

    if not (os.environ.get("ESM3_API_KEY") or os.environ.get("ESM_API_KEY")):
        print("ERROR: ESM3_API_KEY not set. Try:\n"
              "  source /home/ubuntu/alms_inference_env/.env")
        return 1

    seq = load_dystrophin_sequence()
    print(f"[dystrophin] {len(seq)} aa (P11532 canonical)")

    variants = load_variants(specific=args.variant)
    if not variants:
        print(f"No matching variants for '{args.variant}'.")
        return 1
    print(f"[cohort] {len(variants)} variant(s) to bake\n")

    results = []
    for v in variants:
        results.append(bake_one(v, seq))
        print()

    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n[bake_protein_renders] {ok}/{len(results)} baked ok")
    for r in results:
        if r["status"] != "ok":
            print(f"  {r['variant']:24s}  {r['status']}  {r.get('error', '')}")
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    sys.exit(main())
