"""Tests for jog-based Z calibration, stored offsets, and the uncalibrated-run guard."""

import json

import httpx
import pytest
from typer.testing import CliRunner

import labware_offsets
from cli.flex import app as flex_app
from flex_client import FlexClient

runner = CliRunner()
PLATE_URI = "opentrons/armadillo_96_wellplate_200ul_pcr_full_skirt/3"


@pytest.fixture
def runs(tmp_path, monkeypatch):
    monkeypatch.setattr("run_store.RUNS_DIR", tmp_path)
    return tmp_path


def test_offsets_round_trip_and_replace(runs):
    labware_offsets.save_offset(PLATE_URI, "B3", {"x": 0, "y": 0, "z": 40})
    labware_offsets.save_offset(PLATE_URI, "B3", {"x": 0.5, "y": 0, "z": 41.2})
    assert labware_offsets.find(PLATE_URI, "B3")["vector"] == {"x": 0.5, "y": 0, "z": 41.2}
    assert labware_offsets.for_run() == [{
        "definitionUri": PLATE_URI,
        "locationSequence": [{"kind": "onAddressableArea", "addressableAreaName": "B3"}],
        "vector": {"x": 0.5, "y": 0, "z": 41.2},
    }]


def test_create_run_sends_offsets():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(201, json={"data": {"id": "r1"}})

    client = FlexClient("10.0.0.5", transport=httpx.MockTransport(handler))
    offsets = [{"definitionUri": PLATE_URI, "locationSequence": [], "vector": {"x": 0, "y": 0, "z": 1}}]
    client.create_run("p1", labware_offsets=offsets)
    assert bodies == [{"data": {"protocolId": "p1", "labwareOffsets": offsets}}]


def _robot_recorder():
    """Fake robot that records maintenance commands."""
    commands, deleted = [], []

    def handler(request):
        path = request.url.path
        if request.method == "POST" and path == "/maintenance_runs":
            return httpx.Response(201, json={"data": {"id": "m1"}})
        if request.method == "POST" and path == "/maintenance_runs/m1/commands":
            body = json.loads(request.content)["data"]
            commands.append((body["commandType"], body["params"]))
            assert request.url.params["waitUntilComplete"] == "true"
            result = {"pipetteId": "pip"} if body["commandType"] == "loadPipette" else {"labwareId": f"lw{len(commands)}"}
            return httpx.Response(201, json={"data": {"id": "c", "status": "succeeded", "result": result}})
        if request.method == "DELETE" and path == "/maintenance_runs/m1":
            deleted.append(True)
            return httpx.Response(200, json={"data": {}})
        return httpx.Response(404, json={"errors": [{"detail": f"unexpected {request.method} {path}"}]})

    return handler, commands, deleted


def test_calibrate_jog_saves_offset_and_cleans_up(runs, monkeypatch):
    handler, commands, deleted = _robot_recorder()
    monkeypatch.setattr("cli.flex._client", lambda *a: FlexClient("10.0.0.5", transport=httpx.MockTransport(handler)))
    result = runner.invoke(flex_app, ["calibrate", "--host", "10.0.0.5"], input="d 10\nd 5\nu 1\nx 0.5\nok\ny\n")
    assert result.exit_code == 0, result.output
    saved = labware_offsets.find(PLATE_URI, "B3")
    assert saved["vector"] == {"x": 0.5, "y": 0.0, "z": 66.0}
    kinds = [c[0] for c in commands]
    assert kinds[:5] == ["home", "loadPipette", "loadLabware", "loadLabware", "pickUpTip"]
    # Maintenance commands use the robot's internal name (what /instruments reports), not the
    # protocol API name flex_8channel_1000: the robot answers 422 to that.
    assert commands[1][1] == {"pipetteName": "p1000_multi_flex", "mount": "left"}
    move = next(p for k, p in commands if k == "moveToWell")
    assert move["wellLocation"] == {"origin": "top", "offset": {"x": 0, "y": 0, "z": 80.0}}
    jogs = [(p["axis"], p["distance"]) for k, p in commands if k == "moveRelative"]
    assert jogs[:4] == [("z", -10.0), ("z", -5.0), ("z", 1.0), ("x", 0.5)]
    assert kinds[-2:] == ["dropTip", "home"] and deleted == [True]


def test_calibrate_abort_saves_nothing_but_cleans_up(runs, monkeypatch):
    handler, commands, deleted = _robot_recorder()
    monkeypatch.setattr("cli.flex._client", lambda *a: FlexClient("10.0.0.5", transport=httpx.MockTransport(handler)))
    result = runner.invoke(flex_app, ["calibrate", "--host", "10.0.0.5"], input="d 10\nq\n")
    assert result.exit_code == 1
    assert labware_offsets.find(PLATE_URI, "B3") is None
    assert [c[0] for c in commands][-2:] == ["dropTip", "home"] and deleted == [True]


def test_calibrate_rejects_bad_input_and_huge_steps(runs, monkeypatch):
    handler, commands, _ = _robot_recorder()
    monkeypatch.setattr("cli.flex._client", lambda *a: FlexClient("10.0.0.5", transport=httpx.MockTransport(handler)))
    result = runner.invoke(flex_app, ["calibrate", "--host", "10.0.0.5"], input="down\nd 50\nd abc\nd nan\nq\n")
    assert "Unknown" in result.output and "at most 20 mm" in result.output
    assert result.output.count("Unknown") == 3
    assert not [p for k, p in commands if k == "moveRelative" and p["axis"] == "z" and p["distance"] < 0]


def test_fill_refuses_uncalibrated_plate(runs):
    result = runner.invoke(flex_app, ["fill", "--plate", "P", "--mock", "--yes"])
    assert result.exit_code == 2
    assert "flex calibrate" in result.output


def test_fill_passes_calibration_to_the_run(runs, monkeypatch):
    labware_offsets.save_offset(PLATE_URI, "B3", {"x": 0, "y": 0, "z": 42})
    seen = {}
    from flex_client import MockFlexClient

    original = MockFlexClient.create_run

    def spy(self, protocol_id, labware_offsets=None):
        seen["offsets"] = labware_offsets
        return original(self, protocol_id, labware_offsets)

    monkeypatch.setattr(MockFlexClient, "create_run", spy)
    result = runner.invoke(flex_app, ["fill", "--plate", "P", "--mock", "--yes"])
    assert result.exit_code == 0, result.output
    assert seen["offsets"][0]["vector"]["z"] == 42
