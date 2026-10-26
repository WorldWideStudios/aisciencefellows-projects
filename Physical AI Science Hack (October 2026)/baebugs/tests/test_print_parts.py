from baebugs.print_parts import P, parts, to_trimesh


def test_all_parts_watertight_and_sized():
    ps = parts()
    assert len(ps) == 20
    for name, m in ps.items():
        t = to_trimesh(m)
        assert t.is_watertight, name
        assert (t.bounds[1] - t.bounds[0]).max() < 160, name      # fits a 165 mm bed
    v = [to_trimesh(ps[f"trommel_zone_{d:g}mm"]).volume for d in P["zone_holes"]]
    assert v[0] > v[1] > v[2]                                      # bigger holes remove more wall
