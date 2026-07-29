from execution.execution_functions import *

# Explicit, not via the star-import: press_and_capture lives in skills/openshelf_devices.py,
# which is ours, not part of the platform API. Relying on the star-import to supply it is a
# NameError at run time -- Zeon's validator flags exactly this.
from openshelf_devices import press_and_capture


def actuate_module(
    device: SkillObject,
    action: str,
    transport: str = "panel",
    base_url: str = "",
    path: str = "",
    method: str = "POST",
    body_json: str = "",
    api_key: str = "",
    button_anchor: str = "",
    view_anchor: str = "view_front",
    arm: str = "right_arm",
    duration_s: float = 0.0,
    press_depth_m: float = 0.004,
):
    """Actuate an instrument, dispatching on how that instrument can be reached.

    One entry point for three transports, so a workflow does not need to know which kind of
    device it is holding:

      http   -> api_request against the instrument's own REST surface
      panel  -> an arm presses the button and a camera reads the display back
      serial -> refused. A skill cannot open a serial port; run a host-side serial-to-HTTP
                shim and then use transport="http".

    For `panel`, the press is delegated to press_and_capture in the shared
    skills/openshelf_devices.py module, so the press-and-photograph pattern has exactly one
    implementation rather than two that drift apart. A skill cannot call a sibling skill;
    the skill loader puts skills/ on sys.path, which is what makes the shared module work.

    `duration_s` covers the instruments that run unattended once triggered -- a seal cycle, a
    shake, a spin. The dwell is pause_aware_sleep, so an operator Pause still works while the
    instrument is running, and time.sleep would raise NameError here anyway.

    Args:
        device: The instrument object.
        action: What to do. Free-form; recorded in the log for traceability.
        transport: "http", "panel", or "serial".
        base_url: For http. Instrument address, no trailing slash.
        path: For http. Endpoint path.
        method: For http. HTTP method.
        body_json: For http. Request body as a JSON string (workflow inputs have no dict type).
        api_key: For http. Bearer token, sent as a header -- never in the URL, because urls
            are saved into the synced project and headers are not.
        button_anchor: For panel. Contact anchor to press.
        view_anchor: For panel. Viewpoint anchor for reading the display.
        arm: For panel. Which arm presses.
        duration_s: Dwell after triggering, for instruments that then run on their own.
        press_depth_m: For panel. How far past the anchor to travel.
    """
    import json

    print_log(runlog=True, runlog_type="step_start")
    print_log(f"actuate_module: {device.id} action={action!r} via {transport!r}")

    if transport == "serial":
        print_log("actuate_module: serial is not reachable from a skill -- the runtime offers "
                  "api_request (HTTP) and nothing else. Run a serial-to-HTTP shim on the host "
                  "and call this again with transport='http'.")
        return {"success": False, "reason": "serial_unsupported_from_skill"}

    if transport == "http":
        if not base_url or not path:
            print_log("actuate_module: http transport needs base_url and path")
            return {"success": False, "reason": "missing_http_target"}
        body = None
        if body_json.strip():
            try:
                body = json.loads(body_json)
            except ValueError as exc:
                print_log(f"actuate_module: body_json is not valid JSON ({exc})")
                return {"success": False, "reason": "bad_json_body"}
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
        r = api_request(f"{base_url.rstrip('/')}{path}", method=method, json_body=body,
                        headers=headers, timeout=30,
                        save_name=f"{device.id}_{action}", save_to_project=True)
        if not r["success"]:
            print_log(f"actuate_module: http call failed ({r.get('error')}, "
                      f"status={r.get('status')})")
            return {"success": False, "reason": "http_failed", "error": r.get("error")}
        print_log(f"actuate_module: http HTTP {r['status']}")
        if duration_s > 0:
            print_log(f"actuate_module: instrument running, dwelling {duration_s:.0f}s")
            pause_aware_sleep(duration_s)
        return {"success": True, "transport": "http", "status": r["status"],
                "data": r.get("data"), "verifiable": True,
                "note": "The instrument acknowledged over HTTP; that response is the evidence."}

    if transport == "panel":
        if not button_anchor:
            print_log("actuate_module: panel transport needs button_anchor. These devices have "
                      "no host interface, so there is no fallback -- capture the button anchor "
                      "From arm first.")
            return {"success": False, "reason": "missing_button_anchor"}
        res = press_and_capture(
            device.id, button_anchor, view_anchor=view_anchor, arm=arm,
            press_depth_m=press_depth_m,
        )
        if not res.get("success"):
            return res
        if duration_s > 0:
            print_log(f"actuate_module: instrument running unattended, dwelling {duration_s:.0f}s")
            pause_aware_sleep(duration_s)
        res["transport"] = "panel"
        return res

    print_log(f"actuate_module: unknown transport {transport!r}")
    return {"success": False, "reason": "unknown_transport"}
