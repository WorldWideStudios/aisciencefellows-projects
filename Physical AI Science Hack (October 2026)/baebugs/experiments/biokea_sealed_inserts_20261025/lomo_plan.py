#!/usr/bin/env python3
"""Deterministic analysis design, not biological outcome measurements."""
import hashlib
import itertools
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def H(v):return hashlib.sha256(canonical(v)).hexdigest()

def enumerate_design(catalog):
    d=catalog["defaults"]
    rows=[]
    dimensions=("arm","filter","tray","camera","water","heat","reagent","goal")
    for dim in dimensions:
        options=catalog["modules"][dim]
        baseline=d[dim]
        for variant in options:
            if variant["id"]==baseline:continue
            spec=dict(d);spec[dim]=variant["id"]
            rows.append({"study":"LEAVE_ONE_MODULE_CHOICE_OUT_OR_REPLACE", "dimension":dim,
              "baseline_config":dict(d),"candidate_config":spec,
              "variant_id":variant["id"],"variant_status":variant["state"],
              "planned_baseline_measurements":None,"planned_variant_measurements":None,
              "delta_purity":None,"delta_capture":None,"delta_morphology_damage":None,
              "delta_bytes_verified":None,"comparison_result":"NOT_TESTED",
              "safety_gate":"OPERATOR_AND_EXPERT_REQUIRED",
              "claim":"NO EMPIRICAL EFFECT ESTIMATED"})
    reference={"schema":"biokea.lomo.protocol.v1","protocol_id":None,
       "purpose":"factor-specific matched contrasts, future study only",
       "assumptions":["same accession/split and independently reviewed reference labels",
       "one module changed at a time; no outcome inferred from source presence",
       "three or more physical replicates only after site approval",
       "protect specimen morphology and preserve unresolved identities",
       "laboratory hazards and sample consent require expert review"],
       "outcomes":{"specimen_capture_rate":"NOT_COMPUTED",
          "per-fraction_yield":"NOT_COMPUTED","part_damage_rate":"NOT_COMPUTED",
          "taxonomic_novelty_precision":"NOT_COMPUTED",
          "time_per_verified_specimen":"NOT_COMPUTED",
          "RNA_quality":"NOT_TESTED","DNA_barcode_success":"NOT_TESTED",
          "energy_water_reagent_usage":"NOT_COMPUTED"},
       "rows":rows}
    reference["protocol_id"]="biokea-lomo-sha256-"+H(reference)
    return reference

def main():
    cat=json.loads((HERE/"module_catalog.json").read_text())
    result=enumerate_design(cat)
    p=HERE/"lomo_comparison_plan.json"
    p.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"protocol_id":result["protocol_id"],"variants":len(result["rows"]),
       "empirical_comparisons_executed":0,"source_file_sha256":hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
if __name__=="__main__":main()
