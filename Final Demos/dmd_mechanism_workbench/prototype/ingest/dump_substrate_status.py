"""Read data/mechanism.sqlite → write workbench/status.json.

Per-table snapshot: row count, split by data_source, plus static
metadata (what tile the table powers, upstream source, notes). The
status endpoint (workbench/status.html) renders this so you can see at
a glance what's real vs stubbed.

Run:
    python3 -m prototype.ingest.dump_substrate_status
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "mechanism.sqlite"
OUT = REPO / "workbench" / "status.json"

# Static per-table metadata. `powers` names the mechanism.html tile(s)
# that read from the table; `source` is the upstream data provenance.
TABLES = [
    {"name": "lovd_variants",             "powers": "genetic evidence tile · variantsAnalyzed header",
     "source": "LOVD DMD atom feed (databases.lovd.nl)"},
    {"name": "isoforms",                  "powers": "isoform impact tile (labels)",
     "source": "curated from UniProt P11532 + RefSeq NM_004006.2"},
    {"name": "exon_usage",                "powers": "isoform impact tile (per-isoform exon coverage)",
     "source": "curated from Monaco 1988 + UMD-DMD exon phasing map"},
    {"name": "clinvar_phenotype",         "powers": "variant-level phenotype lookup (per-variation records)",
     "source": "NCBI ClinVar variant_summary.txt.gz — DMD gene subset"},
    {"name": "patient_phenotype",         "powers": "per-patient genotype↔phenotype records",
     "source": "Zhang et al. 2024 (Orphanet J Rare Dis, PMC11344408) supp S1+S2 — CC-BY"},
    {"name": "patient_labs",              "powers": "clinical labs tile · per-hypothesis patient evidence",
     "source": "synthetic_v1 — deterministic per patient (bake_synthetic_labs.py); "
               "correlated with phenotype × age × variant position; refs Birnkrant 2018, Ricotti 2016, Pillers 1993"},
    {"name": "phenotype_summary",         "powers": "phenotype distribution tile · phenotyped header",
     "source": "Zhang et al. 2024 cohort counts (N=2,097 patients)"},
    {"name": "celltype_expression",       "powers": "cell types tile",
     "source": "Human Protein Atlas — 'RNA single cell type specific nCPM' (CC-BY-SA)"},
    {"name": "pathway_enrichment",        "powers": "pathways tile",
     "source": "Reactome human pathways GMT — DMD memberships, specificity-scored"},
    {"name": "hypotheses",                "powers": "hypotheses table",
     "source": "curated seed set (4 mechanisms)"},
    {"name": "hypothesis_evidence",       "powers": "hypothesis detail card · evidence bullets",
     "source": "curated with paper citations"},
    {"name": "hypothesis_chain_nodes",    "powers": "hypothesis detail card · reasoning chain nodes",
     "source": "curated"},
    {"name": "hypothesis_chain_edges",    "powers": "hypothesis detail card · reasoning chain edges",
     "source": "curated"},
    {"name": "hypothesis_chain_edge_evidence", "powers": "edge evidence bar (click an arrow in the reasoning chain)",
     "source": "curated with paper citations"},
    {"name": "hypothesis_therapeutic_node","powers": "hypothesis detail card · therapeutic node",
     "source": "curated"},
    {"name": "gene_meta",                 "powers": "header (gene symbol, isoform list, exon count)",
     "source": "curated from UniProt + Ensembl"},
    {"name": "settings",                  "powers": "header · mechanismConfidence",
     "source": "curated placeholder (score_mechanism_confidence.py pending)"},
    # ── World-model registry (Phase 1a) ──────────────────────────────────
    {"name": "premise_source",            "powers": "world-model premise registry · source metadata",
     "source": "curated (Zhang, ClinVar-NMD, HPA, Reactome, isoform arch, synthetic labs, ESM3)"},
    {"name": "premise",                   "powers": "world-model input premises (cohort + patient + variant scope)",
     "source": "populated by bake_hypotheses_and_premises.py from existing baked substrate"},
    {"name": "patient_hypothesis",        "powers": "per-patient stored hypotheses (≥3 per variant) with generator provenance",
     "source": "HYP-MODEL v0-scored — will be replaced by real world-model generator in later phases"},
    {"name": "hypothesis_premise",        "powers": "audit trail: which premises supported which hypothesis (weighted)",
     "source": "computed by the same bake step; joins premise ↔ patient_hypothesis"},
    {"name": "patient_therapeutic",       "powers": "per-hypothesis AAV design candidates with modality + eligibility",
     "source": "AAV-MODEL v0-curated — placeholder for the AAV design world model"},
]


def has_column(conn, table: str, col: str) -> bool:
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})"))


def collect(conn) -> list[dict]:
    out = []
    for t in TABLES:
        name = t["name"]
        n = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        if has_column(conn, name, "data_source"):
            by_src = dict(conn.execute(
                f"SELECT data_source, COUNT(*) FROM {name} GROUP BY data_source"
            ).fetchall())
        else:
            by_src = {"curated": n}
        out.append({
            **t,
            "rows": n,
            "by_source": by_src,
            "is_stub": t["source"].startswith("STUB"),
        })
    return out


def main() -> None:
    conn = sqlite3.connect(DB)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "db_path": str(DB.relative_to(REPO)),
        "db_size_mb": round(DB.stat().st_size / (1024 * 1024), 2),
        "tables": collect(conn),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"[wrote] {OUT} ({OUT.stat().st_size} B, {len(payload['tables'])} tables)")
    conn.close()


if __name__ == "__main__":
    main()
