"""Chat backend for the DMD workbench Explore Data tab.

Turns a natural-language user query into a set of pre-baked chart-renderer
invocations by giving Claude Sonnet 4.6 a tool schema for each of the 17
renderers exposed by workbench/patient_chat.html.

The model doesn't reason about the underlying data; it picks WHICH renderers
to invoke and WHAT FILTERS to pass. The frontend does the rendering.

Run:
    ANTHROPIC_API_KEY=... ~/venv/bin/python -m prototype.workbench.chat_server
    # → listens on 127.0.0.1:8766

Endpoints:
    GET  /health
    POST /chat  { messages: [...], patient: {...} }
      → { text: str, artifacts: [{renderer, filter, qid}, ...] }
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

ANTHROPIC_URL   = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Tool schemas — one per renderer. `input_schema.properties` declares the
# filter dimensions the frontend renderer knows how to apply. Descriptions
# are what the LLM reads to decide which tool to invoke.
#
# The frontend renderer keys (patient_chat.html DATA_CHIPS[].renderer) MUST
# match the second half of the tool name (render_<key>).
TOOLS = [
    {"name": "render_variants_table",
     "description": "Cohort variants table. Shows every patient in the Zhang cohort with their variant (exon, HGVSc, HGVSp, consequence, ACMG) and phenotype. This patient's row is highlighted.",
     "input_schema": {"type": "object", "properties": {
         "consequence": {"type": "string", "description": "Filter to one consequence class, e.g. 'frameshift', 'nonsense', 'splice-site'."},
         "acmg":        {"type": "string", "description": "Filter to one ACMG class, e.g. 'P', 'LP'."},
     }, "additionalProperties": False}},

    {"name": "render_labs_summary",
     "description": "This patient's abnormal labs, grouped by biological-organization layer the lab probes (cellType, tissue, etc.).",
     "input_schema": {"type": "object", "properties": {
         "layer": {"type": "string", "description": "Filter to labs at one layer, e.g. 'cellType', 'tissueType', 'phenotype'."},
         "flag":  {"type": "string", "description": "Filter to abnormal direction, 'high' or 'low'."},
     }, "additionalProperties": False}},

    {"name": "render_variant_card",
     "description": "This patient's variant details card (exon, HGVSc, HGVSp, consequence, ACMG, phenotype, age, ambulatory).",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_variant_lollipop",
     "description": "Genotype-phenotype map: DMD variants plotted along the gene (X = exon 1-79) grouped by sub-phenotype (Y rows = DMD / BMD / IMD / DCM / Cognitive). Marker size = frequency, color = phenotype. Answers 'does variant position along DMD explain phenotype?' — shows the exon 44-55 deletion hotspot, proximal DCM cluster, distal Dp140/Dp71 cognitive cluster. This patient's variant is highlighted. Markers are clickable — open a variant detail modal.",
     "input_schema": {"type": "object", "properties": {
         "phenotype": {"type": "string", "description": "Filter to one sub-phenotype row, e.g. 'DMD', 'BMD', 'DCM', 'Cognitive'."},
     }, "additionalProperties": False}},

    {"name": "render_variant_composition",
     "description": "Compact variant-composition summary in the style of a dashboard tile: total N pathogenic variants + horizontal bars breaking down by category. Answers 'what does the pathogenic variant corpus look like at a glance?' Default groups by consequence class (frameshift / nonsense / splice-site / etc.); can group by ACMG instead.",
     "input_schema": {"type": "object", "properties": {
         "group_by": {"type": "string", "description": "Grouping dimension: 'consequence' (default) or 'acmg'."},
     }, "additionalProperties": False}},

    {"name": "render_nmd_status",
     "description": "Whether this patient's variant is predicted to trigger nonsense-mediated decay (NMD) or escape it. Frameshift/nonsense in non-terminal exons trigger; splice is conditional.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_absplice",
     "description": "AbSplice per-tissue splice-disruption predictions for this patient's variant. Bar-per-tissue with score 0-1.",
     "input_schema": {"type": "object", "properties": {
         "tissue": {"type": "string", "description": "Filter/highlight one tissue, e.g. 'Muscle_Skeletal', 'Heart_Left_Ventricle'."},
     }, "additionalProperties": False}},

    {"name": "render_hpa_cells",
     "description": "Which cell types express DMD. Ranked bar chart of curated per-cell expression score, colored by per-patient hit/spared/partial status.",
     "input_schema": {"type": "object", "properties": {
         "tissue": {"type": "string", "description": "Filter to cell types in one tissue, e.g. 'skeletal_muscle', 'cardiac_muscle'."},
         "status": {"type": "string", "description": "Filter to one impact status, 'hit', 'spared', or 'partial'."},
     }, "additionalProperties": False}},

    {"name": "render_gtex_tissues",
     "description": "Which tissues are hit vs spared for this patient's variant, derived from the isoform × tissue projection.",
     "input_schema": {"type": "object", "properties": {
         "hit_status": {"type": "string", "description": "Show only 'hit' or 'spared' tissues."},
     }, "additionalProperties": False}},

    {"name": "render_isoform_grid",
     "description": "Isoform × tissue coverage matrix. Rows = DMD isoforms (Dp427m, Dp427c, Dp260, Dp140, Dp116, Dp71, Dp45), cols = tissues, cells = hit (variant lands upstream of isoform's promoter) vs spared.",
     "input_schema": {"type": "object", "properties": {
         "isoform": {"type": "string", "description": "Filter to one isoform, e.g. 'Dp71'."},
         "tissue":  {"type": "string", "description": "Filter to one tissue column."},
     }, "additionalProperties": False}},

    {"name": "render_nmd_vs_symptom",
     "description": "Cohort-wide: NMD status vs abnormal-lab count. Groups the 10 patients by predicted NMD outcome (trigger / splice / other) and shows per-group means. Statistical test not run (n=10 too thin).",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_labs_by_consequence",
     "description": "Cohort lab-profile heatmap grouped by variant consequence class (Frameshift / Nonsense / Splice-site). Rows = patients, columns = 15 labs (CK, LDH, aldolase, MRI_ff_VL, FVC_pct, PCF, NT_proBNP, LVEF, LGE, ERG_bwave, IQ, UACR, NSAA, m6MWT, TTS). Cells show high/low/normal flag with color; group header row summarizes fraction abnormal per lab.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_esm3_fold",
     "description": "ESM3-predicted 3D fold of dystrophin with this variant vs wild-type. Reads a cached PDB from cache/esm3/. On dev boxes without the cache this degrades to an honest 'not cached' stub.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_esm2_llr",
     "description": "ROADMAP — ESM2 log-likelihood ratio (LLR) at this patient's variant position vs a WT baseline. Not baked; returns an honest 'not baked yet' stub.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_llr_vs_symptom",
     "description": "ROADMAP — cross-cohort scatter of per-variant LLR vs symptom count. Blocked on esm2_llr. Returns an honest stub.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_opentargets",
     "description": "DMD's Open Targets record — approved drugs, molecular interactors (STRING-scored), and top Reactome pathways.",
     "input_schema": {"type": "object", "properties": {
         "section": {"type": "string", "description": "Filter to one section: 'drugs', 'interactions', or 'pathways'."},
     }, "additionalProperties": False}},

    {"name": "render_archs4",
     "description": "ROADMAP — DMD co-expression network from ARCHS4. Not baked; honest stub.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_string",
     "description": "ROADMAP — STRING protein interaction network for DMD. Not baked; honest stub.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_geneformer",
     "description": "ROADMAP — Geneformer in-silico DMD-knockout perturbation. Not baked; honest stub.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_cmap",
     "description": "ROADMAP — Connectivity Map rescue candidates matched to the DMD-loss signature. Not baked; honest stub.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},

    {"name": "render_route_to_mech",
     "description": "Meta-artifact: a short paragraph + button that switches the user to the Explore Mechanism tab. Use when the user asks a synthesis / mechanism-linking question that the Data view can't answer alone.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
]

# Mapping: tool name → (renderer key, qid) so the frontend gets both.
_TOOL_META = {
    "render_variants_table":  ("variants_table",  "Q1.1"),
    "render_labs_summary":    ("labs_summary",    "LA.1"),
    "render_variant_card":    ("variant_card",    "VA.1"),
    "render_variant_lollipop":("variant_lollipop","VA.2"),
    "render_variant_composition":("variant_composition","VA.3"),
    "render_nmd_status":      ("nmd_status",      "Q2.1"),
    "render_absplice":        ("absplice",        "Q2.2"),
    "render_hpa_cells":       ("hpa_cells",       "Q2.3"),
    "render_gtex_tissues":    ("gtex_tissues",    "Q2.4"),
    "render_isoform_grid":    ("isoform_grid",    "Q2.5"),
    "render_nmd_vs_symptom":  ("nmd_vs_symptom",  "Q2.6"),
    "render_labs_by_consequence": ("labs_by_consequence", "PH.1"),
    "render_esm3_fold":       ("esm3_fold",       "Q3.1"),
    "render_esm2_llr":        ("esm2_llr",        "Q3.2"),
    "render_llr_vs_symptom":  ("llr_vs_symptom",  "Q3.3"),
    "render_opentargets":     ("opentargets",     "Q4.1"),
    "render_archs4":          ("archs4",          "Q4.2"),
    "render_string":          ("string",          "Q4.3"),
    "render_geneformer":      ("geneformer",      "Q4.4"),
    "render_cmap":            ("cmap",            "Q4.5"),
    "render_route_to_mech":   ("route_to_mech",   "Q5"),
}


def _system_prompt(patient: dict) -> str:
    v = patient.get("variant", {}) or {}
    lines = [
        "You are the Explore Data agent for a DMD (Duchenne Muscular Dystrophy)",
        "workbench. The user is a clinician-researcher exploring one patient's",
        "mechanism space.",
        "",
        "Your only job is to pick which of the available chart renderers to invoke",
        "and what filters to apply, based on the user's natural-language question.",
        "You do NOT reason about the underlying data yourself — the frontend renders",
        "each chart from baked indices.",
        "",
        "Rules:",
        "  - Prefer to invoke ONE tool if the question maps to one; invoke MULTIPLE",
        "    tools when the question benefits from side-by-side comparison (e.g.",
        "    'show me tissue impact from both angles' → gtex_tissues + isoform_grid).",
        "  - Apply filters when the user names a specific tissue / cell / consequence /",
        "    isoform / ACMG class. Don't invent filter values — pass what the user said.",
        "  - Include a SHORT text response (1-2 sentences) framing what you're showing.",
        "  - If the user asks a synthesis / mechanism question that no single chart",
        "    answers, invoke render_route_to_mech.",
        "  - ROADMAP renderers (esm2_llr, llr_vs_symptom, archs4, string, geneformer,",
        "    cmap) return honest 'not baked yet' stubs. Only invoke them if the user",
        "    explicitly asks for that specific analysis.",
        "",
        f"Current patient: {patient.get('id', '?')} · exon {v.get('exon','?')} · "
        f"{v.get('nucleotide','?')} · {v.get('consequence','?')} · "
        f"ACMG {v.get('acmg','?')} · phenotype {patient.get('phenotype','?')}.",
    ]
    return "\n".join(lines)


def _call_anthropic(messages: list[dict], system: str, tools: list[dict],
                    max_tokens: int = 2000, timeout: int = 60) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
    body = {
        "model":      ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "system":     system,
        "messages":   messages,
        "tools":      tools,
    }
    req = urllib.request.Request(
        ANTHROPIC_URL, method="POST",
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        data=json.dumps(body).encode(),
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


async def health(request):
    ok = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return JSONResponse({
        "status": "ok" if ok else "no_api_key",
        "model":  ANTHROPIC_MODEL,
        "tools":  len(TOOLS),
    })


async def chat(request):
    try:
        body = await request.json()
    except Exception as e:
        return JSONResponse({"error": f"invalid JSON: {e}"}, status_code=400)

    messages = body.get("messages") or []
    patient  = body.get("patient")  or {}
    if not messages:
        return JSONResponse({"error": "messages required"}, status_code=400)

    try:
        resp = _call_anthropic(messages, _system_prompt(patient), TOOLS)
    except urllib.error.HTTPError as e:
        return JSONResponse({
            "error": f"anthropic {e.code}",
            "detail": (e.read().decode()[:500]),
        }, status_code=502)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # Extract text + tool_use blocks from the assistant response.
    text_parts = []
    artifacts  = []
    for block in resp.get("content", []):
        t = block.get("type")
        if t == "text":
            text_parts.append(block.get("text", ""))
        elif t == "tool_use":
            name = block.get("name") or ""
            meta = _TOOL_META.get(name)
            if not meta:
                continue
            renderer, qid = meta
            artifacts.append({
                "renderer": renderer,
                "qid":      qid,
                "filter":   block.get("input") or {},
            })

    return JSONResponse({
        "text":      "\n\n".join(text_parts).strip(),
        "artifacts": artifacts,
        "model":     resp.get("model"),
        "usage":     resp.get("usage", {}),
    })


middleware = [
    Middleware(CORSMiddleware,
               allow_origins=["*"],       # dev-only; workbench is served from :8765
               allow_methods=["*"],
               allow_headers=["*"]),
]

app = Starlette(debug=False, routes=[
    Route("/health", health, methods=["GET"]),
    Route("/chat",   chat,   methods=["POST"]),
], middleware=middleware)


if __name__ == "__main__":
    import uvicorn
    # Bind 0.0.0.0 so the frontend can reach us regardless of the hostname
    # the browser uses (127.0.0.1 tunnel vs public box IP vs LAN). CORS is
    # already open (dev-only default); tighten allow_origins for prod.
    host = os.environ.get("CHAT_HOST", "0.0.0.0")
    port = int(os.environ.get("CHAT_PORT", "8766"))
    print(f"[chat_server] model={ANTHROPIC_MODEL} tools={len(TOOLS)} → {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
