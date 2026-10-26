"""
One folder per plate holding its layout, protocol, snapshots and run info.

Shared by the CLI and the web API so a snapshot taken in one shows up in
the other. Folder: ``runs/<slug>/`` next to the package, or ``$RUNS_DIR``.
"""

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Union

from plate_layout import PlateLayout

RUNS_DIR = Path(os.environ.get("RUNS_DIR", Path(__file__).resolve().parent.parent / "runs"))
LAYOUT_FILE = "layout.json"
RUN_INFO_FILE = "run.json"


def slugify(name: str) -> str:
    """Safe folder name for a plate name, e.g. ``"Ferroptosis screen 1"`` → ``"ferroptosis-screen-1"``."""
    ascii_name = unicodedata.normalize("NFKD", name.replace("µ", "u")).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or "untitled"


class RunStore:
    """
    Read and write the files of each plate's run folder.

    Parameters
    ----------
    root : Path, optional
        Folder holding one sub-folder per plate. Defaults to ``RUNS_DIR``.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else RUNS_DIR

    def folder(self, plate: str) -> Path:
        """The plate's folder, created if missing."""
        path = self.root / slugify(plate)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise OSError(f"Could not create {path}: {error}") from error
        return path

    def path(self, plate: str, filename: str) -> Path:
        """
        Path of an existing file in the plate's folder.

        Raises
        ------
        ValueError
            If ``filename`` isn't a plain file name.
        FileNotFoundError
            If the file doesn't exist.
        """
        if not filename or Path(filename).name != filename or filename.startswith("."):
            raise ValueError(f"Invalid file name: {filename!r}")
        path = self.root / slugify(plate) / filename
        if not path.is_file():
            raise FileNotFoundError(f"{slugify(plate)}/{filename} does not exist")
        return path

    def write_file(self, plate: str, filename: str, data: Union[bytes, str]) -> Path:
        """Write ``data`` to ``filename`` in the plate's folder and return its path."""
        if Path(filename).name != filename:
            raise ValueError(f"Invalid file name: {filename!r}")
        path = self.folder(plate) / filename
        try:
            if isinstance(data, bytes):
                path.write_bytes(data)
            else:
                path.write_text(data, encoding="utf-8")
        except OSError as error:
            raise OSError(f"Could not write {path}: {error}") from error
        return path

    def save_layout(self, layout: PlateLayout) -> Path:
        """Save ``layout`` as ``layout.json`` in its plate folder."""
        path = self.folder(layout.name) / LAYOUT_FILE
        layout.save_json(path)
        return path

    def load_layout(self, plate: str) -> PlateLayout:
        """Load a plate's saved layout (raises ``FileNotFoundError`` if none)."""
        return PlateLayout.load_json(self.path(plate, LAYOUT_FILE))

    def list_plates(self) -> list[str]:
        """Slugs of all plates with a saved layout, sorted."""
        if not self.root.is_dir():
            return []
        return sorted(p.name for p in self.root.iterdir() if (p / LAYOUT_FILE).is_file())

    def save_run_info(self, plate: str, info: dict) -> None:
        """Write ``run.json`` for the plate."""
        self.write_file(plate, RUN_INFO_FILE, json.dumps(info, indent=2))

    def load_run_info(self, plate: str) -> dict:
        """Read ``run.json`` for the plate, or ``{}`` if there is none."""
        try:
            return json.loads(self.path(plate, RUN_INFO_FILE).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError) as error:
            raise OSError(f"Could not read run info for {plate}: {error}") from error
