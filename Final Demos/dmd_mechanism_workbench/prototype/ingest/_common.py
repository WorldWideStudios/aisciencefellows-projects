"""Shared helpers for baking per-(source, tissue, cell_type, gene) stats into SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
from scipy import sparse

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "data" / "expression.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS gene_celltype_expression (
    gene_symbol TEXT NOT NULL,
    ensembl_id  TEXT,
    source      TEXT NOT NULL,
    tissue      TEXT NOT NULL,
    cell_type   TEXT NOT NULL,
    cell_type_ontology_id TEXT,
    n_cells     INTEGER NOT NULL,
    pct_detected REAL NOT NULL,
    mean_all    REAL NOT NULL,
    mean_detected REAL,
    PRIMARY KEY (gene_symbol, source, tissue, cell_type)
);
CREATE INDEX IF NOT EXISTS idx_gene ON gene_celltype_expression(gene_symbol);
CREATE INDEX IF NOT EXISTS idx_gene_source ON gene_celltype_expression(gene_symbol, source);
CREATE INDEX IF NOT EXISTS idx_source_tissue ON gene_celltype_expression(source, tissue);

CREATE TABLE IF NOT EXISTS source_meta (
    source TEXT PRIMARY KEY,
    description TEXT,
    n_cells INTEGER,
    n_genes INTEGER,
    n_celltypes INTEGER,
    citation TEXT,
    url TEXT
);
"""


def open_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def group_stats(
    expr_block: sparse.csr_matrix,
    counts_block: sparse.csr_matrix | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-gene (pct_detected, mean_all, mean_detected) over one group.

    expr_block:   matrix used for mean (log-normalized or normalized values).
    counts_block: matrix used for "detected" (raw counts > 0). If None,
                  detection is defined as expr > 0.

    Returns numpy arrays of shape (n_genes,). mean_detected is 0 where
    pct_detected is 0; caller should NULL-out those entries on insert.
    """
    detect_block = counts_block if counts_block is not None else expr_block
    if not sparse.issparse(detect_block):
        detect_block = sparse.csr_matrix(detect_block)
    if not sparse.issparse(expr_block):
        expr_block = sparse.csr_matrix(expr_block)

    n_cells = expr_block.shape[0]

    detected_mask = (detect_block > 0).astype(np.float32)
    n_detected = np.asarray(detected_mask.sum(axis=0)).ravel()
    pct_detected = (n_detected / n_cells) * 100.0

    expr_sum_all = np.asarray(expr_block.sum(axis=0)).ravel()
    mean_all = expr_sum_all / n_cells

    expr_detected = expr_block.multiply(detected_mask)
    expr_sum_detected = np.asarray(expr_detected.sum(axis=0)).ravel()
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_detected = np.where(n_detected > 0, expr_sum_detected / n_detected, 0.0)

    return pct_detected, mean_all, mean_detected


def insert_group(
    conn: sqlite3.Connection,
    *,
    source: str,
    tissue: str,
    cell_type: str,
    cell_type_ontology_id: str | None,
    n_cells: int,
    gene_symbols: np.ndarray,
    ensembl_ids: np.ndarray,
    pct_detected: np.ndarray,
    mean_all: np.ndarray,
    mean_detected: np.ndarray,
    keep_zero_detected: bool = False,
) -> int:
    """Insert one (source, tissue, cell_type) block. Returns rows written."""
    rows = []
    for i in range(len(gene_symbols)):
        pct = float(pct_detected[i])
        if not keep_zero_detected and pct == 0.0:
            continue
        sym = gene_symbols[i]
        ens = ensembl_ids[i] if ensembl_ids is not None else None
        if sym is None or (isinstance(sym, float) and np.isnan(sym)):
            if ens is None:
                continue
            sym = ens
        rows.append((
            str(sym),
            str(ens) if ens is not None and not (isinstance(ens, float) and np.isnan(ens)) else None,
            source,
            tissue,
            cell_type,
            cell_type_ontology_id,
            int(n_cells),
            pct,
            float(mean_all[i]),
            float(mean_detected[i]) if pct > 0 else None,
        ))
    if not rows:
        return 0
    conn.executemany(
        "INSERT OR REPLACE INTO gene_celltype_expression "
        "(gene_symbol, ensembl_id, source, tissue, cell_type, cell_type_ontology_id, "
        " n_cells, pct_detected, mean_all, mean_detected) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def upsert_source_meta(
    conn: sqlite3.Connection,
    *,
    source: str,
    description: str,
    n_cells: int,
    n_genes: int,
    n_celltypes: int,
    citation: str,
    url: str,
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO source_meta "
        "(source, description, n_cells, n_genes, n_celltypes, citation, url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (source, description, n_cells, n_genes, n_celltypes, citation, url),
    )
