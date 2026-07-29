from execution.execution_functions import print_log


def wait_for_media_refill_request(endpoint_path: str = "/mediaRefill"):
    """Placeholder for an HTTP listener that waits for a media refill request."""
    print_log(runlog=True, runlog_type="step_start")
    print_log(
        f"PLACEHOLDER wait_for_media_refill_request: host endpoint and wait for POST {endpoint_path}"
    )
    return {"success": True, "placeholder": True, "endpoint_path": endpoint_path}
