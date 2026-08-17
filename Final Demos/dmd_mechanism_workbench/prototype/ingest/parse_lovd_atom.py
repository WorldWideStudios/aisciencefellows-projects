"""Stream-parse the LOVD DMD Atom feed into a flat TSV.

Reads:  data/raw/dmd_lovd_atom.xml   (~38 MB, 41,566 entries)
Writes: data/variants/dmd_variants_raw.tsv
        data/variants/dmd_variants_unparseable.tsv  (fallback bucket)

Uses xml.etree.ElementTree.iterparse to stream — never builds the full
DOM. Each entry is cleared after processing to keep peak memory bounded.
Safe on the 1.9 GB box.

The output is a raw dump: one row per LOVD entry with the fields the
Atom feed exposes. Interpretation (Monaco rule, isoform effect, exon
lookup) happens in bake_dmd_variants.py.

Run:
    python -m prototype.ingest.parse_lovd_atom
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT = REPO_ROOT / "data" / "raw" / "dmd_lovd_atom.xml"
OUT_MAIN = REPO_ROOT / "data" / "variants" / "dmd_variants_raw.tsv"
OUT_UNPARSEABLE = REPO_ROOT / "data" / "variants" / "dmd_variants_unparseable.tsv"

ATOM_NS = "{http://www.w3.org/2005/Atom}"
RE_KV = re.compile(r"^\s*([\w/]+):(.*)$")


def classify_mut_type(hgvs: str) -> str:
    """Best-effort HGVS-suffix classifier. Order matters: most-specific first."""
    if not hgvs or hgvs == "c.?":
        return "unknown"
    # Chromosomal translocation cytogenetic notation
    if hgvs.startswith("t(") or hgvs.startswith("c.t("):
        return "translocation"
    # Compound / in-cis brackets: c.[variant1;variant2] or [[...]]
    if hgvs.startswith("c.[") or "[[" in hgvs:
        return "complex"
    # HGVS "no change confirmed" (silent)
    if hgvs.endswith("="):
        return "noop"
    # Repeat notation at end: {N} or [N] or ([...])
    if re.search(r"[\{\[]\(?[\d_]+\)?[\}\]]\)?$", hgvs):
        return "repeat"
    # Substitution
    if re.search(r"[ACGT]>[ACGT]", hgvs):
        return "sub"
    if "delins" in hgvs:
        return "delins"
    # Inversion — must precede del check (some end in "invACGT" or "inv)")
    if re.search(r"inv[ACGT]*\)?$", hgvs):
        return "inv"
    # Deletion — trailing "del" optionally followed by bases, optionally in brackets
    if re.search(r"del[ACGT]*\)?$", hgvs):
        return "del"
    if re.search(r"dup[ACGT]*\)?$", hgvs):
        return "dup"
    if "ins" in hgvs:
        return "ins"
    return "other"


def parse_content(text: str) -> dict[str, str]:
    """The <content type='text'> body is line-oriented `key:value`."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = RE_KV.match(line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def _tsv_safe(s: str) -> str:
    return s.replace("\t", " ").replace("\n", " ").replace("\r", " ")


def main() -> None:
    if not INPUT.exists():
        sys.exit(f"input missing: {INPUT}")

    OUT_MAIN.parent.mkdir(parents=True, exist_ok=True)

    cols_main = [
        "lovd_id", "dbid", "hgvs", "position_mrna", "position_genomic",
        "mut_type", "times_reported", "published", "updated",
    ]
    cols_unp = ["lovd_id", "dbid", "hgvs", "reason"]

    n_entries = 0
    n_main = 0
    n_unparseable = 0
    mut_type_hist: dict[str, int] = {}

    with OUT_MAIN.open("w") as f_main, OUT_UNPARSEABLE.open("w") as f_unp:
        f_main.write("\t".join(cols_main) + "\n")
        f_unp.write("\t".join(cols_unp) + "\n")

        for _, elem in ET.iterparse(str(INPUT), events=("end",)):
            if elem.tag != ATOM_NS + "entry":
                continue
            n_entries += 1

            published = (elem.findtext(ATOM_NS + "published") or "").strip()
            updated = (elem.findtext(ATOM_NS + "updated") or "").strip()
            content_text = elem.findtext(ATOM_NS + "content") or ""
            kv = parse_content(content_text)

            lovd_id = kv.get("id", "")
            dbid = kv.get("Variant/DBID", "")
            hgvs = kv.get("Variant/DNA", "")
            position_mrna = kv.get("position_mRNA", "")
            position_genomic = kv.get("position_genomic", "")
            times = kv.get("Times_reported", "")

            if not (lovd_id and hgvs):
                f_unp.write("\t".join(_tsv_safe(s) for s in [
                    lovd_id, dbid, hgvs, "missing_lovd_id_or_hgvs",
                ]) + "\n")
                n_unparseable += 1
                elem.clear()
                continue

            mut_type = classify_mut_type(hgvs)
            mut_type_hist[mut_type] = mut_type_hist.get(mut_type, 0) + 1

            f_main.write("\t".join(_tsv_safe(s) for s in [
                lovd_id, dbid, hgvs, position_mrna, position_genomic,
                mut_type, times, published, updated,
            ]) + "\n")
            n_main += 1
            elem.clear()

    print(f"[parsed] {n_entries:,} atom entries")
    print(f"[wrote]  {OUT_MAIN.name} ({n_main:,} rows)")
    print(f"[wrote]  {OUT_UNPARSEABLE.name} ({n_unparseable:,} rows)")
    print()
    print("[sanity] mut_type distribution:")
    for k in sorted(mut_type_hist, key=lambda x: -mut_type_hist[x]):
        n = mut_type_hist[k]
        pct = 100 * n / n_main
        print(f"  {k:<10s} {n:>7,}  ({pct:>5.1f}%)")


if __name__ == "__main__":
    main()
