from execution.execution_functions import *


def openshelf_retrieve(
    base_url: str,
    slot: str,
    retrieve_path: str = "/api/retrieve",
    status_path: str = "/api/status",
    api_key: str = "",
    settled_field: str = "state",
    poll_s: float = 1.0,
    max_wait_s: float = 120.0,
    timeout: float = 15.0,
):
    """Ask the shelf to bring a slot to the access position, then wait until it has settled.

    Returns `safe_to_enter`, and that is the field a workflow must gate arm motion on. It is
    True only after the shelf has *reported itself settled*, not merely after the command
    was accepted. Zeon models the shelf as a static mesh, so the collision world cannot see
    it moving -- if an arm goes in while it is actuating, nothing in the planner will stop it.

    The wait polls, because api_request is request/response only; there is no way to be
    notified. pause_aware_sleep is used rather than time.sleep so an operator Pause still
    works during the wait -- and `from execution.execution_functions import *` does not give
    you the stdlib anyway, so time.sleep would raise NameError.

    Args:
        base_url: Shelf address, no trailing slash.
        slot: Which slot to present.
        retrieve_path: Path reported by openshelf_probe.
        status_path: Status path for the settle poll.
        api_key: Bearer token, sent as a header.
        settled_field: Key in the status response holding the state string.
        poll_s: Seconds between status polls.
        max_wait_s: Give up after this long and report not-settled.
        timeout: Per-request timeout in seconds.
    """
    print_log(runlog=True, runlog_type="step_start")

    base = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None

    # Do not command motion without first confirming the shelf is idle. Stacking a retrieve
    # onto an in-progress move is the kind of thing that jams a mechanism.
    pre = api_request(f"{base}{status_path}", method="GET", headers=headers, timeout=timeout)
    if pre["success"] and isinstance(pre.get("data"), dict):
        s = str(pre["data"].get(settled_field, "")).lower()
        if s in ("moving", "busy", "running", "retrieving", "true", "1"):
            print_log(f"openshelf_retrieve: shelf is already {s!r}; refusing to stack a command")
            return {"success": False, "reason": "shelf_busy", "safe_to_enter": False}

    print_log(f"openshelf_retrieve: requesting slot {slot!r}")
    r = api_request(f"{base}{retrieve_path}", method="POST", json_body={"slot": slot},
                    headers=headers, timeout=timeout,
                    save_name=f"retrieve_{slot}", save_to_project=True)
    if not r["success"]:
        print_log(f"openshelf_retrieve: command rejected ({r.get('error')}, "
                  f"status={r.get('status')})")
        return {"success": False, "reason": "command_failed", "error": r.get("error"),
                "safe_to_enter": False}
    print_log(f"openshelf_retrieve: accepted, HTTP {r['status']}. Waiting for settle.")

    waited = 0.0
    while waited < max_wait_s:
        pause_aware_sleep(poll_s)
        waited += poll_s
        st = api_request(f"{base}{status_path}", method="GET", headers=headers,
                         timeout=timeout)
        if not st["success"]:
            print_log(f"openshelf_retrieve: status poll failed at {waited:.0f}s "
                      f"({st.get('error')}); continuing to poll")
            continue
        data = st.get("data")
        state = data.get(settled_field) if isinstance(data, dict) else None
        text = str(state).lower()
        if text in ("idle", "ready", "settled", "done", "false", "0"):
            print_log(f"openshelf_retrieve: settled after {waited:.0f}s (state={state!r}). "
                      f"SAFE TO ENTER.")
            return {"success": True, "slot": slot, "safe_to_enter": True,
                    "waited_s": waited, "state": state}
        print_log(f"openshelf_retrieve: {waited:.0f}s state={state!r}")

    # Timing out is not the same as failing to move. The shelf may still be in motion, so
    # the honest report is "do not enter", not "it did not work".
    print_log(f"openshelf_retrieve: still not settled after {max_wait_s:.0f}s. "
              f"DO NOT send an arm in. Check the shelf physically.")
    return {"success": False, "reason": "settle_timeout", "safe_to_enter": False,
            "waited_s": waited}
