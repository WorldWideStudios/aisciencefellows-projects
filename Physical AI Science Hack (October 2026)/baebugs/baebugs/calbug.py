"""Calbug / Essig Museum lane: what *should* be in a sample from this place?

The Essig Museum of Entomology collection (Calbug digitization) is published on
GBIF as dataset 5d283bb6-64dd-4626-8b3b-a4e8db5415c3 (~550k records). Records
carry taxonomy, county, preparation and life stage - not images or body sizes.
So we use it as a PRIOR:

  locality -> family composition (Essig) -> x family width ranges -> expected
  size-class mix -> compare to what the camera measured.

A big mismatch flags a sample (wrong bag, broken specimens, debris) before it is
sieved, and the prior lets the planner pre-select frames when imaging is poor.
Network calls run on your machine (this module uses only the stdlib).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections import Counter

import numpy as np

from .sieve import classify, load_yaml

ESSIG_DATASET = "5d283bb6-64dd-4626-8b3b-a4e8db5415c3"
GBIF = "https://api.gbif.org/v1"


def _get(path, **params):
    url = f"{GBIF}/{path}?{urllib.parse.urlencode(params)}" if params else f"{GBIF}/{path}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


def family_composition(place: str, state: str = "California", order: str | None = None,
                       top: int = 25) -> dict[str, int]:
    """Family -> specimen count in the Essig collection for a place (county,
    locality or any free text), e.g. family_composition('Alameda')."""
    params = {"datasetKey": ESSIG_DATASET, "stateProvince": state, "q": place,
              "limit": 0, "facet": "familyKey", "facetLimit": top}
    if order:
        params["order"] = order
    res = _get("occurrence/search", **params)
    out = {}
    for f in (res.get("facets") or [{}])[0].get("counts", []):
        name = _get(f"species/{f['name']}").get("canonicalName", f["name"])
        out[name] = int(f["count"])
    return out


def expected_class_mix(composition: dict[str, int], family_sizes=None,
                       insects=None, n_draw=20000, seed=0) -> dict[str, float]:
    """Monte-Carlo the size-class mix implied by a family composition."""
    family_sizes = family_sizes or load_yaml("family_sizes.yaml")["families"]
    insects = insects or load_yaml("insects.yaml")
    rng = np.random.default_rng(seed)
    known = {f: c for f, c in composition.items() if f in family_sizes}
    if not known:
        return {}
    fams = list(known)
    p = np.array([known[f] for f in fams], float); p /= p.sum()
    draws = rng.choice(len(fams), size=n_draw, p=p)
    widths = [rng.uniform(*family_sizes[fams[i]]["width_mm"]) for i in draws]
    cnt = Counter(classify(w, insects["classes"]) for w in widths)
    return {k: v / n_draw for k, v in cnt.items()}


def compare(expected: dict[str, float], observed_widths, insects=None,
            threshold: float = 0.35) -> dict:
    """Total-variation distance between expected and observed class mixes."""
    insects = insects or load_yaml("insects.yaml")
    obs = Counter(classify(w, insects["classes"]) for w in observed_widths)
    n = max(sum(obs.values()), 1)
    keys = set(expected) | set(obs)
    tv = 0.5 * sum(abs(expected.get(k, 0) - obs.get(k, 0) / n) for k in keys)
    return {"tv_distance": round(tv, 3), "flag": tv > threshold,
            "expected": expected, "observed": {k: obs[k] / n for k in obs}}


def essig_catalog_ref(catalog_number: str) -> dict:
    """Provenance link for a museum specimen, e.g. EMEC347945."""
    return {"catalogNumber": catalog_number, "institutionCode": "EMEC",
            "datasetKey": ESSIG_DATASET,
            "gbif_search": f"https://www.gbif.org/occurrence/search?catalog_number={catalog_number}"}
