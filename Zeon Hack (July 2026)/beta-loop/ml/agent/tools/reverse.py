"""Reverse selection tools — library → scaffold tags, docking, per-compound literature."""

from __future__ import annotations

import json
import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.paths import (
    COMPOUNDS_CSV,
    COMPOUND_DOSSIERS_JSON,
    LITERATURE_REFS_DIR,
    LITERATURE_SEARCH_CACHE_JSON,
    LITERATURE_SUMMARY_JSON,
    LOCAL_DOCKING,
    LOCAL_LITERATURE,
    REPO_ROOT,
    SELECTION_STATE_JSON,
)
from agent.tools.chem import RDKIT_AVAILABLE, normalize_name, rdkit_status, smarts_match
from agent.tools.compounds import load_compounds
from agent.tools.docking import gnina_status, run_batch_dock
from agent.tools.forward import (
    _apply_entry_caps,
    _ref_file_is_curated,
    _write_json_capped,
)
from agent.tools.literature import map_literature_results, search_literature
from agent.tools.literature_repositories import DEFAULT_REPOSITORY_SOURCES, REPOSITORY_SOURCES

# Phase A bootstrap IDs — always inhibitor / exclude regardless of SMARTS.
TIER1_INHIBITOR_IDS = {
    "T19860",
    "T14979",
    "T6685",
    "T1631",
    "T1262",
    "T14081",
    "T13038",
}
EXCLUDE_IDS = {"T19709"}

INHIBITOR_NAME_FRAGMENTS = ("clavulan", "sulbactam", "tazobactam", "enmetazobactam", "sultamicillin")

# Reverse literature check caps (Step R3) — see pvjthomas/COMPOUND_SELECTION.md
# Bump REVERSE_SEARCH_VERSION when query templates or source policy changes (invalidates cache).
REVERSE_SEARCH_VERSION = 2
MAX_REVERSE_LITERATURE_COMPOUNDS = 10
MAX_REVERSE_QUERY_LIMIT = 30
MAX_REVERSE_MAP_PER_RUN = 10
DEFAULT_REVERSE_TIERS = (1, 2)
DEFAULT_REVERSE_SOURCES = DEFAULT_REPOSITORY_SOURCES
REVERSE_MAP_QUESTION_INHIBITOR = (
    "For {name} against TEM-1 beta-lactamase in a nitrocefin colorimetric assay: "
    "report Ki or IC50 in µM, the inhibitor concentration(s) used in the assay "
    "(µM; single-point screen concentration preferred, or the full tested range), "
    "nitrocefin substrate concentration (µM), TEM-1 enzyme concentration (nM), "
    "PMID or PMCID, and whether the compound acts as an inhibitor or substrate."
)
REVERSE_MAP_QUESTION_SUBSTRATE = (
    "For {name} against TEM-1 beta-lactamase in a nitrocefin colorimetric assay: "
    "report whether the compound is hydrolyzed as a substrate or inhibits nitrocefin cleavage, "
    "any Ki or IC50 in µM if measured, nitrocefin substrate concentration (µM), "
    "TEM-1 enzyme concentration (nM), PMID or PMCID, and expected inhibition at 50 µM."
)

DEFAULT_PROJECT_SCREEN_U_M = 50
ACTIVITY_MULTIPLIER = 10
ASSAY_COMPOUND_VOLUME_UL = 5
ASSAY_FINAL_VOLUME_UL = 50
DEFAULT_STOCK_M_M = 10


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


def _normalize_tier(tier: Any) -> int | None:
    """Normalize compounds.csv tier values (float 1.0, int, str) to int."""
    if tier is None or tier == "" or str(tier).lower() == "nan":
        return None
    try:
        return int(float(tier))
    except (TypeError, ValueError):
        return None


def _select_literature_targets(
    compounds: list[dict[str, Any]],
    compound_ids: list[str] | None,
    tiers: tuple[int, ...] | list[int] | None,
    *,
    all_library: bool = False,
) -> list[dict[str, Any]]:
    if all_library:
        return [c for c in compounds if not c.get("exclude")]
    if compound_ids:
        id_set = set(compound_ids)
        return [c for c in compounds if c["compound_id"] in id_set and not c.get("exclude")]
    tier_set = set(tiers or DEFAULT_REVERSE_TIERS)
    return [
        c
        for c in compounds
        if _normalize_tier(c.get("tier")) in tier_set and not c.get("exclude")
    ]


def _scaffold_class_for_compound(compound: dict[str, Any]) -> str:
    existing = compound.get("scaffold_class")
    if existing and str(existing) not in ("", "nan"):
        return str(existing)
    scaffold_class, _ = _classify_compound(compound)
    return scaffold_class


def _build_reverse_query(name: str, scaffold_class: str) -> str:
    if scaffold_class == "inhibitor":
        return f"TEM-1 {name} nitrocefin colorimetric assay inhibitor concentration Ki IC50"
    if scaffold_class == "antibiotic_substrate":
        return f"TEM-1 {name} nitrocefin colorimetric assay hydrolysis substrate Ki IC50"
    return f"TEM-1 {name} nitrocefin colorimetric assay concentration Ki IC50"


def _build_map_question(name: str, scaffold_class: str) -> str:
    if scaffold_class == "antibiotic_substrate":
        return REVERSE_MAP_QUESTION_SUBSTRATE.format(name=name)
    return REVERSE_MAP_QUESTION_INHIBITOR.format(name=name)


def _load_literature_search_cache() -> dict[str, Any]:
    if not LITERATURE_SEARCH_CACHE_JSON.exists():
        return {
            "schema_version": 1,
            "search_version": REVERSE_SEARCH_VERSION,
            "updated_at": None,
            "searches": {},
            "maps": {},
        }
    payload = json.loads(LITERATURE_SEARCH_CACHE_JSON.read_text())
    if payload.get("search_version") != REVERSE_SEARCH_VERSION:
        return {
            "schema_version": 1,
            "search_version": REVERSE_SEARCH_VERSION,
            "updated_at": _utc_now(),
            "searches": {},
            "maps": {},
            "prior_version": payload.get("search_version"),
        }
    payload.setdefault("searches", {})
    payload.setdefault("maps", {})
    return payload


def _save_literature_search_cache(cache: dict[str, Any]) -> None:
    LITERATURE_SEARCH_CACHE_JSON.parent.mkdir(parents=True, exist_ok=True)
    cache["updated_at"] = _utc_now()
    cache["search_version"] = REVERSE_SEARCH_VERSION
    LITERATURE_SEARCH_CACHE_JSON.write_text(json.dumps(cache, indent=2) + "\n")


def _search_cache_fingerprint(
    compound_id: str,
    query: str,
    source: str,
    limit: int,
    search_version: int,
) -> tuple[str, str]:
    raw = f"v{search_version}|{compound_id}|{source}|{limit}|{query}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return digest, raw


def _map_cache_fingerprint(from_results: str, question: str, search_version: int) -> str:
    raw = f"v{search_version}|{from_results}|{question}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _entry_dedup_key(entry: dict[str, Any]) -> str | None:
    search_id = entry.get("paperclip_search_id")
    paperclip_source = entry.get("paperclip_source")
    if search_id and paperclip_source:
        return f"search:{paperclip_source}:{search_id}"
    if entry.get("pmid"):
        return f"pmid:{entry['pmid']}"
    if entry.get("pmcid"):
        return f"pmcid:{entry['pmcid']}"
    if entry.get("doi"):
        return f"doi:{entry['doi']}"
    return None


def _entry_has_useful_activity(entry: dict[str, Any]) -> bool:
    return bool(
        entry.get("ki_uM")
        or entry.get("ic50_uM")
        or entry.get("literature_inhibitor_uM")
        or entry.get("nitrocefin_uM")
        or entry.get("enzyme_nM")
    )


def _screen_conc_source_priority(source: str | None) -> int:
    """Higher = stronger evidence for concentration rule (1 > 2 > 3 default)."""
    if source == "literature":
        return 3
    if source and source.startswith("10x_"):
        return 2
    return 1


def _pick_best_entry(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None

    def rank(entry: dict[str, Any]) -> tuple[int, int, int, int]:
        # Rule 1: nitrocefin-assay inhibitor concentration beats Ki/IC50 (rule 2).
        lit_conc = 1 if entry.get("literature_inhibitor_uM") else 0
        ki_ic50 = 1 if entry.get("ki_uM") or entry.get("ic50_uM") else 0
        assay_ctx = 1 if entry.get("nitrocefin_uM") or entry.get("enzyme_nM") else 0
        any_activity = 1 if _entry_has_useful_activity(entry) else 0
        return (lit_conc, ki_ic50, assay_ctx, any_activity)

    return sorted(entries, key=rank, reverse=True)[0]


def _round_conc_uM(value: float) -> float:
    if value >= 100:
        return float(round(value))
    if value >= 10:
        return round(value, 1)
    return round(value, 2)


def _max_assay_conc_uM(compound: dict[str, Any]) -> float:
    """Max final assay concentration from library stock (5 µL into 50 µL)."""
    try:
        stock_mM = float(compound.get("concentration_mM") or DEFAULT_STOCK_M_M)
    except (TypeError, ValueError):
        stock_mM = DEFAULT_STOCK_M_M
    stock_uM = stock_mM * 1000
    return stock_uM * (ASSAY_COMPOUND_VOLUME_UL / ASSAY_FINAL_VOLUME_UL)


def _parse_inhibitor_concentrations(map_output: str, compound_name: str) -> dict[str, Any]:
    """Extract nitrocefin-assay concentrations from Paperclip map text."""
    parsed: dict[str, Any] = {}

    nitrocefin_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:µM|uM|microM|μM)\s+nitrocefin",
        map_output,
        re.I,
    )
    if not nitrocefin_match:
        nitrocefin_match = re.search(
            r"nitrocefin\s*(?:at\s*)?(\d+(?:\.\d+)?)\s*(?:µM|uM|microM|μM)",
            map_output,
            re.I,
        )
    if nitrocefin_match:
        parsed["nitrocefin_uM"] = float(nitrocefin_match.group(1))

    enzyme_match = re.search(
        r"(?:TEM-1|enzyme)[^.\n]{0,40}?(\d+(?:\.\d+)?)\s*nM",
        map_output,
        re.I,
    )
    if not enzyme_match:
        enzyme_match = re.search(
            r"(\d+(?:\.\d+)?)\s*nM[^.\n]{0,40}?(?:TEM-1|enzyme)",
            map_output,
            re.I,
        )
    if enzyme_match:
        parsed["enzyme_nM"] = float(enzyme_match.group(1))

    screen_match = re.search(
        r"(?:screen(?:ed|ing)?(?:\s+at)?|single[- ]?point|tested at|at a concentration of)"
        r"\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:µM|uM|microM|μM)",
        map_output,
        re.I,
    )
    if screen_match:
        parsed["literature_inhibitor_uM"] = float(screen_match.group(1))
        parsed["literature_inhibitor_source"] = "explicit_screen"

    if "literature_inhibitor_uM" not in parsed:
        name_pattern = re.escape(compound_name.split()[0])
        named_match = re.search(
            rf"{name_pattern}[^.\n]{{0,50}}?(\d+(?:\.\d+)?)\s*(?:µM|uM|microM|μM)",
            map_output,
            re.I,
        )
        if named_match:
            parsed["literature_inhibitor_uM"] = float(named_match.group(1))
            parsed["literature_inhibitor_source"] = "named_single_point"

    range_match = re.search(
        r"(?:inhibitor|compound|concentration)[^.\n]{0,40}?"
        r"(\d+(?:\.\d+)?)\s*[–\-—to]\s*(\d+(?:\.\d+)?)\s*(?:µM|uM|microM|μM)",
        map_output,
        re.I,
    )
    if not range_match:
        range_match = re.search(
            r"(\d+(?:\.\d+)?)\s*[–\-—to]\s*(\d+(?:\.\d+)?)\s*(?:µM|uM|microM|μM)",
            map_output,
            re.I,
        )
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        parsed["inhibitor_uM_range"] = [low, high]
        if "literature_inhibitor_uM" not in parsed:
            parsed["literature_inhibitor_uM"] = high
            parsed["literature_inhibitor_source"] = "assay_range_max"

    return parsed


def _recommend_screen_conc_uM(entry: dict[str, Any], compound: dict[str, Any]) -> dict[str, Any]:
    """Pick a screen concentration: literature assay conc, else 10× IC50/Ki capped at solubility."""
    max_uM = _max_assay_conc_uM(compound)

    literature_uM = entry.get("literature_inhibitor_uM")
    if literature_uM and literature_uM > 0:
        capped = min(literature_uM, max_uM)
        source = entry.get("literature_inhibitor_source") or "literature"
        rationale = f"Literature nitrocefin assay inhibitor concentration ({literature_uM} µM)."
        if capped < literature_uM:
            rationale += f" Capped at library solubility limit ({max_uM:g} µM final)."
        return {
            "screen_conc_uM": _round_conc_uM(capped),
            "screen_rationale": rationale,
            "screen_conc_source": "literature",
            "literature_inhibitor_uM": literature_uM,
            "literature_inhibitor_source": source,
            "max_assay_conc_uM": max_uM,
        }

    ic50_uM = entry.get("ic50_uM")
    ki_uM = entry.get("ki_uM")
    activity_uM = ic50_uM or ki_uM
    activity_metric = "IC50" if ic50_uM else "Ki"
    if activity_uM and activity_uM > 0:
        target = ACTIVITY_MULTIPLIER * activity_uM
        capped = min(target, max_uM)
        rationale = f"{ACTIVITY_MULTIPLIER}× literature {activity_metric} ({activity_uM} µM)"
        if capped < target:
            rationale += f", capped at library solubility ({max_uM:g} µM final from {DEFAULT_STOCK_M_M:g} mM stock)."
        else:
            rationale += "."
        return {
            "screen_conc_uM": _round_conc_uM(capped),
            "screen_rationale": rationale,
            "screen_conc_source": f"{ACTIVITY_MULTIPLIER}x_{activity_metric.lower()}",
            "activity_uM": activity_uM,
            "activity_metric": activity_metric,
            "max_assay_conc_uM": max_uM,
        }

    return {
        "screen_conc_uM": DEFAULT_PROJECT_SCREEN_U_M,
        "screen_rationale": (
            "Project default screen concentration; no literature inhibitor concentration or IC50/Ki extracted."
        ),
        "screen_conc_source": "project_default",
        "max_assay_conc_uM": max_uM,
    }


def _assay_recommendations_from_entry(
    entry: dict[str, Any],
    compound: dict[str, Any],
) -> dict[str, Any]:
    screen = _recommend_screen_conc_uM(entry, compound)
    block: dict[str, Any] = {
        "screen_conc_uM": screen["screen_conc_uM"],
        "screen_rationale": screen["screen_rationale"],
        "screen_conc_source": screen["screen_conc_source"],
        "max_assay_conc_uM": screen["max_assay_conc_uM"],
        "metric": "relative nitrocefin hydrolysis vs no-inhibitor control",
    }
    for key in (
        "literature_inhibitor_uM",
        "literature_inhibitor_source",
        "inhibitor_uM_range",
        "activity_uM",
        "activity_metric",
        "nitrocefin_uM",
        "enzyme_nM",
    ):
        if entry.get(key) is not None:
            block[key] = entry[key]
    return {"tem1_nitrocefin": block}


def _parse_activity_entry(
    map_output: str,
    *,
    compound_name: str,
    search_id: str | None,
    map_id: str | None,
) -> dict[str, Any]:
    """Best-effort structured entry from Paperclip map text."""
    entry: dict[str, Any] = {
        "source": "paperclip",
        "target": "TEM-1",
        "assay": "nitrocefin",
        "note": map_output.strip()[:2000],
    }
    if search_id:
        entry["paperclip_search_id"] = search_id
    if map_id:
        entry["paperclip_map_id"] = map_id

    ki_match = re.search(r"Ki\s*[=≈:]?\s*([\d.]+)\s*(?:µM|uM|microM|μM)", map_output, re.I)
    ic50_match = re.search(r"IC50\s*[=≈:]?\s*([\d.]+)\s*(?:µM|uM|microM|μM)", map_output, re.I)
    pmid_match = re.search(r"PMID[:\s#]*(\d+)", map_output, re.I)
    pmcid_match = re.search(r"(PMC\d+)", map_output, re.I)
    doi_match = re.search(r"(10\.\d{4,9}/[^\s\])]+)", map_output, re.I)

    if ki_match:
        entry["ki_uM"] = float(ki_match.group(1))
    else:
        entry["ki_uM"] = None
    if ic50_match:
        entry["ic50_uM"] = float(ic50_match.group(1))
    else:
        entry["ic50_uM"] = None
    if pmid_match:
        entry["pmid"] = pmid_match.group(1)
    if pmcid_match:
        entry["pmcid"] = pmcid_match.group(1)
    if doi_match:
        entry["doi"] = doi_match.group(1)

    title_match = re.search(r"title[:\s]+(.+)", map_output, re.I)
    if title_match:
        entry["title"] = title_match.group(1).strip()[:300]

    entry.update(_parse_inhibitor_concentrations(map_output, compound_name))

    entry["note"] = (
        f"Reverse literature check for {compound_name}. "
        + (map_output.strip()[:1500] if map_output else "No map output.")
    )
    return entry


def _merge_reverse_ref(
    compound: dict[str, Any],
    entries: dict[str, Any] | list[dict[str, Any]],
    *,
    skip_curated: bool,
) -> dict[str, Any]:
    compound_id = str(compound["compound_id"])
    ref_path = LITERATURE_REFS_DIR / f"{compound_id}.json"
    if skip_curated and _ref_file_is_curated(ref_path):
        return {"status": "skipped_curated", "ref_path": str(ref_path)}

    new_entries = entries if isinstance(entries, list) else [entries]

    if ref_path.exists():
        payload = json.loads(ref_path.read_text())
    else:
        payload = {
            "compound_id": compound_id,
            "name": compound.get("name"),
            "match": "yes",
            "support": "weak",
            "entries": [],
            "raw_local": str(LOCAL_LITERATURE / compound_id / ""),
        }

    merged = list(payload.get("entries", []))
    seen = {k for e in merged if (k := _entry_dedup_key(e))}
    appended = 0
    skipped_dup = 0
    for entry in new_entries:
        key = _entry_dedup_key(entry)
        if key and key in seen:
            skipped_dup += 1
            continue
        merged.append(entry)
        appended += 1
        if key:
            seen.add(key)

    merged, truncated = _apply_entry_caps(merged)
    payload["entries"] = merged
    if truncated:
        payload["cap_truncated"] = True

    best = _pick_best_entry(new_entries)
    if best:
        new_recs = _assay_recommendations_from_entry(best, compound)
        existing = payload.get("assay_recommendations", {}).get("tem1_nitrocefin", {})
        new_block = new_recs.get("tem1_nitrocefin", {})
        existing_pri = _screen_conc_source_priority(existing.get("screen_conc_source"))
        new_pri = _screen_conc_source_priority(new_block.get("screen_conc_source"))
        if not existing or new_pri > existing_pri or (
            new_pri == existing_pri
            and new_pri > 1
            and new_block.get("screen_conc_uM") != existing.get("screen_conc_uM")
        ):
            payload["assay_recommendations"] = new_recs
        if _entry_has_useful_activity(best):
            payload["support"] = "strong"

    LITERATURE_REFS_DIR.mkdir(parents=True, exist_ok=True)
    _write_json_capped(ref_path, payload)
    screen_rec = _recommend_screen_conc_uM(best or {}, compound) if best else {}
    return {
        "status": "written",
        "ref_path": str(ref_path),
        "entries_appended": appended,
        "entries_skipped_duplicate": skipped_dup,
        "ki_uM": best.get("ki_uM") if best else None,
        "ic50_uM": best.get("ic50_uM") if best else None,
        "screen_conc_uM": screen_rec.get("screen_conc_uM"),
        "screen_conc_source": screen_rec.get("screen_conc_source"),
    }


def _patch_literature_summary_prior(compound: dict[str, Any], entry: dict[str, Any], ref_path: str) -> None:
    if not LITERATURE_SUMMARY_JSON.exists():
        return
    summary = json.loads(LITERATURE_SUMMARY_JSON.read_text())
    priors = summary.setdefault("compound_assay_priors", {})
    compound_id = str(compound["compound_id"])
    screen_rec = _recommend_screen_conc_uM(entry, compound)
    existing = priors.get(compound_id, {})
    existing_pri = _screen_conc_source_priority(existing.get("screen_conc_source"))
    new_pri = _screen_conc_source_priority(screen_rec["screen_conc_source"])
    if existing and new_pri < existing_pri:
        return
    if existing and new_pri == existing_pri and existing.get("recommended_screen_uM") == screen_rec["screen_conc_uM"]:
        if existing.get("literature_ki_uM_tem1") and not entry.get("ki_uM"):
            return
    prior: dict[str, Any] = {
        "name": compound.get("name"),
        "recommended_screen_uM": screen_rec["screen_conc_uM"],
        "screen_conc_source": screen_rec["screen_conc_source"],
        "refs_file": str(Path(ref_path).relative_to(REPO_ROOT)),
    }
    ki_uM = entry.get("ki_uM")
    ic50_uM = entry.get("ic50_uM")
    if ki_uM:
        prior["literature_ki_uM_tem1"] = ki_uM
    if ic50_uM:
        prior["literature_ic50_uM_tem1"] = ic50_uM
    if ki_uM or ic50_uM or entry.get("literature_inhibitor_uM"):
        prior["expected_at_recommended_uM"] = ">=50% inhibition"
    if entry.get("assay"):
        prior["literature_assay"] = {"type": f"TEM-1 {entry.get('assay')} inhibition"}
    priors[compound_id] = prior
    summary["reverse_literature_updated_at"] = _utc_now()
    LITERATURE_SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n")


def _run_reverse_search(
    query: str,
    *,
    source: str,
    limit: int,
    save_raw: bool,
    compound_id: str,
    cache: dict[str, Any],
    use_cache: bool,
    search_version: int,
) -> dict[str, Any]:
    cache_key, cache_raw = _search_cache_fingerprint(compound_id, query, source, limit, search_version)
    cached = cache.get("searches", {}).get(cache_key)
    if use_cache and cached and cached.get("status") == "ok":
        return {
            **cached,
            "status": "ok",
            "cache_hit": True,
            "cache_key": cache_key,
        }

    started = time.perf_counter()
    result = search_literature(query=query, source=source, limit=limit)
    result["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    result["cache_hit"] = False
    result["cache_key"] = cache_key
    result["paperclip_source"] = source

    if save_raw and result.get("status") == "ok" and result.get("output"):
        save_dir = LOCAL_LITERATURE / compound_id
        save_dir.mkdir(parents=True, exist_ok=True)
        safe = f"reverse_{source}_{abs(hash(query)) % 10_000_000}.txt"
        out_path = save_dir / safe
        out_path.write_text(result["output"])
        result["saved_path"] = str(out_path)

    if result.get("status") == "ok":
        cache.setdefault("searches", {})[cache_key] = {
            "compound_id": compound_id,
            "query": query,
            "source": source,
            "limit": limit,
            "search_version": search_version,
            "cache_raw": cache_raw,
            "ran_at": _utc_now(),
            **{k: result[k] for k in ("result_id", "elapsed_ms", "saved_path") if k in result},
            "status": "ok",
        }

    return result


def _run_reverse_map(
    question: str,
    from_results: str,
    *,
    cache: dict[str, Any],
    use_cache: bool,
    search_version: int,
) -> dict[str, Any]:
    cache_key = _map_cache_fingerprint(from_results, question, search_version)
    cached = cache.get("maps", {}).get(cache_key)
    if use_cache and cached and cached.get("status") == "ok":
        return {**cached, "status": "ok", "cache_hit": True, "cache_key": cache_key}

    started = time.perf_counter()
    map_result = map_literature_results(question, from_results=from_results)
    map_result["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    map_result["cache_hit"] = False
    map_result["cache_key"] = cache_key

    if map_result.get("status") == "ok":
        cache.setdefault("maps", {})[cache_key] = {
            "from_results": from_results,
            "question": question,
            "search_version": search_version,
            "ran_at": _utc_now(),
            **{k: map_result[k] for k in ("result_id", "output", "elapsed_ms") if k in map_result},
            "status": "ok",
        }

    return map_result


def _classify_compound(compound: dict[str, Any]) -> tuple[str, int | None]:
    cid = compound.get("compound_id", "")
    name = (compound.get("name") or "").lower()
    receptor = (compound.get("receptor") or "").lower()
    target = (compound.get("target") or "").lower()
    text = " ".join([receptor, target, name])

    if cid in EXCLUDE_IDS:
        return "exclude", None
    if cid in TIER1_INHIBITOR_IDS or any(frag in name for frag in INHIBITOR_NAME_FRAGMENTS):
        return "inhibitor", 1

    smiles = compound.get("smiles") or ""
    if RDKIT_AVAILABLE and smiles:
        # Clavulanate / penicillanic sulfone warheads (minimal side chain).
        if smarts_match(smiles, "[#6]1[#6][#6](=O)[#7]1"):
            if any(k in name for k in ("sulbactam", "tazobactam", "clavulan", "enmetazobactam")):
                return "inhibitor", 1
        # Full acyl side chains → antibiotic substrate.
        if smarts_match(smiles, "NC(=O)[C@H]") and any(
            k in text for k in ("antibiotic", "pbp", "bacterial", "penicillin", "cephalosporin", "carbapenem")
        ):
            return "antibiotic_substrate", 3

    if any(k in text for k in ("antibiotic", "pbp", "bacterial")):
        return "antibiotic_substrate", 3
    return "other_β_lactam", 2


def classify_scaffolds_rdkit(write_csv: bool = False) -> dict[str, Any]:
    """Re-tag all library compounds using RDKit SMARTS + bootstrap inhibitor IDs (Phase B reverse R1).

    Args:
        write_csv: If True, patch scaffold_class/tier/exclude columns in data/compounds.csv.
    """
    compounds = load_compounds()
    tagged: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for compound in compounds:
        scaffold_class, tier = _classify_compound(compound)
        counts[scaffold_class] = counts.get(scaffold_class, 0) + 1
        tagged.append(
            {
                "compound_id": compound["compound_id"],
                "name": compound.get("name"),
                "scaffold_class": scaffold_class,
                "tier": tier,
                "exclude": scaffold_class == "exclude",
            }
        )

    if write_csv and COMPOUNDS_CSV.exists():
        import csv

        with COMPOUNDS_CSV.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            fieldnames = rows[0].keys() if rows else []
        tag_by_id = {t["compound_id"]: t for t in tagged}
        for row in rows:
            tag = tag_by_id.get(row["compound_id"])
            if not tag:
                continue
            row["scaffold_class"] = tag["scaffold_class"]
            row["tier"] = str(tag["tier"]) if tag["tier"] is not None else ""
            row["exclude"] = "true" if tag["exclude"] else "false"
        with COMPOUNDS_CSV.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    state = _load_selection_state()
    state["reverse"]["scaffold_classification"] = {
        "ran_at": _utc_now(),
        "rdkit": rdkit_status(),
        "counts": counts,
        "compounds": tagged,
        "csv_updated": write_csv,
    }
    path = _save_selection_state(state)

    return {
        "status": "ok",
        "selection_state": path,
        "rdkit": rdkit_status(),
        "counts": counts,
        "sample": tagged[:5],
    }


def run_gnina_batch(
    receptor_pdb: str = "1JQL",
    max_compounds: int = 105,
    *,
    skip_existing: bool = True,
    exhaustiveness: int = 8,
    timeout_sec: int = 600,
) -> dict[str, Any]:
    """Batch GNINA docking vs TEM-1 (PDB 1JQL). Poses → pvjthomas/local/docking/ (Phase B reverse R2)."""
    LOCAL_DOCKING.mkdir(parents=True, exist_ok=True)
    compounds = [c for c in load_compounds() if not c.get("exclude")][:max_compounds]
    batch = run_batch_dock(
        compounds,
        receptor_pdb=receptor_pdb,
        skip_existing=skip_existing,
        exhaustiveness=exhaustiveness,
        timeout_sec=timeout_sec,
    )

    state = _load_selection_state()
    state["reverse"]["gnina_batch"] = {
        "ran_at": _utc_now(),
        "status": batch["status"],
        "receptor_pdb": batch.get("receptor_pdb", receptor_pdb),
        "requested_pdb": receptor_pdb,
        "alias_note": batch.get("alias_note"),
        "compound_count": len(compounds),
        "docked": batch.get("docked", 0),
        "skipped_existing": batch.get("skipped_existing", 0),
        "failed": batch.get("failed", 0),
        "scores_in_dossiers": batch.get("scores_in_dossiers", 0),
        "poses_local": str(LOCAL_DOCKING),
        "gnina": batch.get("gnina", gnina_status()),
        "autobox_residue": batch.get("autobox_residue"),
        "message": batch.get("message"),
    }
    path = _save_selection_state(state)

    if batch["status"] == "missing_binary":
        return {
            "status": "missing_binary",
            "selection_state": path,
            "receptor_pdb": receptor_pdb,
            "compound_count": len(compounds),
            "poses_local": str(LOCAL_DOCKING),
            "message": batch["message"],
            "next_step": "Install GNINA (scripts/install-gnina.sh), then re-run run_gnina_batch().",
        }

    return {
        "status": batch["status"],
        "selection_state": path,
        "receptor_pdb": receptor_pdb,
        "compound_count": len(compounds),
        "docked": batch.get("docked", 0),
        "scores_in_dossiers": batch.get("scores_in_dossiers", 0),
        "poses_local": str(LOCAL_DOCKING),
        "dossiers": batch.get("dossiers"),
        "sample_results": (batch.get("results") or [])[:5],
    }


def load_dock_scores() -> dict[str, Any]:
    """Load GNINA CNN affinity scores from compound_dossiers.json (if populated)."""
    if not COMPOUND_DOSSIERS_JSON.exists():
        return {"status": "missing", "path": str(COMPOUND_DOSSIERS_JSON), "scores": []}
    dossiers = json.loads(COMPOUND_DOSSIERS_JSON.read_text())
    scores = []
    for cid, entry in dossiers.get("compounds", {}).items():
        affinity = entry.get("docking", {}).get("gnina_cnn_affinity")
        if affinity is not None:
            scores.append({"compound_id": cid, "gnina_cnn_affinity": affinity})
    scores.sort(key=lambda x: x["gnina_cnn_affinity"])
    return {"status": "ok", "count": len(scores), "scores": scores}


def rank_by_dock_score(top_n: int = 8) -> dict[str, Any]:
    """Rank non-Tier-1 library compounds by GNINA score for Tier 3 picks (Phase B reverse R2)."""
    compounds = load_compounds()
    tier1_ids = {c["compound_id"] for c in compounds if _normalize_tier(c.get("tier")) == 1}
    dock = load_dock_scores()

    if dock["count"] == 0:
        # Fallback: diverse antibiotic_substrate / other picks without scores.
        fallback = [
            c["compound_id"]
            for c in compounds
            if c["compound_id"] not in tier1_ids and not c.get("exclude")
        ][:top_n]
        state = _load_selection_state()
        state["reverse"]["dock_rank"] = {
            "ran_at": _utc_now(),
            "status": "fallback_no_scores",
            "tier3_candidates": fallback,
        }
        path = _save_selection_state(state)
        return {
            "status": "fallback",
            "selection_state": path,
            "message": "No GNINA scores in dossiers; returning first non-Tier-1 IDs.",
            "tier3_candidates": fallback,
        }

    ranked = [s for s in dock["scores"] if s["compound_id"] not in tier1_ids][:top_n]
    state = _load_selection_state()
    state["reverse"]["dock_rank"] = {"ran_at": _utc_now(), "status": "ok", "tier3_candidates": ranked}
    path = _save_selection_state(state)
    return {"status": "ok", "selection_state": path, "tier3_candidates": ranked}


def reverse_literature_check(
    compound_ids: list[str] | None = None,
    tiers: list[int] | None = None,
    all_library: bool = False,
    sources: list[str] | None = None,
    limit_per_compound: int = MAX_REVERSE_QUERY_LIMIT,
    extract_activity: bool = True,
    write_refs: bool = True,
    save_raw: bool = True,
    skip_curated: bool = True,
    use_cache: bool = True,
    search_version: int = REVERSE_SEARCH_VERSION,
    max_compounds_per_run: int | None = None,
    max_map_per_run: int | None = None,
) -> dict[str, Any]:
    """Literature search + activity extraction per library candidate (Phase B reverse R3).

    Searches each compound across open repositories by default (europe_pmc, pubmed, chembl,
    semantic_scholar, openalex). Repository hits are parsed directly; Paperclip sources still
    use map for Ki/IC50 extraction when included in sources.
    Reuses cached search/map results when use_cache=True and search_version matches prior runs.

    Writes structured evidence to data/compound_literature/refs/{id}.json when write_refs=True.
    Skips already-curated refs (e.g. T19860 gold) when skip_curated=True.
    Logs elapsed_ms, result_id, cache hits, and caps under state.reverse.literature_checks.
    """
    limit_per_compound = max(1, min(limit_per_compound, MAX_REVERSE_QUERY_LIMIT))
    source_list = list(sources or DEFAULT_REVERSE_SOURCES)
    compounds = load_compounds()
    targets = _select_literature_targets(
        compounds, compound_ids, tiers, all_library=all_library
    )

    compound_cap = max_compounds_per_run
    if compound_cap is None and not all_library and not compound_ids:
        compound_cap = MAX_REVERSE_LITERATURE_COMPOUNDS
    map_cap = max_map_per_run
    if map_cap is None and not all_library and not compound_ids:
        map_cap = MAX_REVERSE_MAP_PER_RUN

    truncated_ids: list[str] = []
    if compound_cap is not None and len(targets) > compound_cap:
        truncated_ids = [c["compound_id"] for c in targets[compound_cap:]]
        targets = targets[:compound_cap]

    cache = _load_literature_search_cache()
    results: list[dict[str, Any]] = []
    refs_written: list[str] = []
    refs_skipped: list[str] = []
    map_count = 0
    search_cache_hits = 0
    map_cache_hits = 0

    for compound in targets:
        compound_id = str(compound["compound_id"])
        name = str(compound.get("name") or compound_id)
        scaffold_class = _scaffold_class_for_compound(compound)
        query = _build_reverse_query(name, scaffold_class)
        map_question = _build_map_question(name, scaffold_class)

        row: dict[str, Any] = {
            "compound_id": compound_id,
            "name": name,
            "scaffold_class": scaffold_class,
            "query": query,
            "sources": source_list,
            "searches": [],
        }

        parsed_entries: list[dict[str, Any]] = []

        for source in source_list:
            search = _run_reverse_search(
                query,
                source=source,
                limit=limit_per_compound,
                save_raw=save_raw,
                compound_id=compound_id,
                cache=cache,
                use_cache=use_cache,
                search_version=search_version,
            )
            if search.get("cache_hit"):
                search_cache_hits += 1
            row["searches"].append(search)

            if not extract_activity or search.get("status") != "ok" or not search.get("result_id"):
                continue

            result_id = str(search["result_id"])
            if source in REPOSITORY_SOURCES or result_id.startswith("repo_"):
                entry = _parse_activity_entry(
                    search.get("output") or "",
                    compound_name=name,
                    search_id=result_id,
                    map_id=None,
                )
                entry["source"] = "repository"
                entry["paperclip_source"] = source
                parsed_entries.append(entry)
                continue

            if map_cap is not None and map_count >= map_cap:
                row.setdefault("maps_skipped", []).append(f"{source}: map cap reached")
                continue

            map_result = _run_reverse_map(
                map_question,
                str(search["result_id"]),
                cache=cache,
                use_cache=use_cache,
                search_version=search_version,
            )
            if map_result.get("cache_hit"):
                map_cache_hits += 1
            map_count += 1
            row.setdefault("maps", []).append({"source": source, **map_result})

            if map_result.get("status") == "ok":
                entry = _parse_activity_entry(
                    map_result.get("output") or "",
                    compound_name=name,
                    search_id=search.get("result_id"),
                    map_id=map_result.get("result_id"),
                )
                entry["paperclip_source"] = source
                parsed_entries.append(entry)

        if not parsed_entries:
            ok_searches = [s for s in row["searches"] if s.get("status") == "ok"]
            if ok_searches:
                parsed_entries.append(
                    {
                        "source": "paperclip",
                        "target": "TEM-1",
                        "assay": "nitrocefin",
                        "paperclip_search_id": ok_searches[0].get("result_id"),
                        "paperclip_source": ok_searches[0].get("paperclip_source", "europe_pmc"),
                        "note": f"Search-only reverse check for {name}; no map output or no activity extracted.",
                    }
                )

        best = _pick_best_entry(parsed_entries)
        if best:
            screen_rec = _recommend_screen_conc_uM(best, compound)
            row["screen_recommendation"] = {
                "screen_conc_uM": screen_rec["screen_conc_uM"],
                "screen_conc_source": screen_rec["screen_conc_source"],
                "screen_rationale": screen_rec["screen_rationale"],
            }

        if write_refs and parsed_entries:
            ref_outcome = _merge_reverse_ref(compound, parsed_entries, skip_curated=skip_curated)
            row["ref"] = ref_outcome
            if ref_outcome["status"] == "written":
                refs_written.append(compound_id)
                if best:
                    _patch_literature_summary_prior(compound, best, ref_outcome["ref_path"])
            elif ref_outcome["status"] == "skipped_curated":
                refs_skipped.append(compound_id)

        results.append(row)

    _save_literature_search_cache(cache)

    state = _load_selection_state()
    state.setdefault("reverse", {})
    state["reverse"]["literature_checks"] = {
        "ran_at": _utc_now(),
        "search_version": search_version,
        "caps": {
            "max_compounds": compound_cap,
            "query_limit": MAX_REVERSE_QUERY_LIMIT,
            "max_map_per_run": map_cap,
            "sources": source_list,
        },
        "targets_requested": len(targets) + len(truncated_ids),
        "search_count": sum(len(r.get("searches", [])) for r in results),
        "map_count": map_count,
        "search_cache_hits": search_cache_hits,
        "map_cache_hits": map_cache_hits,
        "truncated_compound_ids": truncated_ids,
        "all_library": all_library,
        "results": results,
        "refs_written": refs_written,
        "refs_skipped_curated": refs_skipped,
        "cache_path": str(LITERATURE_SEARCH_CACHE_JSON),
    }
    path = _save_selection_state(state)
    return {
        "status": "ok",
        "selection_state": path,
        "checked": len(results),
        "map_count": map_count,
        "search_cache_hits": search_cache_hits,
        "map_cache_hits": map_cache_hits,
        "refs_written": refs_written,
        "refs_skipped_curated": refs_skipped,
        "truncated_compound_ids": truncated_ids,
        "cache_path": str(LITERATURE_SEARCH_CACHE_JSON),
        "results": results,
    }


def _chembl_activity_to_entry(activity: dict[str, Any], compound_name: str) -> dict[str, Any]:
    stype = (activity.get("standard_type") or "").upper()
    sval = activity.get("standard_value")
    sunit = (activity.get("standard_units") or "").lower()
    if sval is None:
        return {}
    try:
        val = float(sval)
    except (TypeError, ValueError):
        return {}
    if sunit in ("nm", "nanom", "nmol/l"):
        val_uM = val / 1000.0
    elif sunit in ("um", "µm", "microm", "umol/l"):
        val_uM = val
    elif "ug.ml" in sunit or "ug/ml" in sunit or sunit in ("ug ml-1", "ug ml-1"):
        # ChEMBL occasionally reports ug/mL; approximate as ug/mL ~ mg/L, not ideal — skip weak units
        return {}
    else:
        val_uM = val

    entry: dict[str, Any] = {
        "source": "chembl",
        "target": activity.get("target_pref_name") or "TEM-1",
        "assay": "nitrocefin",
        "note": (
            f"ChEMBL {stype}={sval} {sunit} vs {activity.get('target_pref_name')}; "
            f"assay: {(activity.get('assay_description') or '')[:200]}"
        ),
    }
    if stype == "KI":
        entry["ki_uM"] = val_uM
    elif stype in ("IC50", "IC90"):
        entry["ic50_uM"] = val_uM
    elif stype == "KD":
        entry["ki_uM"] = val_uM
    else:
        entry["ic50_uM"] = val_uM
    return entry


GOLD_CURATED_COMPOUND_IDS = frozenset({"T19860"})


def enrich_from_chembl_activities(
    compound_ids: list[str] | None = None,
    *,
    skip_curated: bool = False,
) -> dict[str, Any]:
    """Supplement refs with structured ChEMBL Ki/IC50 (concentration rule 2)."""
    from agent.tools.literature import search_chembl_activities

    compounds = load_compounds()
    if compound_ids:
        id_set = set(compound_ids)
        targets = [c for c in compounds if c["compound_id"] in id_set]
    else:
        targets = [c for c in compounds if not c.get("exclude")]

    enriched: list[dict[str, Any]] = []
    for compound in targets:
        compound_id = str(compound["compound_id"])
        name = str(compound.get("name") or compound_id)
        chembl = search_chembl_activities(name, target_query="TEM-1")
        activities = chembl.get("activities") or []
        if not activities:
            enriched.append({"compound_id": compound_id, "status": "no_activities"})
            continue

        entries = [_chembl_activity_to_entry(a, name) for a in activities]
        entries = [e for e in entries if e]
        if not entries:
            enriched.append({"compound_id": compound_id, "status": "no_parsed_activities"})
            continue

        ref_outcome = _merge_reverse_ref(
            compound,
            entries,
            skip_curated=skip_curated or compound_id in GOLD_CURATED_COMPOUND_IDS,
        )
        best = _pick_best_entry(entries)
        if best and ref_outcome.get("status") == "written":
            _patch_literature_summary_prior(compound, best, ref_outcome["ref_path"])
        enriched.append(
            {
                "compound_id": compound_id,
                "status": ref_outcome.get("status"),
                "activities": len(activities),
                "ki_uM": best.get("ki_uM") if best else None,
                "ic50_uM": best.get("ic50_uM") if best else None,
            }
        )

    return {"status": "ok", "enriched": enriched}
