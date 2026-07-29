"""Best-effort run log timing artifact for save_run_folder."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path


def find_repo_root(*, project_data: Path | None = None) -> Path | None:
    """Locate repo root containing ``ml/analysis/run_log_timing.py``."""
    candidates: list[Path] = []
    if project_data is not None:
        candidates.append(project_data.parent)
        candidates.extend(project_data.parent.parents)
    for path in candidates:
        if (path / "ml" / "analysis" / "run_log_timing.py").exists():
            return path
    return None


def workflow_id_from_metadata(meta_path: Path | None) -> str | None:
    if meta_path is None or not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text())
    except Exception:
        return None
    wf = meta.get("workflow_id") or meta.get("workflow")
    return str(wf).strip() if wf else None


def write_run_log_timing_summary(
    logs_dir: Path,
    *,
    workflow_id: str | None = None,
    repo_root: Path | None = None,
    project_data: Path | None = None,
    log_warning: Callable[[str], None] | None = None,
) -> Path | None:
    """Parse ``run_log.jsonl`` (preferred) or ``run_log.txt``; write ``timing_summary.json``."""
    warn = log_warning or (lambda _msg: None)
    jsonl = logs_dir / "run_log.jsonl"
    txt = logs_dir / "run_log.txt"
    log_path = jsonl if jsonl.exists() else txt
    if not log_path.exists():
        return None

    root = repo_root or find_repo_root(project_data=project_data)
    if root is None:
        warn("save_run_folder: timing summary skipped (repo ml/ not found)")
        return None

    ml_dir = root / "ml"
    ml_str = str(ml_dir)
    if ml_str not in sys.path:
        sys.path.insert(0, ml_str)

    try:
        from analysis.run_log_timing import analyze_run_log, write_timing_artifact
    except ImportError as ex:
        warn(f"save_run_folder: timing summary import failed: {ex}")
        return None

    try:
        report = analyze_run_log(log_path, workflow_id=workflow_id)
        return write_timing_artifact(report, logs_dir / "timing_summary.json")
    except Exception as ex:
        warn(f"save_run_folder: timing summary failed: {ex}")
        return None
