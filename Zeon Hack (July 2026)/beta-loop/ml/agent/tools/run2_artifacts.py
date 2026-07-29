"""Agent tool: generate Run 2 post-run artifacts."""

from __future__ import annotations

from typing import Any

from analysis.run2_artifacts import write_run2_artifacts


def generate_run2_artifacts() -> dict[str, Any]:
    """Generate nitrocefin timing, reader lid-close metadata, plate_map_r2, and run_2_summary.

    Reads the Run 2 robot log, Gen5 PDF, and kinetics CSV under
    ``data/screens/2/post-run/``, promotes v5 plate map, and runs median-scoring analysis.
    """
    paths = write_run2_artifacts()
    return {
        "status": "ok",
        "artifacts": {k: str(v) for k, v in paths.items()},
        "message": "Generated timing JSON, reader lid-close UTC, plate_map_r2.json, run_2_summary.json",
    }
