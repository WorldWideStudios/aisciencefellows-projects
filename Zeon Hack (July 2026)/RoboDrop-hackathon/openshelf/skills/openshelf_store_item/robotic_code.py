import json
import time

import requests

# Embedded "read" mini-skill: used to resolve a name -> real UPCA.
from openshelf_read_storage.robotic_code import openshelf_read_storage
# Embedded "snap" mini-skill: after a confirmed store, place the item into the cabinet.
from snap_into_openshelf.robotic_code import snap_into_openshelf

from .modules import is_sim_mode, print_log

# OpenShelf device API (LAN — same host the read/retrieve skills use).
BASE_URL = "http://192.168.1.16:8000"
TIMEOUT_S = 5.0

# Hardcoded dev credentials (temporary).
LOGIN_EMAIL = "admin@opshelf.com"
LOGIN_PIN = "1234"

# Sim-only: seconds to fake the real cabinet store time (hardware waits for real).
# Mirrors dispense_from_openshelf's SIM_DISPENSE_SECONDS so a sim load "feels" like
# hardware; the real store also takes ~50s.
SIM_STORE_SECONDS = 50


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


def _match_by_name(items: list, name: str) -> list:
    """Case-insensitive substring match on each item's 'name' field."""
    q = name.strip().lower()
    return [it for it in items if q in (it.get("name") or "").lower()]


def _event_matches(ev: dict, command_name: str, upca: str, location) -> bool:
    """Strict match: same command + upca (+ location, if given). The /events stream
    is a broadcast — every client's completions arrive here, so we must NOT act on
    the first 'success' we see."""
    if ev.get("command") != command_name:
        return False
    if str(ev.get("upca")) != str(upca):
        return False
    if location is not None:
        loc = ev.get("location") or {}
        if (loc.get("side"), loc.get("shelf_idx"), loc.get("cell_idx")) != (
            location["side"], location["shelf_idx"], location["cell_idx"]
        ):
            return False
    return True


def _stream_confirms_success(token: str, command_name: str, upca: str, location, timeout_s: float) -> bool:
    """Listen on GET /api/robot/events for a matching *success* event before the
    deadline. Never raises — returns False on timeout / stream drop / no match, so
    the caller falls back to the authoritative DB check."""
    deadline = time.time() + timeout_s
    try:
        resp = requests.get(
            f"{BASE_URL}/api/robot/events",
            headers={"Authorization": f"Bearer {token}"},
            stream=True,
            timeout=(5, timeout_s + 5),
        )
        for raw in resp.iter_lines(decode_unicode=True):
            if time.time() > deadline:
                return False
            if not raw:
                continue
            line = raw.strip()
            if not line.startswith("data:"):
                continue
            try:
                ev = json.loads(line[5:].strip())
            except Exception:
                continue
            if _event_matches(ev, command_name, upca, location):
                return ev.get("message") == "success"
        return False
    except Exception:
        return False


def _db_confirms(token: str, command_name: str, upca: str, location) -> bool:
    """Authoritative fallback — check GET /api/storage/items/{upca}. Reliable even
    if our SSE stream dropped, because the server updates the DB from its own
    internal event consumer. store -> a location was added; retrieve -> the
    location was removed."""
    try:
        r = requests.get(
            f"{BASE_URL}/api/storage/items/{upca}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT_S,
        )
    except Exception:
        return False
    if command_name == "store_item":
        return r.status_code == 200 and len(r.json().get("locations", [])) > 0
    # retrieve_item
    if r.status_code == 404:
        return True
    if r.status_code == 200:
        locs = r.json().get("locations", [])
        return not any(
            (l.get("side"), l.get("shelf_idx"), l.get("cell_idx")) == (
                location["side"], location["shelf_idx"], location["cell_idx"]
            )
            for l in locs
        )
    return False


def _snap_stored() -> None:
    """Embedded visual snap: place the stored item into the cabinet. Best-effort and
    isolated — a snap failure can NEVER affect the store API result."""
    try:
        snap_into_openshelf()
    except Exception as e:
        print_log(f"openshelf_store_item: embedded snap failed (non-fatal): {type(e).__name__}: {e}")


def openshelf_store_item(name: str = "", timeout_s: float = 120):
    """Store an item by NAME via the OpenShelf robot API, blocking until the robot
    actually finishes.

    Resolves the name to its real UPCA via the embedded read skill, POSTs
    store_item (robot auto-assigns the cell), then WAITS for completion: listens
    on /api/robot/events for a matching success event, and on timeout/stream-drop
    falls back to the authoritative DB check (GET /api/storage/items/{upca}).
    Only returns once the store is confirmed (or genuinely failed), so downstream
    nodes run after the robot is done. Sim mode returns canned success immediately
    (robot is disabled in sim — no completion event will ever come).
    """
    print_log(runlog=True, runlog_type="step_start")
    sim = is_sim_mode()

    def _fail(error: str, **extra) -> dict:
        print_log(f"openshelf_store_item failed: {error}")
        return {"success": False, "simulated": sim, "command": "store_item", "name": name, "error": error, **extra, "t": time.time()}

    if not name.strip():
        return _fail("provide an item name")

    # Embedded read → resolve name -> upca.
    read = openshelf_read_storage()
    items = read.get("items", [])
    matches = _match_by_name(items, name)
    print_log(f"store name={name!r} -> {len(matches)} match(es)")

    if len(matches) == 0:
        return _fail(f"no item matching name '{name}'")
    if len(matches) > 1:
        options = [{"name": m.get("name"), "upca": m.get("upca")} for m in matches]
        return _fail(f"multiple items match '{name}' — be more specific", matches=options)

    item = matches[0]
    upca = item.get("upca")
    if not upca:
        return _fail(f"item '{item.get('name')}' has no upca")
    print_log(f"resolved name={name!r} -> upca={upca}")

    if sim:
        # Robot is disabled in sim, so no completion event will ever come — skip the
        # events stream and instead sleep SIM_STORE_SECONDS to mimic the real cabinet's
        # store time, so a sim load feels like hardware (mirrors dispense_from_openshelf).
        print_log(f"Sim mode: simulating {SIM_STORE_SECONDS}s cabinet store time")
        time.sleep(SIM_STORE_SECONDS)
        _snap_stored()
        return {"success": True, "simulated": True, "command": "store_item", "name": name, "upca": upca, "t": time.time()}

    # Hardware: login → POST store_item.
    try:
        token = _login()
    except Exception as e:
        return _fail(f"login failed ({type(e).__name__}: {e})", upca=upca)

    command = {"command": "store_item", "item": {"upca": upca}}
    print_log(f"POST {BASE_URL}/api/robot/commands {command}")
    try:
        r = requests.post(
            f"{BASE_URL}/api/robot/commands",
            headers={"Authorization": f"Bearer {token}"},
            json=command,
            timeout=TIMEOUT_S,
        )
    except Exception as e:
        return _fail(f"store command failed ({type(e).__name__}: {e})", upca=upca)
    if r.status_code != 200:
        return _fail(f"store rejected: status={r.status_code} body={r.text[:200]}", upca=upca, status=r.status_code)

    # store_item auto-assigns the cell → we can't match a location; match command+upca only.
    print_log(f"store accepted (200); waiting up to {timeout_s}s for completion...")
    if _stream_confirms_success(token, "store_item", upca, None, timeout_s):
        print_log("store confirmed via events stream")
        _snap_stored()
        return {"success": True, "simulated": False, "command": "store_item", "name": name, "upca": upca, "confirmed_by": "events", "t": time.time()}

    print_log("no matching success event (timeout/drop) — checking DB fallback")
    if _db_confirms(token, "store_item", upca, None):
        print_log("store confirmed via DB (location added)")
        _snap_stored()
        return {"success": True, "simulated": False, "command": "store_item", "name": name, "upca": upca, "confirmed_by": "db", "t": time.time()}

    return _fail("store not confirmed (no success event and DB shows no location)", upca=upca)
