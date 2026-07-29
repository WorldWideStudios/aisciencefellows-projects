"""Plate map read/write tools."""

from __future__ import annotations

import json
from typing import Any

from agent.paths import DATA_DIR
from analysis.plates import design_dose_response_plate, write_plate_map


def load_plate_map(round_number: int = 1) -> dict[str, Any]:
    """Load plate_map_r{N}.json."""
    path = DATA_DIR / f"plate_map_r{round_number}.json"
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    return json.loads(path.read_text())


def design_next_plate(
    round_number: int = 2,
    max_compounds: int = 3,
    agent_rationale: str = "",
) -> dict[str, Any]:
    """Design the next screening plate from the prior round summary.

    For Round 2, builds an 8-point dose-response layout for top R1 hits.
    Writes data/plate_map_r2.json.

    Args:
        round_number: Target round to design (typically 2).
        max_compounds: Number of R1 hits to carry into dose-response.
        agent_rationale: Short explanation of design choices for the demo.
    """
    if round_number != 2:
        return {
            "status": "unsupported",
            "message": "Only Round 2 dose-response design is implemented.",
        }

    summary_path = DATA_DIR / "round_summary_r1.json"
    if not summary_path.exists():
        return {
            "status": "missing",
            "message": "Run analyze_kinetics(round_number=1) first.",
            "expected_path": str(summary_path),
        }

    summary = json.loads(summary_path.read_text())
    hits = summary.get("hits", [])
    if not hits:
        return {
            "status": "no_hits",
            "message": "No R1 hits ≥50% inhibition; cannot design dose-response plate.",
            "round_summary": summary,
        }

    plate = design_dose_response_plate(hits, round_number=2, max_compounds=max_compounds)
    out_path = DATA_DIR / "plate_map_r2.json"
    write_plate_map(plate, out_path)

    round_summary = dict(summary)
    round_summary["agent_rationale"] = agent_rationale or (
        f"Designed dose-response on top {min(len(hits), max_compounds)} R1 hits."
    )
    round_summary["next_plate_path"] = str(out_path)
    summary_path.write_text(json.dumps(round_summary, indent=2) + "\n")

    return {
        "status": "ok",
        "plate_map_path": str(out_path),
        "hit_count": len(hits),
        "compounds_in_dr": min(len(hits), max_compounds),
        "plate_preview": {
            "assay_type": plate["assay_type"],
            "well_count": len(plate["wells"]),
        },
        "agent_rationale": round_summary["agent_rationale"],
    }
