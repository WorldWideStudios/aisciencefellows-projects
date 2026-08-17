#!/usr/bin/env python3
"""Bake per-edge DMD literature evidence via paperclip → PMC.

For each edge in the causal chain (variant → isoform → subcellular → pathway
→ cellType → tissue → phenotype), issue a paperclip PMC query and post-
filter results against a substrate vocabulary. Publication counts per edge
become the surrogate for evidence strength in downstream hypothesis
scoring — see LITERATURE_EVIDENCE_PLAN.md.

Adapted from ALMS1's bake_mutant_paperclip.py.

Run:
    ~/venv/bin/python -m prototype.ingest.bake_dmd_edge_literature
    ~/venv/bin/python -m prototype.ingest.bake_dmd_edge_literature --pilot
    ~/venv/bin/python -m prototype.ingest.bake_dmd_edge_literature --edge-type mech_phenotype
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB   = REPO / "data" / "mechanism.sqlite"
PAPERCLIP_CACHE = REPO / "cache" / "paperclip"

DEFAULT_SOURCE = "pmc"
DEFAULT_N = 100


# ----------------------------------------------------------------------
# Endpoint vocabularies — the substrate for post-filtering.
# ----------------------------------------------------------------------
# Isoforms with canonical first-shared-exon (from data/mechanism.sqlite:isoforms)
ISOFORMS = [
    ("Dp427m", 1,  "skeletal_muscle;cardiac_muscle",
     ["Dp427", "full-length dystrophin", "muscle dystrophin"]),
    ("Dp427c", 1,  "cortical_neurons;hippocampus",
     ["Dp427c", "cortical dystrophin"]),
    ("Dp427p", 1,  "cerebellar_Purkinje_cells",
     ["Dp427p", "Purkinje dystrophin"]),
    ("Dp260",  30, "retinal_photoreceptors",
     ["Dp260", "retinal dystrophin"]),
    ("Dp140",  45, "brain_glia;kidney",
     ["Dp140", "brain dystrophin"]),
    ("Dp116",  56, "peripheral_nerve_Schwann_cells",
     ["Dp116", "Schwann cell dystrophin"]),
    ("Dp71",   63, "retina;brain;kidney;liver;blood",
     ["Dp71", "ubiquitous dystrophin"]),
]

# Subcellular locations DMD isoforms occupy (UniProt P11532)
SUBCELLULAR_LOCATIONS = [
    ("sarcolemma",           ["sarcolemma", "muscle membrane", "plasma membrane"]),
    ("cytoskeleton",         ["cytoskeleton", "actin cytoskeleton"]),
    ("postsynaptic_membrane",["postsynaptic membrane", "postsynaptic density", "synaptic"]),
    ("nuclear_envelope",     ["nuclear membrane", "nuclear envelope"]),
]

# Tissue → search terms
TISSUE_TERMS = {
    "skeletal_muscle": ["skeletal muscle", "quadriceps", "diaphragm"],
    "heart":           ["heart", "cardiac muscle", "myocardium"],
    "retina":          ["retina", "retinal"],
    "cns":             ["brain", "cortex", "cerebellum", "CNS"],
    "kidney":          ["kidney", "renal", "podocyte", "glomerular"],
    "peripheral_nerve":["peripheral nerve", "Schwann"],
    "smooth_muscle":   ["smooth muscle", "vascular smooth muscle"],
    "adipose":         ["adipose", "adipocyte"],
    "salivary_gland":  ["salivary gland"],
}

# Phenotype nodes (from bake_hypothesis_frontier PHENOTYPE_SEVERITY) → search terms
PHENOTYPE_TERMS = {
    "respiratory_failure":                     ["respiratory failure", "respiratory insufficiency", "diaphragm weakness"],
    "cardiac_dysfunction":                     ["cardiomyopathy", "heart failure", "cardiac dysfunction"],
    "skeletal_muscle_fibro_fatty_replacement": ["fibro-fatty", "muscle fibrosis", "fatty infiltration"],
    "functional_impairment_ambulatory":        ["ambulation", "loss of walking", "wheelchair"],
    "cardiac_fibrosis":                        ["cardiac fibrosis", "myocardial fibrosis", "late gadolinium"],
    "cardiac_muscle_injury":                   ["troponin", "cardiac injury", "cardiomyocyte damage"],
    "skeletal_muscle_myonecrosis":             ["myonecrosis", "muscle necrosis", "creatine kinase"],
    "cns_cognitive":                           ["cognitive impairment", "learning disability", "intellectual disability", "IQ"],
    "renal_dysfunction":                       ["albuminuria", "renal dysfunction", "microalbuminuria"],
    "retinal_dysfunction":                     ["ERG b-wave", "negative b-wave", "retinal dysfunction"],
}

# Mechanism family search terms (DMD-canonical phrasings)
MECHANISM_TERMS = {
    "01": ["sarcolemmal fragility", "dystrophin absence", "dystrophin-null", "membrane fragility"],
    "02": ["Becker muscular dystrophy", "BMD", "in-frame deletion", "partial dystrophin"],
    "03": ["nonsense mediated decay", "NMD", "premature termination codon", "PTC readthrough"],
    "04": ["Dp140", "Dp71", "distal isoform", "distal dystrophin promoter"],
}

# Pathway short-name → substrate vocab (loaded from DB at runtime).
# Populated in bake().


# ----------------------------------------------------------------------
# SQLite schema
# ----------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS edge_literature_evidence (
  edge_type       TEXT NOT NULL,
  from_layer_key  TEXT NOT NULL,
  to_layer_key    TEXT NOT NULL,
  query           TEXT NOT NULL,
  paper_id        TEXT NOT NULL,
  paper_rank      INTEGER,
  title           TEXT,
  authors         TEXT,
  paper_source    TEXT,
  date            TEXT,
  url             TEXT,
  summary         TEXT,
  matched_terms   TEXT,
  PRIMARY KEY (edge_type, from_layer_key, to_layer_key, paper_id)
);

CREATE TABLE IF NOT EXISTS edge_literature_bake_meta (
  edge_type            TEXT NOT NULL,
  from_layer_key       TEXT NOT NULL,
  to_layer_key         TEXT NOT NULL,
  query                TEXT NOT NULL,
  n_papers_returned    INTEGER,
  n_papers_kept        INTEGER,
  baked_at             TEXT NOT NULL,
  PRIMARY KEY (edge_type, from_layer_key, to_layer_key)
);

CREATE INDEX IF NOT EXISTS ix_ele_edge ON edge_literature_evidence(edge_type);
CREATE INDEX IF NOT EXISTS ix_ele_from ON edge_literature_evidence(edge_type, from_layer_key);
"""


# ----------------------------------------------------------------------
# paperclip runner (same cache key as bake_mutant_paperclip.py)
# ----------------------------------------------------------------------
PAPER_HEADER_RE = re.compile(r"^\s*(\d+)\.\s+(.+)$")
META_LINE_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*·\s*([^·]+?)\s*·\s*([\d-]+)\s*$")


def _cache_path(query: str, source: str, n: int) -> Path:
    key = hashlib.sha1(f"{query}|{source}|{n}".encode()).hexdigest()
    return PAPERCLIP_CACHE / f"{key}.json"


def _parse_search_output(text: str) -> list[dict]:
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    papers: list[dict] = []
    current: dict | None = None
    summary_open = False
    for line in text.splitlines():
        m = PAPER_HEADER_RE.match(line)
        if m:
            if current:
                papers.append(current)
            current = {
                "rank": int(m.group(1)), "title": m.group(2).strip(),
                "authors": None, "paper_id": None, "source": None,
                "date": None, "url": None, "summary": None,
            }
            summary_open = False
            continue
        if current is None:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if summary_open:
            current["summary"] = (current["summary"] or "") + " " + stripped.rstrip('"')
            if stripped.endswith('"'):
                summary_open = False
            continue
        meta = META_LINE_RE.match(line)
        if meta:
            current["paper_id"] = meta.group(1).strip()
            current["source"] = meta.group(2).strip()
            current["date"] = meta.group(3).strip()
            continue
        if stripped.startswith(("http://", "https://")):
            current["url"] = stripped
            continue
        if stripped.startswith('"'):
            current["summary"] = stripped.strip('"').strip()
            if not stripped.endswith('"') or len(stripped) < 3:
                summary_open = True
            continue
        if current["authors"] is None:
            current["authors"] = stripped
            continue
        current["authors"] = (current["authors"] or "") + " " + stripped
    if current:
        papers.append(current)
    return papers


def _run_paperclip(query: str, source: str, n: int, timeout: int = 60) -> dict:
    cache = _cache_path(query, source, n)
    if cache.exists():
        return {**json.loads(cache.read_text()), "cache_hit": True}
    try:
        proc = subprocess.run(
            ["paperclip", "search", "-s", source, query, "-n", str(n)],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "query": query, "papers": []}
    except FileNotFoundError:
        return {"error": "paperclip not installed", "papers": []}
    if proc.returncode != 0:
        return {"error": "paperclip failed", "stderr": proc.stderr[-400:], "papers": []}
    papers = _parse_search_output(proc.stdout)[:n]
    result = {"query": query, "source": source, "count": len(papers),
              "papers": papers, "cache_hit": False}
    PAPERCLIP_CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result))
    return result


# ----------------------------------------------------------------------
# Post-filter: match paper title+summary against endpoint-specific vocab.
# ----------------------------------------------------------------------

# Domain-generic tokens ALWAYS added to from_vocab — a paper survives paperclip's
# semantic ranking for query "DMD X Y" and mentions the to-endpoint AND at least
# one domain token → it's on-topic to the edge, even if it doesn't use the
# specific mechanistic phrase (e.g. "sarcolemmal fragility") verbatim.
DOMAIN_TOKENS = ["DMD", "dystrophin", "Duchenne", "dystrophic"]


def _compile(terms: list[str]) -> list[tuple[str, re.Pattern]]:
    out = []
    seen = set()
    for t in sorted(terms, key=len, reverse=True):
        low = t.lower().strip()
        if not low or low in seen: continue
        seen.add(low)
        out.append((t, re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE)))
    return out


def _match(text: str, vocab: list[tuple[str, re.Pattern]]) -> list[str]:
    if not text: return []
    return [t for t, pat in vocab if pat.search(text)]


# ----------------------------------------------------------------------
# Query enumeration per edge type.
# Each yields: (from_key, to_key, query, from_vocab, to_vocab)
# ----------------------------------------------------------------------
# FDA-relevant + isoform-boundary exons (first pass) — full 79-exon
# enumeration is too many queries; these are the ones that matter clinically.
REPRESENTATIVE_EXONS = [1, 8, 30, 44, 45, 46, 51, 52, 53, 55, 56, 63, 74, 79]


def _iter_variant_isoform() -> list[tuple]:
    out = []
    for exon in REPRESENTATIVE_EXONS:
        for iso_id, first_exon, _tissues, iso_terms in ISOFORMS:
            # Only include this isoform if the exon is at or beyond its start.
            if exon < first_exon:
                continue
            query = f"DMD exon {exon} {iso_terms[0]}"
            from_key = f"exon_{exon}"
            to_key = iso_id
            from_vocab = _compile([f"exon {exon}", f"exon-{exon}"])
            to_vocab = _compile(iso_terms + [iso_id])
            out.append(("variant_isoform", from_key, to_key, query, from_vocab, to_vocab))
    return out


def _iter_isoform_subcellular() -> list[tuple]:
    out = []
    for iso_id, _fe, _tissues, iso_terms in ISOFORMS:
        for loc_key, loc_terms in SUBCELLULAR_LOCATIONS:
            query = f"dystrophin {iso_terms[0]} {loc_terms[0]}"
            from_vocab = _compile(iso_terms + [iso_id])
            to_vocab = _compile(loc_terms)
            out.append(("isoform_subcellular", iso_id, loc_key, query, from_vocab, to_vocab))
    return out


def _iter_celltype_tissue(conn) -> list[tuple]:
    """Iterate distinct (cell_type, tissue) pairs from the frontier."""
    rows = conn.execute(
        "SELECT DISTINCT cell_type, tissue FROM hypothesis_frontier"
    ).fetchall()
    out = []
    for (cell, tissue) in rows:
        if tissue not in TISSUE_TERMS: continue
        cell_term = cell.lower()
        tissue_terms = TISSUE_TERMS[tissue]
        query = f"DMD {cell_term} {tissue_terms[0]}"
        from_vocab = _compile([cell] + [cell_term])
        to_vocab = _compile(tissue_terms)
        out.append(("celltype_tissue", cell, tissue, query, from_vocab, to_vocab))
    return out


def _iter_tissue_phenotype() -> list[tuple]:
    """Only enumerate plausible tissue×phenotype pairs (from TISSUE_TO_PHENOTYPES)."""
    from prototype.ingest.bake_hypothesis_frontier import TISSUE_TO_PHENOTYPES
    out = []
    for tissue, phenotypes in TISSUE_TO_PHENOTYPES.items():
        if tissue not in TISSUE_TERMS: continue
        for pheno in phenotypes:
            if pheno not in PHENOTYPE_TERMS: continue
            tissue_terms = TISSUE_TERMS[tissue]
            pheno_terms = PHENOTYPE_TERMS[pheno]
            query = f"DMD {tissue_terms[0]} {pheno_terms[0]}"
            from_vocab = _compile(tissue_terms)
            to_vocab = _compile(pheno_terms)
            out.append(("tissue_phenotype", tissue, pheno, query, from_vocab, to_vocab))
    return out


def _iter_mech_phenotype() -> list[tuple]:
    out = []
    for mech_id, mech_terms in MECHANISM_TERMS.items():
        for pheno, pheno_terms in PHENOTYPE_TERMS.items():
            query = f"DMD {mech_terms[0]} {pheno_terms[0]}"
            from_vocab = _compile(mech_terms + [f"H{mech_id}"])
            to_vocab = _compile(pheno_terms)
            out.append(("mech_phenotype", mech_id, pheno, query, from_vocab, to_vocab))
    return out


def _iter_pathway_celltype(conn) -> list[tuple]:
    """Top 20 frontier pathways × top 20 frontier cell types — capped."""
    rows = conn.execute("""
        SELECT DISTINCT pathway_id, pathway_name FROM hypothesis_frontier
    """).fetchall()
    cells = conn.execute("""
        SELECT DISTINCT cell_type FROM hypothesis_frontier
    """).fetchall()
    out = []
    for (pw_id, pw_name) in rows:
        # Short-name = drop "Formation of the " / "Assembly of the " / suffix noise
        short = re.sub(r"^(Formation|Assembly|Regulation) of (the )?", "", pw_name)
        short = short.split(",")[0].split(":")[0].strip()
        pw_vocab = _compile([short, pw_name])
        for (cell,) in cells:
            query = f"DMD {short} {cell.lower()}"
            cell_vocab = _compile([cell, cell.lower()])
            out.append(("pathway_celltype", pw_id, cell, query, pw_vocab, cell_vocab))
    return out


ITER_FNS = {
    "variant_isoform":     lambda conn: _iter_variant_isoform(),
    "isoform_subcellular": lambda conn: _iter_isoform_subcellular(),
    "celltype_tissue":     lambda conn: _iter_celltype_tissue(conn),
    "tissue_phenotype":    lambda conn: _iter_tissue_phenotype(),
    "mech_phenotype":      lambda conn: _iter_mech_phenotype(),
    "pathway_celltype":    lambda conn: _iter_pathway_celltype(conn),
}


# ----------------------------------------------------------------------
# Bake driver
# ----------------------------------------------------------------------
def bake(source: str, n_per_query: int, edge_types: list[str],
         limit: int | None, force: bool) -> None:
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)

    # Assemble all queries
    all_queries: list[tuple] = []
    for et in edge_types:
        fn = ITER_FNS.get(et)
        if not fn:
            print(f"[warn] unknown edge type '{et}' — skipping")
            continue
        queries = fn(conn)
        print(f"[queries] {et:22s}  {len(queries)}")
        all_queries.extend(queries)
    print(f"[total-queries] {len(all_queries)}")

    if limit:
        all_queries = all_queries[:limit]
        print(f"[limited] {len(all_queries)} queries after --limit")

    baked_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    n_total_returned = 0
    n_total_kept = 0
    n_cached = 0
    n_fresh = 0
    hits_by_edge: dict[str, int] = {}

    for i, (et, from_key, to_key, query, from_vocab, to_vocab) in enumerate(all_queries):
        if not force:
            existing = conn.execute(
                "SELECT 1 FROM edge_literature_bake_meta "
                "WHERE edge_type=? AND from_layer_key=? AND to_layer_key=?",
                (et, from_key, to_key)).fetchone()
            if existing:
                # Already baked this query at least once — skip
                continue

        result = _run_paperclip(query, source, n_per_query)
        if result.get("cache_hit"): n_cached += 1
        else: n_fresh += 1

        if result.get("error"):
            print(f"  [{i+1:3d}/{len(all_queries)}] {et:22s}  {query[:60]:60s}  ERR: {result['error']}")
            continue

        papers = result.get("papers", [])
        n_total_returned += len(papers)
        kept = 0
        # Augment from_vocab with domain-generic tokens (see DOMAIN_TOKENS comment)
        from_vocab_ext = from_vocab + _compile(DOMAIN_TOKENS)
        for p in papers:
            haystack = " ".join(filter(None, [p.get("title"), p.get("summary")]))
            from_hits = _match(haystack, from_vocab_ext)
            to_hits   = _match(haystack, to_vocab)
            # Post-filter: BOTH endpoints must appear. The from-side now includes
            # DMD/dystrophin/Duchenne as fallback so mechanism-heavy edges pass.
            if not from_hits or not to_hits:
                continue
            all_hits = list(dict.fromkeys(from_hits + to_hits))  # dedupe, preserve order
            conn.execute(
                """INSERT OR REPLACE INTO edge_literature_evidence
                   (edge_type, from_layer_key, to_layer_key, query,
                    paper_id, paper_rank, title, authors, paper_source,
                    date, url, summary, matched_terms)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (et, from_key, to_key, query,
                 p.get("paper_id") or f"__norank_{p.get('rank')}",
                 p.get("rank"), p.get("title"), p.get("authors"),
                 p.get("source"), p.get("date"), p.get("url"),
                 p.get("summary"), json.dumps(all_hits)))
            kept += 1
        n_total_kept += kept
        hits_by_edge[et] = hits_by_edge.get(et, 0) + kept

        conn.execute(
            """INSERT OR REPLACE INTO edge_literature_bake_meta
               (edge_type, from_layer_key, to_layer_key, query,
                n_papers_returned, n_papers_kept, baked_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (et, from_key, to_key, query, len(papers), kept, baked_at))

        cache_tag = "cached" if result.get("cache_hit") else "fresh"
        print(f"  [{i+1:3d}/{len(all_queries)}] {et:22s}  {query[:56]:56s}  "
              f"{len(papers):3d}→{kept:3d}  {cache_tag}", flush=True)

        # Commit every query so partial progress always persists (this bake
        # keeps dying to background-shell timeout on this box).
        conn.commit()

    conn.commit()
    conn.close()

    print("")
    print("[summary]")
    print(f"  queries executed  : {len(all_queries)} ({n_cached} cached, {n_fresh} fresh)")
    print(f"  papers returned   : {n_total_returned}")
    print(f"  papers kept       : {n_total_kept}")
    print("[per-edge-type hits]")
    for et in sorted(hits_by_edge.keys()):
        print(f"  {et:22s}  {hits_by_edge[et]}")
    print(f"  → {DB}::edge_literature_evidence")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--n-per-query", type=int, default=DEFAULT_N)
    ap.add_argument("--edge-type", action="append",
                    help=f"Restrict to one edge type. Can repeat. Choices: {sorted(ITER_FNS)}")
    ap.add_argument("--limit", type=int, default=None,
                    help="Cap total number of queries (for pilot runs)")
    ap.add_argument("--force", action="store_true",
                    help="Re-run queries already in bake_meta")
    ap.add_argument("--pilot", action="store_true",
                    help="Pilot mode: --n-per-query 5, --limit 20")
    args = ap.parse_args()
    if args.pilot:
        args.n_per_query = 5
        args.limit = 20
    edge_types = args.edge_type or list(ITER_FNS.keys())
    try:
        bake(args.source, args.n_per_query, edge_types, args.limit, args.force)
    except KeyboardInterrupt:
        sys.exit("\n[interrupt] partial results committed; re-run to resume.")


if __name__ == "__main__":
    main()
