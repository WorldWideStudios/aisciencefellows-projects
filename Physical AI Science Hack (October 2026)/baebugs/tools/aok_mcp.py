#!/usr/bin/env python3
"""Minimal read-only JSON-RPC MCP (newline-delimited stdio) for local agents.

Protocol 2025-06-18 subset: initialize, tools/list, tools/call. No data writes,
no remote services, no filesystem parameter interpolation. No auto-trust.
"""
import json,pathlib,sys,importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location("aok_build",ROOT/"tools/aok_build.py")
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
PROTOCOL="2025-06-18"
TOOLS=[
 {"name":"aok_verify","description":"Independently recompute Merkle root, FCO identity, source hash and inclusion proofs.",
  "inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
 {"name":"aok_get","description":"Get a single AoK/FCO node by stable id.",
  "inputSchema":{"type":"object","properties":{"id":{"type":"string"}},"required":["id"],"additionalProperties":False}},
 {"name":"aok_proof","description":"Get ordered Merkle inclusion path for a node id.",
  "inputSchema":{"type":"object","properties":{"id":{"type":"string"}},"required":["id"],"additionalProperties":False}},
 {"name":"aok_search","description":"Read-only case-insensitive search of titles, rights, source and context.",
  "inputSchema":{"type":"object","properties":{"q":{"type":"string"}},"required":["q"],"additionalProperties":False}}
]
def action(name,args):
    if name=="aok_verify":return M.verify()
    graph=M.read("site/aok/data/graph.json")
    if name=="aok_get":
        return next((x for x in graph["nodes"] if x["id"]==args.get("id")),{"error":"UNKNOWN_NODE"})
    if name=="aok_proof":
        doc=M.read("site/aok/data/root.json")
        row=next((x for x in doc["ordered_leaves"] if x["id"]==args.get("id")),None)
        return {"root":doc["root"],"row":row,"verified":bool(row and M.proof_ok(row["sha256"],row["proof"],doc["root"]))}
    if name=="aok_search":
        q=str(args.get("q","")).lower()[:256]
        return [{"id":x["id"],"title":x["title"],"status":x["status"],"license":x["license"]}
                for x in graph["nodes"] if q in json.dumps(x).lower()][:75]
    return {"error":"UNKNOWN_TOOL"}
def receive(request):
    method=request.get("method");rid=request.get("id")
    if rid is None:return None
    if method=="initialize":
        res={"protocolVersion":PROTOCOL,"capabilities":{"tools":{}},"serverInfo":{"name":"baebugs-aok-readonly","version":"0.1.0"}}
    elif method=="tools/list":res={"tools":TOOLS}
    elif method=="tools/call":
        params=request.get("params") or {}
        name=params.get("name");args=params.get("arguments") or {}
        if name not in {x["name"] for x in TOOLS}:
            return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"UNKNOWN_TOOL"}}
        data=action(name,args)
        res={"content":[{"type":"text","text":json.dumps(data,sort_keys=True)}],"isError":bool(data.get("error")) if isinstance(data,dict) else False}
    else:return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"UNKNOWN_METHOD"}}
    return {"jsonrpc":"2.0","id":rid,"result":res}
def main():
    for line in sys.stdin:
        if len(line)>250000:
            print(json.dumps({"jsonrpc":"2.0","id":None,"error":{"code":-32600,"message":"REQUEST_TOO_LARGE"}}),flush=True)
            continue
        try:
            msg=json.loads(line)
            ans=receive(msg)
            if ans is not None:print(json.dumps(ans,separators=(",",":")),flush=True)
        except Exception as e:
            print(json.dumps({"jsonrpc":"2.0","id":None,"error":{"code":-32603,"message":"INTERNAL_ERROR:"+type(e).__name__}}),flush=True)
if __name__=="__main__":main()
