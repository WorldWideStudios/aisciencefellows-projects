"""MCP server for the baebugs instrument ("every instrument gets an API").
Run: python -m baebugs.mcp_server   (needs `pip install mcp`)
Add to Claude: claude mcp add baebugs -- python -m baebugs.mcp_server
"""
from __future__ import annotations

import json

import cv2

from .measure import classical_measure, consensus, px_per_mm_from_aruco
from .provenance import Provenance, sha256_file
from .sieve import load_yaml, plan_stack
from .sieve_calibrate import measure_aperture
from .twin import LabTwin

prov = Provenance()


def _scale(img, px_per_mm, aruco_mm):
    return px_per_mm or px_per_mm_from_aruco(img, aruco_mm)


def tool_measure(image_path: str, sample_id: str, px_per_mm: float | None = None,
                 aruco_mm: float | None = None, yolo_weights: str | None = None) -> str:
    img = cv2.imread(image_path)
    ppm = _scale(img, px_per_mm, aruco_mm)
    ms = classical_measure(img, ppm)
    if yolo_weights:
        from .measure import YoloMeasurer
        ms = consensus(YoloMeasurer(yolo_weights)(img, ppm), ms, ppm)
    rows = [m.to_dict() for m in ms]
    prov.record("measure", sample_id, {"px_per_mm": ppm, "yolo": yolo_weights},
                {"image": sha256_file(image_path)}, {"n": len(rows)})
    return json.dumps({"px_per_mm": ppm, "measurements": rows})


def tool_plan(widths_mm: list[float], sample_id: str) -> str:
    plan = plan_stack(widths_mm)
    errs = LabTwin().preflight(plan)
    prov.record("plan", sample_id, {}, {"n_widths": len(widths_mm)},
                {"plan": plan.to_dict(), "preflight_errors": errs})
    return json.dumps({"plan": plan.to_dict(), "preflight_errors": errs})


def tool_calibrate_sieve(image_path: str, sieve_id: str, px_per_mm: float,
                         dark_openings: bool = False) -> str:
    r = measure_aperture(cv2.imread(image_path), px_per_mm, dark_openings)
    prov.record("calibrate_sieve", sieve_id, {"px_per_mm": px_per_mm},
                {"image": sha256_file(image_path)}, r or {})
    return json.dumps(r)


def tool_inventory() -> str:
    return json.dumps(load_yaml("sieves.yaml"))


def tool_trace(sample_id: str) -> str:
    return json.dumps({"verified": prov.verify(), "records": prov.trace(sample_id)})


def main():
    from mcp.server.fastmcp import FastMCP
    app = FastMCP("baebugs")
    app.tool(name="measure_sample",
             description="Size every body in a USB-camera image (mm); two-model consensus if YOLO weights given")(tool_measure)
    app.tool(name="plan_sieves",
             description="Sieve stack + water flow for measured widths, with digital-twin preflight")(tool_plan)
    app.tool(name="calibrate_sieve",
             description="Measure a mesh's real aperture from a top-down image")(tool_calibrate_sieve)
    app.tool(name="sieve_inventory", description="Current sieve kit and water state")(tool_inventory)
    app.tool(name="trace_sample",
             description="Hash-chained provenance for one sample, with chain verification")(tool_trace)
    app.run()


if __name__ == "__main__":
    main()
