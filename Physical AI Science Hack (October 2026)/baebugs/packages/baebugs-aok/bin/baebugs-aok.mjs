#!/usr/bin/env node
/** Offline Baebugs AoK query + independent Merkle/FCO verification, zero external dependencies. */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import {fileURLToPath} from "node:url";
const here=path.dirname(fileURLToPath(import.meta.url));
const loc=path.resolve(here,"../data");
function load(name){return JSON.parse(fs.readFileSync(path.join(loc,name),"utf8"))}
function norm(x){return Array.isArray(x)?x.map(norm):x!==null&&typeof x==="object"?Object.fromEntries(Object.keys(x).sort().map(k=>[k,norm(x[k])])):x}
function canonical(x){return JSON.stringify(norm(x))}
function H(...bytes){const h=crypto.createHash("sha256");for(const b of bytes)h.update(b);return h.digest("hex")}
const bytes=x=>Buffer.from(x,"hex");
function verify(){
 const graph=load("graph.json"),r=load("root.json"),man=load("manifest.json"),fail=[];
 if(r.root!==graph.root||r.root!==man.root)fail.push("ROOT_RECORD_MISMATCH");
 if(r.size!==graph.nodes.length)fail.push("SIZE");
 const ordered=[...graph.nodes].sort((a,b)=>a.id.localeCompare(b.id,"en"));
 // Node locale sorting for display only; tree checks original graph order.
 if(new Set(graph.nodes.map(n=>n.id)).size!==graph.nodes.length)fail.push("DUPLICATE_ID");
 let level=[];
 for(let i=0;i<graph.nodes.length;i++){
  const n=graph.nodes[i],p=r.ordered_leaves[i];
  if(!p||n.id!==p.id){fail.push("INDEX_"+i);continue}
  if(canonical(JSON.parse(p.canonical_utf8))!==canonical(n))fail.push("SEMANTIC_DRIFT:"+n.id);
  const leaf=H("baebugs:aok:leaf:v1\0",p.canonical_utf8);
  if(leaf!==p.sha256)fail.push("LEAF:"+n.id);
  const ch=H(n.content_canonical_utf8),cx=H(n.context_canonical_utf8);
  if(ch!==n.fco_id.replace("fco:sha256:","")||cx!==n.occurrence_id.replace("occ:sha256:",""))fail.push("FCO:"+n.id);
  if(canonical(JSON.parse(n.content_canonical_utf8))!==canonical(n.content))fail.push("CONTENT_DRIFT:"+n.id);
  if(canonical(JSON.parse(n.context_canonical_utf8))!==canonical(n.context))fail.push("CONTEXT_DRIFT:"+n.id);
  let q=leaf;
  for(const s of p.proof){q=H("baebugs:aok:node:v1\0",bytes(s.side==="left"?s.hash:q),bytes(s.side==="left"?q:s.hash))}
  if(q!==r.root)fail.push("PROOF:"+n.id);
  level.push(leaf)
 }
 while(level.length>1){
  const next=[];
  for(let i=0;i<level.length;i+=2)next.push(H("baebugs:aok:node:v1\0",bytes(level[i]),bytes(level[i+1]??level[i])));
  level=next
 }
 if(level[0]!==r.root)fail.push("TREE_RECOMPUTE");
 const ids=new Set(graph.nodes.map(n=>n.id));
 for(const e of graph.edges)if(!ids.has(e.from)||!ids.has(e.to))fail.push("DANGLING_EDGE");
 return {PASS:fail.length===0,root:r.root,leaves:r.size,edges:graph.edges.length,issues:fail,
         source_bytes_checked:false,signature:"NOT_SIGNED",science:"NOT_VERIFIED",historical_mmr_merged:false}
}
function main(){
 const [cmd="verify",query]=process.argv.slice(2);
 if(cmd==="verify"||cmd==="doctor"){
  const r=verify();if(cmd==="doctor")r.note="Packaged snapshot verifies inclusion and local metadata; source repo bytes not packed.";
  console.log(JSON.stringify(r,null,2));if(!r.PASS)process.exitCode=1;return
 }
 const graph=load("graph.json");
 if(cmd==="list"){console.log(JSON.stringify(graph.nodes.map(n=>({id:n.id,title:n.title,type:n.type})),null,2));return}
 if(cmd==="search"){console.log(JSON.stringify(graph.nodes.filter(n=>JSON.stringify(n).toLowerCase().includes((query||"").toLowerCase())),null,2));return}
 if(cmd==="get"||cmd==="proof"){
  const n=graph.nodes.find(n=>n.id===query);if(!n){console.error("UNKNOWN_ID");process.exitCode=2;return}
  const root=load("root.json");
  console.log(JSON.stringify(cmd==="get"?n:{root:root.root,...root.ordered_leaves.find(x=>x.id===n.id)},null,2));return
 }
 console.error("USAGE: baebugs-aok [verify|doctor|list|search QUERY|get ID|proof ID]");process.exitCode=2
}
main();
