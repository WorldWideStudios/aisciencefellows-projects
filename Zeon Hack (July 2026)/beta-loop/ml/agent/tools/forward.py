"""Forward selection tools — literature → library matching."""

from __future__ import annotations

import csv
import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.paths import (
    FORWARD_SNAPSHOTS_DIR,
    LITERATURE_ONLY_REFS_DIR,
    LITERATURE_REFS_DIR,
    LITERATURE_SUMMARY_JSON,
    LOCAL_LITERATURE,
    REPO_ROOT,
    REFERENCE_INHIBITORS_CSV,
    SELECTION_STATE_JSON,
)
from agent.tools.chem import normalize_name, tanimoto_smiles
from agent.tools.compounds import load_compounds
from agent.tools.literature import load_literature_summary, save_literature_search, search_literature

FORWARD_AGENT_VERSION = "v1"
FORWARD_AGENT_LABEL = "forward-research-agent-v1"

# Literature caps (v1) — see tests/FORWARD_TEST_PLAN.md
MAX_BATCH_PAPERCLIP_QUERIES = 2
MAX_LITERATURE_ONLY_QUERIES = 4
MAX_PAPERCLIP_SEARCHES_PER_RUN = 6
PAPERCLIP_QUERY_LIMIT = 15
MAX_REF_ENTRIES = 5
MAX_REF_ENTRIES_WITH_ACTIVITY = 3
MAX_REF_JSON_BYTES = 50_000
MAX_RAW_SEARCH_FILES_PER_COMPOUND = 2

FORWARD_QUERIES = [
    ("TEM-1 beta-lactamase inhibitor IC50 nitrocefin", "pmc"),
    ("clavulanic acid sulbactam tazobactam beta-lactamase inhibitor", "pmc"),
]

MANUAL_FORM_GROUPS: list[dict[str, Any]] = [
    {
        "group_id": "clavulanate",
        "canonical_compound_id": "T19860",
        "compound_ids": ["T19860", "T14979"],
    },
    {
        "group_id": "sulbactam",
        "canonical_compound_id": "T1631",
        "compound_ids": ["T1631", "T6685"],
    },
]

SEED_INHIBITORS = [
    {
        "name": "clavulanic acid",
        "smiles": "",
        "ic50_uM": None,
        "assay": "nitrocefin",
        "source": "manual_seed",
        "pmid_or_chembl_id": "",
    },
    {
        "name": "sulbactam",
        "smiles": "",
        "ic50_uM": None,
        "assay": "nitrocefin",
        "source": "manual_seed",
        "pmid_or_chembl_id": "",
    },
    {
        "name": "tazobactam",
        "smiles": "",
        "ic50_uM": None,
        "assay": "nitrocefin",
        "source": "manual_seed",
        "pmid_or_chembl_id": "",
    },
    {
        "name": "enmetazobactam",
        "smiles": "",
        "ic50_uM": None,
        "assay": "nitrocefin",
        "source": "manual_seed",
        "pmid_or_chembl_id": "",
    },
]

_SALT_TOKENS = ("sodium", "lithium", "potassium", "zinc", "hydrate", "monohydrate")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_selection_state() -> dict[str, Any]:
    if not SELECTION_STATE_JSON.exists():
        return {"schema_version": 1, "updated_at": None, "forward": {}, "reverse": {}, "bridge": {}, "merge": {}}
    return json.loads(SELECTION_STATE_JSON.read_text())


def _save_selection_state(state: dict[str, Any]) -> str:
    SELECTION_STATE_JSON.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _utc_now()
    SELECTION_STATE_JSON.write_text(json.dumps(state, indent=2) + "\n")
    return str(SELECTION_STATE_JSON)


def _compounds_by_id(compounds: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(c["compound_id"]): c for c in compounds}


def _manual_canonical_overrides(summary: dict[str, Any]) -> dict[str, str]:
    """Map alternate compound_id → canonical from literature_summary priors."""
    overrides: dict[str, str] = {}
    for group in MANUAL_FORM_GROUPS:
        canonical = group["canonical_compound_id"]
        for cid in group["compound_ids"]:
            if cid != canonical:
                overrides[cid] = canonical
    priors = summary.get("compound_assay_priors", {})
    for cid, info in priors.items():
        note = str(info.get("note") or "")
        match = re.search(r"\bT(\d+)\b", note)
        if match:
            canonical = f"T{match.group(1)}"
            if canonical != cid and canonical.startswith("T"):
                overrides[cid] = canonical
    return overrides


def _form_preference_score(compound: dict[str, Any]) -> int:
    name = str(compound.get("name") or "").lower()
    score = 0
    if " acid" in name or name.endswith("acid"):
        score += 20
    if normalize_name(name) in {"sulbactam", "tazobactam", "enmetazobactam", "clavulanate", "clavulanic"}:
        score += 10
    if any(tok in name for tok in _SALT_TOKENS):
        score -= 10
    return score


def _form_type(name: str) -> str:
    lower = name.lower()
    if "lithium" in lower:
        return "lithium_salt"
    if "sodium" in lower:
        return "sodium_salt"
    if " acid" in lower or lower.endswith("acid"):
        return "free_acid"
    return "other"


def _name_core(name: str) -> str:
    return normalize_name(name)


def _union_find(ids: set[str]) -> dict[str, str]:
    parent = {cid: cid for cid in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    return parent, find, union


def _pick_canonical_id(
    compound_ids: list[str],
    by_id: dict[str, dict[str, Any]],
    canonical_overrides: dict[str, str],
) -> str:
    candidates = [cid for cid in compound_ids if cid not in canonical_overrides]
    if not candidates:
        candidates = sorted({canonical_overrides[cid] for cid in compound_ids if cid in canonical_overrides})
    if not candidates:
        candidates = list(compound_ids)
    return sorted(
        candidates,
        key=lambda c: (_form_preference_score(by_id.get(c, {})), c),
        reverse=True,
    )[0]


def _group_id_for_core(core: str, compound_ids: list[str], by_id: dict[str, dict[str, Any]]) -> str:
    for manual in MANUAL_FORM_GROUPS:
        manual_set = set(manual["compound_ids"])
        if manual_set.intersection(compound_ids):
            return manual["group_id"]
    if len(compound_ids) == 1:
        name = str(by_id.get(compound_ids[0], {}).get("name") or compound_ids[0])
        return _name_core(name).replace(" ", "_") or compound_ids[0].lower()
    return core.replace(" ", "_") or "group"


def build_compound_groups(
    compounds: list[dict[str, Any]],
    matched_compound_ids: set[str],
    summary: dict[str, Any] | None = None,
    tanimoto_threshold: float = 0.85,
) -> list[dict[str, Any]]:
    """Cluster in-library alternate forms; assign canonical compound_id per group."""
    summary = summary or load_literature_summary()
    by_id = _compounds_by_id(compounds)
    canonical_overrides = _manual_canonical_overrides(summary)

    ids: set[str] = set(matched_compound_ids)
    for manual in MANUAL_FORM_GROUPS:
        if ids.intersection(manual["compound_ids"]):
            ids.update(manual["compound_ids"])

    if not ids:
        return []

    parent, find, union = _union_find(ids)

    for manual in MANUAL_FORM_GROUPS:
        members = [cid for cid in manual["compound_ids"] if cid in ids]
        for i in range(1, len(members)):
            union(members[0], members[i])

    id_list = sorted(ids)
    for i, cid_a in enumerate(id_list):
        comp_a = by_id.get(cid_a, {})
        smiles_a = comp_a.get("smiles") or ""
        core_a = _name_core(str(comp_a.get("name") or ""))
        for cid_b in id_list[i + 1 :]:
            comp_b = by_id.get(cid_b, {})
            core_b = _name_core(str(comp_b.get("name") or ""))
            if core_a and core_a == core_b:
                union(cid_a, cid_b)
                continue
            smiles_b = comp_b.get("smiles") or ""
            if smiles_a and smiles_b:
                score = tanimoto_smiles(smiles_a, smiles_b)
                if score is not None and score >= tanimoto_threshold:
                    union(cid_a, cid_b)

    clusters: dict[str, list[str]] = {}
    for cid in ids:
        root = find(cid)
        clusters.setdefault(root, []).append(cid)

    groups: list[dict[str, Any]] = []
    for members in clusters.values():
        members = sorted(set(members))
        cores = {_name_core(str(by_id.get(m, {}).get("name") or "")) for m in members}
        core = next(iter(c for c in cores if c), members[0].lower())
        canonical = _pick_canonical_id(members, by_id, canonical_overrides)
        for manual in MANUAL_FORM_GROUPS:
            if set(members) == set(manual["compound_ids"]):
                canonical = manual["canonical_compound_id"]
                break
        group_id = _group_id_for_core(core, members, by_id)
        forms = []
        for cid in members:
            comp = by_id.get(cid, {})
            forms.append(
                {
                    "compound_id": cid,
                    "name": comp.get("name"),
                    "form_type": _form_type(str(comp.get("name") or "")),
                    "is_canonical": cid == canonical,
                }
            )
        groups.append(
            {
                "group_id": group_id,
                "canonical_compound_id": canonical,
                "compound_ids": members,
                "forms": forms,
            }
        )
    return sorted(groups, key=lambda g: g["group_id"])


def _group_lookup(groups: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for group in groups:
        for cid in group["compound_ids"]:
            lookup[cid] = group
    return lookup


def load_reference_inhibitors() -> dict[str, Any]:
    """Load data/reference_inhibitors.csv if present, else return seed inhibitors."""
    if REFERENCE_INHIBITORS_CSV.exists():
        with REFERENCE_INHIBITORS_CSV.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        return {"status": "ok", "source": str(REFERENCE_INHIBITORS_CSV), "count": len(rows), "inhibitors": rows}
    return {"status": "seed", "source": "built_in", "count": len(SEED_INHIBITORS), "inhibitors": SEED_INHIBITORS}


def _compound_names(compound: dict[str, Any]) -> list[str]:
    names = [str(compound.get("name") or "")]
    synonyms = compound.get("synonyms")
    if synonyms and isinstance(synonyms, str):
        names.extend(synonyms.split(";"))
    return names


def _name_match_score(ref_name: str, compound: dict[str, Any]) -> int:
    """Score name overlap; 100 = exact normalized match."""
    ref_norm = normalize_name(ref_name)
    best = 0
    for name in _compound_names(compound):
        name_norm = normalize_name(name)
        if name_norm == ref_norm:
            return 100
        if ref_norm in name_norm:
            overlap = len(ref_norm)
            longer = max(len(ref_norm), len(name_norm))
            if longer and overlap / longer >= 0.9:
                best = max(best, overlap)
        elif name_norm in ref_norm:
            overlap = len(name_norm)
            longer = max(len(ref_norm), len(name_norm))
            if longer and overlap / longer >= 0.9:
                best = max(best, overlap)
    return best


def _name_match(ref_name: str, compound: dict[str, Any]) -> bool:
    score = _name_match_score(ref_name, compound)
    return score >= 100 or score >= 8


def _best_name_match(ref_name: str, compounds: list[dict[str, Any]]) -> dict[str, Any] | None:
    best_compound = None
    best_score = 0
    for compound in compounds:
        if compound.get("exclude"):
            continue
        score = _name_match_score(ref_name, compound)
        if score > best_score:
            best_score = score
            best_compound = compound
        elif score == best_score and score > 0 and best_compound is not None:
            if _form_preference_score(compound) > _form_preference_score(best_compound):
                best_compound = compound
    if best_score >= 100 or best_score >= 8:
        return best_compound
    return None


def _ref_file_is_curated(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return False
    for entry in payload.get("entries", []):
        if entry.get("source") == "paperclip" or entry.get("pmid") or entry.get("pmcid"):
            return True
    return False


def _entry_has_activity(entry: dict[str, Any]) -> bool:
    return any(entry.get(k) is not None for k in ("ki_uM", "ic50_uM", "ki_uM_mutant_Y105G"))


def _apply_entry_caps(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    """Cap curated entries per v1 policy; prefer TEM-1 / activity-bearing rows."""
    if len(entries) <= MAX_REF_ENTRIES:
        activity = [e for e in entries if _entry_has_activity(e)]
        if len(activity) <= MAX_REF_ENTRIES_WITH_ACTIVITY:
            return entries, False

    def rank(entry: dict[str, Any]) -> tuple[int, int]:
        target = str(entry.get("target") or "").upper()
        tem1 = 1 if "TEM-1" in target or target == "TEM-1" else 0
        activity = 1 if _entry_has_activity(entry) else 0
        return (tem1, activity)

    ranked = sorted(entries, key=rank, reverse=True)
    kept: list[dict[str, Any]] = []
    activity_count = 0
    for entry in ranked:
        if len(kept) >= MAX_REF_ENTRIES:
            break
        if _entry_has_activity(entry):
            if activity_count >= MAX_REF_ENTRIES_WITH_ACTIVITY:
                slim = {k: v for k, v in entry.items() if k in ("source", "pmid", "pmcid", "doi", "title", "note")}
                kept.append(slim)
                continue
            activity_count += 1
        kept.append(entry)
    return kept, len(kept) < len(entries)


def _write_json_capped(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2) + "\n"
    if len(text.encode("utf-8")) > MAX_REF_JSON_BYTES:
        payload = dict(payload)
        payload["cap_truncated"] = True
        payload["entries"] = payload.get("entries", [])[:MAX_REF_ENTRIES]
        text = json.dumps(payload, indent=2) + "\n"
    path.write_text(text)


def _write_alternate_ref(
    compound_id: str,
    compound: dict[str, Any],
    group: dict[str, Any],
    reference_name: str,
) -> None:
    canonical_id = group["canonical_compound_id"]
    note = f"Alternate library form; literature on canonical {canonical_id}."
    priors = load_literature_summary().get("compound_assay_priors", {})
    if canonical_id in priors:
        note = str(priors.get(compound_id, {}).get("note") or priors.get(canonical_id, {}).get("note") or note)
    payload = {
        "compound_id": compound_id,
        "name": compound.get("name"),
        "match": "yes",
        "support": "strong",
        "form_type": _form_type(str(compound.get("name") or "")),
        "canonical_compound_id": canonical_id,
        "related_forms": group["compound_ids"],
        "group_id": group["group_id"],
        "reference_inhibitor": reference_name,
        "note": note,
        "entries": [],
        "raw_local": str(LOCAL_LITERATURE / compound_id / ""),
    }
    ref_path = LITERATURE_REFS_DIR / f"{compound_id}.json"
    if _ref_file_is_curated(ref_path):
        return
    _write_json_capped(ref_path, payload)


def _write_canonical_ref(
    compound_id: str,
    compound: dict[str, Any],
    group: dict[str, Any] | None,
    reference_name: str,
    ref_row: dict[str, Any],
    match_type: str,
) -> None:
    ref_path = LITERATURE_REFS_DIR / f"{compound_id}.json"
    if _ref_file_is_curated(ref_path):
        existing = json.loads(ref_path.read_text())
        entries, truncated = _apply_entry_caps(existing.get("entries", []))
        if truncated:
            existing["entries"] = entries
            existing["cap_truncated"] = True
            _write_json_capped(ref_path, existing)
        return

    entries = [ref_row]
    entries, truncated = _apply_entry_caps(entries)
    payload: dict[str, Any] = {
        "compound_id": compound_id,
        "name": compound.get("name"),
        "match": "yes" if match_type == "direct" else "analog",
        "support": "strong" if match_type == "direct" else "weak",
        "reference_inhibitor": reference_name,
        "entries": entries,
        "raw_local": str(LOCAL_LITERATURE / compound_id / ""),
    }
    if truncated:
        payload["cap_truncated"] = True
    if group:
        payload["group_id"] = group["group_id"]
        payload["related_forms"] = group["compound_ids"]
        payload["canonical_compound_id"] = group["canonical_compound_id"]
    _write_json_capped(ref_path, payload)


def _smiles_for_seed_name(name: str, compounds: list[dict[str, Any]]) -> str:
    match = _best_name_match(name, compounds)
    if not match:
        return ""
    groups = build_compound_groups(compounds, {match["compound_id"]})
    lookup = _group_lookup(groups)
    group = lookup.get(match["compound_id"])
    if group:
        by_id = _compounds_by_id(compounds)
        canonical = by_id.get(group["canonical_compound_id"], match)
        return canonical.get("smiles") or match.get("smiles") or ""
    return match.get("smiles") or ""


def seed_reference_inhibitors() -> dict[str, Any]:
    """Write data/reference_inhibitors.csv from manual seeds + literature_summary known inhibitors."""
    summary = load_literature_summary()
    compounds = load_compounds()
    rows = []
    for seed in SEED_INHIBITORS:
        row = dict(seed)
        if not row.get("smiles"):
            row["smiles"] = _smiles_for_seed_name(row["name"], compounds)
        rows.append(row)
    seen = {normalize_name(r["name"]) for r in rows}
    for name in summary.get("known_inhibitors", []):
        key = normalize_name(name)
        if key in seen:
            continue
        rows.append(
            {
                "name": name,
                "smiles": "",
                "ic50_uM": "",
                "assay": "nitrocefin",
                "source": "literature_summary",
                "pmid_or_chembl_id": "",
            }
        )
        seen.add(key)

    REFERENCE_INHIBITORS_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["name", "smiles", "ic50_uM", "assay", "source", "pmid_or_chembl_id"]
    with REFERENCE_INHIBITORS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    return {"status": "ok", "path": str(REFERENCE_INHIBITORS_CSV), "count": len(rows)}


def _run_capped_search(
    query: str,
    source: str,
    *,
    save_raw: bool,
    save_dir: Path | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    if save_raw:
        result = save_literature_search(query=query, source=source, limit=PAPERCLIP_QUERY_LIMIT)
    else:
        result = search_literature(query=query, source=source, limit=PAPERCLIP_QUERY_LIMIT)
    result["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    if save_dir and result.get("status") == "ok" and result.get("output"):
        save_dir.mkdir(parents=True, exist_ok=True)
        existing = list(save_dir.glob("*.txt"))
        if len(existing) >= MAX_RAW_SEARCH_FILES_PER_COMPOUND:
            result["raw_cap_truncated"] = True
            return result
        safe = filename or f"{source}_{abs(hash(query)) % 10_000_000}.txt"
        out_path = save_dir / safe
        out_path.write_text(result.get("output", ""))
        result["saved_path"] = str(out_path)
    return result


def run_forward_literature_searches(save_raw: bool = True) -> dict[str, Any]:
    """Run predefined Paperclip queries for TEM-1 inhibitors (Phase B forward F1)."""
    results = []
    truncated: list[str] = []
    for query, source in FORWARD_QUERIES[:MAX_BATCH_PAPERCLIP_QUERIES]:
        results.append(_run_capped_search(query, source, save_raw=save_raw))

    state = _load_selection_state()
    state.setdefault("forward", {})
    state["forward"]["literature_searches"] = {
        "ran_at": _utc_now(),
        "caps": {
            "max_batch_queries": MAX_BATCH_PAPERCLIP_QUERIES,
            "query_limit": PAPERCLIP_QUERY_LIMIT,
            "max_searches_per_run": MAX_PAPERCLIP_SEARCHES_PER_RUN,
        },
        "queries": [{"query": q, "source": s} for q, s in FORWARD_QUERIES[:MAX_BATCH_PAPERCLIP_QUERIES]],
        "results": results,
        "search_count": len(results),
        "truncated": truncated,
    }
    path = _save_selection_state(state)
    return {"status": "ok", "selection_state": path, "search_results": results, "search_count": len(results)}


def search_literature_only_forms(save_raw: bool = True) -> dict[str, Any]:
    """Paperclip search for literature-only inhibitors (Case B); respects v1 search cap."""
    state = _load_selection_state()
    forward = state.get("forward", {})
    literature_only = forward.get("library_matches", {}).get("literature_only", [])
    if not literature_only:
        return {"status": "ok", "message": "no literature_only forms", "search_results": []}

    prior = forward.get("literature_searches", {})
    already = int(prior.get("search_count") or len(prior.get("results", [])))
    remaining = max(0, MAX_PAPERCLIP_SEARCHES_PER_RUN - already)
    budget = min(MAX_LITERATURE_ONLY_QUERIES, remaining)
    if budget == 0:
        return {
            "status": "error",
            "message": f"Paperclip search cap ({MAX_PAPERCLIP_SEARCHES_PER_RUN}) reached",
            "search_results": [],
        }

    results = list(prior.get("results", []))
    truncated: list[str] = list(prior.get("truncated", []))
    searched = 0
    for item in literature_only:
        if searched >= budget:
            truncated.append(item.get("reference", {}).get("name", "unknown"))
            continue
        ref = item.get("reference", {})
        name = ref.get("name") or "unknown"
        query = f"TEM-1 {name} beta-lactamase inhibitor nitrocefin"
        local_dir = LOCAL_LITERATURE / "_literature_only" / normalize_name(name).replace(" ", "_")
        result = _run_capped_search(
            query,
            "pmc",
            save_raw=save_raw,
            save_dir=local_dir if save_raw else None,
        )
        results.append(result)
        searched += 1
        stub = {
            "name": name,
            "match": "literature_only",
            "query": query,
            "search": {
                "result_id": result.get("result_id"),
                "elapsed_ms": result.get("elapsed_ms"),
                "status": result.get("status"),
            },
            "entries": [],
            "raw_local": str(local_dir),
        }
        LITERATURE_ONLY_REFS_DIR.mkdir(parents=True, exist_ok=True)
        stub_path = LITERATURE_ONLY_REFS_DIR / f"{normalize_name(name).replace(' ', '_')}.json"
        _write_json_capped(stub_path, stub)

    forward.setdefault("literature_searches", {})
    forward["literature_searches"].update(
        {
            "ran_at": _utc_now(),
            "results": results,
            "search_count": len(results),
            "truncated": truncated,
        }
    )
    state["forward"] = forward
    path = _save_selection_state(state)
    return {
        "status": "ok",
        "selection_state": path,
        "search_results": results[-searched:],
        "literature_only_searched": searched,
        "truncated": truncated,
    }


def match_literature_to_library(tanimoto_threshold: float = 0.85) -> dict[str, Any]:
    """Match reference inhibitors to library compounds (name → synonym → Tanimoto).

    Writes per-compound refs under data/compound_literature/refs/{compound_id}.json for direct hits.
    Links in-library alternate forms via forward.compound_groups (Case A).
    """
    refs_payload = load_reference_inhibitors()
    compounds = load_compounds()
    by_id = _compounds_by_id(compounds)
    matches: list[dict[str, Any]] = []
    literature_only: list[dict[str, Any]] = []

    for ref in refs_payload["inhibitors"]:
        ref_name = ref.get("name", "")
        ref_smiles = ref.get("smiles") or ""
        direct = _best_name_match(ref_name, compounds)
        analog = None
        best_tanimoto = 0.0

        if not direct and ref_smiles:
            for compound in compounds:
                if compound.get("exclude"):
                    continue
                if compound.get("smiles"):
                    score = tanimoto_smiles(ref_smiles, compound["smiles"])
                    if score is not None and score >= tanimoto_threshold and score > best_tanimoto:
                        best_tanimoto = score
                        analog = compound

        if direct:
            match_type = "direct"
            target = direct
        elif analog:
            match_type = "analog"
            target = analog
        else:
            literature_only.append({"reference": ref, "match": "none"})
            continue

        matches.append(
            {
                "reference_name": ref_name,
                "match_type": match_type,
                "compound_id": target["compound_id"],
                "compound_name": target.get("name"),
                "tanimoto": best_tanimoto if match_type == "analog" else 1.0,
            }
        )

    matched_ids = {m["compound_id"] for m in matches}
    groups = build_compound_groups(compounds, matched_ids, tanimoto_threshold=tanimoto_threshold)
    lookup = _group_lookup(groups)

    for match in matches:
        group = lookup.get(match["compound_id"])
        if group:
            match["group_id"] = group["group_id"]
            match["canonical_compound_id"] = group["canonical_compound_id"]
            match["related_forms"] = group["compound_ids"]

    refs_written: set[str] = set()
    for match in matches:
        cid = match["compound_id"]
        group = lookup.get(cid)
        compound = by_id.get(cid, {})
        ref_name = match["reference_name"]
        ref_row = next((r for r in refs_payload["inhibitors"] if r.get("name") == ref_name), {})
        canonical_id = group["canonical_compound_id"] if group else cid

        if group and cid != canonical_id:
            _write_alternate_ref(cid, compound, group, ref_name)
            refs_written.add(cid)
            if canonical_id not in refs_written and not _ref_file_is_curated(LITERATURE_REFS_DIR / f"{canonical_id}.json"):
                _write_canonical_ref(
                    canonical_id,
                    by_id.get(canonical_id, {}),
                    group,
                    ref_name,
                    ref_row,
                    match["match_type"],
                )
                refs_written.add(canonical_id)
        elif cid not in refs_written:
            _write_canonical_ref(cid, compound, group, ref_name, ref_row, match["match_type"])
            refs_written.add(cid)

    state = _load_selection_state()
    state.setdefault("forward", {})
    state["forward"]["library_matches"] = {
        "ran_at": _utc_now(),
        "tanimoto_threshold": tanimoto_threshold,
        "matches": matches,
        "literature_only": literature_only,
    }
    state["forward"]["compound_groups"] = groups
    path = _save_selection_state(state)

    return {
        "status": "ok",
        "selection_state": path,
        "direct_and_analog_matches": len(matches),
        "literature_only_count": len(literature_only),
        "compound_group_count": len(groups),
        "matches": matches,
        "literature_only": literature_only,
        "compound_groups": groups,
    }


def write_literature_summary_from_forward() -> dict[str, Any]:
    """Merge forward match results into data/literature_summary.json (non-destructive patch)."""
    state = _load_selection_state()
    forward = state.get("forward", {})
    matches = forward.get("library_matches", {}).get("matches", [])

    if LITERATURE_SUMMARY_JSON.exists():
        summary = json.loads(LITERATURE_SUMMARY_JSON.read_text())
    else:
        summary = {}

    matched_names = [m["reference_name"] for m in matches]
    known = list(summary.get("known_inhibitors", []))
    for name in matched_names:
        if name not in known:
            known.append(name)
    summary["known_inhibitors"] = known
    summary.setdefault("library_notes", {})["forward_match_count"] = len(matches)
    summary["library_notes"]["forward_compound_groups"] = len(forward.get("compound_groups", []))
    summary["forward_updated_at"] = _utc_now()

    LITERATURE_SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n")

    return {"status": "ok", "path": str(LITERATURE_SUMMARY_JSON), "known_inhibitors": known}


def _unique_ref_compound_ids(forward: dict[str, Any]) -> list[str]:
    ids: set[str] = set()
    for group in forward.get("compound_groups", []):
        ids.update(group.get("compound_ids", []))
    for match in forward.get("library_matches", {}).get("matches", []):
        if match.get("compound_id"):
            ids.add(match["compound_id"])
        if match.get("canonical_compound_id"):
            ids.add(match["canonical_compound_id"])
    return sorted(ids)


def finalize_forward_run(version: int = 1, author: str = "pvjthomas") -> dict[str, Any]:
    """Snapshot forward-agent outputs to ml/workflows/compound_selection/snapshots/forward/v{version}/."""
    state = _load_selection_state()
    forward = state.get("forward", {})
    if not forward.get("library_matches"):
        return {
            "status": "error",
            "message": "forward.library_matches missing — run match_literature_to_library() first",
        }

    version_label = f"v{version}"
    run_dir = FORWARD_SNAPSHOTS_DIR / version_label
    refs_dir = run_dir / "refs"
    run_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)

    rel_prefix = run_dir.relative_to(REPO_ROOT).as_posix()
    manifest_rel = f"{rel_prefix}/manifest.json"
    unique_ref_ids = _unique_ref_compound_ids(forward)

    if REFERENCE_INHIBITORS_CSV.exists():
        shutil.copy2(REFERENCE_INHIBITORS_CSV, run_dir / "reference_inhibitors.csv")

    forward_snapshot = {
        "schema_version": 1,
        "agent": "forward_agent",
        "agent_version": version_label,
        "run_label": FORWARD_AGENT_LABEL if version == 1 else f"forward-research-agent-{version_label}",
        "forward": forward,
    }
    (run_dir / "state_forward.json").write_text(json.dumps(forward_snapshot, indent=2) + "\n")

    summary_patch: dict[str, Any] = {}
    if LITERATURE_SUMMARY_JSON.exists():
        summary = json.loads(LITERATURE_SUMMARY_JSON.read_text())
        summary_patch = {
            "known_inhibitors": summary.get("known_inhibitors", []),
            "library_notes": summary.get("library_notes", {}),
            "forward_updated_at": summary.get("forward_updated_at"),
        }
        (run_dir / "literature_summary_patch.json").write_text(json.dumps(summary_patch, indent=2) + "\n")

    copied_refs: list[str] = []
    for compound_id in unique_ref_ids:
        src = LITERATURE_REFS_DIR / f"{compound_id}.json"
        if src.exists():
            dst = refs_dir / f"{compound_id}.json"
            shutil.copy2(src, dst)
            copied_refs.append(compound_id)

    if LITERATURE_ONLY_REFS_DIR.exists():
        lo_dst = refs_dir / "_literature_only"
        lo_dst.mkdir(parents=True, exist_ok=True)
        for src in LITERATURE_ONLY_REFS_DIR.glob("*.json"):
            shutil.copy2(src, lo_dst / src.name)

    created_at = _utc_now()
    manifest = {
        "agent": "forward_agent",
        "version": version,
        "label": FORWARD_AGENT_LABEL if version == 1 else f"forward-research-agent-{version_label}",
        "created_at": created_at,
        "author": author,
        "status": "complete",
        "description": (
            f"Forward research agent {version_label} — Phase B literature → library inhibitor matching"
        ),
        "files": {
            "manifest": manifest_rel,
            "reference_inhibitors": f"{rel_prefix}/reference_inhibitors.csv",
            "state_forward": f"{rel_prefix}/state_forward.json",
            "literature_summary_patch": f"{rel_prefix}/literature_summary_patch.json",
            "refs": f"{rel_prefix}/refs/",
            "active_reference_inhibitors": "data/reference_inhibitors.csv",
            "active_selection_state": SELECTION_STATE_JSON.relative_to(REPO_ROOT).as_posix(),
        },
        "match_count": len(forward.get("library_matches", {}).get("matches", [])),
        "literature_only_count": len(forward.get("library_matches", {}).get("literature_only", [])),
        "compound_group_count": len(forward.get("compound_groups", [])),
        "compound_groups": forward.get("compound_groups", []),
        "ref_compound_ids": unique_ref_ids,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    state.setdefault("forward", {})
    state["forward"]["agent_version"] = version_label
    state["forward"]["run_label"] = manifest["label"]
    state["forward"]["manifest"] = manifest_rel
    state["forward"]["finalized_at"] = created_at
    selection_path = _save_selection_state(state)

    return {
        "status": "ok",
        "manifest": str(run_dir / "manifest.json"),
        "run_dir": str(run_dir),
        "selection_state": selection_path,
        "match_count": manifest["match_count"],
        "compound_group_count": manifest["compound_group_count"],
        "ref_compound_ids": unique_ref_ids,
    }
