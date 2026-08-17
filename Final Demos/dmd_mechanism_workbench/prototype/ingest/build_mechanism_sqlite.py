"""Build data/mechanism.sqlite — the substrate that hydrates workbench/mechanism.html.

Loads real rows from the TSVs the DMD env already produced (LOVD variants,
isoforms, exon-usage) and inserts honestly-labeled stub rows for the
substrate that upstream bakes haven't produced yet (cell-type expression,
pathway enrichment). Zhang et al. 2024 (CC-BY, PMC11344408) provides the
patient-level phenotype substrate — 418 per-patient rows from supp
tables + a 2,097-patient aggregate from the abstract.

Every row carries a `data_source` column tagging its origin:
    'lovd'   — LOVD-DMD variant catalogue
    'zhang2024' — Zhang et al. 2024 (Orphanet J Rare Dis) per-patient rows
    'stub'   — proportional placeholder pending real bake

Curated tables (hypotheses + evidence + chain graph) come from the
HYPOTHESES payload below, which mirrors what workbench/mechanism.html
was rendering inline. Edit HYPOTHESES here to change the workbench.

Run:
    python3 -m prototype.ingest.build_mechanism_sqlite
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "mechanism.sqlite"
VDIR = REPO / "data" / "variants"
ZHANG_DIR = REPO / "data" / "raw" / "zhang2024_supp"

STRUCTURAL = {"del", "dup", "delins", "inv", "complex"}
SNV = {"sub"}

SCHEMA = """
-- SUBSTRATE --------------------------------------------------------------
CREATE TABLE lovd_variants (
  lovd_id           TEXT PRIMARY KEY,
  dbid              TEXT NOT NULL,
  hgvs              TEXT NOT NULL,
  position_mrna     TEXT,
  position_genomic  TEXT,
  mut_type          TEXT NOT NULL,      -- del / sub / dup / etc.
  mut_type_class    TEXT NOT NULL,      -- structural / snv / other
  times_reported    INTEGER,
  published         TEXT,
  updated           TEXT,
  data_source       TEXT NOT NULL       -- 'lovd'
);
CREATE INDEX ix_lovd_dbid    ON lovd_variants(dbid);
CREATE INDEX ix_lovd_class   ON lovd_variants(mut_type_class);
CREATE INDEX ix_lovd_muttype ON lovd_variants(mut_type);

CREATE TABLE isoforms (
  isoform_id                 TEXT PRIMARY KEY,
  refseq_transcript          TEXT NOT NULL,
  uniprot_base               TEXT,
  first_shared_exon          INTEGER NOT NULL,
  promoter_tissue            TEXT,
  primary_expression_tissues TEXT,
  unique_5prime_exon_label   TEXT,
  rank                       INTEGER NOT NULL      -- render order
);

CREATE TABLE exon_usage (
  isoform_id TEXT NOT NULL,
  exon       INTEGER NOT NULL,
  used       INTEGER NOT NULL,
  PRIMARY KEY (isoform_id, exon)
);

-- Per-patient phenotype records. Zhang et al. 2024 supp gives us clean
-- rows for small-sequence-variant patients (S1 = novel, S2 = reported);
-- large del/dup rows aren't published per-patient but are counted in
-- phenotype_summary. Patient IDs are only unique within (source, cohort).
CREATE TABLE patient_phenotype (
  source          TEXT NOT NULL,        -- 'zhang2024'
  cohort          TEXT NOT NULL,        -- 'S1_novel' | 'S2_reported'
  patient_id      TEXT NOT NULL,
  phenotype_label TEXT NOT NULL,        -- DMD / BMD / IMD / pending
  age_years       REAL,
  ambulatory      TEXT,                 -- 'Yes' / 'No' / null
  exon            TEXT,
  nucleotide      TEXT,
  aa_change       TEXT,
  consequence     TEXT,
  acmg            TEXT,
  data_source     TEXT NOT NULL,        -- same as source, kept for uniformity
  PRIMARY KEY (source, cohort, patient_id)
);
CREATE INDEX ix_pp_pheno ON patient_phenotype(phenotype_label);

-- Per-patient clinical labs. Populated by bake_synthetic_labs.py for now
-- (deterministic synthetic values seeded on cohort+patient_id). When real
-- longitudinal labs arrive (registry / CRO handoff), swap the bake step;
-- the schema and downstream consumers are unchanged.
--
-- `layer` maps to the biological-organization hierarchy used in the UI:
-- 'cellType' | 'tissueType' | 'phenotype'. `flag` is derived at bake
-- time so consumers don't have to redo the normal-range comparison.
CREATE TABLE patient_labs (
  cohort      TEXT NOT NULL,
  patient_id  TEXT NOT NULL,
  assay_key   TEXT NOT NULL,             -- 'CK', 'LVEF', ...
  label       TEXT NOT NULL,             -- 'Creatine kinase'
  layer       TEXT NOT NULL,             -- cellType | tissueType | phenotype
  tissue      TEXT,                      -- 'cardiac', 'CNS', 'skeletal', ...
  unit        TEXT NOT NULL,
  value       REAL NOT NULL,
  ref_low     REAL NOT NULL,
  ref_high    REAL NOT NULL,
  flag        TEXT NOT NULL,             -- normal | low | high
  data_source TEXT NOT NULL,             -- 'synthetic_v1' | 'zhang_2024_...' | ...
  PRIMARY KEY (cohort, patient_id, assay_key)
);
CREATE INDEX ix_pl_pat   ON patient_labs(cohort, patient_id);
CREATE INDEX ix_pl_layer ON patient_labs(layer);

-- ======================================================================
-- Premise registry + patient-scoped hypotheses/therapeutics.
-- ----------------------------------------------------------------------
-- Every data source or model that informs the hypothesis world model
-- registers as a `premise_source`. Each patient-specific (or cohort /
-- variant-scoped) piece of evidence lives as a `premise` row. The
-- hypothesis world model consumes premises and emits ranked
-- `patient_hypothesis` rows with an audit trail of which premises fired
-- (via `hypothesis_premise`). Each top-ranked hypothesis emits ≥1
-- `patient_therapeutic` from the AAV design world model, referencing
-- the hypothesis it addresses.
-- ======================================================================

CREATE TABLE premise_source (
  source_id     TEXT PRIMARY KEY,          -- 'aenmd_v1', 'esm3_v1', 'hpa_v1', 'zhang_2024', ...
  source_type   TEXT NOT NULL,             -- 'data' | 'model'
  version       TEXT,
  description   TEXT,
  reference_url TEXT
);

CREATE TABLE premise (
  premise_id    TEXT PRIMARY KEY,          -- unique across all premises
  source_id     TEXT NOT NULL,             -- FK premise_source
  scope         TEXT NOT NULL,             -- 'cohort' | 'patient' | 'variant'
  scope_key     TEXT NOT NULL,             -- 'DMD' or patient_id or variant_key
  evidence      TEXT NOT NULL,             -- JSON blob (typed per source)
  confidence    REAL,                      -- 0..1
  provenance    TEXT NOT NULL              -- JSON: {version, timestamps, cache_paths}
);
CREATE INDEX ix_premise_scope  ON premise(scope, scope_key);
CREATE INDEX ix_premise_source ON premise(source_id);

CREATE TABLE patient_hypothesis (
  hypothesis_id      TEXT PRIMARY KEY,     -- e.g. 'P3:h03:v1'
  patient_id         TEXT NOT NULL,        -- 'P3' etc.
  variant_key        TEXT NOT NULL,        -- 'S2_reported#258:c.9248G>A'
  mechanism_template TEXT,                 -- 'H01'|'H02'|'H03'|'H04'|novel
  rank               INTEGER NOT NULL,     -- 1 = top
  score              REAL NOT NULL,        -- 0..10 (aggregate — legacy scalar)
  confidence         REAL NOT NULL,        -- world-model confidence, distinct from score
  claim              TEXT NOT NULL,        -- patient-specific one-liner
  rationale          TEXT NOT NULL,        -- generated prose explaining the score
  score_vector       TEXT,                 -- JSON: {aggregate, coverage, consistency, parsimony}
  generator_id       TEXT NOT NULL,        -- 'HYP-MODEL v0-scored'
  generator_version  TEXT NOT NULL,
  generated_at       TEXT NOT NULL,        -- ISO timestamp
  input_context_hash TEXT NOT NULL         -- signature of the premises consulted
);
CREATE INDEX ix_ph_patient ON patient_hypothesis(patient_id, rank);
CREATE INDEX ix_ph_variant ON patient_hypothesis(variant_key);

-- Chain-decomposed evidence: attributes each premise to its position in
-- the biological hierarchy (variant → protein → pathway → subcellular →
-- cellType → tissue → phenotype). One row per (hypothesis, chain link,
-- premise). Nodes have layer_from == layer_to; edges have adjacent layers.
CREATE TABLE hypothesis_chain_link (
  hypothesis_id  TEXT NOT NULL,           -- FK patient_hypothesis
  link_type      TEXT NOT NULL,           -- 'node' | 'edge'
  layer_from     TEXT NOT NULL,           -- variant|protein|pathway|subcellular|cellType|tissue|phenotype
  layer_to       TEXT NOT NULL,           -- same as layer_from for nodes
  premise_id     TEXT NOT NULL,           -- FK premise
  weight         REAL NOT NULL,
  rationale      TEXT,
  PRIMARY KEY (hypothesis_id, link_type, layer_from, layer_to, premise_id)
);
CREATE INDEX ix_hcl_hyp   ON hypothesis_chain_link(hypothesis_id);
CREATE INDEX ix_hcl_layer ON hypothesis_chain_link(layer_from, layer_to);

CREATE TABLE hypothesis_premise (
  hypothesis_id TEXT NOT NULL,             -- FK patient_hypothesis
  premise_id    TEXT NOT NULL,             -- FK premise
  weight        REAL NOT NULL,             -- signed contribution to the score
  rationale     TEXT,                      -- one-line "why this premise moved this hyp"
  PRIMARY KEY (hypothesis_id, premise_id)
);

CREATE TABLE patient_therapeutic (
  therapeutic_id     TEXT PRIMARY KEY,     -- e.g. 'P3:h03:aav_readthrough'
  patient_id         TEXT NOT NULL,
  hypothesis_id      TEXT NOT NULL,        -- FK patient_hypothesis
  rank               INTEGER NOT NULL,     -- 1 = top per hypothesis
  score              REAL NOT NULL,
  confidence         REAL NOT NULL,
  modality           TEXT NOT NULL,        -- 'AAV'|'ASO'|'small_molecule'|'readthrough'
  design             TEXT NOT NULL,        -- JSON: capsid, promoter, transgene, dose
  rationale          TEXT NOT NULL,
  eligibility_status TEXT,                 -- 'eligible'|'excluded'|'screening_required'|'unknown'
  generator_id       TEXT NOT NULL,        -- 'AAV-MODEL v0-curated'
  generator_version  TEXT NOT NULL,
  generated_at       TEXT NOT NULL
);
CREATE INDEX ix_pt_patient ON patient_therapeutic(patient_id, rank);
CREATE INDEX ix_pt_hyp     ON patient_therapeutic(hypothesis_id);

-- Cohort-level aggregates. Zhang 2024's abstract publishes total-cohort
-- counts (2,097 patients) that include large-del/dup patients whose
-- per-row data aren't in the supp — those go here.
CREATE TABLE phenotype_summary (
  source          TEXT NOT NULL,        -- 'zhang2024'
  cohort          TEXT NOT NULL,        -- 'total_2097'
  phenotype_label TEXT NOT NULL,        -- DMD / BMD / IMD / pending
  n_patients      INTEGER NOT NULL,
  data_source     TEXT NOT NULL,
  PRIMARY KEY (source, cohort, phenotype_label)
);

CREATE TABLE celltype_expression (
  gene_symbol TEXT NOT NULL,
  source      TEXT NOT NULL,            -- cxg_tabula_sapiens_muscle, ...
  tissue      TEXT,
  cell_type   TEXT NOT NULL,
  score       REAL NOT NULL,            -- log10(1+mean_detected)*10, or similar
  color_hint  TEXT,                     -- palette hint for the tile
  data_source TEXT NOT NULL,
  PRIMARY KEY (gene_symbol, source, cell_type)
);

CREATE TABLE pathway_enrichment (
  gene_symbol  TEXT NOT NULL,
  source       TEXT NOT NULL,           -- reactome / go-bp / kegg
  pathway_id   TEXT NOT NULL,
  pathway_name TEXT NOT NULL,
  score        REAL NOT NULL,           -- -log10(FDR) or membership weight
  color_hint   TEXT,
  data_source  TEXT NOT NULL,
  PRIMARY KEY (gene_symbol, source, pathway_id)
);

-- CURATED ----------------------------------------------------------------
CREATE TABLE hypotheses (
  id                  TEXT PRIMARY KEY, -- '01'..'NN'
  rank                INTEGER NOT NULL,
  name                TEXT NOT NULL,
  subtitle            TEXT,
  supporting_variants INTEGER,
  odds_ratio          REAL,
  evidence_score      REAL,
  druggability        INTEGER,          -- 0..5
  therapeutic         TEXT,
  selected            INTEGER NOT NULL DEFAULT 0,
  lede                TEXT
);

CREATE TABLE hypothesis_evidence (
  hypothesis_id TEXT NOT NULL,
  ord           INTEGER NOT NULL,
  tone          TEXT NOT NULL,          -- 'good' | 'warn'
  text          TEXT NOT NULL,
  citation      TEXT,
  PRIMARY KEY (hypothesis_id, ord)
);

CREATE TABLE hypothesis_chain_nodes (
  hypothesis_id TEXT NOT NULL,
  node_id       TEXT NOT NULL,
  col           INTEGER NOT NULL,
  row           INTEGER NOT NULL,
  tier          TEXT NOT NULL,          -- cause | mechanism | phenotype | therapeutic
  label1        TEXT NOT NULL,
  label2        TEXT,
  meta          TEXT,
  PRIMARY KEY (hypothesis_id, node_id)
);

CREATE TABLE hypothesis_chain_edges (
  hypothesis_id TEXT NOT NULL,
  from_node     TEXT NOT NULL,
  to_node       TEXT NOT NULL,
  PRIMARY KEY (hypothesis_id, from_node, to_node)
);

-- One row per (edge, citation). Multiple rows per edge = multiple
-- supporting refs. Tone matches hypothesis_evidence: 'good' | 'warn'.
CREATE TABLE hypothesis_chain_edge_evidence (
  hypothesis_id TEXT NOT NULL,
  from_node     TEXT NOT NULL,
  to_node       TEXT NOT NULL,
  ord           INTEGER NOT NULL,
  tone          TEXT NOT NULL,
  text          TEXT NOT NULL,
  citation      TEXT,
  PRIMARY KEY (hypothesis_id, from_node, to_node, ord)
);

CREATE TABLE hypothesis_therapeutic_node (
  hypothesis_id TEXT PRIMARY KEY,
  label1        TEXT,
  label2        TEXT
);

-- META -------------------------------------------------------------------
CREATE TABLE gene_meta (
  symbol        TEXT PRIMARY KEY,
  full_name     TEXT NOT NULL,
  uniprot       TEXT,
  locus         TEXT,
  n_exons       INTEGER,
  locus_size_mb REAL,
  isoform_names TEXT                    -- JSON array as string
);

CREATE TABLE settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


def classify_class(mut_type: str) -> str:
    if mut_type in STRUCTURAL:
        return "structural"
    if mut_type in SNV:
        return "snv"
    return "other"


def load_lovd(conn) -> int:
    p = VDIR / "dmd_variants_raw.tsv"
    n = 0
    with p.open() as f:
        r = csv.DictReader(f, delimiter="\t")
        batch: list[tuple] = []
        for x in r:
            mt = x["mut_type"]
            times_raw = x.get("times_reported", "") or ""
            times = int(times_raw) if times_raw.isdigit() else None
            batch.append((
                x["lovd_id"], x["dbid"], x["hgvs"],
                x["position_mrna"] or None, x["position_genomic"] or None,
                mt, classify_class(mt), times,
                x["published"] or None, x["updated"] or None,
                "lovd",
            ))
            if len(batch) == 2000:
                conn.executemany(
                    "INSERT INTO lovd_variants VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch)
                n += len(batch); batch.clear()
        if batch:
            conn.executemany(
                "INSERT INTO lovd_variants VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch)
            n += len(batch)
    return n


def load_isoforms(conn) -> int:
    p = VDIR / "dmd_isoforms.tsv"
    n = 0
    with p.open() as f:
        r = csv.DictReader(f, delimiter="\t")
        for rank, x in enumerate(r):
            conn.execute("INSERT INTO isoforms VALUES (?,?,?,?,?,?,?,?)", (
                x["isoform_id"], x["refseq_transcript"], x["uniprot_base"],
                int(x["first_shared_exon"]), x["promoter_tissue"],
                x["primary_expression_tissues"], x["unique_5prime_exon_label"],
                rank,
            ))
            n += 1
    return n


def load_exon_usage(conn) -> int:
    p = VDIR / "dmd_exon_usage.tsv"
    n = 0
    with p.open() as f:
        r = csv.DictReader(f, delimiter="\t")
        for x in r:
            conn.execute("INSERT INTO exon_usage VALUES (?,?,?)",
                         (x["isoform_id"], int(x["exon"]), int(x["used"])))
            n += 1
    return n


def _docx_first_table(path: Path) -> list[list[str]]:
    """Return the first <w:tbl> in a .docx as a list of rows of cell text."""
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8', errors='replace')
    m = re.search(r'<w:tbl>.*?</w:tbl>', xml, re.S)
    if not m:
        return []
    out = []
    for row in re.findall(r'<w:tr[^>]*>.*?</w:tr>', m.group(0), re.S):
        cells = []
        for tc in re.findall(r'<w:tc>.*?</w:tc>', row, re.S):
            texts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', tc)
            cells.append(''.join(texts).strip())
        out.append(cells)
    return out


def _norm_pheno(raw: str) -> str:
    """Zhang uses DMD / BMD / IMD / pending — normalise casing."""
    r = (raw or '').strip()
    if r.upper() in {'DMD', 'BMD', 'IMD'}:
        return r.upper()
    return 'pending' if r.lower() == 'pending' else r or 'pending'


def load_zhang_patient_phenotype(conn) -> int:
    """Parse Zhang 2024 Tables S1 (novel) + S2 (reported) into patient_phenotype."""
    files = [
        ('S1_novel',    ZHANG_DIR / 'S1_novel_variants.docx'),
        ('S2_reported', ZHANG_DIR / 'S2_reported_variants.docx'),
    ]
    n = 0
    for cohort, path in files:
        rows = _docx_first_table(path)
        if not rows: continue
        for r in rows[1:]:                       # skip header
            if not r or not r[0].strip().isdigit():
                continue                         # skip blank/footnote rows
            # S1 has 12 cols, S2 has 13 (extra 'References'). Cells align on the left.
            pid   = r[0].strip()
            pheno = _norm_pheno(r[1] if len(r) > 1 else '')
            def num(x):
                try: return float(x)
                except (ValueError, TypeError): return None
            age  = num(r[2]) if len(r) > 2 else None
            ambu = (r[4].strip() if len(r) > 4 else None) or None
            exon = (r[7].strip() if len(r) > 7 else None) or None
            nuc  = (r[8].strip() if len(r) > 8 else None) or None
            aa   = (r[9].strip() if len(r) > 9 else None) or None
            csq  = (r[10].strip() if len(r) > 10 else None) or None
            acmg = (r[11].strip() if len(r) > 11 else None) or None
            conn.execute(
                "INSERT OR REPLACE INTO patient_phenotype VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ('zhang2024', cohort, pid, pheno, age, ambu, exon, nuc, aa, csq, acmg,
                 'zhang2024'),
            )
            n += 1
    return n


def load_zhang_phenotype_summary(conn) -> int:
    """Aggregate cohort counts from Zhang 2024's abstract (2,097 patients total)."""
    rows = [
        ('zhang2024', 'total_2097', 'DMD',     1703, 'zhang2024'),
        ('zhang2024', 'total_2097', 'BMD',      311, 'zhang2024'),
        ('zhang2024', 'total_2097', 'IMD',       46, 'zhang2024'),
        ('zhang2024', 'total_2097', 'pending',   37, 'zhang2024'),
    ]
    conn.executemany("INSERT INTO phenotype_summary VALUES (?,?,?,?,?)", rows)
    return len(rows)


def stub_celltype_expression(conn) -> int:
    rows = [
        ("DMD", "cxg_tabula_sapiens_muscle", "skeletal_muscle", "Skeletal myocyte", 9.6, "accent", "stub"),
        ("DMD", "cxg_heart_atlas",           "heart",           "Cardiomyocyte",    8.2, "accent", "stub"),
        ("DMD", "cxg_brain",                 "cortex",          "Cortical neuron",  6.1, "violet", "stub"),
        ("DMD", "cxg_brain",                 "cerebellum",      "Purkinje cell",    5.4, "violet", "stub"),
        ("DMD", "cxg_retina",                "retina",          "Photoreceptor",    4.8, "pink",   "stub"),
        ("DMD", "cxg_pns",                   "sciatic_nerve",   "Schwann cell",     3.1, "teal",   "stub"),
        ("DMD", "cxg_kidney",                "kidney",          "Kidney podocyte",  2.2, "slate",  "stub"),
    ]
    conn.executemany("INSERT INTO celltype_expression VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)


# pathway_enrichment is left empty here — populated by bake_pathways.py,
# which fetches Reactome and writes DMD-scored rows into this same table.


# ---- Curated hypothesis payload (mirrors the JS DATA.hypotheses shape) ----
HYPOTHESES = [
    {
        "id": "01", "rank": 1,
        "name": "Out-of-frame deletions → truncated dystrophin → sarcolemmal fragility",
        "subtitle": "Monaco rule; loss of C-terminal DGC anchor; membrane tears → Ca²⁺ influx → necrosis",
        "supporting": 18204, "or": 14.2, "evidence": 9.4, "drug": 4,
        "therapeutic": "Exon-skipping ASOs (Dp427m rescue); micro-dystrophin gene therapy",
        "selected": 1,
        "lede": ("Out-of-frame deletions in DMD ablate the C-terminal dystroglycan-binding domain, "
                 "decoupling the sarcolemma from the extracellular matrix. Contraction stress produces "
                 "membrane micro-tears, unregulated Ca²⁺ influx activates calpain and disrupts "
                 "mitochondrial handling, triggering necrosis and progressive fibro-fatty replacement."),
        "evidence_list": [
            ("good", "Monaco reading-frame rule: 90% of out-of-frame → DMD; 91% of in-frame → BMD", "Monaco 1988"),
            ("good", "LOVD: 18,204 out-of-frame deletion entries vs 4,822 in-frame (matches 68% severe rate)", "LOVD-DMD 2026"),
            ("good", "Dystrophin-null mdx muscle: elevated resting [Ca²⁺]ᵢ and calpain activation", "Turner 1988; Alderton 2000"),
            ("good", "Membrane sealants (poloxamer-188) reduce sarcolemmal damage in mdx / GRMD", "Yasuda 2005"),
            ("good", "Micro-dystrophin (rAAV) restores DGC + delays fibrosis in Phase III", "Mendell 2020; ELEVIDYS 2023"),
            ("good", "Exon-51 skipping (eteplirsen) restores in-frame Dp427m in ~13% of pts", "Mendell 2013"),
            ("warn", "Frame-rule exception: Δexon 5 in-frame → severe DMD via aberrant splicing", "Aartsma-Rus 2006"),
        ],
        "chain_nodes": [
            ("v1", 0, 0, "cause",     "Out-of-frame",    "deletion",             "LOVD n=18,204"),
            ("v2", 1, 0, "cause",     "Premature stop",  "codon",                "NMD-eligible"),
            ("v3", 2, 0, "cause",     "Truncated /",     "absent dystrophin",    "no C-term DGC anchor"),
            ("m1", 2, 1, "mechanism", "Sarcolemma",      "decouples from ECM",   "membrane micro-tears"),
            ("m2", 1, 1, "mechanism", "Ca²⁺ influx +",   "calpain activation",   "contraction stress"),
            ("m3", 0, 1, "mechanism", "Mitochondrial",   "dysfunction",          "ROS, Δψₘ collapse"),
            ("p1", 0, 2, "phenotype", "Myofiber",        "necrosis",             "CK release, inflammation"),
            ("p2", 1, 2, "phenotype", "Failed regen. /", "satellite exhaustion", "TGF-β elevation"),
            ("p3", 2, 2, "phenotype", "Fibro-fatty",     "replacement",          "progressive weakness"),
        ],
        "chain_edges": [
            ("v1","v2"), ("v2","v3"), ("v3","m1"),
            ("m1","m2"), ("m2","m3"), ("m3","p1"),
            ("p1","p2"), ("p2","p3"),
        ],
        # Per-edge evidence — the "why does A imply B" that lives between
        # the top-level bullets and the chain diagram. Curated first pass.
        # Each edge gets 1-3 citations; tone matches hypothesis_evidence.
        "chain_edge_evidence": [
            # v1 → v2  Out-of-frame deletion → premature stop codon
            ("v1", "v2", "good", "Frameshift produced by exon deletion introduces a PTC downstream, on average within ~200 codons.", "Aartsma-Rus 2006"),
            ("v1", "v2", "good", "Reading-frame rule: deletion produces a PTC unless total deleted length ≡ 0 mod 3.", "Monaco 1988"),

            # v2 → v3  PTC → truncated / absent dystrophin
            ("v2", "v3", "good", "Nonsense-mediated decay degrades transcripts with a PTC ≥50 nt upstream of the last exon-exon junction.", "Popp & Maquat 2013"),
            ("v2", "v3", "good", "Western blot of DMD muscle: <3% dystrophin detected in PTC-carrying patients.", "Hoffman 1988"),

            # v3 → m1  Absent dystrophin → sarcolemma decouples from ECM
            ("v3", "m1", "good", "Dystrophin C-terminal domain binds β-dystroglycan, bridging cytoskeletal actin to sarcolemmal laminin via the DGC.", "Ervasti & Campbell 1993"),
            ("v3", "m1", "good", "In dystrophin-null mdx muscle, DGC components (β-DG, sarcoglycans, nNOS) dissociate from the sarcolemma.", "Ohlendieck 1991"),

            # m1 → m2  Sarcolemma decouples → Ca²⁺ influx + calpain
            ("m1", "m2", "good", "Contraction-induced micro-tears in mdx sarcolemma admit extracellular Ca²⁺ down its steep gradient.", "Petrof 1993"),
            ("m1", "m2", "good", "Calpain-1 is activated by elevated cytosolic [Ca²⁺] and proteolyses a broad set of sarcomeric + membrane substrates.", "Alderton 2000"),

            # m2 → m3  Ca²⁺ + calpain → mitochondrial dysfunction
            ("m2", "m3", "good", "Sustained Ca²⁺ overload opens the mitochondrial permeability transition pore, collapsing ΔΨₘ and triggering ROS.", "Millay 2008"),
            ("m2", "m3", "good", "Mdx mitochondria show reduced membrane potential and elevated superoxide output under contractile load.", "Vila 2017"),

            # m3 → p1  Mito dysfunction → myofiber necrosis
            ("m3", "p1", "good", "Cyclophilin-D knockout (blocks MPTP opening) rescues necrosis in mdx muscle.", "Millay 2008"),
            ("m3", "p1", "good", "Elevated serum creatine kinase is a clinical proxy for ongoing sarcolemmal permeability + necrosis in DMD.", "Zatz 2016"),

            # p1 → p2  Necrosis → failed regen / satellite exhaustion
            ("p1", "p2", "good", "Serial injury cycles deplete the satellite-cell pool via replicative senescence.", "Sacco 2010"),
            ("p1", "p2", "good", "Mdx satellite cells show telomere shortening and impaired self-renewal by late disease.", "Dumont 2015"),

            # p2 → p3  Failed regen → fibro-fatty replacement
            ("p2", "p3", "good", "Fibro-adipogenic progenitors expand and differentiate when muscle regeneration fails, replacing myofibers with fat + collagen.", "Uezumi 2010"),
            ("p2", "p3", "good", "TGF-β signalling drives fibrotic ECM deposition in DMD muscle biopsies.", "Bernasconi 1995"),
        ],
        "therapy": ("Therapeutic entry: exon skipping · micro-dystrophin AAV",
                    "restores in-frame Dp427m or delivers truncated functional protein"),
    },
    {
        "id": "02", "rank": 2,
        "name": "In-frame deletions → partial-function dystrophin → BMD phenotype",
        "subtitle": "Central-rod deletion retains N-term + DGC; slower progression, later onset",
        "supporting": 4822, "or": 3.6, "evidence": 8.7, "drug": 3,
        "therapeutic": "Small-molecule stabilizers (utrophin upregulation); guides ASO target selection",
        "selected": 0,
        "lede": ("In-frame deletions in the central rod domain remove spectrin-like repeats "
                 "but preserve the N-terminal actin-binding domain and the C-terminal DGC anchor. "
                 "A shortened but functional dystrophin still couples the sarcolemma to the ECM, "
                 "yielding reduced but non-zero membrane stability — the biological basis of BMD's "
                 "later onset and slower progression."),
        "evidence_list": [
            ("good", "Monaco reading-frame rule: 91% of in-frame deletions → BMD phenotype", "Monaco 1988"),
            ("good", "Δexons 45–47 (in-frame, spectrin repeats 17-19) → BMD with ambulation to 40s+", "Beggs 1991"),
            ("good", "Truncated dystrophin visualized on Western in BMD muscle at ~50–80% wild-type levels", "Hoffman 1988"),
            ("good", "Micro-dystrophin (Δrod) rescue in mdx approximates the BMD state", "Wang 2000"),
            ("warn", "Some large in-frame deletions (Δexons 3–41) still produce severe DMD — position matters", "Nicholson 1993"),
        ],
        "chain_nodes": [
            ("v1", 0, 0, "cause",     "In-frame",         "deletion",              "≡0 mod 3"),
            ("v2", 1, 0, "cause",     "Central-rod",      "spectrin loss",         "N-term + DGC preserved"),
            ("v3", 2, 0, "cause",     "Shortened but",    "functional dystrophin", "50–80% WT level"),
            ("m1", 2, 1, "mechanism", "Partial DGC",      "assembly",              "sarcolemma anchored"),
            ("m2", 1, 1, "mechanism", "Reduced membrane", "rigidity",              "residual susceptibility"),
            ("m3", 0, 1, "mechanism", "Gradual Ca²⁺",     "leak",                  "not acute"),
            ("p1", 0, 2, "phenotype", "Slower muscle",    "loss",                  "wheelchair ~40y+"),
            ("p2", 1, 2, "phenotype", "Preserved",        "ambulation",            "milder cardiac"),
            ("p3", 2, 2, "phenotype", "BMD",              "phenotype",             "late onset"),
        ],
        "chain_edges": [
            ("v1","v2"), ("v2","v3"), ("v3","m1"),
            ("m1","m2"), ("m2","m3"), ("m3","p1"),
            ("p1","p2"), ("p2","p3"),
        ],
        "chain_edge_evidence": [
            ("v1","v2","good", "In-frame indels remove spectrin repeats without shifting the reading frame; typical central-rod deletions span exons 45–55.", "Aartsma-Rus 2006"),
            ("v2","v3","good", "Shortened dystrophin retains the N-terminal actin-binding domain and the C-terminal β-DG binding domain.", "Ervasti & Campbell 1993"),
            ("v3","m1","good", "DGC assembles around a partial dystrophin; sarcoglycans + β-DG remain at the sarcolemma at reduced levels.", "Ohlendieck 1993"),
            ("m1","m2","good", "Partial DGC bears mechanical load but with reduced fidelity — subclinical membrane injury still occurs.", "Petrof 1993"),
            ("m2","m3","good", "Low-grade Ca²⁺ leak produces slower calpain activation and delayed cellular damage.", "Alderton 2000"),
            ("m3","p1","good", "BMD muscle biopsies show necrosis foci at lower density than DMD — regeneration keeps pace longer.", "Bushby 1993"),
            ("p1","p2","good", "BMD patients often retain ambulation into their 30s–40s; cardiomyopathy still develops but later.", "Bushby 1993"),
            ("p2","p3","good", "The clinical BMD label is applied when ambulation is retained past age 16.", "Emery & Skinner 1976"),
        ],
        "therapy": ("Therapeutic entry: utrophin upregulation · exon-skipping toward in-frame",
                    "convert DMD reading-frame to a BMD-like partial rescue"),
    },
    {
        "id": "03", "rank": 3,
        "name": "Nonsense / splice variants → NMD → tissue-graded transcript loss",
        "subtitle": "Premature stop triggers surveillance; cardiac + brain isoforms less rescued",
        "supporting": 7411, "or": 6.1, "evidence": 7.2, "drug": 2,
        "therapeutic": "Readthrough agents (ataluren); NMD inhibitors under investigation",
        "selected": 0,
        "lede": ("Nonsense mutations and canonical splice-site variants create a premature termination "
                 "codon (PTC). Transcripts with a PTC ≥50 nt upstream of the last exon-exon junction are "
                 "degraded by nonsense-mediated decay (NMD), yielding near-total dystrophin loss. NMD "
                 "efficiency varies across tissues, so cardiac and brain-restricted isoforms sometimes "
                 "retain trace expression — a tissue-graded loss pattern."),
        "evidence_list": [
            ("good", "PTC ≥50 nt upstream of last EEJ triggers NMD in mammalian cells", "Popp & Maquat 2013"),
            ("good", "Nonsense-variant DMD muscle: <3% dystrophin by Western blot", "Hoffman 1988"),
            ("good", "Ataluren (Translarna) promotes ribosomal readthrough of PTC codons → partial rescue", "Bushby 2014"),
            ("good", "Splice-site variants generate downstream PTC in ~70% of cases (via exon skipping or intron retention)", "Aartsma-Rus 2006"),
            ("warn", "NMD efficiency varies 2–5× across tissues; brain + cardiac often show partial escape", "Linde 2007"),
        ],
        "chain_nodes": [
            ("v1", 0, 0, "cause",     "Nonsense or",      "splice-site variant",   "creates PTC"),
            ("v2", 1, 0, "cause",     "PTC ≥50 nt",       "upstream of last EEJ",  "NMD-eligible"),
            ("v3", 2, 0, "cause",     "NMD degrades",     "mutant transcript",     "protein absent"),
            ("m1", 2, 1, "mechanism", "Total Dp427m",     "loss in muscle",        "no functional rescue"),
            ("m2", 1, 1, "mechanism", "Tissue-graded",    "NMD escape",            "brain/cardiac partial"),
            ("m3", 0, 1, "mechanism", "Readthrough",      "opportunity",           "context-dependent"),
            ("p1", 0, 2, "phenotype", "Severe muscle",    "phenotype (DMD)",       "progressive loss"),
            ("p2", 1, 2, "phenotype", "Milder brain +",   "cardiac course",        "if isoform escapes"),
            ("p3", 2, 2, "phenotype", "Ataluren",         "responsive subset",     "PTC-context dependent"),
        ],
        "chain_edges": [
            ("v1","v2"), ("v2","v3"), ("v3","m1"),
            ("m1","m2"), ("m2","m3"), ("m3","p1"),
            ("p1","p2"), ("p2","p3"),
        ],
        "chain_edge_evidence": [
            ("v1","v2","good", "Nonsense codons directly encode a PTC; splice-site variants produce a PTC via exon skipping or intron retention.", "Aartsma-Rus 2006"),
            ("v2","v3","good", "The exon-junction complex marks a PTC as NMD-eligible when it lies ≥50 nt upstream of the terminal EEJ.", "Popp & Maquat 2013"),
            ("v3","m1","good", "NMD reduces mutant mRNA levels to ~5-15% of wild-type in patient muscle biopsies.", "Kerr 2001"),
            ("m1","m2","good", "NMD activity varies by tissue and transcript context; brain isoforms show partial NMD escape.", "Linde 2007"),
            ("m2","m3","good", "PTC codons in favorable sequence contexts are susceptible to pharmacological readthrough (aminoglycosides, ataluren).", "Welch 2007"),
            ("m3","p1","good", "Muscle NMD is efficient → near-total Dp427m loss → severe DMD phenotype indistinguishable from deletion carriers.", "Flanigan 2009"),
            ("p1","p2","good", "Cardiac + CNS symptoms track residual isoform expression; partial NMD escape can soften those phenotypes.", "Bello 2016"),
            ("p2","p3","good", "Ataluren approval (EMA 2014) requires a nonsense mutation genotype; ~13% of DMD patients are eligible.", "Bushby 2014"),
        ],
        "therapy": ("Therapeutic entry: ataluren readthrough · NMD-inhibitor combinations",
                    "restore partial protein production from PTC-containing mRNA"),
    },
    {
        "id": "04", "rank": 4,
        "name": "Distal-promoter variants → tissue-specific isoform loss (Dp140/Dp71)",
        "subtitle": "5′-restricted lesions spare muscle but ablate CNS/retinal isoforms — cognitive/ERG phenotype",
        "supporting": 612, "or": 2.4, "evidence": 6.5, "drug": 1,
        "therapeutic": "Isoform-selective replacement (AAV with tissue-restricted promoter)",
        "selected": 0,
        "lede": ("Variants in the 3′ half of DMD (exons 45–79) or in the internal promoters of Dp140, "
                 "Dp116, and Dp71 selectively ablate the shorter isoforms while sparing Dp427m in skeletal "
                 "and cardiac muscle. Patients with these variants often present with cognitive impairment, "
                 "retinal ERG abnormalities, or kidney phenotypes, but with preserved motor function — an "
                 "isoform-scoped disease pattern distinct from classical DMD."),
        "evidence_list": [
            ("good", "Dp71 knockout in mice: ubiquitous but subtle phenotypes (retinal ERG, kidney podocyte)", "Cohn 1999"),
            ("good", "DMD patients with distal deletions have lower IQ, correlated with Dp140 loss", "Ricotti 2016"),
            ("good", "Dp260 (retinal) loss → negative ERG b-wave — a clinical marker of DMD", "Pillers 1993"),
            ("good", "Dp116 loss in Schwann cells → subtle peripheral nerve conduction changes", "Byers 1993"),
            ("warn", "Cohort is small (n=612 in LOVD) — statistical power for isoform-phenotype mapping is limited", "LOVD-DMD 2026"),
        ],
        "chain_nodes": [
            ("v1", 0, 0, "cause",     "Variant in distal", "5′ region (ex ≥45)",  "or internal promoter"),
            ("v2", 1, 0, "cause",     "Dp427m spared",     "in muscle",           "skeletal + cardiac unaffected"),
            ("v3", 2, 0, "cause",     "Dp140/Dp116/Dp71",  "selectively ablated", "CNS + kidney + Schwann affected"),
            ("m1", 2, 1, "mechanism", "CNS dystrophin",    "loss (Dp140/Dp71)",   "cortical + glial"),
            ("m2", 1, 1, "mechanism", "Retinal dystrophin", "loss (Dp260/Dp71)",  "photoreceptor synapse"),
            ("m3", 0, 1, "mechanism", "Kidney podocyte",   "dystrophin loss (Dp71)", "glomerular signaling"),
            ("p1", 0, 2, "phenotype", "Preserved motor",   "function",            "muscle-sparing"),
            ("p2", 1, 2, "phenotype", "Cognitive",         "deficits",            "IQ reduction ~10 pts"),
            ("p3", 2, 2, "phenotype", "Retinal ERG",       "abnormalities",       "negative b-wave"),
        ],
        "chain_edges": [
            ("v1","v2"), ("v1","v3"), ("v3","m1"),
            ("v3","m2"), ("v3","m3"), ("v2","p1"),
            ("m1","p2"), ("m2","p3"),
        ],
        "chain_edge_evidence": [
            ("v1","v2","good", "Distal variants (exon ≥45) fall downstream of Dp427m's transcribed region only when they lie in later exons; Dp427m's promoter and full-length mRNA remain intact.", "Muntoni 2003"),
            ("v1","v3","good", "Dp140's promoter is in intron 44; Dp71's promoter is in intron 62. Variants distal to these ablate specific isoforms.", "Byers 1993"),
            ("v3","m1","good", "Dp140 is the dominant dystrophin isoform in cortical astrocytes; Dp71 supports ubiquitous CNS expression.", "Lidov 1995"),
            ("v3","m2","good", "Dp260 is the retina-specific isoform; Dp71 provides retinal backup expression.", "Pillers 1993"),
            ("v3","m3","good", "Dp71 is expressed in podocytes and glomerular capillaries; loss correlates with albuminuria in mdx variants.", "Haenggi 2006"),
            ("v2","p1","good", "Dp427m preserved → sarcolemmal DGC intact → skeletal + cardiac muscle spared from progressive dystrophy.", "Muntoni 2003"),
            ("m1","p2","good", "Patients with variants ablating Dp140 show cognitive IQ deficits averaging ~10 points below patients with Dp140-sparing variants.", "Ricotti 2016"),
            ("m2","p3","good", "Retinal loss of Dp260 produces a negative-configuration b-wave on scotopic ERG — a clinical marker of DMD retinal involvement.", "Pillers 1993"),
        ],
        "therapy": ("Therapeutic entry: isoform-selective AAV replacement",
                    "deliver Dp140/Dp71 mini-genes under tissue-restricted promoters"),
    },
]


def load_hypotheses(conn) -> int:
    for h in HYPOTHESES:
        conn.execute(
            """INSERT INTO hypotheses (id, rank, name, subtitle, supporting_variants,
               odds_ratio, evidence_score, druggability, therapeutic, selected, lede)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (h["id"], h["rank"], h["name"], h["subtitle"], h["supporting"],
             h["or"], h["evidence"], h["drug"], h["therapeutic"], h["selected"], h["lede"]),
        )
        for ord_, (tone, text, cite) in enumerate(h["evidence_list"]):
            conn.execute("INSERT INTO hypothesis_evidence VALUES (?,?,?,?,?)",
                         (h["id"], ord_, tone, text, cite))
        for (nid, col, row_, tier, l1, l2, meta) in h["chain_nodes"]:
            conn.execute("INSERT INTO hypothesis_chain_nodes VALUES (?,?,?,?,?,?,?,?)",
                         (h["id"], nid, col, row_, tier, l1, l2, meta))
        for (a, b) in h["chain_edges"]:
            conn.execute("INSERT INTO hypothesis_chain_edges VALUES (?,?,?)",
                         (h["id"], a, b))
        # Per-edge evidence rows use a rolling ord per edge (idempotent
        # within (hid, from, to)). Order preserved by source list.
        edge_ord: dict[tuple[str, str], int] = {}
        for (a, b, tone, text, cite) in h["chain_edge_evidence"]:
            key = (a, b)
            ord_ = edge_ord.get(key, 0)
            edge_ord[key] = ord_ + 1
            conn.execute(
                "INSERT INTO hypothesis_chain_edge_evidence VALUES (?,?,?,?,?,?,?)",
                (h["id"], a, b, ord_, tone, text, cite),
            )
        if h["therapy"]:
            conn.execute("INSERT INTO hypothesis_therapeutic_node VALUES (?,?,?)",
                         (h["id"], h["therapy"][0], h["therapy"][1]))
    return len(HYPOTHESES)


def load_meta(conn) -> None:
    isoform_names = json.dumps(["Dp427m", "Dp427c", "Dp427p", "Dp260", "Dp140", "Dp116", "Dp71"])
    conn.execute("INSERT INTO gene_meta VALUES (?,?,?,?,?,?,?)",
                 ("DMD", "Duchenne Muscular Dystrophy", "P11532", "Xp21.2",
                  79, 2.4, isoform_names))
    conn.executemany("INSERT INTO settings VALUES (?,?)", [
        ("mechanism_confidence", "87"),  # placeholder until computed
    ])


def main() -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)

    n_lovd = load_lovd(conn)
    n_iso  = load_isoforms(conn)
    n_exu  = load_exon_usage(conn)
    n_pp   = load_zhang_patient_phenotype(conn)
    n_ps   = load_zhang_phenotype_summary(conn)
    n_ce   = stub_celltype_expression(conn)
    n_hy   = load_hypotheses(conn)
    load_meta(conn)
    conn.commit()

    print(f"[real]    lovd_variants        {n_lovd:>7,}")
    print(f"[real]    isoforms             {n_iso:>7,}")
    print(f"[real]    exon_usage           {n_exu:>7,}")
    print(f"[real]    patient_phenotype    {n_pp:>7,}  (Zhang 2024 supp S1+S2)")
    print(f"[real]    phenotype_summary    {n_ps:>7,}  (Zhang 2024 abstract, N=2,097)")
    print(f"[stub]    celltype_expression  {n_ce:>7,}")
    print(f"[empty]   pathway_enrichment       0  (populated by bake_pathways)")
    print(f"[curated] hypotheses           {n_hy:>7,}")
    print(f"[wrote]   {DB}  ({DB.stat().st_size / 1e6:.1f} MB)")
    conn.close()


if __name__ == "__main__":
    main()
