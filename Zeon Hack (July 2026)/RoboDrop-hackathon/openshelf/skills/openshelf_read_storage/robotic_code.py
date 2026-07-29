import time

import requests

from .modules import is_sim_mode, print_log

# OpenShelf device API (LAN — reachable only if the skill runtime shares the
# robot's network; the hardware path pre-flights GET /api/health).
BASE_URL = "http://192.168.1.16:8000"
TIMEOUT_S = 5.0

# Hardcoded dev credentials (temporary).
LOGIN_EMAIL = "admin@opshelf.com"
LOGIN_PIN = "1234"

# --- Canned sim data --------------------------------------------------------
# Mirrors the normalized real shape: each item carries {upca, name, locations[]}
# where each location is {side, shelf_idx, cell_idx}. Like laser_read's SIM
# value, this is the nominal "happy path" that runs without touching the network.
SIM_ITEMS = [
    {"upca": "608611372143", "name": "Sim Item A", "locations": [{"side": "left_module", "shelf_idx": 1, "cell_idx": 0}]},
    {"upca": "012345678905", "name": "Sim Item B", "locations": [{"side": "right_module", "shelf_idx": 0, "cell_idx": 2}]},
]


def _login() -> str:
    """POST credentials and return the access_token. Raises on failure."""
    r = requests.post(
        f"{BASE_URL}/api/auth/login/json",
        json={"email": LOGIN_EMAIL, "pin": LOGIN_PIN},
        timeout=TIMEOUT_S,
    )
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError(f"login returned no access_token (body: {r.text[:200]})")
    return token


def _fetch_items(token: str) -> tuple[list, int]:
    """GET /api/storage/items and return (normalized_items, total). Raises on failure."""
    r = requests.get(
        f"{BASE_URL}/api/storage/items",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_S,
    )
    r.raise_for_status()
    body = r.json()
    items = [
        {
            "upca": it.get("upca"),
            "name": it.get("name"),
            "locations": [
                {"side": loc.get("side"), "shelf_idx": loc.get("shelf_idx"), "cell_idx": loc.get("cell_idx")}
                for loc in it.get("locations", [])
            ],
        }
        for it in body.get("items", [])
    ]
    return items, body.get("total", len(items))


def openshelf_read_storage():
    """Read every storage item and its locations from the OpenShelf device.

    Sim mode: skip all HTTP and return canned items (same shape as the real
    API). Hardware mode: reachability pre-flight (GET /api/health) → login
    (POST /api/auth/login/json) → authenticated GET /api/storage/items,
    normalized to {upca, name, locations:[{side, shelf_idx, cell_idx}]}.
    """
    print_log(runlog=True, runlog_type="step_start")

    if is_sim_mode():
        items = SIM_ITEMS
        print_log(f"Sim mode: skipping storage HTTP read, returning {len(items)} canned items: {items}")
        return {
            "success": True,
            "simulated": True,
            "items": items,
            "count": len(items),
            "t": time.time(),
        }

    def _failure(error: str) -> dict:
        print_log(f"openshelf_read_storage failed: {error}")
        return {
            "success": False,
            "simulated": False,
            "items": [],
            "count": 0,
            "error": error,
            "t": time.time(),
        }

    try:
        requests.get(f"{BASE_URL}/api/health", timeout=TIMEOUT_S).raise_for_status()
    except Exception as e:
        return _failure(f"unreachable: GET /api/health failed ({type(e).__name__}: {e}) — runtime not on robot LAN?")

    try:
        token = _login()
    except Exception as e:
        return _failure(f"login failed ({type(e).__name__}: {e})")

    try:
        items, total = _fetch_items(token)
    except Exception as e:
        return _failure(f"storage read failed ({type(e).__name__}: {e})")

    print_log(f"openshelf_read_storage: read {len(items)} items (total={total})")
    return {
        "success": True,
        "simulated": False,
        "items": items,
        "count": len(items),
        "total": total,
        "t": time.time(),
    }
