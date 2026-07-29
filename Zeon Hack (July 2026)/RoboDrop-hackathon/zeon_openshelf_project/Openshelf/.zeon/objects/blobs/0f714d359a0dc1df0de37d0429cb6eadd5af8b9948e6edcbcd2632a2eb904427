from execution.execution_functions import *


def openshelf_status(
    base_url: str,
    status_path: str = "/api/status",
    api_key: str = "",
    settled_field: str = "state",
    timeout: float = 10.0,
):
    """Read the shelf's current state. Read-only, safe to call any time.

    Returns the raw payload plus a decoded `settled` flag. `settled` is the field a workflow
    should gate arm motion on -- not `success`, which only means the HTTP call worked. A
    shelf that is mid-move answers HTTP 200 perfectly well.

    Args:
        base_url: Shelf address, no trailing slash.
        status_path: Path reported by openshelf_probe.
        api_key: Bearer token, sent as a header.
        settled_field: Key in the response holding the state string.
        timeout: Request timeout in seconds.
    """
    print_log(runlog=True, runlog_type="step_start")

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    r = api_request(f"{base_url.rstrip('/')}{status_path}", method="GET",
                    headers=headers, timeout=timeout)
    if not r["success"]:
        print_log(f"openshelf_status: failed ({r.get('error')}, status={r.get('status')})")
        return {"success": False, "reason": "request_failed", "error": r.get("error"),
                "settled": False}

    data = r.get("data")
    state = None
    if isinstance(data, dict):
        state = data.get(settled_field)
        if state is None:
            for alt in ("status", "state", "mode", "busy"):
                if alt in data:
                    state = data[alt]
                    break

    text = str(state).lower() if state is not None else ""
    settled = text in ("idle", "ready", "settled", "done", "false", "0")
    busy = text in ("moving", "busy", "running", "retrieving", "true", "1")

    # Unrecognised state is treated as NOT settled. Guessing "probably fine" here is how an
    # arm ends up inside a moving shelf.
    if not settled and not busy:
        print_log(f"openshelf_status: unrecognised state {state!r} -- treating as NOT settled")

    print_log(f"openshelf_status: state={state!r} settled={settled}")
    return {"success": True, "state": state, "settled": settled, "busy": busy,
            "data": data}
