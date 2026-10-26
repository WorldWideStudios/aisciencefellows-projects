from baebugs.variable_aperture import SlotPair, analog_objects, passes, run, scad


def test_geometry():
    p = SlotPair()
    assert p.width(p.offset_for(2.5)) == 2.5 and p.steps_for(6.0) == 0
    assert p.resolution_mm < 0.001
    sq = SlotPair(mode="square")
    assert sq.travel_for(3.0) > SlotPair().travel_for(3.0)          # diagonal travel is sqrt2 longer


def test_modes_sort_differently():
    noodle = (20.0, 6.0, 1.0)                                       # long, wide, thin
    assert passes(noodle, 1.5, 19.05, mode="slot") and not passes(noodle, 1.5, 19.05, mode="square")


def test_run_accounts_for_every_specimen_and_records_breaks():
    objs = analog_objects()
    r = run(objs, [6, 3, 1.5], pair=SlotPair(mode="square"))
    assert r["status"] == "COMPLETED" and r["accounted"] and len(r["steps"]) == 3
    r2 = run(objs, [6, 3, 1.5], actuate_with_load=True)              # plates move with specimens on them
    assert r2["status"] == "STOPPED_AT_BREAK_POINT" and "shear" in r2["steps"][-1]["result"]
    r3 = run(objs, [6, 3, 1.5], measure=lambda w: w + 0.3)          # camera says the opening is off
    assert r3["break_at"] == 0 and "measured" in r3["steps"][-1]["result"]


def test_scad():
    assert "slot_plate" in scad() and "offset" in scad()
