#!/usr/bin/env python3
"""Read-only OpenShelf largest-cell query.

This script authenticates and performs GET requests only after login. It never
submits a robot command or changes cabinet, calibration, or inventory state.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


SIDES = ("left_module", "right_module")


def configure_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("openshelf_dry_run")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def flatten_cells(grid: dict[str, Any]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for side in SIDES:
        for shelf in grid.get(side, []):
            shelf_idx = shelf.get("shelf_idx")
            for cell in shelf.get("cells", []):
                dimensions = cell.get("dimensions") or {}
                try:
                    width = float(dimensions["width"])
                    length = float(dimensions["length"])
                    height = float(dimensions["height"])
                except (KeyError, TypeError, ValueError):
                    continue

                cells.append(
                    {
                        "side": side,
                        "shelf_idx": shelf_idx,
                        "cell_idx": cell.get("cell_idx"),
                        "status": cell.get("status"),
                        "item": cell.get("item"),
                        "dimensions": {
                            "width": width,
                            "length": length,
                            "height": height,
                        },
                        "volume_mm3": width * length * height,
                        "calibration_point": cell.get("calibration_point"),
                        "is_manual": cell.get("is_manual"),
                    }
                )
    return cells


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENSHELF_BASE_URL", "http://192.168.1.16:8000"),
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("OPENSHELF_EMAIL", "admin@opshelf.com"),
    )
    parser.add_argument(
        "--pin",
        default=os.environ.get("OPENSHELF_PIN", "1234"),
    )
    parser.add_argument(
        "--log",
        type=Path,
        required=True,
    )
    args = parser.parse_args()
    logger = configure_logging(args.log)

    logger.info("DRY RUN START")
    logger.info("Safety mode: login POST and read-only GET requests only")
    logger.info("No /api/robot/commands request will be sent")
    logger.info("Base URL: %s", args.base_url)

    session = requests.Session()

    logger.info("POST /api/auth/login/json (credentials redacted)")
    login = session.post(
        f"{args.base_url}/api/auth/login/json",
        json={"email": args.email, "pin": args.pin},
        timeout=5,
    )
    logger.info("Login HTTP status: %s", login.status_code)
    login.raise_for_status()
    token = login.json().get("access_token")
    if not token:
        raise RuntimeError("Login response did not contain access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    logger.info("Authentication succeeded (token redacted)")

    logger.info("GET /api/health")
    health = session.get(f"{args.base_url}/api/health", timeout=5)
    logger.info("Health HTTP status: %s", health.status_code)
    health.raise_for_status()
    logger.info("Health response: %s", json.dumps(health.json(), sort_keys=True))

    logger.info("GET /api/storage/grid")
    grid_response = session.get(f"{args.base_url}/api/storage/grid", timeout=5)
    logger.info("Grid HTTP status: %s", grid_response.status_code)
    grid_response.raise_for_status()
    grid = grid_response.json()

    cells = flatten_cells(grid)
    logger.info("Usable cells returned: %d", len(cells))
    for cell in cells:
        logger.info("CELL %s", json.dumps(cell, sort_keys=True, default=str))

    if not cells:
        logger.error("No usable cells were returned")
        return 2

    largest_volume = max(cell["volume_mm3"] for cell in cells)
    largest_cells = [
        cell for cell in cells if cell["volume_mm3"] == largest_volume
    ]
    empty_largest_cells = [
        cell
        for cell in largest_cells
        if cell["status"] == "available" and cell["item"] is None
    ]

    logger.info("Largest cell volume: %.3f mm^3", largest_volume)
    logger.info("Cells having the largest volume: %d", len(largest_cells))
    logger.info("Empty cells having the largest volume: %d", len(empty_largest_cells))
    for cell in largest_cells:
        logger.info("LARGEST_CELL %s", json.dumps(cell, sort_keys=True, default=str))

    if empty_largest_cells:
        selected = empty_largest_cells[0]
        logger.info(
            "DRY RUN DECISION: an empty largest-size cell is available: %s",
            json.dumps(selected, sort_keys=True, default=str),
        )
        logger.info(
            "DRY RUN STOP: the real program would submit store_item now; "
            "no command was submitted"
        )
    else:
        logger.info(
            "DRY RUN DECISION: all largest-size cells are occupied; "
            "the real program would sleep and query again"
        )

    logger.info("DRY RUN END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
