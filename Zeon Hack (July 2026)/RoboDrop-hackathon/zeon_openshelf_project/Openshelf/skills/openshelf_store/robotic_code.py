from execution.execution_functions import *


def openshelf_store(
    base_url: str,
    slot: str,
    store_path: str = "/api/store",
    status_path: str = "/api/status",
    api_key: str = "",
    settled_field: str = "state",
    arms_clear: bool = False,
    poll_s: float = 1.0,
    max_wait_s: float = 120.0,
    timeout: float = 15.0,
):
    """Tell the shelf to take the item at the access position back into storage.

    Refuses unless the caller asserts `arms_clear`. This is the mirror hazard of retrieve:
    here the shelf is about to move while an arm may still be reaching in, and the shelf has
    no idea the arm exists. Requiring an explicit assertion makes the workflow author state
    that the arm has been withdrawn, rather than leaving it implied by step ordering.

    Args:
        base_url: Shelf address, no trailing slash.
        slot: Destination slot.
        store_path: Path reported by openshelf_probe.
        status_path: Status path for the settle poll.
        api_key: Bearer token, sent as a header.
        settled_field: Key in the status response holding the state string.
        arms_clear: Must be True. Assert that both arms are withdrawn from the shelf.
        poll_s: Seconds between status polls.
        max_wait_s: Give up after this long.
        timeout: Per-request timeout in seconds.
    """
    print_log(runlog=True, runlog_type="step_start")

    if not arms_clear:
        print_log("openshelf_store: refusing -- arms_clear was not asserted. The shelf is "
                  "about to move and Zeon's collision world models it as static, so it "
                  "cannot see the conflict. Withdraw both arms, then pass arms_clear=True.")
        return {"success": False, "reason": "arms_not_asserted_clear"}

    base = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None

    print_log(f"openshelf_store: storing to slot {slot!r} (arms asserted clear)")
    r = api_request(f"{base}{store_path}", method="POST", json_body={"slot": slot},
                    headers=headers, timeout=timeout,
                    save_name=f"store_{slot}", save_to_project=True)
    if not r["success"]:
        print_log(f"openshelf_store: command rejected ({r.get('error')}, "
                  f"status={r.get('status')})")
        return {"success": False, "reason": "command_failed", "error": r.get("error")}

    waited = 0.0
    while waited < max_wait_s:
        pause_aware_sleep(poll_s)
        waited += poll_s
        st = api_request(f"{base}{status_path}", method="GET", headers=headers,
                         timeout=timeout)
        if not st["success"]:
            continue
        data = st.get("data")
        state = data.get(settled_field) if isinstance(data, dict) else None
        if str(state).lower() in ("idle", "ready", "settled", "done", "false", "0"):
            print_log(f"openshelf_store: settled after {waited:.0f}s (state={state!r})")
            return {"success": True, "slot": slot, "waited_s": waited, "state": state}

    print_log(f"openshelf_store: not settled after {max_wait_s:.0f}s -- check physically")
    return {"success": False, "reason": "settle_timeout", "waited_s": waited}
