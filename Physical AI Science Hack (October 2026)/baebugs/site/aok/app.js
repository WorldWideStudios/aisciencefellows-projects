"use strict";
const $=id=>document.getElementById(id);
let graph,receipt,selected,labStage="sorter",candidate=null;
const enc=new TextEncoder(),COLORS={source:"#89accc",part:"#e2c686",module:"#8cd6bd",claim:"#d1a4dc",dataset:"#789caa",filter:"#75b7a4",experiment:"#b1bed4",breakpoint:"#dd8f8f",ticket:"#f0ad72"};
const sha=async a=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",a))).map(x=>x.toString(16).padStart(2,"0")).join("");
const bytes=h=>new Uint8Array(h.match(/../g).map(x=>parseInt(x,16)));
const join=(...items)=>{let u=new Uint8Array(items.reduce((n,v)=>n+v.length,0)),i=0;for(const a of items){u.set(a,i);i+=a.length}return u};
const norm=v=>Array.isArray(v)?v.map(norm):v!==null&&typeof v==="object"?Object.fromEntries(Object.keys(v).sort().map(k=>[k,norm(v[k])])):v;
const canonical=v=>JSON.stringify(norm(v));
const get=id=>graph.nodes.find(n=>n.id===id);
const text=(id,value)=>$(id).textContent=value==null?"UNKNOWN":String(value);
const elt=(tag,value,cls)=>{const x=document.createElement(tag);if(value!=null)x.textContent=value;if(cls)x.className=cls;return x};
const svg=(tag,attrs={})=>{const x=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const[k,v]of Object.entries(attrs))x.setAttribute(k,String(v));return x};
const linkages=id=>graph.edges.filter(e=>e.from===id||e.to===id).map(e=>({id:e.from===id?e.to:e.from,type:e.type,direction:e.from===id?"→":"←",status:e.status,atom_id:e.atom_id}));
async function copy(s){await navigator.clipboard.writeText(s)}
function copier(id,s){const b=$(id);b.textContent=s||"UNKNOWN";b.onclick=()=>copy(s).then(()=>{b.title="Copied";setTimeout(()=>b.title="Click to copy",1400)}).catch(()=>{b.title="Clipboard unavailable"})}
function show(view){
 for(const b of document.querySelectorAll(".tab")){const ok=b.dataset.view===view;b.classList.toggle("active",ok);if(ok)b.setAttribute("aria-current","page");else b.removeAttribute("aria-current")}
 for(const s of document.querySelectorAll(".view"))s.classList.toggle("shown",s.id==="view-"+view);
 history.replaceState(null,"",location.pathname+"?view="+encodeURIComponent(view)+(selected?"&node="+encodeURIComponent(selected):""))
}
function select(id,view="explore"){if(!get(id))return;selected=id;show(view);details();results();network()}
function options(id,items){for(const v of items){const o=elt("option",v);o.value=v;$(id).append(o)}}
function filtered(){
 const typ=$("typeFilter").value,lic=$("rightsFilter").value,st=$("stageFilter").value,status=$("statusFilter").value,q=$("search").value.trim().toLowerCase();
 return graph.nodes.filter(n=>(!typ||n.type===typ)&&(!lic||n.license===lic)&&(!st||n.stage===st)&&(!status||n.status===status)&&(!q||JSON.stringify(n).toLowerCase().includes(q)))
}
function results(){
 const list=$("searchResults");list.replaceChildren();let a=filtered();text("resultsTotal",a.length+" matching objects");
 for(const n of a.slice(0,100)){
  const b=elt("button",null,"result-item"+(n.id===selected?" selected":""));
  b.append(elt("b",n.title),elt("small",n.type+" · "+n.status+" · "+n.license));
  b.onclick=()=>select(n.id);list.append(b)
 }
 if(a.length>100)list.append(elt("div","Showing first 100. Refine search.","minor"))
}
function details(){
 const n=get(selected),rel=linkages(selected);
 text("detailTitle",n.title);text("detailBody",n.body);text("detailType",n.type.toUpperCase());text("detailLicense",n.license);
 text("detailSource",n.source+(n.source_path?" · "+n.source_path:""));text("detailStatus",n.status);
 $("detailStatus").className="status "+(/UNKNOWN|FAIL|NOT_TESTED|NOT_CALIBRATED|NOT_FOUND/.test(n.status)?"caution":"");
 copier("fcoCopy",n.fco_id);copier("occCopy",n.occurrence_id);
 const r=receipt.ordered_leaves.find(v=>v.id===selected);copier("leafCopy",r?.sha256||"NOT_COMPUTED");
 text("inclusion","VERIFYING…");verifyOne(selected).then(ok=>{text("inclusion",ok?"PASS · exact record inclusion":"FAIL · mismatch");$("inclusion").style.color=ok?"#91e1c8":"#f0a0a0"});
 const sr=$("sourceURL");sr.href=n.url|| (n.source_path?"https://github.com/biobitworks/baebugs/blob/3a1806000ec4ca38e25f2749712d54b82ef612af/"+n.source_path:"#");sr.classList.toggle("hidden",sr.getAttribute("href")==="#");
 const list=$("relationships");list.replaceChildren();
 for(const x of rel.slice(0,55)){
  const y=get(x.id),b=elt("button",null,"relation");
  b.append(elt("b",y?.title||x.id),elt("span",x.direction+" "+x.type+" · "+x.status));b.onclick=()=>select(x.id);list.append(b);if(x.atom_id){const leaf=elt("button","Inspect FCG leaf ↗","relation");leaf.onclick=()=>select(x.atom_id);list.append(leaf)}
 }
 const ex=$("detailExtra");ex.replaceChildren();ex.append(elt("div","Rights: "+n.rights),elt("div","Source exact SHA-256: "+(n.source_sha256||"UNKNOWN")),elt("pre",JSON.stringify(n.details,null,2),"snippet"));
 $("contestButton").onclick=()=>{$("contestNode").value=selected;show("challenge")}
}
function network(){
 const root=get(selected),rel=linkages(selected).filter(e=>get(e.id)).sort((a,b)=>a.id.localeCompare(b.id)).slice(0,17);
 const p=new Map([[selected,{x:305,y:189}]]);
 rel.forEach((n,i)=>{const a=i*2*Math.PI/Math.max(rel.length,1)-Math.PI/2;p.set(n.id,{x:305+Math.cos(a)*211,y:189+Math.sin(a)*135})});
 const v=$("graph");v.replaceChildren();
 for(const n of rel){const q=p.get(n.id);v.append(svg("line",{x1:305,y1:189,x2:q.x,y2:q.y,class:"graph-edge"}))}
 for(const[id,q]of p){
  const n=get(id),focus=id===selected,g=svg("g",{class:"graph-node"+(focus?" active":""),tabindex:"0",role:"button","aria-label":n.title});
  g.append(svg("circle",{cx:q.x,cy:q.y,r:focus?28:19,fill:COLORS[n.type]||"#78959a"}));
  const symbol=svg("text",{x:q.x,y:q.y+3,fill:"#0c2028","text-anchor":"middle","font-size":"11","font-weight":"800"});symbol.textContent=n.type.slice(0,2).toUpperCase();g.append(symbol);
  const label=svg("text",{x:q.x,y:q.y+(focus?46:35),class:"graph-label"+(focus?"":" muted")});label.textContent=n.title.length>25?n.title.slice(0,22)+"…":n.title;g.append(label);
  g.onclick=()=>select(id);g.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();select(id)}};v.append(g)
 }
 text("graphSubtitle",rel.length+" neighbors"+(linkages(selected).length>17?" (top 17 shown)":""))
}
async function verifyOne(id){
 const n=get(id),r=receipt.ordered_leaves.find(v=>v.id===id);
 if(!n||!r)return false;
 if(canonical(JSON.parse(r.canonical_utf8))!==canonical(n))return false;
 if(canonical(JSON.parse(n.content_canonical_utf8))!==canonical(n.content))return false;
 if(canonical(JSON.parse(n.context_canonical_utf8))!==canonical(n.context))return false;
 if("fco:sha256:"+await sha(enc.encode(n.content_canonical_utf8))!==n.fco_id)return false;
 if("occ:sha256:"+await sha(enc.encode(n.context_canonical_utf8))!==n.occurrence_id)return false;
 let x=await sha(join(enc.encode("baebugs:aok:leaf:v1\0"),enc.encode(r.canonical_utf8)));
 if(x!==r.sha256)return false;
 for(const p of r.proof){x=await sha(join(enc.encode("baebugs:aok:node:v1\0"),bytes(p.side==="left"?p.hash:x),bytes(p.side==="left"?x:p.hash)))}
 return x===receipt.root && receipt.root===graph.root
}
async function verifyAll(){
 text("rootState","VERIFYING");
 try{if(graph.nodes.length!==receipt.size)throw Error("SIZE");
  for(const n of graph.nodes)if(!await verifyOne(n.id))throw Error(n.id);
  for(const edge of graph.edges){
   const atom=get(edge.atom_id);
   const payload={from:edge.from,to:edge.to,type:edge.type,status:edge.status};
   if(!atom||atom.type!=="fcg_edge"||canonical(atom.details.relationship)!==canonical(payload)||atom.details.relationship_sha256!==await sha(enc.encode(canonical(payload))))throw Error("FCG mismatch");
  }
  text("rootState","PASS · "+receipt.size+" LEAVES");$("rootState").className="status";return true
 }catch(e){text("rootState","FAIL · "+e.message);$("rootState").className="status caution";return false}
}
function lab(id){
 labStage=id;$("labSelection").value=id;const n=get("stage:"+id);
 text("labTitle",n.title);text("labDesc",n.body);text("labState",n.status);
 const parts=graph.edges.filter(e=>e.to===n.id && ["DESIGNED_FOR","FILTER_OPTION"].includes(e.type)).map(e=>get(e.from)).filter(Boolean);
 const p=$("labParts");p.replaceChildren();for(const x of parts.slice(0,18)){const b=elt("button",x.title);b.onclick=()=>select(x.id);p.append(b)}
 if(!parts.length)p.append(elt("div","No verified physical parts yet.","minor"));
 const v=$("labDrawing");v.replaceChildren();
 const modes=["sorter","disperser","picker","dispenser","incubator"];
 const positions=[...modes.map((k,i)=>({k,x:30+i*178,y:77})),...["camera","robot","opentrons","filtration"].map((k,i)=>({k,x:30+i*198,y:248}))];
 for(let i=0;i<4;i++)v.append(svg("line",{x1:183+i*178,y1:129,x2:205+i*178,y2:129,class:"lab-connector"}));
 for(const a of positions){
  const q=get("stage:"+a.k),g=svg("g",{class:"lab-node"+(a.k===id?" selected":""),tabindex:"0",role:"button","aria-label":q.title});
  g.append(svg("rect",{x:a.x,y:a.y,width:156,height:107,rx:12,fill:a.k===id?"#1d4d44":"#17323a"}));
  const label=svg("text",{x:a.x+13,y:a.y+24,class:"lab-id"});label.textContent=modes.includes(a.k)?"0"+(modes.indexOf(a.k)+1):"AUX";g.append(label);
  const name=svg("text",{x:a.x+13,y:a.y+52,class:"lab-name"});name.textContent=q.title.slice(0,20);g.append(name);
  const sub=svg("text",{x:a.x+13,y:a.y+77,class:"lab-sub"});sub.textContent=q.status.slice(0,22);g.append(sub);
  g.onclick=()=>lab(a.k);g.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();lab(a.k)}};v.append(g)
 }
}
function rights(){
 const tbl=$("rightsTable");tbl.replaceChildren();
 for(const n of graph.nodes.filter(n=>n.type==="source")){
  const tr=elt("tr"),td=elt("td"),a=elt("a",n.title);a.href=n.url||"#";a.target="_blank";a.rel="noopener";td.append(a);
  tr.append(td,elt("td",n.license),elt("td",n.status),elt("td",n.body));
  const cell=elt("td"),button=elt("button","Inspect","quiet");button.onclick=()=>select(n.id);cell.append(button);tr.append(cell);tbl.append(tr)
 }
}
async function contest(ev){
 ev.preventDefault();const n=get($("contestNode").value),claim=$("counterClaim").value.trim(),url=$("counterEvidence").value.trim();
 if(!n||!claim||!url){text("contestPreview","Provide a claim and evidence URL.");return}
 try{const u=new URL(url);if(!["https:","http:"].includes(u.protocol))throw Error("scheme")}
 catch(e){text("contestPreview","Evidence must be an HTTP(S) URL.");return}
 const body={schema:"baebugs.contest.fco.v1",counterclaim:claim,evidence_url:url,
             license_status:$("counterLicense").value,reference_node:n.id,reference_fco:n.fco_id,
             predecessor_root:receipt.root,state:"PROPOSED_NOT_ADMITTED"};
 const fco="fco:sha256:"+await sha(enc.encode(canonical(body)));
 const edge={schema:"baebugs.contest.fcg.v1",from:fco,to:n.fco_id,
             relation:$("counterRelation").value,state:"PROPOSED_NOT_ADMITTED",causality:"NOT_ESTABLISHED"};
 const fcg="fcg:sha256:"+await sha(enc.encode(canonical(edge)));
 candidate={fco:{id:fco,body},fcg:{id:fcg,edge},signed:"NOT_SIGNED",admitted:false};
 text("contestPreview",JSON.stringify(candidate,null,2));$("contestButtons").classList.remove("hidden");
 const title="AoK contest: "+n.id;
 const issue="Candidate FCO/FCG counterevidence\n\n"+JSON.stringify(candidate,null,2)+"\n\nStatus: HUMAN_REVIEW_REQUIRED. No current Merkle root modified.";
 $("submitIssue").href="https://github.com/biobitworks/baebugs/issues/new?title="+encodeURIComponent(title)+"&body="+encodeURIComponent(issue)
}
function download(){
 if(!candidate)return;
 const blob=new Blob([JSON.stringify(candidate,null,2)+"\n"],{type:"application/json"}),a=elt("a");
 a.href=URL.createObjectURL(blob);a.download="counterevidence-"+candidate.fco.id.slice(-12)+".json";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),3000)
}
async function init(){
 try{
  const [g,r]=await Promise.all([fetch("data/graph.json"),fetch("data/root.json")]);
  if(!g.ok||!r.ok)throw Error("Missing graph files");
  graph=await g.json();receipt=await r.json();
  text("nodesCount",graph.nodes.length);text("edgesCount",graph.edges.length);
  text("partCount",graph.nodes.filter(n=>n.type==="part").length);
  text("caveatCount",graph.nodes.filter(n=>/UNKNOWN|NOT_TESTED|NOT_CALIBRATED|NOT_FOUND|NOT_RECOVERED/.test(n.status+" "+n.license)).length);
  text("snapshotCount",receipt.size+" leaves · "+graph.edges.length+" relations");copier("rootCopy",receipt.root);
  for(const [id,key]of [["typeFilter","type"],["rightsFilter","license"],["stageFilter","stage"],["statusFilter","status"]])
    options(id,[...new Set(graph.nodes.map(n=>n[key]).filter(Boolean))].sort());
  for(const id of ["search","typeFilter","rightsFilter","stageFilter","statusFilter"])$(id).addEventListener(id==="search"?"input":"change",results);
  for(const b of document.querySelectorAll(".tab"))b.onclick=()=>show(b.dataset.view);
  $("centerGraph").onclick=network;$("verifyAll").onclick=verifyAll;
  $("contestForm").addEventListener("submit",contest);
  $("contestForm").addEventListener("reset",()=>{candidate=null;text("contestPreview","Fill in the form to create a candidate FCO and typed relationship.");$("contestButtons").classList.add("hidden")});
  $("copyContest").onclick=()=>copy(JSON.stringify(candidate,null,2));
  $("downloadContest").onclick=download;
  for(const n of graph.nodes){const o=elt("option",n.title+" · "+n.id);o.value=n.id;$("contestNode").append(o)}
  for(const n of graph.nodes.filter(n=>n.type==="module")){const o=elt("option",n.title);o.value=n.id.slice(6);$("labSelection").append(o)}
  $("labSelection").onchange=()=>lab($("labSelection").value);
  $("showConnected").onclick=()=>select("stage:"+labStage);
  lab("sorter");rights();
  const params=new URLSearchParams(location.search),id=params.get("node"),view=params.get("view");
  selected=get(id)?id:"stage:sorter";details();results();network();
  show(["explore","lab","rights","challenge","agents"].includes(view)?view:"explore");
  await verifyAll()
 }catch(e){text("rootState","LOAD FAILED");text("snapshotCount",e.message);console.error(e)}
}
init();
