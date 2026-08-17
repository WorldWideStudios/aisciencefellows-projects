"""Read data/mechanism.sqlite → write workbench/mechanism_data.json.

Emits a JSON payload matching the shape of the DATA object in
workbench/mechanism.html. Every field is derived from a SELECT; the
query lives next to the assignment so it's obvious what changes when
the substrate tables change.

Run:
    python3 -m prototype.ingest.hydrate_mechanism_view
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "mechanism.sqlite"
OUT = REPO / "workbench" / "mechanism_data.json"

# Palette hint → CSS var. Kept out of SQL so DB stays presentation-neutral.
CVAR = {
    "accent": "var(--accent)", "violet": "var(--violet)", "teal": "var(--teal)",
    "bad": "var(--bad)", "warn": "var(--warn)", "good": "var(--good)",
    "sky": "var(--sky)", "pink": "var(--pink)", "slate": "var(--slate)",
}


def q_one(conn, sql, *args):
    r = conn.execute(sql, args).fetchone()
    return r[0] if r else None


def build_gene(conn):
    r = conn.execute(
        "SELECT symbol, full_name, uniprot, locus, n_exons, locus_size_mb, isoform_names "
        "FROM gene_meta WHERE symbol='DMD'"
    ).fetchone()
    return {
        "symbol": r[0], "fullName": r[1], "uniprot": r[2], "locus": r[3],
        "nExons": r[4], "locusSizeMb": r[5], "isoformNames": json.loads(r[6]),
    }


def build_header(conn):
    return {
        "variantsAnalyzed":    q_one(conn, "SELECT COUNT(*) FROM lovd_variants"),
        "uniqueVariants":      q_one(conn, "SELECT COUNT(DISTINCT dbid) FROM lovd_variants"),
        "phenotyped":          q_one(conn, "SELECT SUM(n_patients) FROM phenotype_summary "
                                            "WHERE cohort='total_2097'"),
        "mechanismConfidence": int(q_one(conn, "SELECT value FROM settings WHERE key='mechanism_confidence'")),
    }


def build_genetic_evidence(conn):
    total = q_one(conn, "SELECT COUNT(*) FROM lovd_variants")
    by_class = dict(conn.execute(
        "SELECT mut_type_class, COUNT(*) FROM lovd_variants GROUP BY mut_type_class"
    ).fetchall())
    struct_pct = round(100 * by_class.get("structural", 0) / total)
    snv_pct    = round(100 * by_class.get("snv", 0)        / total)
    other_pct  = 100 - struct_pct - snv_pct   # keep sum = 100
    top = conn.execute(
        "SELECT mut_type, ROUND(100.0*COUNT(*)/(SELECT COUNT(*) FROM lovd_variants)) "
        "FROM lovd_variants GROUP BY mut_type ORDER BY 2 DESC LIMIT 4"
    ).fetchall()
    footer = " · ".join(f"{k} {int(v)}%" for k, v in top)
    return {
        "total": total,
        "big": f"{total:,}",
        "bigSub": "LOVD-DMD variant reports",
        "breakdown": [
            {"label": "Structural", "pct": struct_pct, "color": CVAR["accent"]},
            {"label": "SNV",        "pct": snv_pct,    "color": CVAR["violet"]},
            {"label": "Other",      "pct": other_pct,  "color": CVAR["teal"]},
        ],
        "footer": footer,
    }


def build_phenotype_dist(conn):
    # Source: Zhang et al. 2024 (Orphanet J Rare Dis, PMC11344408) reports
    # observed clinical distribution across a 2,097-patient cohort. This
    # is the right substrate for the phenotype tile: ClinVar's per-variant
    # labels are submission-biased (~98% DMD), which misrepresents the
    # actual distribution of dystrophinopathy severity in patients.
    rows = conn.execute(
        "SELECT phenotype_label, n_patients FROM phenotype_summary "
        "WHERE cohort='total_2097' ORDER BY n_patients DESC"
    ).fetchall()
    total = sum(n for _, n in rows)
    color = {"DMD": CVAR["bad"], "BMD": CVAR["teal"], "IMD": CVAR["warn"],
             "pending": CVAR["slate"]}
    label_full = {"DMD": "DMD (Duchenne)", "BMD": "BMD (Becker)",
                  "IMD": "IMD (intermediate)", "pending": "Undetermined"}
    segs = [{"label": label_full.get(l, l), "pct": round(100 * n / total),
             "color": color.get(l, CVAR["slate"])} for l, n in rows]
    top_label, top_n = rows[0]
    return {
        "segments": segs,
        "center": {
            "value": f"{round(100 * top_n / total)}%",
            "label": label_full.get(top_label, top_label),
        },
        "footer": f"Zhang et al. 2024 · N={total:,} patients",
    }


def build_isoform_impact(conn):
    total_exons = q_one(conn, "SELECT n_exons FROM gene_meta WHERE symbol='DMD'")
    rows = conn.execute(
        f"SELECT eu.isoform_id, ROUND(100.0 * SUM(eu.used) / {total_exons}) "
        "FROM exon_usage eu JOIN isoforms i USING (isoform_id) "
        "GROUP BY eu.isoform_id ORDER BY 2 DESC, i.rank"
    ).fetchall()

    def color_for(pct: float) -> str:
        if pct >= 90:  return CVAR["bad"]
        if pct >= 40:  return CVAR["warn"]
        return CVAR["teal"]

    return {
        "rows": [{"label": iso, "value": int(pct), "unit": "%", "color": color_for(pct)}
                 for iso, pct in rows],
        "max": 100,
        "footer": f"Exon coverage of NM_004006.2 ({total_exons} exons)",
    }


def build_hbar(conn, sql: str, footer: str, hard_max: float | None = None):
    rows = conn.execute(sql).fetchall()
    max_v = hard_max if hard_max is not None else (max((r[1] for r in rows), default=1))
    return {
        "rows": [{"label": r[0], "value": r[1], "color": CVAR.get(r[2], CVAR["slate"])}
                 for r in rows],
        "max": max_v,
        "footer": footer,
    }


def build_hypotheses(conn):
    out = []
    for h in conn.execute(
        "SELECT id, rank, name, subtitle, supporting_variants, odds_ratio, "
        "evidence_score, druggability, therapeutic, selected, lede "
        "FROM hypotheses ORDER BY rank"
    ).fetchall():
        hid = h[0]
        row = {
            "id": h[0], "name": h[2], "subtitle": h[3],
            "supporting": h[4], "oddsRatio": h[5], "evidence": h[6],
            "druggability": h[7], "therapeutic": h[8], "selected": bool(h[9]),
        }
        evi = conn.execute(
            "SELECT tone, text, citation FROM hypothesis_evidence "
            "WHERE hypothesis_id=? ORDER BY ord", (hid,)
        ).fetchall()
        nodes = conn.execute(
            "SELECT node_id, col, row, tier, label1, label2, meta "
            "FROM hypothesis_chain_nodes WHERE hypothesis_id=?", (hid,)
        ).fetchall()
        edges = conn.execute(
            "SELECT from_node, to_node FROM hypothesis_chain_edges WHERE hypothesis_id=?",
            (hid,)
        ).fetchall()
        # Group edge evidence by (from, to). Empty list if none curated.
        edge_evi: dict[tuple[str, str], list[dict]] = {}
        for (a, b, tone, text, cite) in conn.execute(
            "SELECT from_node, to_node, tone, text, citation "
            "FROM hypothesis_chain_edge_evidence WHERE hypothesis_id=? "
            "ORDER BY from_node, to_node, ord", (hid,)
        ):
            edge_evi.setdefault((a, b), []).append(
                {"tone": tone, "text": text, "cite": cite})
        therapy = conn.execute(
            "SELECT label1, label2 FROM hypothesis_therapeutic_node WHERE hypothesis_id=?",
            (hid,)
        ).fetchone()

        if h[10] or evi or nodes:  # detail present iff we have lede/evidence/chain
            row["detail"] = {
                "lede": h[10],
                "evidence": [{"tone": t, "text": x, "cite": c} for (t, x, c) in evi],
                "chain": ({
                    "nodes": [{"id": n[0], "col": n[1], "row": n[2], "tier": n[3],
                               "label1": n[4], "label2": n[5], "meta": n[6]} for n in nodes],
                    "edges": [{"from": e[0], "to": e[1],
                               "id": f"{e[0]}-{e[1]}",
                               "evidence": edge_evi.get((e[0], e[1]), [])} for e in edges],
                    "therapeutic": ({"label1": therapy[0], "label2": therapy[1]}
                                    if therapy else None),
                } if nodes else None),
            }
        out.append(row)
    return out


# ======================================================================
# NMD × ACMG cross-tab from ClinVar (for the Marimekko widget).
# ----------------------------------------------------------------------
# For each ClinVar DMD variant, classify:
#   - ACMG: benign | uncertain | pathogenic
#   - NMD:  triggering | escaping | transcript_dependent
#
# NMD classification rules (approximation of Popp & Maquat 2013):
#   - Nonsense (p.XxxNNNTer or p.XxxNNN*)
#       → PTC at codon NNN. NMD-eligible if NNN < 3600 (roughly ex ≤ 78),
#         NMD-escape if NNN ≥ 3600 (last exon of Dp427m at ~aa 3580-3685).
#   - Frameshift (fs) → creates downstream PTC → NMD-triggering
#   - Splice-site (c.*+1/2, c.*-1/2 near splice site) → exon skipping →
#         PTC → NMD-triggering
#   - Missense, synonymous, in-frame indel, promoter deletion, gross del
#         → no PTC → transcript_dependent (protein-level or dose-level effect)
# ======================================================================

DMD_PROTEIN_LEN = 3685              # Dp427m
NMD_ESCAPE_AA_THRESHOLD = 3600      # PTCs beyond this are in the last exon


def classify_variant_nmd(clin_sig: str | None, variant_name: str | None) -> tuple[str, str]:
    cs = (clin_sig or '').lower()
    if 'conflicting' in cs or 'not provided' in cs or 'no classification' in cs or cs.strip() in ('', '-'):
        acmg = 'uncertain'
    elif 'uncertain' in cs:
        acmg = 'uncertain'
    elif 'benign' in cs:
        acmg = 'benign'
    elif 'pathogenic' in cs:
        acmg = 'pathogenic'
    else:
        acmg = 'uncertain'

    name = variant_name or ''
    # nonsense: p.(XxxNNNTer) or p.XxxNNN* or p.(XxxNNN*)
    m = re.search(r'p\.\(?[A-Za-z]{3}(\d+)(?:Ter|\*)\)?', name)
    if m:
        pos = int(m.group(1))
        return acmg, ('escape' if pos >= NMD_ESCAPE_AA_THRESHOLD else 'triggering')
    # frameshift
    if re.search(r'fs\*?\d*', name):
        return acmg, 'triggering'
    # canonical splice-site (c.NNN+1..+2 or -1..-2)
    if re.search(r'c\.\d+[+-][12](?![0-9])', name):
        return acmg, 'triggering'
    # everything else — missense, synonymous, in-frame indel, gross del,
    # promoter changes: no PTC per se; effect is transcript-context-dependent
    return acmg, 'transcript_dependent'


def _classify_consequence(variant_name: str | None) -> str:
    """Classify a ClinVar variant_name into a consequence class.

    Order matters — the most specific patterns match first. Returns one of:
      nonsense · frameshift · splice · missense · inframe_indel · large_del · other
    """
    name = variant_name or ''
    # HGVSp-based signals (most reliable)
    if re.search(r'p\.\(?[A-Za-z]{3}\d+(?:Ter|\*)\)?', name):
        return 'nonsense'
    if re.search(r'fs\*?\d*', name):
        return 'frameshift'
    # Canonical splice sites (c.NNN+/-1..2, or intron in variant_name)
    if re.search(r'c\.\d+[+-][12](?![0-9])', name) or 'IVS' in name:
        return 'splice'
    # Large gross deletions — spanning-exon syntax or multi-kb dels
    if re.search(r'ex(?:on)?\s*\d+.*(del|dup)', name, re.I) or re.search(r'c\.[-\d]+_[-\d]+del', name):
        return 'large_del'
    # HGVSc-based single-nt deletion/duplication without HGVSp → frameshift
    if re.search(r'c\.\d+[+_-]?\d*(?:del|dup)', name) and 'p.' not in name:
        return 'frameshift'
    # Missense: p.XxxNNNYyy where Yyy is a different amino acid (not Ter/fs)
    if re.search(r'p\.\(?[A-Za-z]{3}\d+[A-Za-z]{3}\)?', name):
        return 'missense'
    return 'other'


def build_clinvar_composition(conn) -> dict:
    """Aggregate ClinVar Pathogenic + Likely Pathogenic DMD variants by
    consequence class. Powers Lauren's Genetic Variants tile."""
    CATS = ['nonsense', 'frameshift', 'splice', 'missense', 'inframe_indel',
            'large_del', 'other']
    counts = {c: 0 for c in CATS}
    for (cs, name) in conn.execute(
        "SELECT clin_sig, variant_name FROM clinvar_phenotype "
        "WHERE data_source='clinvar' AND clin_sig IN "
        "('Pathogenic', 'Likely pathogenic', 'Pathogenic/Likely pathogenic')"
    ):
        counts[_classify_consequence(name)] += 1
    total = sum(counts.values())
    breakdown = [{"label": k, "n": v, "pct": round(100.0 * v / total, 1) if total else 0.0}
                 for k, v in sorted(counts.items(), key=lambda kv: -kv[1]) if v > 0]
    return {
        "source":  "ClinVar (variation_id where DMD gene, P + LP + P/LP)",
        "total":   total,
        "breakdown": breakdown,
        "categories": CATS,
    }


def _nmd_escape_variants(conn) -> list[dict]:
    """List the specific pathogenic NMD-escape variants + their residue positions.
    Powers Lauren's Protein Impact tile (consensus-truncated protein bar).
    Filters: ClinVar Pathogenic/LP + PTC-generating + residue >= threshold."""
    out: list[dict] = []
    ptc_re = re.compile(r'p\.\(?[A-Za-z]{3}(\d+)(?:Ter|\*)\)?')
    fs_re  = re.compile(r'p\.\(?[A-Za-z]{3}(\d+)[A-Za-z]{3}fs')
    for (name, cs) in conn.execute(
        "SELECT variant_name, clin_sig FROM clinvar_phenotype "
        "WHERE data_source='clinvar' AND clin_sig IN "
        "('Pathogenic','Likely pathogenic','Pathogenic/Likely pathogenic')"
    ):
        name = name or ''
        m = ptc_re.search(name)
        r, cls = (None, None)
        if m:
            r, cls = int(m.group(1)), 'nonsense'
        else:
            m = fs_re.search(name)
            if m:
                r, cls = int(m.group(1)), 'frameshift'
        if r is None or r < NMD_ESCAPE_AA_THRESHOLD:
            continue
        out.append({
            "variantName": name,
            "residue":     r,
            "consequence": cls,
            "clinSig":     cs,
        })
    out.sort(key=lambda x: x["residue"])
    return out


def build_nmd_cohort(conn) -> dict:
    NMD_CATS = ('triggering', 'transcript_dependent', 'escape')
    ACMG_CATS = ('benign', 'uncertain', 'pathogenic')
    grid = {a: {n: 0 for n in NMD_CATS} for a in ACMG_CATS}
    total = 0
    for (cs, nm) in conn.execute(
        "SELECT clin_sig, variant_name FROM clinvar_phenotype"
    ):
        acmg, nmd = classify_variant_nmd(cs, nm)
        grid[acmg][nmd] += 1
        total += 1
    acmg_totals = {a: sum(grid[a].values()) for a in ACMG_CATS}
    nmd_totals  = {n: sum(grid[a][n] for a in ACMG_CATS) for n in NMD_CATS}
    return {
        "source": "ClinVar DMD variant subset",
        "total": total,
        "acmgOrder": list(ACMG_CATS),
        "nmdOrder":  list(NMD_CATS),
        "acmgTotals": acmg_totals,
        "nmdTotals":  nmd_totals,
        "grid": grid,
        "escapeVariants": _nmd_escape_variants(conn),
        "rules": {
            "nmd_escape_aa_threshold": NMD_ESCAPE_AA_THRESHOLD,
            "protein_length": DMD_PROTEIN_LEN,
            "notes": ("Approximation of Popp & Maquat 2013: PTCs upstream of "
                      "the last exon-exon junction trigger NMD; late PTCs escape. "
                      "Splice-site variants are assumed to trigger NMD via "
                      "exon skipping. In-frame and missense variants are "
                      "'transcript-dependent' — no PTC generated."),
        },
    }


def build_premise_sources(conn) -> list[dict]:
    """Return the premise-source registry plus per-source count of
    baked premises. Used by the substrate explorer artifact."""
    try:
        rows = conn.execute(
            "SELECT source_id, source_type, version, description, reference_url "
            "FROM premise_source ORDER BY source_id"
        ).fetchall()
    except Exception:
        return []
    counts = dict(conn.execute(
        "SELECT source_id, COUNT(*) FROM premise GROUP BY source_id"
    ).fetchall())
    hyp_counts = dict(conn.execute(
        "SELECT p.source_id, COUNT(DISTINCT hp.hypothesis_id) "
        "FROM hypothesis_premise hp JOIN premise p ON hp.premise_id = p.premise_id "
        "GROUP BY p.source_id"
    ).fetchall())
    return [
        {"sourceId": sid, "type": stype, "version": ver,
         "description": desc, "url": url,
         "nPremises": counts.get(sid, 0),
         "nHypothesesFired": hyp_counts.get(sid, 0)}
        for (sid, stype, ver, desc, url) in rows
    ]


def _load_exon_coords() -> list[dict]:
    """Load data/variants/dmd_exon_coords.tsv → list of {exon, c_start, c_end}
    for exons that fall entirely or partially inside the CDS."""
    path = Path(__file__).resolve().parent.parent.parent / "data" / "variants" / "dmd_exon_coords.tsv"
    if not path.exists():
        return []
    rows: list[dict] = []
    header = None
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"): continue
        parts = line.split("\t")
        if header is None:
            header = parts
            continue
        r = dict(zip(header, parts))
        rows.append({
            "exon":    int(r["exon_num"]),
            "c_start": int(r["c_start"]),
            "c_end":   int(r["c_end"]),
        })
    return rows


def _load_isoforms() -> list[dict]:
    path = Path(__file__).resolve().parent.parent.parent / "data" / "variants" / "dmd_isoforms.tsv"
    rows: list[dict] = []
    header = None
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"): continue
        parts = line.split("\t")
        if header is None:
            header = parts
            continue
        r = dict(zip(header, parts))
        rows.append({
            "id":              r["isoform_id"],
            "firstSharedExon": int(r["first_shared_exon"]),
            "promoterTissue":  r.get("promoter_tissue", ""),
        })
    return rows


# Parse a c-coord (int) out of a ClinVar variant_name. Handles:
#   NM_004006.3(DMD):c.3469G>T           → 3469
#   NM_004006.3(DMD):c.6540del           → 6540
#   NM_004006.3(DMD):c.9974+2T>A         → 9974  (splice-donor + offset)
#   NM_004006.3(DMD):c.9225-285A>G       → 9225  (deep intronic - offset)
#   c.NNN_MMM del / dup                  → NNN
_CDOT_RE = re.compile(r'c\.(-?\d+)')


def _c_pos_to_exon(c_pos: int, exon_coords: list[dict]) -> int | None:
    """Return the exon number containing this c-coordinate. Uses the first
    exon whose [c_start, c_end] range brackets c_pos. Splice-flank offsets
    (e.g. c.9974+2) are treated as belonging to the exon at the anchor
    position (9974), which is what the caller extracts."""
    if c_pos < 1: return None
    for e in exon_coords:
        if e["c_start"] <= c_pos <= e["c_end"]:
            return e["exon"]
    return None


def build_isoform_variant_counts(conn) -> dict:
    """For each of the 7 DMD isoforms, count how many ClinVar pathogenic
    variants land at exon ≥ isoform.first_shared_exon (i.e. hit that isoform).

    Counts are NESTED — every variant hits Dp427* (first shared exon = 1),
    a subset also hits Dp260 (≥ ex30), a smaller subset hits Dp140 (≥ ex45),
    etc. So Dp71 count ⊂ Dp116 count ⊂ Dp140 count ⊂ Dp260 count ⊂ Dp427*.

    Returns { source, denominator, unparseable, isoforms: [{id, firstSharedExon,
             promoterTissue, nHits, pct}...] }
    """
    exon_coords = _load_exon_coords()
    if not exon_coords:
        return {"error": "dmd_exon_coords.tsv missing — run bake_dmd_exon_coords"}
    isoforms = _load_isoforms()

    total = 0
    unparseable = 0
    variant_rows: list[tuple[int, str]] = []   # (exon, category) per parseable variant
    for (name,) in conn.execute(
        "SELECT variant_name FROM clinvar_phenotype "
        "WHERE data_source='clinvar' AND clin_sig IN "
        "('Pathogenic','Likely pathogenic','Pathogenic/Likely pathogenic')"
    ):
        total += 1
        if not name:
            unparseable += 1
            continue
        m = _CDOT_RE.search(name)
        if not m:
            unparseable += 1
            continue
        try:
            c_pos = int(m.group(1))
        except ValueError:
            unparseable += 1
            continue
        exon = _c_pos_to_exon(c_pos, exon_coords)
        if exon is None:
            unparseable += 1
            continue
        category = _classify_consequence(name)
        variant_rows.append((exon, category))

    n_parsed = len(variant_rows)
    # Categories to expose (drop those with 0 counts to keep the table clean)
    all_cats = ['nonsense', 'frameshift', 'splice', 'missense',
                'inframe_indel', 'large_del', 'other']
    cat_totals = {c: sum(1 for (_e, cc) in variant_rows if cc == c) for c in all_cats}
    active_cats = [c for c in all_cats if cat_totals[c] > 0]

    # Re-parse each variant for its NMD outcome using the same classifier
    # that drives the NMD tile (classify_variant_nmd). Cache by variant name.
    nmd_rows: list[tuple[int, str]] = []
    for (name,) in conn.execute(
        "SELECT variant_name FROM clinvar_phenotype "
        "WHERE data_source='clinvar' AND clin_sig IN "
        "('Pathogenic','Likely pathogenic','Pathogenic/Likely pathogenic')"
    ):
        if not name: continue
        m = _CDOT_RE.search(name)
        if not m: continue
        try:
            c_pos = int(m.group(1))
        except ValueError:
            continue
        exon = _c_pos_to_exon(c_pos, exon_coords)
        if exon is None: continue
        _acmg, nmd_outcome = classify_variant_nmd('Pathogenic', name)
        nmd_rows.append((exon, nmd_outcome))
    NMD_CATS = ['triggering', 'escape', 'transcript_dependent']
    nmd_totals = {n: sum(1 for (_e, nn) in nmd_rows if nn == n) for n in NMD_CATS}

    iso_rows: list[dict] = []
    for iso in isoforms:
        f = iso["firstSharedExon"]
        n_hits = sum(1 for (e, _c) in variant_rows if e >= f)
        by_cat = {c: sum(1 for (e, cc) in variant_rows if e >= f and cc == c) for c in active_cats}
        by_nmd = {n: sum(1 for (e, nn) in nmd_rows  if e >= f and nn == n) for n in NMD_CATS}
        iso_rows.append({
            **iso,
            "nHits":       n_hits,
            "pct":         round(100.0 * n_hits / n_parsed, 1) if n_parsed else 0.0,
            "byCategory":  by_cat,
            "byNmd":       by_nmd,
        })
    return {
        "source":       "ClinVar (P + LP + P/LP) × dmd_exon_coords · nested per-isoform hits",
        "denominator":  total,
        "parsed":       n_parsed,
        "unparseable":  unparseable,
        "note":         "counts are nested — variant hits isoform iff variant_exon ≥ first_shared_exon",
        "categories":   active_cats,
        "categoryTotals": {c: cat_totals[c] for c in active_cats},
        "nmdCategories": NMD_CATS,
        "nmdTotals":    nmd_totals,
        "isoforms":     iso_rows,
    }


def build_celltype_ranking(conn) -> dict | None:
    """Rank cell types by DGC-COMPLETENESS × CLINICAL-RELEVANCE.

    DGC-completeness alone (# of DMD's 13 partners co-expressed) surfaces
    cells where the DGC is molecularly complete — but that includes false
    positives like thymic myoid cells (which recapitulate muscle protein
    expression for T-cell tolerance, not because they need the DGC to
    function). Weighting by TISSUE_RELEVANCE keeps molecular completeness
    but demotes cells whose tissue is not clinically implicated in DMD.
    """
    DGC_MEMBERS = ['DMD', 'DAG1', 'SNTA1', 'SNTB1', 'SNTB2', 'SGCA', 'SGCB',
                   'SGCD', 'SGCG', 'DTNA', 'DTNB', 'UTRN', 'CAV3', 'SSPN']
    # Clinical relevance to DMD/BMD symptoms per tissue (curated from Muntoni
    # 2003 + DMD symptom literature). Weight 1.0 = primary clinical driver,
    # 0.0 = molecular presence but no known DMD role.
    TISSUE_RELEVANCE = {
        "skeletal_muscle":  1.00,   # progressive weakness, wheelchair — the disease
        "heart":            0.95,   # cardiomyopathy is the leading cause of death in DMD
        "cns":              0.60,   # cognitive comorbidity (Dp140, Dp427c/p)
        "retina":           0.55,   # ERG changes; Dp260 loss
        "peripheral_nerve": 0.30,   # Schwann cells; Dp116 loss (subclinical usually)
        "smooth_muscle":    0.30,   # some GI dysmotility in DMD
        "vascular":         0.25,   # vessel wall utrophin; indirect
        "kidney":           0.20,   # Dp71 in podocytes; subclinical
        "liver":            0.15,   # Dp71 present; no clear DMD role
        "adipose":          0.10,   # metabolic changes; role unclear
        "salivary_gland":   0.05,   # muscle-adjacent, clinically silent for DMD
        "breast":           0.05,
        "prostate":         0.05,
        "thymus":           0.00,   # thymic myoid cells → myasthenia gravis, NOT DMD
        "other":            0.15,   # unknown default
    }
    placeholders = ",".join(["?"] * len(DGC_MEMBERS))
    rows = conn.execute(
        f"""
        SELECT cell_type, tissue,
               COUNT(DISTINCT gene_symbol) AS n_dgc_members,
               AVG(score)                  AS mean_score
        FROM celltype_expression
        WHERE gene_symbol IN ({placeholders}) AND source='hpa'
        GROUP BY cell_type, tissue
        """,
        DGC_MEMBERS,
    ).fetchall()
    # For each cell type, list which DGC members are present (helpful in the UI)
    members_by_cell: dict[str, list[str]] = {}
    for (ct, gene) in conn.execute(
        f"SELECT cell_type, gene_symbol FROM celltype_expression "
        f"WHERE gene_symbol IN ({placeholders}) AND source='hpa'",
        DGC_MEMBERS,
    ):
        members_by_cell.setdefault(ct, []).append(gene)

    # Fix a small bug in the partner bake's tissue classifier: cardiomyocytes
    # got tagged as skeletal_muscle because "cardiomyocyte" contains "myocyte".
    # Reclassify from the cell_type name to the correct tissue for scoring.
    def _fix_tissue(cell_type: str, tissue: str) -> str:
        n = (cell_type or '').lower()
        if 'cardiomyocyte' in n:                              return 'heart'
        if any(k in n for k in ('astrocyte', 'purkinje',
                'cerebell', 'bergmann', 'choroid plexus',
                'neuron', 'glia')):                           return 'cns'
        if 'schwann' in n:                                    return 'peripheral_nerve'
        return tissue

    entries = []
    for (ct, tissue, n_dgc, mean_score) in rows:
        pct = 100.0 * n_dgc / len(DGC_MEMBERS)
        tissue_fixed = _fix_tissue(ct, tissue)
        relevance = TISSUE_RELEVANCE.get(tissue_fixed, TISSUE_RELEVANCE["other"])
        # Weighted score: DGC-completeness × clinical relevance. Magnitude
        # kept as a very-small tiebreaker so cells with identical (n, relevance)
        # rank consistently.
        weighted = round(n_dgc * relevance + (mean_score / 1000.0 if mean_score else 0.0), 3)
        entries.append({
            "cellType":         ct,
            "tissue":           tissue_fixed,
            "nDgcMembers":      n_dgc,
            "totalDgcMembers":  len(DGC_MEMBERS),
            "completenessPct":  round(pct, 1),
            "meanScore":        round(mean_score, 2) if mean_score is not None else None,
            "clinicalRelevance": relevance,
            "weightedScore":    weighted,
            "members":          sorted(members_by_cell.get(ct, [])),
            "hasDmd":           'DMD' in members_by_cell.get(ct, []),
        })
    entries.sort(key=lambda x: -x["weightedScore"])
    return {
        "method":           "DGC-completeness × clinical-tissue-relevance",
        "dgcMembers":       DGC_MEMBERS,
        "nDgcMembers":      len(DGC_MEMBERS),
        "tissueRelevance":  TISSUE_RELEVANCE,
        "cellTypes":        entries,
    }


def build_pathway_ranking(conn) -> dict | None:
    """Rank pathways containing DMD by INTERACTOR-COVERAGE DENSITY, not by
    pathway size. For each Reactome pathway containing DMD, count how many
    of DMD's top STRING/Open-Targets interactors are also members. Density =
    interactors_in_pathway / total_members. Higher density = pathway is
    more DMD-embedded (the pathway IS the DGC neighborhood, not a
    coincidental umbrella term)."""
    # Interactor list: DMD itself + top STRING/OT interactors.
    interactor_row = conn.execute(
        "SELECT evidence FROM premise WHERE source_id='open_targets' LIMIT 1"
    ).fetchone()
    interactors: list[str] = ['DMD']
    if interactor_row:
        try:
            ev = json.loads(interactor_row[0])
            for x in (ev.get('interactions') or []):
                sym = x.get('symbol')
                if sym and sym not in interactors:
                    interactors.append(sym)
        except Exception:
            pass
    if len(interactors) < 2:
        return {"error": "openTargets interactor list missing — re-bake"}

    # Attach to the pathways.sqlite side database
    conn.execute("ATTACH DATABASE ? AS pw",
                 [str(Path(__file__).resolve().parent.parent.parent / "data" / "pathways.sqlite")])
    try:
        placeholders = ",".join(["?"] * len(interactors))
        rows = conn.execute(
            f"""
            SELECT
              gp.pathway_id, gp.pathway_name,
              COUNT(DISTINCT gp.gene_symbol) AS n_interactors_in_path,
              (SELECT COUNT(*) FROM pw.gene_pathway WHERE pathway_id=gp.pathway_id) AS n_members
            FROM pw.gene_pathway gp
            WHERE gp.pathway_id IN (
              SELECT pathway_id FROM pw.gene_pathway WHERE gene_symbol='DMD'
            )
            AND gp.gene_symbol IN ({placeholders})
            GROUP BY gp.pathway_id, gp.pathway_name
            """,
            interactors,
        ).fetchall()
    finally:
        conn.execute("DETACH DATABASE pw")

    entries = []
    for (pid, pname, n_int, n_mem) in rows:
        density = n_int / n_mem if n_mem else 0.0
        entries.append({
            "pathwayId":         pid,
            "name":              pname,
            "nInteractors":      n_int,
            "nMembers":          n_mem,
            "densityPct":        round(density * 100, 1),
            "coveragePctOfInteractors": round(100.0 * n_int / len(interactors), 1),
        })
    entries.sort(key=lambda x: (-x["densityPct"], -x["nInteractors"]))
    return {
        "method":     "interactor-coverage density (n_interactors_in_path / n_pathway_members)",
        "interactors": interactors,
        "nInteractors": len(interactors),
        "pathways":   entries,
    }


def build_open_targets(conn) -> dict | None:
    """Return the Open Targets DMD summary if the bake has been run;
    None otherwise. Emits a compact shape sized for direct rendering."""
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
    tract_by_mod: dict[str, list[str]] = {}
    for mod, label, val in conn.execute(
        "SELECT modality, label, value FROM opentargets_dmd_tractability"
    ):
        tract_by_mod.setdefault(mod, []).append({"label": label, "value": bool(val)})
    return {
        "ensemblId":    ensembl_id,
        "symbol":       symbol,
        "name":         name,
        "biotype":      biotype,
        "refreshedAt":  refreshed_at,
        "sourceUrl":    source_url,
        "tractability": tract_by_mod,
        "pathways": [
            {"id": r[0], "name": r[1], "topLevel": r[2]}
            for r in conn.execute(
                "SELECT pathway_id, pathway, top_level_term FROM opentargets_dmd_pathway"
            )
        ],
        "topDiseases": [
            {"id": r[0], "name": r[1], "score": r[2]}
            for r in conn.execute(
                "SELECT disease_id, disease_name, score "
                "FROM opentargets_dmd_disease ORDER BY score DESC LIMIT 10"
            )
        ],
        "drugs": [
            {"id": r[0], "name": r[1], "type": r[2],
             "maxStage": r[3], "drugMaxStage": r[4]}
            for r in conn.execute(
                "SELECT drug_id, drug_name, drug_type, max_clinical_stage, "
                "       drug_max_stage FROM opentargets_dmd_drug"
            )
        ],
        "interactions": [
            {"partnerId": r[0], "symbol": r[1], "score": r[2], "source": r[3]}
            for r in conn.execute(
                "SELECT partner_id, partner_symbol, score, source_database "
                "FROM opentargets_dmd_interaction "
                "WHERE partner_symbol IS NOT NULL "
                "ORDER BY score DESC LIMIT 20"
            )
        ],
    }


def main() -> None:
    conn = sqlite3.connect(DB)
    data = {
        "gene":   build_gene(conn),
        "header": build_header(conn),
        "tiles": {
            "geneticEvidence": build_genetic_evidence(conn),
            "phenotypeDist":   build_phenotype_dist(conn),
            "isoformImpact":   build_isoform_impact(conn),
            "cellTypes": build_hbar(conn,
                "SELECT cell_type, score, color_hint FROM celltype_expression "
                "WHERE gene_symbol='DMD' ORDER BY score DESC LIMIT 7",
                "Human Protein Atlas · nCPM (log-scaled)",
                hard_max=10),
            "pathways": build_hbar(conn,
                "SELECT pathway_name, score, color_hint FROM pathway_enrichment "
                "WHERE gene_symbol='DMD' ORDER BY score DESC LIMIT 7",
                "Reactome membership · specificity = 10 − log(n_genes)",
                hard_max=10),
        },
        "hypotheses": build_hypotheses(conn),
        "hypothesesMeta": {
            "top":   q_one(conn, "SELECT COUNT(*) FROM hypotheses"),
            "total": q_one(conn, "SELECT COUNT(*) FROM lovd_variants"),
            "unit":  "hypotheses shown",
        },
        "nmdCohort":     build_nmd_cohort(conn),
        "clinvarComposition": build_clinvar_composition(conn),
        "isoformVariantCounts": build_isoform_variant_counts(conn),
        "openTargets":   build_open_targets(conn),
        "pathwayRanking": build_pathway_ranking(conn),
        "celltypeRanking": build_celltype_ranking(conn),
        "premiseSources": build_premise_sources(conn),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"[wrote] {OUT} ({OUT.stat().st_size / 1024:.1f} KB)")
    conn.close()


if __name__ == "__main__":
    main()
