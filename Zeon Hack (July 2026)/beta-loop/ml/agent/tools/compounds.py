"""Compound library tools."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from agent.paths import COMPOUNDS_CSV, DATA_DIR


def load_compounds() -> list[dict[str, Any]]:
    """Load the full TargetMol library from data/compounds.csv."""
    if not COMPOUNDS_CSV.exists():
        return []
    df = pd.read_csv(COMPOUNDS_CSV)
    df["exclude"] = df["exclude"].astype(str).str.lower().isin(["true", "1", "yes"])
    records = df.to_dict(orient="records")
    return records


def prioritize_compounds(max_compounds: int = 24) -> dict[str, Any]:
    """Return Round 1 compound picks grounded in library tiers and literature.

    For the hackathon, Round 1 is pre-signed-off in data/plate_map_r1.json.
    This tool returns that plate's sample compounds when available, otherwise
    falls back to tier-based selection from compounds.csv.
    """
    plate_path = DATA_DIR / "plate_map_r1.json"
    if plate_path.exists():
        plate = json.loads(plate_path.read_text())
        samples = [
            {
                "well": well,
                "compound_id": spec.get("compound_id"),
                "bucket": spec.get("bucket"),
                "functional_class": spec.get("functional_class"),
            }
            for well, spec in plate.get("wells", {}).items()
            if spec.get("role") == "sample" and spec.get("compound_id")
        ]
        return {
            "status": "ok",
            "source": str(plate_path),
            "count": len(samples),
            "compounds": samples[:max_compounds],
            "note": "Round 1 uses the signed-off plate map; do not replate without pvjthomas sign-off.",
        }

    compounds = load_compounds()
    picks = []
    for tier in (1, 2, 3):
        tier_rows = [
            c
            for c in compounds
            if not c.get("exclude") and str(c.get("tier")) == str(tier)
        ]
        picks.extend(tier_rows)
        if len(picks) >= max_compounds:
            break

    return {
        "status": "ok",
        "source": "compounds.csv",
        "count": min(len(picks), max_compounds),
        "compounds": picks[:max_compounds],
    }
