"""
Labware offsets measured with ``flex calibrate``, kept on this laptop.

They are passed with every run we create, so a plate on a riser is addressed at
its real height. They are deliberately not written to the robot's shared offset
store, which holds other teams' calibrations.
"""

import json
from pathlib import Path
from typing import Optional

import run_store

FILE_NAME = "labware_offsets.json"


def _path() -> Path:
    return run_store.RUNS_DIR / FILE_NAME


def load() -> list[dict]:
    """All saved offsets: ``{"definitionUri", "slot", "vector", "measured"}``."""
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as error:
        raise OSError(f"Could not read {_path()}: {error}") from error


def find(definition_uri: str, slot: str) -> Optional[dict]:
    """The saved offset for one labware definition in one slot, or None."""
    return next((o for o in load() if o["definitionUri"] == definition_uri and o["slot"] == slot), None)


def save_offset(definition_uri: str, slot: str, vector: dict, measured: str = "") -> None:
    """Save (or replace) the offset of ``definition_uri`` in ``slot``."""
    offsets = [o for o in load() if not (o["definitionUri"] == definition_uri and o["slot"] == slot)]
    offsets.append({"definitionUri": definition_uri, "slot": slot, "vector": vector, "measured": measured})
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(offsets, indent=2), encoding="utf-8")
    except OSError as error:
        raise OSError(f"Could not write {path}: {error}") from error


def for_run() -> list[dict]:
    """Saved offsets in the shape the robot's ``POST /runs`` expects."""
    return [
        {
            "definitionUri": o["definitionUri"],
            "locationSequence": [{"kind": "onAddressableArea", "addressableAreaName": o["slot"]}],
            "vector": o["vector"],
        }
        for o in load()
    ]
