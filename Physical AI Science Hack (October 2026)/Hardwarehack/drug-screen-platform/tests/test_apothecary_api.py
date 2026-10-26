"""Tests for the concoction console API (mock robot)."""

import pytest
from fastapi.testclient import TestClient

from api.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("run_store.RUNS_DIR", tmp_path / "runs")
    monkeypatch.setenv("FLEX_MOCK", "1")
    return TestClient(create_app(), base_url="http://127.0.0.1:8000")


ORDER = {"plate": "Batch 1", "recipes": [
    {"column": 1, "name": "Cisplatin in saline", "ingredients": [{"trough": 1, "volume_ul": 40}, {"trough": 3, "volume_ul": 10}]},
    {"column": 2, "name": "Doxorubicin in D5W", "ingredients": [{"trough": 2, "volume_ul": 120}]},
]}


def test_initial_state(client):
    state = client.get("/apothecary/state", params={"plate": "Batch 1"}).json()
    assert len(state["troughs"]) == 12
    assert state["troughs"][0] == {"trough": 1, "name": "0.9% Saline", "color": state["troughs"][0]["color"], "volume_ul": None}
    assert state["tips"] == {"small_next": 1, "large_next": 1, "small_left": 12, "large_left": 12}
    assert state["columns"] == {} and state["robot"]["mock"] is True


def test_rename_and_fill_troughs(client):
    troughs = client.get("/apothecary/state").json()["troughs"]
    troughs[0].update(name="Saline", volume_ul=12000)
    saved = client.put("/apothecary/troughs", json=troughs).json()
    assert saved[0]["name"] == "Saline" and saved[0]["volume_ul"] == 12000
    assert client.put("/apothecary/troughs", json=troughs[:3]).status_code == 422


def test_plan_reports_problems_and_simulates_valid_orders(client):
    plan = client.post("/apothecary/plan", json=ORDER).json()
    assert plan["problems"] == [] and plan["simulation"]["ok"] is True
    assert plan["summary"]["small_tips"] == 2 and plan["summary"]["large_tips"] == 1
    bad = {"plate": "Batch 1", "recipes": [{"column": 1, "ingredients": [{"trough": 1, "volume_ul": 250}]}]}
    plan = client.post("/apothecary/plan", json=bad).json()
    assert any("more than a well holds" in p for p in plan["problems"]) and plan["simulation"] is None


def test_brew_runs_and_records(client):
    troughs = client.get("/apothecary/state").json()["troughs"]
    troughs[0]["volume_ul"] = 1000
    client.put("/apothecary/troughs", json=troughs)
    brew = client.post("/apothecary/brew", json=ORDER)
    assert brew.status_code == 200, brew.text
    assert brew.json()["run_id"] == "mock-run"
    state = client.get("/apothecary/state", params={"plate": "Batch 1"}).json()
    assert state["tips"]["small_next"] == 3 and state["tips"]["large_next"] == 2
    assert state["columns"]["1"]["name"] == "Cisplatin in saline"
    assert state["troughs"][0]["volume_ul"] == 1000 - 8 * 40
    again = client.post("/apothecary/brew", json=ORDER)
    assert again.status_code == 422 and "already holds a concoction" in again.json()["detail"]


def test_new_plate_and_tip_refill(client):
    client.post("/apothecary/brew", json=ORDER)
    assert client.post("/apothecary/plates/Batch 1/clear").json()["columns"] == {}
    tips = client.post("/apothecary/tips-refilled").json()["tips"]
    assert tips["small_next"] == 1 and tips["large_next"] == 1


def test_real_robot_brew_needs_calibration(client, monkeypatch):
    client.put("/robot/config", json={"host": "10.0.0.5", "port": 31950, "mock": False})
    response = client.post("/apothecary/brew", json=ORDER)
    assert response.status_code == 422 and "calibrate" in response.json()["detail"]


def test_troughs_get_themed_default_names(client):
    names = [t["name"] for t in client.get("/apothecary/state").json()["troughs"]]
    assert len(set(names)) == 12
    assert not any(name.startswith("Trough ") for name in names)
    assert all(len(name) <= 40 for name in names)


def test_old_default_names_upgrade_but_typed_names_stay(client):
    import apothecary_state

    state = apothecary_state.load()
    state["troughs"][0]["name"] = "Trough 1"            # placeholder saved by an earlier version
    state["troughs"][3]["name"] = "Dorwinion Red"       # Middle-earth default from an earlier version
    state["troughs"][1]["name"] = "My stock A"          # typed by someone
    apothecary_state.save(state)
    troughs = client.get("/apothecary/state").json()["troughs"]
    assert troughs[0]["name"] == "0.9% Saline"
    assert troughs[3]["name"] == "Doxorubicin"
    assert troughs[1]["name"] == "My stock A"


def test_trough_names_are_oncology_drugs_and_diluents():
    import apothecary_state

    names = apothecary_state.DEFAULT_NAMES
    for expected in ("0.9% Saline", "5% Dextrose (D5W)", "DMSO vehicle", "Doxorubicin", "Paclitaxel", "Cisplatin"):
        assert expected in names
