"""Tier 1 — literature ref entry caps."""

from __future__ import annotations

import json
from pathlib import Path

from agent.tools.forward import (
    MAX_REF_ENTRIES,
    MAX_REF_ENTRIES_WITH_ACTIVITY,
    _apply_entry_caps,
    _write_json_capped,
)


def test_apply_entry_caps_truncates_at_max_entries() -> None:
    entries = [
        {"pmid": str(i), "target": "TEM-1" if i % 2 == 0 else "other", "ki_uM": float(i)}
        for i in range(10)
    ]
    kept, truncated = _apply_entry_caps(entries)
    assert len(kept) <= MAX_REF_ENTRIES
    assert truncated is True


def test_apply_entry_caps_limits_full_activity_extractions() -> None:
    entries = [{"pmid": str(i), "target": "TEM-1", "ki_uM": float(i)} for i in range(6)]
    kept, truncated = _apply_entry_caps(entries)
    full_activity = [e for e in kept if e.get("ki_uM") is not None and "title" in e]
    assert len(full_activity) <= MAX_REF_ENTRIES_WITH_ACTIVITY


def test_write_json_capped_flags_oversized_payload(tmp_path: Path) -> None:
    path = tmp_path / "oversized.json"
    huge_entries = [{"note": "x" * 5000, "pmid": str(i)} for i in range(20)]
    payload = {"compound_id": "T0000", "entries": huge_entries}
    _write_json_capped(path, payload)
    written = json.loads(path.read_text())
    assert written.get("cap_truncated") is True
    assert len(written.get("entries", [])) <= MAX_REF_ENTRIES
