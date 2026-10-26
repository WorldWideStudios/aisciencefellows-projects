"""
HTTP client for the Opentrons Flex robot server (port 31950).

Covers what the demo needs: health, protocol upload, run control, and a
camera snapshot. ``MockFlexClient`` has the same methods and needs no robot.
Request shapes follow the robot-server source; check them against
``http://<robot>:31950/openapi.json`` on robot day.
"""

import base64
import os
import time
from pathlib import Path
from typing import Callable, Literal, Optional

import httpx

DEFAULT_PORT = 31950
TERMINAL_STATUSES = {"succeeded", "failed", "stopped"}
RunAction = Literal["play", "pause", "stop"]


class FlexError(RuntimeError):
    """The robot couldn't be reached or refused a request."""


class FlexClient:
    """
    Talk to one Flex over its HTTP API.

    Parameters
    ----------
    host : str
        Robot IP address or host name.
    port : int, default=31950
        Robot server port.
    transport : httpx.BaseTransport, optional
        Custom transport (tests use httpx.MockTransport).
    timeout : float, default=30
        Seconds per request.
    """

    def __init__(self, host: str, port: int = DEFAULT_PORT,
                 transport: Optional[httpx.BaseTransport] = None, timeout: float = 30) -> None:
        self.host = host
        self.port = port
        self._http = httpx.Client(
            base_url=f"http://{host}:{port}",
            headers={"Opentrons-Version": "*"},
            transport=transport,
            timeout=timeout,
        )

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise FlexError(f"Can't reach the Flex at {self.host}:{self.port}: {error}") from error
        if response.status_code >= 400:
            raise FlexError(f"Flex returned {response.status_code} for {method} {path}: {_detail(response)}")
        return response

    def health(self) -> dict:
        """Robot name, model and software versions."""
        return self._request("GET", "/health").json()

    def upload_protocol(self, path: Path) -> str:
        """Upload a protocol file and return its protocol id."""
        path = Path(path)
        try:
            content = path.read_bytes()
        except OSError as error:
            raise FlexError(f"Could not read {path}: {error}") from error
        response = self._request("POST", "/protocols", files={"files": (path.name, content, "text/x-python")})
        return response.json()["data"]["id"]

    def create_run(self, protocol_id: str, labware_offsets: Optional[list[dict]] = None) -> str:
        """Create a run for an uploaded protocol (with optional labware offsets) and return its id."""
        data: dict = {"protocolId": protocol_id}
        if labware_offsets:
            data["labwareOffsets"] = labware_offsets
        response = self._request("POST", "/runs", json={"data": data})
        return response.json()["data"]["id"]

    def start_maintenance(self) -> str:
        """Open a maintenance run (manual control, used for calibration) and return its id."""
        return self._request("POST", "/maintenance_runs", json={"data": {}}).json()["data"]["id"]

    def maintenance_command(self, run_id: str, command_type: str, params: dict) -> dict:
        """Run one command in a maintenance run, wait for it, and return its result."""
        response = self._request(
            "POST", f"/maintenance_runs/{run_id}/commands",
            params={"waitUntilComplete": "true", "timeout": "120000"},
            json={"data": {"commandType": command_type, "params": params, "intent": "setup"}},
            timeout=150,
        )
        data = response.json()["data"]
        if data.get("status") == "failed":
            error = data.get("error") or {}
            raise FlexError(f"{command_type} failed: {error.get('detail') or error}")
        return data.get("result") or {}

    def end_maintenance(self, run_id: str) -> None:
        """Close a maintenance run."""
        self._request("DELETE", f"/maintenance_runs/{run_id}")

    def action(self, run_id: str, action: RunAction) -> None:
        """Play, pause or stop a run."""
        self._request("POST", f"/runs/{run_id}/actions", json={"data": {"actionType": action}})

    def run_status(self, run_id: str) -> dict:
        """The run's data object (status, errors, ...)."""
        return self._request("GET", f"/runs/{run_id}").json()["data"]

    def wait_until_done(self, run_id: str, on_progress: Optional[Callable[[dict], None]] = None,
                        poll_s: float = 2.0) -> dict:
        """Poll the run until it succeeds, fails or is stopped; return its final data."""
        while True:
            data = self.run_status(run_id)
            if on_progress:
                on_progress(data)
            if data.get("status") in TERMINAL_STATUSES:
                return data
            time.sleep(poll_s)

    def snapshot(self) -> bytes:
        """JPEG from the deck camera."""
        try:
            return self._request("POST", "/camera/capturePreviewImage", json={"data": {}}).content
        except FlexError as error:
            if not any(f" {code} " in str(error) for code in (404, 405, 422)):
                raise
        return self._request("POST", "/camera/picture").content


def _detail(response: httpx.Response) -> str:
    """Best human-readable error message from a robot response."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:200] or response.reason_phrase
    errors = body.get("errors") if isinstance(body, dict) else None
    if errors:
        return "; ".join(str(e.get("detail") or e.get("title") or e) for e in errors)
    return str(body.get("message") or body)[:200] if isinstance(body, dict) else str(body)[:200]


_MOCK_JPEG = base64.b64decode("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")


class MockFlexClient:
    """Stand-in robot for rehearsals and tests: every call succeeds instantly."""

    host = "mock"
    port = 0

    def health(self) -> dict:
        return {"name": "mock-flex", "robot_model": "OT-3 Standard", "api_version": "10.1.0"}

    def upload_protocol(self, path: Path) -> str:
        return "mock-protocol"

    def create_run(self, protocol_id: str, labware_offsets: Optional[list[dict]] = None) -> str:
        return "mock-run"

    def action(self, run_id: str, action: RunAction) -> None:
        return None

    def run_status(self, run_id: str) -> dict:
        return {"id": run_id, "status": "succeeded", "errors": []}

    def wait_until_done(self, run_id: str, on_progress: Optional[Callable[[dict], None]] = None,
                        poll_s: float = 2.0) -> dict:
        data = self.run_status(run_id)
        if on_progress:
            on_progress(data)
        return data

    def snapshot(self) -> bytes:
        return _MOCK_JPEG


def client_from_env(mock: bool = False, host: Optional[str] = None,
                    port: Optional[int] = None) -> FlexClient | MockFlexClient:
    """
    Build a client from arguments, falling back to ``FLEX_HOST``, ``FLEX_PORT``, ``FLEX_MOCK``.

    Raises
    ------
    FlexError
        If no host is given and mock mode is off.
    """
    if mock or os.environ.get("FLEX_MOCK") == "1":
        return MockFlexClient()
    host = host or os.environ.get("FLEX_HOST")
    if not host:
        raise FlexError("No robot host: set FLEX_HOST or pass --host (or use --mock).")
    return FlexClient(host, port or int(os.environ.get("FLEX_PORT", DEFAULT_PORT)))
