"""Tests for the plate and flex command-line tools."""

import json

import pytest
from typer.testing import CliRunner

from cli.flex import app as flex_app
from cli.plate import app as plate_app
from planning import example_layout

runner = CliRunner()


@pytest.fixture
def layout_file(tmp_path):
    path = tmp_path / "plate.json"
    example_layout().save_json(path)
    return path


@pytest.fixture
def runs_dir(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    monkeypatch.setattr("run_store.RUNS_DIR", runs)
    return runs


def test_plate_check_example_passes():
    result = runner.invoke(plate_app, ["check"])
    assert result.exit_code == 0, result.output
    assert "PASSED" in result.output


def test_plate_protocol_writes_file_and_tube_map(layout_file, tmp_path, runs_dir):
    out = tmp_path / "out.py"
    result = runner.invoke(plate_app, ["protocol", str(layout_file), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert "capture_image" in out.read_text()
    assert "A1: Erastin" in result.output


def test_plate_simulate(layout_file, tmp_path, runs_dir):
    out = tmp_path / "out.py"
    runner.invoke(plate_app, ["protocol", str(layout_file), "-o", str(out)])
    result = runner.invoke(plate_app, ["simulate", str(out)])
    assert result.exit_code == 0, result.output
    assert "Simulation OK" in result.output


def test_flex_demo_mock_leaves_run_files(layout_file, runs_dir):
    result = runner.invoke(flex_app, ["demo", str(layout_file), "--mock"])
    assert result.exit_code == 0, result.output
    folder = runs_dir / "example-screen"
    for name in ("before.jpg", "after.jpg", "protocol.py", "layout.json", "run.json"):
        assert (folder / name).is_file(), name
    assert json.loads((folder / "run.json").read_text())["status"] == "succeeded"


def test_flex_health_unreachable_is_one_line_error():
    result = runner.invoke(flex_app, ["health", "--host", "127.0.0.1", "--port", "1"])
    assert result.exit_code == 2
    assert result.output.startswith("Error: Can't reach the Flex at 127.0.0.1:1")
    assert "Traceback" not in result.output
