import shutil
import subprocess

import pytest

from baebugs.opentrons_parts import SBS, O, labware_defs, parts
from baebugs.print_parts import to_trimesh


def test_deck_parts_fit_the_slot_and_are_watertight():
    for name, m in parts().items():
        t = to_trimesh(m)
        assert t.is_watertight, name
        dx, dy, _ = t.bounds[1] - t.bounds[0]
        if name != "ot_mini_trommel_drum":
            assert abs(dx - SBS[0]) < 0.01 and abs(dy - SBS[1]) < 0.01, name
    assert O["axis_z"] - O["drum_od"] / 2 > O["well_depth"] + 2          # drum clears the bins
    from manifold3d import Manifold
    hz = O["skirt_h"] + O["plate_t"]
    probe = Manifold.cube([2, 2, 0.5]).translate([SBS[0] / 2 - 1, SBS[1] / 2 - 7, hz - 3.6])
    assert (parts()["ot_handoff_plate"] ^ probe).volume() > 1.9          # socket has a floor (not a through-hole)


def test_labware_definitions_declare_flat_adapter_stacking():
    for d in labware_defs().values():
        assert d["dimensions"]["xDimension"] == SBS[0]
        assert "opentrons_universal_flat_adapter" in d["stackingOffsetWithLabware"]


SIM = shutil.which("opentrons_simulate")


@pytest.mark.skipif(not SIM, reason="opentrons not installed in this environment")
def test_protocol_simulates():
    r = subprocess.run([SIM, "-L", "opentrons/labware", "opentrons/protocols/baebugs_flex_line.py"], capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr[-500:]
