"""Tests for the Flex HTTP client against a mocked transport."""

import json

import httpx
import pytest

from flex_client import FlexClient, FlexError, MockFlexClient, client_from_env


def _client(handler) -> FlexClient:
    return FlexClient("10.0.0.5", transport=httpx.MockTransport(handler))


def test_version_header_on_every_request():
    seen = []

    def handler(request):
        seen.append(request.headers.get("Opentrons-Version"))
        return httpx.Response(200, json={"name": "flex"})

    _client(handler).health()
    assert seen == ["*"]


def test_upload_create_play(tmp_path):
    protocol = tmp_path / "protocol.py"
    protocol.write_text("requirements = {}")
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path, request.content))
        if request.url.path == "/protocols":
            assert b'name="files"; filename="protocol.py"' in request.content
            return httpx.Response(201, json={"data": {"id": "p1"}})
        if request.url.path == "/runs":
            assert json.loads(request.content) == {"data": {"protocolId": "p1"}}
            return httpx.Response(201, json={"data": {"id": "r1"}})
        return httpx.Response(201, json={"data": {}})

    client = _client(handler)
    assert client.upload_protocol(protocol) == "p1"
    assert client.create_run("p1") == "r1"
    client.action("r1", "play")
    assert calls[-1][:2] == ("POST", "/runs/r1/actions")
    assert json.loads(calls[-1][2]) == {"data": {"actionType": "play"}}


def test_snapshot_falls_back_to_picture():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        if request.url.path == "/camera/capturePreviewImage":
            return httpx.Response(404, json={"errors": [{"detail": "not found"}]})
        return httpx.Response(200, content=b"\xff\xd8jpeg\xff\xd9", headers={"content-type": "image/jpeg"})

    assert _client(handler).snapshot() == b"\xff\xd8jpeg\xff\xd9"
    assert paths == ["/camera/capturePreviewImage", "/camera/picture"]


def test_unreachable_robot_names_host():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(FlexError, match="10.0.0.5:31950"):
        _client(handler).health()


def test_server_error_detail_is_surfaced():
    def handler(request):
        return httpx.Response(500, json={"errors": [{"detail": "boom"}]})

    with pytest.raises(FlexError, match="boom"):
        _client(handler).health()


def test_wait_until_done_reports_progress():
    statuses = iter(["running", "running", "succeeded"])

    def handler(request):
        return httpx.Response(200, json={"data": {"id": "r1", "status": next(statuses)}})

    seen = []
    final = _client(handler).wait_until_done("r1", on_progress=lambda d: seen.append(d["status"]), poll_s=0)
    assert final["status"] == "succeeded"
    assert seen == ["running", "running", "succeeded"]


def test_mock_client_runs_and_snapshots(tmp_path):
    client = MockFlexClient()
    assert client.health()["name"] == "mock-flex"
    run_id = client.create_run(client.upload_protocol(tmp_path / "p.py"))
    client.action(run_id, "play")
    assert client.wait_until_done(run_id, poll_s=0)["status"] == "succeeded"
    image = client.snapshot()
    assert image[:2] == b"\xff\xd8" and image[-2:] == b"\xff\xd9"


def test_client_from_env(monkeypatch):
    monkeypatch.delenv("FLEX_HOST", raising=False)
    monkeypatch.delenv("FLEX_MOCK", raising=False)
    with pytest.raises(FlexError, match="FLEX_HOST"):
        client_from_env()
    assert isinstance(client_from_env(mock=True), MockFlexClient)
    monkeypatch.setenv("FLEX_HOST", "10.0.0.9")
    monkeypatch.setenv("FLEX_PORT", "1234")
    client = client_from_env()
    assert (client.host, client.port) == ("10.0.0.9", 1234)
