"""Read data/mechanism.sqlite → write workbench/patient_data.json.

Per-patient projection: given a specific pathogenic variant (exon N),
compute which DMD isoforms are hit vs spared, and propagate to affected
cell types + tissues via curated cell-type→isoform mapping.

The rule for hit/spared is `iso.first_shared_exon <= patient.exon`. That
approximates the biology: an isoform whose promoter fires downstream of
the variant will not transcribe past the variant, so the variant does
not appear in that isoform's mRNA. This is only an approximation for
splice-site variants (which can have non-local effects) and for internal
deletions that skip over shorter isoforms cleanly — the tile footer
notes that.

Run:
    python3 -m prototype.ingest.hydrate_patient_view
"""
from __future__ import annotations

import html
import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "mechanism.sqlite"
OUT = REPO / "workbench" / "patient_data.json"


# Curated cell-type → isoform requirement mapping. Which isoforms does a
# given cell type depend on for its dystrophin? Sources: Muntoni 2003
# review (Dp427m in skeletal + cardiac); Pillers 1993 (Dp260 in retina);
# Lidov 1995 (Dp71 ubiquitous, high in retina/brain/kidney). If ANY
# listed isoform is spared, we mark the cell type "partially spared"; if
# ALL are spared, "spared"; if all are hit, "hit".
CELL_TO_ISOFORMS: dict[str, list[str]] = {
    "Myonuclei":                    ["Dp427m"],           # skeletal muscle
    "Cardiomyocytes":               ["Dp427m"],           # heart
    "Thymic myoid cells":           ["Dp427m"],           # muscle-lineage
    "Salivary myoepithelial cells": ["Dp427m"],           # smooth-muscle-like
    "Rod photoreceptor cells":      ["Dp260", "Dp71"],    # retina — Dp260 short-axis, Dp71 backup
    "Cone photoreceptor cells":     ["Dp260", "Dp71"],
    "Adipocytes":                   ["Dp71"],             # ubiquitous
}

# Patients are numbered sequentially 1..N by (cohort, cohort_patient_id)
# order (S1_novel first, then S2_reported). The raw Zhang cohort IDs
# collide across S1/S2, but this sequential ID is unique per patient
# across the whole cohort. `cohort` and `cohortPatientId` are retained
# in the patient record for provenance.

# Curated 10-patient roster — one per instructive combination of variant
# type × phenotype × severity. This is the ONLY patient set that goes
# into patient_data.json (the full 418-cohort is not exposed to the UI
# in this phase — we're focused on high-signal cases the agent can
# reason over).
ROSTER = [
    # 10 DMD-only patients (BMD/IMD retired — the demo narrative is
    # "convert DMD → BMD via gene therapy"). Selected for variant-type
    # variety, exon-position range, and age/ambulatory spread.
    ("S1_novel",    "2",   "DMD frameshift, exon 45, non-ambulant · H01 top"),
    ("S1_novel",    "30",  "DMD nonsense, exon 10 · H03 top; long-isoform tail spared"),
    ("S2_reported", "258", "DMD nonsense, exon 63 · global loss incl. Dp71"),
    ("S1_novel",    "57",  "DMD frameshift, exon 8, age 5.4 · early-progression profile"),
    ("S1_novel",    "5",   "DMD frameshift, exon 75, age 16.3 non-amb · advanced-progression"),
    ("S1_novel",    "11",  "DMD frameshift, exon 20 · mid-exon frameshift"),
    ("S2_reported", "202", "DMD nonsense, exon 45 · Dp140 boundary"),
    ("S2_reported", "225", "DMD nonsense, exon 53 · Dp140-hit ambulant"),
    ("S1_novel",    "49",  "DMD nonsense, exon 53, age 4.3 · young ambulant"),
    ("S2_reported", "266", "DMD splice, intron 64 · Dp116-adjacent splice-site"),
]


def make_uid(seq_num: int) -> str:
    return f"P{seq_num}"


def parse_exon(s: str | None) -> int | None:
    """'55' → 55; 'int25' → 25; 'Int53' → 53; None/garbage → None."""
    if not s:
        return None
    t = s.strip()
    lower = t.lower()
    if lower.startswith("int"):
        t = t[3:]
    try:
        return int(t)
    except ValueError:
        return None


def isoform_hit(first_shared_exon: int, patient_exon: int) -> bool:
    """Isoform is hit iff its transcription starts at or before the variant."""
    return first_shared_exon <= patient_exon


# Per-patient hypothesis scoring. Scores are on a 0-10 scale and are
# derived from the variant's consequence, the observed phenotype, and
# (for H04) how distal the variant is on the transcript. Kept as a small
# set of hand-tuned rules — the goal is to make the top hypothesis
# obvious and defensible, not to be a probabilistic classifier.
def score_hypotheses(
    variant_consequence: str | None,
    phenotype: str | None,
    exon_n: int | None,
) -> list[dict]:
    cons = (variant_consequence or "").lower()
    phen = (phenotype or "")
    scores: dict[str, tuple[float, str]] = {}

    # H01 — out-of-frame → truncated → sarcolemmal fragility
    if cons == "frameshift":
        scores["01"] = (9.5, "frameshift → out-of-frame → truncated dystrophin (Monaco rule)")
    elif cons == "nonsense":
        scores["01"] = (6.0, "premature stop → truncated protein (before NMD)")
    elif cons == "splice-site":
        scores["01"] = (5.0, "splice defect can produce out-of-frame transcript")
    elif cons == "missense":
        scores["01"] = (1.5, "missense does not truncate — poor fit")
    else:
        scores["01"] = (0.5, "not a truncating variant")

    # H02 — in-frame / partial-function / BMD
    if phen == "BMD":
        scores["02"] = (9.0, "BMD phenotype label — partial-function dystrophin consistent")
    elif phen == "IMD":
        scores["02"] = (6.5, "intermediate phenotype — some partial rescue plausible")
    elif cons == "missense":
        scores["02"] = (5.5, "missense can preserve some dystrophin function")
    elif cons in ("synonymous",):
        scores["02"] = (3.0, "synonymous — possible mild effect via splicing")
    else:
        scores["02"] = (1.5, "no evidence of in-frame rescue")

    # H03 — NMD / nonsense / splice → tissue-graded transcript loss
    if cons == "nonsense":
        scores["03"] = (9.5, "PTC → NMD-mediated transcript loss (direct fit)")
    elif cons == "splice-site":
        scores["03"] = (9.0, "splice defect → downstream PTC → NMD-eligible")
    elif cons == "frameshift":
        scores["03"] = (8.5, "frameshift creates downstream PTC → NMD-eligible")
    else:
        scores["03"] = (1.5, "no PTC generated")

    # H04 — distal-promoter / tissue-specific isoform loss
    # Coding-region variants don't cleanly fit H04 (all such variants hit
    # Dp427m since it starts at exon 1). But the more distal the variant,
    # the more the additional isoforms it hits (Dp140@45, Dp116@56, Dp71@63)
    # dominate the residual protein population — so we scale by distality.
    if exon_n is None:
        scores["04"] = (1.0, "variant position not parseable")
    elif exon_n >= 63:
        scores["04"] = (5.0, f"exon {exon_n} — hits Dp71 (last ubiquitous isoform)")
    elif exon_n >= 56:
        scores["04"] = (4.0, f"exon {exon_n} — hits Dp116 (Schwann)")
    elif exon_n >= 45:
        scores["04"] = (3.0, f"exon {exon_n} — hits Dp140 (brain/kidney)")
    else:
        scores["04"] = (1.5, f"exon {exon_n or '?'} — proximal, doesn't selectively affect distal isoforms")

    ranked = sorted(scores.items(), key=lambda kv: -kv[1][0])
    return [{"id": hid, "score": round(s, 2), "fit": fit, "rank": i + 1}
            for i, (hid, (s, fit)) in enumerate(ranked)]


# ======================================================================
# Clinical labs — read from mechanism.sqlite.patient_labs
# ----------------------------------------------------------------------
# Labs are stored in SQL (baked by bake_synthetic_labs.py). This hydrator
# just reads them per patient and shapes them for the JSON payload.
# ======================================================================
def load_labs(conn, cohort: str, patient_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT assay_key, label, layer, tissue, unit, value, ref_low, ref_high, flag "
        "FROM patient_labs WHERE cohort=? AND patient_id=? "
        "ORDER BY layer, tissue, assay_key",
        (cohort, patient_id),
    ).fetchall()
    return [{
        "key": r[0], "label": r[1], "layer": r[2], "tissue": r[3],
        "unit": r[4], "value": r[5], "refLow": r[6], "refHigh": r[7], "flag": r[8],
    } for r in rows]


# ----------------------------------------------------------------------
# Per-hypothesis patient-specific evidence extraction.
# Given the patient's labs, return the bullets that ARGUE FOR each of
# the 4 hypotheses. These sit alongside the generic literature evidence
# in the UI but are marked "patient-specific" and rank above literature.
# ----------------------------------------------------------------------
def _lab_map(labs: list[dict]) -> dict[str, dict]:
    return {r["key"]: r for r in labs}


def _fmt(row: dict, precision_note: str = "") -> str:
    v = row["value"]
    if row["unit"] == "presence":
        return f"{row['label']}: {'present' if v else 'absent'}"
    if row["unit"] in ("U/L", "pg/mL", "meters", "µV", "FSIQ", "L/min", "mg/g", "score/34"):
        vs = f"{int(v):,}" if v >= 1000 else str(v)
    else:
        vs = str(v)
    return f"{row['label']} {vs} {row['unit']}" + (f" ({precision_note})" if precision_note else "")


def _fold(row: dict) -> float:
    """Fold-over-ULN (or fold-under-LLN if low)."""
    if row["flag"] == "high" and row["refHigh"] > 0:
        return row["value"] / row["refHigh"]
    if row["flag"] == "low" and row["refLow"] > 0:
        return row["refLow"] / max(row["value"], 0.01)
    return 1.0


def patient_evidence_for_hypothesis(hyp_id: str, patient: dict, labs: list[dict]) -> list[dict]:
    """Return [{lab_key, tone: 'supports'|'against'|'neutral', text}] for hyp_id."""
    L = _lab_map(labs)
    out: list[dict] = []

    def push(lab_key: str, tone: str, text: str):
        out.append({"labKey": lab_key, "tone": tone, "text": text})

    ck = L.get("CK");   lvef = L.get("LVEF"); fvc = L.get("FVC_pct")
    mri = L.get("MRI_ff_VL"); m6 = L.get("m6MWT"); nsaa = L.get("NSAA")
    iq = L.get("IQ");   erg = L.get("ERG_bwave"); uacr = L.get("UACR")

    if hyp_id == "01":
        if ck and ck["flag"] == "high" and _fold(ck) >= 20:
            push("CK", "supports",
                 f"{_fmt(ck)} — {_fold(ck):.0f}× ULN, direct readout of sarcolemmal membrane damage consistent with truncated / absent dystrophin.")
        if lvef and lvef["value"] < 55:
            push("LVEF", "supports",
                 f"{_fmt(lvef)} — reduced ejection fraction consistent with H01's DGC loss in cardiac muscle.")
        if fvc and fvc["value"] < 80:
            push("FVC_pct", "supports",
                 f"{_fmt(fvc)} — respiratory muscle involvement matches H01's tissue-wide dystrophy.")
        if mri and mri["value"] > 25:
            push("MRI_ff_VL", "supports",
                 f"{_fmt(mri)} — advanced fibro-fatty replacement in skeletal muscle, the phenotypic endpoint of H01.")
        if m6 and m6["value"] < 350 and m6["value"] > 0:
            push("m6MWT", "supports",
                 f"{_fmt(m6)} — impaired motor phenotype consistent with muscle-scaled dystrophin loss.")

    elif hyp_id == "02":
        # BMD signature: moderate CK, preserved LVEF/FVC, better-than-DMD motor.
        if ck and 1000 <= ck["value"] <= 8000:
            push("CK", "supports",
                 f"{_fmt(ck)} — moderate elevation (5-40× ULN) fits BMD's partial-function pattern, not the extreme DMD range.")
        if lvef and lvef["value"] >= 55:
            push("LVEF", "supports",
                 f"{_fmt(lvef)} — preserved ejection fraction consistent with in-frame rescue keeping cardiac DGC partially assembled.")
        if fvc and fvc["value"] >= 80:
            push("FVC_pct", "supports",
                 f"{_fmt(fvc)} — preserved respiratory function typical of BMD trajectory.")
        if nsaa and nsaa["value"] >= 20:
            push("NSAA", "supports",
                 f"{_fmt(nsaa)} — retained motor function argues for partial-function dystrophin.")
        if patient["phenotype"] == "BMD":
            push("_phenotype", "supports",
                 f"Clinical label: BMD. Trajectory of preserved ambulation past age 16 is the defining criterion (Bushby 1993).")

    elif hyp_id == "03":
        if ck and ck["flag"] == "high" and _fold(ck) >= 20:
            push("CK", "supports",
                 f"{_fmt(ck)} — massive CK release matches near-total Dp427m loss from NMD-degraded transcript.")
        if mri and mri["value"] > 25:
            push("MRI_ff_VL", "supports",
                 f"{_fmt(mri)} — extensive muscle fibro-fatty replacement consistent with total protein loss.")
        # Tissue-graded NMD escape signature: severe muscle + preserved brain
        if (iq and iq["value"] >= 90) and (mri and mri["value"] > 25):
            push("IQ", "supports",
                 f"{_fmt(iq)} — cognitive function preserved despite advanced muscle disease; consistent with tissue-graded NMD escape in brain isoforms.")
        if lvef and lvef["value"] < 55 and lvef["value"] > 40:
            push("LVEF", "supports",
                 f"{_fmt(lvef)} — moderate cardiac involvement (partial NMD escape in cardiomyocytes may soften trajectory).")

    elif hyp_id == "04":
        if iq and iq["value"] < 90:
            push("IQ", "supports",
                 f"{_fmt(iq)} — reduced IQ correlates with Dp140 loss (Ricotti 2016). Distal-isoform signature.")
        if erg and erg["value"] < 200:
            push("ERG_bwave", "supports",
                 f"{_fmt(erg)} — attenuated ERG b-wave amplitude suggests Dp260 loss in retina.")
        if uacr and uacr["value"] > 30:
            push("UACR", "supports",
                 f"{_fmt(uacr)} — elevated urine albumin suggests Dp71 loss in podocytes.")
        # H04's negative-space signature: muscle preserved despite genotype.
        if ck and ck["value"] < 5000:
            push("CK", "supports",
                 f"{_fmt(ck)} — CK is unusually low for a truncating variant; consistent with muscle isoforms (Dp427m) being spared.")
        if lvef and lvef["value"] >= 55 and mri and mri["value"] < 25:
            push("LVEF", "supports",
                 f"LVEF {lvef['value']}%, MRI ff {mri['value']}% — muscle tissues preserved despite variant, characteristic of isoform-scoped disease.")

    return out


def cell_status(iso_hit_map: dict[str, bool], required_isoforms: list[str]) -> str:
    """'hit' if all requirements hit; 'spared' if all spared; else 'partial'."""
    if not required_isoforms:
        return "unknown"
    states = [iso_hit_map.get(i, True) for i in required_isoforms]  # missing iso = assume hit
    if all(states):
        return "hit"
    if not any(states):
        return "spared"
    return "partial"


def load_lab_phenotype_map() -> dict[str, dict]:
    """Load data/variants/lab_phenotype_map.tsv → { lab_key: {phenotype_node,
    interpretation} }. Empty dict if the curation file is missing."""
    path = Path(__file__).resolve().parent.parent.parent / "data" / "variants" / "lab_phenotype_map.tsv"
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    header = None
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"): continue
        parts = line.split("\t")
        if header is None:
            header = parts; continue
        r = dict(zip(header, parts))
        if r.get("lab_key"):
            out[r["lab_key"]] = {
                "phenotypeNode": r.get("phenotype_node", ""),
                "interpretation": r.get("interpretation", ""),
            }
    return out


def compute_phenotypes_observed(labs: list[dict], lab_map: dict[str, dict]) -> dict:
    """From a patient's labs + the curated lab→phenotype map, return
    { phenotype_node: {supportingLabs: [...], nAbnormal: N, nEvaluated: N} }.
    A phenotype is 'observed' if at least one lab pointing to it is abnormal."""
    by_phen: dict[str, dict] = {}
    for l in labs or []:
        m = lab_map.get(l.get("key"))
        if not m: continue
        pn = m["phenotypeNode"]
        b = by_phen.setdefault(pn, {"supportingLabs": [], "nAbnormal": 0, "nEvaluated": 0})
        is_abn = l.get("flag") not in ("normal", None, "")
        b["nEvaluated"] += 1
        if is_abn: b["nAbnormal"] += 1
        b["supportingLabs"].append({
            "labKey":  l.get("key"),
            "label":   l.get("label"),
            "value":   l.get("value"),
            "unit":    l.get("unit"),
            "flag":    l.get("flag"),
            "abnormal": is_abn,
        })
    return by_phen


def load_protein_impact() -> dict[str, dict]:
    """Load the ESM3 protein-impact bake (data/variants/protein_impact.tsv).

    Returns { "S1_novel#2": {residue, mean_wt_plddt, wt_ptm,
              truncation_fraction, impact_score, status, ...}, ... }
    keyed by "cohort#patient_id". Empty dict if the bake hasn't run.
    """
    path = Path(__file__).resolve().parent.parent.parent / "data" / "variants" / "protein_impact.tsv"
    if not path.exists():
        return {}
    rows: dict[str, dict] = {}
    with path.open() as f:
        header = None
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"): continue
            if header is None:
                header = line.split("\t")
                continue
            vals = line.split("\t")
            r = dict(zip(header, vals))
            def _num(k):
                v = r.get(k, "")
                if v in ("", "None"): return None
                try: return float(v)
                except (ValueError, TypeError): return None
            key = f"{r.get('cohort','')}#{r.get('patient_id','')}"
            rows[key] = {
                "residue":             int(float(r["residue"])) if r.get("residue") not in ("", "None") else None,
                "windowStart":         int(float(r["window_start"])) if r.get("window_start") not in ("", "None") else None,
                "windowEnd":           int(float(r["window_end"])) if r.get("window_end") not in ("", "None") else None,
                "meanWtPlddt":         _num("mean_wt_plddt"),
                "wtPtm":               _num("wt_ptm"),
                "truncationFraction":  _num("truncation_fraction"),
                "impactScore":         _num("impact_score"),
                "consequence":         r.get("consequence", ""),
                "hgvsp":               r.get("hgvsp", ""),
                "hgvsc":               r.get("hgvsc", ""),
                "uniprot":             r.get("uniprot", ""),
                "status":              r.get("status", ""),
                "notes":               r.get("notes", ""),
            }
    return rows


def load_gene(conn) -> dict:
    r = conn.execute(
        "SELECT symbol, full_name, uniprot, locus, n_exons, locus_size_mb, isoform_names "
        "FROM gene_meta WHERE symbol='DMD'"
    ).fetchone()
    return {
        "symbol": r[0], "fullName": r[1], "uniprot": r[2], "locus": r[3],
        "nExons": r[4], "locusSizeMb": r[5], "isoformNames": json.loads(r[6]),
    }


def load_isoforms(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT isoform_id, refseq_transcript, uniprot_base, first_shared_exon, "
        "       promoter_tissue, primary_expression_tissues, unique_5prime_exon_label, rank "
        "FROM isoforms ORDER BY rank"
    ).fetchall()
    return [{
        "id": r[0], "refseq": r[1], "uniprot": r[2],
        "firstSharedExon": r[3], "promoterTissue": r[4],
        "tissues": [t.strip() for t in (r[5] or "").split(";") if t.strip()],
        "label": r[6], "rank": r[7],
    } for r in rows]


def load_celltypes(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT cell_type, tissue, score, color_hint FROM celltype_expression "
        "WHERE gene_symbol='DMD' ORDER BY score DESC"
    ).fetchall()
    return [{
        "name": r[0], "tissue": r[1], "score": r[2],
        "colorHint": r[3],
        "requiresIsoforms": CELL_TO_ISOFORMS.get(r[0], []),
    } for r in rows]


def load_stored_hypotheses(conn: sqlite3.Connection, cohort: str, pid_raw: str
                           ) -> list[dict] | None:
    """Read patient_hypothesis + hypothesis_premise + hypothesis_chain_link
    + patient_therapeutic for this patient. Returns None if no stored rows
    (caller can fall back to computing). Returns [] if the table exists
    but has no rows."""
    try:
        rows = conn.execute("""
            SELECT hypothesis_id, mechanism_template, rank, score, confidence,
                   claim, rationale, generator_id, generator_version, generated_at,
                   score_vector, refined_claim,
                   variant_key, parent_hypothesis_id, mutation_trace, mechanism_family
            FROM patient_hypothesis
            WHERE patient_id = ?
            ORDER BY variant_key, rank
        """, (pid_raw,)).fetchall()
    except sqlite3.OperationalError:
        # Fall back to the old shape if newer columns don't exist yet
        try:
            rows = conn.execute("""
                SELECT hypothesis_id, mechanism_template, rank, score, confidence,
                       claim, rationale, generator_id, generator_version, generated_at,
                       score_vector, refined_claim,
                       NULL AS variant_key, NULL AS parent_hypothesis_id,
                       NULL AS mutation_trace, mechanism_template AS mechanism_family
                FROM patient_hypothesis
                WHERE patient_id = ?
                ORDER BY rank
            """, (pid_raw,)).fetchall()
        except sqlite3.OperationalError:
            try:
                rows = conn.execute("""
                    SELECT hypothesis_id, mechanism_template, rank, score, confidence,
                           claim, rationale, generator_id, generator_version, generated_at,
                           score_vector, NULL AS refined_claim,
                           NULL AS variant_key, NULL AS parent_hypothesis_id,
                           NULL AS mutation_trace, mechanism_template AS mechanism_family
                    FROM patient_hypothesis
                    WHERE patient_id = ?
                    ORDER BY rank
                """, (pid_raw,)).fetchall()
            except sqlite3.OperationalError:
                return None
    if not rows:
        return None

    hyps = []
    for r in rows:
        (hid, tmpl, rank, score, conf, claim, rationale, gen_id, gen_ver, gen_at,
         sv_json, rc_json, variant_key, parent_hyp_id, mutation_trace_json,
         mechanism_family) = r
        try: mutation_trace = json.loads(mutation_trace_json) if mutation_trace_json else None
        except Exception: mutation_trace = None
        # Load premises supporting this hypothesis
        premises = [{
            "premiseId": p[0], "sourceId": p[1], "weight": p[2],
            "rationale": p[3], "evidence": json.loads(p[4]),
            "confidence": p[5], "scope": p[6], "scopeKey": p[7],
        } for p in conn.execute("""
            SELECT hp.premise_id, p.source_id, hp.weight, hp.rationale,
                   p.evidence, p.confidence, p.scope, p.scope_key
            FROM hypothesis_premise hp
            JOIN premise p ON hp.premise_id = p.premise_id
            WHERE hp.hypothesis_id = ?
            ORDER BY ABS(hp.weight) DESC
        """, (hid,))]
        # Load chain-decomposed evidence links (per-layer / per-edge premises)
        chain_rows = conn.execute("""
            SELECT hcl.link_type, hcl.layer_from, hcl.layer_to,
                   hcl.premise_id, hcl.weight, hcl.rationale, p.source_id
            FROM hypothesis_chain_link hcl
            JOIN premise p ON hcl.premise_id = p.premise_id
            WHERE hcl.hypothesis_id = ?
            ORDER BY hcl.link_type, hcl.layer_from, hcl.layer_to
        """, (hid,)).fetchall()
        chain_nodes: dict[str, list[dict]] = {}
        chain_edges: dict[str, list[dict]] = {}
        for (lt, lf, ltc, pid_, w, rat, src) in chain_rows:
            entry = {"premiseId": pid_, "sourceId": src, "weight": w, "rationale": rat}
            if lt == "node":
                chain_nodes.setdefault(lf, []).append(entry)
            else:
                chain_edges.setdefault(f"{lf}->{ltc}", []).append(entry)

        # Score vector (JSON blob written by the bake step)
        try: score_vector = json.loads(sv_json) if sv_json else None
        except Exception: score_vector = None

        # Refined claim (Layer 1 deterministic + Layer 2 LLM). May be null
        # for legacy rows or when LLM was unavailable.
        try: refined_claim = json.loads(rc_json) if rc_json else None
        except Exception: refined_claim = None

        # Load therapeutics attached to this hypothesis
        therapies = [{
            "therapeuticId": t[0], "rank": t[1], "score": t[2], "confidence": t[3],
            "modality": t[4], "design": json.loads(t[5]), "rationale": t[6],
            "eligibilityStatus": t[7],
            "generatorId": t[8], "generatorVersion": t[9],
        } for t in conn.execute("""
            SELECT therapeutic_id, rank, score, confidence, modality, design,
                   rationale, eligibility_status, generator_id, generator_version
            FROM patient_therapeutic
            WHERE hypothesis_id = ?
            ORDER BY rank
        """, (hid,))]

        hyps.append({
            "id": tmpl,                    # legacy: keep template id as 'id' for GUI compat
            "hypothesisId": hid,           # new: full stored-hypothesis id
            "variantKey": variant_key,     # NEW: variant this hypothesis is scoped to
            "parentHypothesisId": parent_hyp_id,   # NEW: Phase 2 mutation lineage (NULL for seeds)
            "mutationTrace": mutation_trace,        # NEW: Phase 2 mutation trace (NULL for seeds)
            "mechanismFamily": mechanism_family,     # NEW: diversity key (= template for seeds)
            "rank": rank,
            "score": score,
            "confidence": conf,
            "fit": rationale,              # legacy: the GUI expects 'fit' as one-liner
            "claim": claim,
            "rationale": rationale,
            "generator": {"id": gen_id, "version": gen_ver, "at": gen_at},
            "premises": premises,
            "therapeutics": therapies,
            "chainLinks": {"nodes": chain_nodes, "edges": chain_edges},
            "scoreVector": score_vector,
            "refinedClaim": refined_claim,
            # patientEvidence retained for backward compat (was per-hypothesis
            # lab bullet list). Rebuilt from lab-scoped premises.
            "patientEvidence": [
                {"labKey": p["evidence"].get("assay", ""),
                 "tone": "supports" if p["weight"] > 0 else "against",
                 "text": p["rationale"] or f"{p['evidence'].get('label', '')}: {p['evidence'].get('value', '')} {p['evidence'].get('unit', '')} [{p['evidence'].get('flag', '')}]"}
                for p in premises if p["sourceId"] == "synthetic_labs"
            ],
        })
    return hyps


def build_patient(seq_num: int, row, isoforms: list[dict], cells: list[dict],
                   conn: sqlite3.Connection,
                   protein_impact_by_key: dict[str, dict] | None = None,
                   lab_phenotype_map: dict[str, dict] | None = None) -> dict:
    (cohort, pid_raw, phen, age, amb, exon_str, nuc, aa, cons, acmg) = row
    uid = make_uid(seq_num)
    exon_n = parse_exon(exon_str)

    # If we can't parse the exon (shouldn't happen with Zhang 2024 data),
    # every isoform is "unknown" — emit but flag.
    iso_impact = []
    iso_hit_map: dict[str, bool] = {}
    for iso in isoforms:
        if exon_n is None:
            hit = None
            reason = "exon position could not be parsed"
        else:
            hit = isoform_hit(iso["firstSharedExon"], exon_n)
            reason = (f"promoter fires at exon {iso['firstSharedExon']} "
                      f"({'≤' if hit else '>'} variant exon {exon_n})")
        iso_hit_map[iso["id"]] = bool(hit) if hit is not None else True
        iso_impact.append({
            "id": iso["id"],
            "label": iso["label"],
            "hit": hit,
            "firstSharedExon": iso["firstSharedExon"],
            "promoterTissue": iso["promoterTissue"],
            "tissues": iso["tissues"],
            "reason": reason,
        })

    cell_impact = []
    for c in cells:
        status = cell_status(iso_hit_map, c["requiresIsoforms"])
        if c["requiresIsoforms"]:
            spared = [i for i in c["requiresIsoforms"] if not iso_hit_map.get(i, True)]
            hit    = [i for i in c["requiresIsoforms"] if iso_hit_map.get(i, True)]
            if status == "hit":
                reason = f"depends on {'+'.join(hit)} — all hit"
            elif status == "spared":
                reason = f"carried by {'+'.join(spared)} — all spared"
            else:
                reason = f"hit: {'+'.join(hit)}; spared: {'+'.join(spared)}"
        else:
            reason = "no isoform mapping curated"
        cell_impact.append({
            "name":   c["name"],
            "tissue": c["tissue"],
            "score":  c["score"],
            "colorHint": c["colorHint"],
            "status": status,
            "reason": reason,
        })

    # Tissue projection: union of tissues from hit isoforms; spared =
    # tissues that appear ONLY on spared isoforms.
    hit_tissues: set[str] = set()
    all_tissues: set[str] = set()
    for iso in isoforms:
        for t in iso["tissues"]:
            all_tissues.add(t)
            if iso_hit_map.get(iso["id"], True):
                hit_tissues.add(t)
    spared_tissues = sorted(all_tissues - hit_tissues)

    # Prefer stored hypotheses from patient_hypothesis (world-model output);
    # fall back to inline scoring if the table is empty or missing (dev safety).
    stored = load_stored_hypotheses(conn, cohort, pid_raw)
    if stored:
        hyp_ranking = stored
    else:
        hyp_ranking = score_hypotheses(cons, phen, exon_n)

    p = {
        "id":       uid,
        "seqNum":   seq_num,
        "cohort":   cohort,
        "cohortPatientId": pid_raw,
        "phenotype": phen,
        "age": age,
        "ambulatory": amb,
        "variant": {
            "exon":       exon_str,
            "exonNum":    exon_n,
            "nucleotide": html.unescape(nuc) if nuc else nuc,
            "aaChange":   html.unescape(aa)  if aa  else aa,
            "consequence": cons,
            "acmg":       acmg,
        },
        "isoformImpact":  iso_impact,
        "cellTypeImpact": cell_impact,
        "tissuesHit":     sorted(hit_tissues),
        "tissuesSpared":  spared_tissues,
    }

    # Labs come from mechanism.sqlite.patient_labs (baked by
    # bake_synthetic_labs.py). If the table is empty for this patient,
    # `labs` is [] and the UI shows an empty tile.
    labs = load_labs(conn, cohort, pid_raw)
    p["labs"] = labs
    # Project labs onto phenotype nodes so downstream views can render lab
    # data as evidence for the phenotype layer of the mechanism chain.
    if lab_phenotype_map:
        p["phenotypesObserved"] = compute_phenotypes_observed(labs, lab_phenotype_map)

    # Attach per-hypothesis patient-specific evidence to the ranking.
    # Stored hypotheses already include patientEvidence (built from lab
    # premises); only the fallback path needs to compute it here.
    for r in hyp_ranking:
        if "patientEvidence" not in r or not r["patientEvidence"]:
            r["patientEvidence"] = patient_evidence_for_hypothesis(r["id"], p, labs)
    p["hypothesisRanking"] = hyp_ranking

    # Group by variant so the UI can render a per-variant "compare 3" block.
    # Phase 1: each patient in the Zhang cohort carries one pathogenic
    # variant, so there is exactly one bucket per patient. Phase 2 will
    # populate multiple buckets naturally when a patient carries ≥ 2 variants.
    by_variant: dict[str, list[dict]] = {}
    for r in hyp_ranking:
        vk = r.get("variantKey") or (p["variant"].get("nucleotide") or "unknown")
        by_variant.setdefault(vk, []).append(r)
    for vk in by_variant:
        by_variant[vk].sort(key=lambda h: h.get("rank", 99))
    p["hypothesisRankingByVariant"] = by_variant

    # Attach ESM3 protein-impact (baked by prototype/ingest/bake_esm3_impact.py).
    # Present only if the bake has been run; else key is absent (frontend
    # renders a "not baked" tile).
    if protein_impact_by_key:
        p["proteinImpact"] = protein_impact_by_key.get(f"{cohort}#{pid_raw}")

    return p


def main() -> None:
    conn = sqlite3.connect(DB)

    isoforms = load_isoforms(conn)
    cells    = load_celltypes(conn)
    gene     = load_gene(conn)

    pheno_breakdown = dict(conn.execute(
        "SELECT phenotype_label, COUNT(*) FROM patient_phenotype GROUP BY phenotype_label"
    ).fetchall())

    # Fetch only the 10 roster patients (not the full cohort). Emit in
    # ROSTER order so sequence numbers reflect the curated ordering.
    roster_keys = [(c, p) for (c, p, _n) in ROSTER]
    rows_by_key = {}
    placeholders = ",".join(["(?,?)"] * len(roster_keys))
    flat = [v for pair in roster_keys for v in pair]
    query = (
        "SELECT cohort, patient_id, phenotype_label, age_years, ambulatory, "
        "       exon, nucleotide, aa_change, consequence, acmg "
        f"FROM patient_phenotype WHERE (cohort, patient_id) IN (VALUES {placeholders})"
    )
    for row in conn.execute(query, flat):
        rows_by_key[(row[0], row[1])] = row

    # Load ESM3 protein-impact bake once (may be empty if the bake hasn't run).
    protein_impact_by_key = load_protein_impact()
    if protein_impact_by_key:
        print(f"[protein_impact] loaded {len(protein_impact_by_key)} variant scores from bake")
    else:
        print(f"[protein_impact] no bake found — Lauren's Protein Impact tile will show a stub")

    # Load the curated lab → phenotype-node mapping.
    lab_phenotype_map = load_lab_phenotype_map()
    if lab_phenotype_map:
        print(f"[lab_phen] loaded {len(lab_phenotype_map)} lab → phenotype-node mappings")

    patients = []
    for i, (cohort, pid) in enumerate(roster_keys, start=1):
        row = rows_by_key.get((cohort, pid))
        if not row:
            print(f"[warn] roster miss: {cohort}#{pid}")
            continue
        patients.append(build_patient(i, row, isoforms, cells, conn,
                                       protein_impact_by_key, lab_phenotype_map))

    # Featured chips = all roster patients (there are only 10).
    featured_ids = [p["id"] for p in patients]

    # Expose the whole cohort's protein-impact table once at top level for the
    # Lauren tab's distribution tile. Keyed by patient uid ("P1", "P2", ...).
    protein_impact_cohort = {}
    for i, (cohort, pid) in enumerate(roster_keys, start=1):
        row = protein_impact_by_key.get(f"{cohort}#{pid}")
        if row: protein_impact_cohort[make_uid(i)] = row

    # Cohort phenotype matrix: rows = patients, cols = phenotype nodes,
    # cell = # abnormal labs supporting that phenotype. Powers the
    # "variants grouped by observed phenotype" viz.
    all_phenotypes = sorted({
        pn for p in patients for pn in (p.get("phenotypesObserved") or {}).keys()
    })
    phenotype_matrix = {
        "phenotypes": all_phenotypes,
        "patients": [
            {
                "id":         p["id"],
                "variant":    {
                    "exon":        p["variant"].get("exon"),
                    "consequence": p["variant"].get("consequence"),
                    "acmg":        p["variant"].get("acmg"),
                },
                "phenotype":  p.get("phenotype"),
                "abnormalByPhenotype": {
                    pn: (p.get("phenotypesObserved") or {}).get(pn, {}).get("nAbnormal", 0)
                    for pn in all_phenotypes
                },
                "totalByPhenotype": {
                    pn: (p.get("phenotypesObserved") or {}).get(pn, {}).get("nEvaluated", 0)
                    for pn in all_phenotypes
                },
            }
            for p in patients
        ],
    }

    payload = {
        "gene":     gene,
        "isoforms": isoforms,
        "cellTypes": cells,
        "patients": patients,
        "featured": featured_ids,
        "proteinImpactCohort": protein_impact_cohort,
        "phenotypeMatrix":     phenotype_matrix,
        "labPhenotypeMap":     lab_phenotype_map,
        "phenoBreakdown": pheno_breakdown,
        "notes": {
            "impactRule": ("isoform hit iff first_shared_exon ≤ variant exon. "
                           "Approximation: exact splice-site consequences and "
                           "in-frame deletion rescue are not modeled."),
            "cellMappingSource": "curated from Muntoni 2003; Pillers 1993; Lidov 1995",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"[wrote] {OUT} ({OUT.stat().st_size / 1024:.1f} KB, "
          f"{len(patients)} patients, {len(isoforms)} isoforms, {len(cells)} cell types)")

    # Sanity: print the featured patients' isoform-impact fingerprints
    # and their top-ranked hypothesis.
    print("\nFeatured patients:")
    by_id = {p["id"]: p for p in patients}
    for fid in featured_ids:
        p = by_id.get(fid)
        if not p:
            print(f"  [{fid}] NOT FOUND")
            continue
        fp = "".join("●" if i["hit"] else "○" for i in p["isoformImpact"])
        top = p["hypothesisRanking"][0]
        print(f"  [{fid}] {p['phenotype']:<7} exon={p['variant']['exon']:<7} "
              f"{p['variant']['consequence']:<11} {fp}  "
              f"top-hyp=H{top['id']}({top['score']})  "
              f"({p['cohort']}#{p['cohortPatientId']})")

    conn.close()


if __name__ == "__main__":
    main()
