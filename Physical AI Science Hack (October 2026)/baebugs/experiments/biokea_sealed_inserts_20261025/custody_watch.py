#!/usr/bin/env python3
"""Read-only local integrity API with fail-closed status and SSE polling.
NO instrument actuation. Within 1s of local file change when service is alive.
Not a remote notification delivery guarantee.
"""
import argparse
import hashlib
import json
import mimetypes
import pathlib
import shutil
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
HERE=pathlib.Path(__file__).resolve().parent
CAD=HERE.parent/"biokea_scad_custody_20261025"
sys.path.insert(0,str(CAD))
import cad_build as b

BASELINE=HERE/"design_attestation.json"
def digest(p):
    with pathlib.Path(p).open("rb") as f:
        h=hashlib.sha256()
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()
def freeze(paths):
    if BASELINE.exists():raise RuntimeError("baseline already exists; create immutable successor")
    records={}
    for path in paths:
        p=HERE/path
        if not p.is_file():raise FileNotFoundError(path)
        records[path]={"sha256":digest(p),"size_bytes":p.stat().st_size}
    record={"schema":"biokea.design-attestation.v1","capture":"EXACT_BYTES","source_repo":"biobitworks/baebugs",
       "files":records,"previous_baebugs_mmr":b.verify()["root"],
       "original_file_mtime_not_authoritative":True,
       "signed":False,"physical_sorting":"NOT_TESTED"}
    BASELINE.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")
    return record
def snapshot(cad=None,attestation=None):
    """Verification is a new read-only observation, not an append of new canonical data."""
    r=(cad or b).verify()
    faults=[]
    if not r.get("PASS",False):
        faults.append({"source":"CAD_MMR","kind":"CHAIN_INTEGRITY","first_divergence":r.get("at"),
          "detail":r.get("failure","verification failed")})
    p=attestation or BASELINE
    if p.exists():
        try:
            manifest=json.loads(p.read_text())
            for relative,expected in manifest.get("files",{}).items():
                target=HERE/relative
                if not target.is_file():
                    faults.append({"source":relative,"kind":"MISSING_FILE"})
                elif digest(target)!=expected["sha256"]:
                    faults.append({"source":relative,"kind":"SOURCE_BYTES_DRIFT",
                         "expected_sha256":expected["sha256"],"observed_sha256":digest(target)})
        except Exception as exc:
            faults.append({"source":"DESIGN_ATTESTATION","kind":"INVALID_BASELINE","detail":str(exc)})
    else: faults.append({"source":"DESIGN_ATTESTATION","kind":"BASELINE_NOT_FROZEN"})
    return {"schema":"biokea.integrity-watch.v1","checked_utc":time.time(),
      "status":"CHAIN_BREAK_HOLD" if faults else "PASS",
      "faults":faults,"cad_mmr_root":r.get("root"),"cad_mmr_count":r.get("leaves"),
      "geometry_operational":"DESIGN_ONLY","physical_samples":"NOT_TESTED",
      "camera_telemetry":"NOT_CONNECTED","robot_telemetry":"NOT_CONNECTED",
      "alert_scope":"LOCAL_BROWSER_ONLY","notification_delivery":"NOT_IMPLEMENTED",
      "read_only":True,"poll_interval_seconds":1,
      "meaning":"A source change is a custody divergence, not necessarily an invalid scientific result"}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(HERE),**kwargs)
    def do_GET(self):
        if self.path.startswith("/api/status"):
            body=json.dumps(snapshot()).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Cache-Control","no-cache, no-store")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers();self.wfile.write(body);return
        if self.path.startswith("/api/events"):
            self.send_response(200)
            self.send_header("Content-Type","text/event-stream")
            self.send_header("Cache-Control","no-cache, no-store")
            self.send_header("Connection","keep-alive")
            self.end_headers()
            last=None
            try:
                for _ in range(1800):
                    data=snapshot()
                    state=json.dumps(data,sort_keys=True,separators=(",",":"))
                    # Send each poll observation, useful as an integrity heartbeat.
                    self.wfile.write(("event: integrity\ndata: "+state+"\n\n").encode());self.wfile.flush()
                    time.sleep(1)
            except (BrokenPipeError,ConnectionResetError):
                return
            return
        if self.path=="/":
            self.path="/index.html"
        super().do_GET()
    def log_message(self,format,*args):return
def self_test():
    assert snapshot()["status"] in ("PASS","CHAIN_BREAK_HOLD")
    original_out,original_ledger=b.OUT,b.LEDGER
    with tempfile.TemporaryDirectory() as temp:
        t=pathlib.Path(temp)
        (t/"events.jsonl").write_bytes(original_ledger.read_bytes())
        for p in original_out.glob("prefix-*.json"):shutil.copy2(p,t/p.name)
        b.OUT=t; b.LEDGER=t/"events.jsonl"
        try:
            assert b.verify()["PASS"]
            records=(t/"events.jsonl").read_text().splitlines()
            obj=json.loads(records[0]);obj["record"]["kind"]="TAMPERED"
            records[0]=json.dumps(obj,sort_keys=True,separators=(",",":"))
            (t/"events.jsonl").write_text("\n".join(records)+"\n")
            after=snapshot()
            assert after["status"]=="CHAIN_BREAK_HOLD"
            assert after["faults"][0]["first_divergence"]==1
            print("NEGATIVE_TEST_PASS: predecessor retained; first divergence 1")
        finally:
            b.OUT,b.LEDGER=original_out,original_ledger
    return True
def main():
    a=argparse.ArgumentParser()
    a.add_argument("command",choices=("snapshot","serve","freeze","self-test"))
    a.add_argument("--port",type=int,default=8786)
    a.add_argument("--files",nargs="*")
    args=a.parse_args()
    if args.command=="freeze":
        paths=args.files or ["variable_aperture_cassette.scad","sealed_insert_cassette.scad",
          "module_catalog.json","source_inventory.json","lomo_comparison_plan.json",
          "capture_receipt.py","lomo_plan.py","index.html",
          "output/variable_overview.png","output/variable_flat_base.dxf",
          "output/variable_flat_slider.dxf","output/variable_flat_retainer.dxf"]
        print(json.dumps(freeze(paths),indent=2));return
    if args.command=="self-test":
        self_test();return
    if args.command=="snapshot":print(json.dumps(snapshot(),indent=2));return
    print("LOCAL_READ_ONLY_SSE http://127.0.0.1:%s/"%args.port,flush=True)
    ThreadingHTTPServer(("127.0.0.1",args.port),Handler).serve_forever()
if __name__=="__main__":main()
