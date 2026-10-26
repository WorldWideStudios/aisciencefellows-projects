"""Tests for the 8-channel medium fill protocol and its position bookkeeping."""

import io
import json
from pathlib import Path

import pytest
from opentrons.simulate import simulate
from typer.testing import CliRunner

from cli.flex import app as flex_app
from medium_fill import POSITIONS, protocol_source, well_for_position

runner = CliRunner()


def test_one_position_per_column_of_the_96_well_plate():
    assert POSITIONS == 12
    assert [well_for_position(p) for p in (1, 2, 12)] == ["A1", "A2", "A12"]
    with pytest.raises(ValueError):
        well_for_position(13)


@pytest.mark.parametrize("position", [1, 2, 12])
def test_protocol_simulates(position):
    log, _ = simulate(io.StringIO(protocol_source(position=position, volume_ul=50)), "medium_fill.py")
    text = "\n".join(entry["payload"]["text"] for entry in log)
    assert "Picking up tip from A1 of Opentrons Flex 96 Filter Tip Rack 50 µL on slot A2" in text
    assert "Aspirating 50.0 uL from A1 of NEST 12 Well Reservoir 15 mL on slot B1" in text
    assert f"Dispensing 50.0 uL into {well_for_position(position)} of Armadillo 96 Well Plate 200 µL PCR Full Skirt on slot B3" in text
    assert "Dropping tip into Trash Bin on slot A3" in text
    source = protocol_source(position=position, volume_ul=50)
    assert source.index("protocol.home()") < source.index("pipette.drop_tip()")  # home, then eject


def test_tip_column_is_used():
    """Each run takes the next column of tips, so 12 runs use one full rack."""
    log, _ = simulate(io.StringIO(protocol_source(position=1, volume_ul=50, tip_column=3)), "medium_fill.py")
    text = "\n".join(entry["payload"]["text"] for entry in log)
    assert "Picking up tip from A3 of Opentrons Flex 96 Filter Tip Rack 50 µL" in text


def test_volume_limits():
    with pytest.raises(ValueError, match="50 µL"):
        protocol_source(position=1, volume_ul=60)
    with pytest.raises(ValueError, match="5 µL"):
        protocol_source(position=1, volume_ul=2)


def _calibrated(tmp_path, monkeypatch):
    import labware_offsets

    monkeypatch.setattr("run_store.RUNS_DIR", tmp_path)
    labware_offsets.save_offset("opentrons/armadillo_96_wellplate_200ul_pcr_full_skirt/3", "B3", {"x": 0, "y": 0, "z": 40})


def test_fill_command_tracks_next_position(tmp_path, monkeypatch):
    _calibrated(tmp_path, monkeypatch)
    for expected_well, expected_tips in (("A1", 1), ("A2", 2)):
        result = runner.invoke(flex_app, ["fill", "--plate", "Medium test", "--mock", "--yes"])
        assert result.exit_code == 0, result.output
        assert f"position {expected_well}" in result.output
        assert f"tip column {expected_tips}" in result.output
    fills = json.loads((tmp_path / "medium-test" / "fills.json").read_text())
    assert [f["well"] for f in fills] == ["A1", "A2"]
    assert [f["tip_column"] for f in fills] == [1, 2]
    assert (tmp_path / "medium-test" / "medium_fill.py").is_file()


def test_fill_command_refuses_when_plate_full(tmp_path, monkeypatch):
    _calibrated(tmp_path, monkeypatch)
    folder = tmp_path / "full"
    folder.mkdir()
    (folder / "fills.json").write_text(json.dumps([{"position": p} for p in range(1, 13)]))
    result = runner.invoke(flex_app, ["fill", "--plate", "Full", "--mock", "--yes"])
    assert result.exit_code == 2
    assert "full" in result.output.lower()


def test_tip_columns_wrap_after_a_full_rack():
    with pytest.raises(ValueError, match="1-12"):
        protocol_source(position=1, volume_ul=50, tip_column=13)
