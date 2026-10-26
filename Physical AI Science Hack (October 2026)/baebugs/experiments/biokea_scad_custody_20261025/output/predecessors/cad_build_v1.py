#!/usr/bin/env python3
"""Standalone OpenSCAD build with an append-only Antigense-style HYDRALAMP_MMR_V1.
Source contract: biobitworks/antigense-cyberhack/src/custody.py, read-only port.
No existing Antigense MMR is modified. No safety/physical recovery claim.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "output"
LEDGER = OUT / "events.jsonl"
KIND = "HYDRALAMP_MMR_V1"
SOURCE = "biobitworks/antigense-cyberhack/src/custody.py"
def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
def digest(v):
    return hashlib.sha256(v).hexdigest()
def hash_file(p):
    with open(p,"rb") as f:
        h=hashlib.sha256()
        for b in iter(lambda:f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()
def mmr(rows):
    peaks=[]; leaves=[]
    for i,item in enumerate(rows):
        body={"event_index":i+1,"event_hash":item["event_hash"],"cfmo_version_id":item["fco_id"]}
        leaf=digest(canon(body))
        leaves.append({"body":body,"leaf_sha256":leaf})
        size=i+1
        while size%2==0:
            leaf=digest(bytes.fromhex(peaks.pop())+bytes.fromhex(leaf))
            size//=2
        peaks.append(leaf)
    if not peaks:
        root=digest(b"HYDRALAMP_MMR_EMPTY")
    else:
        acc=peaks[0]
        for peak in peaks[1:]:
            acc=digest(bytes.fromhex(acc)+bytes.fromhex(peak))
        root=digest(b"HYDRALAMP_MMR_BAG_V1:"+bytes.fromhex(acc))
    return {"algorithm":KIND,"leaf_count":len(leaves),"leaves":leaves,"peaks":peaks,"root":root}
def independent_root(rows):
    hs=[digest(canon({"event_index":i+1,"event_hash":x["event_hash"],"cfmo_version_id":x["fco_id"]})) for i,x in enumerate(rows)]
    peaks=[]; pos=0
    for j in range(len(hs).bit_length()-1,-1,-1):
        n=1<<j
        if len(hs)&n:
            level=hs[pos:pos+n];pos+=n
            while len(level)>1:
                level=[digest(bytes.fromhex(level[i])+bytes.fromhex(level[i+1])) for i in range(0,len(level),2)]
            peaks.append(level[0])
    if not peaks:return digest(b"HYDRALAMP_MMR_EMPTY")
    acc=peaks[0]
    for p in peaks[1:]:acc=digest(bytes.fromhex(acc)+bytes.fromhex(p))
    return digest(b"HYDRALAMP_MMR_BAG_V1:"+bytes.fromhex(acc))
def read_rows():
    return [json.loads(s) for s in LEDGER.read_text().splitlines() if s.strip()] if LEDGER.exists() else []
def verify(rows=None):
    rows=read_rows() if rows is None else rows
    for i,r in enumerate(rows):
        rec=r["record"]
        identity=digest(canon(rec))
        if r["event_index"]!=i+1 or r["event_hash"]!=identity or r["fco_id"]!="fco:sha256:"+identity:
            return {"PASS":False,"failure":"event identity mismatch","at":i+1}
        m=mmr(rows[:i+1]); pref=OUT/("prefix-%06d.json"%(i+1))
        if not pref.exists() or json.loads(pref.read_text())!={"algorithm":KIND,"size":i+1,"root":m["root"],"peaks":m["peaks"],"leaf_hashes":[x["leaf_sha256"] for x in m["leaves"]]}:
            return {"PASS":False,"failure":"prefix mismatch or missing","at":i+1}
        if m["root"]!=independent_root(rows[:i+1]):
            return {"PASS":False,"failure":"independent MMR mismatch","at":i+1}
    m=mmr(rows)
    return {"PASS":True,"algorithm":KIND,"leaves":len(rows),"root":m["root"],"peaks":m["peaks"],
            "identity_recomputed":True,"prefixes_recomputed":True,"independent_root_recomputed":True,
            "signing":"NOT_SIGNED","external_antigense_mmr_updated":False}
def append(kind,state,details,inputs=None):
    if LEDGER.exists():
        prev=verify()
        if not prev["PASS"]:raise RuntimeError("predecessor FAIL: "+str(prev))
    rows=read_rows()
    t=dt.datetime.now(dt.timezone.utc).isoformat()
    rec={"schema":"biokea.cad.ObservationFCO.v1","kind":kind,"state":state,"time_utc":t,
         "project":"biobitworks/baebugs","role":"READ_ONLY_VIRTUAL_CAD",
         "parent_fco_id":rows[-1]["fco_id"] if rows else None,
         "previous_root":mmr(rows)["root"] if rows else None,
         "details":details,"inputs":inputs or {},
         "reference_source":SOURCE,"physical_hardware_executed":False,
         "signed":"NOT_SIGNED"}
    identity=digest(canon(rec))
    row={"event_index":len(rows)+1,"record":rec,"event_hash":identity,"fco_id":"fco:sha256:"+identity}
    m=mmr(rows+[row])
    if m["root"]!=independent_root(rows+[row]):raise RuntimeError("MMR verifier mismatch")
    pf=OUT/("prefix-%06d.json"%(len(rows)+1))
    with pf.open("x") as f:
        json.dump({"algorithm":KIND,"size":len(rows)+1,"root":m["root"],"peaks":m["peaks"],
                   "leaf_hashes":[x["leaf_sha256"] for x in m["leaves"]]},f,sort_keys=True,indent=2)
    with LEDGER.open("a",encoding="utf-8") as f:
        f.write(canon(row).decode()+"\n");f.flush();os.fsync(f.fileno())
    return row,m
def render(cmd,label):
    p=subprocess.run(cmd,cwd=HERE,capture_output=True,text=True,timeout=160)
    return {"cmd":cmd,"returncode":p.returncode,"stdout_tail":p.stdout[-1200:],"stderr_tail":p.stderr[-1800:]}
def publish():
    rows=read_rows()
    v=verify(rows)
    if not v["PASS"]:raise RuntimeError(str(v))
    files={}
    for name in ("tower_preview.png","tower_mesh.stl","source_model.scad"):
        p=OUT/name
        if p.exists():files[name]={"sha256":hash_file(p),"bytes":p.stat().st_size}
    projection={"schema":"biokea.cad.dashboard.v1","status":"VIRTUAL_RENDER" if files.get("tower_preview.png") else "NOT_TESTED",
                "version":1,"updated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"verification":v,
                "files":files,"events":rows,"source_repository":"biobitworks/baebugs",
                "upstream_antigense":{"repository":"biobitworks/antigense-cyberhack","algorithm_source":SOURCE,
                   "relation":"ALGORITHM_DERIVED_FROM","existing_mmr_joined":False,"upstream_root":"UNKNOWN"},
                "safety":"CAD VIRTUAL ONLY; dimensions MEASURE placeholders; robot motions NOT_TESTED",
                "three_objects":[{"id":"T01","analog":"rice-like","status":"SCHEMATIC_IN_MODEL","observed_recovery":"NOT_TESTED"},
                                 {"id":"T02","analog":"chia-like","status":"SCHEMATIC_IN_MODEL","observed_recovery":"NOT_TESTED"},
                                 {"id":"T03","analog":"ditalini-like","status":"SCHEMATIC_IN_MODEL","observed_recovery":"NOT_TESTED"}]}
    (OUT/"status.json").write_text(json.dumps(projection,indent=2))
    return projection
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("command",choices=("build","verify","publish"))
    a=ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if a.command=="verify":
        v=verify();print(json.dumps(v,indent=2));sys.exit(0 if v["PASS"] else 1)
    if a.command=="publish":
        p=publish();print(json.dumps(p["verification"],indent=2));return
    if LEDGER.exists():raise SystemExit("ABSTAIN: lane already built; never overwrite ledger; use a successor directory")
    src=HERE/"tower_three_analogs.scad"
    (OUT/"source_model.scad").write_bytes(src.read_bytes())
    git=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD"],capture_output=True,text=True)
    rev=git.stdout.strip() if git.returncode==0 else "UNKNOWN"
    ver=subprocess.run(["openscad","--version"],capture_output=True,text=True)
    input_files={x:hash_file(ROOT/x) for x in
        ("print/bench/tower.scad","baebugs/config/tower.yaml","print/bench/demo_run.json")}
    append("SOURCE_SNAPSHOT","OBSERVED",{"baebugs_head":rev,"openscad":(ver.stdout+ver.stderr).strip(),
        "source_sha256":hash_file(src),"antigense_mmr_implementation":SOURCE,
        "antigense_chain_spliced":False},input_files)
    cmds=[("OPENSCAD_PNG",["openscad","-o",str(OUT/"tower_preview.png"),"--imgsize=1200,960","--autocenter","--viewall",str(src)],"tower_preview.png"),
          ("OPENSCAD_STL",["openscad","-o",str(OUT/"tower_mesh.stl"),str(src)],"tower_mesh.stl")]
    for kind,cmd,name in cmds:
        p=render(cmd,kind);f=OUT/name
        ok=p["returncode"]==0 and f.exists() and f.stat().st_size>100
        append(kind,"OBSERVED" if ok else "FAILED",{"execution":p,"output_sha256":hash_file(f) if ok else None,
            "bytes":f.stat().st_size if f.exists() else None})
        if not ok:break
    history=json.loads((ROOT/"print/bench/demo_run.json").read_text())
    h=history.get("summary",{})
    append("HISTORICAL_PREFLIGHT","OBSERVED",{"historical_status":h.get("status"),"break_point":h.get("break_point"),
        "note":"source file read; historical simulation only; not rerun by this lane",
        "physical_motion":"NOT_TESTED","source_sha256":input_files["print/bench/demo_run.json"]})
    p=publish()
    print(json.dumps({"outputs":p["files"],"verification":p["verification"]},indent=2))
if __name__=="__main__": main()
