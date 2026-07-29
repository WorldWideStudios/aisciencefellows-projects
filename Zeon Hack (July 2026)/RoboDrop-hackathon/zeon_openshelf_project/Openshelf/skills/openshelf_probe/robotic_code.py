from execution.execution_functions import *


def openshelf_probe(
    base_url: str,
    api_key: str = "",
    timeout: float = 5.0,
    save: bool = True,
):
    """Discover what the OpenShelf's HTTP API actually exposes. Read-only.

    GET only, deliberately. A blind POST to an unknown path on a machine with moving parts
    could actuate it, and discovery is exactly the moment you do not know which paths those
    are. Nothing here can move the shelf.

    Reports the status code and a shape summary for each candidate path, so the real
    endpoint table can be written from evidence instead of guessed. An OpenAPI document, if
    one is served, makes the rest of this unnecessary.

    Args:
        base_url: Shelf address, e.g. "http://192.168.1.50:8080". No trailing slash.
        api_key: Bearer token if the shelf wants one. Sent as a header, never in the URL --
            urls and params are saved into the synced project, headers are not.
        timeout: Per-request timeout in seconds. Short, because most paths will 404.
        save: Write each response into the project under data/api/<run>/.
    """
    print_log(runlog=True, runlog_type="step_start")

    base = base_url.rstrip("/")
    if not base:
        print_log("openshelf_probe: base_url is empty")
        return {"success": False, "reason": "no_base_url"}

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None

    paths = [
        "/api/status", "/api/state", "/api/health", "/health", "/status",
        "/api/inventory", "/api/items", "/api/slots", "/api/v1/status",
        "/api/v1/inventory", "/api/config", "/api/version", "/", "/openapi.json",
        "/swagger.json", "/docs", "/api/docs",
    ]

    found = []
    unreachable = 0
    for p in paths:
        r = api_request(
            f"{base}{p}",
            method="GET",
            headers=headers,
            timeout=timeout,
            save_name=("probe" + p.replace("/", "_")) if save else None,
            save_to_project=save,
        )
        if not r["success"]:
            # api_request fails soft, so distinguish "no route" from "no host".
            if r.get("status") is None:
                unreachable += 1
                print_log(f"openshelf_probe: {p} -> unreachable ({r.get('error')})")
            else:
                print_log(f"openshelf_probe: {p} -> HTTP {r['status']}")
            continue

        data = r.get("data")
        if isinstance(data, dict):
            shape = "object keys=" + ",".join(sorted(data.keys())[:10])
        elif isinstance(data, list):
            shape = f"array len={len(data)}"
            if data and isinstance(data[0], dict):
                shape += " item keys=" + ",".join(sorted(data[0].keys())[:10])
        else:
            shape = f"{type(data).__name__} " + str(data)[:120]
        found.append({"path": p, "status": r["status"], "shape": shape})
        print_log(f"openshelf_probe: {p} -> HTTP {r['status']}  {shape}")

    if unreachable == len(paths):
        print_log(
            "openshelf_probe: every path was unreachable. The address or port is wrong, or "
            "the shelf is not on a network this backend can see. Nothing was sent that "
            "could have moved it."
        )
        return {"success": False, "reason": "host_unreachable", "base_url": base}

    spec = [f for f in found if f["path"] in ("/openapi.json", "/swagger.json")]
    if spec:
        print_log(f"openshelf_probe: an API spec is served at {spec[0]['path']} -- read that "
                  f"and write the endpoint table from it rather than from these guesses.")

    print_log(f"openshelf_probe: {len(found)} responding path(s) of {len(paths)} tried")
    return {"success": True, "responding": found, "n_responding": len(found),
            "has_spec": bool(spec), "base_url": base}
