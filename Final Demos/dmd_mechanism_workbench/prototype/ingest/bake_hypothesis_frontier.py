"""Bake the DMD hypothesis frontier: full cross-product of
(Zhang patients × mechanism families × top-N pathways × top-N cell types),
scored on three objectives, pareto-masked within-patient + globally.

This is the "world-model instantiated at all combinations" table that
powers the pareto-scatter view. Each row is a candidate hypothesis; the
non-dominated subset flagged `is_pareto_global` is what the UI plots.
The LLM-composition step (later) only writes prose for a small subset of
frontier anchors — this bake is pure deterministic scoring, no LLM calls.

Row shape:
  hypothesis_id, cohort, patient_id, patient_label, mechanism_family,
  variant_key, variant_exon,
  pathway_id, pathway_name, pathway_source,
  cell_type, tissue, dgc_completeness,
  predicted_phenotypes (JSON list), observed_phenotypes (JSON list),
  coverage, depth, actionability,
  is_pareto_within_patient, is_pareto_global

Cross-product size: 10 × 4 × 20 × 20 = 16,000 rows (trimmed).
Change TOP_N_PATHWAYS / TOP_N_CELL_TYPES to scale.

Run:
    ~/venv/bin/python -m prototype.ingest.bake_hypothesis_frontier
"""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "mechanism.sqlite"
PATHWAYS_DB = REPO / "data" / "pathways.sqlite"
LAB_MAP_TSV = REPO / "data" / "variants" / "lab_phenotype_map.tsv"

# Trim caps. 10 × 4 × TOP_N_PATHWAYS × TOP_N_CELL_TYPES rows total.
TOP_N_PATHWAYS   = 20
TOP_N_CELL_TYPES = 20

MECH_FAMILIES = [
    ("01", "Out-of-frame LoF → NMD → sarcolemmal fragility"),
    ("02", "In-frame truncation → BMD-like partial function"),
    ("03", "NMD-driven tissue-graded transcript loss"),
    ("04", "Distal-isoform / promoter loss (Dp140/Dp71)"),
]

# 14 DGC members (mirrors bake_hypotheses_and_premises.DGC_MEMBERS).
DGC_MEMBERS = ("DMD", "DAG1", "SNTA1", "SNTB1", "SNTB2",
               "SGCA", "SGCB", "SGCD", "SGCG",
               "DTNA", "DTNB", "UTRN", "CAV3", "SSPN")

# Clinical-tissue-relevance weights (mirrors hydrate_mechanism_view).
TISSUE_RELEVANCE = {
    "skeletal_muscle": 1.00, "heart": 0.95, "cns": 0.60,
    "retina": 0.55, "peripheral_nerve": 0.30, "smooth_muscle": 0.30,
    "vascular": 0.25, "kidney": 0.20, "liver": 0.15, "adipose": 0.10,
    "salivary_gland": 0.05, "breast": 0.05, "prostate": 0.05,
    "thymus": 0.00, "other": 0.15,
}

# Per-phenotype severity (0=none, 5=life-threatening). Drives the
# severity-weighted fit score AND the "predicts severe phenotype"
# highlight in the pareto viz. Sourced from DMD natural-history:
# respiratory failure + cardiomyopathy are the two leading causes of
# death; loss of ambulation is the major functional milestone;
# retinal/renal are sub-clinical in most patients.
PHENOTYPE_SEVERITY = {
    "respiratory_failure":                    5,
    "cardiac_dysfunction":                    5,
    "skeletal_muscle_fibro_fatty_replacement": 4,
    "functional_impairment_ambulatory":       4,
    "cardiac_fibrosis":                       4,
    "cardiac_muscle_injury":                  3,
    "skeletal_muscle_myonecrosis":            3,
    "cns_cognitive":                          2,
    "renal_dysfunction":                      2,
    "retinal_dysfunction":                    1,
}
SEVERE_THRESHOLD = 4     # phenotype-severity >= 4 marks a hypothesis as "severe-predicting"

# Tissue → phenotype-node predictions. Each cell type in a tissue is
# taken to predict this set of phenotype nodes. Multi-phenotype tissues
# (muscle → myonecrosis + fibro-fat + ambulation) are the norm here.
TISSUE_TO_PHENOTYPES = {
    "skeletal_muscle": ["skeletal_muscle_myonecrosis",
                        "skeletal_muscle_fibro_fatty_replacement",
                        "functional_impairment_ambulatory",
                        "respiratory_failure"],
    "heart":           ["cardiac_muscle_injury", "cardiac_dysfunction",
                        "cardiac_fibrosis"],
    "retina":          ["retinal_dysfunction"],
    "cns":             ["cns_cognitive"],
    "kidney":          ["renal_dysfunction"],
    # Tissues below have no direct phenotype node in the lab map.
    "peripheral_nerve": [], "smooth_muscle": [], "vascular": [],
    "liver": [], "adipose": [], "salivary_gland": [],
    "breast": [], "prostate": [], "thymus": [], "other": [],
}

# FDA-approved exon-skipping ASOs (mirrors bake_hypotheses_and_premises).
FDA_APPROVED_SKIPS = {45, 51, 53}

# Roster labels (mirrors bake_hypotheses_and_premises.ROSTER_LABELS).
ROSTER_KEYS = [
    ("S1_novel", "2"), ("S1_novel", "30"), ("S2_reported", "258"),
    ("S1_novel", "57"), ("S1_novel", "5"), ("S1_novel", "11"),
    ("S2_reported", "202"), ("S2_reported", "225"),
    ("S1_novel", "49"), ("S2_reported", "266"),
]
ROSTER_LABELS = {k: f"P{i}" for i, k in enumerate(ROSTER_KEYS, start=1)}


SCHEMA = """
DROP TABLE IF EXISTS hypothesis_frontier;
CREATE TABLE IF NOT EXISTS hypothesis_frontier (
  hypothesis_id           TEXT PRIMARY KEY,
  cohort                  TEXT NOT NULL,
  patient_id              TEXT NOT NULL,
  patient_label           TEXT NOT NULL,
  mechanism_family        TEXT NOT NULL,
  mechanism_desc          TEXT NOT NULL,
  variant_key             TEXT NOT NULL,
  variant_exon            INTEGER,
  variant_hgvsc           TEXT,
  variant_hgvsp           TEXT,
  pathway_id              TEXT,
  pathway_name            TEXT,
  pathway_source          TEXT,
  pathway_dgc_coverage    REAL,
  cell_type               TEXT,
  tissue                  TEXT,
  cell_dgc_completeness   REAL,
  cell_tissue_relevance   REAL,
  predicted_phenotypes    TEXT,      -- JSON list
  observed_phenotypes     TEXT,      -- JSON list (patient-specific)
  n_predicted             INTEGER,
  n_observed              INTEGER,
  n_intersect             INTEGER,
  coverage                REAL,       -- precision of predicted vs observed (legacy)
  depth                   INTEGER,    -- integer count (legacy)
  actionability           INTEGER,    -- therapeutic grade (0..3)  (legacy)
  weighted_fit            REAL,       -- CONTINUOUS: Σ (severity × |z-score| × 1[observed]) / Σ (severity)
  therapeutic_reach       REAL,       -- CONTINUOUS: (act/3) × HPA_DMD_in_cell × tissue_relevance × delivery_prior
  confidence              REAL,       -- CONTINUOUS: 0.5·pLDDT + 0.5·evidence_density
  hypothesis_score        REAL,       -- CONTINUOUS: mean of the three above (LEGACY — see hypothesis_strength/aav_viability)
  hypothesis_strength     REAL,       -- OBJECTIVE 1: weighted_fit × xlab_bonus + confidence
  aav_viability           REAL,       -- OBJECTIVE 2: tissue_delivery × payload_fit × dgc_rescue × precedent × target_boost × rescue_window
  max_predicted_severity  INTEGER,    -- max severity across this row's predicted phenotype set
  predicts_severe         INTEGER,    -- boolean: max severity >= 4 (viz highlight)
  is_pareto_within_patient INTEGER,
  is_pareto_global         INTEGER,
  generated_at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_hf_patient   ON hypothesis_frontier(cohort, patient_id);
CREATE INDEX IF NOT EXISTS ix_hf_pareto_g  ON hypothesis_frontier(is_pareto_global);
CREATE INDEX IF NOT EXISTS ix_hf_family    ON hypothesis_frontier(mechanism_family);
"""


# ----------------------------------------------------------------------
# Substrate loaders
# ----------------------------------------------------------------------
def load_patients(conn) -> list[dict]:
    out = []
    for (cohort, pid) in ROSTER_KEYS:
        r = conn.execute(
            "SELECT nucleotide, aa_change, exon, consequence "
            "FROM patient_phenotype WHERE cohort=? AND patient_id=?",
            (cohort, pid),
        ).fetchone()
        if not r: continue
        (nuc, aa, exon_str, cons) = r
        exon_n = None
        if exon_str:
            try: exon_n = int("".join(c for c in str(exon_str) if c.isdigit()))
            except Exception: exon_n = None
        out.append({
            "cohort": cohort, "patient_id": pid,
            "label": ROSTER_LABELS[(cohort, pid)],
            "hgvsc": nuc, "hgvsp": aa, "consequence": cons,
            "exon_n": exon_n,
            "variant_key": f"{cohort}#{pid}:{nuc or '?'}",
        })
    return out


def load_lab_map() -> dict[str, str]:
    """assay_key → phenotype_node."""
    out: dict[str, str] = {}
    with LAB_MAP_TSV.open() as f:
        for line in f:
            if line.startswith("#") or line.startswith("lab_key\t"): continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2 or not parts[0].strip(): continue
            out[parts[0]] = parts[1]
    return out


def observed_phenotype_set(conn, cohort: str, pid: str,
                            lab_map: dict[str, str]) -> set[str]:
    """Set of phenotype nodes for which this patient shows an abnormal lab."""
    obs: set[str] = set()
    for (key, flag) in conn.execute(
        "SELECT assay_key, flag FROM patient_labs "
        "WHERE cohort=? AND patient_id=?", (cohort, pid)):
        if (flag or "").lower() != "normal":
            node = lab_map.get(key)
            if node: obs.add(node)
    return obs


def observed_phenotype_zscores(conn, cohort: str, pid: str,
                                 lab_map: dict[str, str]) -> dict[str, float]:
    """{phenotype_node → max |z-score| across labs mapping to that node}.

    Continuous per patient — this is what makes fit-to-patient a real
    distribution instead of a 4-bucket step function.

    z = (value - ref_mid) / (ref_half_range).  Ref_low/high define the
    normal band; z-score is how many "band widths" outside normal the
    value sits. |z| > 1 = outside normal; higher = more abnormal.
    """
    out: dict[str, float] = {}
    for (key, val, lo, hi, flag) in conn.execute(
        "SELECT assay_key, value, ref_low, ref_high, flag "
        "FROM patient_labs WHERE cohort=? AND patient_id=?", (cohort, pid)):
        node = lab_map.get(key)
        if not node: continue
        mid = (lo + hi) / 2.0
        half = max((hi - lo) / 2.0, 1e-9)
        z = abs((val - mid) / half)
        if node not in out or z > out[node]:
            out[node] = z
    return out


def load_patient_labs_raw(conn, cohort: str, pid: str) -> dict[str, dict]:
    """Load raw lab values + signed z-scores + flags for one patient.

    Returns {assay_key → {value, z_signed, flag}}. Used by the
    lab-multiplier fns (cross-lab consistency, tissue-target boost,
    rescue window). z is *signed* here (unlike observed_phenotype_zscores
    which takes |z|) — we need direction to distinguish e.g. LVEF↓ from
    LVEF↑.
    """
    out: dict[str, dict] = {}
    for (key, val, lo, hi, flag) in conn.execute(
        "SELECT assay_key, value, ref_low, ref_high, flag "
        "FROM patient_labs WHERE cohort=? AND patient_id=?", (cohort, pid)):
        mid = (lo + hi) / 2.0
        half = max((hi - lo) / 2.0, 1e-9)
        z_signed = (val - mid) / half
        out[key] = {"value": val, "z": z_signed, "flag": (flag or "").lower()}
    return out


def cross_lab_consistency_bonus(labs: dict[str, dict]) -> float:
    """1.20 if CK, aldolase, LDH ALL elevated (z > 2); else 1.00.

    Correlated muscle-enzyme elevation is stronger evidence for
    sarcolemmal fragility than any one enzyme alone.
    """
    def elevated(k):
        r = labs.get(k)
        return bool(r) and r["z"] > 2.0
    return 1.20 if (elevated("CK") and elevated("aldolase") and elevated("LDH")) else 1.00


def tissue_target_boost(labs: dict[str, dict], tissue: str) -> float:
    """Product of matched rules from TISSUE_TARGET_LAB_RULES[tissue]. 1.0 if no rules match.

    Multiple active rules multiply (e.g. LVEF↓ AND LGE+ → 1.2 × 1.2 = 1.44).
    """
    rules = TISSUE_TARGET_LAB_RULES.get(tissue, [])
    factor = 1.0
    for (assay, direction, thr, boost) in rules:
        r = labs.get(assay)
        if not r: continue
        if direction == "low"  and r["z"] < -thr:            factor *= boost
        elif direction == "high" and r["z"] >  thr:          factor *= boost
        elif direction == "abn"  and r["flag"] != "normal":  factor *= boost
        elif direction == "flag" and r["value"] is not None: factor *= boost
    return factor


def rescue_window(labs: dict[str, dict], tissue: str) -> float:
    """How much healthy tissue remains → how much there is to rescue.

    skeletal_muscle: 1 − MRI_ff_VL/100 (fibro-fat is irretrievable).
    heart:           LVEF/60           (lower EF = less to preserve).
    else:            1.0               (no lab proxy).
    Clipped to [0, 1].
    """
    if tissue == "skeletal_muscle":
        r = labs.get("MRI_ff_VL")
        if r and r["value"] is not None:
            return max(0.0, min(1.0, 1.0 - r["value"] / 100.0))
    elif tissue == "heart":
        r = labs.get("LVEF")
        if r and r["value"] is not None:
            return max(0.0, min(1.0, r["value"] / 60.0))
    return 1.0


def score_precedent_prior(mech_id: str, tissue: str, exon: int | None,
                           consequence: str | None) -> float:
    """Clinical precedent for (mechanism, tissue, variant).

    0.95: FDA-approved exon-skip covers this patient's exon AND mech is H01/H02.
    0.75: H02 + skeletal_muscle (delandistrogene micro-dys precedent).
    0.60: H03 + PTC-generating variant (ataluren readthrough precedent).
    0.30: everything else.
    """
    if mech_id in ("01", "02") and exon in FDA_APPROVED_SKIPS:
        return 0.95
    if mech_id == "02" and tissue == "skeletal_muscle":
        return 0.75
    if mech_id == "03" and (consequence or "").lower() in ("nonsense", "splice-site"):
        return 0.60
    return 0.30


def load_dmd_hpa_by_cell(conn) -> dict[str, float]:
    """{cell_type → HPA expression score of DMD in that cell} (0..10 real)."""
    return {r[0]: r[1] for r in conn.execute(
        "SELECT cell_type, score FROM celltype_expression "
        "WHERE gene_symbol='DMD'")}


def load_esm3_plddt(cohort: str, pid: str) -> float | None:
    """Per-patient ESM3 pLDDT from protein_impact.tsv (0..100 real).
    Returns None for the splice-site patient (no residue → no fold).
    """
    tsv = REPO / "data" / "variants" / "protein_impact.tsv"
    if not tsv.exists(): return None
    with tsv.open() as f:
        for line in f:
            if line.startswith("#") or line.startswith("patient_id\t"): continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 10: continue
            if parts[0] == pid and parts[1] == cohort:
                try: return float(parts[8]) if parts[8] else None
                except ValueError: return None
    return None


def load_pathway_sizes(conn) -> dict[str, int]:
    """{pathway_id → pathway_size} — used for log-pathway-size factor."""
    conn.execute(f"ATTACH DATABASE '{PATHWAYS_DB}' AS px2")
    out = {r[0]: r[1] for r in conn.execute(
        "SELECT pathway_id, COUNT(DISTINCT gene_symbol) "
        "FROM px2.gene_pathway GROUP BY pathway_id"
    )}
    conn.execute("DETACH DATABASE px2")
    return out


# Tissue delivery priors (0..1) — how deliverable an intervention is.
# Mirrors TISSUE_TRACTABILITY from bake_hypotheses_and_premises.
TISSUE_DELIVERY = {
    "skeletal_muscle": 0.95, "heart": 0.75, "retina": 0.90,
    "cns": 0.35, "peripheral_nerve": 0.40, "smooth_muscle": 0.40,
    "vascular": 0.30, "kidney": 0.35, "liver": 0.45, "adipose": 0.15,
    "salivary_gland": 0.05, "breast": 0.10, "prostate": 0.10,
    "thymus": 0.20, "other": 0.30,
}

# ----------------------------------------------------------------------
# Two-objective refactor: AAV-viability terms + lab-derived multipliers.
# See PARETO_REFACTOR_PLAN.md for design rationale.
# ----------------------------------------------------------------------

# Per-mechanism payload_fit — how well the mechanism fits an AAV capsid.
# H01 full DMD gene (~11kb cDNA) exceeds AAV 4.7kb limit → very low.
# H02 in-frame → micro-dystrophin construct fits (Elevidys precedent) → high.
# H03 exon-skipping delivered as AAV-ASO — feasible but less mature.
# H04 distal isoforms (Dp71, Dp140) are small → good fit.
PAYLOAD_FIT = {"01": 0.10, "02": 0.90, "03": 0.60, "04": 0.75}

# Lab-driven tissue-target boosts: if a patient's lab flags this tissue as an
# active target of pathology, its AAV-viability gets a boost (or penalty for
# tissues where AAV delivery is harder like CNS/kidney).
# Rule tuple: (assay_key, direction, threshold_z, boost_factor)
#   direction: "low" (z<-thr), "high" (z>+thr), "abn" (flag != normal), "flag" (any non-null value = present)
TISSUE_TARGET_LAB_RULES: dict[str, list[tuple]] = {
    "heart":           [("LVEF", "low", 2.0, 1.2),
                        ("NT_proBNP", "high", 2.0, 1.2),
                        ("LGE", "flag", None, 1.2)],
    "skeletal_muscle": [("FVC_pct", "low", 2.0, 1.2),
                        ("PCF", "low", 2.0, 1.2)],
    "cns":             [("IQ", "low", 2.0, 0.7)],
    "retina":          [("ERG_bwave", "abn", None, 1.3)],
    "kidney":          [("UACR", "high", 2.0, 0.7)],
}


def load_top_pathways(conn) -> list[dict]:
    """Top-N Reactome pathways by DGC-member coverage density
    (n DGC members ∩ pathway / pathway_size). Uses ATTACHed pathways.sqlite."""
    conn.execute(f"ATTACH DATABASE '{PATHWAYS_DB}' AS px")
    dgc_str = ",".join(f"'{g}'" for g in DGC_MEMBERS)
    rows = conn.execute(f"""
        WITH pw_sizes AS (
            SELECT pathway_id, pathway_name,
                   COUNT(DISTINCT gene_symbol) AS pathway_size
            FROM px.gene_pathway GROUP BY pathway_id
        ),
        pw_dgc AS (
            SELECT pathway_id,
                   COUNT(DISTINCT gene_symbol) AS n_dgc
            FROM px.gene_pathway
            WHERE gene_symbol IN ({dgc_str})
            GROUP BY pathway_id
        )
        SELECT s.pathway_id, s.pathway_name, s.pathway_size, d.n_dgc,
               1.0 * d.n_dgc / s.pathway_size AS coverage
        FROM pw_sizes s JOIN pw_dgc d USING (pathway_id)
        WHERE s.pathway_size BETWEEN 3 AND 500
        ORDER BY coverage DESC, d.n_dgc DESC
        LIMIT ?
    """, (TOP_N_PATHWAYS,)).fetchall()
    conn.execute("DETACH DATABASE px")
    return [{"pathway_id": r[0], "pathway_name": r[1],
             "pathway_size": r[2], "n_dgc": r[3],
             "coverage": r[4], "source": "reactome"} for r in rows]


def load_top_cell_types(conn) -> list[dict]:
    """Top-N cell types by DGC-completeness × clinical-tissue-relevance."""
    dgc_str = ",".join(f"'{g}'" for g in DGC_MEMBERS)
    # DGC-completeness per cell type = distinct DGC members with score > 0.
    rows = conn.execute(f"""
        SELECT cell_type, tissue,
               COUNT(DISTINCT gene_symbol) AS n_dgc
        FROM celltype_expression
        WHERE gene_symbol IN ({dgc_str}) AND score > 0
        GROUP BY cell_type, tissue
    """).fetchall()
    scored = []
    for (cell, tissue, n_dgc) in rows:
        completeness = n_dgc / len(DGC_MEMBERS)
        relevance = TISSUE_RELEVANCE.get((tissue or "other").lower(),
                                          TISSUE_RELEVANCE["other"])
        score = completeness * relevance
        scored.append({
            "cell_type": cell, "tissue": (tissue or "other").lower(),
            "n_dgc": n_dgc, "dgc_completeness": completeness,
            "tissue_relevance": relevance, "score": score,
        })
    scored.sort(key=lambda x: (-x["score"], -x["dgc_completeness"]))
    return scored[:TOP_N_CELL_TYPES]


# ----------------------------------------------------------------------
# Per-row scoring
# ----------------------------------------------------------------------
def score_coverage(predicted: list[str], observed: set[str]) -> tuple[int, float]:
    """(n_intersect, precision-style coverage)."""
    if not predicted:
        return 0, 0.0
    n_int = sum(1 for p in predicted if p in observed)
    return n_int, n_int / len(predicted)


def score_weighted_fit(predicted: list[str], obs_z: dict[str, float]) -> float:
    """CONTINUOUS severity-weighted fit-to-patient (Framing-A X axis).

    Σ (severity[p] × min(|z_p|, Z_CAP))  /  Σ (severity[p] × Z_CAP)   for p in predicted.

    obs_z: {phenotype_node → max |z-score|}. Zero for phenotypes without
    an observed lab. Z_CAP=8 clips extreme lab values (e.g. CK 15000
    could give |z|>100) so one wildly-abnormal lab doesn't dominate.
    Result is continuous 0..1.
    """
    Z_CAP = 8.0
    if not predicted: return 0.0
    denom = sum(PHENOTYPE_SEVERITY.get(p, 1) * Z_CAP for p in predicted)
    if denom == 0: return 0.0
    num = sum(PHENOTYPE_SEVERITY.get(p, 1) * min(obs_z.get(p, 0.0), Z_CAP)
              for p in predicted)
    return num / denom


def score_therapeutic_reach(actionability: int, tissue: str,
                              hpa_dmd_in_cell: float) -> float:
    """CONTINUOUS therapeutic reach (Framing-A Y axis).

    reach = (act/3) × (HPA_DMD_in_cell/10) × tissue_delivery_prior
    All three factors continuous → thousands of unique combinations.
    """
    delivery = TISSUE_DELIVERY.get((tissue or "other").lower(), 0.30)
    return (actionability / 3.0) * (hpa_dmd_in_cell / 10.0) * delivery


def score_confidence(mean_plddt: float | None, pathway_size: int | None,
                      depth_layers: int) -> float:
    """CONTINUOUS confidence: how well-supported is this chain overall?

    confidence = 0.4·pLDDT_norm + 0.4·log_pathway_size_norm + 0.2·depth_norm
    Continuous 0..1. pLDDT and log(pathway_size) are the two real-valued
    components; depth is retained as a small tiebreaker.
    """
    import math
    plddt_norm = ((mean_plddt or 60.0) - 40.0) / 60.0    # ~0..1 for typical pLDDT 40-100
    plddt_norm = max(0.0, min(1.0, plddt_norm))
    size = pathway_size or 100
    size_norm = (math.log10(max(size, 1)) - math.log10(3)) / (math.log10(500) - math.log10(3))
    size_norm = max(0.0, min(1.0, size_norm))
    depth_norm = depth_layers / 5.0
    return 0.4 * plddt_norm + 0.4 * size_norm + 0.2 * depth_norm


def score_hypothesis_strength(wfit: float, conf: float, xlab_bonus: float) -> float:
    """Objective 1 — how well-supported this hypothesis is for THIS patient.

    strength = weighted_fit × cross_lab_consistency_bonus + confidence

    weighted_fit already encodes severity-weighted lab z-scores; the
    xlab_bonus adds the co-elevation multiplier (correlated muscle
    enzymes strengthen H01 more than any single enzyme). confidence is
    the mechanism/pathway/structural support term. Sum (not product) so
    a hypothesis can still score high on structural/pathway confidence
    even if the patient's labs don't fit — that's an interpretable
    high-Y-low-X mode.
    """
    return wfit * xlab_bonus + conf


def score_aav_viability(mech_id: str, tissue: str, exon: int | None,
                        consequence: str | None,
                        dgc_pw: float, dgc_cell: float,
                        tissue_boost: float, rescue_win: float) -> float:
    """Objective 2 — how deliverable this hypothesis is as an AAV therapeutic.

    aav = tissue_delivery × payload_fit × dgc_rescue
        × precedent_prior × tissue_target_boost × rescue_window

    Purely multiplicative: any factor at zero kills the score (correct —
    e.g. undeliverable tissue OR unreachable payload → not viable).
    """
    return (TISSUE_DELIVERY.get(tissue, 0.30)
            * PAYLOAD_FIT.get(mech_id, 0.30)
            * dgc_pw * dgc_cell
            * score_precedent_prior(mech_id, tissue, exon, consequence)
            * tissue_boost
            * rescue_win)


def max_severity_of(predicted: list[str]) -> int:
    if not predicted:
        return 0
    return max((PHENOTYPE_SEVERITY.get(p, 0) for p in predicted), default=0)


def score_depth(patient: dict, pathway: dict, cell: dict,
                observed: set[str], predicted: list[str]) -> int:
    """0..5 layers with any evidence.
    Variant: 1 if patient has a variant on file (always true for cohort).
    Protein / mechanism: 1 if consequence + exon_n both parseable.
    Pathway: 1 if pathway carries ≥1 DGC member.
    Cell type: 1 if cell type has DGC completeness > 0.
    Phenotype: 1 if the predicted phenotype set intersects the observed set.
    """
    d = 1                                     # variant node
    if patient["consequence"] and patient["exon_n"] is not None: d += 1
    if pathway["n_dgc"] > 0: d += 1
    if cell["dgc_completeness"] > 0: d += 1
    if any(p in observed for p in predicted): d += 1
    return d


def score_actionability(mech_id: str, tissue: str, patient: dict) -> int:
    """0..3 grade.
    3: FDA-approved exon-skip ASO covers this patient's exon AND mechanism
       is H01/H02 AND cell tissue is skeletal_muscle
    2: gene-replacement AAV (H01 or H03) AND tissue is muscle/heart
    2: ataluren readthrough (H03) with PTC-generating variant
    1: utrophin upregulator (H02) with muscle tissue OR distal AAV (H04)
    0: nothing plausible
    """
    exon = patient.get("exon_n")
    if (mech_id in ("01", "02") and exon in FDA_APPROVED_SKIPS
        and tissue == "skeletal_muscle"):
        return 3
    if mech_id in ("01", "03") and tissue in ("skeletal_muscle", "heart"):
        return 2
    if mech_id == "03" and (patient.get("consequence") or "").lower() in ("nonsense", "splice-site"):
        return 2
    if mech_id == "02" and tissue == "skeletal_muscle":
        return 1
    if mech_id == "04" and tissue in ("retina", "cns", "kidney"):
        return 1
    return 0


# ----------------------------------------------------------------------
# Pareto masking — axis-sort algorithm.
# ----------------------------------------------------------------------
def pareto_flags(rows: list[dict], axes: tuple[str, ...]) -> list[int]:
    """Boolean mask: 1 = non-dominated on `axes` (all maximised).

    Efficient enough for ~50k rows. Sorts by axis-0 desc, then linear
    scan tracking the best-seen tuple across the remaining axes.
    """
    n = len(rows)
    keep = [1] * n
    if n == 0 or len(axes) < 2:
        return keep
    idx = list(range(n))
    idx.sort(key=lambda i: tuple(-rows[i][a] for a in axes))
    # Track: for each row, if there exists another row that is ≥ on all
    # axes and > on at least one → dominated. We walk sorted order (best
    # on axis 0 first). Any later row can only dominate if it matches
    # axis-0 exactly AND beats on some other axis. We track the max seen
    # over axes[1:] for rows with the current axis-0 value.
    # For >2 axes with ties this is not fully correct — fall back to O(n²)
    # for tie-heavy small n (our case).
    for i in range(n):
        pi = tuple(rows[i][a] for a in axes)
        for j in range(n):
            if i == j: continue
            pj = tuple(rows[j][a] for a in axes)
            if all(pj[k] >= pi[k] for k in range(len(axes))) \
               and any(pj[k] >  pi[k] for k in range(len(axes))):
                keep[i] = 0
                break
    return keep


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------
def main() -> None:
    t0 = time.time()
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)

    patients   = load_patients(conn)
    lab_map    = load_lab_map()
    pathways   = load_top_pathways(conn)
    cell_types = load_top_cell_types(conn)
    hpa_dmd    = load_dmd_hpa_by_cell(conn)
    pw_sizes   = load_pathway_sizes(conn)
    print(f"[loaded] {len(patients)} patients · {len(pathways)} pathways · "
          f"{len(cell_types)} cell types · {len(lab_map)} lab→pheno mappings · "
          f"{len(hpa_dmd)} HPA-DMD cell scores")

    # Precompute per-patient observed-phenotype vector + z-scores + pLDDT.
    # Also raw labs (dict[assay → {value, z, flag}]) + cross-lab consistency
    # bonus — patient-invariant across the inner (mech × pw × cell) loop.
    observed_by_patient: dict[tuple, set[str]] = {}
    obs_z_by_patient:    dict[tuple, dict[str, float]] = {}
    plddt_by_patient:    dict[tuple, float | None] = {}
    labs_raw_by_patient: dict[tuple, dict[str, dict]] = {}
    xlab_bonus_by_patient: dict[tuple, float] = {}
    for p in patients:
        k = (p["cohort"], p["patient_id"])
        observed_by_patient[k] = observed_phenotype_set(
            conn, p["cohort"], p["patient_id"], lab_map)
        obs_z_by_patient[k] = observed_phenotype_zscores(
            conn, p["cohort"], p["patient_id"], lab_map)
        plddt_by_patient[k] = load_esm3_plddt(p["cohort"], p["patient_id"])
        labs_raw_by_patient[k] = load_patient_labs_raw(
            conn, p["cohort"], p["patient_id"])
        xlab_bonus_by_patient[k] = cross_lab_consistency_bonus(labs_raw_by_patient[k])
    print("[obs-phenotypes] " + " ".join(
        f"{p['label']}=n{len(observed_by_patient[(p['cohort'], p['patient_id'])])}"
        for p in patients))
    print("[pLDDT] " + " ".join(
        f"{p['label']}={(plddt_by_patient[(p['cohort'], p['patient_id'])] or 0):.0f}"
        for p in patients))
    print("[xlab-bonus] " + " ".join(
        f"{p['label']}={xlab_bonus_by_patient[(p['cohort'], p['patient_id'])]:.2f}"
        for p in patients))

    NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    all_rows: list[dict] = []

    for p in patients:
        k = (p["cohort"], p["patient_id"])
        obs = observed_by_patient[k]
        obs_z = obs_z_by_patient[k]
        plddt = plddt_by_patient[k]
        labs_raw = labs_raw_by_patient[k]
        xlab_bonus = xlab_bonus_by_patient[k]
        patient_rows: list[dict] = []

        for (mech_id, mech_desc) in MECH_FAMILIES:
            for pw in pathways:
                for cell in cell_types:
                    predicted = TISSUE_TO_PHENOTYPES.get(cell["tissue"], [])
                    n_int, cov = score_coverage(predicted, obs)   # legacy
                    depth = score_depth(p, pw, cell, obs, predicted)
                    action = score_actionability(mech_id, cell["tissue"], p)
                    # ---- Continuous scoring axes (Framing A, legacy) ------
                    wfit  = score_weighted_fit(predicted, obs_z)
                    hpa   = hpa_dmd.get(cell["cell_type"], 0.0)
                    reach = score_therapeutic_reach(action, cell["tissue"], hpa)
                    conf  = score_confidence(plddt, pw_sizes.get(pw["pathway_id"]), depth)
                    hscore = (wfit + reach + conf) / 3.0
                    # ---- Two-objective axes (current) ---------------------
                    t_boost   = tissue_target_boost(labs_raw, cell["tissue"])
                    r_win     = rescue_window(labs_raw, cell["tissue"])
                    strength  = score_hypothesis_strength(wfit, conf, xlab_bonus)
                    aav_v     = score_aav_viability(
                        mech_id, cell["tissue"], p["exon_n"], p.get("consequence"),
                        pw["coverage"], cell["dgc_completeness"], t_boost, r_win,
                    )
                    max_sev = max_severity_of(predicted)
                    predicts_severe = 1 if max_sev >= SEVERE_THRESHOLD else 0
                    key = f"{p['cohort']}#{p['patient_id']}|h{mech_id}|{pw['pathway_id']}|{cell['cell_type']}"
                    hyp_id = "HF_" + hashlib.sha1(key.encode()).hexdigest()[:12]
                    row = {
                        "hypothesis_id": hyp_id,
                        "cohort": p["cohort"],
                        "patient_id": p["patient_id"],
                        "patient_label": p["label"],
                        "mechanism_family": mech_id,
                        "mechanism_desc": mech_desc,
                        "variant_key": p["variant_key"],
                        "variant_exon": p["exon_n"],
                        "variant_hgvsc": p["hgvsc"],
                        "variant_hgvsp": p["hgvsp"],
                        "pathway_id": pw["pathway_id"],
                        "pathway_name": pw["pathway_name"],
                        "pathway_source": pw["source"],
                        "pathway_dgc_coverage": round(pw["coverage"], 4),
                        "cell_type": cell["cell_type"],
                        "tissue": cell["tissue"],
                        "cell_dgc_completeness": round(cell["dgc_completeness"], 4),
                        "cell_tissue_relevance": round(cell["tissue_relevance"], 3),
                        "predicted_phenotypes": json.dumps(predicted),
                        "observed_phenotypes":  json.dumps(sorted(obs)),
                        "n_predicted": len(predicted),
                        "n_observed":  len(obs),
                        "n_intersect": n_int,
                        "coverage": round(cov, 4),
                        "depth": depth,
                        "actionability": action,
                        "weighted_fit": round(wfit, 6),
                        "therapeutic_reach": round(reach, 6),
                        "confidence": round(conf, 6),
                        "hypothesis_score": round(hscore, 6),
                        "hypothesis_strength": round(strength, 6),
                        "aav_viability": round(aav_v, 6),
                        "max_predicted_severity": max_sev,
                        "predicts_severe": predicts_severe,
                        "is_pareto_within_patient": 0,
                        "is_pareto_global": 0,
                        "generated_at": NOW,
                    }
                    patient_rows.append(row)

        keep_v = pareto_flags(patient_rows, ("hypothesis_strength", "aav_viability"))
        for r, k in zip(patient_rows, keep_v):
            r["is_pareto_within_patient"] = k
        all_rows.extend(patient_rows)

    print(f"[enumerate] {len(all_rows)} rows in {time.time() - t0:.1f}s")

    tp = time.time()
    keep_g = pareto_flags(all_rows, ("hypothesis_strength", "aav_viability"))
    for r, k in zip(all_rows, keep_g):
        r["is_pareto_global"] = k
    print(f"[pareto·global] {sum(keep_g)} non-dominated in {time.time() - tp:.1f}s")

    conn.execute("DELETE FROM hypothesis_frontier")
    cols = [
        "hypothesis_id", "cohort", "patient_id", "patient_label",
        "mechanism_family", "mechanism_desc",
        "variant_key", "variant_exon", "variant_hgvsc", "variant_hgvsp",
        "pathway_id", "pathway_name", "pathway_source", "pathway_dgc_coverage",
        "cell_type", "tissue", "cell_dgc_completeness", "cell_tissue_relevance",
        "predicted_phenotypes", "observed_phenotypes",
        "n_predicted", "n_observed", "n_intersect",
        "coverage", "depth", "actionability",
        "weighted_fit", "therapeutic_reach", "confidence", "hypothesis_score",
        "hypothesis_strength", "aav_viability",
        "max_predicted_severity", "predicts_severe",
        "is_pareto_within_patient", "is_pareto_global", "generated_at",
    ]
    placeholders = ",".join("?" for _ in cols)
    conn.executemany(
        f"INSERT INTO hypothesis_frontier ({','.join(cols)}) VALUES ({placeholders})",
        [tuple(r[c] for c in cols) for r in all_rows],
    )
    conn.commit()

    # Summary
    n_pv = sum(r["is_pareto_within_patient"] for r in all_rows)
    n_pg = sum(r["is_pareto_global"] for r in all_rows)
    print(f"\n[summary] {len(all_rows)} rows written")
    print(f"          {n_pv} non-dominated within-patient (avg "
          f"{n_pv / len(patients):.1f}/patient)")
    print(f"          {n_pg} non-dominated globally")

    print("\nPer-patient frontier + top-scored row:")
    for p in patients:
        cur = conn.execute(
            "SELECT COUNT(*), SUM(is_pareto_within_patient), "
            "       SUM(is_pareto_global) "
            "FROM hypothesis_frontier WHERE cohort=? AND patient_id=?",
            (p["cohort"], p["patient_id"]),
        ).fetchone()
        top = conn.execute(
            "SELECT mechanism_family, pathway_name, cell_type, tissue, "
            "       coverage, depth, actionability "
            "FROM hypothesis_frontier "
            "WHERE cohort=? AND patient_id=? "
            "ORDER BY (coverage+depth/5.0+actionability/3.0) DESC "
            "LIMIT 1",
            (p["cohort"], p["patient_id"]),
        ).fetchone()
        print(f"  {p['label']}: {cur[0]:5d} rows  · frontier(patient)="
              f"{cur[1]:3d}  frontier(global)={cur[2]:3d}")
        if top:
            print(f"         top: H{top[0]}  {top[1][:44]:44s}  "
                  f"| {top[2][:24]:24s} ({top[3]}) "
                  f"cov={top[4]:.2f} dep={top[5]} act={top[6]}")

    conn.close()
    print(f"\n[wall] {time.time() - t0:.1f}s total")


if __name__ == "__main__":
    main()
