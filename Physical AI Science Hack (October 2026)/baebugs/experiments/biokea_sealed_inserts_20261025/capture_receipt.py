#!/usr/bin/env python3
"""Register camera evidence without inferring that an insect is uniquely identified.
The command does NOT operate cameras, servos, robots, filters, or fluidics.
It only admits exact bytes of already captured files and human-entered context.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

EXPERIMENT = Path(__file__).resolve().parent
CAD = EXPERIMENT.parent / "biokea_scad_custody_20261025"
sys.path.insert(0, str(CAD))
import cad_build as receipt

STAGES = (
    "INTAKE", "PRE_SORT", "FILTER_FRACTION", "PRE_INVERSION",
    "INVERTED_CATCH", "EDGE_INSPECTION", "FINAL_EMPTY_TRAY", "BUGPICKER_HANDOFF")
FAULTS = (
    "UNLATCHED_INSERT", "OPEN_CATCH_PATH", "EDGE_GAP", "GASKET_PINCHED",
    "RINSE_PRESSURE_UNKNOWN", "CLUMPED_SAMPLE", "DETECTOR_DISAGREEMENT",
    "FRAME_STALE", "SPECIMEN_DAMAGED", "COUNT_DISCREPANCY",
    "PHYSICAL_CONTAINER_UNTRACKED", "CLEANING_NOT_CLEARED")
ALLOWED = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

def file_hash(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            h.update(part)
    return h.hexdigest()

def media_header_ok(data, suffix):
    if suffix==".png": return data.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".jpeg",".jpg"}:return data.startswith(b"\xff\xd8\xff")
    if suffix in {".tif",".tiff"}:return data[:4] in (b"II*\x00",b"MM\x00*")
    return False

def stage_status(stage, flagged):
    if flagged: return "QUARANTINED"
    if stage in ("FILTER_FRACTION","INVERTED_CATCH","BUGPICKER_HANDOFF"):
        return "REQUIRES_HUMAN_REVIEW"
    return "OBSERVED_IMAGE_BYTES"

def normalize_args(a):
    required={name:getattr(a,name,None) for name in (
        "sample_id","fraction_id","tray_id","insert_id","gasket_lot",
        "camera_id","calibration_id","operator_id","frame_id")}
    absent=[k for k,v in required.items() if not v or not v.strip()]
    if absent:raise ValueError("context missing "+",".join(absent))
    if a.stage not in STAGES: raise ValueError("unsupported stage")
    if a.flag and a.flag not in FAULTS:raise ValueError("unsupported VIP code")
    if a.observed_count is not None and a.observed_count<0:raise ValueError("invalid count")
    return required

def ingest(a, store=None, append=None):
    """store and append injections allow isolated software tests."""
    context=normalize_args(a)
    src=Path(a.image)
    if not src.is_file() or src.is_symlink():raise ValueError("source must be regular file")
    suffix=src.suffix.lower()
    if suffix not in ALLOWED:raise ValueError("file type not accepted")
    with src.open("rb") as f:
        head=f.read(16)
    if not media_header_ok(head,suffix):raise ValueError("image magic mismatch")
    size=src.stat().st_size
    if size<16 or size>1024*1024*1024:raise ValueError("image file invalid size")
    original_sha=file_hash(src)
    target_root=Path(store) if store is not None else CAD/"output"/"captured_images"
    target_root.mkdir(parents=True,exist_ok=True)
    dst=target_root/(original_sha+suffix)
    if dst.exists():
        if file_hash(dst)!=original_sha:raise ValueError("content-addressed target modified")
    else:
        # no overwrite; the attempt itself is atomic, verified before publishing receipt
        pending=target_root/(original_sha+".partial-"+str(os.getpid()))
        with src.open("rb") as f, pending.open("xb") as out:
            shutil.copyfileobj(f,out)
            out.flush();os.fsync(out.fileno())
        if file_hash(pending)!=original_sha:
            pending.unlink(missing_ok=True)
            raise ValueError("copied bytes mismatch")
        try:
            os.link(pending,dst)
        except FileExistsError:
            if file_hash(dst)!=original_sha:
                raise ValueError("raced content-addressed destination changed")
        finally:
            pending.unlink(missing_ok=True)
    if file_hash(src)!=original_sha or file_hash(dst)!=original_sha:
        raise ValueError("source changed while importing")
    aperture_state=getattr(a,"aperture_stage",None)
    if aperture_state not in (None,0,1,2):
        raise ValueError("invalid aperture setting")
    variable_filter=getattr(a,"filter_revision",None)
    event={
        "schema":"biokea.capture.ObservationFCO.v2",
        "filter_revision":variable_filter or "UNKNOWN",
        "aperture_stage":aperture_state,
        "nominal_aperture_mm":([3.6,2.4,1.2][aperture_state] if aperture_state is not None else None),
        "aperture_source":"OPERATOR_DECLARED_UNVERIFIED" if aperture_state is not None else "UNKNOWN",
        "camera_capture_time":getattr(a,"capture_time",None) or "UNKNOWN",
        "camera_capture_time_provenance":"OPERATOR_REPORTED" if getattr(a,"capture_time",None) else "UNKNOWN",

        "stage":a.stage,"image_sha256":original_sha,"image_bytes":size,
        "image_occurrence_id":a.frame_id,"physical_context":context,
        "observer_reported_count":a.observed_count,
        "count_provenance":"OPERATOR_REPORTED" if a.observed_count is not None else "NULL",
        "fault":a.flag or None,"operator_claim":a.notes or None,
        "source_capture_time":"UNKNOWN", # not from file modification time
        "ingest_semantics":"OBSERVED_EXACT_FILE_BYTES",
        "organism_identity":"UNKNOWN",
        "capture_mode":"IMPORTED_EXISTING_FILE",
        "physical_recovery":"NOT_INFERRED",
        "downstream_auto_admit":False,
        "object_store_relative":str(dst.relative_to(target_root)),
    }
    record_hash=hashlib.sha256(receipt.canon(event)).hexdigest()
    event["capture_atom_content_sha256"]=record_hash
    if append is None:
        r,m=receipt.append("CAMERA_EVIDENCE",stage_status(a.stage,a.flag),event,
                           {"image_sha256":original_sha,
                            "image_context_id":a.frame_id})
        return {"image_sha256":original_sha,"fco_id":r["fco_id"],
                "mmr_size":len(receipt.read_rows()),"mmr_root":m["root"],
                "status":stage_status(a.stage,a.flag)}
    return append(event)

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--image",required=True)
    p.add_argument("--stage",choices=STAGES,required=True)
    for key in ("sample_id","fraction_id","tray_id","insert_id","gasket_lot",
                "camera_id","calibration_id","operator_id","frame_id"):
        p.add_argument("--"+key.replace("_","-"),required=True)
    p.add_argument("--observed-count",type=int,default=None)
    p.add_argument("--flag",choices=FAULTS,default=None)
    p.add_argument("--notes",default="")
    p.add_argument("--aperture-stage",type=int,choices=[0,1,2],default=None)
    p.add_argument("--filter-revision",default=None)
    p.add_argument("--capture-time",default=None)
    a=p.parse_args(argv)
    print(json.dumps(ingest(a),indent=2))
if __name__=="__main__":main()
