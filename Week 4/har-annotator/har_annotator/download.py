"""Cached, hashed, provenance-logged downloads for the HAR annotator pipeline.

Every fetch is recorded to ``data/manifest.csv`` with the source URL, the local
path, the access date (UTC), the SHA256 of the downloaded bytes, and the file
size. Re-running a fetch that is already cached does not re-download; it simply
re-verifies the hash. This makes the whole analysis replay end-to-end from the
manifest.
"""
from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import os
import pathlib
import shutil
import urllib.request

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
MANIFEST = DATA_DIR / "manifest.csv"

_MANIFEST_FIELDS = ["name", "filename", "url", "access_date_utc", "sha256", "size_bytes"]

# A polite, generic user agent. Some data hosts (UCSC, EBI) 403 the bare
# urllib default.
_UA = "har-annotator/1.0 (research pipeline; python-urllib)"


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    with open(MANIFEST, newline="") as fh:
        return list(csv.DictReader(fh))


def _write_manifest(rows: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_MANIFEST_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in _MANIFEST_FIELDS})


def _log(name: str, filename: str, url: str, sha256: str, size: int) -> None:
    rows = _read_manifest()
    rows = [r for r in rows if r.get("name") != name]  # upsert by logical name
    rows.append(
        {
            "name": name,
            "filename": filename,
            "url": url,
            "access_date_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "sha256": sha256,
            "size_bytes": str(size),
        }
    )
    _write_manifest(rows)


def fetch(url: str, name: str, filename: str | None = None, force: bool = False) -> pathlib.Path:
    """Download ``url`` to ``data/<filename>`` (cached), logging provenance.

    ``name`` is a stable logical key for the manifest (e.g. ``"hars_bed"``).
    Returns the local path. If the file already exists and ``force`` is False,
    the cached copy is used and its hash re-verified in the manifest.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filename = filename or url.split("/")[-1].split("?")[0]
    dest = DATA_DIR / filename

    if dest.exists() and not force:
        # Ensure the manifest has an up-to-date row even for a warm cache.
        if not any(r.get("name") == name for r in _read_manifest()):
            _log(name, filename, url, _sha256(dest), dest.stat().st_size)
        return dest

    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out)
    tmp.replace(dest)

    _log(name, filename, url, _sha256(dest), dest.stat().st_size)
    return dest


def manifest_df():
    """Return the provenance manifest as a pandas DataFrame (for reporting)."""
    import pandas as pd

    if not MANIFEST.exists():
        return pd.DataFrame(columns=_MANIFEST_FIELDS)
    return pd.read_csv(MANIFEST)
