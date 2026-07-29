from protocol_schema import SkillObject

from .modules import (
    ask_user_slack,
    is_sim_mode,
    pause_for_user,
    print_log,
)

# Confirmation prompt: button label shown to the operator -> value returned.
CONFIRM_OPTIONS = {"Yes, it's unsealed": "ok", "No, still sealed": "retry"}
# How long to wait for the operator to answer the confirmation before defaulting.
CONFIRM_TIMEOUT_S = 1800.0


def plate_unseal(plate: SkillObject):
    """Pause for the operator to manually unseal a plate, then confirm before continuing.

    A manual step — it moves nothing. Pings the operator, pauses the run (the app
    shows a Resume button), and blocks until they resume. On resume it asks them to
    confirm the seal is off; if they answer "no" it re-pauses and asks again, so the
    workflow only continues once the operator has confirmed the plate is unsealed.
    A cancel while paused propagates out as usual (not swallowed) so the run stops.

    In simulation this is a no-op (logs and returns success) so a sim run of the
    workflow does not hang waiting on a human or ping a real operator — the manual
    unseal only matters on real hardware.

    Args:
        plate: The sealed plate the operator needs to unseal.
    """
    print_log(runlog=True, runlog_type="step_start")

    if is_sim_mode():
        print_log(f"plate_unseal: sim mode — skipping the manual unseal pause for {plate.id}.")
        return {"success": True}

    print_log(f"plate_unseal: waiting for the operator to unseal plate {plate.id}.")

    # Pause -> operator physically unseals and resumes -> confirm. Loop until the
    # operator confirms the seal is off (a "no" or a timeout re-pauses).
    while True:
        pause_for_user(
            "Please manually remove the seal from the plate, then click Resume."
        )
        choice = ask_user_slack(
            "Is the plate fully unsealed and ready to continue?",
            CONFIRM_OPTIONS,
            timeout_s=CONFIRM_TIMEOUT_S,
            default="retry",
        )
        if choice == "ok":
            break
        print_log("plate_unseal: operator reports the plate is still sealed — pausing again.")

    print_log("plate_unseal: operator confirmed the plate is unsealed; continuing.")
    return {"success": True}
