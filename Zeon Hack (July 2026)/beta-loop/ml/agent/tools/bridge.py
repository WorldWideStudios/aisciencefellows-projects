"""Bridge selection tools — Tanimoto similarity and library clustering."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from agent.paths import (
    LOCAL_SIMILARITY,
    SELECTION_STATE_JSON,
    SIMILARITY_NEIGHBORS_JSON,
)
from agent.tools.chem import RDKIT_AVAILABLE, morgan_fp, parse_smiles, rdkit_status, tanimoto_smiles
from agent.tools.compounds import load_compounds
from agent.tools.forward import load_reference_inhibitors

try:
    from rdkit import DataStructs
    from rdkit.ML.Cluster import Butina

    BUTINA_AVAILABLE = RDKIT_AVAILABLE
except (ImportError, AttributeError, ModuleNotFoundError):
    BUTINA_AVAILABLE = False


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


def find_tanimoto_neighbors(
    threshold: float = 0.70,
    reference_source: str = "reference_inhibitors",
) -> dict[str, Any]:
    """Find library analogs of literature/reference inhibitors (Phase B bridge B1–B2).

    Args:
        threshold: Minimum Tanimoto to report a neighbor (default 0.70).
        reference_source: reference_inhibitors | forward_literature_only
    """
    if not RDKIT_AVAILABLE:
        return {
            "status": "error",
            "message": "RDKit required for Tanimoto similarity. pip install rdkit",
            "rdkit": rdkit_status(),
        }

    compounds = [c for c in load_compounds() if not c.get("exclude")]
    refs_payload = load_reference_inhibitors()
    references = refs_payload["inhibitors"]

    if reference_source == "forward_literature_only":
        state = _load_selection_state()
        literature_only = state.get("forward", {}).get("library_matches", {}).get("literature_only", [])
        references = [item["reference"] for item in literature_only]

    neighbors: list[dict[str, Any]] = []
    for ref in references:
        ref_name = ref.get("name", "")
        ref_smiles = ref.get("smiles") or ""
        if not ref_smiles:
            # Resolve SMILES from library name match if reference lacks structure.
            for compound in compounds:
                if ref_name.lower() in (compound.get("name") or "").lower():
                    ref_smiles = compound.get("smiles") or ""
                    break
        if not ref_smiles:
            continue

        hits = []
        for compound in compounds:
            score = tanimoto_smiles(ref_smiles, compound.get("smiles") or "")
            if score is not None and score >= threshold:
                label = "probable_analog" if score >= 0.85 else "scaffold_neighbor"
                hits.append(
                    {
                        "compound_id": compound["compound_id"],
                        "name": compound.get("name"),
                        "tanimoto": round(score, 3),
                        "label": label,
                    }
                )
        hits.sort(key=lambda x: x["tanimoto"], reverse=True)
        neighbors.append({"reference_name": ref_name, "reference_smiles": ref_smiles, "neighbors": hits[:10]})

    SIMILARITY_NEIGHBORS_JSON.parent.mkdir(parents=True, exist_ok=True)
    SIMILARITY_NEIGHBORS_JSON.write_text(json.dumps({"threshold": threshold, "neighbors": neighbors}, indent=2) + "\n")
    LOCAL_SIMILARITY.mkdir(parents=True, exist_ok=True)

    state = _load_selection_state()
    groups_with_hits = sum(1 for n in neighbors if n["neighbors"])
    state["bridge"]["tanimoto_neighbors"] = {
        "ran_at": _utc_now(),
        "threshold": threshold,
        "reference_count": len(references),
        "groups_with_hits": groups_with_hits,
        "output": str(SIMILARITY_NEIGHBORS_JSON),
    }
    path = _save_selection_state(state)

    return {
        "status": "ok",
        "selection_state": path,
        "neighbors_file": str(SIMILARITY_NEIGHBORS_JSON),
        "reference_count": len(references),
        "groups_with_hits": groups_with_hits,
    }


def cluster_library(tanimoto_threshold: float = 0.7, reps_per_cluster: int = 1) -> dict[str, Any]:
    """Cluster library compounds by Morgan FP; pick diverse representatives (Phase B bridge B3)."""
    if not BUTINA_AVAILABLE:
        return {
            "status": "fallback",
            "message": "RDKit clustering unavailable — using scaffold-class diversity from reverse pass.",
            "rdkit": rdkit_status(),
        }

    compounds = [c for c in load_compounds() if not c.get("exclude") and c.get("smiles")]
    fps = []
    valid = []
    for compound in compounds:
        mol = parse_smiles(compound["smiles"])
        fp = morgan_fp(mol)
        if fp is not None:
            fps.append(fp)
            valid.append(compound)

    if not fps:
        return {"status": "error", "message": "No valid SMILES for clustering."}

    dists = []
    n = len(fps)
    for i in range(1, n):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
        dists.extend([1 - x for x in sims])

    clusters = Butina.ClusterData(dists, n, 1 - tanimoto_threshold, isDistData=True)
    representatives: list[dict[str, Any]] = []
    for cluster in clusters:
        for idx in cluster[:reps_per_cluster]:
            representatives.append(
                {
                    "compound_id": valid[idx]["compound_id"],
                    "name": valid[idx].get("name"),
                    "cluster_size": len(cluster),
                }
            )

    LOCAL_SIMILARITY.mkdir(parents=True, exist_ok=True)
    cluster_path = LOCAL_SIMILARITY / "cluster_reps.json"
    cluster_path.write_text(json.dumps({"representatives": representatives}, indent=2) + "\n")

    state = _load_selection_state()
    state["bridge"]["clustering"] = {
        "ran_at": _utc_now(),
        "tanimoto_threshold": tanimoto_threshold,
        "cluster_count": len(clusters),
        "representatives": representatives,
        "output_local": str(cluster_path),
    }
    path = _save_selection_state(state)

    return {
        "status": "ok",
        "selection_state": path,
        "cluster_count": len(clusters),
        "representative_count": len(representatives),
        "representatives": representatives[:20],
        "output_local": str(cluster_path),
    }


def assign_tier2_analogs(max_analogs: int = 4, min_tanimoto: float = 0.70) -> dict[str, Any]:
    """Promote top Tanimoto neighbors to Tier 2 analog candidates (Phase B bridge)."""
    if not SIMILARITY_NEIGHBORS_JSON.exists():
        seed = find_tanimoto_neighbors(threshold=min_tanimoto)
        if seed.get("status") != "ok":
            return seed

    payload = json.loads(SIMILARITY_NEIGHBORS_JSON.read_text())
    tier1_ids = {"T19860", "T14979", "T6685", "T1631", "T1262", "T14081", "T13038"}
    picks: list[dict[str, Any]] = []
    seen: set[str] = set()

    for group in payload.get("neighbors", []):
        for neighbor in group.get("neighbors", []):
            cid = neighbor["compound_id"]
            if cid in tier1_ids or cid in seen:
                continue
            seen.add(cid)
            picks.append(
                {
                    "compound_id": cid,
                    "name": neighbor.get("name"),
                    "tanimoto": neighbor.get("tanimoto"),
                    "reference_name": group.get("reference_name"),
                    "tier": 2,
                    "bucket": "inhibitor_analog",
                }
            )
            if len(picks) >= max_analogs:
                break
        if len(picks) >= max_analogs:
            break

    state = _load_selection_state()
    state["bridge"]["tier2_analogs"] = {"ran_at": _utc_now(), "candidates": picks}
    path = _save_selection_state(state)

    return {"status": "ok", "selection_state": path, "tier2_candidates": picks}
