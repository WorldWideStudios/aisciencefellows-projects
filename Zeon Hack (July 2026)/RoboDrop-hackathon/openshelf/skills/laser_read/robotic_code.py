import time

import requests

from .modules import is_sim_mode, print_log

# LASER_HOST = "http://laser.local"
LASER_HOST = "http://192.168.0.140"
TIMEOUT_S = 2.0
READ_COUNT = 10
SAMPLE_DELAY_S = 0.5

SIM_VALUE_PER_SAMPLE = 20000 # above the 20000 tip-present threshold


def _fetch_laser_status() -> dict:
    r = requests.get(f"{LASER_HOST}/api/status", timeout=TIMEOUT_S)
    r.raise_for_status()
    return r.json()


def laser_read():
    if is_sim_mode():
        values = [SIM_VALUE_PER_SAMPLE] * READ_COUNT
        total = sum(values)
        print_log(f"Sim mode: skipping laser HTTP read, returning sum={total} from {values}")
        return {
            "success": True,
            "value": total,
            "values": values,
            "detected": True,
            "threshold": 20000,
            "direction": "above",
            "t": time.time(),
        }

    def _failure_result():
        return {
            "success": False,
            "value": 0,
            "values": [],
            "detected": False,
            "threshold": None,
            "direction": None,
            "t": time.time(),
        }

    try:
        values = []
        last_status = None
        for i in range(READ_COUNT):
            if i > 0:
                time.sleep(SAMPLE_DELAY_S)
            try:
                status = _fetch_laser_status()
            except Exception as e:
                print_log(f"laser_read: sample {i} failed ({type(e).__name__}: {e}); skipping")
                continue
            last_status = status
            values.append(status["value"])

        if last_status is None:
            print_log("laser_read: all samples failed; returning failure result")
            return _failure_result()

        total = sum(values)
        threshold = last_status["threshold"]
        direction = last_status["direction"]
        detected = (total > threshold) if direction == "above" else (total < threshold)
        print_log(f"laser_read: samples={values} sum={total} threshold={threshold} detected={detected}")
        return {
            "success": True,
            "value": total,
            "values": values,
            "detected": detected,
            "threshold": threshold,
            "direction": direction,
            "t": last_status["t"],
        }
    except Exception as e:
        print_log(f"laser_read: unexpected error ({type(e).__name__}: {e}); returning failure result")
        return _failure_result()
