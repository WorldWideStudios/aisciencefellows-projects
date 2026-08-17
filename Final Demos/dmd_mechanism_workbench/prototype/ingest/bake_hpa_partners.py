"""Bake HPA single-cell expression for the DMD DGC partners.

Extends celltype_expression (currently only holds DMD's 7 cell types)
with per-cell-type expression for the 12 top DMD interactors so the
Lauren tab can rank cell types by DGC-completeness (how many DGC
components are co-expressed there), not just by DMD expression magnitude.

Run: ~/venv/bin/python -m prototype.ingest.bake_hpa_partners
"""
from __future__ import annotations

import json
import math
import sqlite3
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MECH_DB   = REPO / "data" / "mechanism.sqlite"
CACHE_DIR = REPO / "data" / "raw"

# Ensembl gene IDs for the 12 DMD interactors (top STRING/OT co-DGC set).
PARTNERS = {
    "DAG1":  "ENSG00000173991",
    "SNTA1": "ENSG00000101400",
    "SNTB1": "ENSG00000172164",
    "SNTB2": "ENSG00000168807",
    "SGCA":  "ENSG00000108823",
    "SGCB":  "ENSG00000163069",
    "SGCD":  "ENSG00000170624",
    "SGCG":  "ENSG00000102683",
    "DTNA":  "ENSG00000134769",
    "DTNB":  "ENSG00000144228",
    "UTRN":  "ENSG00000152818",
    "CAV3":  "ENSG00000182533",
    "SSPN":  "ENSG00000123096",
}


def tissue_for(cell_type: str) -> str:
    n = cell_type.lower()
    if "myonuclei" in n or "skeletal" in n or "myocyte" in n:  return "skeletal_muscle"
    if "cardiomyocyte" in n:                                    return "heart"
    if "photoreceptor" in n or "retinal" in n or "rod" in n or "cone" in n: return "retina"
    if "adipocyte" in n:                                        return "adipose"
    if "salivary" in n:                                         return "salivary_gland"
    if "thymic" in n:                                           return "thymus"
    if "breast" in n:                                           return "breast"
    if "prostate" in n:                                         return "prostate"
    if "purkinje" in n or "neuron" in n or "cortic" in n or "cerebell" in n: return "cns"
    if "schwann" in n:                                          return "peripheral_nerve"
    if "kidney" in n or "podocyte" in n or "renal" in n:        return "kidney"
    if "liver" in n or "hepatocyte" in n:                       return "liver"
    if "endothel" in n:                                         return "vascular"
    if "smooth muscle" in n:                                    return "smooth_muscle"
    return "other"


def color_for(cell_type: str) -> str:
    n = cell_type.lower()
    if any(k in n for k in ("myonuclei", "cardiomyocyte", "skeletal", "myocyte")): return "accent"
    if any(k in n for k in ("myoepithelial", "myoid", "smooth muscle")):           return "teal"
    if any(k in n for k in ("photoreceptor", "rod", "cone", "retinal")):           return "pink"
    if any(k in n for k in ("neuron", "purkinje", "cortical", "hippocamp", "cerebell")): return "violet"
    if any(k in n for k in ("schwann", "endothel")):                               return "sky"
    return "slate"


def fetch_hpa(symbol: str, ensg: str) -> dict | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"hpa_{symbol}.json"
    if cache.exists() and cache.stat().st_size > 1000:
        return json.loads(cache.read_text())
    url = f"https://www.proteinatlas.org/{ensg}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    print(f"  [download] {symbol} → {url}", flush=True)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
    except Exception as e:
        print(f"    FAILED: {e}", flush=True)
        return None
    cache.write_bytes(body)
    time.sleep(0.5)   # polite
    return json.loads(body.decode())


def main() -> None:
    conn = sqlite3.connect(MECH_DB)
    # Wipe prior partner rows (leave DMD's rows alone).
    q_placeholders = ",".join(["?"] * len(PARTNERS))
    conn.execute(
        f"DELETE FROM celltype_expression WHERE source='hpa' AND gene_symbol IN ({q_placeholders})",
        list(PARTNERS.keys()),
    )

    rows: list[tuple] = []
    partner_counts: dict[str, int] = {}
    for symbol, ensg in PARTNERS.items():
        d = fetch_hpa(symbol, ensg)
        if not d:
            partner_counts[symbol] = 0
            continue
        ncpm = d.get("RNA single cell type specific nCPM") or {}
        if not ncpm:
            print(f"  [{symbol}] no specific nCPM (broad expression only)", flush=True)
            partner_counts[symbol] = 0
            continue
        partner_counts[symbol] = len(ncpm)
        for ct, v in ncpm.items():
            score = round(min(10.0, math.log10(max(float(v), 1.0)) * 2.4), 2)
            rows.append((
                symbol, "hpa", tissue_for(ct), ct, score, color_for(ct), "hpa",
            ))

    conn.executemany("INSERT INTO celltype_expression VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()

    print(f"\n[mechanism] wrote {len(rows)} partner rows for {len(PARTNERS)} genes")
    print("[per-partner cell-type counts]")
    for sym in PARTNERS:
        print(f"  {sym:<6} {partner_counts.get(sym, 0):>3} cell types")
    conn.close()


if __name__ == "__main__":
    main()
