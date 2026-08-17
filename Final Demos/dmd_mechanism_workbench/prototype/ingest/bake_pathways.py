"""Bake Reactome pathway membership into data/pathways.sqlite AND populate
mechanism.sqlite.pathway_enrichment with DMD's scored memberships.

Iteration 1: Reactome only (~300 KB GMT, fully offline after one fetch).
GO-BP and KEGG slated for iteration 2 — Reactome alone covers muscle
contraction, DGC assembly, costamere, Ca²⁺ homeostasis and ECM
organisation, which are the pathway categories the mechanism workbench
surfaces for DMD.

Two outputs:
    data/pathways.sqlite → gene_pathway(gene_symbol, source, pathway_id, pathway_name)
                            (full membership catalogue for downstream use)
    data/mechanism.sqlite → pathway_enrichment rows for gene_symbol='DMD',
                            scored by pathway specificity (1/log(n_genes)),
                            color-hinted by keyword class.

Run:
    python3 -m prototype.ingest.bake_pathways
"""

from __future__ import annotations

import io
import math
import sqlite3
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "data" / "pathways.sqlite"
MECH_DB = REPO / "data" / "mechanism.sqlite"
CACHE = REPO / "data" / "raw"

REACTOME_URL = "https://reactome.org/download/current/ReactomePathways.gmt.zip"
REACTOME_GMT = CACHE / "ReactomePathways.gmt"

# Keyword → palette hint. First matching class wins (order matters).
# Kept small — the tile shows the top ~7 pathways and 3 buckets is
# enough visual grouping without a legend.
PATHWAY_COLOR_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("good",   ("muscle", "dystrophin", "sarcomere", "sarcoglycan",
                "dystroglycan", "costamere", "contract", "actin")),
    ("sky",    ("calcium", "ca2+", "membrane", "cytoskelet", "focal adhesion",
                "extracellular matrix", "ecm", "collagen", "laminin",
                "integrin", "mitochondri")),
    ("violet", ("immune", "inflamm", "cytokine", "tgf", "signal")),
]


def color_for(name: str) -> str:
    n = name.lower()
    for hint, keys in PATHWAY_COLOR_RULES:
        if any(k in n for k in keys):
            return hint
    return "slate"

SCHEMA = """
CREATE TABLE IF NOT EXISTS gene_pathway (
    gene_symbol TEXT NOT NULL,
    source      TEXT NOT NULL,
    pathway_id  TEXT NOT NULL,
    pathway_name TEXT NOT NULL,
    PRIMARY KEY (gene_symbol, source, pathway_id)
);
CREATE INDEX IF NOT EXISTS idx_gp_gene ON gene_pathway(gene_symbol);
CREATE INDEX IF NOT EXISTS idx_gp_pathway ON gene_pathway(pathway_id);

CREATE TABLE IF NOT EXISTS pathway_source_meta (
    source TEXT PRIMARY KEY,
    description TEXT,
    n_pathways INTEGER,
    n_gene_edges INTEGER,
    url TEXT
);
"""


def download_reactome() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    if REACTOME_GMT.exists() and REACTOME_GMT.stat().st_size > 1_000_000:
        print(f"[skip-download] {REACTOME_GMT} ({REACTOME_GMT.stat().st_size / 1e6:.1f} MB)")
        return REACTOME_GMT
    print(f"[download] {REACTOME_URL}")
    zip_path = CACHE / "ReactomePathways.gmt.zip"
    # Reactome 403s the default urllib UA — use a browser-style header
    req = urllib.request.Request(
        REACTOME_URL,
        headers={"User-Agent": "Mozilla/5.0 (alstroms_inference_env)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp, zip_path.open("wb") as out:
        out.write(resp.read())
    print(f"[unzip] {zip_path}")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if not names:
            sys.exit("empty zip")
        with zf.open(names[0]) as fp, REACTOME_GMT.open("wb") as out:
            out.write(fp.read())
    zip_path.unlink()
    print(f"[done] {REACTOME_GMT} ({REACTOME_GMT.stat().st_size / 1e6:.1f} MB)")
    return REACTOME_GMT


def parse_reactome_gmt(path: Path) -> list[tuple[str, str, str, str]]:
    """Reactome GMT format:
        <pathway_name>\t<R-HSA-XXXX URL or ID>\t<symbol>\t<symbol>\t...

    The species filter: Reactome's combined GMT bundles multiple species —
    we keep only human (R-HSA-*) rows.
    """
    rows: list[tuple[str, str, str, str]] = []
    n_lines = 0
    n_kept = 0
    with path.open() as fp:
        for line in fp:
            n_lines += 1
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 3:
                continue
            pathway_name = fields[0].strip()
            # field 1 is either the bare R-HSA-ID or a full Reactome URL
            id_field = fields[1].strip()
            if "R-HSA-" not in id_field:
                continue  # non-human
            # extract pathway_id (last URL segment that starts with R-HSA-)
            pathway_id = next(
                (seg for seg in id_field.split("/") if seg.startswith("R-HSA-")),
                id_field,
            )
            genes = [g.strip() for g in fields[2:] if g.strip()]
            for g in genes:
                rows.append((g, "reactome", pathway_id, pathway_name))
            n_kept += 1
    print(f"[parse] {n_kept} human pathways from {n_lines} lines; {len(rows)} (gene, pathway) edges")
    return rows


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    gmt = download_reactome()
    rows = parse_reactome_gmt(gmt)

    # wipe prior reactome rows so re-runs are idempotent
    conn.execute("DELETE FROM gene_pathway WHERE source = 'reactome'")
    conn.executemany(
        "INSERT OR REPLACE INTO gene_pathway "
        "(gene_symbol, source, pathway_id, pathway_name) VALUES (?, ?, ?, ?)",
        rows,
    )
    n_pathways = len({(r[2], r[3]) for r in rows})
    conn.execute(
        "INSERT OR REPLACE INTO pathway_source_meta "
        "(source, description, n_pathways, n_gene_edges, url) VALUES (?, ?, ?, ?, ?)",
        ("reactome", "Reactome human pathways (current GMT)", n_pathways, len(rows), REACTOME_URL),
    )
    conn.commit()

    # DMD sanity check
    print("\n[sanity] DMD Reactome memberships:")
    for r in conn.execute(
        "SELECT pathway_id, pathway_name FROM gene_pathway "
        "WHERE source='reactome' AND gene_symbol='DMD' "
        "ORDER BY pathway_id"
    ):
        print(f"  {r[0]:<14s}  {r[1]}")

    print(f"\n[output] {DB_PATH} ({DB_PATH.stat().st_size / 1e6:.1f} MB)")

    # Populate mechanism.sqlite.pathway_enrichment with DMD's rows,
    # scored by pathway specificity (smaller pathway → higher score).
    if MECH_DB.exists():
        write_dmd_enrichment_to_mechanism(conn)
    else:
        print(f"[skip] {MECH_DB} not present — run build_mechanism_sqlite first")

    conn.close()


def write_dmd_enrichment_to_mechanism(pathways_conn: sqlite3.Connection) -> None:
    """Push DMD's Reactome memberships into mechanism.sqlite.pathway_enrichment.

    Score = max(0, 10 − log(n_genes_in_pathway)); small/specific pathways
    rank higher than broad ones like 'Signal Transduction' (~600 genes,
    score ~3.6) and top out near 10 for singletons. This is a proxy for
    enrichment, not a real hypergeometric test — sufficient for the
    workbench tile, honest about its limits.
    """
    rows = pathways_conn.execute(
        "SELECT pathway_id, pathway_name FROM gene_pathway "
        "WHERE source='reactome' AND gene_symbol='DMD'"
    ).fetchall()

    # For each pathway DMD is in, count how many genes are in it.
    pathway_sizes = dict(pathways_conn.execute(
        "SELECT pathway_id, COUNT(*) FROM gene_pathway "
        "WHERE source='reactome' GROUP BY pathway_id"
    ).fetchall())

    mech = sqlite3.connect(MECH_DB)
    mech.execute("DELETE FROM pathway_enrichment WHERE source='reactome' AND gene_symbol='DMD'")
    inserted = 0
    for pid, name in rows:
        n_genes = pathway_sizes.get(pid, 1)
        score = round(max(0.0, 10.0 - math.log(max(n_genes, 1))), 2)
        mech.execute(
            "INSERT OR REPLACE INTO pathway_enrichment VALUES (?,?,?,?,?,?,?)",
            ("DMD", "reactome", pid, name, score, color_for(name), "reactome"),
        )
        inserted += 1
    mech.commit()

    print(f"\n[mechanism] wrote {inserted} DMD Reactome rows to pathway_enrichment")
    print("[mechanism] top-7 by specificity score:")
    for r in mech.execute(
        "SELECT pathway_name, score, color_hint FROM pathway_enrichment "
        "WHERE gene_symbol='DMD' AND source='reactome' "
        "ORDER BY score DESC LIMIT 7"
    ):
        print(f"  {r[1]:>5.2f}  [{r[2]:>6s}]  {r[0]}")
    mech.close()


if __name__ == "__main__":
    main()
