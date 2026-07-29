"""Run a plate-reader read on the Windows control PC and pull the export into the project.

The reader has no API — it is driven through its own Windows GUI by an AutoGUI HTTP
server that replays named screen clicks. So this skill is an ordered click/type
script (``STEPS``) plus one file pull. The clicks go through ``api_request``:
https://readme.zeonsystems.app/docs/calling-an-external-api

The export lands in ``<project_root>/data/platereader/<execution_id>/``.
"""

import re

import requests

from .modules import (
    ExecutionInfoContext,
    api_request,
    is_sim_mode,
    pause_aware_sleep,
    print_log,
    project_data_dir,
)

AUTOGUI_BASE_URL = "http://100.115.255.117:8000"
DOWNLOAD_TIMEOUT_S = 60.0
SIM_DWELL_S = 2.0

# Where Gen5's save dialog already points — nothing types this, so changing it does
# not redirect the export; it only changes where we look for the PDF, and must match
# the dialog's real destination.
REMOTE_EXPORT_DIR = r"C:\Users\Owner\Documents"

# The click/type script, as walked through on the real GUI. Waits are AFTER each step.
#   ("click", "<press_action>", wait_s)   — a press action saved on the box
#   ("type",  "<text>",         wait_s)   — {run_id} {export_file} {export_dir}
#   ("wait",  "",               wait_s)
# The save dialog's name field arrives pre-selected, so typing replaces it, and Gen5
# appends the .pdf itself — hence the bare {run_id} rather than {export_file}.
STEPS = (
    ("click", "Experiment_ReadPlate", 15.0),
    ("click", "Hackathon_2_OK", 60.0),  # the read itself
    ("click", "Hackathon_Fix_1_Cancel", 5.0),
    ("click", "Hackathon_3_No", 3.0),
    ("click", "Hackathon_4_Print", 5.0),
    ("click", "Hackathon_5_PDFOK", 5.0),
    ("type", "{run_id}", 1.0),
    ("click", "Experiment_Fix_ExportSave", 5.0),
    ("click", "Hackathon_5_PDFOK", 5.0),
)


def _call(url, **kw):
    """api_request that raises instead of returning success=False."""
    r = api_request(url, **kw)
    if not r["success"]:
        raise RuntimeError(f"AutoGUI {url} failed: {r['error']}")
    return r["data"]


def _safe_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(label).strip())
    return cleaned.strip("_") or "read"


def platereader_measure(read_label: str = "read"):
    """Read the loaded plate and save the exported PDF into the project.

    Args:
        read_label: Suffix for the exported read report, e.g. "initial" or
            "endpoint_5min". Multiple reads in one workflow must use distinct
            labels so the exported PDFs do not overwrite each other.

    Assumes a plate is already loaded and the lid is closed (platereader_load then
    platereader_closed first).
    """
    print_log(runlog=True, runlog_type="step_start")
    run_id = ExecutionInfoContext.get().execution_id or "no_execution"
    # Gen5 exports PDF and nothing else, and it appends the extension itself.
    safe_label = _safe_label(read_label)
    export_stem = f"{run_id}_{safe_label}"
    export_file = f"{export_stem}.pdf"
    remote_path = REMOTE_EXPORT_DIR.rstrip("\\/") + "\\" + export_file
    print_log(f"Starting platereader_measure ({safe_label}) -> {export_file}", runlog=True)

    if is_sim_mode():
        print_log(f"[SIM] skipping the GUI bridge; would export {remote_path}")
        pause_aware_sleep(SIM_DWELL_S)
        return {"success": True, "run_id": run_id, "export_path": None, "sim": True}

    ids = {
        a["name"]: a["id"]
        for a in _call(f"{AUTOGUI_BASE_URL}/api/v1/press-actions/", params={"limit": 1000})
    }
    subs = {"run_id": export_stem, "export_dir": REMOTE_EXPORT_DIR, "export_file": export_file}

    for kind, value, wait_s in STEPS:
        if kind == "click":
            print_log(f"  click {value}")
            _call(f"{AUTOGUI_BASE_URL}/api/v1/press-actions/{ids[value]}/execute", method="POST")
        elif kind == "type":
            text = value.format(**subs)
            print_log(f"  type {text!r}")
            _call(
                f"{AUTOGUI_BASE_URL}/api/v1/screen/type",
                method="POST",
                json_body={"text": text, "interval": 0.0},
            )
        pause_aware_sleep(wait_s)

    resp = requests.post(
        f"{AUTOGUI_BASE_URL}/api/v1/screen/download-file",
        json={"path": remote_path},
        timeout=DOWNLOAD_TIMEOUT_S,
    )
    resp.raise_for_status()

    out_path = project_data_dir(f"platereader/{run_id}", create=True) / export_file
    out_path.write_bytes(resp.content)

    print_log(f"platereader_measure completed -> {out_path} ({len(resp.content)} bytes)", runlog=True)
    return {"success": True, "run_id": run_id, "export_path": str(out_path)}
    
