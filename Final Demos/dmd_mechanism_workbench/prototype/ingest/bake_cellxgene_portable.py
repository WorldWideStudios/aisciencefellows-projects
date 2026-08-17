#!/usr/bin/env python3
"""Portable CellxGene atlas bake — run on the same ≥ 8 GB host as bake_gtex_portable.

Bakes the 4 CellxGene tissue atlases (eye / kidney / liver / pancreas) into
SQLite rows with the same schema as `bake_gtex_portable.py`. Run after (or
before) the GTEx bake on the bigger host; scp one SQLite back to the dev
box and merge with the same `ATTACH / INSERT INTO` one-liner.

The script is defensive about CellxGene schema variation:
  - gene symbol lives in `var["feature_name"]` when present, else var_names
  - Ensembl ID lives in var_names when symbols are in feature_name, else var["feature_id"]
  - Cell type label from `obs["cell_type"]`; Cell Ontology ID from
    `obs["cell_type_ontology_term_id"]`
  - Tissue from `obs["tissue"]`
  - Detection mask uses `.raw.X` (raw counts) when present, else `.X > 0`

Usage:
    # Bake all 4 cxg sources in sequence (downloads each on demand)
    python bake_cellxgene_portable.py default cxg_rows.sqlite

    # Bake just one source from a local h5ad
    python bake_cellxgene_portable.py /path/to/eye.h5ad cxg_eye cxg_rows.sqlite

Sources / URLs (CellxGene dataset IDs):
    cxg_eye      e9b8ea4b-7901-4992-94c7-8e85ccd06fb5
    cxg_kidney   76b6cf23-56db-4eac-8ee8-d84ce64c0395
    cxg_liver    a4b3a49e-062b-4e3f-8915-02f40607651f
    cxg_pancreas ba587dee-e050-4a31-bcb8-05e5418f9086
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

import anndata as ad
import numpy as np
from scipy import sparse

SOURCES: dict[str, dict[str, str]] = {
    "cxg_eye": {
        "url": "https://datasets.cellxgene.cziscience.com/e9b8ea4b-7901-4992-94c7-8e85ccd06fb5.h5ad",
        "description": "CellxGene eye atlas",
    },
    "cxg_kidney": {
        "url": "https://datasets.cellxgene.cziscience.com/76b6cf23-56db-4eac-8ee8-d84ce64c0395.h5ad",
        "description": "CellxGene kidney atlas",
    },
    "cxg_liver": {
        "url": "https://datasets.cellxgene.cziscience.com/a4b3a49e-062b-4e3f-8915-02f40607651f.h5ad",
        "description": "CellxGene liver atlas",
    },
    "cxg_pancreas": {
        "url": "https://datasets.cellxgene.cziscience.com/ba587dee-e050-4a31-bcb8-05e5418f9086.h5ad",
        "description": "CellxGene pancreas atlas",
    },
}

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


def _hr(n: int) -> str:
    if n >= 1e9:
        return f"{n / 1e9:.2f} GB"
    if n >= 1e6:
        return f"{n / 1e6:.1f} MB"
    return f"{n / 1e3:.0f} KB"


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 10_000_000:
        print(f"  [skip-download] reusing {dest} ({_hr(dest.stat().st_size)})")
        return dest
    print(f"  [download] {url}")
    t0 = time.time()

    def _progress(chunk: int, chunk_size: int, total: int) -> None:
        done = chunk * chunk_size
        if total > 0 and chunk % 200 == 0:
            pct = min(100.0, 100.0 * done / total)
            sys.stdout.write(f"\r    {pct:5.1f}%  {_hr(done)} / {_hr(total)}")
            sys.stdout.flush()

    urllib.request.urlretrieve(url, dest, reporthook=_progress)
    sys.stdout.write("\n")
    print(f"  [done] {_hr(dest.stat().st_size)} in {time.time() - t0:.0f} s")
    return dest


def resolve_gene_columns(a: ad.AnnData) -> tuple[np.ndarray, np.ndarray]:
    """Return (gene_symbols, ensembl_ids) for the var axis, handling CellxGene quirks."""
    var = a.var
    var_names = a.var_names.to_numpy()

    # CellxGene convention: var_names = Ensembl IDs, var["feature_name"] = symbol
    if "feature_name" in var.columns:
        symbols = var["feature_name"].to_numpy()
        # CellxGene's feature_id (if present) duplicates var_names; var_names IS the Ensembl
        ensembl = var_names
        return symbols, ensembl

    # Fallback: some files store symbols in var_names and Ensembl in a column
    for col in ("gene_ids", "gene_id", "ensembl_id"):
        if col in var.columns:
            return var_names, var[col].to_numpy()

    # Last resort: only var_names — use as both
    return var_names, var_names


def resolve_counts_block(
    a: ad.AnnData, idx: np.ndarray
) -> sparse.csr_matrix:
    """Return the matrix block used for the 'detected' mask.

    Prefers `.raw.X` (raw counts) when present; falls back to `.X` (whose
    `> 0` mask is still a valid detection signal even if normalized).
    """
    if a.raw is not None:
        try:
            return a.raw.X[idx]
        except Exception:
            pass
    return a.X[idx]


def group_stats(
    expr_block: sparse.csr_matrix,
    counts_block: sparse.csr_matrix,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not sparse.issparse(expr_block):
        expr_block = sparse.csr_matrix(expr_block)
    if not sparse.issparse(counts_block):
        counts_block = sparse.csr_matrix(counts_block)

    n_cells = expr_block.shape[0]
    detected_mask = (counts_block > 0).astype(np.float32)
    n_detected = np.asarray(detected_mask.sum(axis=0)).ravel()
    pct_detected = (n_detected / n_cells) * 100.0

    mean_all = np.asarray(expr_block.sum(axis=0)).ravel() / n_cells

    expr_detected_sum = np.asarray(
        expr_block.multiply(detected_mask).sum(axis=0)
    ).ravel()
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_detected = np.where(
            n_detected > 0, expr_detected_sum / n_detected, 0.0
        )

    return pct_detected, mean_all, mean_detected


def bake_one(
    h5ad_path: Path,
    source: str,
    conn: sqlite3.Connection,
) -> int:
    """Bake one source into the shared sqlite. Returns rows inserted."""
    print(f"\n=== {source}  ({h5ad_path.name}) ===")
    a = ad.read_h5ad(h5ad_path, backed="r")
    print(f"  shape: cells={a.shape[0]:,}  genes={a.shape[1]:,}")
    if "cell_type" not in a.obs.columns:
        sys.exit(f"  expected obs['cell_type'] in {source} — abort")
    if "tissue" not in a.obs.columns:
        print(f"  [warn] no obs['tissue'] in {source} — using source name as tissue")

    gene_symbols, ensembl_ids = resolve_gene_columns(a)
    print(f"  gene_symbols[:3] = {list(gene_symbols[:3])}")
    print(f"  ensembl_ids[:3]  = {list(ensembl_ids[:3])}")

    obs = a.obs
    has_tissue = "tissue" in obs.columns
    has_ont = "cell_type_ontology_term_id" in obs.columns

    # Build groups
    if has_tissue:
        group_keys = list(zip(obs["tissue"].astype(str), obs["cell_type"].astype(str)))
    else:
        group_keys = list(zip([source] * len(obs), obs["cell_type"].astype(str)))

    print(f"  building cell-id → row-index map ...")
    cell_to_idx = {c: i for i, c in enumerate(a.obs_names)}

    print(f"  grouping by (tissue, cell_type) ...")
    if has_tissue:
        gb = obs.groupby(["tissue", "cell_type"], observed=True)
    else:
        gb = obs.groupby(["cell_type"], observed=True)

    groups: dict[tuple[str, str], tuple[np.ndarray, str | None]] = {}
    for key, df in gb:
        if has_tissue:
            tissue, cell_type = key  # type: ignore[misc]
        else:
            tissue = source
            cell_type = key  # type: ignore[assignment]
        idx = np.fromiter(
            (cell_to_idx[c] for c in df.index), dtype=np.int64, count=len(df)
        )
        if not len(idx):
            continue
        ont_id = None
        if has_ont:
            ont_vals = df["cell_type_ontology_term_id"].astype(str).unique()
            ont_id = str(ont_vals[0]) if len(ont_vals) else None
        groups[(str(tissue), str(cell_type))] = (idx, ont_id)

    n_groups = len(groups)
    print(f"  {n_groups} (tissue, cell_type) combos")

    rows_inserted = 0
    t0 = time.time()
    for i, ((tissue, cell_type), (idx, ont_id)) in enumerate(
        sorted(groups.items()), start=1
    ):
        gstart = time.time()
        n = int(len(idx))
        expr_block = a.X[idx]
        counts_block = resolve_counts_block(a, idx)

        pct_det, mean_all, mean_det = group_stats(expr_block, counts_block)

        rows: list[tuple] = []
        for gi in range(len(gene_symbols)):
            pct = float(pct_det[gi])
            if pct == 0.0:
                continue
            sym = gene_symbols[gi]
            ens = ensembl_ids[gi]
            if sym is None or (isinstance(sym, float) and np.isnan(sym)):
                if ens is None:
                    continue
                sym = ens
            rows.append(
                (
                    str(sym),
                    str(ens)
                    if ens is not None
                    and not (isinstance(ens, float) and np.isnan(ens))
                    else None,
                    source,
                    tissue,
                    cell_type,
                    ont_id,
                    n,
                    pct,
                    float(mean_all[gi]),
                    float(mean_det[gi]),
                )
            )

        if rows:
            conn.executemany(
                "INSERT OR REPLACE INTO gene_celltype_expression "
                "(gene_symbol, ensembl_id, source, tissue, cell_type, "
                " cell_type_ontology_id, n_cells, pct_detected, mean_all, mean_detected) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        rows_inserted += len(rows)
        print(
            f"  [{i:3d}/{n_groups}] {tissue[:24]:<24s} {cell_type[:36]:<36s} "
            f"n={n:>5d}  rows={len(rows):>6d}  {time.time() - gstart:5.1f}s"
        )
        del expr_block, counts_block, pct_det, mean_all, mean_det, rows

    description = SOURCES.get(source, {}).get("description", source)
    url = SOURCES.get(source, {}).get("url", "")
    conn.execute(
        "INSERT OR REPLACE INTO source_meta "
        "(source, description, n_cells, n_genes, n_celltypes, citation, url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            source,
            description,
            int(a.shape[0]),
            int(a.shape[1]),
            n_groups,
            "CellxGene Census",
            url,
        ),
    )
    conn.commit()

    elapsed = time.time() - t0
    print(
        f"  [done {source}] {rows_inserted:,} rows in {elapsed / 60:.1f} min"
    )
    a.file.close()
    return rows_inserted


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Bake CellxGene atlases into portable SQLite."
    )
    ap.add_argument(
        "input",
        help="'default' to download + bake all 4 cxg sources; "
        "or a local h5ad path (then requires source_tag)",
    )
    ap.add_argument(
        "source_or_output",
        help="If input is a path: the source tag (cxg_eye / cxg_kidney / "
        "cxg_liver / cxg_pancreas). If input is 'default': the output sqlite path.",
    )
    ap.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output sqlite path (required when input is a local h5ad).",
    )
    ap.add_argument(
        "--scratch",
        default="/tmp",
        help="Directory for downloaded h5ad files (default: /tmp)",
    )
    args = ap.parse_args()

    if args.input == "default":
        out = Path(args.source_or_output)
        targets = list(SOURCES.keys())
    else:
        if args.output is None:
            sys.exit("local h5ad mode requires: <h5ad_path> <source_tag> <output_sqlite>")
        if args.source_or_output not in SOURCES:
            sys.exit(
                f"unknown source tag '{args.source_or_output}'. "
                f"expected one of: {list(SOURCES)}"
            )
        out = Path(args.output)
        targets = [args.source_or_output]

    out.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(out)
    conn.executescript(SCHEMA)

    scratch = Path(args.scratch)
    grand_total = 0
    overall_t0 = time.time()

    for source in targets:
        if args.input == "default":
            url = SOURCES[source]["url"]
            h5ad_path = download(url, scratch / f"{source}.h5ad")
        else:
            h5ad_path = Path(args.input)
            if not h5ad_path.exists():
                sys.exit(f"input not found: {h5ad_path}")
        grand_total += bake_one(h5ad_path, source, conn)

    # DMD sanity check across all sources baked
    sanity = conn.execute(
        "SELECT source, tissue, cell_type, n_cells, pct_detected, mean_detected "
        "FROM gene_celltype_expression "
        "WHERE gene_symbol = 'DMD' "
        "ORDER BY pct_detected DESC LIMIT 10",
    ).fetchall()
    print("\n[sanity] DMD top-10 (source, tissue, cell_type) by pct_detected:")
    if not sanity:
        print("  (no DMD rows — check gene-symbol resolution)")
    for src, tissue, cell_type, n, pct, mean_det in sanity:
        print(
            f"  {src:<14s} {tissue[:24]:<24s} {cell_type[:36]:<36s} "
            f"n={n:>5d}  pct={pct:>5.2f}%  mean_det={mean_det:.3f}"
        )

    elapsed = time.time() - overall_t0
    print(
        f"\n[all done] {grand_total:,} rows across {len(targets)} sources "
        f"in {elapsed / 60:.1f} min"
    )
    print(f"[output] {out}  ({_hr(out.stat().st_size)})")
    conn.close()


if __name__ == "__main__":
    main()
