"""Fetch DMD single-cell expression from Human Protein Atlas → populate
mechanism.sqlite.celltype_expression.

HPA publishes a per-gene JSON that includes 'RNA single cell type specific
nCPM' — a dict of {cell_type: nCPM} for the cell types where the gene is
specifically enriched. For DMD this returns 7 cell types spanning muscle
(Myonuclei, Cardiomyocytes, Thymic/Salivary myoepithelial-like),
retina (Rod / Cone photoreceptors) and adipose. That's a real, pre-baked
substrate with a citeable source (proteinatlas.org, CC-BY-SA).

Limits: HPA's 'specific nCPM' set only includes cell types above its
specificity threshold. So the broader DMD isoform biology (Dp140/Dp71 in
CNS, Dp116 in Schwann cells, low baseline in kidney podocytes) does NOT
appear here — those would need a CellxGene bake. The tile footer flags
this.

Score = log10(nCPM) * 2.4 → tops out near 10 for high-expressing cell
types (Myonuclei @ ~15000 nCPM → ~10.0), floors near 7.5 for the low end
of HPA's specific set. Linear-in-nCPM would compress muscle vs. non-muscle
too tightly to read on a bar tile.

Run:
    python3 -m prototype.ingest.bake_hpa_expression
"""
from __future__ import annotations

import json
import math
import sqlite3
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MECH_DB = REPO / "data" / "mechanism.sqlite"
CACHE = REPO / "data" / "raw"
HPA_CACHE = CACHE / "hpa_dmd.json"

HPA_URL = "https://www.proteinatlas.org/ENSG00000198947.json"  # DMD

# cell_type substring → palette hint. First match wins.
COLOR_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("accent", ("myonuclei", "cardiomyocyte", "skeletal", "myocyte")),
    ("teal",   ("myoepithelial", "myoid", "smooth muscle")),
    ("pink",   ("photoreceptor", "rod", "cone", "retinal")),
    ("violet", ("neuron", "purkinje", "cortical", "hippocamp", "cerebell")),
    ("sky",    ("schwann", "endothel")),
]


def color_for(cell_type: str) -> str:
    n = cell_type.lower()
    for hint, keys in COLOR_RULES:
        if any(k in n for k in keys):
            return hint
    return "slate"


# Rough tissue guess from cell type name — HPA's specific-nCPM dict does
# not carry a tissue field, so we derive it. Used only for provenance /
# grouping; not shown in the tile.
def tissue_for(cell_type: str) -> str:
    n = cell_type.lower()
    if "myonuclei" in n or "skeletal" in n or "myocyte" in n:
        return "skeletal_muscle"
    if "cardiomyocyte" in n:
        return "heart"
    if "photoreceptor" in n or "retinal" in n or "rod" in n or "cone" in n:
        return "retina"
    if "adipocyte" in n:
        return "adipose"
    if "salivary" in n:
        return "salivary_gland"
    if "thymic" in n:
        return "thymus"
    if "breast" in n:
        return "breast"
    if "prostate" in n:
        return "prostate"
    return "other"


def download_hpa() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    if HPA_CACHE.exists() and HPA_CACHE.stat().st_size > 1000:
        print(f"[skip-download] {HPA_CACHE} ({HPA_CACHE.stat().st_size} bytes)")
        return HPA_CACHE
    print(f"[download] {HPA_URL}")
    req = urllib.request.Request(HPA_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp, HPA_CACHE.open("wb") as out:
        out.write(resp.read())
    print(f"[done] {HPA_CACHE} ({HPA_CACHE.stat().st_size} bytes)")
    return HPA_CACHE


def main() -> None:
    path = download_hpa()
    d = json.loads(path.read_text())

    ncpm = d.get("RNA single cell type specific nCPM") or {}
    if not ncpm:
        # HPA sometimes drops this key when a gene isn't specifically
        # enriched anywhere — bail loudly rather than silently write 0 rows
        raise SystemExit("HPA returned no 'RNA single cell type specific nCPM' for DMD")

    parsed = sorted(
        ((ct, float(v)) for ct, v in ncpm.items()),
        key=lambda x: -x[1],
    )
    print(f"[parse] {len(parsed)} cell types from HPA")
    for ct, v in parsed:
        print(f"  {v:>10.1f} nCPM  {ct}")

    conn = sqlite3.connect(MECH_DB)
    # wipe prior DMD rows (stubs OR previous HPA bake — both go)
    conn.execute("DELETE FROM celltype_expression WHERE gene_symbol='DMD'")

    rows = []
    for ct, nc in parsed:
        # log10-scale so the ~10x range across cell types spreads across
        # the 7.5-10 band of the tile, rather than compressing to 3-4.
        score = round(min(10.0, math.log10(max(nc, 1.0)) * 2.4), 2)
        rows.append((
            "DMD",
            "hpa",
            tissue_for(ct),
            ct,
            score,
            color_for(ct),
            "hpa",
        ))
    conn.executemany(
        "INSERT INTO celltype_expression VALUES (?,?,?,?,?,?,?)", rows,
    )
    conn.commit()

    print(f"\n[mechanism] wrote {len(rows)} DMD rows to celltype_expression")
    print("[mechanism] top-7 by score:")
    for r in conn.execute(
        "SELECT cell_type, score, color_hint FROM celltype_expression "
        "WHERE gene_symbol='DMD' ORDER BY score DESC LIMIT 7"
    ):
        print(f"  {r[1]:>5.2f}  [{r[2]:>6s}]  {r[0]}")
    conn.close()


if __name__ == "__main__":
    main()
