#!/usr/bin/env python3
"""Build data/screens/2/v3 from v2 with literature-backed concentrations."""

from __future__ import annotations

import copy
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
V2 = REPO / "data/screens/2/v2"
V3 = REPO / "data/screens/2/v3"
REFS = REPO / "data/compound_literature/refs"
SUMMARY = REPO / "data/literature_summary.json"
RUNS = REPO / "pvjthomas/runs/2/v3"

RULE_BY_SOURCE = {
    "literature": 1,
    "10x_ic50": 2,
    "10x_ki": 2,
    "project_default": 3,
}

# ChEMBL evidence for T1262 (not retained in truncated ref entries)
CHEMBL_T1262 = {
    "database": "ChEMBL",
    "molecule_chembl_id": "CHEMBL404",
    "target_chembl_id": "CHEMBL2065",
    "target_pref_name": "Beta-lactamase TEM",
    "document_chembl_id": "CHEMBL1149192",
    "standard_type": "IC50",
    "standard_value_nM": 100.0,
    "standard_value_uM": 0.1,
    "assay_description": "In vitro inhibitory activity against Class A (TEM-1) beta-Lactamases",
}


def _best_literature_entry(entries: list[dict]) -> dict | None:
    for entry in entries:
        if entry.get("pmid") or entry.get("pmcid") or entry.get("doi"):
            if entry.get("ki_uM") or entry.get("ic50_uM") or entry.get("source") == "paperclip":
                return entry
    return entries[0] if entries else None


def build_concentration_reference(
    compound_id: str,
    ref: dict,
    prior: dict,
    assay: dict,
    source: str,
) -> dict:
    rule = RULE_BY_SOURCE.get(source, 3)
    out: dict = {
        "concentration_rule": rule,
        "screen_conc_source": source,
        "refs_file": f"data/compound_literature/refs/{compound_id}.json",
        "literature_search_at": "2026-07-26T01:35:51Z",
    }

    if rule == 1:
        entry = _best_literature_entry(ref.get("entries") or [])
        out.update(
            {
                "evidence_type": "literature_nitrocefin_assay",
                "pmid": (entry or {}).get("pmid"),
                "pmcid": (entry or {}).get("pmcid"),
                "doi": (entry or {}).get("doi"),
                "citation": (
                    f"{(entry or {}).get('authors', 'Radojković et al.')}, "
                    f"{(entry or {}).get('journal', 'J Biol Chem')} {(entry or {}).get('year', 2025)}"
                ).strip(", "),
                "activity_uM": prior.get("literature_ki_uM_tem1") or (entry or {}).get("ki_uM"),
                "activity_metric": "Ki",
                "note": assay.get("screen_rationale")
                or "Literature TEM-1 nitrocefin inhibition; project positive control at 50 µM.",
            }
        )
    elif rule == 2:
        activity_uM = (
            assay.get("activity_uM")
            or prior.get("literature_ic50_uM_tem1")
            or prior.get("literature_ki_uM_tem1")
        )
        metric = assay.get("activity_metric") or (
            "IC50" if prior.get("literature_ic50_uM_tem1") else "Ki"
        )
        out.update(
            {
                "evidence_type": f"10x_{metric.lower()}",
                "activity_uM": activity_uM,
                "activity_metric": metric,
                "multiplier": 10,
                "note": assay.get("screen_rationale"),
            }
        )
        if compound_id == "T1262":
            out["chembl"] = CHEMBL_T1262
    else:
        out.update(
            {
                "evidence_type": "project_default",
                "note": (
                    "No TEM-1 nitrocefin Ki/IC50 or assay inhibitor concentration extracted "
                    "from open repositories + ChEMBL (2026-07-26). Project HTS default 50 µM."
                ),
            }
        )
    return out


def enrich_compound(row: dict, priors: dict) -> dict:
    compound_id = row["compound_id"]
    ref_path = REFS / f"{compound_id}.json"
    ref = json.loads(ref_path.read_text()) if ref_path.exists() else {}
    prior = priors.get(compound_id, {})
    assay = ref.get("assay_recommendations", {}).get("tem1_nitrocefin", {})

    source = (
        assay.get("screen_conc_source")
        or prior.get("screen_conc_source")
        or row.get("screen_conc_source")
        or "project_default"
    )
    conc = assay.get("screen_conc_uM") or prior.get("recommended_screen_uM") or row["screen_conc_uM"]
    working = round(conc * 10, 2) if conc else row["working_solution_uM"]

    updated = copy.deepcopy(row)
    updated["screen_conc_uM"] = conc
    updated["working_solution_uM"] = working
    updated["screen_conc_source"] = source
    updated["concentration_rule"] = RULE_BY_SOURCE.get(source, 3)
    updated["screen_rationale"] = assay.get("screen_rationale")
    updated["concentration_reference"] = build_concentration_reference(
        compound_id, ref, prior, assay, source
    )
    return updated


def main() -> None:
    V3.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)

    priors = json.loads(SUMMARY.read_text()).get("compound_assay_priors", {})
    cl_v2 = json.loads((V2 / "compound_list.json").read_text())
    compounds = [enrich_compound(c, priors) for c in cl_v2["compounds"]]

    compound_list = {
        **{k: v for k, v in cl_v2.items() if k not in ("compounds", "rationale_doc")},
        "version": 3,
        "version_label": "r2-discovery-v3",
        "supersedes": "data/screens/2/v2/compound_list.json",
        "rationale_doc": "pvjthomas/runs/2/v3/selection_rationale.md",
        "note": (
            "Same 10-compound layout as v2; per-compound screen concentrations from "
            "literature search (rules 1–3) with concentration_reference on each compound."
        ),
        "concentration_rules_doc": "pvjthomas/COMPOUND_SELECTION.md Step F5",
        "literature_search_at": "2026-07-26T01:35:51Z",
        "compounds": compounds,
    }
    compound_list["default_screen_conc_uM"] = 50
    (V3 / "compound_list.json").write_text(json.dumps(compound_list, indent=2) + "\n")

    # CSV
    fieldnames = [
        "slot",
        "compound_id",
        "name",
        "bucket",
        "functional_class",
        "screen_conc_uM",
        "working_solution_uM",
        "concentration_rule",
        "screen_conc_source",
        "expected_at_screen_conc",
        "source_plate",
        "source_well",
        "refs_file",
        "reference_summary",
    ]
    with (V3 / "compound_list.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for c in compounds:
            ref = c["concentration_reference"]
            summary = ref.get("citation") or ref.get("note") or ref.get("evidence_type", "")
            if ref.get("chembl"):
                summary = f"ChEMBL {ref['chembl']['document_chembl_id']} IC50={ref['chembl']['standard_value_uM']} µM"
            writer.writerow(
                {
                    "slot": c["slot"],
                    "compound_id": c["compound_id"],
                    "name": c["name"],
                    "bucket": c["bucket"],
                    "functional_class": c["functional_class"],
                    "screen_conc_uM": c["screen_conc_uM"],
                    "working_solution_uM": c["working_solution_uM"],
                    "concentration_rule": c["concentration_rule"],
                    "screen_conc_source": c["screen_conc_source"],
                    "expected_at_screen_conc": c["expected_at_screen_conc"],
                    "source_plate": c["source_plate"],
                    "source_well": c["source_well"],
                    "refs_file": c["refs_file"],
                    "reference_summary": summary[:200],
                }
            )

    # Plate map — update concentrations from compound list
    conc_by_id = {c["compound_id"]: c["screen_conc_uM"] for c in compounds}
    plate = json.loads((V2 / "plate_map.json").read_text())
    plate["version"] = 3
    plate["version_label"] = "r2-discovery-v3"
    plate["compound_list"] = "data/screens/2/v3/compound_list.json"
    plate["rationale_doc"] = "pvjthomas/runs/2/v3/selection_rationale.md"
    plate["versioned_path"] = "data/screens/2/v3/plate_map.json"
    plate["description"] = (
        "Round 2 discovery v3 — 10 compounds in triplicate with literature-backed "
        "per-compound concentrations (see compound_list.json)"
    )
    plate["layout_notes"] = (
        "96-well flat bottom: row A = 12 plate controls; row B = 4 tier-1 inhibitors × 3; "
        "row C = 4 substrate controls × 3; row D = 2 diverse picks × 3. "
        "T1262 @ 1 µM (rule 2); all others @ 50 µM unless noted in compound_list.json."
    )
    plate.pop("compound_concentration_uM", None)
    plate["default_compound_concentration_uM"] = 50
    plate["concentrations_from"] = "data/screens/2/v3/compound_list.json"

    for well in plate["wells"].values():
        cid = well.get("compound_id")
        if cid and cid in conc_by_id:
            well["concentration_uM"] = conc_by_id[cid]

    (V3 / "plate_map.json").write_text(json.dumps(plate, indent=2) + "\n")

    # Manifest
    manifest = {
        "run": 2,
        "round": 2,
        "version": 3,
        "label": "r2-discovery-v3",
        "created_at": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "author": "pvjthomas",
        "status": "pending_signoff",
        "supersedes": "data/screens/2/v2/manifest.json",
        "note": "v3 adds literature-backed per-compound concentrations (concentration_rule + concentration_reference in compound_list.json)",
        "description": "Round 2 discovery v3 — 10 compounds × triplicate; T1262 @ 1 µM, others mostly @ 50 µM",
        "concentration_policy": {
            "rules": {
                "1": "literature nitrocefin assay inhibitor concentration",
                "2": "10× IC50 or Ki (IC50 preferred)",
                "3": "project default 50 µM",
            },
            "canonical_file": "data/screens/2/v3/compound_list.json",
            "literature_search_at": "2026-07-26T01:35:51Z",
        },
        "files": {
            "compound_list": "data/screens/2/v3/compound_list.json",
            "compound_list_csv": "data/screens/2/v3/compound_list.csv",
            "plate_map": "data/screens/2/v3/plate_map.json",
            "selection_rationale": "pvjthomas/runs/2/v3/selection_rationale.md",
            "active_plate_map": "data/plate_map_r2.json",
            "active_selection_rationale": "pvjthomas/selection_rationale.md",
        },
    }
    (V3 / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # Selection rationale stub
    rationale = f"""# Round 2 / version 3 — literature-backed concentrations

**Round:** 2 · **Version:** 3 (`r2-discovery-v3`)  
**Supersedes:** [`data/screens/2/v2/`](../v2/)  
**Canonical concentrations:** [`compound_list.json`](../../../../data/screens/2/v3/compound_list.json)

---

## What changed from v2

Same **10-compound layout** as v2. v3 adds per-compound **screen concentrations**, **concentration_rule** (1–3), and **concentration_reference** from the 2026-07-26 literature search.

| Rule | Meaning |
|------|---------|
| **1** | Literature nitrocefin assay concentration |
| **2** | 10× literature IC50 or Ki |
| **3** | Project default 50 µM |

---

## Concentrations

| Slot | ID | Name | µM | Rule | Source |
|------|-----|------|-----|------|--------|
"""
    for c in compounds:
        rationale += (
            f"| {c['slot']} | {c['compound_id']} | {c['name']} | {c['screen_conc_uM']} | "
            f"{c['concentration_rule']} | {c['screen_conc_source']} |\n"
        )
    rationale += """
---

## Where data lives

- **Per-compound detail (rule + reference):** `compound_list.json` → `compounds[].concentration_reference`
- **Well layout:** `plate_map.json` (concentrations copied from compound list)
- **Manifest:** file index only — does not duplicate compound fields

Promote to robot: copy `plate_map.json` → `data/plate_map_r2.json` after sign-off.
"""
    (RUNS / "selection_rationale.md").write_text(rationale)

    print(f"Wrote {V3}")
    for c in compounds:
        if c["concentration_rule"] < 3:
            print(f"  rule {c['concentration_rule']}: {c['compound_id']} @ {c['screen_conc_uM']} µM")


if __name__ == "__main__":
    main()
