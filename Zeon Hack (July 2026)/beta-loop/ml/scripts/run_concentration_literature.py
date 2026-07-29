#!/usr/bin/env python3
"""Run full-repository reverse literature + ChEMBL enrichment for v3 plate compounds."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ml"))

from agent.paths import LITERATURE_REFS_DIR, LITERATURE_SUMMARY_JSON
from agent.tools.compounds import load_compounds
from agent.tools.literature_repositories import ALL_LITERATURE_SOURCES
from agent.tools.reverse import enrich_from_chembl_activities, reverse_literature_check

PLATE_PATH = REPO / "data/screens/1/v3/plate_map.json"
OUT_JSON = REPO / "pvjthomas/output/concentration_table.json"
OUT_MD = REPO / "pvjthomas/output/concentration_table.md"


def plate_compound_ids() -> list[str]:
    plate = json.loads(PLATE_PATH.read_text())
    return sorted({w["compound_id"] for w in plate["wells"].values() if w.get("compound_id")})


def build_table(compound_ids: list[str]) -> list[dict]:
    compounds = {c["compound_id"]: c for c in load_compounds()}
    summary = json.loads(LITERATURE_SUMMARY_JSON.read_text()) if LITERATURE_SUMMARY_JSON.exists() else {}
    priors = summary.get("compound_assay_priors", {})
    rows: list[dict] = []

    for cid in compound_ids:
        compound = compounds.get(cid, {})
        prior = priors.get(cid, {})
        ref_path = LITERATURE_REFS_DIR / f"{cid}.json"
        assay = {}
        if ref_path.exists():
            assay = json.loads(ref_path.read_text()).get("assay_recommendations", {}).get("tem1_nitrocefin", {})

        src = assay.get("screen_conc_source") or prior.get("screen_conc_source") or "missing"
        rule = {"literature": 1, "10x_ic50": 2, "10x_ki": 2}.get(src, 3 if src == "project_default" else 0)

        rows.append(
            {
                "compound_id": cid,
                "name": compound.get("name") or prior.get("name"),
                "screen_conc_uM": assay.get("screen_conc_uM") or prior.get("recommended_screen_uM"),
                "screen_conc_source": src,
                "rule_applied": rule,
                "screen_rationale": assay.get("screen_rationale"),
                "ki_uM": prior.get("literature_ki_uM_tem1") or assay.get("activity_uM") if assay.get("activity_metric") == "Ki" else prior.get("literature_ki_uM_tem1"),
                "ic50_uM": prior.get("literature_ic50_uM_tem1") or (assay.get("activity_uM") if assay.get("activity_metric") == "IC50" else None),
                "literature_inhibitor_uM": assay.get("literature_inhibitor_uM"),
            }
        )
    return rows


def write_markdown(rows: list[dict]) -> None:
    lines = [
        "# Concentration table — v3 discovery plate",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Rules: **1** = literature nitrocefin assay conc · **2** = 10× Ki/IC50 · **3** = project default 50 µM",
        "",
        "| ID | Name | Screen µM | Source | Rule | Ki µM | IC50 µM | Lit assay µM | Rationale |",
        "|----|------|-----------|--------|------|-------|---------|--------------|-----------|",
    ]
    for r in rows:
        rule = r["rule_applied"] or "—"
        lines.append(
            f"| {r['compound_id']} | {r.get('name', '')} | {r.get('screen_conc_uM', '')} | "
            f"{r.get('screen_conc_source', '')} | {rule} | {r.get('ki_uM') or '—'} | "
            f"{r.get('ic50_uM') or '—'} | {r.get('literature_inhibitor_uM') or '—'} | "
            f"{(r.get('screen_rationale') or '')[:60]} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n")


def main() -> None:
    compound_ids = plate_compound_ids()
    sources = sorted(ALL_LITERATURE_SOURCES)
    print(f"Compounds: {len(compound_ids)}")
    print(f"Sources: {sources}")

    print("\n=== reverse_literature_check (all repositories) ===")
    lit_out = reverse_literature_check(
        compound_ids=compound_ids,
        sources=sources,
        limit_per_compound=30,
        extract_activity=True,
        write_refs=True,
        save_raw=True,
        skip_curated=True,
        use_cache=True,
        max_compounds_per_run=None,
        max_map_per_run=None,
    )
    print(
        f"checked={lit_out.get('checked')} maps={lit_out.get('map_count')} "
        f"search_cache_hits={lit_out.get('search_cache_hits')} map_cache_hits={lit_out.get('map_cache_hits')}"
    )

    print("\n=== enrich_from_chembl_activities ===")
    chembl_out = enrich_from_chembl_activities(compound_ids, skip_curated=False)
    hits = [e for e in chembl_out.get("enriched", []) if e.get("ki_uM") or e.get("ic50_uM")]
    print(f"chembl_hits={len(hits)}")

    rows = build_table(compound_ids)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"compound_ids": compound_ids, "rows": rows}, indent=2) + "\n")
    write_markdown(rows)

    rule12 = [r for r in rows if r.get("rule_applied") in (1, 2)]
    print(f"\nRule 1/2 applied: {len(rule12)}/{len(rows)}")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
