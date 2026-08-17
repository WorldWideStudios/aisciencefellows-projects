"""Bake per-hypothesis LLM narratives for the Pareto-frontier hypotheses.

Scope: only the (patient, mechanism_family) hypotheses that appear on the
per-patient Pareto frontier (12,000-row scatter filtered to valid combos).
That's ~22 hypotheses — a targeted Opus pass rather than the full 30.

For each, we assemble the FULL layered-chain evidence bundle:
  - Patient context (variant, phenotype, cohort)
  - Node premises for every biological layer (variant / protein / pathway /
    subcellular / cellType / tissue / phenotype)
  - Edge premises for every transition between layers (protein→subcellular,
    subcellular→cellType, cellType→tissue, etc.)
  - Contradictions with per-position positive vs negative weights
  - The mechanism-family template description
  - The scoreVector (weighted_fit, therapeutic_reach, confidence, layerScores,
    edgeScores) so the LLM knows how strong each part of the chain is

Opus reads all of this and returns a mechanistic narrative that links every
layer through its supporting edges into a single coherent chain — the point
of the panel is to answer "how do these facts fit together to explain the
patient's phenotype?"

Writes:
  workbench/pareto_frontier_narratives.json  — {"{patient}|{hyp_id}": {narrative,
                                                 model, generated}}

Usage:
    ANTHROPIC_API_KEY=... ~/venv/bin/python -m prototype.ingest.bake_pareto_frontier_narratives
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
PATIENT_JSON  = REPO / "workbench" / "patient_data.json"
MECH_JSON     = REPO / "workbench" / "mechanism_data.json"
FRONTIER_JSON = REPO / "workbench" / "frontier_data.json"
OUT_JSON      = REPO / "workbench" / "pareto_frontier_narratives.json"

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")
ENDPOINT = "https://api.anthropic.com/v1/messages"

LAYERS = ["variant", "protein", "pathway", "subcellular",
          "cellType", "tissue", "phenotype"]
LAYER_LABELS = {
    "variant": "Variant", "protein": "Protein", "pathway": "Pathway",
    "subcellular": "Subcellular localisation", "cellType": "Cell type",
    "tissue": "Tissue", "phenotype": "Phenotype",
}


# ── frontier scoping ─────────────────────────────────────────────────────

def frontier_combos() -> list[tuple[str, str]]:
    """Return sorted unique (patient_id, hypothesis_id) pairs on the
    per-patient Pareto frontier — matches the UI's frontierFiltered set."""
    pd = json.loads(PATIENT_JSON.read_text())
    fd = json.loads(FRONTIER_JSON.read_text())
    IDX = {f: i for i, f in enumerate(fd["meta"]["row_fields"])}
    valid = set()
    for p in pd["patients"]:
        for h in p.get("hypothesisRanking") or []:
            valid.add((p["id"], h["id"]))
    rows = [r for r in fd["rows"]
            if (r[IDX["patient"]], r[IDX["mech"]]) in valid]
    by_pat = defaultdict(list)
    for r in rows:
        by_pat[r[IDX["patient"]]].append(r)
    front = set()
    for pt, group in by_pat.items():
        best_aav = -1
        for r in sorted(group, key=lambda r: (-r[IDX["hypothesis_strength"]],)):
            if r[IDX["aav_viability"]] > best_aav + 1e-9:
                front.add((pt, r[IDX["mech"]]))
                best_aav = r[IDX["aav_viability"]]
    return sorted(front)


# ── evidence bundle assembly ─────────────────────────────────────────────

def assemble_bundle(patient: dict, hyp: dict, mech_meta: dict) -> dict:
    """Full evidence bundle for one hypothesis — every node premise, every
    edge premise, every contradiction, plus the scoring context."""
    sv          = hyp.get("scoreVector", {}) or {}
    chain_nodes = (hyp.get("chainLinks") or {}).get("nodes", {}) or {}
    chain_edges = (hyp.get("chainLinks") or {}).get("edges", {}) or {}
    contras     = sv.get("contradictions") or []

    # Node premise entries per biological layer
    nodes_out = {}
    for k in LAYERS:
        entries = chain_nodes.get(k, []) or []
        if not entries:
            continue
        # Enrich each entry with rationale/evidence from the flat premises list
        enriched = []
        premise_by_id = {p.get("premiseId"): p for p in (hyp.get("premises") or [])}
        for e in entries:
            full = premise_by_id.get(e.get("premiseId")) or {}
            enriched.append({
                "premiseId":  e.get("premiseId"),
                "sourceId":   e.get("sourceId"),
                "weight":     e.get("weight"),
                "rationale":  e.get("rationale") or full.get("rationale", ""),
                "evidence":   full.get("evidence", {}) if isinstance(full.get("evidence"), dict) else full.get("evidence"),
            })
        nodes_out[k] = enriched

    # Edge premise entries per biological transition
    edges_out = {}
    for key, entries in chain_edges.items():
        if not entries:
            continue
        enriched = []
        premise_by_id = {p.get("premiseId"): p for p in (hyp.get("premises") or [])}
        for e in entries:
            full = premise_by_id.get(e.get("premiseId")) or {}
            enriched.append({
                "premiseId": e.get("premiseId"),
                "sourceId":  e.get("sourceId"),
                "weight":    e.get("weight"),
                "rationale": e.get("rationale") or full.get("rationale", ""),
            })
        edges_out[key] = enriched

    return {
        "patient": {
            "id":          patient.get("id"),
            "cohort":      patient.get("cohort"),
            "hgvsc":       (patient.get("variant") or {}).get("nucleotide"),
            "hgvsp":       (patient.get("variant") or {}).get("aaChange"),
            "exon":        (patient.get("variant") or {}).get("exon"),
            "consequence": (patient.get("variant") or {}).get("consequence"),
            "phenotype":   patient.get("phenotype"),
            "abnormal_labs": [
                {"label": l.get("label"), "value": l.get("value"),
                 "unit":  l.get("unit"), "flag":  l.get("flag"),
                 "layer": l.get("layer"), "tissue": l.get("tissue")}
                for l in (patient.get("labs") or []) if l.get("flag") != "normal"
            ],
        },
        "mechanism_family": {
            "id":          hyp.get("id"),
            "name":        mech_meta.get("name"),
            "description": (mech_meta.get("detail") or {}).get("lede"),
        },
        "scoring": {
            "aggregate":     sv.get("aggregate"),
            "coverage":      sv.get("coverage"),
            "consistency":   sv.get("consistency"),
            "confidence":    sv.get("confidence"),
            "severity":      sv.get("severity"),
            "treatability":  sv.get("treatability"),
            "layerScores":   sv.get("layerScores"),
            "edgeScores":    sv.get("edgeScores"),
            "chainLinks":    sv.get("chainLinks"),
        },
        "layered_chain": {
            "nodes": nodes_out,
            "edges": edges_out,
        },
        "contradictions": contras,
        "patient_evidence_bullets": hyp.get("patientEvidence") or [],
    }


# ── LLM call ─────────────────────────────────────────────────────────────

def call_opus(bundle: dict, max_tokens: int = 1500,
              timeout: int = 180) -> tuple[str, dict]:
    """Send the bundle to Opus with a mechanism-reasoning prompt.
    Returns (narrative text, usage dict with input_tokens + output_tokens)."""
    system = (
        "You are a rare-disease mechanism analyst. You will receive a full "
        "evidence bundle for ONE candidate hypothesis (patient × mechanism "
        "family) — every premise attached to every biological layer AND "
        "every layer→layer transition. Your job is to write a single "
        "mechanistic narrative that links these facts into ONE coherent "
        "chain from variant to phenotype for this patient.\n\n"
        "REQUIREMENTS:\n"
        "  1. Follow the biological chain in order: variant → protein → "
        "     pathway → subcellular localisation → cell type → tissue → "
        "     phenotype. Use every layer that has premises.\n"
        "  2. For EACH transition, cite the specific edge premise that "
        "     supports it (by rationale, source, or premiseId — whichever "
        "     names the actual evidence). Do not skip transitions with "
        "     evidence.\n"
        "  3. Cite specific values from the input: variant (HGVSc/HGVSp), "
        "     isoform names (Dp427m, Dp140, Dp71 etc.), pathway names, "
        "     cell types, lab values, literature authors. Every specific "
        "     value in your narrative MUST appear in the bundle.\n"
        "  4. If contradictions[] is non-empty, explicitly acknowledge them "
        "     and explain how the mechanism handles the conflicting evidence "
        "     (or why the mechanism is weakened by it).\n"
        "  5. Close with a one-sentence verdict on whether this mechanism "
        "     credibly explains this patient's phenotype, or is a partial / "
        "     secondary contributor.\n"
        "  6. Length: 180–260 words. One paragraph. Clinician-readable. "
        "     Dense, not verbose. No markdown headings, no lists."
    )
    messages = [{
        "role": "user",
        "content": (
            f"Reason across the full layered-chain evidence bundle below and "
            f"write the mechanistic narrative. Return ONLY the narrative "
            f"paragraph — no preamble, no meta-commentary, no headers.\n\n"
            f"```json\n{json.dumps(bundle, indent=2, default=str)}\n```"
        ),
    }]
    body = {
        "model":      MODEL,
        "max_tokens": max_tokens,
        "system":     system,
        "messages":   messages,
    }
    req = urllib.request.Request(
        ENDPOINT,
        method="POST",
        headers={
            "x-api-key":         os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        data=json.dumps(body).encode(),
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    return resp["content"][0]["text"].strip(), resp.get("usage", {})


# ── main ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== Bake Pareto-frontier hypothesis narratives (Opus) ===\n")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Run with:")
        print("  ANTHROPIC_API_KEY=... ~/venv/bin/python -m prototype.ingest.bake_pareto_frontier_narratives")
        sys.exit(2)

    combos = frontier_combos()
    print(f"Pareto-frontier hypotheses to reason over: {len(combos)}")
    for pt, h in combos:
        print(f"  {pt} · H{h}")
    print()

    pd = json.loads(PATIENT_JSON.read_text())
    md = json.loads(MECH_JSON.read_text())
    patients   = {p["id"]: p for p in pd["patients"]}
    mech_by_id = {h["id"]: h for h in md.get("hypotheses", [])}

    # Preserve prior narratives on re-run so we can add new frontier points
    # without paying for the ones already baked.
    prior = {}
    if OUT_JSON.exists():
        try:
            prior = json.loads(OUT_JSON.read_text())
        except Exception:
            prior = {}
    print(f"Existing cached narratives: {len(prior)}\n")

    out = dict(prior)
    for pt_id, hyp_id in combos:
        key = f"{pt_id}|{hyp_id}"
        if key in out:
            print(f"[{key}] cached — skipping")
            continue
        patient = patients.get(pt_id)
        if not patient:
            print(f"[{key}] no patient blob — skipping")
            continue
        hyp = next((h for h in (patient.get("hypothesisRanking") or [])
                    if h.get("id") == hyp_id), None)
        if not hyp:
            print(f"[{key}] no hypothesisRanking entry — skipping")
            continue
        mech_meta = mech_by_id.get(hyp_id) or {}
        bundle = assemble_bundle(patient, hyp, mech_meta)
        print(f"[{key}] calling {MODEL} (nodes={len(bundle['layered_chain']['nodes'])}, "
              f"edges={len(bundle['layered_chain']['edges'])}, "
              f"contras={len(bundle['contradictions'])})...", flush=True)
        try:
            narrative, usage = call_opus(bundle)
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            continue
        # Opus 4.7 pricing (Aug 2025): input $15/M, output $75/M
        in_tok  = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        cost    = in_tok * 15 / 1e6 + out_tok * 75 / 1e6
        out[key] = {
            "patient_id":   pt_id,
            "hypothesis_id": hyp_id,
            "narrative":    narrative,
            "model":        MODEL,
            "generated":    datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n_node_premises": sum(len(v) for v in bundle["layered_chain"]["nodes"].values()),
            "n_edge_premises": sum(len(v) for v in bundle["layered_chain"]["edges"].values()),
            "usage":        {"input_tokens": in_tok, "output_tokens": out_tok,
                             "cost_usd":     round(cost, 4)},
        }
        # Write after each successful call so partial runs aren't lost
        OUT_JSON.write_text(json.dumps(out, indent=2))
        print(f"  ✓ {len(narrative.split())} words · {in_tok} in / {out_tok} out · ${cost:.4f}", flush=True)
        time.sleep(0.6)   # gentle rate-limit

    # Total cost summary
    total = sum(v.get("usage", {}).get("cost_usd", 0) for v in out.values())
    total_in  = sum(v.get("usage", {}).get("input_tokens", 0)  for v in out.values())
    total_out = sum(v.get("usage", {}).get("output_tokens", 0) for v in out.values())
    print(f"\nWrote {len(out)} narratives → {OUT_JSON}")
    print(f"Cumulative usage: {total_in:,} in / {total_out:,} out · ${total:.3f}")


if __name__ == "__main__":
    main()
