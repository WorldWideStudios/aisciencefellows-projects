# OpenShelf Cabinet API — Access Guide

The OpenShelf cabinet runs its own REST API over the lab LAN. This is **separate
from the Zeon arm workflow** — it's the cabinet's control server: log in, read
inventory, and command the cabinet to dispense or store items. Everything below
is a plain HTTP call, so a browser or `curl` is enough to try it.

## Where it lives
- **Base URL:** `http://192.168.1.16:8000` (all paths under `/api`).
- It's a **LAN address**, so you have to be on the robot's network to reach it.
- If it stops responding, the IP may have **changed on reboot** — check the
  cabinet's touchscreen under **system information → lan ip** for the current one.
- **Reachability test (no login):** open `http://192.168.1.16:8000/api/health` —
  a healthy cabinet returns `{"status":"ok", ...}`.

## Logging in
- **Credentials (current dev login):** `admin@opshelf.com` / PIN `1234` — admin, full access.
- Get a token: `POST /api/auth/login/json` with body
  `{"email":"admin@opshelf.com","pin":"1234"}` → returns an `access_token`.
- Put it on **every** other request as a header: `Authorization: Bearer <access_token>`.
- Tokens last ~30 min — just log in again if one expires.

## Easiest way in: the built-in API browser
1. Open **`http://192.168.1.16:8000/docs`** — an interactive page listing every
   endpoint, each with a **"Try it out"** button.
2. To unlock the authenticated endpoints there: run `POST /api/auth/login/json`
   with the creds above, copy the `access_token` from the response, click
   **Authorize** (top-right), paste the token, and hit Authorize.
3. You can now click through inventory, the grid, and commands right in the browser.

## The endpoints that matter
| What you want | Call |
|---|---|
| All stored items + where each one is | `GET /api/storage/items` |
| The shelf grid / cell layout + sizes | `GET /api/storage/grid` |
| **Dispense** an item out | `POST /api/robot/commands` → `{"command":"retrieve_item","location":{"side","shelf_idx","cell_idx"}}` |
| **Store** an item (cabinet picks the cell — you can't choose it) | `POST /api/robot/commands` → `{"command":"store_item","item":{"upca":"..."}}` |
| Watch a command finish, live | `GET /api/robot/events` (streams a `success` event when the move completes) |

Items are identified by **`upca`** (their barcode); a stored item's location is
`{side, shelf_idx, cell_idx}` (e.g. `left_module / 0 / 0`).

## One thing to know
A `200` from a robot command means **"accepted," not "finished"** — the arm takes
~50 seconds. To know it actually completed, either watch `/api/robot/events` for a
matching `success`, or re-check `/api/storage/items` and confirm the item's
location changed.

## Heads-up
The cabinet's WiFi is **flaky** — it drops off the network periodically. If a call
fails, it's usually the network (not your request); wait a bit and retry.
