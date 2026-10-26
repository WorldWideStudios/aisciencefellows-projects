from baebugs.dataone_adapter import event_fco, load_events, summary
from baebugs.essig_adapter import specimen_context

CSV = """﻿ObjectID,GlobalID,site_ID,observers,email,phone_number,survey_comments,Sample type collected:,Sample ID,Sample date and time,utc,ecoregion,location_notes,Photo filenames (NESW),repeat_visit,habitat_type,habitat_type_other,ground_disturbance,ground_disturbances_other,soil_moisture,plant_species,habitat_notes,canopy_cover,central_coords,latitude,longitude,xyaccuracy_m,elevation_z,z_accuracy_m,ParentGlobalID,CreationDate,Creator,EditDate,Editor,Acknowledgements
1,g1,7,A Person,a@x.com,555,,Litter,20240101-1-AB,1/1/2024 10:00,,Diablo Range,,,No,shrubland,,None,,Saturated,,,25-Jan,,37.5,-121.9,0,300,,p,d,someone,d,someone,
2,g2,8,B Person,b@x.com,,,InsectMalaise,20240102-1-AB,1/2/2024 10:00,,Diablo Range,,,No,forest_woodland,,roads_trails,,Dry/xeric,,,0,,37.6,-121.8,0,350,,p,d,someone,d,someone,
"""


def test_load_clean_and_drop_pii(tmp_path):
    p = tmp_path / "s.csv"; p.write_text(CSV, encoding="utf-8")
    d = load_events(p)
    assert not {"observers", "email", "phone_number", "Creator", "Editor"} & set(d.columns)
    assert d.loc[0, "canopy_cover"] == "1-25" and d.loc[0, "soil_moisture"] == "saturated"
    assert d.loc[1, "soil_moisture"] == "dry_xeric" and summary(d)["sites"] == 2


def test_event_fco_prep_hint_and_context(tmp_path):
    p = tmp_path / "s.csv"; p.write_text(CSV, encoding="utf-8")
    d = load_events(p)
    litter = event_fco(d.iloc[0].to_dict())
    assert "Berlese" in litter.fields["prep_hint"]["extraction"]
    assert "clogging" in litter.fields["prep_hint"]["warning"]
    assert "a@x.com" not in str(litter.to_dict())
    mal = event_fco(d.iloc[1].to_dict())
    assert mal.fields["prep_hint"]["flow"] == "very low" and mal.license == "CC0-1.0"
    ctx = specimen_context(mal)
    assert ctx.fields["habitat_type"] == "forest_woodland" and mal.id in ctx.parents
