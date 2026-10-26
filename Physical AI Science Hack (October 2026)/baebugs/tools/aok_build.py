#!/usr/bin/env python3
"""Public Baebugs AoK v1: source-bound atoms, content and occurrence IDs, graph, Merkle proofs."""
from __future__ import annotations
import argparse,hashlib,json,pathlib,sys
R=pathlib.Path(__file__).resolve().parents[1]
O=R/"site/aok/data"
ALGO="BAEBUGS_AOK_MERKLE_V1"
SOURCE_REV="3a1806000ec4ca38e25f2749712d54b82ef612af"
PARENT="c2292e38a40e789256cc0e14ee0565d032795ae5171fa88bdda6b9a05720c23f"
TRAIN="09b78c8ff6abbbb8a81738ac474807603463c54ee1f98f6825bd9edea176d9bc"
UPSTREAM_REGISTRY=R/"tools/aok_upstream_sources.json"
def canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def h(b):return hashlib.sha256(b).hexdigest()
def fhash(p):return h(pathlib.Path(p).read_bytes()) if pathlib.Path(p).is_file() else None
def read(p):return json.loads((R/p).read_text())
def fpath(p):return fhash(R/p) if p else None
SOURCES=[
("baebugs","Baebugs code and generated designs","MIT","LICENSE","biobitworks","https://github.com/biobitworks/baebugs","REPO_DECLARED"),
("bugpicker","BioKEA BugPicker","GPL-3.0","", "BioKEA","https://github.com/BioKEA/BugPicker","UPSTREAM_LICENSE"),
("armdemo","BioKEA BugPicker arm demo","GPL-3.0","","BioKEA","https://github.com/BioKEA/BugPicker-arm-demo","UPSTREAM_LICENSE"),
("bugsorter","BioKEA BugSorter","UNKNOWN","","BioKEA","https://github.com/BioKEA/BugSorter","LICENSE_NOT_FOUND"),
("entosieve","zlite EntoSieve","UNKNOWN","","zlite","https://github.com/zlite/entosieve","LICENSE_NOT_FOUND"),
("gbif","GBIF specimen occurrences and media","PER_RECORD","","MIXED","https://www.gbif.org/","MEDIA_LICENSE_SEPARATE"),
("essig","Essig Museum collection","UNKNOWN","","UNKNOWN","https://essigdb.berkeley.edu/","TERMS_UNVERIFIED"),
("calacademy","California Academy entomology","RESTRICTED","","California Academy of Sciences","https://www.calacademy.org/scientists/entomology-information-page","NONCOMMERCIAL_NO_REDISTRIBUTION"),
("opentrons","Opentrons interfaces","UNKNOWN","","Opentrons","https://docs.opentrons.com/","TERMS_NOT_AUDITED"),
("ilea","ILEA dataset (user mention)","UNKNOWN","","UNKNOWN","","IDENTITY_NOT_RESOLVED")]
STAGES=[
("sorter","BugSorter / EntoSieve","Coarse specimen fractionation","PHYSICAL_SORTING_NOT_TESTED"),
("disperser","BugDisperser","Flotation and object separation","NOT_TESTED"),
("picker","BugPicker","Specimen identity, pickup and plate transfer","FILE_PROTOCOL_PRESENT"),
("dispenser","Enzyme dispenser","Reagent delivery","NOT_TESTED"),
("incubator","Turnstile incubator","Incubation and state tracking","NOT_TESTED"),
("camera","Camera and vision","Detection, scale, source context","PSEUDOLABEL_EVALUATION_ONLY"),
("robot","Robot and Partabot arm","Reachability and tray handling","EMULATED_PREFLIGHT_FAILURE"),
("opentrons","Opentrons modular deck","Labware adapter and handoff","PARTS_GENERATED"),
("filtration","Flow-through and eDNA","Capture the missing fine fraction","PROPOSED")]
CLAIMS=[
("mit","Baebugs MIT declaration","Repository root LICENSE text declares MIT and 2026 biobitworks copyright.","OBSERVED","baebugs","Does not independently prove copyright to third-party works."),
("gpl","Upstream BugPicker GPL","The BioKEA BugPicker LICENSE is GNU GPL v3.","OBSERVED","bugpicker","Do not claim upstream IP as Baebugs invention."),
("parts","Baebugs generated STL prototypes","STL bytes and generator output identifiers are recorded in parts manifests.","SUPPORTED_REPO","baebugs","Geometry integrity, not fit or patent novelty."),
("photo","CA-photo transfer result","002a reports higher held-out teacher agreement for CA+synthetic compared with synthetic-only.","OBSERVED_EXPLORATORY","baebugs","AZ +0.6955, OR +0.5205 pseudo-label mAP50-95. No expert labels."),
("toys","Synthetic-only toy length result","002a records median length error at 20 px/mm 9.41% synthetic versus 22.67% CA+synthetic.","OBSERVED_EXPLORATORY","baebugs","Weights not recovered."),
("three","Three real insects preserved downstream","A three-specimen full recovery and identification run.","NOT_TESTED","baebugs","No physical recovery receipt."),
("novel","New species confirmed by expert","A human-qualified taxonomist verifies novelty.","NOT_TESTED","essig","Novelty score does not prove a new taxon."),
("patent","Patentable originality","Exclusive rights and novelty of the workcell architecture.","UNKNOWN","baebugs","Requires inventor/assignment/prior-art/legal review."),
("custody","Graph root represents content inclusion","This build provides exact-byte source hashes and recomputable Merkle proofs.","SUPPORTED_BUILD","baebugs","Integrity does not establish scientific truth or causality.")]
def license_digest(short):
    if short=="baebugs":return fpath("LICENSE")
    return json.loads(UPSTREAM_REGISTRY.read_text())["sources"].get(short,{}).get("license_sha256")
def upstream_info(short):
    return json.loads(UPSTREAM_REGISTRY.read_text())["sources"].get(short,{})
def build_records():
    n,e,files=[],[],{"tools/aok_upstream_sources.json":fpath("tools/aok_upstream_sources.json")}
    def add(id,typ,title,body,source="baebugs",status="PROPOSED",license="UNKNOWN",rights="UNKNOWN",path="",url="",details=None,stage=""):
        source_hash=fpath(path)
        if path and source_hash is None:raise ValueError("SOURCE_FILE_MISSING "+path)
        c={"type":typ,"title":title,"body":body,"source_sha256":source_hash,"details":details or {}}
        x={"id":id,"type":typ,"title":title,"body":body,"source":source,"status":status,"license":license,
           "rights":rights,"source_path":path or None,"source_sha256":source_hash,"url":url or None,
           "details":details or {},"stage":stage or None,"content":c}
        ctx={"id":id,"source":source,"status":status,"license":license,"rights":rights,"stage":stage or None,"path":path or None}
        x["context"]=ctx;x["content_canonical_utf8"]=canon(c).decode("utf-8");x["context_canonical_utf8"]=canon(ctx).decode("utf-8");x["fco_id"]="fco:sha256:"+h(canon(c));x["occurrence_id"]="occ:sha256:"+h(canon(ctx))
        if id in {z["id"] for z in n}:raise ValueError("DUPLICATE_NODE "+id)
        n.append(x)
        if source_hash:files[path]=source_hash
        return id
    def edge(a,b,t,status="DECLARED_NOT_CAUSAL"):e.append({"from":a,"to":b,"type":t,"status":status})
    for key,title,license,path,owner,url,state in SOURCES:
        add("source:"+key,"source",title,"Source rights status: "+state,key,state,license,
           "SOURCE_SPECIFIC",path,url,{"attribution":owner,"license_evidence_sha256":license_digest(key),"upstream_commit":upstream_info(key).get("commit"),"upstream_license_status":upstream_info(key).get("status")})
    for key,title,body,state in STAGES:
        add("stage:"+key,"module",title,body,"baebugs",state,"MIT_REPO_CONTEXT","UPSTREAM_SEPARATE",
            "baebugs/tower_twin.py" if key=="sorter" else "",stage=key)
        edge("source:baebugs","stage:"+key,"DECLARES")
    parts=read("print/parts/parts.json")
    for p in (parts if isinstance(parts,list) else parts["parts"]):
        name=p["part"];path="print/parts/"+p["stl"]
        if fpath(path)!=p["sha256"]:raise ValueError("PART_HASH_MISMATCH "+path)
        st="robot" if name.startswith("arm_") else "sorter"
        id=add("part:"+name,"part",name.replace("_"," ").title(),
               "Printable concept geometry, not specimen-safe or calibrated.",
               "baebugs","GEOMETRY_BYTES_VERIFIED","MIT_REPO_CONTEXT","CONTRIBUTOR_OWNERSHIP_UNVERIFIED",
               path,"https://github.com/biobitworks/baebugs/blob/"+SOURCE_REV+"/"+path,
               {"bbox_mm":p.get("bbox_mm"),"sha256_from_manifest":p["sha256"],"physical_fit":"NOT_TESTED"},st)
        edge("source:baebugs",id,"GENERATED_ARTIFACT","BYTES_VERIFIED")
        edge(id,"stage:"+st,"DESIGNED_FOR")
    for p in read("opentrons/parts.json")["parts"]:
        path="opentrons/"+p["stl"]
        if fpath(path)!=p["sha256"]:raise ValueError("ADAPTER_HASH_MISMATCH "+path)
        id=add("part:"+p["part"],"part",p["part"].replace("_"," ").title(),
               "Opentrons deck-shaped concept; integration is not certified.",
               "baebugs","GEOMETRY_BYTES_VERIFIED","MIT_REPO_CONTEXT","CONTRIBUTOR_OWNERSHIP_UNVERIFIED",
               path,"https://github.com/biobitworks/baebugs/blob/"+SOURCE_REV+"/"+path,
               {"bbox_mm":p.get("bbox_mm"),"sha256_from_manifest":p["sha256"],"physical_fit":"NOT_TESTED"},"opentrons")
        edge(id,"stage:opentrons","DESIGNED_FOR")
        edge("source:opentrons",id,"INTERFACE_REFERENCE")
    for x in read("print/filters/filters.json"):
        id=add("filter:"+x["id"],"filter",x["id"],x.get("note","")+" [nominal, unmeasured]",
               "baebugs","NOMINAL_NOT_CALIBRATED","MIT_REPO_CONTEXT","VENDOR_MATERIAL_UNVERIFIED",
               "print/filters/filters.json","https://github.com/biobitworks/baebugs/blob/main/print/filters/filters.json",
               {"hole_shape":x.get("shape"),"params_mm":x.get("params_mm"),"hash_from_manifest":x.get("hash"),
                "realisation":x.get("realisation"),"fuse_printable":x.get("fuse_printable")},"sorter")
        edge(id,"stage:sorter","FILTER_OPTION")
    for key,d in sorted(read("daisy/datasets.json").get("datasets",{}).items()):
        src="gbif" if key.startswith(("gbif","pseudo","r3","holdout")) else "baebugs"
        add("dataset:"+key,"dataset",key,"Dataset inventory entry; media not redistributed on site.",
            src,d.get("status","UNKNOWN"),"PER_RECORD_OR_UNKNOWN","NOT_RELICENSED",
            "daisy/datasets.json","",{"declared_merkle_root":d.get("merkle_root"),
            "role":d.get("role"),"bytes_separately_reverified":"NOT_TESTED"},"camera")
        edge("source:"+src,"dataset:"+key,"REGISTERS")
    add("experiment:002a","experiment","DAISY-BB-002a","41 source events with independent source-event-root recomputation.",
        "baebugs","EXECUTED_EXPLORATORY","MIT_REPO_CONTEXT","TRAINING_METADATA_ONLY",
        "daisy/results/DAISY-BB-002a/v2/results.json","",
        {"events_root":TRAIN,"model_weights":"NOT_RECOVERED","human_truth":"NOT_TESTED"},"camera")
    edge("stage:camera","experiment:002a","EVALUATED_BY")
    add("ticket:2","ticket","P1 Lost best.pt checkpoints","Open GitHub Issue #2; no human approval implied.",
       "baebugs","OPEN","MIT_REPO_CONTEXT","HUMAN_DECISION_PENDING","",
       "https://github.com/biobitworks/baebugs/issues/2",{"ticket_kind":"WEIGHT_EXPORT"})
    edge("ticket:2","experiment:002a","CHALLENGES_ARTIFACT")
    for key,title,body,status,src,bound in CLAIMS:
        add("claim:"+key,"claim",title,body,src,status,"SOURCE_SPECIFIC",
            "CLAIM_BOUNDARY_DISCLOSED","","",{"limit":bound})
        edge("source:"+src,"claim:"+key,"ATTRIBUTED_CONTEXT")
    for key in ("photo","toys"):edge("experiment:002a","claim:"+key,"SUPPORTS_EXPLORATORY")
    for key in ("trommel_zone_2mm","trommel_zone_4mm","trommel_zone_7mm"):
        edge("part:"+key,"claim:parts","EXAMPLE_OF")
    ordered=["sorter","disperser","picker","dispenser","incubator"]
    for a,b in zip(ordered,ordered[1:]):edge("stage:"+a,"stage:"+b,"PROPOSED_WORKFLOW")
    add("breakpoint:cad14","breakpoint","Historical CAD 14-leaf MMR","Reference only, not cryptographically spliced.",
        "baebugs","PREDECESSOR_REFERENCE","MIT_REPO_CONTEXT","NOT_MERGED","","",{"root":PARENT,"signed":False})
    add("breakpoint:002a41","breakpoint","Historical DAISY 41-event root","Referenced provenance, separate construction.",
        "baebugs","SOURCE_RECOMPUTED","MIT_REPO_CONTEXT","NOT_MERGED",
        "daisy/results/DAISY-BB-002a/v2/events.jsonl","",{"root":TRAIN,"signed":False})
    edge("breakpoint:002a41","experiment:002a","INCLUDES_SOURCE_EVENTS")
    edge("breakpoint:cad14","breakpoint:002a41","DECLARED_CROSS_LANE_REFERENCE")
    # Each declared FCG edge is a separate immutable addressable *atom* as well.
    # This makes the Merkle root commit both scientific objects and their typed
    # declared graph relationships. Edges remain noncausal until independently tested.
    edge_snapshot=sorted(e,key=lambda v:(v["from"],v["to"],v["type"],v["status"]))
    for relation in edge_snapshot:
        payload={k:relation[k] for k in ("from","to","type","status")}
        edge_hash=h(canon(payload))
        node_id="fcg-edge:"+edge_hash
        add(node_id,"fcg_edge",
            payload["type"]+" / "+payload["from"]+" → "+payload["to"],
            "Typed relationship proposed or sourced from repository declarations; causal effect NOT_ESTABLISHED.",
            "baebugs","DECLARED_NOT_CAUSAL","ENDPOINT_SPECIFIC","DECLARED_NOT_CAUSAL",
            "","",{"relationship":payload,"relationship_sha256":edge_hash})
        relation["atom_id"]=node_id
    ids={x["id"] for x in n}
    if any(x["from"] not in ids or x["to"] not in ids or x["atom_id"] not in ids for x in e):raise ValueError("DANGLING_EDGE")
    return sorted(n,key=lambda v:v["id"]),edge_snapshot,dict(sorted(files.items()))
def tree(nodes):
    leaf=[h(b"baebugs:aok:leaf:v1\x00"+canon(n)) for n in nodes]
    proofs=[[] for _ in leaf]
    level=leaf[:];clusters=[[i] for i in range(len(leaf))]
    while len(level)>1:
        nxt=[];ng=[]
        for i in range(0,len(level),2):
            a=level[i];b=level[i+1] if i+1<len(level) else a
            left=clusters[i];right=clusters[i+1] if i+1<len(level) else []
            for j in left:proofs[j].append({"side":"right","hash":b})
            for j in right:proofs[j].append({"side":"left","hash":a})
            nxt.append(h(b"baebugs:aok:node:v1\x00"+bytes.fromhex(a)+bytes.fromhex(b)))
            ng.append(left+right)
        level,clusters=nxt,ng
    return (level[0] if level else "0"*64),leaf,proofs
def proof_ok(leaf,steps,root):
    for v in steps:
        if v["side"]=="left":a,b=v["hash"],leaf
        elif v["side"]=="right":a,b=leaf,v["hash"]
        else:return False
        leaf=h(b"baebugs:aok:node:v1\x00"+bytes.fromhex(a)+bytes.fromhex(b))
    return leaf==root
def generate():
    nodes,edges,files=build_records()
    root,leaves,proofs=tree(nodes)
    reg={"schema":"baebugs.aok.graph.v1","root":root,"algorithm":ALGO,"nodes":nodes,"edges":edges}
    receipt={"schema":"baebugs.aok.root.v1","algorithm":ALGO,"root":root,"size":len(nodes),
             "construction":"sorted node id, canonical JSON; SHA256('baebugs:aok:leaf:v1\\0'||node), parents SHA256('baebugs:aok:node:v1\\0'||binary(left)||binary(right)), odd-last duplicated",
             "ordered_leaves":[{"index":i,"id":n["id"],"sha256":leaves[i],"canonical_utf8":canon(n).decode("utf-8"),"proof":proofs[i]} for i,n in enumerate(nodes)],
             "references":[{"root":PARENT,"type":"DECLARED_NOT_MERGED","name":"CAD14"},
                           {"root":TRAIN,"type":"DECLARED_NOT_MERGED","name":"DAISY002a"}],
             "signed":"NOT_SIGNED","historical_mmr_commit":"NOT_COMPUTED",
             "truth":"IDENTITY_AND_DECLARATIONS_ONLY"}
    manifest={"schema":"baebugs.aok.sources.v1","source_hashes":files,"source_git_commit":SOURCE_REV,"node_count":len(nodes),
             "edge_count":len(edges),"root":root}
    O.mkdir(parents=True,exist_ok=True)
    for name,doc in (("graph.json",reg),("root.json",receipt),("manifest.json",manifest)):
        (O/name).write_bytes(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n")
    return {"root":root,"nodes":len(nodes),"edges":len(edges),"sources":len(files)}
def verify():
    reg=read("site/aok/data/graph.json");receipt=read("site/aok/data/root.json");manifest=read("site/aok/data/manifest.json")
    root,leaves,_=tree(reg["nodes"]);errors=[]
    if any(x!=root for x in (reg["root"],receipt["root"],manifest["root"])):errors.append("ROOT_MISMATCH")
    if len(receipt["ordered_leaves"])!=len(leaves):errors.append("COUNT_MISMATCH")
    for i,n in enumerate(reg["nodes"]):
        r=receipt["ordered_leaves"][i]
        if r["id"]!=n["id"] or r["sha256"]!=leaves[i] or not proof_ok(leaves[i],r["proof"],root):errors.append("INCLUSION_MISMATCH:"+n["id"])
        if n["fco_id"]!="fco:sha256:"+h(canon(n["content"])):errors.append("FCO_IDENTITY:"+n["id"])
        if n["occurrence_id"]!="occ:sha256:"+h(canon(n["context"])):errors.append("OCCURRENCE_IDENTITY:"+n["id"])
    lookup={n["id"]:n for n in reg["nodes"]};ids=set(lookup)
    for edge in reg["edges"]:
        if edge["from"] not in ids or edge["to"] not in ids or edge.get("atom_id") not in ids:
            errors.append("DANGLING_EDGE");continue
        atom=lookup[edge["atom_id"]]
        payload={k:edge[k] for k in ("from","to","type","status")}
        if atom["type"]!="fcg_edge" or atom["details"].get("relationship")!=payload or atom["details"].get("relationship_sha256")!=h(canon(payload)):
            errors.append("EDGE_ATOM_MISMATCH:"+edge["atom_id"])
    for path,d in manifest["source_hashes"].items():
        if fpath(path)!=d:errors.append("SOURCE_DRIFT:"+path)
    return {"PASS":not errors,"root":root,"nodes":len(leaves),"edges":len(reg["edges"]),
            "source_files_rehashed":len(manifest["source_hashes"]),"errors":errors,
            "signed":False,"scientific_truth":"NOT_DETERMINED","history_spliced":False}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("cmd",choices=["build","verify","doctor","list","get","search","proof"])
    ap.add_argument("item",nargs="?");a=ap.parse_args()
    if a.cmd=="build":res=generate()
    elif a.cmd in ("verify","doctor"):
        res=verify()
        if a.cmd=="doctor":res["warnings"]=["Source license and copyright need human review","Physical and taxonomic novelty NOT_TESTED","Gum is a UI tool, not a builtin doctor","Contest issues pending review do not modify canonical root"]
    else:
        graph=read("site/aok/data/graph.json")
        if a.cmd=="list":res=[{"id":n["id"],"title":n["title"]} for n in graph["nodes"]]
        elif a.cmd=="search":res=[n for n in graph["nodes"] if a.item and a.item.lower() in canon(n).decode().lower()]
        elif a.cmd=="get":res=next((n for n in graph["nodes"] if n["id"]==a.item),None)
        else:
            r=read("site/aok/data/root.json");x=next((n for n in r["ordered_leaves"] if n["id"]==a.item),None)
            res={"root":r["root"],**x,"verified":proof_ok(x["sha256"],x["proof"],r["root"])} if x else None
        if res is None:raise SystemExit("UNKNOWN_ID")
    print(json.dumps(res,ensure_ascii=False,indent=2))
    if isinstance(res,dict) and res.get("PASS") is False:raise SystemExit(1)
if __name__=="__main__":main()
