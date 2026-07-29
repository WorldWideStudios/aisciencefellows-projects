"""Kinetics analysis tool wrappers."""

from __future__ import annotations

import json
from typing import Any

from agent.paths import DATA_DIR
from analysis.kinetics import analyze_kinetics_file


def analyze_kinetics(round_number: int = 1) -> dict[str, Any]:
    """Analyze kinetics CSV for a screening round and write round_summary JSON.

    Reads data/kinetics_r{N}.csv and data/plate_map_r{N}.json, computes
    percent inhibition vs vehicle/no-TEM-1 controls, and writes
    data/round_summary_r{N}.json.

    Args:
        round_number: Screening round (1 or 2).
    """
    kinetics_path = DATA_DIR / f"kinetics_r{round_number}.csv"
    plate_map_path = DATA_DIR / f"plate_map_r{round_number}.json"
    summary_path = DATA_DIR / f"round_summary_r{round_number}.json"

    if not kinetics_path.exists():
        return {
            "status": "missing",
            "message": f"No kinetics file at {kinetics_path}",
            "expected_path": str(kinetics_path),
        }

    summary = analyze_kinetics_file(
        kinetics_path,
        plate_map_json=plate_map_path if plate_map_path.exists() else None,
        round_number=round_number,
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    summary["status"] = "ok"
    summary["summary_path"] = str(summary_path)
    return summary


def load_round_summary(round_number: int = 1) -> dict[str, Any]:
    """Load a saved round summary JSON."""
    path = DATA_DIR / f"round_summary_r{round_number}.json"
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    return json.loads(path.read_text())
