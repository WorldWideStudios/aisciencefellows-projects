import time

from execution.execution_functions import is_sim_mode
import tinytuya

# Zeon Internal Science Gateway — parent of the Zigbee fingerbots / switches
GATEWAY_ID = "eb285ec4c33852d67cnupg"
GATEWAY_KEY = "'~R9$FiU^J2E.R2="
GATEWAY_IP = "192.168.1.199"

SWITCH_CID = "a4c138e460a338a3"

DP_SWITCH = 1


def _tuya_press(cid: str) -> None:
    """Click one Zigbee fingerbot once (flip switch_1 to a real new value)."""
    device = tinytuya.Device(GATEWAY_ID, GATEWAY_IP, GATEWAY_KEY, version=3.4)
    device.set_socketPersistent(True)
    device.set_socketTimeout(8)
    device.cid = cid
    try:
        status = device.status()
        dps = status.get("dps") if isinstance(status, dict) else None
        current = dps.get(str(DP_SWITCH)) if isinstance(dps, dict) else None
        target = (not current) if isinstance(current, bool) else True

        result = device.set_value(DP_SWITCH, target)
        time.sleep(2.5)

        echoed = result.get("dps") if isinstance(result, dict) else None
        if isinstance(echoed, dict) and echoed.get(str(DP_SWITCH)) == target:
            print(f"platemax seal press: CONFIRMED switch_1 -> {target}")
        else:
            print(f"platemax seal press: NO ACK (sent switch_1 -> {target}); reply={result!r}")
    finally:
        device.close()


def platesealer_platemax_seal():
    """Press the platemax plate sealer's seal button once."""
    if not is_sim_mode():
        _tuya_press(SWITCH_CID)

    return {"success": True}
