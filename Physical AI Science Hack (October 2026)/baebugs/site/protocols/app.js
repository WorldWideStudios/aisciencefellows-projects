"use strict";
(function () {
 const $=s=>document.querySelector(s);
 const esc=v=>String(v==null?"":v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const KEY="baebugs-protocols-v1";
 function getState(){try{return JSON.parse(localStorage.getItem(KEY)||"{}")}catch{return {}}}
 const prior=getState();
 const S={catalog:null,category:"All",view:"all",query:"",selected:null,parent:null,
   saved:new Set(Array.isArray(prior.saved)?prior.saved:[]),
   custom:Array.isArray(prior.custom)?prior.custom:[],
   collections:prior.collections&&typeof prior.collections==="object"?prior.collections:{},
   sessions:prior.sessions&&typeof prior.sessions==="object"?prior.sessions:{}};
 function persist(){try{localStorage.setItem(KEY,JSON.stringify({saved:[...S.saved],custom:S.custom,collections:S.collections,sessions:S.sessions}))}catch{toast("Storage unavailable. Export your private work.")}}
 function toast(t){$("#toast").textContent=t;$("#toast").classList.add("show");clearTimeout(toast.t);toast.t=setTimeout(()=>$("#toast").classList.remove("show"),3400)}
 const colors={cyan:["#214953","#102b33","#b3e9db"],amber:["#53432b","#292824","#f4c795"],orange:["#5d3b28","#302829","#f5b88f"],teal:["#20534b","#163136","#b2e9c8"],violet:["#4a3956","#232c40","#cfb5e8"],sky:["#38546b","#233646","#a6d8ed"],lime:["#435a3c","#23382c","#c9ecae"],pink:["#59404e","#2c2b3a","#efc1d8"],slate:["#3f4d56","#222c34","#c1cbd4"]};
 const sourceIcon={
 camera:'<rect x="90" y="50" width="177" height="111" rx="16"/><circle cx="179" cy="104" r="38"/><path d="M142 52V37h70v15M103 180h149"/><ellipse cx="147" cy="186" rx="12" ry="5"/><ellipse cx="192" cy="185" rx="16" ry="5"/>',
 filter:'<rect x="99" y="50" width="170" height="132" rx="15"/><path d="M122 65v100m23-100v100m23-100v100m23-100v100m23-100v100m23-100v100M112 87h142m-142 26h142m-142 26h142"/>',
 trommel:'<ellipse cx="111" cy="111" rx="28" ry="58"/><ellipse cx="248" cy="111" rx="28" ry="58"/><path d="M111 53h137M111 169h137M147 56q-22 55 0 110m48-110q-22 55 0 110M98 179v20h35m107-19v19h32M278 111h25v29h18"/>',
 vortex:'<ellipse cx="182" cy="132" rx="83" ry="29"/><path d="M99 132V87c0-17 39-28 83-28s83 11 83 28v45"/><ellipse cx="182" cy="87" rx="83" ry="27"/><ellipse cx="182" cy="87" rx="54" ry="15"/><path d="M89 170q-30-22-16-66m198 65q33-29 15-69"/>',
 robot:'<path d="M117 184h155M149 184v-28l26-35 29 5 25-41 24 10-16 45-29 13-26-8-10 15v24"/><circle cx="176" cy="120" r="10"/><circle cx="229" cy="85" r="10"/><path d="M252 89l17-17 12 14"/>',
 plate:'<rect x="93" y="62" width="187" height="119" rx="12"/><path d="M139 38v23m-12-28h24"/><circle cx="126" cy="94" r="8"/><circle cx="160" cy="94" r="8"/><circle cx="194" cy="94" r="8"/><circle cx="228" cy="94" r="8"/><circle cx="126" cy="124" r="8"/><circle cx="160" cy="124" r="8"/><circle cx="194" cy="124" r="8"/><circle cx="228" cy="124" r="8"/><circle cx="126" cy="154" r="8"/><circle cx="160" cy="154" r="8"/><circle cx="194" cy="154" r="8"/><circle cx="228" cy="154" r="8"/>',
 search:'<rect x="100" y="59" width="179" height="110" rx="12"/><circle cx="164" cy="106" r="32"/><path d="m189 131 31 31M213 84h48M213 102h40M213 120h45"/>',
 graph:'<circle cx="117" cy="100" r="20"/><circle cx="214" cy="72" r="19"/><circle cx="272" cy="153" r="20"/><circle cx="167" cy="171" r="17"/><path d="M135 96l59-18m27 13 38 46m-107 20-23-41m57 53 66-14m-83-3 38-63"/>',
 model:'<rect x="100" y="59" width="177" height="124" rx="12"/><path d="M119 164h139M119 164v-88M126 149l28-25 28 8 39-51 35 23"/><circle cx="155" cy="124" r="6"/><circle cx="221" cy="81" r="6"/>'};
 function art(r){const c=colors[r.accent]||colors.teal;return '<div class="card-scene" style="--scene0:'+c[0]+';--scene1:'+c[1]+'"><svg viewBox="0 0 360 230" aria-hidden="true" focusable="false"><g fill="none" stroke="'+c[2]+'" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'+(sourceIcon[r.motif]||sourceIcon.graph)+'</g></svg><span class="card-category">'+esc(r.category)+'</span></div>'}
 function all(){return (S.catalog?S.catalog.recipes:[]).concat(S.custom).filter(v=>v&&typeof v.id==="string")}
 function find(id){return all().find(v=>v.id===id)}
 function stored(id){return S.saved.has(id)||Object.values(S.collections).some(a=>Array.isArray(a)&&a.includes(id))}
 function categories(){return ["All"].concat([...new Set(all().map(v=>v.category||"My lab"))].sort())}
 function matched(){
  const q=S.query.toLowerCase().trim();
  return all().filter(r=>{
    if(S.view==="saved"&&!stored(r.id))return false;
    if(S.view==="mine"&&!r.local)return false;
    if(S.view.startsWith("collection:")&&!(S.collections[S.view.slice(11)]||[]).includes(r.id))return false;
    if(S.category!=="All"&&S.category!==r.category)return false;
    return !q||[r.name,r.subtitle,r.category,r.fit,(r.tags||[]).join(" "),(r.sources||[]).join(" ")].join(" ").toLowerCase().includes(q);
  });
 }
 function card(r){
  return '<article class="protocol-card" data-card="'+esc(r.id)+'">'+art(r).replace('</div>','<button class="bookmark-btn" type="button" data-bookmark="'+esc(r.id)+'" aria-label="'+esc(S.saved.has(r.id)?"Remove bookmark":"Bookmark")+' '+esc(r.name)+'" aria-pressed="'+S.saved.has(r.id)+'">'+(S.saved.has(r.id)?"★":"☆")+'</button></div>')+
   '<div class="card-copy"><span class="eyebrow muted">'+esc(r.local?"LOCAL / PRIVATE":r.stage.toUpperCase()+" / BAEBUGS")+'</span><h3>'+esc(r.name)+'</h3><p>'+esc(r.subtitle)+'</p>'+
   '<div class="meta-line"><span class="mini">'+esc(r.steps.length)+' review steps</span><span class="mini">'+esc(r.local?"PRIVATE":r.fit)+'</span><span class="mini '+(r.hardware_gate?"warn":"")+'">'+esc(r.hardware_gate?"HUMAN GATE":r.status.replaceAll("_"," "))+'</span></div>'+
   '<div class="card-footer"><span class="sourcelabel">'+(r.local?"Not publicly shared":r.sources.length+" source leaves")+'</span><button class="open-card" type="button" data-open="'+esc(r.id)+'">Explore protocol ↗</button></div></div></article>';
 }
 function render(){
  const sel=$("#show-mode");
  sel.querySelectorAll('optgroup[label="My collections"]').forEach(x=>x.remove());
  const names=Object.keys(S.collections).sort();
  if(names.length){
   const group=document.createElement("optgroup");group.label="My collections";
   names.forEach(n=>{const o=document.createElement("option");o.value="collection:"+n;o.textContent=n;group.appendChild(o)});
   sel.appendChild(group);
  }
  sel.value=S.view;
  $("#category-chips").innerHTML=categories().map(c=>'<button type="button" data-category="'+esc(c)+'" aria-pressed="'+(S.category===c)+'">'+esc(c)+'</button>').join("");
  const f=matched();
  $("#protocol-grid").innerHTML=f.map(card).join("");
  $("#empty-state").hidden=f.length>0;
  $("#result-count").textContent=f.length+" of "+all().length+" workflows · "+S.saved.size+" bookmarks · "+S.custom.length+" local drafts";
  $("#count-templates").textContent=S.catalog?.recipes.length||"—";
 }
 function openDialog(id){const el=$("#"+id);if(!el.open)el.showModal()}
 function closeDialog(button){button.closest("dialog")?.close()}
 function bookmark(id){if(S.saved.has(id))S.saved.delete(id);else S.saved.add(id);persist();render();if($("#protocol-dialog").open&&S.selected===id)details(id);toast(S.saved.has(id)?"Saved to bookmarks":"Bookmark removed")}
 function sourceLinks(r){
  if(!r.source_atoms)return "";
  return r.source_atoms.map(a=>{
   const url="https://github.com/biobitworks/baebugs/blob/"+S.catalog.source_commit+"/"+a.path.split("/").map(encodeURIComponent).join("/");
   return '<div class="source-item"><a target="_blank" rel="noopener noreferrer" href="'+esc(url)+'">'+esc(a.path)+'</a><span class="licence">'+esc(a.licence)+' · '+esc(a.claim)+' · '+esc(a.status)+'</span>sha256: '+esc(a.sha256.slice(0,20))+'… · leaf: '+esc(a.leaf.slice(0,14))+'… <a href="../#leaf:'+encodeURIComponent(a.path)+'">Open in graph</a></div>'
  }).join("");
 }
 function details(id){
  const r=find(id);if(!r)return;S.selected=id;
  $("#detail-kicker").textContent=r.local?"PRIVATE / YOUR WORKSPACE":"PUBLIC / SOURCE-BOUND";
  const steps=(r.steps||[]).map((s,i)=>'<li><span class="step-index">'+(i+1)+'</span><div><b>'+esc(s.title)+'</b><p>'+esc(s.detail||"")+'</p><span class="gate">'+esc(s.gate||"REVIEW_ONLY")+(s.source?" · "+esc(s.source):"")+'</span></div></li>').join("");
  $("#protocol-detail").innerHTML=[
    art(r).replace(' style="--scene0',' style="height:185px;--scene0'),
    '<h2 id="detail-heading">'+esc(r.name)+'</h2><p class="detail-summary">'+esc(r.subtitle)+'</p>',
    '<div class="detail-tags">'+(r.tags||[]).map(s=>'<span>'+esc(s)+'</span>').join("")+'<span>'+esc(r.local?"LOCAL_UNREVIEWED":r.status)+'</span></div>',
    '<div class="detail-evidence"><div class="detail-box"><b>Rights in context</b><small>'+esc(r.rights_note||"RIGHTS_UNKNOWN")+'</small><small>'+esc(r.execution_permission||"GUIDED_BROWSER_REVIEW_ONLY")+'</small></div>',
    '<div class="detail-box"><b>Content SHA-256</b><code>'+esc(r.content_sha256||"NOT_COMPUTED")+'</code><small>Not an MMR root. Physical outcome NOT_TESTED; NOT_SIGNED.</small></div></div>',
    (r.parent?'<div class="detail-box" style="margin-top:10px"><b>Remix predecessor</b><code>'+esc(r.parent.id)+" · "+esc(r.parent.content_sha256)+'</code></div>':""),
    '<h3 class="detail-section-heading">Guided review steps</h3><ol class="step-list">'+steps+'</ol>',
    (r.local?'<p class="privacy-note">Private user-authored text has NOT been independently verified or published.</p>':'<h3 class="detail-section-heading">Source-linked AoK / FCO references</h3><div class="source-list">'+sourceLinks(r)+'</div>'),
    '<div class="dialog-actions"><button type="button" class="btn subtle" id="detail-save">'+(S.saved.has(r.id)?"★ Bookmarked":"☆ Bookmark")+'</button><button type="button" class="btn subtle" id="detail-collection">Collect</button><button type="button" class="btn subtle" id="detail-remix">Remix</button><button type="button" class="btn subtle" id="detail-share">'+(r.local?"Export private JSON":"Share public link")+'</button><button type="button" class="btn primary" id="detail-review">Guided review ↗</button></div>',
    '<div id="detail-collection-entry" hidden class="detail-box" style="margin-top:13px"><label for="detail-collection-name">Collection name</label><input id="detail-collection-name" maxlength="80" placeholder="e.g. Field prep"><button id="detail-add-collection" class="btn subtle" type="button">Save to collection</button></div>'
   ].join("");
  openDialog("protocol-dialog");
 }
 async function sha256(v){const bytes=new TextEncoder().encode(v);const d=await crypto.subtle.digest("SHA-256",bytes);return [...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,"0")).join("")}
 function sortObject(v){if(Array.isArray(v))return v.map(sortObject);if(v&&typeof v==="object")return Object.fromEntries(Object.keys(v).sort().map(k=>[k,sortObject(v[k])]));return v}
 function stable(v){return JSON.stringify(sortObject(v))}
 function download(name,obj){const url=URL.createObjectURL(new Blob([JSON.stringify(obj,null,2)+"\n"],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 async function copy(s){try{await navigator.clipboard.writeText(s);return true}catch{return false}}
 function openEditor(parent){
  S.parent=parent||null;
  $("#edit-heading").textContent=parent?"Remix · "+parent.name:"Bring your own protocol";
  $("#editor-intro").textContent=parent?"Your copy stays local and preserves its predecessor identity.":"Paste a protocol or import JSON, Markdown or text. No upload occurs.";
  $("#edit-name").value=parent?parent.name+" · remix":"";
  $("#edit-notes").value=parent?parent.steps.map((s,i)=>(i+1)+". "+s.title+": "+(s.detail||"")).join("\n"):"";
  $("#edit-rights").value=parent?"DERIVED / RIGHTS_REVIEW_REQUIRED / "+parent.rights_note:"RIGHTS_UNKNOWN — REVIEW_REQUIRED";
  $("#edit-file").value="";$("#edit-status").textContent="";
  openDialog("edit-dialog");
 }
 function stepsFromText(text){
  const lines=text.split(/\r?\n/).map(s=>s.trim()).filter(Boolean).slice(0,16);
  return (lines.length?lines:[text]).map((s,i)=>({title:(s.replace(/^[\d.* -]+/,"")||"Step "+(i+1)).slice(0,110),detail:s.slice(0,400),gate:"HUMAN_EVIDENCE_REVIEW"}));
 }
 async function savePrivate(e){
  e.preventDefault();
  const name=$("#edit-name").value.trim(),notes=$("#edit-notes").value.trim(),rights=$("#edit-rights").value.trim()||"RIGHTS_UNKNOWN";
  if(name.length<3||notes.length<4){$("#edit-status").textContent="Enter a title and some steps or context.";return}
  const parent=S.parent;
  const predecessor=parent?{id:parent.id,content_sha256:parent.content_sha256||"UNKNOWN",evidence_root:parent.evidence_root||"UNKNOWN"}:null;
  const steps=stepsFromText(notes);
  const raw={schema:"baebugs.LocalProtocolContent.v1",name,notes,rights,predecessor,steps};
  const content_sha256=await sha256(stable(raw));
  const id="local-"+content_sha256.slice(0,20);
  const record={id,name,subtitle:notes.slice(0,116),category:parent?.category||"My lab",
    stage:parent?.stage||"evidence",accent:parent?.accent||"teal",motif:parent?.motif||"graph",
    fit:"Private draft",status:"LOCAL_UNREVIEWED",hardware_gate:!!parent?.hardware_gate,
    sources:parent?.sources||[],source_atoms:parent?.source_atoms||[],steps,tags:parent?.tags||["private"],
    rights_note:rights,content_sha256,context_sha256:"NOT_COMPUTED",evidence_root:parent?.evidence_root||"UNKNOWN",
    parent:predecessor,local:true,notes,execution_permission:"GUIDED_BROWSER_REVIEW_ONLY",signed:"NOT_SIGNED"};
  const i=S.custom.findIndex(x=>x.id===id);if(i>=0)S.custom[i]=record;else S.custom.unshift(record);
  persist();$("#edit-dialog").close();$("#protocol-dialog").close();
  S.view="mine";S.category="All";S.query="";$("#show-mode").value="mine";$("#protocol-search").value="";
  render();details(id);toast("Private protocol saved locally; no lab action performed.");
 }
 async function importFile(e){
  const f=e.target.files?.[0];if(!f)return;
  if(f.size>65536){$("#edit-status").textContent="Limit files to 64 KB.";return}
  try{
   const content=await f.text();let notes=content.slice(0,14000);
   if(f.name.toLowerCase().endsWith(".json")){
    const j=JSON.parse(content);
    if(j&&typeof j==="object"&&!Array.isArray(j)){
      if(typeof j.name==="string")$("#edit-name").value=j.name.slice(0,120);
      if(Array.isArray(j.steps))notes=j.steps.slice(0,16).map((s,i)=>(i+1)+". "+(typeof s==="string"?s:(String(s?.title||"Step")+": "+String(s?.detail||"")))).join("\n").slice(0,14000);
      else if(typeof j.notes==="string")notes=j.notes.slice(0,14000);
    }
   }
   $("#edit-notes").value=notes;
   if(!$("#edit-name").value)$("#edit-name").value=f.name.replace(/\.[^.]+$/,"");
   $("#edit-status").textContent="Imported to this browser only. Review provenance before saving.";
  }catch(err){$("#edit-status").textContent="Import failed: "+err.message}
 }
 function sessionKey(id){return "review:"+id}
 function sessionStart(id){
  const r=find(id);if(!r)return;S.selected=id;$("#protocol-dialog").close();
  $("#session-heading").textContent="Review · "+r.name;
  const checked=(S.sessions[sessionKey(id)]?.checked)||[];
  $("#session-steps").innerHTML=r.steps.map((s,i)=>'<label class="review-item"><input type="checkbox" data-review-step="'+i+'" '+(checked.includes(i)?"checked":"")+'><span><b>'+esc(s.title)+'</b><p>'+esc(s.detail||"")+'</p><small>'+esc(s.gate||"REVIEW_ONLY")+'</small></span></label>').join("");
  updateSessionCount();openDialog("session-dialog");
 }
 function checkedSteps(){return [...$("#session-steps").querySelectorAll("input:checked")].map(n=>Number(n.dataset.reviewStep))}
 function updateSessionCount(){$("#session-count").textContent=checkedSteps().length+" self-checked · PHYSICAL NOT_TESTED"}
 function saveSession(){const k=sessionKey(S.selected);S.sessions[k]={...(S.sessions[k]||{}),checked:checkedSteps()};persist();updateSessionCount()}
 async function sessionExport(){
  const r=find(S.selected);if(!r)return;saveSession();
  const session=S.sessions[sessionKey(r.id)];
  const receipt={
    schema:"baebugs.BrowserReviewFCO.v1",protocol_id:r.id,
    protocol_content_sha256:r.content_sha256||"UNKNOWN",
    protocol_context_sha256:r.context_sha256||"UNKNOWN",
    referenced_evidence_root:r.evidence_root||"UNKNOWN",
    self_checked_step_indices:session.checked,step_count:r.steps.length,
    parent_browser_review_sha256:session.last_receipt||null,
    browser_checklist:"EXECUTED",physical_execution:"NOT_TESTED",specimen_recovery:"NOT_OBSERVED",
    operator_approval:"NOT_GRANTED",scientific_result:"UNKNOWN",signature:"NOT_SIGNED",
    limitation:"Self-reported browser checklist only. No instrument commands were sent."
  };
  const content_sha256=await sha256(stable(receipt));
  S.sessions[sessionKey(r.id)].last_receipt=content_sha256;persist();
  download("baebugs-browser-review-"+r.id+"-"+content_sha256.slice(0,8)+".json",{...receipt,content_sha256});
  toast("Source-addressed browser-review FCO exported. Hardware untouched.");
 }
 document.addEventListener("click",async e=>{
  const a=e.target.closest("[data-open]");if(a){details(a.dataset.open);return}
  const b=e.target.closest("[data-bookmark]");if(b){bookmark(b.dataset.bookmark);return}
  const c=e.target.closest("[data-category]");if(c){S.category=c.dataset.category;render();return}
  if(e.target.closest(".close-dialog")){closeDialog(e.target);return}
  if(e.target.id==="detail-save"){bookmark(S.selected);return}
  if(e.target.id==="detail-collection"){$("#detail-collection-entry").hidden=!$("#detail-collection-entry").hidden;return}
  if(e.target.id==="detail-add-collection"){
   const n=$("#detail-collection-name").value.trim();if(!n||n.length>80){toast("Enter a valid collection name.");return}
   if(!Array.isArray(S.collections[n]))S.collections[n]=[];
   if(!S.collections[n].includes(S.selected))S.collections[n].push(S.selected);
   persist();S.view="collection:"+n;S.category="All";S.query="";$("#protocol-search").value="";render();toast("Showing collection "+n+" (local only).");return;
  }
  if(e.target.id==="detail-remix"){openEditor(find(S.selected));return}
  if(e.target.id==="detail-share"){
   const r=find(S.selected);if(!r)return;
   if(r.local){download("baebugs-private-"+r.id+".json",{schema:"baebugs.LocalProtocolExport.v1",record:r,publication:"NOT_SHARED"});toast("Private copy exported; not published.");return}
   const url=location.origin+location.pathname+"#protocol/"+encodeURIComponent(r.id);
   toast(await copy(url)?"Public template link copied.":"Could not copy; use "+url);return;
  }
  if(e.target.id==="detail-review"){sessionStart(S.selected);return}
 });
 $("#show-mode").addEventListener("change",e=>{S.view=e.target.value;render()});
 $("#protocol-search").addEventListener("input",e=>{S.query=e.target.value;render()});
 $("#reset-filters").addEventListener("click",()=>{S.view="all";S.category="All";S.query="";$("#show-mode").value="all";$("#protocol-search").value="";render()});
 ["nav-import","hero-import","bottom-import","empty-import"].forEach(id=>$("#"+id).addEventListener("click",()=>openEditor(null)));
 $("#edit-form").addEventListener("submit",savePrivate);
 $("#edit-file").addEventListener("change",importFile);
 $("#session-steps").addEventListener("change",saveSession);
 $("#session-export").addEventListener("click",sessionExport);
 $("#session-done").addEventListener("click",()=>$("#session-dialog").close());
 document.addEventListener("keydown",e=>{if(e.key==="/"&&!document.querySelector("dialog[open]")&&!["INPUT","TEXTAREA"].includes(document.activeElement?.tagName)){e.preventDefault();$("#protocol-search").focus()}});
 function activateHash(){if(location.hash==='#new'){openEditor(null);return}const match=location.hash.match(/^#protocol\/(.+)$/);if(!match)return;const id=decodeURIComponent(match[1]);if(find(id))details(id)}
 window.addEventListener("hashchange",activateHash);
 async function init(){
  try{
   const req=await fetch("catalog.json",{cache:"no-store"});
   if(!req.ok)throw new Error("HTTP "+req.status);
   const d=await req.json();
   if(d.schema!=="baebugs.protocol_discovery_projection.v1"||!d.recipes?.length)throw new Error("Incorrect catalog schema");
   const ids=new Set();
   for(const r of d.recipes){
    if(ids.has(r.id))throw new Error("Duplicate protocol");
    ids.add(r.id);
    const core={...r};["content_sha256","context_sha256","source_atoms","evidence_root","execution_permission","signed"].forEach(k=>delete core[k]);
    const digest=await sha256(stable(core));
    if(digest!==r.content_sha256)throw new Error("Template source identity mismatch: "+r.id);
   }
   S.catalog=d;
   const q=new URLSearchParams(location.search).get("q");if(q){S.query=q.slice(0,160);$("#protocol-search").value=S.query}
   render();activateHash();
  }catch(err){
   $("#protocol-grid").innerHTML='<div class="empty" style="display:block"><h3>Catalog integrity gate failed</h3><p>'+esc(err.message)+'. No public templates admitted.</p></div>';
   $("#result-count").textContent="FAILED / source catalog integrity";
   $("#count-templates").textContent="—";
  }
 }
 init();
})();
