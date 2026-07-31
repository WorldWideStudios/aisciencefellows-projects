import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


class ServiceClientError(RuntimeError):
    pass


class JsonHttpClient:
    def __init__(self, base_url: str, service_name: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: float = 10,
        accept: str = "application/json",
    ) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": accept}
        if body is not None:
            headers["Content-Type"] = "application/json"

        request = Request(
            urljoin(f"{self.base_url}/", path.lstrip("/")),
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ServiceClientError(f"{self.service_name} returned {exc.code} for {method} {path}: {detail}") from exc
        except URLError as exc:
            raise ServiceClientError(f"{self.service_name} request failed for {method} {path}: {exc.reason}") from exc

        return json.loads(text) if text else None


class OpenShelfClient:
    def __init__(
        self,
        api_base_url: str | None = None,
        command_timeout_seconds: float | None = None,
    ) -> None:
        self.http = JsonHttpClient(
            api_base_url or os.getenv("OPENSHELF_API_BASE_URL", "http://192.168.1.16:8080/api"),
            "OpenShelf",
        )
        self.command_timeout_seconds = command_timeout_seconds or float(
            os.getenv("OPENSHELF_COMMAND_TIMEOUT_SECONDS", "120")
        )

    def create_item(self, item: dict[str, object]) -> Any:
        return self.http.request("POST", "/storage/items", item)

    def get_item(self, upca: str) -> Any:
        return self.http.request("GET", f"/storage/items/{upca}")

    def post_command(self, command: dict[str, object]) -> Any:
        return self.http.request("POST", "/robot/commands", command)

    def wait_for_command_completion(self) -> dict[str, Any]:
        deadline = time.time() + self.command_timeout_seconds
        earliest_idle_at = time.time() + 1.5
        observed_work = False

        while time.time() < deadline:
            status = self._read_status_event()
            if self._is_idle(status):
                if observed_work or time.time() >= earliest_idle_at:
                    return status
            else:
                observed_work = True
            time.sleep(1)

        raise ServiceClientError(
            f"OpenShelf command did not complete within {self.command_timeout_seconds:g} seconds"
        )

    def _read_status_event(self) -> dict[str, Any]:
        request = Request(
            urljoin(f"{self.http.base_url}/", "robot/status"),
            headers={"Accept": "text/event-stream"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=10) as response:
                event_lines: list[str] = []
                deadline = time.time() + 10
                while time.time() < deadline:
                    line = response.readline().decode("utf-8", errors="replace").strip()
                    if line == "":
                        if event_lines:
                            data = "\n".join(line[5:].strip() for line in event_lines if line.startswith("data:"))
                            if data:
                                return json.loads(data)
                            event_lines = []
                        continue
                    event_lines.append(line)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ServiceClientError(f"OpenShelf status stream returned {exc.code}: {detail}") from exc
        except URLError as exc:
            raise ServiceClientError(f"OpenShelf status stream failed: {exc.reason}") from exc

        raise ServiceClientError("OpenShelf status stream did not send a robot status event")

    @staticmethod
    def _is_idle(status: dict[str, Any]) -> bool:
        if status.get("running") is True:
            return False
        if status.get("current_command") is not None:
            return False
        queued_operations = status.get("queued_operations")
        if isinstance(queued_operations, list) and len(queued_operations) > 0:
            return False
        return int(status.get("queue_length") or 0) == 0


class RpiMonitoringClient:
    def get_level(self, culture: dict[str, object]) -> Any:
        base_url = f"http://{culture['ip_address']}:{culture['port']}"
        return JsonHttpClient(base_url, "Raspberry Pi").request("GET", "/level", timeout=20)
