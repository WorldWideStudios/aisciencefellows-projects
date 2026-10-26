import pytest

from baebugs.inserts import DESIGNS, Registry


def test_ladder_and_qualification(tmp_path):
    r = Registry(tmp_path / "reg.jsonl")
    rec = r.register("C-HEX-2.5AF", "BB-0001", "agent:claude")
    sid = rec["serial_id"]
    assert r.status(sid) == "CONCEPT"
    with pytest.raises(ValueError):
        r.advance(sid, "MEASURED", "x")                                    # cannot skip RECEIVED
    r.advance(sid, "RECEIVED", "human:byron", {"vendor": "tbd"})
    r.advance(sid, "MEASURED", "human:byron", {"measured_aperture_mm": 2.62, "nominal_aperture_mm": 2.5})
    with pytest.raises(ValueError):                                        # 0.12 mm off and no damage assessment
        r.advance(sid, "QUALIFIED", "human:byron", {"deburred": True, "cleaning_compatibility": "70% EtOH ok"})
    r.log_event(sid, "cleaned", "human:byron", {"agent": "water rinse"})
    assert len(r.history(sid)) == 4 and r.log.verify()[0]
    with pytest.raises(ValueError):
        r.register("C-HEX-2.5AF", "BB-0001", "agent:claude")              # serial reuse refused
    assert set(DESIGNS) >= {"C-HEX-2.5AF", "D-MESH-1.0", "D-MESH-2.0", "V-SQUARE-0-6"}
