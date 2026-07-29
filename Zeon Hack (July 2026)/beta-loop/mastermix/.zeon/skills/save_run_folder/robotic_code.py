"""Finalize a run: assemble a named, timestamped output folder in the project.

Copies the run's structured log, any captured images, and the run metadata /
inputs into ``data/logs/<execution_id>/<run_name>_<YYYYmmdd_HHMMSS>/`` under the
project data folder (``project_data_dir()`` → ``<project_root>/data/``). That tree is what the
platform pushes to the cloud when the workflow reaches a terminal state, so the
assembled folder syncs with the project. The raw per-run artifacts are *read*
from ``execution_dir()`` — the out-of-tree run scratch where they are produced —
and copied into ``data/`` here.

Intended as the last node of a workflow; the operator supplies ``run_name`` from
the run-setup canvas.
"""

import json
import re
import shutil
from datetime import datetime

from .modules import ExecutionInfoContext, execution_dir, print_log, project_data_dir
from .timing_summary import write_run_log_timing_summary, workflow_id_from_metadata


def save_run_folder(run_name: str = "run"):
    """Bundle this run's log, images, and inputs into a named folder under
    ``<project>/data/`` so it syncs to the cloud on workflow terminal.

    Args:
        run_name: Operator-facing folder label; combined with a timestamp into
            ``<run_name>_<YYYYmmdd_HHMMSS>``. Sanitised to a safe filename.
    """
    # Source: the out-of-tree run scratch where run_log / images / metadata live.
    src = execution_dir(create=True)
    if src is None:
        print_log(
            "save_run_folder: no execution dir (no run bound) — skipping",
            runlog=True,
            runlog_type="event",
        )
        return {"success": False, "reason": "no run dir"}

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(run_name)).strip("_")[:48] or "run"
    eid = ExecutionInfoContext.get().execution_id or "no_execution"

    # Destination: inside the project data tree, keyed by execution id under
    # data/logs/<eid>/ so it syncs on terminal (and stays clear of the reserved,
    # non-syncing data/screens/).
    out = project_data_dir(f"logs/{eid}/{safe}_{stamp}", create=True)
    if out is None:
        print_log(
            "save_run_folder: no project bound — cannot write run folder",
            runlog=True,
            runlog_type="event",
        )
        return {"success": False, "reason": "no project"}

    logs = out / "logs"
    captures = out / "captures"
    logs.mkdir(parents=True, exist_ok=True)
    captures.mkdir(parents=True, exist_ok=True)

    meta_path = src / "metadata.json"

    # Run log: copy the raw jsonl and render a readable .txt (one line per event).
    copied_run_log = False
    for jl in sorted(src.glob("run_log_*.jsonl")):
        try:
            shutil.copy(jl, logs / "run_log.jsonl")
            lines = []
            for raw in jl.read_text().splitlines():
                if not raw.strip():
                    continue
                try:
                    e = json.loads(raw)
                except Exception:
                    lines.append(raw)
                    continue
                t = e.get("t", "")
                typ = e.get("type", "")
                label = e.get("label", "")
                msg = e.get("msg", "")
                lines.append(f"{t}  [{typ}] {label}{(' — ' + msg) if msg else ''}".rstrip())
            (logs / "run_log.txt").write_text("\n".join(lines) + "\n")
            copied_run_log = True
        except Exception as ex:
            print_log(f"save_run_folder: run log copy failed: {ex}")
        break  # only the current run's log

    if copied_run_log:
        try:
            timing_out = write_run_log_timing_summary(
                logs,
                workflow_id=workflow_id_from_metadata(meta_path),
                project_data=project_data_dir(create=False),
                log_warning=print_log,
            )
            if timing_out is not None:
                print_log(
                    f"save_run_folder: wrote {timing_out.name}",
                    runlog=True,
                    runlog_type="event",
                )
        except Exception as ex:
            print_log(f"save_run_folder: timing summary failed: {ex}")

    # Any images produced this run (best-effort; typically empty in simulation).
    # src (execution_dir) and out (project data) are different trees, so globbing
    # src never picks up the folder we are building.
    n_img = 0
    for pat in ("**/*.png", "**/*.jpg", "**/*.jpeg"):
        for img in src.glob(pat):
            try:
                shutil.copy(img, captures / img.name)
                n_img += 1
            except Exception:
                pass

    # Metadata + input values snapshot.
    if meta_path.exists():
        try:
            shutil.copy(meta_path, out / "metadata.json")
            meta = json.loads(meta_path.read_text())
            inputs = meta.get("input_values", meta.get("inputs", {}))
            (out / "run_inputs.json").write_text(json.dumps(inputs, indent=2))
        except Exception as ex:
            print_log(f"save_run_folder: metadata copy failed: {ex}")

    print_log(f"Saved run folder: {out.name} ({n_img} image(s))", runlog=True, runlog_type="event")
    return {"success": True, "folder": str(out), "images": n_img}
