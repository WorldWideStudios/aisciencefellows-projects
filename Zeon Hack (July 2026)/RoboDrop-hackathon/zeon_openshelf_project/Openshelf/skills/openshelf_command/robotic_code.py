from execution.execution_functions import *


def openshelf_command(
    base_url: str,
    path: str,
    method: str = "GET",
    body_json: str = "",
    api_key: str = "",
    save_name: str = "",
    timeout: float = 30.0,
):
    """Call an arbitrary OpenShelf endpoint. The escape hatch for anything not yet modelled.

    Deliberately generic so the shelf's full API is reachable from a workflow without a new
    skill per endpoint. That also means it can command motion, so it does NOT wait for a
    settle and does NOT return safe_to_enter -- if the call actuates the shelf, follow it
    with openshelf_status and gate on `settled` yourself.

    `body_json` is a JSON string rather than a dict because workflow inputs are typed
    object/string/float/int/boolean; there is no dict input type.

    Args:
        base_url: Shelf address, no trailing slash.
        path: Endpoint path, e.g. "/api/slots/3".
        method: HTTP method.
        body_json: Request body as a JSON string. Empty for none.
        api_key: Bearer token, sent as a header.
        save_name: Basename to save the response under. Empty to skip saving.
        timeout: Request timeout in seconds.
    """
    import json

    print_log(runlog=True, runlog_type="step_start")

    body = None
    if body_json.strip():
        try:
            body = json.loads(body_json)
        except ValueError as exc:
            print_log(f"openshelf_command: body_json is not valid JSON ({exc})")
            return {"success": False, "reason": "bad_json_body"}

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    print_log(f"openshelf_command: {method} {path}")
    r = api_request(f"{base_url.rstrip('/')}{path}", method=method, json_body=body,
                    headers=headers, timeout=timeout,
                    save_name=save_name or None, save_to_project=bool(save_name))
    if not r["success"]:
        print_log(f"openshelf_command: failed ({r.get('error')}, status={r.get('status')})")
        return {"success": False, "reason": "request_failed", "status": r.get("status"),
                "error": r.get("error")}

    print_log(f"openshelf_command: HTTP {r['status']}")
    return {"success": True, "status": r["status"], "data": r.get("data")}
