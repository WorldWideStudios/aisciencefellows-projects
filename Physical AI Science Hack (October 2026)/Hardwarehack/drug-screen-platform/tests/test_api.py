"""Tests for the loopback FastAPI backend."""

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from planning import example_layout


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("run_store.RUNS_DIR", tmp_path / "runs")
    monkeypatch.delenv("FLEX_HOST", raising=False)
    monkeypatch.delenv("FLEX_MOCK", raising=False)
    return TestClient(create_app(), base_url="http://127.0.0.1:8000")


def _layout() -> dict:
    return example_layout().to_dict()


def test_formats(client):
    formats = {f["name"]: f for f in client.get("/formats").json()}
    assert formats["96-well"]["opentrons_load_name"] == "corning_96_wellplate_360ul_flat"
    assert formats["1536-well"]["flex_note"]


def test_layout_save_list_load(client):
    assert client.put("/layouts/Example screen", json=_layout()).status_code == 200
    assert client.get("/layouts").json() == [{"slug": "example-screen", "name": "Example screen"}]
    assert client.get("/layouts/example-screen").json()["name"] == "Example screen"
    assert client.get("/layouts/missing").status_code == 404


def test_plan_example_passes(client):
    body = client.post("/plan", json={"layout": _layout()}).json()
    assert body["check"]["passed"] is True
    assert len(body["plan"]["transfers"]) == 128
    assert body["volume_ul"] == 100
    assert any("Erastin" in line for line in body["materials"])


def test_plan_invalid_settings_is_422(client):
    layout = _layout()
    layout["pipetting"] = {"intermediate_transfer_ul": 500}
    response = client.post("/plan", json={"layout": layout})
    assert response.status_code == 422
    assert "Intermediate transfer" in response.json()["detail"]


def test_transfers_csv(client):
    response = client.post("/plan/transfers.csv", json={"layout": _layout()})
    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.startswith("step,phase")


def test_protocol_generates_and_simulates(client):
    body = client.post("/protocol", json={"layout": _layout()}).json()
    assert '"apiLevel": "2.30"' in body["protocol"]
    assert body["simulation"]["ok"] is True
    assert body["tubes"]["Erastin"] == "A1"


def test_mock_robot_snapshot_and_run(client):
    assert client.put("/robot/config", json={"host": "", "port": 31950, "mock": True}).status_code == 200
    assert client.get("/robot/health").json()["name"] == "mock-flex"
    client.post("/protocol", json={"layout": _layout()})
    url = client.post("/robot/snapshot", json={"plate": "Example screen", "tag": "before"}).json()["url"]
    image = client.get(url)
    assert image.headers["content-type"] == "image/jpeg"
    run_id = client.post("/robot/runs", json={"plate": "Example screen"}).json()["run_id"]
    assert client.get(f"/robot/runs/{run_id}").json()["status"] == "succeeded"


def test_unreachable_robot_is_502(client):
    client.put("/robot/config", json={"host": "127.0.0.1", "port": 1, "mock": False})
    response = client.get("/robot/health")
    assert response.status_code == 502
    assert "127.0.0.1:1" in response.json()["detail"]


def test_no_robot_configured_is_502(client):
    assert client.get("/robot/health").status_code == 502


def test_bad_snapshot_tag_rejected(client):
    client.put("/robot/config", json={"host": "", "port": 31950, "mock": True})
    assert client.post("/robot/snapshot", json={"plate": "x", "tag": "../evil"}).status_code == 422


def test_cors_only_for_local_ui(client):
    good = client.options("/formats", headers={"Origin": "http://127.0.0.1:3000",
                                               "Access-Control-Request-Method": "GET"})
    assert good.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
    evil = client.options("/formats", headers={"Origin": "http://evil.com",
                                               "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in evil.headers


def test_foreign_host_rejected(client):
    """DNS rebinding: a page on evil.com resolving to 127.0.0.1 sends Host: evil.com."""
    assert client.get("/formats", headers={"Host": "evil.com"}).status_code == 400
    # Same attack through the Next.js proxy, which rewrites Host but forwards the original.
    assert client.get("/formats", headers={"X-Forwarded-Host": "evil.com:3000"}).status_code == 400
    assert client.get("/formats", headers={"X-Forwarded-Host": "127.0.0.1:3000"}).status_code == 200
    # A proxy that appends instead of replacing must not let a spoofed first entry through.
    assert client.get("/formats", headers={"X-Forwarded-Host": "localhost, evil.com:3000"}).status_code == 400


def test_cross_site_post_rejected(client):
    client.put("/robot/config", json={"host": "", "port": 31950, "mock": True})
    for headers in ({"Origin": "http://evil.com"}, {"Sec-Fetch-Site": "cross-site"}):
        response = client.post("/robot/runs/mock-run/play", headers=headers)
        assert response.status_code == 403, headers
    assert client.post("/robot/runs/mock-run/play",
                       headers={"Origin": "http://127.0.0.1:3000", "Sec-Fetch-Site": "same-origin"}).status_code == 200


def test_robot_host_must_be_a_plain_host(client):
    for host in ("evil.com/x", "a@b", "http://10.0.0.1", "10.0.0.1:80", "a b"):
        assert client.put("/robot/config", json={"host": host, "port": 31950}).status_code == 422, host
    assert client.put("/robot/config", json={"host": "192.168.0.42", "port": 31950}).status_code == 200
    assert client.put("/robot/config", json={"host": "opentrons-flex.local", "port": 31950}).status_code == 200


def test_run_id_validated(client):
    client.put("/robot/config", json={"host": "", "port": 31950, "mock": True})
    assert client.get("/robot/runs/..%2Fhealth").status_code in (404, 405, 422)
    assert client.get("/robot/runs/a.b").status_code == 422


def test_extra_ui_origin_only_on_loopback(monkeypatch):
    import importlib

    import api.app as app_module

    monkeypatch.setenv("UI_ORIGIN", "http://127.0.0.1:3001")
    assert "http://127.0.0.1:3001" in importlib.reload(app_module).LOCAL_ORIGINS
    monkeypatch.setenv("UI_ORIGIN", "http://evil.com:3001")
    assert "http://evil.com:3001" not in importlib.reload(app_module).LOCAL_ORIGINS
    monkeypatch.delenv("UI_ORIGIN")
    importlib.reload(app_module)
