"""DataONE adapter -> sampling-event FCOs -> sample-prep context.

First dataset: "California Insect and Soil Biodiversity Sampling, Stillwater
Sciences (May 2023-August 2025)", California Institute for Biodiversity (CIB),
CC0 1.0. Series urn:uuid:8d8187ba-... (obsoleted by urn:uuid:4929e888-...), data
object Soil_Sampling_Survey_Public_08212025.csv: ~1,440 sampling events at 536
sites (Soil eDNA, Bulk soil, Insect, Litter, InsectMalaise, InsectOther) with
habitat, ecoregion, soil moisture, disturbance, canopy cover, coordinates, dates.

What it gives the sieve/vision lane: the *collecting event* behind a bag. Sample
type and habitat set expectations (litter = soft-bodied micro-arthropods, Malaise
= delicate flying insects, saturated soil = clay that clogs fine mesh) before
anything is imaged, and the Sample ID can ride along as BugPicker's
collection_event_slot so the plate well traces back to the field.

Privacy: observer names, emails, phone numbers and editor accounts are dropped
on load; they never enter FCOs, logs or the repo.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import math
import re
import urllib.parse
import urllib.request
from pathlib import Path

from .fco import FCO

CN = "https://cn.dataone.org/cn/v2"
UA = {"User-Agent": "baebugs/0.1 (+https://github.com/biobitworks/baebugs)"}
CIB_SERIES = "urn:uuid:8d8187ba-683e-4c14-b5a5-c00655e4e852"

PII_COLUMNS = ["observers", "email", "phone_number", "Creator", "Editor"]

# sample type -> prep expectations (placeholders to refine with the team)
PREP_HINTS = {
    "insect":        {"profiles": ["membrane_wings", "long_appendage", "hard_bodied"],
                      "preservation": "ethanol_95", "extraction": "pour off ethanol, sieve submerged",
                      "mesh_floor_mm": 0.5, "flow": "low"},
    "insectmalaise": {"profiles": ["long_appendage", "membrane_wings", "scaled_wings"],
                      "preservation": "ethanol_95", "extraction": "submerged sieving, no jets on fine fraction",
                      "mesh_floor_mm": 0.5, "flow": "very low"},
    "insectother":   {"profiles": ["hard_bodied", "soft_bodied"], "preservation": "ethanol_70",
                      "extraction": "standard stack", "mesh_floor_mm": 0.5, "flow": "low"},
    "litter":        {"profiles": ["soft_bodied", "hard_bodied"], "preservation": "ethanol_70",
                      "extraction": "Berlese/Tullgren funnel first, then fine sieve",
                      "mesh_floor_mm": 0.063, "flow": "very low"},
    "bulk soil":     {"profiles": ["soft_bodied", "hard_bodied"], "preservation": "ethanol_70",
                      "extraction": "flotation (sugar/salt) before sieving; expect clogging",
                      "mesh_floor_mm": 0.063, "flow": "low"},
    "soil edna":     {"profiles": [], "preservation": "frozen/buffer",
                      "extraction": "not for sieving (eDNA sample)", "mesh_floor_mm": None, "flow": None},
}


# ---------- fetching ----------

def _solr(q, fl="*"):
    url = f"{CN}/query/solr/?" + urllib.parse.urlencode({"q": q, "fl": fl, "wt": "json", "rows": 100})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read())["response"]["docs"]


def latest_version(pid: str) -> dict:
    doc = _solr(f'id:"{pid}"')[0]
    while doc.get("obsoletedBy"):
        doc = _solr(f'id:"{doc["obsoletedBy"]}"')[0]
    return doc


def pull_dataone(pid: str, out_dir, workers=4) -> dict:
    """Follow obsoletedBy to the newest metadata, then download it and every
    data object it documents, in parallel, with sha256 + licence manifest."""
    meta = latest_version(pid)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    objs = _solr(f'resourceMap:"{meta["resourceMap"][0]}"', "id,fileName,formatId,size")

    def get(o):
        dest = out / (o.get("fileName") or o["id"].replace(":", "_"))
        url = f"{CN}/resolve/{urllib.parse.quote(o['id'], safe='')}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
            data = r.read()
        dest.write_bytes(data)
        return {**o, "file": dest.name, "sha256": hashlib.sha256(data).hexdigest()}

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        files = list(ex.map(get, objs))
    manifest = {"requested": pid, "latest": meta["id"], "title": meta.get("title"),
                "license": meta.get("license") or "see EML", "datasource": meta.get("datasource"),
                "files": files}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


# ---------- cleaning ----------

_CANOPY_FIX = {"25-Jan": "1-25", "Jan-25": "1-25", "50-Jan": "1-50"}


def _norm(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip()
    return s or None


def _cat(v):
    s = _norm(v)
    return None if s is None else re.sub(r"[\s/]+", "_", s.lower())


def load_events(csv_path):
    import pandas as pd
    d = pd.read_csv(csv_path, encoding="utf-8-sig")
    d = d.drop(columns=[c for c in PII_COLUMNS if c in d.columns])
    d = d.rename(columns={"Sample type collected:": "sample_type", "Sample ID": "sample_id",
                          "Sample date and time": "sampled_at"})
    for c in ["sample_type", "habitat_type", "soil_moisture", "ground_disturbance", "ecoregion"]:
        if c in d:
            d[c] = d[c].map(_cat) if c != "ecoregion" else d[c].map(_norm)
    d["soil_moisture"] = d["soil_moisture"].replace({"dry_xeric": "dry_xeric", "dry_xeric_": "dry_xeric"})
    if "canopy_cover" in d:
        d["canopy_cover"] = d["canopy_cover"].map(lambda v: _CANOPY_FIX.get(_norm(v), _norm(v)))
    return d


# ---------- FCOs ----------

def event_fco(row) -> FCO:
    keep = ["sample_id", "site_ID", "sample_type", "sampled_at", "ecoregion", "habitat_type",
            "habitat_type_other", "ground_disturbance", "soil_moisture", "canopy_cover",
            "plant_species", "latitude", "longitude", "elevation_z", "repeat_visit"]
    f = {k: _norm(row.get(k)) for k in keep if _norm(row.get(k)) is not None}
    for k in ("latitude", "longitude", "elevation_z"):
        if k in f:
            f[k] = float(f[k])
    if "latitude" in f and "longitude" in f:
        f["lat_long"] = [f["latitude"], f["longitude"]]
    st = (f.get("sample_type") or "").replace("_", " ")
    hint = PREP_HINTS.get(st)
    if hint:
        f["prep_hint"] = hint
        if f.get("soil_moisture") in ("saturated", "flooded"):
            f["prep_hint"] = {**hint, "warning": "saturated sample: deflocculate/soak before fine mesh; expect clogging"}
    return FCO("sampling_event", f"dataone:{CIB_SERIES}#{f.get('sample_id', '?')}", f,
               license="CC0-1.0")


def events_for_bag(df, sample_id: str):
    return [event_fco(r) for r in df[df["sample_id"] == sample_id].to_dict("records")]


def summary(df) -> dict:
    return {"events": len(df), "sites": int(df["site_ID"].nunique()),
            "sample_types": df["sample_type"].value_counts().to_dict(),
            "habitats": df["habitat_type"].value_counts().head(8).to_dict(),
            "moisture": df["soil_moisture"].value_counts().to_dict()}
