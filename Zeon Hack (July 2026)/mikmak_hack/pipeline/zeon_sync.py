"""Sync stage: get a planned round's numbers into the Zeon app.

Plan writes `inputs/<round_id>.json`. That file is the round's audit record, but
the Zeon app never reads it — the app fills its run-setup canvas from the
workflow's own `inputs[].defaultValue`. So this module bakes the preset into the
workflow file, then hands the result to the `zeon` CLI (`commit` + `push`) so the
cloud HEAD the app opens is the one the agent just planned.

Two deliberate limits:
  - `bake_preset_into_workflow` raises on any preset key that has no matching
    workflow input. A silently-dropped key would mean the operator runs a plate
    that isn't the plate the round bead claims — worse than a hard failure.
  - Nothing here calls `bd`. Stage transitions belong to beads_writer, the single
    writer; the agent layer decides when to record a sync as a note on the round.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUTS_DIR = PROJECT_ROOT / "inputs"
WORKFLOWS_DIR = PROJECT_ROOT / "workflows"
PROJECT_MANIFEST = PROJECT_ROOT / "project.json"

# Which workflow a round of each assay type targets. cfps_expression is a
# two-part round: Part 1 (cfps_mastermix) is set up by hand in its own canvas and
# has no Plan-generated preset, so only Part 2 is listed as bakeable.
WORKFLOW_FOR_ASSAY = {
    "kinetics": "tem1_kinetics_characterization",
    "inhibitor_dose_response": "cfps_inhibitor_dose_response",
    "cfps_expression": "cfps_sfgfp_confirmation",
}

# `zeon commit` with no paths snapshots the *entire* working tree — which here
# includes the beads Dolt DB, graphify-out/, and the pipeline's own source. None
# of that belongs in a cloud lab project, so every commit from this module is
# scoped to the Zeon-authored parts of the tree.
SYNC_PATHS = ["project.json", "workflows", "skills", "worlds", "objects", "canvas", "inputs", "data"]


class SyncError(RuntimeError):
    """A bake or a `zeon` invocation failed. Raised, never returned as a flag."""


def _coerce(value, declared_type: str):
    """Match the workflow input's declared type. The app is strict about this —
    an int input holding 5.0 is a different thing to it than one holding 5."""
    if declared_type == "int":
        return int(value)
    if declared_type == "float":
        return float(value)
    if declared_type in ("string", "object"):
        return str(value)
    return value


def workflow_path(workflow_id: str) -> Path:
    path = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not path.exists():
        raise SyncError(f"no workflow at {path}")
    return path


def bake_preset_into_workflow(round_id: str, workflow_id: str, dry_run: bool = False) -> dict:
    """Write every value in `inputs/<round_id>.json` into the matching
    `inputs[].defaultValue` of `workflows/<workflow_id>.json`.

    Returns a summary of what changed. Raises if a preset key matches no input.
    """
    preset_path = INPUTS_DIR / f"{round_id}.json"
    if not preset_path.exists():
        raise SyncError(f"no input preset at {preset_path} — plan the round first")
    preset = json.loads(preset_path.read_text())

    path = workflow_path(workflow_id)
    workflow = json.loads(path.read_text())
    by_name = {i["name"]: i for i in workflow["inputs"]}

    changed, unchanged, unmatched = [], [], []
    for key, value in preset.items():
        if key.startswith("_"):  # _label and friends are preset metadata, not inputs
            continue
        spec = by_name.get(key)
        if spec is None:
            unmatched.append(key)
            continue
        new_value = _coerce(value, spec["type"])
        if spec.get("defaultValue") == new_value:
            unchanged.append(key)
        else:
            changed.append({"name": key, "from": spec.get("defaultValue"), "to": new_value})
            spec["defaultValue"] = new_value

    if unmatched:
        raise SyncError(
            f"{len(unmatched)} preset key(s) have no input in {workflow_id}: {unmatched[:8]}"
            " — the plan and the workflow graph have drifted apart; fix one of them "
            "before syncing, or the operator runs a different plate than the round claims"
        )

    missing = [n for n in by_name if n not in preset]
    if not dry_run:
        path.write_text(json.dumps(workflow, indent=2) + "\n")

    return {
        "workflow_id": workflow_id,
        "changed": changed,
        "changed_count": len(changed),
        "unchanged_count": len(unchanged),
        "inputs_left_at_workflow_default": missing,
        "dry_run": dry_run,
    }


def set_active_workflow(workflow_id: str) -> dict:
    """Point project.json at `workflow_id` so it's what the Zeon app opens."""
    workflow_path(workflow_id)  # existence check
    manifest = json.loads(PROJECT_MANIFEST.read_text())
    previous = manifest.get("active_workflow")
    manifest["active_workflow"] = workflow_id
    PROJECT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"active_workflow": workflow_id, "previous": previous}


# --- zeon CLI ------------------------------------------------------------------

def _zeon(*args: str) -> str:
    proc = subprocess.run(["zeon", *args], capture_output=True, text=True, cwd=PROJECT_ROOT)
    if proc.returncode != 0:
        raise SyncError(f"zeon {' '.join(args)} failed: {(proc.stderr or proc.stdout).strip()[-800:]}")
    return proc.stdout.strip()


def _in_sync_scope(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in SYNC_PATHS)


def zeon_status(scoped: bool = True) -> dict:
    """Working tree vs cloud HEAD. `scoped` keeps only the paths a sync would
    actually send, so the report matches what pushing would do."""
    out = _zeon("status", "--json")
    try:
        status = json.loads(out)
    except json.JSONDecodeError:
        return {"raw": out}
    if not scoped:
        return status
    scoped_status = {k: v for k, v in status.items() if not isinstance(v, list)}
    for key in ("added", "modified", "deleted", "unmerged"):
        if key in status:
            scoped_status[key] = [f for f in status[key] if _in_sync_scope(f)]
    scoped_status["sync_paths"] = SYNC_PATHS
    return scoped_status


def _cloud_tip() -> str:
    """The sha the cloud ref actually points at right now (not our cached copy)."""
    from zeon.sync.commands import DEFAULT_REF, _find_local_repo, _open_client

    _, pid = _find_local_repo()
    with _open_client() as client:
        return client.get_ref(pid, DEFAULT_REF).get("commit_sha", "")


def reconcile_with_cloud(message: str) -> dict:
    """Merge cloud changes into the working tree and re-anchor a *scoped* commit
    on the cloud tip. Call this when a push comes back with "the cloud has
    changed since your last sync".

    `zeon sync`/`zeon pull` both finish by committing the WHOLE working tree,
    which here would push graphify-out/ and the beads Dolt DB into the cloud lab
    project. So this does the merge, then resets HEAD back to the cloud tip and
    rebuilds the commit from SYNC_PATHS only — same merge result, none of the
    noise. The working tree is never reset, only HEAD.

    The merge itself is safe for local edits: `zeon`'s 3-way merge keeps our
    version of any file the cloud didn't touch, and only deletes a file the cloud
    removed that we hadn't modified.
    """
    tip_before = _cloud_tip()
    merge_out = _zeon("pull", "--force")  # 3-way merge; leaves HEAD as a whole-tree commit
    tip = _cloud_tip()
    _zeon("reset", tip)  # HEAD only — working tree keeps the merged content
    return {"merged_from": tip_before, "cloud_tip": tip, "output": merge_out}


def zeon_commit_and_push(message: str, paths: list[str] | None = None) -> dict:
    """Snapshot the Zeon-authored paths into a local commit and send them to the
    cloud.

    Outward-facing: after this returns, the Zeon app's HEAD is the working tree,
    and whoever opens the project sees these values. The agent layer asks the
    operator before calling it. Defaults to SYNC_PATHS rather than the whole tree
    — see the note there.
    """
    targets = [p for p in (paths or SYNC_PATHS) if (PROJECT_ROOT / p).exists()]
    if not targets:
        raise SyncError(f"none of the sync paths exist under {PROJECT_ROOT}")

    def commit_and_push() -> dict:
        try:
            commit_out = _zeon("commit", *targets, "-m", message)
        except SyncError as exc:
            # A merge can leave the tree already matching HEAD; there is then
            # nothing to record but still a commit to send.
            if "nothing to commit" not in str(exc):
                raise
            commit_out = "nothing to commit (working tree matches HEAD)"
        push_out = _zeon("push")
        return {"committed": commit_out, "pushed": push_out, "paths": targets}

    try:
        return commit_and_push()
    except SyncError as exc:
        # Someone else moved the cloud ref — usually a run finishing in the Zeon
        # app and writing its logs back. Merge their work in and retry once.
        if "cloud has changed" not in str(exc):
            raise
        reconciled = reconcile_with_cloud(message)
        result = commit_and_push()
        return {**result, "reconciled_with_cloud": reconciled}
