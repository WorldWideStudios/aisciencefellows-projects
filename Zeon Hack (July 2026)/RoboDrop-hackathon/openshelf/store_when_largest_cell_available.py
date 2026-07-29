#!/usr/bin/env python3
"""Store an input-tray item once a largest-size OpenShelf cell is available.

The script:
1. Authenticates with OpenShelf.
2. Polls the storage grid.
3. Waits until at least one globally largest-size cell is empty.
4. Forces that cell as the destination through ``item.location``.
5. Submits exactly one ``store_item`` command.
6. Polls inventory until OpenShelf records the item at that exact location.

No code runs merely by importing this module. CLI use additionally requires
the explicit ``--execute`` flag.
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


DEFAULT_BASE_URL = "http://192.168.1.16:8000"
SIDES = ("left_module", "right_module")


def configure_logging(log_path: Path) -> logging.Logger:
    """Log to both a file and stdout without recording credentials or tokens."""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("openshelf_store")
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


def location_key(location: dict[str, Any]) -> tuple[Any, Any, Any]:
    """Return the stable identity of an OpenShelf storage location."""
    return (
        location.get("side"),
        location.get("shelf_idx"),
        location.get("cell_idx"),
    )


def flatten_cells(grid: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the nested grid response into one record per storage cell."""
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


def largest_empty_cells(
    grid: dict[str, Any],
) -> tuple[float, list[dict[str, Any]], list[dict[str, Any]]]:
    """Return largest volume, all largest cells, and empty largest cells."""
    cells = flatten_cells(grid)
    if not cells:
        raise RuntimeError("OpenShelf returned no usable storage cells")

    largest_volume = max(cell["volume_mm3"] for cell in cells)
    largest = [
        cell for cell in cells if cell["volume_mm3"] == largest_volume
    ]
    empty = [
        cell
        for cell in largest
        if cell["status"] == "available" and cell["item"] is None
    ]
    return largest_volume, largest, empty


class OpenShelfClient:
    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        pin: str,
        logger: logging.Logger,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.pin = pin
        self.logger = logger
        self.session = requests.Session()

    def login(self) -> None:
        self.logger.info("POST /api/auth/login/json (credentials redacted)")
        response = self.session.post(
            f"{self.base_url}/api/auth/login/json",
            json={"email": self.email, "pin": self.pin},
            timeout=5,
        )
        self.logger.info("Login HTTP status: %s", response.status_code)
        response.raise_for_status()

        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("Login response did not contain access_token")

        self.session.headers.update(
            {"Authorization": f"Bearer {token}"}
        )
        self.logger.info("Authentication succeeded (token redacted)")

    def get(self, path: str, *, timeout: float = 5) -> requests.Response:
        response = self.session.get(
            f"{self.base_url}{path}",
            timeout=timeout,
        )
        if response.status_code == 401:
            self.logger.info("Token expired; authenticating again")
            self.login()
            response = self.session.get(
                f"{self.base_url}{path}",
                timeout=timeout,
            )
        return response

    def get_health(self) -> dict[str, Any]:
        response = self.get("/api/health")
        self.logger.info("GET /api/health -> HTTP %s", response.status_code)
        response.raise_for_status()
        return response.json()

    def get_grid(self) -> dict[str, Any]:
        response = self.get("/api/storage/grid")
        self.logger.info("GET /api/storage/grid -> HTTP %s", response.status_code)
        response.raise_for_status()
        return response.json()

    def get_item(self, upca: str) -> dict[str, Any] | None:
        response = self.get(f"/api/storage/items/{upca}")
        self.logger.info(
            "GET /api/storage/items/%s -> HTTP %s",
            upca,
            response.status_code,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def submit_store_once(
        self,
        item: dict[str, Any],
        destination: dict[str, Any],
    ) -> dict[str, Any]:
        """Submit exactly one physical store command.

        A transport exception after the request begins is deliberately not
        retried: the cabinet may have accepted the command even if the client
        did not receive the response.
        """
        command_item = json.loads(json.dumps(item))
        command_item["location"] = {
            "side": destination["side"],
            "shelf_idx": destination["shelf_idx"],
            "cell_idx": destination["cell_idx"],
        }
        command = {"command": "store_item", "item": command_item}
        self.logger.info(
            "POST /api/robot/commands payload=%s",
            json.dumps(command, sort_keys=True),
        )

        response = self.session.post(
            f"{self.base_url}/api/robot/commands",
            json=command,
            timeout=5,
        )

        if response.status_code == 401:
            # A 401 response means the command was rejected before execution,
            # so re-authentication followed by one submission is safe.
            self.logger.info("Store request rejected with 401; authenticating again")
            self.login()
            response = self.session.post(
                f"{self.base_url}/api/robot/commands",
                json=command,
                timeout=5,
            )

        self.logger.info(
            "POST /api/robot/commands -> HTTP %s body=%s",
            response.status_code,
            response.text[:500],
        )
        response.raise_for_status()
        return response.json()


def wait_for_largest_empty_cell(
    client: OpenShelfClient,
    *,
    poll_seconds: float,
    timeout_seconds: float | None,
) -> dict[str, Any]:
    """Poll until at least one cell of the globally largest size is empty."""
    started = time.monotonic()
    query_number = 0

    while True:
        query_number += 1
        grid = client.get_grid()
        cells = flatten_cells(grid)
        largest_volume, largest, empty = largest_empty_cells(grid)

        client.logger.info(
            "Grid query %d: cells=%d largest_volume_mm3=%.3f "
            "largest_cells=%d empty_largest_cells=%d",
            query_number,
            len(cells),
            largest_volume,
            len(largest),
            len(empty),
        )
        for cell in cells:
            client.logger.info(
                "GRID_CELL %s",
                json.dumps(cell, sort_keys=True, default=str),
            )

        if empty:
            selected = empty[0]
            client.logger.info(
                "Largest empty destination selected: %s",
                json.dumps(selected, sort_keys=True, default=str),
            )
            return selected

        if (
            timeout_seconds is not None
            and time.monotonic() - started >= timeout_seconds
        ):
            raise TimeoutError(
                "No empty cell of the largest size became available"
            )

        client.logger.info(
            "All largest-size cells are occupied; sleeping %.1f seconds",
            poll_seconds,
        )
        time.sleep(poll_seconds)


def wait_for_expected_item_location(
    client: OpenShelfClient,
    *,
    upca: str,
    destination: dict[str, Any],
    poll_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Wait until inventory records the item at the forced destination."""
    deadline = time.monotonic() + timeout_seconds
    expected_key = location_key(destination)

    while time.monotonic() < deadline:
        item = client.get_item(upca)
        if item is not None:
            locations = item.get("locations") or []
            client.logger.info(
                "Inventory locations for %s: %s",
                upca,
                json.dumps(locations, sort_keys=True, default=str),
            )
            for location in locations:
                if location_key(location) == expected_key:
                    return location

        time.sleep(poll_seconds)

    raise TimeoutError(
        "OpenShelf accepted the store command, but UPCA "
        f"{upca!r} did not appear at the forced destination "
        f"{expected_key!r} within {timeout_seconds:.1f} seconds. "
        "Do not automatically resubmit; inspect the cabinet first."
    )


def store_when_largest_cell_available(
    item: dict[str, Any],
    *,
    base_url: str,
    email: str,
    pin: str,
    log_path: Path,
    grid_poll_seconds: float = 5.0,
    grid_wait_timeout_seconds: float | None = None,
    completion_poll_seconds: float = 2.0,
    completion_timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Run the complete query, store, and completion-verification sequence."""
    upca = str(item.get("upca") or "").strip()
    if not upca:
        raise ValueError("item must contain a non-empty 'upca'")

    logger = configure_logging(log_path)
    logger.info("STORE RUN START")
    logger.info("Base URL: %s", base_url)
    logger.info("Item payload: %s", json.dumps(item, sort_keys=True))

    client = OpenShelfClient(
        base_url=base_url,
        email=email,
        pin=pin,
        logger=logger,
    )
    client.login()

    health = client.get_health()
    logger.info("Health response: %s", json.dumps(health, sort_keys=True))
    if health.get("status") != "ok" or health.get("robot_status") != "ok":
        raise RuntimeError(f"OpenShelf is not ready: {health}")

    destination = wait_for_largest_empty_cell(
        client,
        poll_seconds=grid_poll_seconds,
        timeout_seconds=grid_wait_timeout_seconds,
    )

    existing_item = client.get_item(upca)
    locations_before = {
        location_key(location)
        for location in (
            existing_item.get("locations", []) if existing_item else []
        )
    }
    logger.info(
        "Locations before store: %s",
        json.dumps(sorted(locations_before), default=str),
    )
    destination_key = location_key(destination)
    if destination_key in locations_before:
        raise RuntimeError(
            "The selected grid cell is empty, but the item already lists that "
            f"location: {destination_key!r}. Refusing an ambiguous store."
        )

    accepted_response = client.submit_store_once(item, destination)
    logger.info(
        "Store command accepted; waiting for forced destination %s",
        destination_key,
    )

    actual_location = wait_for_expected_item_location(
        client,
        upca=upca,
        destination=destination,
        poll_seconds=completion_poll_seconds,
        timeout_seconds=completion_timeout_seconds,
    )

    logger.info(
        "Store confirmed at forced destination: %s",
        json.dumps(actual_location, sort_keys=True, default=str),
    )
    logger.info("STORE RUN END")

    return {
        "success": True,
        "upca": upca,
        "forced_destination": destination,
        "confirmed_location": actual_location,
        "command_response": accepted_response,
        "log_path": str(log_path),
    }


def build_item_from_args(args: argparse.Namespace) -> dict[str, Any]:
    item: dict[str, Any] = {
        "upca": args.upca,
        "data": {"name": args.name},
    }

    dimension_values = (args.width, args.length, args.height)
    supplied_dimensions = [value is not None for value in dimension_values]
    if any(supplied_dimensions) and not all(supplied_dimensions):
        raise ValueError(
            "--width, --length, and --height must be provided together"
        )
    if all(supplied_dimensions):
        item["dimensions"] = {
            "width": args.width,
            "length": args.length,
            "height": args.height,
        }
    if args.weight is not None:
        item["weight"] = args.weight

    return item


def main() -> int:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(
        description=(
            "Wait for a largest-size empty OpenShelf cell and then store "
            "the supplied item from the input tray."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--upca", required=True)
    parser.add_argument("--name", default="plate")
    parser.add_argument("--width", type=float)
    parser.add_argument("--length", type=float)
    parser.add_argument("--height", type=float)
    parser.add_argument("--weight", type=float)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENSHELF_BASE_URL", DEFAULT_BASE_URL),
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("OPENSHELF_EMAIL"),
    )
    parser.add_argument(
        "--pin",
        default=os.environ.get("OPENSHELF_PIN"),
    )
    parser.add_argument("--grid-poll-seconds", type=float, default=5.0)
    parser.add_argument("--grid-timeout-seconds", type=float)
    parser.add_argument("--completion-poll-seconds", type=float, default=2.0)
    parser.add_argument("--completion-timeout-seconds", type=float, default=120.0)
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("logs") / f"openshelf_store_{timestamp}.log",
    )
    args = parser.parse_args()

    if not args.execute:
        parser.error(
            "Refusing to send a physical store command without --execute"
        )
    if not args.email:
        parser.error(
            "Provide --email or set OPENSHELF_EMAIL"
        )
    if not args.pin:
        parser.error(
            "Provide --pin or set OPENSHELF_PIN"
        )
    if args.grid_poll_seconds <= 0:
        parser.error("--grid-poll-seconds must be positive")
    if args.completion_poll_seconds <= 0:
        parser.error("--completion-poll-seconds must be positive")
    if args.completion_timeout_seconds <= 0:
        parser.error("--completion-timeout-seconds must be positive")

    try:
        item = build_item_from_args(args)
        result = store_when_largest_cell_available(
            item,
            base_url=args.base_url,
            email=args.email,
            pin=args.pin,
            log_path=args.log,
            grid_poll_seconds=args.grid_poll_seconds,
            grid_wait_timeout_seconds=args.grid_timeout_seconds,
            completion_poll_seconds=args.completion_poll_seconds,
            completion_timeout_seconds=args.completion_timeout_seconds,
        )
    except Exception:
        logging.getLogger("openshelf_store").exception("STORE RUN FAILED")
        return 1

    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
