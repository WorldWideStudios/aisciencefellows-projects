from execution.execution_functions import print_log


def put_on_top():
    """Placeholder for replacing the top."""
    print_log(runlog=True, runlog_type="step_start")
    print_log("PLACEHOLDER put_on_top")
    return {"success": True, "placeholder": True}
