"""Populate the premise registry + patient-scoped hypotheses/therapeutics.

Phase 1a of the world-model refactor:
- Register each data source / model as a `premise_source`
- Emit `premise` rows from existing baked substrate (labs, isoforms, HPA,
  Reactome, ClinVar NMD, ESM3 folds, Zhang cohort)
- Generate ≥3 (up to 4) `patient_hypothesis` rows per patient, each with
  a stored rationale + a `hypothesis_premise` audit trail
- Generate `patient_therapeutic` rows per top-ranked hypothesis
  (currently curated from the existing therapy nodes; will be replaced
  by a real AAV design model in later phases)

Migration-safe: creates tables if missing, idempotent (wipes prior rows
with matching generator_id before insert).

Run:
    python3 -m prototype.ingest.bake_hypotheses_and_premises
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "mechanism.sqlite"

HYP_GENERATOR = ("HYP-MODEL", "v0-scored-2026-08")
AAV_GENERATOR = ("AAV-MODEL", "v0-curated-2026-08")
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

# Migration DDL — safe to re-run on an already-built DB.
SCHEMA_MIGRATION = """
CREATE TABLE IF NOT EXISTS premise_source (
  source_id     TEXT PRIMARY KEY,
  source_type   TEXT NOT NULL,
  version       TEXT,
  description   TEXT,
  reference_url TEXT
);

CREATE TABLE IF NOT EXISTS premise (
  premise_id    TEXT PRIMARY KEY,
  source_id     TEXT NOT NULL,
  scope         TEXT NOT NULL,
  scope_key     TEXT NOT NULL,
  evidence      TEXT NOT NULL,
  confidence    REAL,
  provenance    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_premise_scope  ON premise(scope, scope_key);
CREATE INDEX IF NOT EXISTS ix_premise_source ON premise(source_id);

CREATE TABLE IF NOT EXISTS patient_hypothesis (
  hypothesis_id      TEXT PRIMARY KEY,
  patient_id         TEXT NOT NULL,
  variant_key        TEXT NOT NULL,
  mechanism_template TEXT,
  rank               INTEGER NOT NULL,
  score              REAL NOT NULL,
  confidence         REAL NOT NULL,
  claim              TEXT NOT NULL,
  rationale          TEXT NOT NULL,
  score_vector       TEXT,
  generator_id       TEXT NOT NULL,
  generator_version  TEXT NOT NULL,
  generated_at       TEXT NOT NULL,
  input_context_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ph_patient ON patient_hypothesis(patient_id, rank);
CREATE INDEX IF NOT EXISTS ix_ph_variant ON patient_hypothesis(variant_key);

CREATE TABLE IF NOT EXISTS hypothesis_premise (
  hypothesis_id TEXT NOT NULL,
  premise_id    TEXT NOT NULL,
  weight        REAL NOT NULL,
  rationale     TEXT,
  PRIMARY KEY (hypothesis_id, premise_id)
);

CREATE TABLE IF NOT EXISTS hypothesis_chain_link (
  hypothesis_id TEXT NOT NULL,
  link_type     TEXT NOT NULL,       -- 'node' | 'edge'
  layer_from    TEXT NOT NULL,
  layer_to      TEXT NOT NULL,
  premise_id    TEXT NOT NULL,
  weight        REAL NOT NULL,
  rationale     TEXT,
  PRIMARY KEY (hypothesis_id, link_type, layer_from, layer_to, premise_id)
);
CREATE INDEX IF NOT EXISTS ix_hcl_hyp   ON hypothesis_chain_link(hypothesis_id);
CREATE INDEX IF NOT EXISTS ix_hcl_layer ON hypothesis_chain_link(layer_from, layer_to);

CREATE TABLE IF NOT EXISTS patient_therapeutic (
  therapeutic_id     TEXT PRIMARY KEY,
  patient_id         TEXT NOT NULL,
  hypothesis_id      TEXT NOT NULL,
  rank               INTEGER NOT NULL,
  score              REAL NOT NULL,
  confidence         REAL NOT NULL,
  modality           TEXT NOT NULL,
  design             TEXT NOT NULL,
  rationale          TEXT NOT NULL,
  eligibility_status TEXT,
  generator_id       TEXT NOT NULL,
  generator_version  TEXT NOT NULL,
  generated_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pt_patient ON patient_therapeutic(patient_id, rank);
CREATE INDEX IF NOT EXISTS ix_pt_hyp     ON patient_therapeutic(hypothesis_id);
"""

# The 10-patient roster (mirrors hydrate_patient_view.ROSTER).
ROSTER_KEYS = [
    ("S1_novel",    "2"),
    ("S1_novel",    "30"),
    ("S2_reported", "258"),
    ("S1_novel",    "57"),
    ("S1_novel",    "5"),
    ("S1_novel",    "11"),
    ("S2_reported", "202"),
    ("S2_reported", "225"),
    ("S1_novel",    "49"),
    ("S2_reported", "266"),
]
# Display labels — mirrors patient_data.json patient ids (P1..P10).
ROSTER_LABELS = {key: f"P{i}" for i, key in enumerate(ROSTER_KEYS, start=1)}

# The four canonical mechanism templates (kept in mechanism.sqlite.hypotheses).
HYP_TEMPLATES = [
    ("01", "Out-of-frame deletions → truncated dystrophin → sarcolemmal fragility"),
    ("02", "In-frame deletions → partial-function dystrophin → BMD phenotype"),
    ("03", "Nonsense / splice variants → NMD → tissue-graded transcript loss"),
    ("04", "Distal-promoter variants → tissue-specific isoform loss (Dp140/Dp71)"),
]


# ----------------------------------------------------------------------
# Premise source registry
# ----------------------------------------------------------------------
PREMISE_SOURCES = [
    ("zhang_2024",           "data",  "supp S1+S2 (2024)",  "Per-patient genotype/phenotype records (Zhang et al. 2024, PMC11344408)", "https://pmc.ncbi.nlm.nih.gov/articles/PMC11344408/"),
    ("clinvar_nmd",          "model", "aenmd-rule v1",      "NMD prediction (PTC ≥50nt upstream of last EEJ) applied to ClinVar DMD variants", None),
    ("hpa_expression",       "data",  "HPA 2024",           "Human Protein Atlas single cell type specific nCPM", "https://www.proteinatlas.org/"),
    ("reactome",             "data",  "Reactome v96",       "Reactome DMD pathway memberships + specificity scoring", "https://reactome.org/"),
    ("isoform_arch",         "data",  "UniProt+RefSeq",     "DMD isoform architecture (first-shared-exon per isoform)", "https://www.uniprot.org/uniprotkb/P11532"),
    ("synthetic_labs",       "model", "synthetic_v1",       "Per-patient synthetic clinical labs (Birnkrant 2018 ranges)", None),
    ("esm3",                 "model", "esm3-open-2024-03",  "ESM3 protein fold + InterPro function annotation", "https://forge.evolutionaryscale.ai/"),
    # A: composition premises — close the variant→cellType and cellType→tissue chain gap
    ("patient_celltype_impact", "model", "compose_v1",      "Per-patient cell-type impact: isoform_arch × curated cell-to-isoform dependency map (Muntoni 2003, Pillers 1993, Lidov 1995)", None),
    ("patient_tissue_impact",   "model", "compose_v1",      "Per-patient tissue impact: composes cell-type impact × isoforms.primary_expression_tissues", None),
    # B: literature as first-class premise (migrated from hypothesis_chain_edge_evidence)
    ("literature",              "data",  "curated_2026-08", "Peer-reviewed citations anchoring specific chain-edge and chain-node claims (Monaco 1988, Popp & Maquat 2013, Ervasti & Campbell 1993, Pillers 1993, ...)", None),
    ("uniprot_subcellular",     "data",  "UniProt REST",    "UniProt-curated subcellular localization (sarcolemma, cytoskeleton, postsynaptic membrane for DMD P11532)", "https://www.uniprot.org/uniprotkb/P11532"),
    ("absplice",                "model", "absplice_v1.0.4", "AbSplice-DNA per-tissue aberrant-splicing probability (Wagner et al. Nat Genet 2023). Distinguishes canonical splice-site variants from exonic ones — flags cryptic-splice risk that isoform_arch and clinvar_nmd cannot see.", "https://github.com/gagneurlab/absplice"),
    ("open_targets",            "data",  "opentargets_25.06", "Open Targets Platform target record for DMD (ENSG00000198947): approved-drug list, DGC molecular interactors, tractability profile, top disease associations, Reactome pathway memberships.", "https://platform.opentargets.org/target/ENSG00000198947"),
    ("nmd_prediction",          "model", "50nt-rule v1",     "Per-patient NMD prediction: applies the 50-nt rule (Popp & Maquat 2013) to this patient's PTC using DMD exon coordinates from ENST00000357033 (79 exons; last EEJ at c.11039, aa 3680).", "https://pubmed.ncbi.nlm.nih.gov/23849625/"),
    ("exon_skip_viability",     "model", "asos_2026-08",     "Per-patient exon-skip therapeutic viability: checks the patient's variant exon against FDA-approved skips (exon 45 casimersen, exon 51 eteplirsen, exon 53 golodirsen/viltolarsen) + Aartsma-Rus reading-frame rule.", "https://www.pmda.go.jp/"),
    ("dgc_completeness",        "model", "hpa-derived v1",   "Per-patient DGC-completeness score per affected cell type: fraction of 14 DGC members (DMD DAG1 SNTA1 SNTB1 SNTB2 SGCA SGCB SGCD SGCG DTNA DTNB UTRN CAV3 SSPN) co-expressed in that cell type — quantifies how much of the assembly this variant abolishes.", None),
    ("domain_annotation",       "data",  "UniProt+lit v1",   "DMD (P11532) 4-domain architecture with per-domain functional literature: N-term actin-binding (Way 1992, Rybakova 2000), spectrin rod (Winder 1997, Rybakova 1996), cysteine-rich β-DG-binding (Suzuki 1994, Rentschler 1999), C-terminal syntrophin/dystrobrevin-binding (Ahn & Kunkel 1995, Peters 1997).", "https://www.uniprot.org/uniprotkb/P11532"),
]

# DGC assembly members — used by dgc_completeness scoring. 14 canonical
# partners including dystrophin itself, utrophin (paralog), the four
# sarcoglycans (A/B/D/G), sarcospan (SSPN), two syntrophins (A/B1),
# additional syntrophin (B2), two dystrobrevins (A/B), dystroglycan
# (DAG1), and caveolin-3 (CAV3) as a myofiber-membrane partner.
DGC_MEMBERS = ("DMD", "DAG1", "SNTA1", "SNTB1", "SNTB2",
               "SGCA", "SGCB", "SGCD", "SGCG",
               "DTNA", "DTNB", "UTRN", "CAV3", "SSPN")

# DMD (P11532) domain architecture — aa ranges per UniProt + Winder 1997.
# Cysteine-rich (β-DG binding) + C-terminal (syntrophin/dystrobrevin
# binding) are the DGC-anchoring domains — loss of either abolishes
# sarcolemmal DGC assembly. Full-length canonical = 3,685 aa (Dp427m).
DMD_DOMAINS = [
    {"id": "ntd",  "name": "N-terminal actin-binding",
     "aa_start": 1,    "aa_end": 240,
     "function": "F-actin binding (CH1+CH2 tandem calponin homology domains); anchors dystrophin to the sub-sarcolemmal cytoskeleton.",
     "citations": ["Way 1992", "Rybakova 2000"]},
    {"id": "rod",  "name": "Spectrin-like rod",
     "aa_start": 241, "aa_end": 3080,
     "function": "24 spectrin-like triple-helical repeats separated by 4 hinge regions; elastic mechanical link between actin and the DGC. Deletions in-frame in this region often produce BMD.",
     "citations": ["Winder 1997", "Rybakova 1996", "Koenig 1988"]},
    {"id": "cys",  "name": "Cysteine-rich (β-DG binding)",
     "aa_start": 3081, "aa_end": 3360,
     "function": "WW + EF-hand + ZZ zinc-finger motifs bind the cytoplasmic tail of β-dystroglycan — the direct sarcolemmal anchor for the entire DGC. Loss abolishes DGC assembly.",
     "citations": ["Suzuki 1994", "Rentschler 1999", "Huang 2000"]},
    {"id": "ctd",  "name": "C-terminal (syntrophin/dystrobrevin)",
     "aa_start": 3361, "aa_end": 3685,
     "function": "Coiled-coil scaffolding domain that recruits syntrophins (α, β1, β2) and dystrobrevins (α, β) — links nNOS + signalling adapters to the sarcolemmal DGC.",
     "citations": ["Ahn & Kunkel 1995", "Peters 1997", "Sadoulet-Puccio 1997"]},
]

# NMD 50-nt rule constants (Popp & Maquat 2013). Applied against ENST00000357033.
DMD_LAST_EEJ_CDNA_POS = 11039        # exon 78/79 boundary (c.11039)
NMD_ESCAPE_UPSTREAM_NT = 50          # PTC within 50 nt upstream of last EEJ → escape
DMD_NMD_ESCAPE_CDNA_THRESHOLD = DMD_LAST_EEJ_CDNA_POS - NMD_ESCAPE_UPSTREAM_NT  # c.10989

# FDA-approved DMD exon-skipping ASOs (as of 2026-08). Each key is the
# targeted exon; value is the approved drug label.
FDA_APPROVED_SKIPS = {
    45: "casimersen (AMONDYS 45, approved 2021)",
    51: "eteplirsen (EXONDYS 51, approved 2016)",
    53: "golodirsen (VYONDYS 53, 2019) / viltolarsen (VILTEPSO, 2020)",
}

# Cell-type → required-isoform dependency map (mirrors hydrate_patient_view.CELL_TO_ISOFORMS).
CELL_TO_ISOFORMS: dict[str, list[str]] = {
    "Myonuclei":                    ["Dp427m"],
    "Cardiomyocytes":               ["Dp427m"],
    "Thymic myoid cells":           ["Dp427m"],
    "Salivary myoepithelial cells": ["Dp427m"],
    "Rod photoreceptor cells":      ["Dp260", "Dp71"],
    "Cone photoreceptor cells":     ["Dp260", "Dp71"],
    "Adipocytes":                   ["Dp71"],
}

# Tissue tractability by AAV / oligonucleotide delivery success.
# These are surrogate priors, not measured efficacy — grounded in the
# approved therapies currently in market (AAV9 systemic → skeletal
# muscle; subretinal AAV for RPE65; nusinersen intrathecal for infant
# SMA), and the well-known delivery-failure tissues (adult CNS, kidney,
# adipose). Used by the treatability axis of the Pareto ranking.
TISSUE_TRACTABILITY: dict[str, float] = {
    "Muscle_Skeletal":      0.95,  # delandistrogene AAV9 approved
    "Heart_Left_Ventricle": 0.75,  # cardiac AAV works but harder to dose
    "Retina":               0.90,  # subretinal AAV (voretigene precedent)
    "CNS_young":            0.60,  # infant intrathecal delivery is real
    "CNS_adult":            0.35,  # blood-brain barrier stays hard
    "Kidney":               0.35,  # AAV kidney tropism is poor
    "Adipose":              0.15,  # essentially no clinical delivery
    "Salivary":             0.05,
    "Thymus":               0.20,
    "Peripheral_nerve":     0.40,
}

# Target-tissue weightings per mechanism template. Sums to 1.0 per
# template. Used to fold TISSUE_TRACTABILITY into a per-hypothesis
# treatability score.
TEMPLATE_TARGET_TISSUES: dict[str, dict[str, float]] = {
    "01": {"Muscle_Skeletal": 0.60, "Heart_Left_Ventricle": 0.40},
    "02": {"Muscle_Skeletal": 0.85, "Heart_Left_Ventricle": 0.15},
    "03": {"Muscle_Skeletal": 0.60, "Heart_Left_Ventricle": 0.40},
    "04": {"Retina": 0.35, "CNS_young": 0.30, "Kidney": 0.20, "Adipose": 0.15},
}

# Baseline severity per phenotype class. DMD ~ life-limiting by 20s;
# BMD ~ ambulatory into adulthood; IMD in between; DCM = cardiac
# variant. Multiplied by a per-template severity factor below.
PHENOTYPE_SEVERITY: dict[str, float] = {
    "DMD":   0.90,
    "IMD":   0.75,
    "BMD":   0.50,
    "DCM":   0.65,
    "other": 0.40,
}

# Per-mechanism severity multiplier: complete-loss mechanisms (H01/H03)
# imply the worst prognosis; H02 (partial-function BMD) is milder; H04
# (distal-isoform) adds CNS/renal/retinal on top of skeletal but is
# usually cognitive/subclinical severity in isolation.
TEMPLATE_SEVERITY: dict[str, float] = {
    "01": 1.00,   # sarcolemmal fragility: full DMD trajectory
    "02": 0.60,   # partial-function BMD scenario
    "03": 1.00,   # NMD-driven complete loss
    "04": 0.70,   # distal-isoform loss: cognitive/renal comorbid
}


# Node → biological-layer mapping per curated hypothesis chain
# (hypothesis_chain_nodes uses v1/v2/v3, m1/m2/m3, p1/p2/p3 node IDs;
# this table maps each to its position in the seven-layer hierarchy).
CHAIN_NODE_TO_LAYER: dict[str, dict[str, str]] = {
    '01': {
        'v1': 'variant', 'v2': 'variant', 'v3': 'protein',
        'm1': 'subcellular', 'm2': 'pathway', 'm3': 'subcellular',
        'p1': 'cellType', 'p2': 'cellType', 'p3': 'tissue',
    },
    '02': {
        'v1': 'variant', 'v2': 'protein', 'v3': 'protein',
        'm1': 'subcellular', 'm2': 'subcellular', 'm3': 'pathway',
        'p1': 'cellType', 'p2': 'phenotype', 'p3': 'phenotype',
    },
    '03': {
        'v1': 'variant', 'v2': 'variant', 'v3': 'protein',
        'm1': 'subcellular', 'm2': 'cellType', 'm3': 'cellType',
        'p1': 'cellType', 'p2': 'phenotype', 'p3': 'phenotype',
    },
    '04': {
        'v1': 'variant', 'v2': 'protein', 'v3': 'protein',
        'm1': 'cellType', 'm2': 'cellType', 'm3': 'cellType',
        'p1': 'phenotype', 'p2': 'phenotype', 'p3': 'phenotype',
    },
}


def _slug(s: str) -> str:
    """Sanitize a citation string into a stable slug."""
    return re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_').lower()


def register_sources(conn):
    conn.execute("DELETE FROM premise_source")
    for row in PREMISE_SOURCES:
        conn.execute("INSERT INTO premise_source VALUES (?,?,?,?,?)", row)


# ----------------------------------------------------------------------
# Premise emission helpers
# ----------------------------------------------------------------------
def _pid(*parts: str) -> str:
    """Stable ID from parts."""
    return "|".join(str(p) for p in parts)


def _hash(*parts: str) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def _prov(cache_path: str | None = None) -> str:
    return json.dumps({"fetched_at": NOW, "cache": cache_path})


def emit_zhang_premise(conn, cohort: str, pid: str, phen: str, exon: str,
                        consequence: str, aa_change: str | None, acmg: str | None) -> str:
    premise_id = _pid("zhang", cohort, pid)
    ev = {
        "cohort": cohort, "patient_id": pid, "phenotype": phen,
        "exon": exon, "consequence": consequence, "aa_change": aa_change, "acmg": acmg,
    }
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "zhang_2024", "patient", pid, json.dumps(ev), 1.0, _prov()),
    )
    return premise_id


def emit_lab_premises(conn, cohort: str, pid: str) -> list[str]:
    """Emit one premise per abnormal lab for this patient."""
    ids = []
    rows = conn.execute(
        "SELECT assay_key, label, layer, tissue, value, ref_low, ref_high, flag, unit "
        "FROM patient_labs WHERE cohort=? AND patient_id=? AND flag != 'normal'",
        (cohort, pid),
    ).fetchall()
    for (key, label, layer, tissue, value, ref_lo, ref_hi, flag, unit) in rows:
        premise_id = _pid("labs", cohort, pid, key)
        fold = (value / ref_hi) if (flag == "high" and ref_hi > 0) else \
               (ref_lo / value) if (flag == "low" and value > 0) else 1.0
        ev = {"assay": key, "label": label, "layer": layer, "tissue": tissue,
              "value": value, "unit": unit, "flag": flag,
              "ref_low": ref_lo, "ref_high": ref_hi, "fold": round(fold, 2)}
        conn.execute(
            "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
            (premise_id, "synthetic_labs", "patient", pid, json.dumps(ev), 0.85, _prov()),
        )
        ids.append(premise_id)
    return ids


def emit_isoform_premise(conn, cohort: str, pid: str, exon_n: int | None) -> str:
    """Per-patient isoform-impact projection (which isoforms are hit)."""
    if exon_n is None: return ""
    hit = []; spared = []
    for iso in conn.execute(
        "SELECT isoform_id, first_shared_exon FROM isoforms ORDER BY rank"
    ):
        (hit if iso[1] <= exon_n else spared).append(iso[0])
    ev = {"variant_exon": exon_n, "hit_isoforms": hit, "spared_isoforms": spared}
    premise_id = _pid("iso_arch", cohort, pid)
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "isoform_arch", "patient", pid, json.dumps(ev), 0.9, _prov()),
    )
    return premise_id


def emit_hpa_premise(conn) -> str:
    """One cohort-scope premise: DMD expression by HPA cell type."""
    rows = conn.execute(
        "SELECT cell_type, score, tissue FROM celltype_expression "
        "WHERE gene_symbol='DMD' ORDER BY score DESC LIMIT 7"
    ).fetchall()
    ev = {"cell_types": [{"name": r[0], "score": r[1], "tissue": r[2]} for r in rows]}
    premise_id = _pid("hpa", "DMD")
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "hpa_expression", "cohort", "DMD", json.dumps(ev), 0.95, _prov()),
    )
    return premise_id


def emit_reactome_premise(conn) -> str:
    rows = conn.execute(
        "SELECT pathway_name, score FROM pathway_enrichment "
        "WHERE gene_symbol='DMD' ORDER BY score DESC LIMIT 5"
    ).fetchall()
    ev = {"pathways": [{"name": r[0], "specificity": r[1]} for r in rows]}
    premise_id = _pid("reactome", "DMD")
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "reactome", "cohort", "DMD", json.dumps(ev), 0.9, _prov()),
    )
    return premise_id


def emit_opentargets_premise(conn) -> str | None:
    """Cohort-scope premise summarizing the Open Targets DMD record.

    Reads the six `opentargets_dmd_*` tables baked by
    `prototype.ingest.bake_opentargets`. Returns None if the tables are
    empty (fresh clones may not have run the fetch yet)."""
    have = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='opentargets_dmd_summary'"
    ).fetchone()
    if not have:
        return None
    summ = conn.execute("SELECT * FROM opentargets_dmd_summary").fetchone()
    if not summ:
        return None
    (ensembl_id, symbol, name, biotype, refreshed_at, source_url) = summ

    # Tractable modalities: only where value=1. Group by modality
    # (SM=small-molecule, AB=antibody, PR=PROTAC, OC=other clinical).
    tract_by_mod: dict[str, list[str]] = {}
    for mod, label, val in conn.execute(
        "SELECT modality, label, value FROM opentargets_dmd_tractability"
    ):
        if val:
            tract_by_mod.setdefault(mod, []).append(label)

    pathways = [
        {"id": pid, "name": pname, "top_level": tlt}
        for pid, pname, tlt in conn.execute(
            "SELECT pathway_id, pathway, top_level_term "
            "FROM opentargets_dmd_pathway"
        )
    ]

    top_diseases = [
        {"id": did, "name": dname, "score": round(sc, 3)}
        for did, dname, sc in conn.execute(
            "SELECT disease_id, disease_name, score "
            "FROM opentargets_dmd_disease ORDER BY score DESC LIMIT 8"
        )
    ]

    drugs = [
        {"id": did, "name": dname, "type": dtype,
         "max_stage": mcs, "drug_max_stage": dms}
        for did, dname, dtype, mcs, dms in conn.execute(
            "SELECT drug_id, drug_name, drug_type, max_clinical_stage, "
            "       drug_max_stage FROM opentargets_dmd_drug"
        )
    ]
    approved = [d for d in drugs if (d["max_stage"] or "").upper() == "APPROVAL"]

    interactions = [
        {"partner_id": pid, "symbol": sym, "score": round(sc, 3),
         "source": src}
        for pid, sym, sc, src in conn.execute(
            "SELECT partner_id, partner_symbol, score, source_database "
            "FROM opentargets_dmd_interaction "
            "WHERE partner_symbol IS NOT NULL "
            "ORDER BY score DESC LIMIT 12"
        )
    ]

    ev = {
        "ensembl_id":     ensembl_id,
        "symbol":         symbol,
        "name":           name,
        "biotype":        biotype,
        "refreshed_at":   refreshed_at,
        "tractability":   tract_by_mod,
        "pathways":       pathways,
        "top_diseases":   top_diseases,
        "drugs":          drugs,
        "approved_drugs": approved,
        "interactions":   interactions,
    }

    premise_id = _pid("opentargets", "DMD")
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "open_targets", "cohort", "DMD",
         json.dumps(ev), 0.9, _prov(source_url)),
    )
    return premise_id


def emit_uniprot_subcellular_premise(conn, uniprot_id: str = "P11532") -> str:
    """Fetch UniProt subcellular annotations and emit as a cohort-scope
    premise for the subcellular node. Result is cached under
    data/raw/uniprot_{id}_subcellular.json — subsequent runs skip the fetch.
    Fills the subcellular chain-node gap with curated protein-biology data."""
    cache = REPO / "data" / "raw" / f"uniprot_{uniprot_id}_subcellular.json"
    if cache.exists() and cache.stat().st_size > 100:
        d = json.loads(cache.read_text())
    else:
        import urllib.request
        cache.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read())
        cache.write_text(json.dumps(d, indent=2))

    # Extract subcellular location comments
    locations = []
    notes = []
    for comment in d.get("comments", []):
        if comment.get("commentType") != "SUBCELLULAR LOCATION":
            continue
        for loc_entry in comment.get("subcellularLocations", []):
            loc = loc_entry.get("location", {}).get("value")
            topology = loc_entry.get("topology", {}).get("value", "")
            if loc:
                locations.append({"location": loc, "topology": topology})
        for note in comment.get("note", {}).get("texts", []):
            if note.get("value"):
                notes.append(note["value"])

    ev = {
        "uniprot_id": uniprot_id,
        "locations":  locations,
        "notes":      notes[:3],
        "gene":       "DMD",
    }
    premise_id = _pid("uniprot_subcellular", "DMD")
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "uniprot_subcellular", "cohort", "DMD",
         json.dumps(ev), 0.95, _prov(str(cache.relative_to(REPO)))),
    )
    return premise_id


# Module-level cache of the curated AbSplice TSV keyed on variant_key.
_ABSPLICE_TSV = REPO / "data" / "variants" / "absplice_dmd_variants.tsv"
_ABSPLICE_CACHE: dict[str, dict] | None = None


def _load_absplice_table() -> dict[str, dict]:
    global _ABSPLICE_CACHE
    if _ABSPLICE_CACHE is not None:
        return _ABSPLICE_CACHE
    rows: dict[str, dict] = {}
    if not _ABSPLICE_TSV.exists():
        _ABSPLICE_CACHE = rows
        return rows
    with _ABSPLICE_TSV.open() as f:
        header: list[str] | None = None
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                continue
            r = dict(zip(header, parts))
            for k in ("muscle_skeletal", "heart_lv", "brain_cortex", "retina_proxy", "max_score"):
                if k in r and r[k] != "":
                    try: r[k] = float(r[k])
                    except ValueError: pass
            rows[r["variant_key"]] = r
    _ABSPLICE_CACHE = rows
    return rows


def emit_absplice_premise(conn, cohort: str, pid: str, variant_key: str) -> str | None:
    """Patient-scope AbSplice premise: per-tissue aberrant-splicing probability.

    Distinguishes canonical splice-site variants (top score ~0.85) from
    exonic ones (~0.02) — a signal isoform_arch and clinvar_nmd don't see.
    Skips patients whose variant isn't in the curated table."""
    table = _load_absplice_table()
    row = table.get(variant_key)
    if not row: return None
    ev = {
        "variant_key":      variant_key,
        "hgvsc":            row.get("hgvsc"),
        "category":         row.get("category"),
        "tissue_scores": {
            "Muscle_Skeletal":      row.get("muscle_skeletal"),
            "Heart_Left_Ventricle": row.get("heart_lv"),
            "Brain_Cortex":         row.get("brain_cortex"),
            "Retina_proxy":         row.get("retina_proxy"),
        },
        "max_score":        row.get("max_score"),
        "max_tissue":       row.get("max_tissue"),
        "notes":            row.get("notes"),
        "confidence":       row.get("confidence"),
        "compute":          "off-box (AbSplice v1.0.4 estimates pending)",
    }
    # Baseline confidence lower when scores are estimates rather than an
    # actual model run.
    conf = 0.55 if row.get("confidence") == "estimated" else 0.85
    premise_id = _pid("absplice", cohort, pid)
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "absplice", "patient", pid, json.dumps(ev), conf,
         _prov(str(_ABSPLICE_TSV.relative_to(REPO)))),
    )
    return premise_id


def emit_nmd_cohort_premise(conn) -> str:
    """Cohort-scope NMD × ACMG cross-tab (built at hydration time; here
    we materialize it as a premise so hypothesis rationales can cite it)."""
    # Grid from the hydrator's build_nmd_cohort — replicate the summary here
    # for storage. We just re-count from clinvar_phenotype.
    from prototype.ingest.hydrate_mechanism_view import build_nmd_cohort
    ev = build_nmd_cohort(conn)
    premise_id = _pid("nmd_cohort", "DMD")
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "clinvar_nmd", "cohort", "DMD", json.dumps(ev), 0.9, _prov()),
    )
    return premise_id


def emit_celltype_impact_premise(conn, cohort: str, pid: str, exon_n: int | None) -> str | None:
    """Composition premise: for each HPA cell type, is it hit / partial /
    spared given the variant's isoform-hit pattern + the curated cell-to-
    isoform dependency map. Closes the variant→cellType chain gap that
    HPA (gene-scoped) and isoform_arch (ends at protein) together leave open."""
    if exon_n is None: return None
    iso_hit = {r[0]: r[1] <= exon_n
               for r in conn.execute(
                   "SELECT isoform_id, first_shared_exon FROM isoforms")}
    cells = []
    for (name, tissue) in conn.execute(
        "SELECT cell_type, tissue FROM celltype_expression "
        "WHERE gene_symbol='DMD' ORDER BY score DESC"):
        req = CELL_TO_ISOFORMS.get(name, [])
        if not req:
            status, hit_isos, spared_isos = "unknown", [], []
        else:
            hit_isos    = [i for i in req if iso_hit.get(i, True)]
            spared_isos = [i for i in req if not iso_hit.get(i, True)]
            status = "hit" if len(hit_isos) == len(req) \
                     else "spared" if not hit_isos \
                     else "partial"
        cells.append({"name": name, "tissue": tissue, "status": status,
                      "hit_isoforms": hit_isos, "spared_isoforms": spared_isos})
    ev = {"variant_exon": exon_n, "cells": cells,
          "curation": "Muntoni 2003, Pillers 1993, Lidov 1995"}
    pid_ = _pid("celltype_impact", cohort, pid)
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (pid_, "patient_celltype_impact", "patient", pid, json.dumps(ev), 0.85, _prov()),
    )
    return pid_


def emit_tissue_impact_premise(conn, cohort: str, pid: str, exon_n: int | None) -> str | None:
    """Composition premise: tissues hit / spared for this patient, derived
    from which isoforms are hit × each isoform's primary_expression_tissues."""
    if exon_n is None: return None
    iso_hit = {r[0]: r[1] <= exon_n
               for r in conn.execute(
                   "SELECT isoform_id, first_shared_exon FROM isoforms")}
    hit_tissues, all_tissues = set(), set()
    for (iso_id, tissues_str) in conn.execute(
        "SELECT isoform_id, primary_expression_tissues FROM isoforms"):
        tissues = [t.strip() for t in (tissues_str or "").split(";") if t.strip()]
        for t in tissues:
            all_tissues.add(t)
            if iso_hit.get(iso_id, True):
                hit_tissues.add(t)
    spared_tissues = all_tissues - hit_tissues
    ev = {"variant_exon": exon_n,
          "tissues_hit":    sorted(hit_tissues),
          "tissues_spared": sorted(spared_tissues)}
    pid_ = _pid("tissue_impact", cohort, pid)
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (pid_, "patient_tissue_impact", "patient", pid, json.dumps(ev), 0.85, _prov()),
    )
    return pid_


def emit_esm3_premise(conn, cohort: str, pid: str) -> str | None:
    """ESM3 fold premise for patients whose variant we've folded."""
    known = {
        ("S2_reported", "258"): {"isoform": "Dp71", "cache": "P11532_Dp71",
                                  "variant_resi_full": 3083, "variant_label": "Trp3083*"},
        ("S1_novel",    "5"):   {"isoform": "Dp71", "cache": "P11532_Dp71",
                                  "variant_resi_full": 3552, "variant_label": "Ser3552Lysfs*6",
                                  "truncated_cache": "P11532_Dp71_truncP5"},
    }
    k = known.get((cohort, pid))
    if not k: return None
    premise_id = _pid("esm3", cohort, pid)
    ev = dict(k)
    ev["mean_plddt"] = 0.69
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "esm3", "patient", pid, json.dumps(ev), 0.7, _prov(k.get("cache"))),
    )
    return premise_id


# Parse HGVSp → residue index (mirrors bake_esm3_impact.parse_residue).
_HGVSP_RE = re.compile(r"p\.\(?[A-Za-z]{3}(\d+)")


def _residue_from_hgvsp(hgvsp: str | None) -> int | None:
    if not hgvsp: return None
    m = _HGVSP_RE.search(hgvsp)
    return int(m.group(1)) if m else None


def _cdna_pos_from_hgvsc(hgvsc: str | None) -> int | None:
    """First base position from a c.-notation string (e.g., c.6540del → 6540)."""
    if not hgvsc: return None
    m = re.search(r"c\.(\d+)", hgvsc)
    return int(m.group(1)) if m else None


def emit_nmd_prediction_premise(conn, cohort: str, pid: str,
                                 nuc: str | None, aa: str | None,
                                 cons: str | None, exon_n: int | None) -> str | None:
    """Per-patient NMD prediction: apply 50-nt rule to this patient's PTC.

    Cites Popp & Maquat 2013. Emits a premise that carries:
      - patient's PTC residue (from HGVSp) and cDNA position (from HGVSc)
      - the DMD last-EEJ threshold (c.11039 = exon 78/79 boundary)
      - a verdict: 'nmd_triggered' | 'nmd_escape' | 'not_ptc_generating'
      - a rationale explaining the numeric distance

    Splice-site variants without a parseable HGVSp are conservatively
    marked 'nmd_triggered' (they typically generate PTCs downstream).
    Missense variants are marked 'not_ptc_generating'.
    """
    cons_l = (cons or "").lower()
    ptc_generating = any(k in cons_l for k in
                          ("nonsense", "frameshift", "splice", "stop"))
    residue = _residue_from_hgvsp(aa)
    cdna_pos = _cdna_pos_from_hgvsc(nuc)

    if not ptc_generating:
        verdict = "not_ptc_generating"
        rationale = f"variant consequence '{cons_l}' does not create a PTC — NMD rule N/A"
    elif residue is None and "splice" in cons_l:
        # Splice-site variants without HGVSp: presume PTC in a downstream
        # exon → NMD-triggered (conservative default). Real answer needs
        # RNA-seq or minigene.
        verdict = "nmd_triggered"
        rationale = ("splice-site variant; presumed to create a PTC via "
                     "exon skipping or intron retention — NMD-triggered "
                     "(unknown cryptic-splice outcome pending RNA-seq)")
    elif residue is None:
        return None   # Can't classify — skip the premise entirely.
    else:
        # 50-nt rule: PTC ≥50nt upstream of last EEJ (c.11039) → NMD-triggered.
        # Convert aa residue to approximate cDNA position (aa*3 − 2, +5'UTR).
        # DMD CDS starts at c.245 (5'UTR = 244 nt).
        est_cdna = 245 + (residue - 1) * 3 if cdna_pos is None else cdna_pos
        distance_nt = DMD_LAST_EEJ_CDNA_POS - est_cdna
        if est_cdna < DMD_NMD_ESCAPE_CDNA_THRESHOLD:
            verdict = "nmd_triggered"
            rationale = (f"PTC at aa {residue} (~c.{est_cdna}) is "
                         f"{distance_nt} nt upstream of last EEJ "
                         f"(c.{DMD_LAST_EEJ_CDNA_POS}, exon 78/79 boundary) — "
                         f"≥50-nt rule fires → NMD-triggered → mRNA degraded, "
                         f"protein effectively absent")
        else:
            verdict = "nmd_escape"
            rationale = (f"PTC at aa {residue} (~c.{est_cdna}) is only "
                         f"{distance_nt} nt from last EEJ (c.{DMD_LAST_EEJ_CDNA_POS}) — "
                         f"within the 50-nt escape window → NMD-escape → truncated "
                         f"protein produced, C-terminal fragment lost")

    ev = {
        "residue": residue, "cdna_position": cdna_pos,
        "last_eej_cdna": DMD_LAST_EEJ_CDNA_POS,
        "escape_threshold_cdna": DMD_NMD_ESCAPE_CDNA_THRESHOLD,
        "verdict": verdict, "rationale": rationale,
        "citation": "Popp & Maquat 2013 (Nat Rev Genet 14:801-813) — 50-nt rule for NMD",
    }
    premise_id = _pid("nmd_prediction", cohort, pid)
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "nmd_prediction", "patient", pid,
         json.dumps(ev), 0.88, _prov()),
    )
    return premise_id


def emit_exon_skip_viability_premise(conn, cohort: str, pid: str,
                                       exon_n: int | None,
                                       cons: str | None) -> str | None:
    """Per-patient exon-skip therapeutic viability.

    Checks:
      1. Does an FDA-approved skip DIRECTLY target the patient's exon?
         (casimersen skip 45 / eteplirsen skip 51 / golodirsen+viltolarsen skip 53)
      2. Or: does the patient's exon SIT ADJACENT to an approved skip
         that could rescue the reading frame if the pathogenic lesion
         is an out-of-frame deletion? (Aartsma-Rus reading-frame rule
         2006; requires deletion breakpoint info that we don't have
         cohort-wide — flagged as 'requires_deletion_breakpoint').

    Emits {variant_exon, direct_skip_hit, adjacent_skip_candidates,
    verdict, rationale, citations}. Verdict enum:
      'direct_skip_eligible'  — approved drug targets this exon
      'adjacent_skip_candidate' — patient's exon adjacent to approved skip
      'no_approved_skip'      — no coverage
      'not_applicable'        — variant is splice-site or requires structural detail
    """
    if exon_n is None:
        return None

    direct_drug = FDA_APPROVED_SKIPS.get(exon_n)
    adjacent_exons = [e for e in FDA_APPROVED_SKIPS
                       if abs(e - exon_n) == 1]

    if direct_drug:
        verdict = "direct_skip_eligible"
        rationale = (f"Variant lies in exon {exon_n} — directly targeted by "
                     f"{direct_drug}. Skipping this exon rejoins the flanking "
                     f"exons in-frame under the Aartsma-Rus reading-frame rule, "
                     f"restoring a BMD-like truncated dystrophin.")
    elif adjacent_exons:
        adj_str = " / ".join(f"exon {e} ({FDA_APPROVED_SKIPS[e]})" for e in adjacent_exons)
        verdict = "adjacent_skip_candidate"
        rationale = (f"Variant in exon {exon_n} is adjacent to approved skip(s): "
                     f"{adj_str}. If the pathogenic lesion is an out-of-frame "
                     f"deletion spanning into these exons, skipping the neighbour "
                     f"could restore reading frame. Requires deletion-breakpoint "
                     f"validation.")
    else:
        verdict = "no_approved_skip"
        rationale = (f"Variant in exon {exon_n} has no FDA-approved exon-skipping "
                     f"ASO coverage. Approved skips target exons 45, 51, 53 only.")

    ev = {
        "variant_exon": exon_n,
        "direct_drug": direct_drug,
        "adjacent_skip_exons": adjacent_exons,
        "verdict": verdict,
        "rationale": rationale,
        "approved_skips": FDA_APPROVED_SKIPS,
        "citations": ["Aartsma-Rus 2006 (Mol Ther 14:401-407)",
                      "Mendell 2013 (Ann Neurol 74:637-647)",
                      "Frank 2020 (Neurology 94:e2270)"],
    }
    premise_id = _pid("exon_skip", cohort, pid)
    # Confidence: high for direct_skip_eligible (approved indication), medium
    # for adjacent (needs breakpoint), low for no_approved (asserted absence).
    conf = {"direct_skip_eligible": 0.9,
            "adjacent_skip_candidate": 0.5,
            "no_approved_skip": 0.7}.get(verdict, 0.5)
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "exon_skip_viability", "patient", pid,
         json.dumps(ev), conf, _prov()),
    )
    return premise_id


def emit_dgc_completeness_premise(conn, cohort: str, pid: str,
                                    exon_n: int | None) -> str | None:
    """Per-patient DGC-completeness score per affected cell type.

    For each cell type where this patient's variant knocks out DMD
    (via isoform-hit projection), score the fraction of the 14 DGC
    members that are co-expressed in that cell type. A high score means
    losing dystrophin abolishes a nearly-complete assembly (worst case);
    a low score means the DGC was already incomplete without dystrophin,
    so the mechanistic consequence is muted.

    Emits {variant_exon, affected_cells: [{name, tissue, dgc_score,
    dgc_partners_present, dgc_partners_missing}], mean_dgc_completeness,
    interpretation}. Cites HPA-derived scores.
    """
    if exon_n is None:
        return None

    # Reuse the isoform-hit projection to pick the AFFECTED cell types.
    iso_hit = {r[0]: r[1] <= exon_n
               for r in conn.execute(
                   "SELECT isoform_id, first_shared_exon FROM isoforms")}
    affected_cells: list[dict] = []
    # For each cell type in celltype_expression that requires an affected
    # isoform, compute how many DGC partners are also expressed there.
    for (cell_type, tissue) in conn.execute(
        "SELECT DISTINCT cell_type, tissue FROM celltype_expression "
        "WHERE gene_symbol='DMD' ORDER BY cell_type"):
        req = CELL_TO_ISOFORMS.get(cell_type, [])
        if not req: continue
        hit_isos = [i for i in req if iso_hit.get(i, True)]
        if not hit_isos: continue        # cell spared — skip
        # Count DGC partners expressed in this cell type (any score > 0).
        partners_present = [g for g in DGC_MEMBERS if conn.execute(
            "SELECT 1 FROM celltype_expression "
            "WHERE gene_symbol=? AND cell_type=? AND score > 0 LIMIT 1",
            (g, cell_type)).fetchone()]
        partners_missing = [g for g in DGC_MEMBERS if g not in partners_present]
        dgc_score = round(len(partners_present) / len(DGC_MEMBERS), 3)
        affected_cells.append({
            "name": cell_type, "tissue": tissue,
            "dgc_completeness": dgc_score,
            "dgc_partners_present": partners_present,
            "dgc_partners_missing": partners_missing,
            "affected_isoforms": hit_isos,
        })

    if not affected_cells:
        return None

    mean_dgc = round(sum(c["dgc_completeness"] for c in affected_cells)
                     / len(affected_cells), 3)
    top = max(affected_cells, key=lambda c: c["dgc_completeness"])
    interpretation = (f"Across {len(affected_cells)} affected cell type(s), "
                       f"mean DGC-completeness is {mean_dgc:.2f}. Highest impact: "
                       f"{top['name']} ({top['tissue']}) at {top['dgc_completeness']:.2f} "
                       f"— {len(top['dgc_partners_present'])} of {len(DGC_MEMBERS)} DGC "
                       f"partners co-expressed → dystrophin loss abolishes a nearly-"
                       f"complete sarcolemmal assembly.")

    ev = {
        "variant_exon": exon_n,
        "affected_cells": affected_cells,
        "mean_dgc_completeness": mean_dgc,
        "dgc_members": list(DGC_MEMBERS),
        "interpretation": interpretation,
        "data_source": "HPA single-cell RNA (score > 0 threshold)",
    }
    premise_id = _pid("dgc_completeness", cohort, pid)
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "dgc_completeness", "patient", pid,
         json.dumps(ev), 0.75, _prov()),
    )
    return premise_id


def emit_domain_annotation_premise(conn) -> str:
    """Cohort-scope DMD 4-domain architecture with per-domain literature.

    Feeds the protein-viz hover popovers. Static reference data (not
    patient-specific) — same premise attaches to every hypothesis whose
    chain traverses the protein node.
    """
    ev = {
        "uniprot": "P11532",
        "canonical_length_aa": 3685,
        "isoform": "Dp427m",
        "domains": DMD_DOMAINS,
        "dgc_anchoring_domains": ["cys", "ctd"],
        "note": ("Loss of the cysteine-rich (β-DG binding) OR C-terminal "
                 "domain abolishes DGC assembly. Deletions strictly within "
                 "the spectrin rod that maintain reading frame often produce "
                 "BMD (partial function) rather than DMD."),
    }
    premise_id = _pid("domain_annotation", "DMD")
    conn.execute(
        "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
        (premise_id, "domain_annotation", "cohort", "DMD",
         json.dumps(ev), 0.95, _prov()),
    )
    return premise_id


# ----------------------------------------------------------------------
# Literature migration: hypothesis_chain_edge_evidence → literature premises
# ----------------------------------------------------------------------
# Each unique citation becomes one `literature` premise in the registry.
# For each hypothesis that cites the paper, we record: which chain edge
# (mapped to biological-layer edge via CHAIN_NODE_TO_LAYER), the claim
# text, and the tone (good/warn).

def collect_literature_data(conn) -> dict[str, dict]:
    """Return {citation → {premise_id, claims, per_hyp: {template_id: [claim]}}}.
    Each per_hyp claim has {position: (link_type, layer_from, layer_to),
    text, tone}."""
    lit_data: dict[str, dict] = {}
    rows = conn.execute("""
        SELECT hypothesis_id, from_node, to_node, ord, tone, text, citation
        FROM hypothesis_chain_edge_evidence
        ORDER BY citation, hypothesis_id, ord
    """).fetchall()
    for (hid, from_node, to_node, _ord, tone, text, citation) in rows:
        if not citation: continue
        entry = lit_data.setdefault(citation, {
            "premise_id": _pid("lit", _slug(citation)),
            "claims": [],
            "per_hyp": {},
        })
        layers = CHAIN_NODE_TO_LAYER.get(hid, {})
        lf, lt = layers.get(from_node), layers.get(to_node)
        if not lf or not lt:
            continue
        position = ("node", lf, lf) if lf == lt else ("edge", lf, lt)
        entry["claims"].append({"hyp": hid, "text": text, "tone": tone,
                                 "position": list(position)})
        entry["per_hyp"].setdefault(hid, []).append({
            "position": position, "text": text, "tone": tone,
        })
    return lit_data


def emit_literature_premises(conn, lit_data: dict) -> int:
    """Emit one premise per unique citation. Chain-position attribution
    happens per hypothesis at bake time (see literature_links_for_template)."""
    for citation, entry in lit_data.items():
        ev = {
            "citation":         citation,
            "claims":           entry["claims"],
            "n_hyp_citations":  len(entry["per_hyp"]),
        }
        conn.execute(
            "INSERT OR REPLACE INTO premise VALUES (?,?,?,?,?,?,?)",
            (entry["premise_id"], "literature", "cohort", "DMD",
             json.dumps(ev), 0.9, _prov()),
        )
    return len(lit_data)


def literature_links_for_template(lit_data: dict, tmpl_id: str
                                  ) -> list[tuple[str, float, str, tuple[str, str, str]]]:
    """Return (premise_id, weight, rationale, chain_position) for each
    literature citation attributed to this hypothesis template's chain.

    Also produces "dual attribution": when a citation informs an edge
    landing at or emanating from a specific layer (e.g. protein →
    subcellular, cellType → tissue), the same citation is *also*
    attributed to that layer as node evidence — because papers that
    establish a transition typically also establish the biology at
    the layers they connect. This especially matters for the
    subcellular node, which otherwise has only UniProt data."""
    out = []
    NODE_DUAL_ATTRIBUTION = {"subcellular"}  # extendable to other node gaps
    for citation, entry in lit_data.items():
        for claim in entry["per_hyp"].get(tmpl_id, []):
            weight = 0.5 if claim["tone"] == "good" else -0.3
            text = (claim["text"] or "")[:180]
            pos = claim["position"]
            out.append((entry["premise_id"], weight, text, pos))

            # Dual attribution: if this edge connects with a
            # dual-attribution layer, ALSO attribute at that layer's node.
            (link_type, lf, lt) = pos
            if link_type == "edge":
                for endpoint in (lf, lt):
                    if endpoint in NODE_DUAL_ATTRIBUTION:
                        out.append((
                            entry["premise_id"],
                            weight * 0.5,   # half weight for the dual attribution
                            f"[dual] {text}",
                            ("node", endpoint, endpoint),
                        ))
    return out


# ----------------------------------------------------------------------
# Hypothesis generation (world-model stub v0)
# ----------------------------------------------------------------------
# For now this replicates the scoring rules from hydrate_patient_view.py,
# but as a "generator" that emits stored hypothesis rows with rationale
# + a hypothesis_premise audit trail.

def pick_topk_diverse(ranked, *, family_of, k=3):
    """Greedy top-K with a hard one-per-family diversity constraint.

    `ranked` is `[(item_id, payload), ...]` already sorted best-first.
    `family_of(item_id)` returns the mechanism-family key. Walks the ranking
    once, admitting each candidate whose family hasn't already been claimed
    until K survivors are picked. If fewer than K distinct families exist we
    return however many families we found (never dips into a second-from-a-
    family filler — Phase 2 will introduce that fallback if needed).
    """
    picked, seen = [], set()
    for item in ranked:
        fam = family_of(item[0])
        if fam in seen:
            continue
        picked.append(item)
        seen.add(fam)
        if len(picked) == k:
            break
    return picked


def parse_exon(s: str | None) -> int | None:
    if not s: return None
    t = s.strip()
    if t.lower().startswith("int"): t = t[3:]
    try: return int(t)
    except ValueError: return None


# (weight, rationale) per (template, feature) — mirrors the current
# hydrate_patient_view.score_hypotheses rules.
def score_templates(consequence: str, phenotype: str, exon_n: int | None
                    ) -> dict[str, tuple[float, str]]:
    cons = (consequence or "").lower()
    phen = phenotype or ""
    out: dict[str, tuple[float, str]] = {}

    # H01 — out-of-frame → truncation
    if cons == "frameshift":
        out["01"] = (9.5, "frameshift → out-of-frame → truncated dystrophin (Monaco rule)")
    elif cons == "nonsense":
        out["01"] = (6.0, "premature stop → truncated protein (before NMD)")
    elif cons == "splice-site":
        out["01"] = (5.0, "splice defect can produce out-of-frame transcript")
    elif cons == "missense":
        out["01"] = (1.5, "missense does not truncate — poor fit")
    else:
        out["01"] = (0.5, "not a truncating variant")

    # H02 — in-frame / partial-function / BMD
    if phen == "BMD":
        out["02"] = (9.0, "BMD phenotype label — partial-function dystrophin consistent")
    elif phen == "IMD":
        out["02"] = (6.5, "intermediate phenotype — some partial rescue plausible")
    elif cons == "missense":
        out["02"] = (5.5, "missense can preserve some dystrophin function")
    else:
        out["02"] = (1.5, "no evidence of in-frame rescue")

    # H03 — NMD / PTC
    if cons == "nonsense":
        out["03"] = (9.5, "PTC → NMD-mediated transcript loss (direct fit)")
    elif cons == "splice-site":
        out["03"] = (9.0, "splice defect → downstream PTC → NMD-eligible")
    elif cons == "frameshift":
        out["03"] = (8.5, "frameshift creates downstream PTC → NMD-eligible")
    else:
        out["03"] = (1.5, "no PTC generated")

    # H04 — distal-isoform loss
    if exon_n is None:
        out["04"] = (1.0, "variant position not parseable")
    elif exon_n >= 63:
        out["04"] = (5.0, f"exon {exon_n} — hits Dp71 (last ubiquitous isoform)")
    elif exon_n >= 56:
        out["04"] = (4.0, f"exon {exon_n} — hits Dp116 (Schwann)")
    elif exon_n >= 45:
        out["04"] = (3.0, f"exon {exon_n} — hits Dp140 (brain/kidney)")
    else:
        out["04"] = (1.5, f"exon {exon_n} — proximal, doesn't selectively affect distal isoforms")
    return out


# Rough claim templates per hypothesis, filled in per patient.
CLAIM_TEMPLATES = {
    "01": "Patient {p}'s {cons} at exon {exon} produces an out-of-frame transcript → truncated dystrophin lacking the C-terminal DGC anchor → sarcolemmal fragility in skeletal + cardiac muscle.",
    "02": "Patient {p}'s {cons} at exon {exon} may retain partial function via in-frame rescue → BMD-like presentation with slower progression.",
    "03": "Patient {p}'s {cons} at exon {exon} generates a PTC upstream of the last exon-exon junction → NMD degrades the transcript → near-total Dp427m loss.",
    "04": "Patient {p}'s {cons} at exon {exon} selectively ablates distal isoforms (Dp140 / Dp116 / Dp71) → tissue-specific dysfunction beyond muscle.",
}


# Which premise sources support which templates (for the audit trail).
# Weight interpretation: score contribution / 10 (relative unit).
# Chain layers (must match the order used in the layered biological view).
LAYERS = ["variant", "protein", "pathway", "subcellular",
          "cellType", "tissue", "phenotype"]


# Attribute a premise (by its source_id) to a position in the biological
# chain. A premise informs either a NODE (layer_from == layer_to) or an
# EDGE (adjacent layers). Some sources inform multiple positions.
def premise_chain_positions(source_id: str, evidence: dict) -> list[tuple[str, str, str]]:
    """Return [(link_type, layer_from, layer_to)] positions for this premise."""
    if source_id == "zhang_2024":
        # Variant record itself + patient phenotype label
        return [("node", "variant", "variant"), ("node", "phenotype", "phenotype")]
    if source_id == "clinvar_nmd":
        # Cohort NMD cross-tab argues for the variant→protein transition
        return [("edge", "variant", "protein")]
    if source_id == "isoform_arch":
        # Per-patient isoform-hit projection: variant→protein edge + protein node
        return [("edge", "variant", "protein"), ("node", "protein", "protein")]
    if source_id == "esm3":
        # ESM3 fold: protein node + evidence for the variant→protein transition
        return [("node", "protein", "protein"), ("edge", "variant", "protein")]
    if source_id == "reactome":
        # Pathway memberships: pathway node + edge to cellType
        return [("node", "pathway", "pathway"), ("edge", "pathway", "subcellular")]
    if source_id == "hpa_expression":
        # HPA cell-type expression: cellType node + edge to tissue
        return [("node", "cellType", "cellType"), ("edge", "cellType", "tissue")]
    if source_id == "synthetic_labs":
        # Each lab has its own layer (evidence.layer field: cellType|tissueType|phenotype)
        layer = evidence.get("layer", "phenotype")
        # Our labs use "tissueType" in the labs table but LAYERS uses "tissue"
        norm = "tissue" if layer == "tissueType" else layer
        return [("node", norm, norm)]
    if source_id == "patient_celltype_impact":
        return [("node", "cellType", "cellType"), ("edge", "protein", "cellType")]
    if source_id == "patient_tissue_impact":
        return [("node", "tissue", "tissue"), ("edge", "cellType", "tissue")]
    if source_id == "uniprot_subcellular":
        # Curated protein-biology at the subcellular node + informs the
        # protein→subcellular edge (where does the protein normally sit).
        return [("node", "subcellular", "subcellular"),
                ("edge", "protein", "subcellular")]
    if source_id == "absplice":
        # AbSplice speaks to the variant→protein transition: cryptic /
        # canonical splice disruption changes the transcript, hence the
        # protein produced. Also anchors the variant node itself
        # (variant-level classification signal).
        return [("node", "variant", "variant"),
                ("edge", "variant", "protein")]
    if source_id == "open_targets":
        # Open Targets supplies multi-position evidence:
        #  - Reactome pathway memberships (DGC formation, striated muscle
        #    contraction, non-integrin ECM interactions) → pathway node.
        #  - Molecular interactors (SNTA1, SNTB1, SGCD, SSPN, ...) argue
        #    the protein sits in a complex on the sarcolemma →
        #    protein→subcellular edge.
        #  - Approved-drug list (exon-skipping ASOs + delandistrogene AAV)
        #    proves the phenotype end is treatable via dystrophin
        #    restoration → phenotype node.
        return [("node", "pathway", "pathway"),
                ("edge", "protein", "subcellular"),
                ("node", "phenotype", "phenotype")]
    if source_id == "nmd_prediction":
        # Per-patient 50-nt-rule verdict determines the variant→protein
        # transition (transcript degraded vs truncated protein produced).
        return [("edge", "variant", "protein"),
                ("node", "protein", "protein")]
    if source_id == "exon_skip_viability":
        # Therapeutic branch: whether this variant is FDA-approved-ASO
        # eligible. Anchors the variant node itself (variant-level
        # therapeutic classification) + the phenotype node (approved
        # intervention exists → treatable).
        return [("node", "variant", "variant"),
                ("node", "phenotype", "phenotype")]
    if source_id == "dgc_completeness":
        # Quantifies how much of the DGC assembly this variant
        # abolishes per affected cell type. Anchors the cellType node
        # + the cellType→tissue transition (which tissues suffer
        # nearly-complete DGC loss).
        return [("node", "cellType", "cellType"),
                ("edge", "cellType", "tissue")]
    if source_id == "domain_annotation":
        # Static protein-domain architecture: anchors the protein node
        # + the protein→subcellular edge (which domains bind the
        # sarcolemmal DGC).
        return [("node", "protein", "protein"),
                ("edge", "protein", "subcellular")]
    # `literature` premises carry their per-hypothesis chain positions
    # via literature_links_for_template — no source-level default.
    return []


def premise_weights_for_template(hyp_id: str, patient_premises: dict, cohort_premises: dict
                                  ) -> list[tuple[str, float, str]]:
    """Return [(premise_id, signed_weight, rationale)] linking premises to this hyp."""
    out = []
    zhang_pid = patient_premises.get("zhang")
    iso_pid   = patient_premises.get("iso")
    esm3_pid  = patient_premises.get("esm3")
    lab_pids  = patient_premises.get("labs", [])
    ct_pid    = patient_premises.get("celltype_impact")
    ct_ev     = patient_premises.get("celltype_impact_ev", {})
    tis_pid   = patient_premises.get("tissue_impact")
    tis_ev    = patient_premises.get("tissue_impact_ev", {})
    nmd_pid   = cohort_premises.get("nmd_cohort")
    hpa_pid   = cohort_premises.get("hpa")
    reactome_pid = cohort_premises.get("reactome")

    # Every hypothesis draws on the Zhang variant record.
    if zhang_pid:
        out.append((zhang_pid, 1.0, "variant + phenotype + exon from Zhang 2024 record"))

    # Isoform architecture projection is the substrate for isoform-impact reasoning.
    if iso_pid:
        out.append((iso_pid, 0.7, "per-isoform hit/spared projection from variant exon position"))

    # NMD cohort premise informs H03 primarily.
    if nmd_pid and hyp_id == "03":
        out.append((nmd_pid, 0.8, "ClinVar 11,790-variant NMD × ACMG cross-tab supports NMD mechanism at cohort scale"))

    # HPA expression informs H01/H03/H04 (which cell types express which isoforms).
    if hpa_pid and hyp_id in ("01", "03", "04"):
        out.append((hpa_pid, 0.5, "HPA cell-type expression identifies which tissues lose dystrophin"))

    # Reactome informs H01 (DGC pathway).
    if reactome_pid and hyp_id == "01":
        out.append((reactome_pid, 0.4, "Reactome DGC-formation pathway is a first-order consequence of dystrophin loss"))

    # ESM3 fold informs H01/H03 by making the truncated protein claim structural.
    if esm3_pid and hyp_id in ("01", "03"):
        out.append((esm3_pid, 0.6, "ESM3 fold of WT + truncated dystrophin visualizes the DGC-anchor loss"))

    # UniProt subcellular localization anchors the sarcolemma-based DGC
    # mechanism. Supports all mechanisms of protein LOSS (they all depend
    # on knowing where dystrophin normally sits) — weak for H04 which is
    # about distal isoforms with different localization patterns.
    us_pid = cohort_premises.get("uniprot_subcellular")
    if us_pid:
        if hyp_id in ("01", "02", "03"):
            out.append((us_pid, 0.6,
                "UniProt: dystrophin localizes at sarcolemma (peripheral membrane, cytoplasmic face); loss disrupts DGC anchoring"))
        elif hyp_id == "04":
            out.append((us_pid, 0.2,
                "UniProt: primary localization is sarcolemma; distal isoforms (Dp71 in retina/CNS/kidney) have separate localization patterns"))

    # Open Targets: approved drugs + DGC interactors + Reactome pathways
    # + top disease associations. Cohort-scope premise — same weight
    # rationale applies to every patient. We compose ONE synthesized
    # rationale per hypothesis (rather than three competing INSERT OR
    # REPLACE writes) so the strongest evidence surfaces intact.
    ot_pid = cohort_premises.get("opentargets")
    ot_ev  = cohort_premises.get("opentargets_ev", {})
    if ot_pid and ot_ev:
        approved     = ot_ev.get("approved_drugs") or []
        n_approved   = len(approved)
        interactors  = ot_ev.get("interactions") or []
        dgc_partners = sorted({x["symbol"] for x in interactors
                               if x.get("symbol") in
                               {"SNTA1", "SNTB1", "SNTB2", "SGCA", "SGCB",
                                "SGCD", "SGCG", "SSPN", "DAG1", "DTNA",
                                "DTNB", "NOS1"}})
        top_disease  = (ot_ev.get("top_diseases") or [{}])[0].get("name") or "?"
        top_score    = (ot_ev.get("top_diseases") or [{}])[0].get("score") or 0.0

        parts: list[str] = []
        if n_approved >= 2:
            parts.append(f"{n_approved} approved dystrophin-restoration drugs (exon-skipping ASOs + AAV μ-dystrophin)")
        if dgc_partners:
            parts.append("DGC partners " + ", ".join(dgc_partners[:5]))
        if top_score >= 0.7 and top_disease.lower().startswith("duchenne"):
            parts.append(f"assoc {top_score:.2f} → {top_disease}")
        prefix = "; ".join(parts) if parts else "target record present"

        # Signed weight per hypothesis
        if hyp_id in ("01", "03"):
            w = 0.6
            tail = "treats/anchors the DGC-loss mechanism"
        elif hyp_id == "02":
            w = 0.4
            tail = "same rescue target; partial-function fits the BMD scenario"
        else:  # H04 — approved drugs restore full-length, not distal isoforms
            w = -0.2
            tail = "approved drugs target Dp427 restoration, not distal isoforms — H04 mechanism has no approved treatment"

        out.append((ot_pid, w, f"OpenTargets: {prefix} — {tail}"))

    # AbSplice: per-tissue aberrant-splicing probability.
    # Weight scales with max_score across tissues:
    #   > 0.5  -> strong splice-mechanism signal; boosts H01/H03 (extra NMD
    #            trigger from cryptic/exon-skipping) and H02 (partial
    #            in-frame product possible from cryptic acceptor)
    #   0.05-0.5 -> moderate secondary effect; small positive for H01/H03
    #   < 0.05 -> negligible; no weight contribution
    absp_pid = patient_premises.get("absplice")
    absp_ev  = patient_premises.get("absplice_ev", {})
    if absp_pid and absp_ev:
        max_score  = absp_ev.get("max_score") or 0.0
        max_tissue = absp_ev.get("max_tissue") or "?"
        category   = absp_ev.get("category") or "?"
        if max_score >= 0.5:
            if hyp_id in ("01", "03"):
                out.append((absp_pid, 0.7,
                    f"AbSplice {max_score:.2f} in {max_tissue} ({category}) — aberrant splicing compounds the NMD/DGC-loss mechanism"))
            elif hyp_id == "02":
                out.append((absp_pid, 0.3,
                    f"AbSplice {max_score:.2f} — cryptic-acceptor use could yield a partial in-frame product"))
            elif hyp_id == "04":
                out.append((absp_pid, 0.1,
                    f"AbSplice {max_score:.2f} — splice disruption affects full-length transcript; distal isoforms less relevant"))
        elif max_score >= 0.05:
            if hyp_id in ("01", "03"):
                out.append((absp_pid, 0.2,
                    f"AbSplice {max_score:.2f} ({category}) — moderate secondary splicing effect"))
        else:
            # Low score is itself evidence: no splice mechanism, so the
            # exonic-consequence interpretation stands unchallenged.
            if hyp_id in ("01", "03"):
                out.append((absp_pid, 0.1,
                    f"AbSplice {max_score:.2f} — negligible splice signal; exonic consequence is the whole story"))

    # Composition premises: cell-type & tissue impact.
    # Weight signs matter — spared distal cell types actively argue against H04.
    if ct_pid and ct_ev:
        cells = ct_ev.get("cells", [])
        muscle_cells = [c for c in cells
                        if any(m in (c.get("tissue") or "").lower()
                               for m in ("muscle", "cardiac", "thymus", "salivary"))]
        distal_cells = [c for c in cells
                        if any(d in (c.get("tissue") or "").lower()
                               for d in ("retina", "adipose"))]
        muscle_hit    = sum(1 for c in muscle_cells if c["status"] == "hit")
        distal_hit    = sum(1 for c in distal_cells if c["status"] == "hit")
        distal_spared = sum(1 for c in distal_cells if c["status"] == "spared")

        if hyp_id in ("01", "03") and muscle_hit > 0:
            out.append((ct_pid, 0.6,
                f"{muscle_hit} muscle-lineage cell types affected — supports muscle-fragility mechanism"))
        if hyp_id == "02" and muscle_hit > 0:
            out.append((ct_pid, 0.3,
                f"{muscle_hit} muscle cell types affected — consistent with partial-function BMD scenario"))
        if hyp_id == "04":
            if distal_hit > 0:
                out.append((ct_pid, 0.8,
                    f"{distal_hit} distal (retinal/adipose) cell types affected — supports distal-isoform-loss mechanism"))
            if distal_spared > 0:
                out.append((ct_pid, -0.5,
                    f"{distal_spared} distal cell types SPARED — argues against distal-isoform-loss mechanism"))
            if distal_hit == 0 and distal_spared > 0:
                # Full-negative case: all distal cells spared → H04 unsupported
                out.append((ct_pid, -0.3, "no evidence of distal-isoform cell-type effects for this patient"))

    if tis_pid and tis_ev:
        hit_tissues    = tis_ev.get("tissues_hit", [])
        spared_tissues = tis_ev.get("tissues_spared", [])
        muscle_hit = any("muscle" in t for t in hit_tissues)
        cns_hit    = any(t in hit_tissues for t in ("brain", "brain_glia", "cortical_neurons",
                                                     "hippocampus", "cerebellar_Purkinje_cells"))
        renal_hit  = "kidney" in hit_tissues
        retina_hit = any("retina" in t for t in hit_tissues)

        if hyp_id in ("01", "03") and muscle_hit:
            out.append((tis_pid, 0.5, "skeletal + cardiac muscle tissue affected — core H01/H03 phenotype"))
        if hyp_id == "04":
            distal_tissues_hit = sum([cns_hit, renal_hit, retina_hit])
            if distal_tissues_hit > 0:
                out.append((tis_pid, 0.7,
                    f"{distal_tissues_hit} distal tissue systems (CNS/kidney/retina) affected — supports H04"))
            else:
                out.append((tis_pid, -0.4,
                    "no distal tissue systems affected — argues against H04"))

    # NMD prediction: per-patient 50-nt-rule verdict. Strongest signal for
    # H01 (LoF via NMD, canonical DMD trajectory) and H03 (NMD-driven
    # tissue-graded loss). Weakly supportive for H04 if PTC also hits
    # distal-isoform transcripts. Not applicable for missense (verdict
    # 'not_ptc_generating').
    nmd_p_pid = patient_premises.get("nmd_prediction")
    nmd_p_ev  = patient_premises.get("nmd_prediction_ev", {})
    if nmd_p_pid and nmd_p_ev:
        verdict = nmd_p_ev.get("verdict")
        rat = nmd_p_ev.get("rationale") or ""
        if verdict == "nmd_triggered":
            if hyp_id in ("01", "03"):
                out.append((nmd_p_pid, 0.75, rat))
            elif hyp_id == "04":
                out.append((nmd_p_pid, 0.2,
                    "PTC also degrades transcripts encoding distal isoforms — supports isoform-loss H04"))
        elif verdict == "nmd_escape":
            # NMD-escape shifts the mechanism from "no protein" toward
            # "truncated protein produced" — actively argues for a
            # dominant-negative-flavoured H02 and against pure-LoF H01/H03.
            if hyp_id == "02":
                out.append((nmd_p_pid, 0.6,
                    "PTC in last-exon escape window — truncated protein IS produced (dominant-negative candidate)"))
            elif hyp_id in ("01", "03"):
                out.append((nmd_p_pid, -0.3,
                    "PTC escapes NMD — pure-LoF mechanism weakened; truncated fragment is present"))

    # Exon-skip viability: therapeutic branch. Positive for hypotheses
    # whose canonical rescue IS exon-skipping (H01 out-of-frame → in-frame
    # via skip; H02 already partial-function; H03 sees skip as second-line
    # after readthrough).
    skip_pid = patient_premises.get("exon_skip")
    skip_ev  = patient_premises.get("exon_skip_ev", {})
    if skip_pid and skip_ev:
        verdict = skip_ev.get("verdict")
        rat = skip_ev.get("rationale") or ""
        if verdict == "direct_skip_eligible":
            if hyp_id in ("01", "02"):
                out.append((skip_pid, 0.7, rat))
            elif hyp_id == "03":
                out.append((skip_pid, 0.4,
                    f"{skip_ev.get('direct_drug')} — exon-skip is second-line after readthrough for H03 NMD mechanism"))
        elif verdict == "adjacent_skip_candidate":
            if hyp_id in ("01", "02"):
                out.append((skip_pid, 0.35, rat))
        else:  # no_approved_skip
            if hyp_id in ("01", "02"):
                out.append((skip_pid, -0.2,
                    "no FDA-approved exon-skip covers this variant — H01/H02 rescue must use AAV or readthrough"))

    # DGC-completeness per affected cell type. Direct evidence for the
    # cellType→tissue transition in H01/H03 (where DGC loss IS the
    # mechanism). Weaker for H02 (partial-function still needs DGC) and
    # H04 (distal isoforms have simpler assemblies).
    dgc_pid = patient_premises.get("dgc_completeness")
    dgc_ev  = patient_premises.get("dgc_completeness_ev", {})
    if dgc_pid and dgc_ev:
        mean_dgc = dgc_ev.get("mean_dgc_completeness", 0.0)
        n_cells = len(dgc_ev.get("affected_cells", []))
        if hyp_id in ("01", "03"):
            out.append((dgc_pid, 0.55,
                f"mean DGC-completeness {mean_dgc:.2f} across {n_cells} affected cell types — quantifies the DGC-assembly loss"))
        elif hyp_id == "02":
            out.append((dgc_pid, 0.3,
                f"DGC-completeness {mean_dgc:.2f} — partial-function truncation still needs the DGC scaffold"))
        elif hyp_id == "04":
            out.append((dgc_pid, 0.1,
                f"DGC-completeness {mean_dgc:.2f} — distal isoforms have simpler assemblies; not the H04 mechanism"))

    # Domain annotation (cohort-scope): protein architecture + per-domain
    # literature. Same weight for all patients. Supports every hypothesis
    # whose chain touches the protein node.
    dom_pid = cohort_premises.get("domain_annotation")
    if dom_pid:
        if hyp_id in ("01", "02", "03"):
            out.append((dom_pid, 0.4,
                "4-domain DMD architecture (N-term actin-binding, spectrin rod, cysteine-rich β-DG, C-terminal syntrophin/dystrobrevin) — cys-rich + C-term are the DGC-anchoring domains"))
        elif hyp_id == "04":
            out.append((dom_pid, 0.15,
                "domain architecture reference; distal isoforms use different N-terminal exons but share the DGC-anchoring C-terminus"))

    # Abnormal labs contribute per-lab weight for the mechanism they support.
    if hyp_id == "01":
        # elevated CK, low LVEF, low FVC, high MRI ff → all support muscle fragility
        for lp in lab_pids:
            if any(k in lp for k in ("CK", "LVEF", "FVC", "MRI_ff", "m6MWT")):
                out.append((lp, 0.4, "abnormal lab consistent with H01 sarcolemmal-fragility mechanism"))
    elif hyp_id == "02":
        for lp in lab_pids:
            if any(k in lp for k in ("NSAA", "m6MWT")):
                out.append((lp, 0.3, "motor function retention weakly supports partial-rescue hypothesis"))
    elif hyp_id == "03":
        for lp in lab_pids:
            if any(k in lp for k in ("CK", "MRI_ff")):
                out.append((lp, 0.5, "muscle-damage lab consistent with total protein loss from NMD"))
            if "IQ" in lp:
                out.append((lp, 0.2, "tissue-graded NMD escape — IQ status is diagnostic"))
    elif hyp_id == "04":
        for lp in lab_pids:
            if any(k in lp for k in ("IQ", "ERG", "UACR")):
                out.append((lp, 0.6, "distal-tissue lab abnormality points at distal isoform loss"))

    return out


# ----------------------------------------------------------------------
# Claim enrichment
#
# Layer 0 = CLAIM_TEMPLATES with 3 slots (p / cons / exon). Every H01
#           patient reads the same. `exon_str` bug leaks through.
# Layer 1 = deterministic enrichment — reads real values out of the
#           premise bundle (exon_n from isoform_arch, AbSplice score,
#           muscle_hit count, distal spared/hit, hit_isoforms) and
#           weaves them into the mechanism sentence + a "distinguishing
#           evidence" line built from the top-3 weighted premises.
#           Pure code, no LLM.
# Layer 2 = LLM refinement (below) — takes Layer 1 + full premise bundle
#           and produces {narrative, considered_but_discarded, testable}.
# ----------------------------------------------------------------------

_DISTAL_TISSUE_KEYS  = ("retina", "adipose", "brain", "cortex", "hippocampus", "cerebellum")
_MUSCLE_TISSUE_KEYS  = ("muscle", "cardiac", "thymus", "salivary")


def build_claim_context(patient_key: str, nuc: str | None, exon_n: int | None,
                        patient_premises: dict) -> dict:
    """Extract structured, template-agnostic values from the premise bundle
    for claim composition. Values are None when the underlying premise
    is absent."""
    ctx: dict = {
        "p":       patient_key,
        "hgvsc":   nuc,
        "exon_n":  exon_n,
    }

    # isoform_arch: which isoforms are hit vs spared for this patient
    iso_ev = patient_premises.get("iso_ev") or {}
    ctx["hit_isoforms"]    = iso_ev.get("hit_isoforms")    or []
    ctx["spared_isoforms"] = iso_ev.get("spared_isoforms") or []

    # AbSplice: variant-level splice-disruption score
    absp = patient_premises.get("absplice_ev") or {}
    ctx["absplice_max"]      = absp.get("max_score")
    ctx["absplice_tissue"]   = absp.get("max_tissue")
    ctx["absplice_category"] = absp.get("category")

    # patient_celltype_impact: which cell types are hit/spared for this patient
    ct = patient_premises.get("celltype_impact_ev") or {}
    cells = ct.get("cells", [])
    def _match(c, keys):
        return any(k in ((c.get("tissue") or "") + " " + (c.get("name") or "")).lower() for k in keys)
    ctx["muscle_hit_cells"]    = [c["name"] for c in cells if _match(c, _MUSCLE_TISSUE_KEYS)  and c["status"] == "hit"]
    ctx["distal_hit_cells"]    = [c["name"] for c in cells if _match(c, _DISTAL_TISSUE_KEYS)  and c["status"] == "hit"]
    ctx["distal_spared_cells"] = [c["name"] for c in cells if _match(c, _DISTAL_TISSUE_KEYS)  and c["status"] == "spared"]

    # patient_tissue_impact: tissues hit/spared
    tis = patient_premises.get("tissue_impact_ev") or {}
    ctx["tissues_hit"]    = tis.get("tissues_hit")    or []
    ctx["tissues_spared"] = tis.get("tissues_spared") or []
    return ctx


def _fmt_list(xs: list[str], limit: int = 4) -> str:
    """Human-readable comma list with ellipsis after `limit`."""
    if not xs: return ""
    if len(xs) <= limit: return ", ".join(xs)
    return ", ".join(xs[:limit]) + f", +{len(xs) - limit} more"


def enrich_claim(tmpl_id: str, ctx: dict, prem_weights: list[tuple[str, float, str]]) -> dict:
    """Layer 1: produce a per-patient claim by weaving premise-bundle
    values into the mechanism sentence. Returns {claim, distinguishing}."""
    p     = ctx.get("p")     or "patient"
    hgvsc = ctx.get("hgvsc") or "variant"
    exon  = ctx.get("exon_n") if ctx.get("exon_n") is not None else "?"

    if tmpl_id == "01":
        muscle = _fmt_list(ctx.get("muscle_hit_cells") or [])
        muscle_note = f" Composition: {len(ctx.get('muscle_hit_cells') or [])} muscle-lineage cell types hit ({muscle})." if muscle else ""
        claim = (
            f"{p}'s {hgvsc} at exon {exon} produces an out-of-frame transcript → "
            f"truncated dystrophin lacking the C-terminal DGC anchor → "
            f"sarcolemmal fragility in skeletal + cardiac muscle."
            f"{muscle_note}"
        )
    elif tmpl_id == "02":
        rescue_note = ""
        hit = ctx.get("hit_isoforms") or []
        spared = ctx.get("spared_isoforms") or []
        if spared:
            rescue_note = f" Spared isoforms: {_fmt_list(spared)}."
        claim = (
            f"{p}'s {hgvsc} at exon {exon} may retain partial function via "
            f"in-frame rescue → BMD-like presentation with slower progression."
            f"{rescue_note}"
        )
    elif tmpl_id == "03":
        splice_note = ""
        if ctx.get("absplice_max") is not None and ctx["absplice_max"] >= 0.5:
            splice_note = (
                f" AbSplice {ctx['absplice_max']:.2f} in "
                f"{ctx.get('absplice_tissue') or 'target tissue'} "
                f"({ctx.get('absplice_category') or 'splice event'}) — "
                f"aberrant splicing is a compounding NMD trigger."
            )
        claim = (
            f"{p}'s {hgvsc} at exon {exon} generates a PTC upstream of the last "
            f"exon-exon junction → NMD degrades the Dp427m transcript → "
            f"near-total protein loss."
            f"{splice_note}"
        )
    elif tmpl_id == "04":
        distal_note = ""
        hit    = ctx.get("distal_hit_cells")    or []
        spared = ctx.get("distal_spared_cells") or []
        if hit:
            distal_note = f" Composition supports: {len(hit)} distal cell types hit ({_fmt_list(hit)})."
        elif spared:
            distal_note = f" Composition contradicts: {len(spared)} distal cell types spared for this patient — H04 mechanism unlikely."
        claim = (
            f"{p}'s {hgvsc} at exon {exon} selectively ablates distal isoforms "
            f"(Dp140 / Dp116 / Dp71) → tissue-specific dysfunction beyond muscle."
            f"{distal_note}"
        )
    else:
        claim = CLAIM_TEMPLATES.get(tmpl_id, "").format(p=p, cons=hgvsc, exon=exon)

    top3 = sorted(prem_weights, key=lambda x: -abs(x[1]))[:3]
    distinguishing = [
        {"weight": round(w, 2),
         "premiseId": pr_id,
         "rationale": (rat or "")[:200]}
        for (pr_id, w, rat) in top3
    ]

    return {"claim": claim, "distinguishing": distinguishing}


# ----------------------------------------------------------------------
# Layer 2: LLM refinement via Anthropic Messages API (stdlib urllib —
# no SDK dep). Takes the Layer-1 claim + full premise bundle for all 4
# hypotheses of a patient, returns per-hypothesis {narrative,
# considered_but_discarded, testable_predictions}.
# ----------------------------------------------------------------------
import os as _os
import urllib.request as _urllib_req
import urllib.error as _urllib_err

_LLM_CACHE_DIR = REPO / "cache" / "llm_refine"
_LLM_ENDPOINT  = "https://api.anthropic.com/v1/messages"
_LLM_MODEL     = _os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def _llm_available() -> bool:
    return bool(_os.environ.get("ANTHROPIC_API_KEY"))


def _llm_cache_path(cache_key: str) -> Path:
    _LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _LLM_CACHE_DIR / f"{cache_key}.json"


def _call_anthropic(messages: list[dict], max_tokens: int = 3000,
                    timeout: int = 180) -> str:
    """Blocking single-turn Messages API call. Returns assistant text."""
    body = {
        "model":      _LLM_MODEL,
        "max_tokens": max_tokens,
        "messages":   messages,
    }
    req = _urllib_req.Request(
        _LLM_ENDPOINT,
        method="POST",
        headers={
            "x-api-key":         _os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        data=json.dumps(body).encode(),
    )
    with _urllib_req.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    return resp["content"][0]["text"]


def _extract_json_object(text: str) -> dict | None:
    """Parse the first top-level {...} JSON object from `text`. Returns
    None on failure. Handles markdown fences and pre/post prose."""
    if not text: return None
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.startswith("json"): s = s[4:]
        s = s.rsplit("```", 1)[0]
    start = s.find("{")
    end   = s.rfind("}")
    if start < 0 or end < 0 or end <= start: return None
    try: return json.loads(s[start:end + 1])
    except json.JSONDecodeError: return None


def _build_llm_prompt(patient_label: str, patient_meta: dict,
                      hypotheses: list[dict]) -> list[dict]:
    """Build a single-turn prompt asking the model to refine claims for
    ALL of a patient's hypotheses in one call. Cross-hypothesis context
    is needed so the "considered but discarded" text can reference the
    other templates' specific premises."""
    system_intent = (
        "You are refining draft mechanism claims for a rare-disease "
        "mechanism workbench. You are strictly grounded: every specific "
        "value (numbers, cell names, isoform names, tissue names, citation "
        "authors) MUST appear in the input premise bundle. If a claim "
        "would require an unsupported value, omit it rather than "
        "invent it. Do NOT re-rank the hypotheses. For each hypothesis: "
        "(a) narrative: ≤ 90 words, one paragraph, clinician-readable, "
        "cite specific premise values by short name (e.g. 'AbSplice 0.88', "
        "'Muntoni 2003'); (b) considered_but_discarded: for each of the "
        "OTHER 3 hypotheses, one sentence ≤ 25 words citing the specific "
        "premise that made it rank lower; (c) testable_predictions: "
        "exactly 3 concrete assays, each ≤ 22 words. Do not repeat the "
        "input premise bundle. Be dense, not verbose."
    )
    schema = {
        "hypotheses": [
            {
                "id": "01",
                "narrative": "one paragraph, clinician-readable, cite specific premise values",
                "considered_but_discarded": [
                    {"other_id": "02", "why_lower": "specific premise-cited reason"},
                    {"other_id": "03", "why_lower": "..."},
                    {"other_id": "04", "why_lower": "..."}
                ],
                "testable_predictions": [
                    "assay 1 with expected result",
                    "assay 2 with expected result"
                ]
            }
        ]
    }
    user = {
        "role": "user",
        "content": (
            f"{system_intent}\n\n"
            f"Patient: {patient_label}\n"
            f"Variant: {patient_meta.get('hgvsc')} at exon {patient_meta.get('exon_n')}\n"
            f"Phenotype: {patient_meta.get('phenotype')}\n"
            f"Consequence: {patient_meta.get('consequence')}\n\n"
            f"Hypotheses (each with rank, score, Layer-1 claim, premises, contradictions):\n"
            f"```json\n{json.dumps(hypotheses, indent=2)}\n```\n\n"
            f"Return EXACTLY ONE JSON object matching this schema (no prose before or after, no markdown fences):\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```"
        ),
    }
    return [user]


def refine_claims_with_llm(patient_label: str, patient_meta: dict,
                            hypotheses_bundle: list[dict], cache_key: str
                            ) -> dict | None:
    """Layer 2. Returns {"hypotheses": [{id, narrative, considered_but_discarded,
    testable_predictions}, ...]} or None if LLM unavailable / call failed.
    Cached by cache_key."""
    # Cache lookup happens first so previously-baked refinements survive
    # re-runs even when ANTHROPIC_API_KEY isn't sourced in the shell.
    cache_path = _llm_cache_path(cache_key)
    if cache_path.exists():
        try:
            print(f"[llm] {patient_label} — cache hit")
            return json.loads(cache_path.read_text())
        except Exception: pass  # fall through and re-call
    if not _llm_available(): return None

    print(f"[llm] {patient_label} — refining {len(hypotheses_bundle)} hypotheses via {_LLM_MODEL}...")
    try:
        messages = _build_llm_prompt(patient_label, patient_meta, hypotheses_bundle)
        raw = _call_anthropic(messages, max_tokens=8000)
    except (_urllib_err.URLError, TimeoutError, KeyError, ValueError, OSError) as e:
        print(f"[llm]   FAILED for {patient_label}: {type(e).__name__}: {e}")
        return None

    parsed = _extract_json_object(raw)
    if not parsed or "hypotheses" not in parsed:
        # Persist the raw response so we can debug parse failures.
        debug_path = _LLM_CACHE_DIR / f"{cache_key}.debug.txt"
        debug_path.write_text(raw or "")
        print(f"[llm]   unparseable response for {patient_label} — saved to {debug_path}")
        return None

    payload = {
        "model":     _LLM_MODEL,
        "generated": NOW,
        "raw":       raw,
        "hypotheses": parsed["hypotheses"],
    }
    cache_path.write_text(json.dumps(payload, indent=2))
    return payload


# Patterns for lightweight groundedness verification: any specific value
# the LLM mentions (isoform, number, author-year) should appear somewhere
# in the input premise bundle. Unverified mentions get logged, not blocked.
_ISOFORM_RE = re.compile(r"\bDp(?:427[mcp]?|260|140|116|71)\b")
_NUMBER_RE  = re.compile(r"\b\d+(?:\.\d+)?\b")
_AUTHOR_RE  = re.compile(r"\b[A-Z][a-zäöüéèñ]+ (?:\d{4}|et al\.? \d{4})")


def _check_groundedness(narrative: str, bundle_text: str) -> dict:
    """Return {unverified_isoforms, unverified_numbers, unverified_citations,
    total_mentions}. Numbers < 3 chars (like page counts, cell counts) are
    ignored — only decimal scores and 4-digit years get checked."""
    findings = {
        "unverified_isoforms":  sorted(
            {m.group() for m in _ISOFORM_RE.finditer(narrative)
             if m.group() not in bundle_text}
        ),
        "unverified_citations": sorted(
            {m.group() for m in _AUTHOR_RE.finditer(narrative)
             if m.group() not in bundle_text}
        ),
        "unverified_numbers": sorted(
            {m.group() for m in _NUMBER_RE.finditer(narrative)
             if ("." in m.group() or len(m.group()) == 4)
             and m.group() not in bundle_text}
        ),
    }
    findings["total_mentions"] = (
        len(_ISOFORM_RE.findall(narrative))
        + len(_AUTHOR_RE.findall(narrative))
        + sum(1 for m in _NUMBER_RE.finditer(narrative)
              if "." in m.group() or len(m.group()) == 4)
    )
    return findings


def _hyp_bundle_for_llm(hyp_id: str, tmpl_id: str, rank: int, score: float,
                        layer1_claim: str, prem_weights: list[tuple[str, float, str]],
                        contradictions: list[dict]) -> dict:
    """Shape one hypothesis for the LLM prompt — only the fields the
    model needs to write a narrative + differential."""
    return {
        "id":            tmpl_id,
        "rank":          rank,
        "score":         round(score, 2),
        "layer1_claim":  layer1_claim,
        "premises":      [
            {"weight": round(w, 2),
             "premiseId": pr_id,
             "rationale": (rat or "")[:200]}
            for (pr_id, w, rat) in
            sorted(prem_weights, key=lambda x: -abs(x[1]))[:15]
        ],
        "contradictions": contradictions,
    }


def bake_hypotheses_for_patient(conn, cohort: str, pid: str, phen: str, age: float | None,
                                 amb: str | None, exon_str: str | None, nuc: str | None,
                                 aa: str | None, cons: str | None, acmg: str | None,
                                 lit_data: dict | None = None
                                 ) -> tuple[int, int]:
    """Emit premises + patient_hypothesis + patient_therapeutic rows for one patient.
    Returns (n_hyps, n_therapies)."""
    exon_n = parse_exon(exon_str)
    variant_key = f"{cohort}#{pid}:{nuc or '?'}"

    # 1. Emit patient-scope premises
    zhang_pid = emit_zhang_premise(conn, cohort, pid, phen, exon_str, cons, aa, acmg)
    iso_pid   = emit_isoform_premise(conn, cohort, pid, exon_n)
    esm3_pid  = emit_esm3_premise(conn, cohort, pid)  # None for most
    lab_pids  = emit_lab_premises(conn, cohort, pid)
    ct_pid    = emit_celltype_impact_premise(conn, cohort, pid, exon_n)
    tis_pid   = emit_tissue_impact_premise(conn, cohort, pid, exon_n)
    absp_pid  = emit_absplice_premise(conn, cohort, pid, variant_key)
    nmd_p_pid = emit_nmd_prediction_premise(conn, cohort, pid, nuc, aa, cons, exon_n)
    skip_pid  = emit_exon_skip_viability_premise(conn, cohort, pid, exon_n, cons)
    dgc_pid   = emit_dgc_completeness_premise(conn, cohort, pid, exon_n)

    # Load evidence blobs for the composition premises so premise-weighting
    # can inspect their content (which cells hit/spared, which tissues, etc.).
    def _load_ev(pid_):
        if not pid_: return {}
        r = conn.execute("SELECT evidence FROM premise WHERE premise_id=?", (pid_,)).fetchone()
        try: return json.loads(r[0]) if r else {}
        except Exception: return {}

    patient_premises = {
        "zhang": zhang_pid, "iso": iso_pid, "iso_ev": _load_ev(iso_pid),
        "esm3": esm3_pid, "labs": lab_pids,
        "celltype_impact": ct_pid, "celltype_impact_ev": _load_ev(ct_pid),
        "tissue_impact":   tis_pid, "tissue_impact_ev":   _load_ev(tis_pid),
        "absplice":        absp_pid, "absplice_ev":       _load_ev(absp_pid),
        "nmd_prediction":  nmd_p_pid, "nmd_prediction_ev": _load_ev(nmd_p_pid),
        "exon_skip":       skip_pid,  "exon_skip_ev":     _load_ev(skip_pid),
        "dgc_completeness": dgc_pid,  "dgc_completeness_ev": _load_ev(dgc_pid),
    }
    cohort_premises = {
        "nmd_cohort":          _pid("nmd_cohort", "DMD"),
        "hpa":                 _pid("hpa", "DMD"),
        "reactome":            _pid("reactome", "DMD"),
        "uniprot_subcellular": _pid("uniprot_subcellular", "DMD"),
        "opentargets":         _pid("opentargets", "DMD"),
        "opentargets_ev":      _load_ev(_pid("opentargets", "DMD")),
        "domain_annotation":   _pid("domain_annotation", "DMD"),
    }
    lit_data = lit_data or {}

    # 2. Score templates, then prune to top-K with mechanism-family diversity.
    #
    # Phase 1: each of H01-H04 is its own mechanism family, so top-K-diverse
    # with K=3 just drops the lowest-scoring template. The diversity primitive
    # is written now (rather than a bare `[:3]`) so Phase 2 — LLM-mutated
    # candidates whose family is inherited from their seed — can reuse it
    # without further plumbing.
    scores = score_templates(cons, phen, exon_n)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1][0])
    pruned = pick_topk_diverse(
        ranked,
        family_of=lambda tmpl_id: tmpl_id,   # seed rows: family = template
        k=3,
    )
    input_hash = _hash(variant_key, phen, cons or "", str(exon_n), acmg or "")

    # Look up each premise's source_id + evidence so we can attribute
    # it to a chain position. Cache the lookup for this patient.
    def _get_premise_source_and_ev(premise_id: str) -> tuple[str, dict]:
        row = conn.execute(
            "SELECT source_id, evidence FROM premise WHERE premise_id=?",
            (premise_id,),
        ).fetchone()
        if not row: return ("unknown", {})
        try: ev = json.loads(row[1])
        except Exception: ev = {}
        return (row[0], ev)

    # Shared context for claim enrichment. Uses "P{seq}" label if a
    # roster order was passed via ROSTER_LABELS; else falls back to the
    # cohort-scoped variant key.
    patient_label = ROSTER_LABELS.get((cohort, pid)) or f"{cohort}#{pid}"
    claim_ctx = build_claim_context(patient_label, nuc, exon_n, patient_premises)

    n_hyps = 0
    layer1_bundles: list[dict] = []  # Collected during the loop and
                                     # fed into one batched Layer-2 LLM
                                     # call after all hypotheses baked.
    for rank, (tmpl_id, (score, fit)) in enumerate(pruned, start=1):
        hyp_id = f"P_{cohort}#{pid}:h{tmpl_id}:v1"
        # Layer 0 claim (raw template) — kept for backwards compat + audit.
        claim = CLAIM_TEMPLATES[tmpl_id].format(
            p=f"{cohort}#{pid}",
            cons=(cons or "variant").lower(),
            exon=exon_str or "?",
        )
        rationale = f"Rule fired: {fit}. Score {score:.2f}/10 (rank #{rank})."

        # Emit hypothesis_premise + hypothesis_chain_link audit rows
        conn.execute("DELETE FROM hypothesis_premise    WHERE hypothesis_id=?", (hyp_id,))
        conn.execute("DELETE FROM hypothesis_chain_link WHERE hypothesis_id=?", (hyp_id,))
        prem_weights = premise_weights_for_template(tmpl_id, patient_premises, cohort_premises)

        # Track per-layer contributions to compute the score vector.
        # `layer_evidence` (abs) drives coverage — any-evidence counts.
        # `signed_layer`  (signed) drives aggregate — negative premises
        # (e.g. spared distal cells arguing against H04) reduce the score.
        # `position_premises` keeps the raw (pr_id, w, rat) list per chain
        # position so we can detect contradictions (positions where both
        # positive and negative premises accrue meaningful weight).
        layer_evidence: dict[str, float] = {layer: 0.0 for layer in LAYERS}
        edge_evidence:  dict[tuple[str, str], float] = {}
        signed_layer:   dict[str, float] = {layer: 0.0 for layer in LAYERS}
        signed_edge:    dict[tuple[str, str], float] = {}
        position_premises: dict[str, list[tuple[str, float, str]]] = {}
        n_chain_links = 0

        def _link(pr_id, w, rat, positions):
            nonlocal n_chain_links
            for (link_type, lf, lt) in positions:
                conn.execute(
                    "INSERT OR REPLACE INTO hypothesis_chain_link VALUES (?,?,?,?,?,?,?)",
                    (hyp_id, link_type, lf, lt, pr_id, w, rat),
                )
                n_chain_links += 1
                key = f"node:{lf}" if link_type == "node" else f"edge:{lf}->{lt}"
                position_premises.setdefault(key, []).append((pr_id, w, rat))
                if link_type == "node":
                    layer_evidence[lf] += abs(w)
                    signed_layer[lf]   += w
                else:
                    edge_evidence[(lf, lt)] = edge_evidence.get((lf, lt), 0) + abs(w)
                    signed_edge[(lf, lt)]   = signed_edge.get((lf, lt), 0) + w

        # A. Route the data/model premises via source-level chain positions
        for (pr_id, w, rat) in prem_weights:
            if not pr_id: continue
            conn.execute(
                "INSERT OR REPLACE INTO hypothesis_premise VALUES (?,?,?,?)",
                (hyp_id, pr_id, w, rat),
            )
            source_id, ev = _get_premise_source_and_ev(pr_id)
            _link(pr_id, w, rat, premise_chain_positions(source_id, ev))

        # B. Literature premises — attribution is per-hypothesis (each
        # citation carries its own chain position for THIS template).
        for (pr_id, w, rat, position) in literature_links_for_template(lit_data, tmpl_id):
            conn.execute(
                "INSERT OR REPLACE INTO hypothesis_premise VALUES (?,?,?,?)",
                (hyp_id, pr_id, w, rat),
            )
            _link(pr_id, w, rat, [position])

        # Compute score vector:
        #   aggregate   = signed sum of all evidence weights (nodes + edges)
        #   coverage    = fraction of layers with any evidence
        #   consistency = fraction of covered chain positions with no
        #                 opposing evidence. A position is *contradicting*
        #                 when both positive and negative premises accrue
        #                 ≥ CONTRADICTION_THRESHOLD magnitude there.
        #   parsimony   = 1 / (1 + number of empty layers)
        CONTRADICTION_THRESHOLD = 0.1  # magnitude below which a signed
                                       # premise doesn't count as opposition
        n_layers_covered = sum(1 for v in layer_evidence.values() if v > 0)
        n_layers_empty   = len(LAYERS) - n_layers_covered
        aggregate = sum(signed_layer.values()) + sum(signed_edge.values())
        coverage  = n_layers_covered / len(LAYERS)
        parsimony = 1.0 / (1.0 + n_layers_empty)

        contradictions = []
        for pos_key, prems in position_premises.items():
            pos_sum = sum(w for (_, w, _) in prems if w > 0)
            neg_sum = sum(-w for (_, w, _) in prems if w < 0)
            if pos_sum >= CONTRADICTION_THRESHOLD and neg_sum >= CONTRADICTION_THRESHOLD:
                contradictions.append({
                    "position":     pos_key,
                    "positiveSum":  round(pos_sum, 3),
                    "negativeSum":  round(neg_sum, 3),
                    "supporting":   [{"premiseId": pr, "weight": round(w, 3),
                                      "rationale": (r or "")[:160]}
                                     for (pr, w, r) in prems if w > 0],
                    "opposing":     [{"premiseId": pr, "weight": round(w, 3),
                                      "rationale": (r or "")[:160]}
                                     for (pr, w, r) in prems if w < 0],
                })

        n_covered_positions = sum(1 for prems in position_premises.values() if prems)
        consistency = (1.0 - len(contradictions) / n_covered_positions
                       if n_covered_positions > 0 else 1.0)

        # ----- Pareto axes: confidence / severity / treatability -----
        # confidence is aggregated from the existing score-vector primitives
        # so downstream code doesn't need to re-derive it (min-max
        # normalisation is done at render time). Range: roughly 0-1.
        # Aggregate normalizer: divide by 20 so a strongly-supported
        # hypothesis (all-premise-sources firing, aggregate ~24) hits the
        # cap while weaker mechanisms sit around 0.5-0.6. Empirically tuned
        # to the current 4-template × 8-premise-source substrate — recheck
        # if aggregate ranges shift materially.
        confidence = max(0.0, min(1.0,
            0.5 * min(aggregate / 20.0, 1.0)
            + 0.25 * coverage
            + 0.15 * consistency
            + 0.10 * parsimony))

        # Treatability: weighted average of tissue tractability over
        # this template's target tissues. Age-based CNS shift: for
        # patients under 4 years, CNS delivery is closer to CNS_young.
        target_tissues = dict(TEMPLATE_TARGET_TISSUES.get(tmpl_id, {}))
        if age is not None and age >= 4 and "CNS_young" in target_tissues:
            w_young = target_tissues.pop("CNS_young")
            target_tissues["CNS_adult"] = target_tissues.get("CNS_adult", 0.0) + w_young
        treatability_axis = {
            t: {"weight": round(w, 3),
                "tractability": TISSUE_TRACTABILITY.get(t, 0.3)}
            for t, w in target_tissues.items()
        }
        treatability = sum(w * TISSUE_TRACTABILITY.get(t, 0.3)
                           for t, w in target_tissues.items())

        # Severity: phenotype baseline × per-template multiplier, with
        # a cardiac bump if the patient has abnormal cardiac labs.
        base_sev = PHENOTYPE_SEVERITY.get(phen, 0.5)
        sev_mult = TEMPLATE_SEVERITY.get(tmpl_id, 0.7)
        cardiac_bump = 0.0
        for lp in lab_pids:
            if "LVEF" in lp:
                cardiac_bump = 0.05  # any LVEF premise → cardiac involvement
        severity = min(1.0, base_sev * sev_mult + cardiac_bump)

        score_vector = {
            "aggregate":     round(aggregate, 3),
            "coverage":      round(coverage, 3),
            "consistency":   round(consistency, 3),
            "parsimony":     round(parsimony, 3),
            "confidence":    round(confidence, 3),
            "severity":      round(severity, 3),
            "treatability":  round(treatability, 3),
            "treatabilityBreakdown": treatability_axis,
            "severityBreakdown": {
                "phenotypeBaseline":  round(base_sev, 3),
                "templateMultiplier": round(sev_mult, 3),
                "cardiacBump":        round(cardiac_bump, 3),
            },
            "layerScores":   {layer: round(v, 3) for layer, v in layer_evidence.items()},
            "edgeScores":    {f"{lf}->{lt}": round(v, 3) for (lf, lt), v in edge_evidence.items()},
            "chainLinks":    n_chain_links,
            "contradictions": contradictions,
        }

        # Layer 1: deterministic claim enrichment (fills the raw template
        # with real premise values + top-3 distinguishing evidence).
        layer1 = enrich_claim(tmpl_id, claim_ctx, prem_weights)
        refined_claim = {
            "layer1":  layer1,
            "layer2":  None,  # populated by the LLM refinement pass below
            "context": {k: claim_ctx.get(k) for k in
                        ("hgvsc", "exon_n", "hit_isoforms", "spared_isoforms",
                         "absplice_max", "absplice_tissue", "absplice_category",
                         "muscle_hit_cells", "distal_hit_cells",
                         "distal_spared_cells")},
        }

        conn.execute(
            "INSERT OR REPLACE INTO patient_hypothesis "
            "(hypothesis_id, patient_id, variant_key, mechanism_template, rank, score, "
            " confidence, claim, rationale, score_vector, refined_claim, "
            " parent_hypothesis_id, mutation_trace, mechanism_family, "
            " generator_id, generator_version, generated_at, input_context_hash) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (hyp_id, pid, variant_key, tmpl_id, rank, score,
             min(1.0, score / 10.0), claim, rationale,
             json.dumps(score_vector), json.dumps(refined_claim),
             None, None, tmpl_id,   # Phase 1: seeds have no parent + family=template
             HYP_GENERATOR[0], HYP_GENERATOR[1], NOW, input_hash),
        )

        # Collect per-hypothesis bundle for the batched LLM call below.
        layer1_bundles.append({
            "hyp_id":         hyp_id,
            "tmpl_id":        tmpl_id,
            "rank":           rank,
            "score":          score,
            "layer1_claim":   layer1["claim"],
            "prem_weights":   prem_weights,
            "contradictions": contradictions,
            "refined_claim":  refined_claim,
        })
        n_hyps += 1

    # 2b. Layer 2 — one LLM call per patient covering all 4 hypotheses.
    #     Batched so the model has cross-hypothesis context needed for
    #     "considered but discarded". Cached by patient input_hash so
    #     unchanged inputs skip the API call. Cache hits are honored
    #     even without ANTHROPIC_API_KEY (see refine_claims_with_llm),
    #     so previously-baked refinements survive re-runs.
    if layer1_bundles:
        llm_bundles = [
            _hyp_bundle_for_llm(b["hyp_id"], b["tmpl_id"], b["rank"], b["score"],
                                 b["layer1_claim"], b["prem_weights"], b["contradictions"])
            for b in layer1_bundles
        ]
        patient_meta = {
            "hgvsc":       nuc,
            "exon_n":      exon_n,
            "phenotype":   phen,
            "consequence": cons,
        }
        cache_key = f"{cohort}_{pid}_{input_hash}"
        refined = refine_claims_with_llm(patient_label, patient_meta,
                                          llm_bundles, cache_key)
        if refined and "hypotheses" in refined:
            by_tmpl = {h.get("id"): h for h in refined["hypotheses"]}
            # Serialize the full input bundle once — used as the "ground
            # truth" text against which the LLM output is verified.
            bundle_text = json.dumps(llm_bundles)
            n_unverified_total = 0
            for b in layer1_bundles:
                layer2 = by_tmpl.get(b["tmpl_id"])
                if not layer2: continue
                narrative = layer2.get("narrative") or ""
                grounded = _check_groundedness(narrative, bundle_text)
                n_unverified_total += (
                    len(grounded["unverified_isoforms"]) +
                    len(grounded["unverified_citations"]) +
                    len(grounded["unverified_numbers"])
                )
                rc = b["refined_claim"]
                rc["layer2"] = {
                    "narrative":               narrative,
                    "considered_but_discarded": layer2.get("considered_but_discarded"),
                    "testable_predictions":    layer2.get("testable_predictions"),
                    "model":                   refined.get("model"),
                    "generated":               refined.get("generated"),
                    "groundedness":            grounded,
                }
                conn.execute(
                    "UPDATE patient_hypothesis SET refined_claim = ? WHERE hypothesis_id = ?",
                    (json.dumps(rc), b["hyp_id"]),
                )
            if n_unverified_total:
                print(f"[llm]   grounded: {n_unverified_total} unverified mentions across {len(layer1_bundles)} hypotheses")

    # 3. Emit patient_therapeutic rows for the top surviving hypothesis
    top_hyp_id = f"P_{cohort}#{pid}:h{pruned[0][0]}:v1"
    n_therapies = emit_therapeutics(conn, cohort, pid, pruned[0][0], top_hyp_id)
    return n_hyps, n_therapies


# Curated therapy templates per mechanism template. Real AAV design model
# would generate these on the fly conditioned on patient immune profile;
# for v0 we use the therapy_node text from the hypotheses table plus
# structured design blobs.
THERAPY_DESIGNS = {
    "01": [
        {"modality": "AAV",         "design": {"capsid": "AAVrh74", "promoter": "MHCK7", "transgene": "µ-dystrophin"},
         "rationale": "Delivers a truncated but functional dystrophin under a muscle-specific promoter; rescues DGC assembly.",
         "eligibility": "screening_required"},
        {"modality": "ASO",         "design": {"target_exon": "51", "chemistry": "PMO"},
         "rationale": "Exon-skipping restores in-frame Dp427m for eligible deletions.",
         "eligibility": "screening_required"},
    ],
    "02": [
        {"modality": "small_molecule", "design": {"agent": "utrophin_upregulator"},
         "rationale": "Utrophin upregulation compensates for reduced dystrophin function in BMD-like patients.",
         "eligibility": "unknown"},
    ],
    "03": [
        {"modality": "readthrough",    "design": {"agent": "ataluren", "target": "PTC"},
         "rationale": "Promotes ribosomal readthrough of PTCs — restores partial protein from NMD-degraded transcripts.",
         "eligibility": "screening_required"},
    ],
    "04": [
        {"modality": "AAV",            "design": {"capsid": "AAV9", "promoter": "tissue_restricted", "transgene": "Dp140_or_Dp71_mini"},
         "rationale": "Isoform-selective AAV delivers a Dp140/Dp71 mini-gene under a CNS/renal promoter to rescue distal-isoform loss.",
         "eligibility": "unknown"},
    ],
}


def emit_therapeutics(conn, cohort: str, pid: str, tmpl_id: str, hyp_id: str) -> int:
    designs = THERAPY_DESIGNS.get(tmpl_id, [])
    for i, d in enumerate(designs, start=1):
        tid = f"P_{cohort}#{pid}:h{tmpl_id}:t{i}"
        conn.execute(
            "INSERT OR REPLACE INTO patient_therapeutic VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, pid, hyp_id, i, 0.7, 0.7, d["modality"],
             json.dumps(d["design"]), d["rationale"], d["eligibility"],
             AAV_GENERATOR[0], AAV_GENERATOR[1], NOW),
        )
    return len(designs)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def _ensure_column(conn, table: str, column: str, decl: str) -> None:
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA_MIGRATION)
    _ensure_column(conn, "patient_hypothesis", "score_vector",         "TEXT")
    _ensure_column(conn, "patient_hypothesis", "refined_claim",        "TEXT")
    # Phase 1 lineage columns — populated as scaffolding for Phase 2
    # (LLM select-and-mutate). Seed rows: parent_hypothesis_id is NULL,
    # mutation_trace is NULL, mechanism_family = mechanism_template.
    _ensure_column(conn, "patient_hypothesis", "parent_hypothesis_id", "TEXT")
    _ensure_column(conn, "patient_hypothesis", "mutation_trace",       "TEXT")
    _ensure_column(conn, "patient_hypothesis", "mechanism_family",     "TEXT")

    # 1. Register premise sources
    register_sources(conn)
    print(f"[sources]  {len(PREMISE_SOURCES)} premise sources registered")

    # 2. Emit cohort-scope premises (shared across patients)
    emit_hpa_premise(conn)
    emit_reactome_premise(conn)
    emit_nmd_cohort_premise(conn)
    emit_uniprot_subcellular_premise(conn, "P11532")
    ot_pid = emit_opentargets_premise(conn)
    emit_domain_annotation_premise(conn)
    ot_tag = "OpenTargets " if ot_pid else ""
    print(f"[cohort]   HPA + Reactome + NMD + UniProt-subcellular + {ot_tag}+ DMD-domains cohort premises emitted")

    # 2b. Migrate curated citations from hypothesis_chain_edge_evidence
    #     into the literature premise source. One premise per unique
    #     citation; per-hypothesis chain-position attribution via
    #     CHAIN_NODE_TO_LAYER.
    lit_data = collect_literature_data(conn)
    n_lit = emit_literature_premises(conn, lit_data)
    print(f"[literature] {n_lit} unique citations promoted to premises")

    # 3. Wipe & regenerate per-patient hypotheses + therapeutics for the roster
    #    (we scope by generator_id so re-runs are idempotent across versions).
    conn.execute("DELETE FROM patient_hypothesis WHERE generator_id=? AND generator_version=?",
                 HYP_GENERATOR)
    conn.execute("DELETE FROM patient_therapeutic WHERE generator_id=? AND generator_version=?",
                 AAV_GENERATOR)

    total_h, total_t = 0, 0
    for (cohort, pid) in ROSTER_KEYS:
        row = conn.execute(
            "SELECT phenotype_label, age_years, ambulatory, exon, "
            "       nucleotide, aa_change, consequence, acmg "
            "FROM patient_phenotype WHERE cohort=? AND patient_id=?",
            (cohort, pid),
        ).fetchone()
        if not row:
            print(f"[warn] {cohort}#{pid} not in patient_phenotype")
            continue
        (phen, age, amb, exon, nuc, aa, cons, acmg) = row
        aa = html.unescape(aa) if aa else aa
        nuc = html.unescape(nuc) if nuc else nuc
        n_h, n_t = bake_hypotheses_for_patient(
            conn, cohort, pid, phen, age, amb, exon, nuc, aa, cons, acmg,
            lit_data=lit_data)
        total_h += n_h
        total_t += n_t

    conn.commit()

    # 4. Sanity summary
    n_prem = conn.execute("SELECT COUNT(*) FROM premise").fetchone()[0]
    n_hp   = conn.execute("SELECT COUNT(*) FROM patient_hypothesis").fetchone()[0]
    n_hpp  = conn.execute("SELECT COUNT(*) FROM hypothesis_premise").fetchone()[0]
    n_pt   = conn.execute("SELECT COUNT(*) FROM patient_therapeutic").fetchone()[0]
    print(f"\n[premises] {n_prem:>5} rows (cohort + patient scope)")
    print(f"[patient_hypothesis]    {n_hp:>5} rows ({total_h} freshly baked)")
    print(f"[hypothesis_premise]    {n_hpp:>5} audit-trail rows")
    print(f"[patient_therapeutic]   {n_pt:>5} rows ({total_t} freshly baked)")
    print()

    # Spot-check
    print("Sample: top hypothesis + supporting premises for Patient 5 (S1_novel#5):")
    for row in conn.execute("""
        SELECT h.mechanism_template, h.rank, h.score,
               COUNT(hp.premise_id) as n_premises
        FROM patient_hypothesis h
        LEFT JOIN hypothesis_premise hp ON h.hypothesis_id = hp.hypothesis_id
        WHERE h.patient_id = '5'
        GROUP BY h.hypothesis_id ORDER BY h.rank
    """):
        print(f"  H{row[0]} rank #{row[1]} score {row[2]:.1f} · {row[3]} premises consulted")

    conn.close()


if __name__ == "__main__":
    main()
