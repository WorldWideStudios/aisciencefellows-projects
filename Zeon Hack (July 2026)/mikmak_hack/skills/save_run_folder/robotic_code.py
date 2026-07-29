"""Checkpoint a run: assemble/refresh this execution's output folder in the project.

Copies the run's structured log, any captured images, and the run metadata /
inputs into ``data/logs/<execution_id>/<run_name>/`` under the project data
folder (``project_data_dir()`` → ``<project_root>/data/``). That tree is what the
platform pushes to the cloud. The raw per-run artifacts are *read* from
``execution_dir()`` — the out-of-tree run scratch where they are produced — and
copied into ``data/`` here.

**Call this repeatedly, not just at the end.** The folder is keyed by execution
id and run name with no per-call timestamp, so every call refreshes one folder
rather than creating a new one. That is deliberate: a run that died partway used
to leave *nothing* in the project tree, because the only call was the final node.
Now a ``checkpoint="start"`` node right after ``start`` registers the execution
before any hardware moves, mid-run checkpoints record how far it got, and the
final call marks it complete. ``run_status.json`` accumulates one entry per
checkpoint, so "how far did this run actually get" is answerable from the project
tree alone — success or failure.

Historic folders written by the older ``<run_name>_<timestamp>`` scheme are left
alone; readers walk whatever subdirectories exist.
"""

import json
import re
import shutil
from datetime import datetime, timezone

from .modules import ExecutionInfoContext, execution_dir, print_log, project_data_dir


def save_run_folder(run_name: str = "run", checkpoint: str = "end"):
    """Bundle this run's log, images, and inputs into ``<project>/data/`` so it
    syncs to the cloud, and record that this checkpoint was reached.

    Args:
        run_name: Operator-facing folder label, from the run-setup canvas.
            Sanitised to a safe filename.
        checkpoint: Short tag for *where in the graph* this call sits — by
            convention ``"start"``, ``"mid"``, or ``"end"``. ``"end"`` marks the
            run complete in ``run_status.json``; anything else marks it partial.
            Free-form, so a longer protocol can name its phases.
    """
    src = execution_dir(create=True)
    if src is None:
        print_log(
            "save_run_folder: no execution dir (no run bound) — skipping",
            runlog=True,
            runlog_type="event",
        )
        return {"success": False, "reason": "no run dir"}

    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(run_name)).strip("_")[:48] or "run"
    tag = re.sub(r"[^A-Za-z0-9_-]+", "_", str(checkpoint)).strip("_")[:24] or "checkpoint"
    eid = ExecutionInfoContext.get().execution_id or "no_execution"

    # Stable per-execution destination — no timestamp, so repeat calls update in
    # place instead of scattering one folder per checkpoint.
    out = project_data_dir(f"logs/{eid}/{safe}", create=True)
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

    # Run log: copy the raw jsonl and render a readable .txt (one line per event).
    n_events = 0
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
            n_events = len(lines)
            (logs / "run_log.txt").write_text("\n".join(lines) + "\n")
        except Exception as ex:
            print_log(f"save_run_folder: run log copy failed: {ex}")
        break  # only the current run's log

    # Any images produced this run (best-effort; typically empty in simulation).
    n_img = 0
    for pat in ("**/*.png", "**/*.jpg", "**/*.jpeg"):
        for img in src.glob(pat):
            try:
                shutil.copy(img, captures / img.name)
                n_img += 1
            except Exception:
                pass

    # Metadata + input values snapshot. Written on every checkpoint, so the inputs
    # are on disk from the very first one — that is what makes an aborted run
    # attributable to the round that planned it.
    meta_path = src / "metadata.json"
    if meta_path.exists():
        try:
            shutil.copy(meta_path, out / "metadata.json")
            meta = json.loads(meta_path.read_text())
            inputs = meta.get("input_values", meta.get("inputs", {}))
            (out / "run_inputs.json").write_text(json.dumps(inputs, indent=2))
        except Exception as ex:
            print_log(f"save_run_folder: metadata copy failed: {ex}")

    # Provenance ledger: append this checkpoint, keep the earlier ones.
    status_path = out / "run_status.json"
    try:
        status = json.loads(status_path.read_text()) if status_path.exists() else {}
    except Exception:
        status = {}
    entries = status.get("checkpoints", [])
    entries.append({
        "checkpoint": tag,
        "at": datetime.now(timezone.utc).isoformat(),
        "log_events": n_events,
        "images": n_img,
    })
    status.update({
        "execution_id": eid,
        "run_name": run_name,
        "checkpoints": entries,
        "last_checkpoint": tag,
        "complete": tag == "end",
        "source": "workflow",
    })
    status_path.write_text(json.dumps(status, indent=2) + "\n")

    print_log(
        f"Run folder checkpoint '{tag}': {out.name} ({n_events} event(s), {n_img} image(s))",
        runlog=True,
        runlog_type="event",
    )
    return {"success": True, "folder": str(out), "checkpoint": tag, "images": n_img}
